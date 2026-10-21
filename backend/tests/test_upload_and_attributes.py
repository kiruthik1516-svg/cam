"""Tests for S6 (upload limits and MIME validation) and R10 (mask and glasses attribute tracking and filtering)."""

import io
import os
import sys
import uuid
from datetime import datetime
from pathlib import Path
import pytest
from fastapi import HTTPException
from fastapi.testclient import TestClient

backend_dir = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(backend_dir))
sys.path.insert(0, str(backend_dir.parent))

from auth import create_access_token
from config import IST
from database import SessionLocal
from main import app
from models import Camera, Detection, DetectionStatus, Profile, ProfileRole, Embedding
from utils import validate_image_upload, is_valid_image_bytes

client = TestClient(app)
EDGE_KEY = os.environ.get("EDGE_API_KEY", "test-edge-api-key")


def _auth():
    return {"Authorization": f"Bearer {create_access_token({'sub': 'admin'})}"}


def _edge():
    return {"X-API-Key": EDGE_KEY}


import asyncio


# ---------------------------------------------------------------- S6: Upload Validation Tests

def test_validate_image_upload_magic_bytes():
    assert is_valid_image_bytes(b"\xff\xd8\xff\xe0" + b"\x00" * 10) is True  # JPEG
    assert is_valid_image_bytes(b"\x89PNG\r\n\x1a\n" + b"\x00" * 10) is True  # PNG
    assert is_valid_image_bytes(b"RIFF\x00\x00\x00\x00WEBP" + b"\x00" * 10) is True  # WebP
    assert is_valid_image_bytes(b"BM" + b"\x00" * 10) is True  # BMP
    assert is_valid_image_bytes(b"Hello World, not an image") is False
    assert is_valid_image_bytes(b"") is False


def test_validate_image_upload_empty():
    class MockEmptyFile:
        async def read(self, n=-1):
            return b""

    with pytest.raises(HTTPException) as exc_info:
        asyncio.run(validate_image_upload(MockEmptyFile()))
    assert exc_info.value.status_code == 400
    assert "empty" in exc_info.value.detail.lower()


def test_validate_image_upload_oversized():
    # Test with custom max_size of 100 bytes
    class MockOversizedFile:
        async def read(self, n=-1):
            return b"\xff\xd8\xff" + b"\x00" * 200

    with pytest.raises(HTTPException) as exc_info:
        asyncio.run(validate_image_upload(MockOversizedFile(), max_size=100))
    assert exc_info.value.status_code == 413


def test_validate_image_upload_invalid_mime():
    class MockTextFile:
        content_type = "text/plain"

        async def read(self, n=-1):
            return b"Plain text file"

    with pytest.raises(HTTPException) as exc_info:
        asyncio.run(validate_image_upload(MockTextFile()))
    assert exc_info.value.status_code == 400
    assert "unsupported file type" in exc_info.value.detail.lower()


def test_detect_endpoint_rejects_non_image_payload():
    resp = client.post(
        "/detect",
        headers=_edge(),
        files={"file": ("test.txt", io.BytesIO(b"Not an image"), "text/plain")},
    )
    assert resp.status_code == 400


def test_detect_endpoint_rejects_empty_payload():
    resp = client.post(
        "/detect",
        headers=_edge(),
        files={"file": ("test.jpg", io.BytesIO(b""), "image/jpeg")},
    )
    assert resp.status_code == 400


def test_create_profile_rejects_non_image_upload():
    import state
    db = SessionLocal()
    unique_name = f"TestSubject-{uuid.uuid4().hex[:6]}"
    orig_detector = state.ai_models.get("detector")
    try:
        state.ai_models["detector"] = object()
        resp = client.post(
            "/api/profiles",
            headers=_auth(),
            data={"name": unique_name, "role": "visitor"},
            files={"photos": ("script.sh", io.BytesIO(b"#!/bin/bash\necho bad"), "text/x-shellscript")},
        )
        assert resp.status_code == 400
        # Ensure no orphaned profile was committed to the DB
        profile = db.query(Profile).filter(Profile.name == unique_name).first()
        assert profile is None, "Profile should not exist in DB after upload validation failure"
    finally:
        state.ai_models["detector"] = orig_detector
        db.close()


