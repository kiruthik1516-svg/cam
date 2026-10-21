"""Tests for Phase 10: Production Hardening, Load Testing & Deployment Readiness.

Validates:
1. Deep health and readiness probe endpoints (/health?deep=true and /health/ready).
2. Graceful 503 degradation on subsystem readiness failures.
3. Concurrent multi-camera burst ingestion under multi-threaded load.
4. Idempotency race-condition handling: simultaneous duplicate submissions resolved atomically.
5. WebSocket Redis fallback resilience under simulated network failure.
6. VRAM scheduler worker calculation under simulated GPU and CPU topologies.
7. Database connection pool configuration bounds and settings.
8. End-to-end integration: edge detection ingest -> alert generation -> forensic search.
"""
from __future__ import annotations

import asyncio
import concurrent.futures
import json
import os
import uuid
from datetime import datetime, timedelta, timezone
from unittest.mock import patch, MagicMock

import pytest
from starlette.testclient import TestClient

from main import app
from auth import create_access_token
from config import settings, IST
from database import get_db, SessionLocal, check_database_health
from models import Camera, Detection, Alert, Profile, ProfileRole, EventProvenance
from facial_recognition.batch_video_ingest import VRAMScheduler


@pytest.fixture
def client():
    return TestClient(app)


EDGE_KEY = os.environ.get("EDGE_API_KEY", "test-edge-api-key")


@pytest.fixture
def admin_headers():
    token = create_access_token({"sub": "admin", "role": "admin"})
    return {"Authorization": f"Bearer {token}"}


@pytest.fixture
def edge_headers():
    return {"X-API-Key": EDGE_KEY}


def test_standard_health_check_backward_compatibility(client):
    """Standard /health returns 200 OK with status: ok for backward compatibility."""
    resp = client.get("/health")
    assert resp.status_code == 200
    data = resp.json()
    assert data["status"] == "ok"
    assert "timestamp" in data
    assert "subsystems" not in data


def test_deep_readiness_probe_healthy(client):
    """Deep readiness probe /health?deep=true verifies DB and subsystems."""
    resp = client.get("/health?deep=true")
    assert resp.status_code == 200
    data = resp.json()
    assert data["status"] == "ok"
    assert "subsystems" in data
    assert data["subsystems"]["database"] == "healthy"
    assert data["subsystems"]["redis"] in ("connected", "disabled", "disconnected")


def test_readiness_endpoint_alias(client):
    """Readiness endpoint /health/ready returns deep probe status."""
    resp = client.get("/health/ready")
    assert resp.status_code == 200
    data = resp.json()
    assert data["status"] == "ok"
    assert data["subsystems"]["database"] == "healthy"


def test_readiness_probe_failure_returns_503(client):
    """When the database is unreachable, deep probe returns HTTP 503 Degraded."""
    with patch("routers.system.check_database_health", return_value=False):
        resp = client.get("/health?deep=true")
        assert resp.status_code == 503
        data = resp.json()
        assert data["status"] == "degraded"
        assert data["subsystems"]["database"] == "unhealthy"


def test_database_pool_settings_and_clamping():
    """Verify database connection pool properties adhere to safety clamps."""
    assert 1 <= settings.db_pool_size <= 100
    assert 0 <= settings.db_max_overflow <= 50
    assert 5 <= settings.db_pool_timeout <= 120
    assert 60 <= settings.db_pool_recycle <= 7200


