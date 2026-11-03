"""
Spatial Geometry and Computer Vision Contact Math for Engine v2.
"""
from typing import Tuple, List, Dict, Optional
import numpy as np
import cv2
from .config import ASSET_ZONES, AssetZone, KPT_LEFT_WRIST, KPT_RIGHT_WRIST

def point_in_box(pt: Tuple[float, float], box: Tuple[int, int, int, int]) -> bool:
    """Check if point (x, y) is inside box [x1, y1, x2, y2]."""
    x, y = pt
    x1, y1, x2, y2 = box
    return x1 <= x <= x2 and y1 <= y <= y2

def point_to_box_distance(pt: Tuple[float, float], box: Tuple[int, int, int, int]) -> float:
    """Calculate Euclidean distance from point (x, y) to closest boundary of box."""
    x, y = pt
    x1, y1, x2, y2 = box
    dx = max(x1 - x, 0, x - x2)
    dy = max(y1 - y, 0, y - y2)
    return float(np.hypot(dx, dy))

def box_intersection_ratio(boxA: Tuple[float, float, float, float], boxB: Tuple[int, int, int, int]) -> float:
    """Calculate intersection area relative to boxA area."""
    xA = max(boxA[0], boxB[0])
    yA = max(boxA[1], boxB[1])
    xB = min(boxA[2], boxB[2])
    yB = min(boxA[3], boxB[3])

    inter_w = max(0.0, xB - xA)
    inter_h = max(0.0, yB - yA)
    inter_area = inter_w * inter_h

    boxA_area = max(1.0, (boxA[2] - boxA[0]) * (boxA[3] - boxA[1]))
    return float(inter_area / boxA_area)

def evaluate_asset_interaction(
    person_box: Tuple[float, float, float, float],
    keypoints: np.ndarray,
    zone: AssetZone,
    min_kpt_conf: float = 0.35
) -> Dict[str, any]:
    """
    Evaluates whether a detected person is physically interacting with an asset zone,
    enforcing rigorous physical geometry, vertical elevation, and stance gates.
    """
    lw = keypoints[KPT_LEFT_WRIST]   # [x, y, conf]
    rw = keypoints[KPT_RIGHT_WRIST]  # [x, y, conf]

    lw_valid = lw[2] >= min_kpt_conf
    rw_valid = rw[2] >= min_kpt_conf

    lw_dist = point_to_box_distance((lw[0], lw[1]), zone.hardware_box) if lw_valid else 9999.0
    rw_dist = point_to_box_distance((rw[0], rw[1]), zone.hardware_box) if rw_valid else 9999.0
    min_wrist_dist = min(lw_dist, rw_dist)

    cx = (person_box[0] + person_box[2]) / 2.0
    cy = (person_box[1] + person_box[3]) / 2.0
    overlap = box_intersection_ratio(person_box, zone.operational_envelope)
    body_center_in_envelope = point_in_box((cx, cy), zone.operational_envelope)

    interacted = False
    interaction_type = "NONE"
    wrist_contact = False
    active_wrist = None

    if zone.id == "ZONE_SWITCH":
        # 1. Physical Perspective & Elevation Gate for Wall Power Switch:
        # A) Perspective Ground-Plane Gate: The wall switch sits on the foreground pillar.
        # An operator standing at the switch has feet on the deck floor (person_box[3] >= 480px).
        # Background pedestrians (person_box[3] < 480px) are 15m away in the background doorway/stairs.
        if person_box[3] < 480.0:
            return {
                "interacted": False,
                "interaction_type": "NONE",
                "wrist_contact": False,
                "active_wrist": None,
                "min_wrist_dist": min_wrist_dist,
                "overlap_ratio": overlap
            }

        # B) Vertical Elevation Gate: Switch toggle handle is at Y in [170, 265].
        # Wrist MUST reach into the toggle casing (Y <= 270px) to touch or toggle the breaker.
        # Walking arms swinging at hip/waist height (Y >= 280px) are physically rejected.
        lw_contact = lw_valid and (lw[1] <= 270.0) and (lw_dist <= zone.wrist_reach_radius)
        rw_contact = rw_valid and (rw[1] <= 270.0) and (rw_dist <= zone.wrist_reach_radius)

        if lw_contact and rw_contact:
            wrist_contact = True
            active_wrist = "BOTH"
            interacted = True
            interaction_type = "WRIST_CONTACT"
        elif lw_contact:
            wrist_contact = True
            active_wrist = "LEFT"
            interacted = True
            interaction_type = "WRIST_CONTACT"
        elif rw_contact:
            wrist_contact = True
            active_wrist = "RIGHT"
            interacted = True
            interaction_type = "WRIST_CONTACT"
        elif (lw_valid and lw[1] <= 270.0 and lw_dist <= 55.0) or (rw_valid and rw[1] <= 270.0 and rw_dist <= 55.0):
            interacted = True
            interaction_type = "INSTANT_MICRO_TOGGLE"
            active_wrist = "LEFT" if (lw_valid and lw[1] <= 270.0 and lw_dist <= 55.0) else "RIGHT"

    elif zone.id == "ZONE_VALVES":
        # 2. Operator Stance & Valve Reach Gate:
        # Operator must be stationed on the valve maintenance deck (person_box x1 <= 850 or cx <= 820)
        # and wrist must penetrate the valve manipulation plane (x <= 820, y in [260, 550]).
        operator_on_deck = (person_box[0] <= 850.0) or (cx <= 820.0)
        if operator_on_deck:
            lw_v_contact = lw_valid and (lw[0] <= 820.0 and 260.0 <= lw[1] <= 550.0) and (lw_dist <= zone.wrist_reach_radius)
            rw_v_contact = rw_valid and (rw[0] <= 820.0 and 260.0 <= rw[1] <= 550.0) and (rw_dist <= zone.wrist_reach_radius)
            if lw_v_contact and rw_v_contact:
                wrist_contact = True
                active_wrist = "BOTH"
                interacted = True
                interaction_type = "WRIST_CONTACT"
            elif lw_v_contact:
                wrist_contact = True
                active_wrist = "LEFT"
                interacted = True
                interaction_type = "WRIST_CONTACT"
            elif rw_v_contact:
                wrist_contact = True
                active_wrist = "RIGHT"
                interacted = True
                interaction_type = "WRIST_CONTACT"
            elif body_center_in_envelope and overlap > 0.40:
                interacted = True
                interaction_type = "PROXIMITY_DWELL"

    elif zone.id == "ZONE_RO_SKID":
        # 3. RO Skid Controls:
        # Equipment deck controls are at Y in [340, 700]. Walking in corridor entrance (Y < 340) is not deck control contact.
        lw_skid = lw_valid and (960.0 <= lw[0] <= 1420.0 and 340.0 <= lw[1] <= 700.0) and (lw_dist <= zone.wrist_reach_radius)
        rw_skid = rw_valid and (960.0 <= rw[0] <= 1420.0 and 340.0 <= rw[1] <= 700.0) and (rw_dist <= zone.wrist_reach_radius)
        if lw_skid or rw_skid:
            wrist_contact = True
            active_wrist = "BOTH" if (lw_skid and rw_skid) else ("LEFT" if lw_skid else "RIGHT")
            interacted = True
            interaction_type = "WRIST_CONTACT"
        elif body_center_in_envelope and overlap > 0.35:
            interacted = True
            interaction_type = "PROXIMITY_DWELL"

    elif zone.id == "ZONE_DOORWAY":
        # 4. Corridor Walkway:
        if body_center_in_envelope and overlap > 0.25:
            interacted = True
            interaction_type = "CORRIDOR_PRESENCE"

    return {
        "interacted": interacted,
        "interaction_type": interaction_type,
        "wrist_contact": wrist_contact,
        "active_wrist": active_wrist,
        "min_wrist_dist": min_wrist_dist,
        "overlap_ratio": overlap
    }

