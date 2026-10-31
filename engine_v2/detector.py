"""
Human Pose & Interaction Detector for Engine v2.
"""
from typing import List, Dict, Tuple, Optional
import cv2
import numpy as np
from ultralytics import YOLO

from .config import (
    MODEL_POSE_PATH,
    EQUIPMENT_ROI,
    ASSET_ZONES,
    CONF_PERSON_MIN,
    CONF_KEYPOINT_MIN,
    MOTION_DIFF_THRESHOLD,
    MOTION_PIXEL_COUNT_THRESHOLD
)
from .geometry import evaluate_asset_interaction

class MotionFilter:
    """Ultra-fast background difference filter to bypass static video blocks."""
    def __init__(self, diff_threshold: int = MOTION_DIFF_THRESHOLD, pixel_thresh: int = MOTION_PIXEL_COUNT_THRESHOLD):
        self.diff_threshold = diff_threshold
        self.pixel_thresh = pixel_thresh
        self.prev_gray: Optional[np.ndarray] = None

    def has_motion(self, roi_bgr: np.ndarray) -> bool:
        gray = cv2.cvtColor(roi_bgr, cv2.COLOR_BGR2GRAY)
        # Downsample for microsecond motion check
        small_gray = cv2.resize(gray, (320, 180), interpolation=cv2.INTER_NEAREST)
        if self.prev_gray is None:
            self.prev_gray = small_gray
            return True

        diff = cv2.absdiff(self.prev_gray, small_gray)
        self.prev_gray = small_gray
        num_changed = int(np.count_nonzero(diff > self.diff_threshold))
        return num_changed > self.pixel_thresh

class PoseInteractionDetector:
    """Loads YOLOv8-pose and detects Human-Object Interactions within the plant envelope."""
    def __init__(self, model_path: str = MODEL_POSE_PATH, conf: float = CONF_PERSON_MIN):
        self.model = YOLO(model_path)
        self.conf = conf
        self.motion_filter = MotionFilter()

    def process_frame(
        self,
        frame_bgr: np.ndarray,
        force_detect: bool = False
    ) -> Tuple[bool, List[Dict[str, any]]]:
        """
        Processes a full native 3K CCTV frame.
        Returns:
            (motion_detected, list_of_person_detections)
        """
        ymin, xmin, ymax, xmax = EQUIPMENT_ROI
        roi = frame_bgr[ymin:ymax, xmin:xmax]

        # Fast motion gate
        if not force_detect and not self.motion_filter.has_motion(roi):
            return False, []

        results = self.model(roi, conf=self.conf, verbose=False)[0]
        if len(results.boxes) == 0:
            return True, []

        detections = []
        for box, kpt in zip(results.boxes, results.keypoints):
            box_roi = box.xyxy[0].cpu().numpy()
            conf_person = float(box.conf[0])
            kpts_roi = kpt.data[0].cpu().numpy() # [17, 3]

            # Shift coordinates from ROI back to native full-frame
            person_box_native = (
                float(box_roi[0] + xmin),
                float(box_roi[1] + ymin),
                float(box_roi[2] + xmin),
                float(box_roi[3] + ymin)
            )
            kpts_native = kpts_roi.copy()
            kpts_native[:, 0] += xmin
            kpts_native[:, 1] += ymin

            # Check interactions against all registered asset zones
            zone_interactions = {}
            for zone_id, zone in ASSET_ZONES.items():
                eval_res = evaluate_asset_interaction(
                    person_box_native,
                    kpts_native,
                    zone,
                    min_kpt_conf=CONF_KEYPOINT_MIN
                )
                if eval_res["interacted"]:
                    zone_interactions[zone_id] = eval_res

            detections.append({
                "person_box": person_box_native,
                "confidence": conf_person,
                "keypoints": kpts_native,
                "interactions": zone_interactions
            })

        return True, detections

