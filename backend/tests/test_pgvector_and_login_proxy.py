"""Tests for R9 (vector search & duplicate identity detection) and S7 (proxy-aware login scoping)."""

import os
import sys
import uuid
from pathlib import Path

import numpy as np
import pytest

backend_dir = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(backend_dir))
sys.path.insert(0, str(backend_dir.parent))

from fastapi.testclient import TestClient

import auth
from database import get_db
from main import app
from models import Embedding, Profile, ProfileRole

client = TestClient(app)
EDGE_KEY = os.environ.get("EDGE_API_KEY", "test-edge-key-123")


@pytest.fixture(autouse=True)
def _reset_env(monkeypatch):
    client.cookies.clear()
    auth._failed_logins.clear()
    monkeypatch.setenv("EDGE_API_KEY", EDGE_KEY)
    yield
    client.cookies.clear()
    auth._failed_logins.clear()


def test_vector_search_requires_edge_api_key():
    dummy_vec = [0.05] * 512
    assert client.post(
        "/api/internal/vector-search",
        json={"embedding": dummy_vec, "top_k": 5, "threshold": 0.5},
    ).status_code == 422

    assert client.post(
        "/api/internal/vector-search",
        headers={"X-API-Key": "invalid-key"},
        json={"embedding": dummy_vec, "top_k": 5, "threshold": 0.5},
    ).status_code == 403


def test_vector_search_rejects_unrecognized_model():
    dummy_vec = [0.05] * 512
    res = client.post(
        "/api/internal/vector-search",
        headers={"X-API-Key": EDGE_KEY},
        json={
            "embedding": dummy_vec,
            "top_k": 5,
            "threshold": 0.5,
            "embedding_model_version": "unknown_future_model_xyz",
        },
    )
    assert res.status_code == 400
    assert "unsupported" in res.json()["detail"].lower() or "unrecognized" in res.json()["detail"].lower()


def test_vector_search_and_duplicate_detection(monkeypatch):
    db = next(get_db())

    # Create two test profiles with near-identical embeddings
    p1_id = f"test-p1-{uuid.uuid4().hex[:8]}"
    p2_id = f"test-p2-{uuid.uuid4().hex[:8]}"

    # 512-dim normalized base vector
    base_vec = np.random.randn(512).astype(np.float32)
    base_vec /= np.linalg.norm(base_vec)

    # Nearly identical vector for p2 (similarity ~0.98)
    noise = np.random.randn(512).astype(np.float32)
    noise /= np.linalg.norm(noise)
    similar_vec = 0.98 * base_vec + 0.02 * noise
    similar_vec /= np.linalg.norm(similar_vec)

    p1 = Profile(
        id=p1_id,
        name="Test Person Alpha",
        role=ProfileRole.employee,
        embedding_count=1,
    )
    e1 = Embedding(
        id=f"emb-{uuid.uuid4().hex[:8]}",
        profile_id=p1_id,
        vector=base_vec.tolist(),
        model_version="w600k_mbf_v1",
    )
    p2 = Profile(
        id=p2_id,
        name="Test Person Beta",
        role=ProfileRole.employee,
        embedding_count=1,
    )
    e2 = Embedding(
        id=f"emb-{uuid.uuid4().hex[:8]}",
        profile_id=p2_id,
        vector=similar_vec.tolist(),
        model_version="w600k_mbf_v1",
    )

    db.add_all([p1, e1, p2, e2])
    db.commit()

    try:
        # 1. Search with base_vec: should match p1 with high score
        res = client.post(
            "/api/internal/vector-search",
            headers={"X-API-Key": EDGE_KEY},
            json={
                "embedding": base_vec.tolist(),
                "top_k": 3,
                "threshold": 0.70,
                "embedding_model_version": "w600k_mbf_v1",
            },
        )
        assert res.status_code == 200
        data = res.json()
        assert "matches" in data
        assert len(data["matches"]) >= 1
        top_match = data["matches"][0]
        assert top_match["profile_id"] == p1_id
        assert top_match["score"] >= 0.95

        # 2. Check duplicates endpoint: should detect p1 and p2 as duplicate candidate
        dup_res = client.get("/api/analytics/duplicates", headers={"Authorization": "Bearer dev-token"})
        assert dup_res.status_code == 200
        dups = dup_res.json()
        match_pair = [
            d for d in dups
            if (d["profileAId"] == p1_id and d["profileBId"] == p2_id)
            or (d["profileAId"] == p2_id and d["profileBId"] == p1_id)
        ]
        assert len(match_pair) == 1
        assert match_pair[0]["cosineSimilarity"] >= 0.90
    finally:
        # Cleanup
        db.query(Embedding).filter(Embedding.profile_id.in_([p1_id, p2_id])).delete()
        db.query(Profile).filter(Profile.id.in_([p1_id, p2_id])).delete()
        db.commit()


def test_proxy_aware_client_id_and_scoped_lockout(monkeypatch):
    monkeypatch.setenv("ADMIN_PASSWORD", "correct-horse-battery")

    proxy_ip = "198.51.100.42"
    headers = {"X-Forwarded-For": f"{proxy_ip}, 10.0.0.1"}

    # Fail login 5 times for user "attacker" from proxy_ip
    for _ in range(auth.MAX_FAILED_LOGINS):
        r = client.post("/api/auth/login", data={"username": "attacker", "password": "wrong"}, headers=headers)
        assert r.status_code == 401

    # "attacker" from proxy_ip is now locked out (429)
    locked = client.post("/api/auth/login", data={"username": "attacker", "password": "wrong"}, headers=headers)
    assert locked.status_code == 429
    assert "retry-after" in locked.headers

    # BUT another username "admin" from the same proxy_ip is NOT locked out by attacker's attempts!
    good = client.post("/api/auth/login", data={"username": "admin", "password": "correct-horse-battery"}, headers=headers)
    assert good.status_code == 200
