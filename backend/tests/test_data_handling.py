"""Tests for safe file loading, camera URL masking, profile merge/delete guards and the gallery version."""

import os
import sys
import uuid
from datetime import datetime
from pathlib import Path

import numpy as np
import pytest

backend_dir = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(backend_dir))
sys.path.insert(0, str(backend_dir.parent))

from fastapi.testclient import TestClient

from auth import create_access_token
from config import IST
from database import SessionLocal
from facial_recognition.safeio import load_npz
from main import app
from models import (
    Camera, CameraTransition, DataSource, Detection, DetectionStatus, Profile,
)
from utils import compute_gallery_version

client = TestClient(app)


def _auth():
    return {"Authorization": f"Bearer {create_access_token({'sub': 'admin'})}"}


# ---------------------------------------------------------------- safe .npz loading

def test_npz_with_plain_arrays_loads_without_pickle(tmp_path):
    path = tmp_path / "gallery.npz"
    np.savez(path, labels=np.array(["alice", "bob"], dtype=str), embeddings=np.zeros((2, 512), dtype=np.float32))
    data = load_npz(path)
    assert "labels" in data and data["labels"].tolist() == ["alice", "bob"]
    with load_npz(path) as again:
        assert sorted(again.files) == ["embeddings", "labels"]


def test_npz_with_pickled_arrays_is_refused_by_default(tmp_path, monkeypatch):
    monkeypatch.delenv("ALLOW_PICKLE_NPZ", raising=False)
    path = tmp_path / "legacy.npz"
    np.savez(path, labels=np.array(["alice"], dtype=object))
    with pytest.raises(ValueError):
        load_npz(path)


def test_pickled_npz_can_be_loaded_only_with_explicit_opt_in(tmp_path, monkeypatch):
    path = tmp_path / "legacy.npz"
    np.savez(path, labels=np.array(["alice"], dtype=object))
    monkeypatch.setenv("ALLOW_PICKLE_NPZ", "1")
    assert load_npz(path)["labels"].tolist() == ["alice"]


# ---------------------------------------------------------------- camera URL masking

def test_camera_credentials_are_not_returned_by_the_api():
    camera_id = f"cred-cam-{uuid.uuid4().hex[:6]}"
    db = SessionLocal()
    try:
        db.add(Camera(id=camera_id, name=camera_id, rtsp_url="rtsp://viewer:topsecret@10.0.0.9:554/stream1"))
        db.commit()
    finally:
        db.close()
    cameras = {c["id"]: c for c in client.get("/api/cameras", headers=_auth()).json()}
    assert "topsecret" not in str(cameras[camera_id]) and "viewer" not in cameras[camera_id]["rtsp_url"]
    assert cameras[camera_id]["rtsp_url"] == "rtsp://***@10.0.0.9:554/stream1"


# ---------------------------------------------------------------- profile merge / delete

def _make_profile(db, name, count=0):
    profile = Profile(id=str(uuid.uuid4()), name=name, embedding_count=count)
    db.add(profile)
    db.flush()
    return profile


def test_merge_rejects_a_profile_merged_with_itself():
    db = SessionLocal()
    try:
        profile = _make_profile(db, "Solo")
        db.commit()
        pid = profile.id
    finally:
        db.close()
    response = client.post("/api/profiles/merge", json={"profileAId": pid, "profileBId": pid}, headers=_auth())
    assert response.status_code == 400
    assert client.get(f"/api/profiles/{pid}", headers=_auth()).status_code == 200   # still exists


def test_merge_rejects_a_keep_id_that_is_not_one_of_the_two():
    db = SessionLocal()
    try:
        a, b, c = _make_profile(db, "A"), _make_profile(db, "B"), _make_profile(db, "C")
        db.commit()
        ids = (a.id, b.id, c.id)
    finally:
        db.close()
    response = client.post(
        "/api/profiles/merge",
        json={"profileAId": ids[0], "profileBId": ids[1], "keepProfileId": ids[2]},
        headers=_auth(),
    )
    assert response.status_code == 400


def test_merge_moves_transitions_and_recounts_vectors():
    camera_a, camera_b = f"mc-{uuid.uuid4().hex[:5]}", f"mc-{uuid.uuid4().hex[:5]}"
    db = SessionLocal()
    try:
        db.add_all([Camera(id=camera_a, name=camera_a), Camera(id=camera_b, name=camera_b)])
        keep, drop = _make_profile(db, "Keep", count=3), _make_profile(db, "Drop", count=2)
        db.add(CameraTransition(
            id=str(uuid.uuid4()), profile_id=drop.id, from_camera_id=camera_a, to_camera_id=camera_b,
            detected_at=datetime.now(IST), travel_seconds=5.0, confidence=0.9, transition_type="CONFIRMED",
        ))
        db.commit()
        keep_id, drop_id = keep.id, drop.id
    finally:
        db.close()

    response = client.post(
        "/api/profiles/merge",
        json={"profileAId": keep_id, "profileBId": drop_id, "keepProfileId": keep_id},
        headers=_auth(),
    )
    assert response.status_code == 200 and response.json()["deletedProfileId"] == drop_id

    db = SessionLocal()
    try:
        assert db.query(Profile).filter(Profile.id == drop_id).first() is None
        assert db.query(CameraTransition).filter(CameraTransition.profile_id == keep_id).count() == 1
        # no vectors are actually attached, so the stored count is corrected from the old "3 + 2" figure
        assert db.query(Profile).filter(Profile.id == keep_id).first().embedding_count == 0
    finally:
        db.close()


def _profile_with_detection():
    camera_id = f"dc-{uuid.uuid4().hex[:5]}"
    db = SessionLocal()
    try:
        db.add(Camera(id=camera_id, name=camera_id))
        profile = _make_profile(db, "Erase Me")
        detection = Detection(
            id=str(uuid.uuid4()), camera_id=camera_id, profile_id=profile.id, timestamp=datetime.now(IST),
            source=DataSource.live, status=DetectionStatus.recognized, face_image="BASE64FACE",
        )
        db.add(detection)
        db.commit()
        return profile.id, detection.id
    finally:
        db.close()


def test_delete_keeps_history_by_default():
    profile_id, detection_id = _profile_with_detection()
    assert client.delete(f"/api/profiles/{profile_id}", headers=_auth()).status_code == 200
    db = SessionLocal()
    try:
        detection = db.query(Detection).filter(Detection.id == detection_id).first()
        assert detection.profile_id is None and detection.face_image == "BASE64FACE"
    finally:
        db.close()


def test_delete_with_erase_biometrics_removes_the_stored_face():
    profile_id, detection_id = _profile_with_detection()
    response = client.delete(f"/api/profiles/{profile_id}?erase_biometrics=true", headers=_auth())
    assert response.status_code == 200
    db = SessionLocal()
    try:
        detection = db.query(Detection).filter(Detection.id == detection_id).first()
        assert detection.profile_id is None
        assert detection.face_image is None and detection.embedding_vector is None
    finally:
        db.close()


# ---------------------------------------------------------------- gallery version

def test_gallery_version_changes_when_one_vector_replaces_another():
    assert compute_gallery_version([]) == 1
    before = compute_gallery_version(["e1", "e2", "e3"])
    replaced = compute_gallery_version(["e1", "e2", "e4"])        # same number of vectors, different content
    assert before != replaced
    assert before == compute_gallery_version(["e3", "e2", "e1"])  # order does not matter
    assert 1 <= before <= 2_000_000_000
