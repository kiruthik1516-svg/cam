"""Unit and integration tests for Phase 5: Biometric data retention policy and scheduled cleanup."""

import io
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

from auth import create_access_token
from config import IST
from database import SessionLocal
from main import app
from models import (
    Camera,
    Detection,
    DetectionStatus,
    EventPriority,
    Alert,
    Profile,
    ProfileRole,
    Embedding,
)
from retention import purge_expired_biometrics, get_retention_status

client = TestClient(app)


def _auth():
    return {"Authorization": f"Bearer {create_access_token({'sub': 'admin'})}"}


def test_retention_status_reporting():
    db = SessionLocal()
    try:
        status = get_retention_status(db)
        assert "retention_days" in status
        assert "is_enabled" in status
        assert "total_detections" in status
        assert "detections_with_face_crops" in status
        assert "enrolled_profiles_protected" in status

        resp = client.get("/api/system/retention/status", headers=_auth())
        assert resp.status_code == 200
        data = resp.json()
        assert data["retention_days"] == status["retention_days"]
        assert data["is_enabled"] == status["is_enabled"]
    finally:
        db.close()


def test_purge_expired_biometrics_deletes_old_crops_only():
    db = SessionLocal()
    cam_id = f"cam-{uuid.uuid4().hex[:6]}"
    now = datetime.now(IST)
    old_time = now - timedelta(days=45)
    recent_time = now - timedelta(days=5)

    try:
        db.add(Camera(id=cam_id, name="Retention Test Cam"))

        # 1. Old unflagged detection with face crop
        old_det = Detection(
            id=str(uuid.uuid4()),
            event_id=f"evt_old_{uuid.uuid4().hex[:8]}",
            camera_id=cam_id,
            timestamp=old_time,
            status=DetectionStatus.recognized,
            confidence=0.92,
            bbox="[10, 10, 50, 50]",
            face_image="data:image/jpeg;base64,oldcropdata",
        )
        db.add(old_det)

        # 2. Recent detection with face crop
        recent_det = Detection(
            id=str(uuid.uuid4()),
            event_id=f"evt_recent_{uuid.uuid4().hex[:8]}",
            camera_id=cam_id,
            timestamp=recent_time,
            status=DetectionStatus.recognized,
            confidence=0.88,
            bbox="[20, 20, 60, 60]",
            face_image="data:image/jpeg;base64,recentcropdata",
        )
        db.add(recent_det)
        db.commit()

        # Run purge with 30 days retention
        result = purge_expired_biometrics(db, retention_days=30, preserve_flagged_alerts=True)
        assert result["purged_face_crops_count"] >= 1
        assert result["retention_days"] == 30

        # Verify old detection face_image is pruned but audit record remains
        db.refresh(old_det)
        assert old_det.face_image is None
        assert old_det.confidence == 0.92
        assert old_det.camera_id == cam_id

        # Verify recent detection still has face_image
        db.refresh(recent_det)
        assert recent_det.face_image == "data:image/jpeg;base64,recentcropdata"

    finally:
        db.close()


def test_preserve_flagged_alerts_spares_critical_crops():
    db = SessionLocal()
    cam_id = f"cam-{uuid.uuid4().hex[:6]}"
    now = datetime.now(IST)
    old_time = now - timedelta(days=50)

    try:
        db.add(Camera(id=cam_id, name="Alert Retention Cam"))

        # Old detection that triggered a critical alert
        alert_det_id = str(uuid.uuid4())
        alert_det = Detection(
            id=alert_det_id,
            event_id=f"evt_alert_{uuid.uuid4().hex[:8]}",
            camera_id=cam_id,
            timestamp=old_time,
            status=DetectionStatus.flagged,
            priority=EventPriority.critical,
            confidence=0.95,
            bbox="[15, 15, 55, 55]",
            face_image="data:image/jpeg;base64,criticalalertcrop",
        )
        db.add(alert_det)

        alert_record = Alert(
            id=str(uuid.uuid4()),
            detection_id=alert_det_id,
            camera_id=cam_id,
            timestamp=old_time,
            severity="critical",
            reason="Blacklist match",
        )
        db.add(alert_record)
        db.commit()

        # Purge with preserve_flagged_alerts=True
        purge_expired_biometrics(db, retention_days=30, preserve_flagged_alerts=True)

        # Flagged crop must be preserved
        db.refresh(alert_det)
        assert alert_det.face_image == "data:image/jpeg;base64,criticalalertcrop"

    finally:
        db.close()


def test_system_retention_purge_api_endpoint():
    resp = client.post(
        "/api/system/retention/purge",
        headers=_auth(),
        json={"retention_days": 30, "preserve_flagged_alerts": True},
    )
    assert resp.status_code == 200
    data = resp.json()
    assert "purged_face_crops_count" in data
    assert "retained_face_crops_count" in data
    assert data["retention_days"] == 30
    assert data["preserve_flagged_alerts"] is True


def test_retention_disabled_when_zero():
    db = SessionLocal()
    try:
        res = purge_expired_biometrics(db, retention_days=0)
        assert res["purged_face_crops_count"] == 0
        assert res["cutoff_timestamp"] is None
    finally:
        db.close()
