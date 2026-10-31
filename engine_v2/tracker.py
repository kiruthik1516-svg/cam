"""
Temporal Tracklet & Identity Fusion Manager for Engine v2.
"""
from typing import List, Dict, Tuple, Optional
import numpy as np

def calculate_iou(boxA: Tuple[float, float, float, float], boxB: Tuple[float, float, float, float]) -> float:
    xA = max(boxA[0], boxB[0])
    yA = max(boxA[1], boxB[1])
    xB = min(boxA[2], boxB[2])
    yB = min(boxA[3], boxB[3])

    inter_w = max(0.0, xB - xA)
    inter_h = max(0.0, yB - yA)
    inter_area = inter_w * inter_h

    areaA = max(1.0, (boxA[2] - boxA[0]) * (boxA[3] - boxA[1]))
    areaB = max(1.0, (boxB[2] - boxB[0]) * (boxB[3] - boxB[1]))
    union_area = areaA + areaB - inter_area
    return float(inter_area / union_area)

class Tracklet:
    def __init__(self, track_id: int, initial_box: Tuple[float, float, float, float], timestamp: float):
        self.track_id = track_id
        self.boxes: List[Tuple[float, float, float, float]] = [initial_box]
        self.timestamps: List[float] = [timestamp]
        self.last_seen: float = timestamp
        self.interactions: List[Dict[str, any]] = []
        self.identity_label: str = f"PERSON_TRK_{track_id:03d}"
        self.identity_confidence: float = 0.0
        self.doorway_entered: bool = False

    @property
    def latest_box(self) -> Tuple[float, float, float, float]:
        return self.boxes[-1]

    def update(self, box: Tuple[float, float, float, float], timestamp: float, interaction_data: Dict[str, any]):
        self.boxes.append(box)
        self.timestamps.append(timestamp)
        self.last_seen = timestamp
        if interaction_data:
            self.interactions.append({
                "timestamp": timestamp,
                "data": interaction_data
            })

class TrackletManager:
    """Associates detections across time and retains tracklet continuity."""
    def __init__(self, max_gap_seconds: float = 5.0, min_iou: float = 0.15):
        self.max_gap_seconds = max_gap_seconds
        self.min_iou = min_iou
        self.next_track_id = 1
        self.active_tracks: List[Tracklet] = []
        self.completed_tracks: List[Tracklet] = []

    def update(self, detections: List[Dict[str, any]], timestamp: float) -> List[Tracklet]:
        """
        Updates active tracklets with new frame detections.
        Returns list of matched tracklets for this frame.
        """
        # Retire stale tracks
        active = []
        for trk in self.active_tracks:
            if timestamp - trk.last_seen <= self.max_gap_seconds:
                active.append(trk)
            else:
                self.completed_tracks.append(trk)
        self.active_tracks = active

        assigned_detections = set()
        matched_tracks = []

        # Greedy IoU assignment
        for trk in self.active_tracks:
            best_iou = self.min_iou
            best_idx = -1
            for idx, det in enumerate(detections):
                if idx in assigned_detections:
                    continue
                iou = calculate_iou(trk.latest_box, det["person_box"])
                if iou > best_iou:
                    best_iou = iou
                    best_idx = idx

            if best_idx != -1:
                assigned_detections.add(best_idx)
                det = detections[best_idx]
                trk.update(det["person_box"], timestamp, det.get("interactions", {}))
                matched_tracks.append(trk)

        # Create new tracklets for unmatched detections
        for idx, det in enumerate(detections):
            if idx not in assigned_detections:
                new_trk = Tracklet(self.next_track_id, det["person_box"], timestamp)
                self.next_track_id += 1
                if det.get("interactions"):
                    new_trk.interactions.append({
                        "timestamp": timestamp,
                        "data": det["interactions"]
                    })
                self.active_tracks.append(new_trk)
                matched_tracks.append(new_trk)

        return matched_tracks

    def finalize(self) -> List[Tracklet]:
        """Flushes all remaining active tracks."""
        self.completed_tracks.extend(self.active_tracks)
        self.active_tracks = []
        return self.completed_tracks

