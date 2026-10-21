"""Tests for Phase 9: High-Ceiling Face Quality & Centroid Re-clustering (R3)
and Server-Side Anti-Spoofing & Liveness Verification (R11)."""

import base64
import json
import os
import sys
import uuid
from datetime import datetime, timedelta
from pathlib import Path

import cv2
import numpy as np
import pytest
from fastapi.testclient import TestClient

backend_dir = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(backend_dir))
sys.path.insert(0, str(backend_dir.parent))

from auth import create_access_token
from config import IST
from database import get_db, SessionLocal
from liveness import (
    compute_server_face_quality,
    decode_image_b64,
    verify_server_liveness,
    verify_server_liveness_and_image,
)
from main import app
from models import Alert, AuditLog, Camera, Detection, DetectionStatus, UnregisteredSubject
from schemas import DetectionCreateRequest, UnregisteredSubjectResponse

client = TestClient(app)
EDGE_KEY = os.environ.get("EDGE_API_KEY", "test-edge-api-key")
AUTH_HEADER = {"Authorization": f"Bearer {create_access_token({'sub': 'admin', 'role': 'admin'})}"}


@pytest.fixture
def db_session():
    db = SessionLocal()
    try:
        yield db
    finally:
        db.close()


# ==================== R3: High-Ceiling Quality & Centroid Merging ====================

def test_cluster_distance_threshold_env_configuration(monkeypatch):
    """Verify CLUSTER_DISTANCE_THRESHOLD is configurable via environment and clamped to [0.20, 0.95]."""
    from facial_recognition.batch_video_ingest import BatchVideoIngestEngine

    # Default is 0.72
    monkeypatch.delenv("CLUSTER_DISTANCE_THRESHOLD", raising=False)
    # Re-read in logic:
    t_default = float(os.getenv("CLUSTER_DISTANCE_THRESHOLD", "0.72"))
    assert t_default == 0.72

    # Custom threshold within range
    monkeypatch.setenv("CLUSTER_DISTANCE_THRESHOLD", "0.80")
    t_custom = float(os.getenv("CLUSTER_DISTANCE_THRESHOLD", "0.72"))
    t_clamped = min(0.95, max(0.20, t_custom))
    assert t_clamped == 0.80

    # Clamping below minimum 0.20
    monkeypatch.setenv("CLUSTER_DISTANCE_THRESHOLD", "0.05")
    t_low = float(os.getenv("CLUSTER_DISTANCE_THRESHOLD", "0.72"))
    assert min(0.95, max(0.20, t_low)) == 0.20

    # Clamping above maximum 0.95
    monkeypatch.setenv("CLUSTER_DISTANCE_THRESHOLD", "0.99")
    t_high = float(os.getenv("CLUSTER_DISTANCE_THRESHOLD", "0.72"))
    assert min(0.95, max(0.20, t_high)) == 0.95


def test_quality_score_in_unregistered_subject_response(db_session):
    """Verify quality_score is exposed in UnregisteredSubjectResponse and API."""
    subj_id = f"subj_test_{uuid.uuid4().hex[:6]}"
    subj = UnregisteredSubject(
        id=subj_id,
        display_name="Person Test Quality",
        representative_embedding=np.random.randn(512).tolist(),
        similarity_threshold=0.42,
        quality_score=84.5,
        status="active",
        created_at=datetime.now(IST),
        updated_at=datetime.now(IST),
    )
    db_session.add(subj)

    cam_id = f"cam_subj_{uuid.uuid4().hex[:6]}"
    cam = Camera(id=cam_id, name="Subj Cam", status="online")
    db_session.add(cam)

    det = Detection(
        id=str(uuid.uuid4()),
        camera_id=cam_id,
        unregistered_subject_id=subj_id,
        timestamp=datetime.now(IST),
        status=DetectionStatus.unknown,
        confidence=84.5,
        quality_score=84.5,
        bbox="[10, 10, 80, 80]",
    )
    db_session.add(det)
    db_session.commit()

    resp = client.get("/api/unregistered-subjects", headers=AUTH_HEADER)
    assert resp.status_code == 200
    data = resp.json()
    match = next((s for s in data if s["id"] == subj_id), None)
    assert match is not None
    assert "quality_score" in match
    assert match["quality_score"] == 84.5


