"""Tests for camera topology persistence, route evaluation, and camera zone updates (solves R5, R6, R7)."""

import os
from fastapi.testclient import TestClient

from auth import create_access_token
from database import SessionLocal
from main import app, _sync_topology_from_database
from models import Camera, CameraTopologyEdge
from state import topology_graph, prune_stale_stream_slots, _frame_store, _FrameSlot

client = TestClient(app)


def _auth():
    return {"Authorization": f"Bearer {create_access_token({'sub': 'admin'})}"}


def test_topology_edge_crud_and_persistence():
    db = SessionLocal()
    try:
        # Clean any prior edges for this test
        db.query(CameraTopologyEdge).filter(
            CameraTopologyEdge.from_camera_id.in_(["cam-entrance", "cam-hallway"])
        ).delete()
        db.commit()

        # 1. Verify adding an edge persists to database and in-memory graph
        edge_payload = {
            "from_camera_id": "cam-entrance",
            "to_camera_id": "cam-hallway",
            "min_travel_seconds": 3.0,
            "max_travel_seconds": 45.0,
            "typical_travel_seconds": 12.0,
            "distance_meters": 15.0,
            "transition_probability": 0.95,
            "bidirectional": True,
        }
        res = client.post("/api/topology/edges", json=edge_payload, headers=_auth())
        assert res.status_code == 200, res.text
        data = res.json()
        assert data["from_camera_id"] == "cam-entrance"
        assert data["to_camera_id"] == "cam-hallway"
        assert data["bidirectional"] is True

        # Check database rows
        fwd = db.query(CameraTopologyEdge).filter_by(
            from_camera_id="cam-entrance", to_camera_id="cam-hallway"
        ).first()
        rev = db.query(CameraTopologyEdge).filter_by(
            from_camera_id="cam-hallway", to_camera_id="cam-entrance"
        ).first()
        assert fwd is not None
        assert rev is not None
        assert fwd.min_travel_seconds == 3.0
        assert rev.typical_travel_seconds == 12.0

        # 2. Verify GET /api/topology returns both nodes and edges
        top_res = client.get("/api/topology", headers=_auth())
        assert top_res.status_code == 200
        top_data = top_res.json()
        assert "cam-entrance" in top_data["nodes"]
        assert "cam-hallway" in top_data["nodes"]
        edge_pairs = [(e["from_camera_id"], e["to_camera_id"]) for e in top_data["edges"]]
        assert ("cam-entrance", "cam-hallway") in edge_pairs
        assert ("cam-hallway", "cam-entrance") in edge_pairs

        # 3. Test graph restart simulation: clear in-memory graph and resync from DB
        topology_graph.edges.clear()
        topology_graph.nodes.clear()
        assert len(topology_graph.edges) == 0

        _sync_topology_from_database(db)
        assert topology_graph.is_transition_allowed("cam-entrance", "cam-hallway")
        assert topology_graph.is_transition_allowed("cam-hallway", "cam-entrance")

        # 4. Verify DELETE /api/topology/edges
        del_res = client.delete(
            "/api/topology/edges",
            params={"from_camera_id": "cam-entrance", "to_camera_id": "cam-hallway", "bidirectional": "true"},
            headers=_auth(),
        )
        assert del_res.status_code == 200
        assert del_res.json()["status"] == "deleted"

        # Verify deleted from DB
        remaining = db.query(CameraTopologyEdge).filter_by(
            from_camera_id="cam-entrance", to_camera_id="cam-hallway"
        ).first()
        assert remaining is None

        # Verify deleted from in-memory graph
        assert not topology_graph.is_transition_allowed("cam-entrance", "cam-hallway")
    finally:
        db.close()


def test_camera_display_name_and_zone_update():
    """Verify camera name and zone updates via PUT /api/cameras/{id} (solves R7)."""
    db = SessionLocal()
    try:
        # Create test camera
        cam = db.query(Camera).filter_by(id="door-cam-1").first()
        if not cam:
            cam = Camera(id="door-cam-1", name="door-cam-1", zone="Unassigned")
            db.add(cam)
            db.commit()

        # Update camera display name and zone
        update_payload = {
            "name": "Executive Entrance Door",
            "zone": "North Wing Security Perimeter",
        }
        res = client.put("/api/cameras/door-cam-1", json=update_payload, headers=_auth())
        assert res.status_code == 200, res.text
        updated = res.json()
        assert updated["name"] == "Executive Entrance Door"
        assert updated["zone"] == "North Wing Security Perimeter"

        # Verify database updated
        db.expire_all()
        db_cam = db.query(Camera).filter_by(id="door-cam-1").first()
        assert db_cam.name == "Executive Entrance Door"
        assert db_cam.zone == "North Wing Security Perimeter"

        # Verify topology node updated
        assert topology_graph.nodes["door-cam-1"].name == "Executive Entrance Door"
        assert topology_graph.nodes["door-cam-1"].zone == "North Wing Security Perimeter"
    finally:
        db.close()


def test_prune_stale_stream_slots():
    """Verify idle frame slots are pruned to prevent lingering renamed cameras (solves R6)."""
    import time
    old_time = time.time() - 7200.0  # 2 hours ago
    fresh_time = time.time() - 5.0     # 5 seconds ago

    _frame_store["ghost-cam-old"] = _FrameSlot(last_frame_at=old_time)
    _frame_store["active-cam-fresh"] = _FrameSlot(last_frame_at=fresh_time)

    pruned = prune_stale_stream_slots(max_idle_seconds=3600.0)
    assert pruned >= 1
    assert "ghost-cam-old" not in _frame_store
    assert "active-cam-fresh" in _frame_store