# Skeleton connections for rendering (COCO format)
SKELETON_PAIRS = [
    (0, 1), (0, 2), (1, 3), (2, 4),           # Head
    (5, 6), (5, 7), (7, 9), (6, 8), (8, 10),  # Arms & Wrists
    (5, 11), (6, 12), (11, 12),               # Torso
    (11, 13), (13, 15), (12, 14), (14, 16)    # Legs
]

def render_pose_skeleton(
    img: np.ndarray,
    keypoints: np.ndarray,
    person_box: Optional[Tuple[float, float, float, float]] = None,
    min_conf: float = 0.35,
    highlight_wrists: bool = False
) -> np.ndarray:
    """Renders high-visibility skeleton and joints onto the image."""
    canvas = img.copy()
    
    if person_box is not None:
        x1, y1, x2, y2 = [int(v) for v in person_box]
        cv2.rectangle(canvas, (x1, y1), (x2, y2), (0, 255, 0), 2)

    # Draw bones
    for p1, p2 in SKELETON_PAIRS:
        if p1 < len(keypoints) and p2 < len(keypoints):
            pt1 = keypoints[p1]
            pt2 = keypoints[p2]
            if pt1[2] >= min_conf and pt2[2] >= min_conf:
                c1 = (int(pt1[0]), int(pt1[1]))
                c2 = (int(pt2[0]), int(pt2[1]))
                cv2.line(canvas, c1, c2, (0, 220, 255), 2, cv2.LINE_AA)

    # Draw keypoint circles
    for i, pt in enumerate(keypoints):
        if pt[2] >= min_conf:
            pos = (int(pt[0]), int(pt[1]))
            if i in (KPT_LEFT_WRIST, KPT_RIGHT_WRIST):
                color = (0, 0, 255) if highlight_wrists else (0, 255, 255)
                radius = 7 if highlight_wrists else 5
                cv2.circle(canvas, pos, radius, color, -1, cv2.LINE_AA)
                cv2.circle(canvas, pos, radius + 2, (255, 255, 255), 1, cv2.LINE_AA)
            else:
                cv2.circle(canvas, pos, 4, (255, 0, 0), -1, cv2.LINE_AA)

    return canvas