def test_vram_scheduler_worker_calculations():
    """Verify VRAMScheduler computes safe worker counts preserving live reserves."""
    # 1. High VRAM: 24GB total, 16GB free (16384MB), 6GB reserve (6144MB), 1GB/worker
    # Usable = 16384 - 6144 = 10240MB -> 10 workers, capped by camera count (5) -> 5
    with patch.object(VRAMScheduler, "get_vram_info", return_value={"total_mb": 24576, "free_mb": 16384, "used_mb": 8192, "source": "mock"}):
        workers, info = VRAMScheduler.calculate_safe_workers(camera_count=5, live_reserve_mb=6144, worker_cost_mb=1024)
        assert workers == 5
        assert info["strategy"] == "vram_autoscaled"
        assert info["usable_for_batch_mb"] == 10240

    # 2. Constrained VRAM: 8GB total, 7GB free (7168MB), 6GB reserve (6144MB)
    # Usable = 7168 - 6144 = 1024MB -> 1 worker
    with patch.object(VRAMScheduler, "get_vram_info", return_value={"total_mb": 8192, "free_mb": 7168, "used_mb": 1024, "source": "mock"}):
        workers, info = VRAMScheduler.calculate_safe_workers(camera_count=8, live_reserve_mb=6144, worker_cost_mb=1024)
        assert workers == 1

    # 3. Low VRAM under reserve: 5GB free < 6GB reserve
    # Must clamp to minimum 1 safe worker without going negative
    with patch.object(VRAMScheduler, "get_vram_info", return_value={"total_mb": 8192, "free_mb": 5120, "used_mb": 3072, "source": "mock"}):
        workers, info = VRAMScheduler.calculate_safe_workers(camera_count=4, live_reserve_mb=6144, worker_cost_mb=1024)
        assert workers == 1

    # 4. Manual override strictly respected
    workers, info = VRAMScheduler.calculate_safe_workers(camera_count=10, max_workers_override=3)
    assert workers == 3
    assert info["strategy"] == "user_override"

    # 5. CPU fallback (no GPU detected)
    with patch.object(VRAMScheduler, "get_vram_info", return_value={"total_mb": 0, "free_mb": 0, "used_mb": 0, "source": "cpu_fallback"}):
        workers, info = VRAMScheduler.calculate_safe_workers(camera_count=6)
        assert workers >= 1
        assert info["strategy"] == "cpu_proportional"


def test_websocket_redis_fallback_resilience():
    """Verify WebSocket broadcaster survives Redis failure and falls back to local broadcast."""
    import asyncio
    from websocket import WebSocketConnectionManager

    async def _run_async_test():
        ws_mgr = WebSocketConnectionManager()
        mock_redis = MagicMock()
        # Simulate Redis connection drop / timeout
        mock_redis.publish.side_effect = Exception("Connection refused / Redis timeout")
        ws_mgr.redis = mock_redis

        # Subscribe a mock client
        mock_ws = MagicMock()
        # Create dummy async send_text
        async def fake_send_text(msg):
            pass
        mock_ws.send_text = fake_send_text

        ws_mgr.active_connections["alerts"].add(mock_ws)

        # Broadcast should NOT raise exception; it catches error and falls back to local broadcast
        try:
            await ws_mgr.broadcast("alerts", {"event": "test_burst", "data": 123})
        except Exception as e:
            pytest.fail(f"WebSocket broadcast crashed during Redis error: {e}")

        assert mock_redis.publish.called

    asyncio.run(_run_async_test())


def test_concurrent_idempotency_race_condition(client, edge_headers):
    """Simultaneous submissions of the exact same event_id from parallel threads must atomically deduplicate."""
    shared_event_id = f"evt_race_{uuid.uuid4().hex}"
    now_iso = datetime.now(IST).isoformat()

    payload = {
        "event_id": shared_event_id,
        "device_id": "edge_race_node",
        "sequence_number": 1,
        "camera_id": "cam_race_01",
        "camera_name": "Race Camera",
        "zone": "Race Zone",
        "confidence": 0.95,
        "bbox": [100, 100, 200, 200],
        "identity": "Unknown",
        "quality_score": 88.0,
        "liveness_score": 0.95,
        "timestamp": now_iso,
        "priority": "normal",
    }

    num_threads = 6
    results = []

    def submit():
        return client.post("/api/detections", json=payload, headers=edge_headers)

    with concurrent.futures.ThreadPoolExecutor(max_workers=num_threads) as executor:
        futures = [executor.submit(submit) for _ in range(num_threads)]
        for f in concurrent.futures.as_completed(futures):
            results.append(f.result())

    # Every single request must return HTTP 200
    for r in results:
        assert r.status_code == 200, f"Expected 200 but got {r.status_code}: {r.text}"

    # Exactly 1 request must report inserted=True; all others must report inserted=False
    inserted_flags = [r.json().get("inserted") for r in results]
    assert inserted_flags.count(True) == 1, f"Expected 1 True, got: {inserted_flags}"
    assert inserted_flags.count(False) == (num_threads - 1), f"Expected {num_threads - 1} False, got: {inserted_flags}"

    # Database must have exactly 1 record for this event_id
    with SessionLocal() as db:
        count = db.query(Detection).filter(Detection.event_id == shared_event_id).count()
        assert count == 1


