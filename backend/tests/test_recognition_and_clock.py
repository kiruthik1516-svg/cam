"""Tests for Phase 7: Recognition Quality, Edge Stream Scoping & Clock Synchronization (R1, R2, R4, R7)."""

import os
import sys
import uuid
from datetime import datetime, timedelta
from pathlib import Path

import pytest
from fastapi.testclient import TestClient

backend_dir = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(backend_dir))
sys.path.insert(0, str(backend_dir.parent))

from config import IST
from database import get_db
from main import app
from models import Camera, Detection, EventProvenance
from auth import create_access_token
from facial_recognition.sources import CameraSource, dvr_sources_from_env
from facial_recognition.main_cpu import CpuCameraPipeline, TIERS

client = TestClient(app)
EDGE_KEY = os.environ.get("EDGE_API_KEY", "test-edge-api-key")
AUTH_HEADER = {"Authorization": f"Bearer {create_access_token({'sub': 'admin', 'role': 'admin'})}"}


# ==================== R1: Stream Selection & CameraSource Tuple ====================

def test_camera_source_tuple_backward_compatibility():
    """Verify CameraSource behaves as a 2-tuple while providing rich stream and zone metadata."""
    url = "rtsp://viewer:pass@192.168.1.100:554/cam/realmonitor?channel=1&subtype=0"
    src = CameraSource(
        camera_id="door-1",
        url=url,
        name="Front Door Entrance",
        zone="Entrance Lobby",
        stream_type="main",
    )

    # 1. Standard tuple unpacking
    cam_id, rtsp_url = src
    assert cam_id == "door-1"
    assert rtsp_url == url

    # 2. Positional indexing
    assert src[0] == "door-1"
    assert src[1] == url

    # 3. Tuple equality against standard tuple
    assert src == ("door-1", url)
    assert isinstance(src, tuple)

    # 4. Attribute access
    assert src.camera_id == "door-1"
    assert src.url == url
    assert src.name == "Front Door Entrance"
    assert src.zone == "Entrance Lobby"
    assert src.stream_type == "main"


def test_dvr_sources_from_env_parses_display_names_and_zones():
    """Verify dvr_sources_from_env parses display names, zones, and main/sub stream choices."""
    env = {
        "DVR_IP": "10.0.0.50",
        "DVR_USERNAME": "admin",
        "DVR_PASSWORD": "secretpassword",
        "DVR_RTSP_PORT": "554",
        "DVR_RTSP_PATH": "cam/realmonitor?channel={channel}&subtype=1",
        "DVR_CHANNELS": "1:0, 2:1, 3:main",
        "DVR_CAMERA_NAMES": "reception, lane, vault",
        "DVR_CAMERA_DISPLAY_NAMES": "Reception Desk, Vehicle Lane 1, Vault Corridor",
        "DVR_CAMERA_ZONES": "Lobby, Perimeter, Secure Zone",
    }
    sources = dvr_sources_from_env(env)
    assert len(sources) == 3

    # Check Channel 1 (reception, main stream :0)
    assert sources[0].camera_id == "reception"
    assert sources[0].name == "Reception Desk"
    assert sources[0].zone == "Lobby"
    assert sources[0].stream_type == "main"
    assert "subtype=0" in sources[0].url

    # Check Channel 2 (lane, sub stream :1)
    assert sources[1].camera_id == "lane"
    assert sources[1].name == "Vehicle Lane 1"
    assert sources[1].zone == "Perimeter"
    assert sources[1].stream_type == "sub"
    assert "subtype=1" in sources[1].url

    # Check Channel 3 (vault, main stream :main)
    assert sources[2].camera_id == "vault"
    assert sources[2].name == "Vault Corridor"
    assert sources[2].zone == "Secure Zone"
    assert sources[2].stream_type == "main"
    assert "subtype=0" in sources[2].url


# ==================== R2: Dynamic Tier & Resolution Scoping ====================

class DummyDetector:
    def __init__(self):
        self.det_size = (384, 384)

    def detect(self, img):
        return []

    def extract_embedding(self, img, face):
        return None


class DummyRecognizer:
    def __init__(self):
        self.threshold = 0.55
        self.labels = []
        self.embeddings = None