# ---------------------------------------------------------------- R10: Attribute Tracking Tests

def test_detection_ingest_records_mask_and_glasses_attributes():
    db = SessionLocal()
    cam_id = f"cam-{uuid.uuid4().hex[:6]}"
    try:
        db.add(Camera(id=cam_id, name="Attr Test Cam"))
        db.commit()

        event_masked = f"evt_masked_{uuid.uuid4().hex}"
        payload_masked = {
            "camera_id": cam_id,
            "identity": "Unknown",
            "confidence": 0.90,
            "bbox": [10, 10, 60, 60],
            "timestamp": datetime.now(IST).isoformat(),
            "event_id": event_masked,
            "wearing_mask": True,
            "wearing_glasses": False,
        }
        res_m = client.post("/api/detections", headers=_edge(), json=payload_masked)
        assert res_m.status_code == 200, res_m.text
        data_m = res_m.json()
        assert data_m["wearing_mask"] is True
        assert data_m["wearing_glasses"] is False

        # Ingest another with glasses
        event_glasses = f"evt_glasses_{uuid.uuid4().hex}"
        payload_glasses = {
            "camera_id": cam_id,
            "identity": "Unknown",
            "confidence": 0.88,
            "bbox": [15, 15, 65, 65],
            "timestamp": datetime.now(IST).isoformat(),
            "event_id": event_glasses,
            "wearing_mask": False,
            "wearing_glasses": True,
        }
        res_g = client.post("/api/detections", headers=_edge(), json=payload_glasses)
        assert res_g.status_code == 200, res_g.text
        data_g = res_g.json()
        assert data_g["wearing_mask"] is False
        assert data_g["wearing_glasses"] is True

        # Verify DB records
        row_m = db.query(Detection).filter(Detection.event_id == event_masked).first()
        assert row_m is not None
        assert row_m.wearing_mask is True
        assert row_m.wearing_glasses is False

        row_g = db.query(Detection).filter(Detection.event_id == event_glasses).first()
        assert row_g is not None
        assert row_g.wearing_mask is False
        assert row_g.wearing_glasses is True

    finally:
        db.close()


def test_forensic_search_filters_by_mask_and_glasses():
    db = SessionLocal()
    cam_id = f"cam-{uuid.uuid4().hex[:6]}"
    p_id = str(uuid.uuid4())
    dummy_vec = [0.1] * 512
    try:
        db.add(Camera(id=cam_id, name="Forensic Test Cam"))
        profile = Profile(id=p_id, name="Forensic Mask Subject", role=ProfileRole.visitor, embedding_count=1)
        db.add(profile)
        db.add(Embedding(id=str(uuid.uuid4()), profile_id=p_id, vector=dummy_vec))

        det_masked = Detection(
            id=str(uuid.uuid4()),
            event_id=f"evt_f_mask_{uuid.uuid4().hex[:6]}",
            camera_id=cam_id,
            profile_id=p_id,
            timestamp=datetime.now(IST),
            status=DetectionStatus.recognized,
            confidence=0.95,
            bbox="[10, 10, 50, 50]",
            wearing_mask=True,
            wearing_glasses=False,
            embedding_vector=dummy_vec,
        )
        db.add(det_masked)
        db.commit()

        # Search matching mask=True
        resp_mask_match = client.post(
            "/api/forensic/search",
            headers=_auth(),
            data={"profile_id": p_id, "threshold": 0.50, "wearing_mask": True},
        )
        assert resp_mask_match.status_code == 200
        matches_mask = resp_mask_match.json()
        matched_mask_ids = [m["profile_id"] for m in matches_mask]
        assert p_id in matched_mask_ids

        # Search with glasses=True should not match p_id since its detection had wearing_glasses=False
        resp_glasses_mismatch = client.post(
            "/api/forensic/search",
            headers=_auth(),
            data={"profile_id": p_id, "threshold": 0.50, "wearing_glasses": True},
        )
        assert resp_glasses_mismatch.status_code == 200
        matches_glasses = resp_glasses_mismatch.json()
        matched_glasses_ids = [m["profile_id"] for m in matches_glasses]
        assert p_id not in matched_glasses_ids

    finally:
        db.close()