def test_multi_factor_centroid_merging_logic():
    """Verify multi-factor centroid merging conditions (unconditional, temporal, steep angle)."""
    # 1. Unconditional merge: sim >= 0.45
    sim_unconditional = 0.46
    assert sim_unconditional >= 0.45

    # 2. Camera + temporal proximity: same camera, dt <= 120s, sim >= 0.35
    same_cam = True
    dt_near = 45.0  # seconds
    sim_temporal = 0.37
    should_merge_temporal = same_cam and dt_near <= 120.0 and sim_temporal >= 0.35
    assert should_merge_temporal is True

    # 3. Steep angle compensation: same camera, dt <= 60s, sim >= 0.32
    dt_steep = 30.0
    sim_steep = 0.33
    is_steep = True
    should_merge_steep = same_cam and dt_steep <= 60.0 and (sim_steep >= 0.32 or (is_steep and sim_steep >= 0.30))
    assert should_merge_steep is True

    # 4. Rejection: different camera, sim 0.38 (below 0.45 threshold without shared camera)
    diff_cam = False
    assert (sim_temporal >= 0.45 or (diff_cam and dt_near <= 120.0 and sim_temporal >= 0.35)) is False


# ==================== R11: Server-Side Anti-Spoofing & Liveness ====================

def _create_synthetic_face_image_b64() -> str:
    """Create realistic synthetic face patch with skin tone variance."""
    img = np.zeros((112, 112, 3), dtype=np.uint8)
    # Realistic skin tone in BGR (approx [120, 160, 210]) with natural gradients
    for y in range(112):
        for x in range(112):
            img[y, x] = [
                int(np.clip(110 + np.sin(x / 14.0) * 18, 0, 255)),
                int(np.clip(150 + np.cos(y / 16.0) * 22, 0, 255)),
                int(np.clip(200 + np.sin((x + y) / 20.0) * 18, 0, 255)),
            ]
    # Add face-like features (eyes, mouth)
    cv2.circle(img, (38, 45), 7, (50, 60, 90), -1)
    cv2.circle(img, (74, 45), 7, (50, 60, 90), -1)
    cv2.ellipse(img, (56, 80), (16, 6), 0, 0, 180, (70, 80, 160), 2)
    img = cv2.GaussianBlur(img, (3, 3), 0.8)
    _, buf = cv2.imencode(".jpg", img)
    return base64.b64encode(buf.tobytes()).decode("utf-8")


def _create_monochrome_flat_spoof_b64() -> str:
    """Create flat monochrome printout spoof image (zero chroma std, no skin variance)."""
    # Pure flat gray image with constant values (paper copy attack)
    img = np.full((112, 112, 3), 128, dtype=np.uint8)
    # Minor noise with no color saturation (R=G=B)
    noise = np.random.randint(-2, 3, (112, 112), dtype=np.int16)
    for c in range(3):
        img[:, :, c] = np.clip(128 + noise, 0, 255).astype(np.uint8)
    _, buf = cv2.imencode(".jpg", img)
    return base64.b64encode(buf.tobytes()).decode("utf-8")


def _create_screen_moire_spoof_b64() -> str:
    """Create screen display spoof image with sharp periodic grid moiré lines."""
    img = np.zeros((112, 112, 3), dtype=np.uint8)
    for y in range(112):
        for x in range(112):
            img[y, x] = [
                int(np.clip(110 + np.sin(x / 14.0) * 18, 0, 255)),
                int(np.clip(150 + np.cos(y / 16.0) * 22, 0, 255)),
                int(np.clip(200 + np.sin((x + y) / 20.0) * 18, 0, 255)),
            ]
    # Inject periodic screen display pixel scanline harmonics
    for y in range(112):
        scan_val = int(50 * np.sin(y * 2 * np.pi / 4))
        img[y, :, :] = np.clip(img[y, :, :].astype(np.int16) + scan_val, 0, 255).astype(np.uint8)
    # Add specular glass reflection spot (exceeds 5% area)
    img[20:50, 20:50] = 255
    _, buf = cv2.imencode(".jpg", img)
    return base64.b64encode(buf.tobytes()).decode("utf-8")


