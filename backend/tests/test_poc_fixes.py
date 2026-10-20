"""Regression tests for the dashboard KPI fields, live camera registration, thresholds and enrollment errors."""

import io
import os
import sys
import uuid
from datetime import datetime, timedelta
from pathlib import Path

backend_dir = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(backend_dir))
sys.path.insert(0, str(backend_dir.parent))

from fastapi.testclient import TestClient

from auth import create_access_token
from config import IST
from database import SessionLocal
from main import app
from models import Camera, Detection, DetectionStatus, DataSource

client = TestClient(app)
EDGE_KEY = os.environ.get("EDGE_API_KEY", "test-edge-api-key")


def _auth():
    return {"Authorization": f"Bearer {create_access_token({'sub': 'admin'})}"}


def _edge():
    return {"X-API-Key": EDGE_KEY}


def _push_frame(camera_id: str):
    return client.post(
        f"/api/internal/cameras/{camera_id}/frame",
        content=b"\xff\xd8fake-jpeg\xff\xd9",
        headers={**_edge(), "Content-Type": "image/jpeg"},
    )


# ---------------------------------------------------------------- KPIs

def test_kpis_expose_the_fields_the_dashboard_reads():
    data = client.get("/api/kpis?source=live", headers=_auth()).json()
    for key in ("connected_cameras", "total_cameras", "detections_today", "active_alerts", "system_health"):
        assert key in data, key
    assert data["system_health"] in ("green", "yellow", "red")
    assert data["connected_cameras"] <= data["total_cameras"]


def test_archive_kpis_use_the_batch_totals_not_today():
    batch_id = f"batch_{uuid.uuid4().hex[:8]}"
    camera_id = f"archive-cam-{uuid.uuid4().hex[:6]}"
    old = datetime.now(IST) - timedelta(days=30)
    db = SessionLocal()
    try:
        db.add(Camera(id=camera_id, name=camera_id))
        db.flush()
        for _ in range(2):
            db.add(Detection(
                id=str(uuid.uuid4()), camera_id=camera_id, timestamp=old, source=DataSource.archive,
                batch_id=batch_id, status=DetectionStatus.unknown, confidence=0.0,
            ))
        db.commit()
    finally:
        db.close()

    data = client.get(f"/api/kpis?source=archive&batch_id={batch_id}", headers=_auth()).json()
    assert data["detections_today"] == 2          # batch total, although the data is 30 days old
    assert data["total_cameras"] == 1
    assert data["connected_cameras"] == 1
    assert data["system_health"] == "green"

    archive_cams = client.get(f"/api/cameras?source=archive&batch_id={batch_id}", headers=_auth()).json()
    assert [c["id"] for c in archive_cams] == [camera_id]
    live_ids = [c["id"] for c in client.get("/api/cameras?source=live", headers=_auth()).json()]
    assert camera_id not in live_ids              # imported footage must not appear as a live camera


# ---------------------------------------------------------------- live camera registration

def test_first_frame_registers_a_live_camera():
    camera_id = f"live-cam-{uuid.uuid4().hex[:6]}"
    assert _push_frame(camera_id).status_code == 204

    live = {c["id"]: c for c in client.get("/api/cameras?source=live", headers=_auth()).json()}
    assert camera_id in live
    assert live[camera_id]["status"] == "online"

    kpis = client.get("/api/kpis?source=live", headers=_auth()).json()
    assert kpis["total_cameras"] >= 1 and kpis["connected_cameras"] >= 1

    archive_ids = [c["id"] for c in client.get("/api/cameras?source=archive", headers=_auth()).json()]
    assert camera_id not in archive_ids


def test_camera_goes_offline_when_frames_stop():
    import state
    camera_id = f"stale-cam-{uuid.uuid4().hex[:6]}"
    assert _push_frame(camera_id).status_code == 204
    state.get_frame_slot(camera_id).last_frame_at -= state.LIVE_FRAME_MAX_AGE_SECONDS + 5

    live = {c["id"]: c for c in client.get("/api/cameras?source=live", headers=_auth()).json()}
    assert live[camera_id]["status"] == "offline"


def test_frame_push_rejects_odd_camera_ids():
    assert _push_frame("bad%20id").status_code == 400
    assert _push_frame("x" * 65).status_code == 400


def test_cameras_without_source_still_lists_everything():
    camera_id = f"all-cam-{uuid.uuid4().hex[:6]}"
    assert _push_frame(camera_id).status_code == 204
    ids = [c["id"] for c in client.get("/api/cameras", headers=_auth()).json()]
    assert camera_id in ids


# ---------------------------------------------------------------- thresholds and enrollment

def test_update_thresholds_succeeds():
    body = {"similarity_confidence": 0.61, "liveness_threshold": 0.5, "age_variance": 5.0}
    response = client.post("/api/thresholds", json=body, headers=_auth())
    assert response.status_code == 200
    assert response.json()["similarity_confidence"] == 0.61


def test_enrolling_photos_without_a_loaded_model_is_a_clear_error():
    import state
    assert state.ai_models.get("detector") is None  # tests run without the face model
    before = client.get("/api/profiles", headers=_auth()).json()
    response = client.post(
        "/api/profiles",
        data={"name": "No Model Person", "role": "visitor"},
        files={"photos": ("face.jpg", io.BytesIO(b"not-a-real-image"), "image/jpeg")},
        headers=_auth(),
    )
    assert response.status_code == 503
    assert "ENABLE_FORENSIC_SEARCH" in response.json()["detail"]
    after = client.get("/api/profiles", headers=_auth()).json()
    assert len(after) == len(before)              # no half-created profile left behind


def test_package_attributes_are_lazy_and_unknown_names_fail():
    import facial_recognition
    import pytest
    with pytest.raises(AttributeError):
        facial_recognition.DoesNotExist
def test_thresholds_round_trip_including_switches_and_retention():
    body = {
        "similarity_confidence": 0.66, "liveness_threshold": 0.4, "age_variance": 7.5,
        "unknown_face_retention_days": 14, "auto_alert_on_blacklist": False,
    }
    assert client.post("/api/thresholds", json=body, headers=_auth()).status_code == 200
    saved = client.get("/api/thresholds", headers=_auth()).json()
    assert saved["similarity_confidence"] == 0.66 and saved["age_variance"] == 7.5
    assert saved["unknown_face_retention_days"] == 14
    assert saved["auto_alert_on_blacklist"] is False   # a boolean survives storage in a numeric column