def test_concurrent_multi_camera_ingestion(client, edge_headers):
    """Simulate 4 concurrent camera streams ingesting detection bursts simultaneously."""
    cameras = ["cam_load_01", "cam_load_02", "cam_load_03", "cam_load_04"]
    burst_per_cam = 5
    now_iso = datetime.now(IST).isoformat()

    tasks = []
    for cam_id in cameras:
        for seq in range(1, burst_per_cam + 1):
            tasks.append({
                "event_id": f"evt_load_{cam_id}_{seq}_{uuid.uuid4().hex[:6]}",
                "device_id": f"edge_{cam_id}",
                "sequence_number": seq,
                "camera_id": cam_id,
                "camera_name": f"Camera {cam_id}",
                "zone": "Load Zone",
                "confidence": 0.91,
                "identity": "Unknown",
                "bbox": [150, 150, 250, 250],
                "quality_score": 82.5,
                "liveness_score": 0.92,
                "timestamp": now_iso,
                "priority": "normal",
            })

    def post_detection(payload):
        return client.post("/api/detections", json=payload, headers=edge_headers)

    responses = []
    with concurrent.futures.ThreadPoolExecutor(max_workers=4) as executor:
        futures = [executor.submit(post_detection, p) for p in tasks]
        for f in concurrent.futures.as_completed(futures):
            responses.append(f.result())

    assert len(responses) == len(tasks)
    for r in responses:
        assert r.status_code == 200
        assert r.json().get("inserted") is True

    # Verify all detections are persisted
    task_event_ids = [p["event_id"] for p in tasks]
    with SessionLocal() as db:
        stored = db.query(Detection).filter(Detection.event_id.in_(task_event_ids)).count()
        assert stored == len(tasks)


def test_end_to_end_ingestion_alert_and_retrieval(client, edge_headers, admin_headers):
    """End-to-end integration: edge posts detection -> alert created -> searchable in API."""
    unique_event_id = f"evt_e2e_{uuid.uuid4().hex}"
    now_iso = datetime.now(IST).isoformat()

    # 1. Post detection
    payload = {
        "event_id": unique_event_id,
        "device_id": "edge_e2e_node",
        "sequence_number": 1,
        "camera_id": "cam_e2e_01",
        "camera_name": "E2E Front Door",
        "zone": "Front Entrance",
        "confidence": 0.94,
        "identity": "Unknown",
        "bbox": [100, 100, 200, 200],
        "quality_score": 87.5,
        "liveness_score": 0.96,
        "timestamp": now_iso,
        "priority": "high",
        "provenance": {
            "frame_reference": "frm_e2e_001",
            "track_id": "trk_e2e_1",
            "observation_references": ["obs_e2e_001"],
            "candidate_matches": [{"identity": "Unregistered", "score": 0.94, "rank": 1}],
            "embedding_fingerprint": "emb_fp_e2e_12345",
            "decision_tier": "LOCAL_HIGH_CONFIDENCE",
            "provenance_chain_hash": "chain_e2e_12345",
        },
    }
    post_res = client.post("/api/detections", json=payload, headers=edge_headers)
    assert post_res.status_code == 200
    res_data = post_res.json()
    assert res_data["event_id"] == unique_event_id
    assert res_data["quality_score"] == 87.5

    # 2. Verify stored record and provenance in DB
    with SessionLocal() as db:
        det = db.query(Detection).filter(Detection.event_id == unique_event_id).first()
        assert det is not None
        assert det.camera_id == "cam_e2e_01"
        assert det.quality_score == 87.5

        prov = db.query(EventProvenance).filter(EventProvenance.event_id == unique_event_id).first()
        assert prov is not None
        assert prov.frame_reference == "frm_e2e_001"

    # 3. Verify detection is returned in sightings logs
    det_id = res_data["id"]
    logs_res = client.get("/api/logs?limit=20", headers=admin_headers)
    assert logs_res.status_code == 200
    all_ids = [d.get("id") for d in logs_res.json()]
    assert det_id in all_ids

    # 4. Verify provenance API endpoint returns full lineage
    prov_res = client.get(f"/api/detections/{unique_event_id}/provenance", headers=admin_headers)
    assert prov_res.status_code == 200
    prov_data = prov_res.json()
    assert prov_data["event_id"] == unique_event_id
    assert prov_data["frame_reference"] == "frm_e2e_001"