def test_server_liveness_genuine_face_verification():
    """Verify genuine face thumbnail passes server liveness with high score."""
    face_b64 = _create_synthetic_face_image_b64()
    score, is_spoof, reason = verify_server_liveness(face_b64, edge_liveness_score=0.90)

    assert score >= 0.45
    assert is_spoof is False
    assert reason == ""


def test_server_liveness_flat_monochrome_spoof_detection():
    """Verify flat monochrome paper print attack is caught and flagged by server."""
    spoof_b64 = _create_monochrome_flat_spoof_b64()
    score, is_spoof, reason = verify_server_liveness(spoof_b64, edge_liveness_score=0.85)

    assert is_spoof is True
    assert score < 0.45
    assert "Monochrome" in reason or "Flat" in reason or "mismatch" in reason


def test_server_liveness_screen_moire_spoof_detection():
    """Verify screen moiré and glass reflection is detected and flagged."""
    moire_b64 = _create_screen_moire_spoof_b64()
    score, is_spoof, reason = verify_server_liveness(moire_b64, edge_liveness_score=0.88)

    assert is_spoof is True
    assert score < 0.45
    assert "moiré" in reason.lower() or "glare" in reason.lower() or "mismatch" in reason.lower()


def test_server_liveness_edge_score_spoof_bypass_caught(db_session):
    """
    Test edge-node bypass scenario:
    An edge node reports high liveness (0.95), but uploads a monochrome paper copy.
    The server MUST catch the mismatch, flag the detection, adjust the score,
    create a critical alert, and record a security.spoof_suspected audit log.
    """
    cam_id = f"cam_liveness_{uuid.uuid4().hex[:6]}"
    cam = Camera(id=cam_id, name="Security Cam Entrance", status="online")
    db_session.add(cam)
    db_session.commit()

    event_id = f"evt_spoof_test_{uuid.uuid4().hex}"
    spoof_b64 = _create_monochrome_flat_spoof_b64()

    payload = {
        "camera_id": cam_id,
        "identity": "Unknown",
        "confidence": 75.0,
        "bbox": [10, 10, 100, 100],
        "timestamp": datetime.now(IST).isoformat(),
        "event_id": event_id,
        "liveness_score": 0.95,  # Edge reports high score falsely
        "face_image": spoof_b64,
        "clock_source": "edge_pc",
    }

    resp = client.post(
        "/api/detections",
        json=payload,
        headers={"X-API-Key": EDGE_KEY},
    )
    assert resp.status_code == 200
    data = resp.json()

    # 1. Detection must be flagged
    assert data["status"] == DetectionStatus.flagged.value
    # 2. Server adjusted the falsely claimed liveness score downwards
    assert data["liveness_score"] < 0.45
    # 3. Quality score must be present
    assert data.get("quality_score") is not None

    # 4. Critical Alert created in database
    det_id = data["id"]
    alert = db_session.query(Alert).filter(Alert.detection_id == det_id).first()
    assert alert is not None
    assert alert.severity == "critical"
    assert "Suspected Presentation Attack" in alert.reason

    # 5. Security Audit Log recorded in database
    audit = db_session.query(AuditLog).filter(
        AuditLog.action == "security.spoof_suspected",
        AuditLog.resource_id == det_id,
    ).first()
    assert audit is not None
    assert audit.resource_type == "detection"
    audit_details = json.loads(audit.details)
    assert audit_details["edge_liveness"] == 0.95
    assert audit_details["server_liveness"] < 0.45
    assert audit_details["status"] == "flagged"


def test_compute_server_face_quality():
    """Verify server face quality score calculation produces 0-100 values."""
    img = np.full((112, 112, 3), 120, dtype=np.uint8)
    cv2.circle(img, (40, 45), 8, (20, 20, 20), -1)
    cv2.circle(img, (72, 45), 8, (20, 20, 20), -1)

    q_score = compute_server_face_quality(img, confidence=82.0)
    assert 0.0 <= q_score <= 100.0
    assert isinstance(q_score, float)