def test_cpu_pipeline_per_camera_tier_override():
    """Verify CpuCameraPipeline honors camera_tiers from config.yaml."""
    camera_tiers = {
        "reception": "max",
        "lane": "slow",
    }
    detector = DummyDetector()
    recognizer = DummyRecognizer()

    pipeline_reception = CpuCameraPipeline(
        camera_id="reception",
        source=CameraSource("reception", "rtsp://...", name="Reception", stream_type="sub"),
        detector=detector,
        recognizer=recognizer,
        logger=None,
        frame_size=(256, 256),
        frame_skip=5,
        cpu_tier="auto",
        camera_tiers=camera_tiers,
    )
    # 'max' tier sets (480, 480) and frame_skip=2
    assert pipeline_reception.frame_size == TIERS["max"]["det_size"]
    assert pipeline_reception.frame_skip == TIERS["max"]["frame_skip"]
    assert pipeline_reception.cpu_tier == "max"

    pipeline_lane = CpuCameraPipeline(
        camera_id="lane",
        source=CameraSource("lane", "rtsp://...", name="Lane", stream_type="main"),
        detector=detector,
        recognizer=recognizer,
        logger=None,
        frame_size=(256, 256),
        frame_skip=5,
        cpu_tier="auto",
        camera_tiers=camera_tiers,
    )
    # Explicit camera_tiers override takes precedence over stream_type
    assert pipeline_lane.frame_size == TIERS["slow"]["det_size"]
    assert pipeline_lane.frame_skip == TIERS["slow"]["frame_skip"]
    assert pipeline_lane.cpu_tier == "slow"


def test_cpu_pipeline_elevates_main_stream_to_max_quality():
    """Verify main stream camera is elevated to max quality tier when tier is auto."""
    detector = DummyDetector()
    recognizer = DummyRecognizer()

    pipeline_entrance = CpuCameraPipeline(
        camera_id="door-main",
        source=CameraSource("door-main", "rtsp://...", name="Doorway", stream_type="main"),
        detector=detector,
        recognizer=recognizer,
        logger=None,
        frame_size=(256, 256),
        frame_skip=5,
        cpu_tier="auto",
        camera_tiers={},
    )
    # Main stream without explicit tier should elevate to max (480x480, skip 2)
    assert pipeline_entrance.frame_size == TIERS["max"]["det_size"]
    assert pipeline_entrance.frame_skip == TIERS["max"]["frame_skip"]
    assert pipeline_entrance.cpu_tier == "max"


# ==================== R4: Clock Skew Detection & Timestamp Provenance ====================

def test_clock_skew_detection_and_provenance_audit():
    """Verify clock skew >120s is detected, logged, and captured in event provenance."""
    event_id = f"evt_skew_{uuid.uuid4().hex[:12]}"
    cam_id = f"cam_skew_{uuid.uuid4().hex[:6]}"

    # Skewed timestamp: 300 seconds in the past
    skewed_ts = datetime.now(IST) - timedelta(seconds=300)

    payload = {
        "camera_id": cam_id,
        "identity": "Unknown",
        "confidence": 0.88,
        "bbox": [50, 50, 150, 150],
        "timestamp": skewed_ts.isoformat(),
        "event_id": event_id,
        "clock_source": "nvr_clock",
        "camera_name": "Perimeter Cam 1",
        "zone": "Perimeter Fence",
    }

    res = client.post(
        "/api/detections",
        headers={"X-API-Key": EDGE_KEY},
        json=payload,
    )
    assert res.status_code == 200

    # Verify provenance endpoint returns clock_source and recorded skew
    prov_res = client.get(f"/api/detections/{event_id}/provenance", headers=AUTH_HEADER)
    assert prov_res.status_code == 200
    prov_data = prov_res.json()

    assert prov_data["clock_source"] == "nvr_clock"
    assert prov_data["clock_skew_seconds"] >= 290.0

    # Verify Stage 1 Camera Ingestion includes clock provenance
    stage1 = next(s for s in prov_data["stages"] if s["stage_name"] == "1. Camera Ingestion")
    assert stage1["metadata"]["clock_source"] == "nvr_clock"
    assert stage1["metadata"]["clock_skew_seconds"] >= 290.0


# ==================== R7: Camera Display Names & Spatial Zone Sync ====================

def test_camera_display_name_and_zone_synchronization():
    """Verify camera display name and zone are synchronized on detection ingestion."""
    cam_id = f"cam_sync_{uuid.uuid4().hex[:8]}"
    event_id = f"evt_sync_{uuid.uuid4().hex[:12]}"

    # Ingest detection with camera_name and zone
    payload = {
        "camera_id": cam_id,
        "identity": "Unknown",
        "confidence": 0.85,
        "bbox": [10, 10, 100, 100],
        "timestamp": datetime.now(IST).isoformat(),
        "event_id": event_id,
        "camera_name": "Executive Boardroom",
        "zone": "Management Suite",
        "clock_source": "edge_pc",
    }

    res = client.post(
        "/api/detections",
        headers={"X-API-Key": EDGE_KEY},
        json=payload,
    )
    assert res.status_code == 200

    # Verify camera was created with human-readable name and zone
    cam_res = client.get(f"/api/cameras/{cam_id}", headers=AUTH_HEADER)
    assert cam_res.status_code == 200
    cam_data = cam_res.json()

    assert cam_data["name"] == "Executive Boardroom"
    assert cam_data["zone"] == "Management Suite"
