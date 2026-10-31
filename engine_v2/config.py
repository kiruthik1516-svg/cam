"""
Configuration for Engine v2 (Continuous HOI Computer Vision Incident Engine)
Standalone module - keeps all legacy systems untouched.
"""
from dataclasses import dataclass
from typing import Dict, List, Tuple
import os

# Physical File Paths
CCTV_MASTER_DIR = r"E:\RO WATER SEP"
OUTPUT_MASTER_DIR = r"d:\facial\incident_evidence_v2"
MODEL_POSE_PATH = r"d:\facial\yolov8n-pose.pt"

# Frame Geometry (Native 3K CCTV)
NATIVE_WIDTH = 2880
NATIVE_HEIGHT = 1620

# Active Surveillance Equipment ROI [ymin, xmin, ymax, xmax]
# All plant assets are within the left 1800px and top 1200px
EQUIPMENT_ROI = (0, 0, 1200, 1800)

@dataclass
class AssetZone:
    id: str
    name: str
    severity: str
    # Bounding box in native coordinates: [x1, y1, x2, y2]
    hardware_box: Tuple[int, int, int, int]
    # Human operational envelope: [x1, y1, x2, y2]
    operational_envelope: Tuple[int, int, int, int]
    # Maximum reach radius in pixels for wrist contact trigger
    wrist_reach_radius: int = 90

ASSET_ZONES: Dict[str, AssetZone] = {
    "ZONE_SWITCH": AssetZone(
        id="ZONE_SWITCH",
        name="Plant Main Power Switch Breaker",
        severity="SEVERE",
        hardware_box=(1020, 180, 1085, 260),
        operational_envelope=(960, 150, 1260, 680),
        wrist_reach_radius=100
    ),
    "ZONE_VALVES": AssetZone(
        id="ZONE_VALVES",
        name="Multiport Backwash Valves",
        severity="CRITICAL",
        hardware_box=(720, 210, 960, 430),
        operational_envelope=(680, 200, 1050, 750),
        wrist_reach_radius=110
    ),
    "ZONE_RO_SKID": AssetZone(
        id="ZONE_RO_SKID",
        name="RO Skid Controls & Pump Deck",
        severity="ELEVATED",
        hardware_box=(940, 260, 1450, 720),
        operational_envelope=(900, 240, 1500, 850),
        wrist_reach_radius=120
    ),
    "ZONE_DOORWAY": AssetZone(
        id="ZONE_DOORWAY",
        name="Terrace Entrance Doorway",
        severity="INFORMATIONAL",
        hardware_box=(1220, 150, 1480, 680),
        operational_envelope=(1180, 140, 1520, 750),
        wrist_reach_radius=80
    )
}

# COCO 17-Keypoint Indices
KPT_NOSE = 0
KPT_LEFT_EYE = 1
KPT_RIGHT_EYE = 2
KPT_LEFT_EAR = 3
KPT_RIGHT_EAR = 4
KPT_LEFT_SHOULDER = 5
KPT_RIGHT_SHOULDER = 6
KPT_LEFT_ELBOW = 7
KPT_RIGHT_ELBOW = 8
KPT_LEFT_WRIST = 9
KPT_RIGHT_WRIST = 10
KPT_LEFT_HIP = 11
KPT_RIGHT_HIP = 12
KPT_LEFT_KNEE = 13
KPT_RIGHT_KNEE = 14
KPT_LEFT_ANKLE = 15
KPT_RIGHT_ANKLE = 16

# Detection & Tracking Hyperparameters
CONF_PERSON_MIN = 0.25
CONF_KEYPOINT_MIN = 0.35
MOTION_DIFF_THRESHOLD = 25
MOTION_PIXEL_COUNT_THRESHOLD = 500

# Temporal Clustering & Trimming
SAMPLING_RATE_SCAN_FPS = 2.0         # 2 FPS during scan (1 frame every 15 frames)
SAMPLING_RATE_ACTIVE_FPS = 5.0       # 5 FPS when human presence detected
MIN_INTERACTION_DURATION_SEC = 2.0   # Require at least 2.0s contact / dwell
MERGE_INCIDENT_GAP_SEC = 45.0        # Group interactions within 45s into single session
LEAD_IN_BUFFER_SEC = 30.0            # 30s pre-event buffer
LEAD_OUT_BUFFER_SEC = 30.0           # 30s post-event buffer

