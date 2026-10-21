"""Unit tests for Phase 6: Multi-User Access Control (RBAC), Audit Ledger & Edge Device Scoping.

Covers:
1. User creation, role assignment (viewer, operator, admin), and duplicate rejection.
2. DB user authentication and disabled account handling.
3. Role enforcement (viewer vs operator vs admin) on profile creation, deletion, merge, retention purge.
4. Tamper-resistant audit ledger recording and filtering.
5. Scoped edge device API keys (S8) and camera-level authorization.
"""

import os
import sys
import uuid
from datetime import datetime
from pathlib import Path

import pytest
from fastapi.testclient import TestClient

backend_dir = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(backend_dir))
sys.path.insert(0, str(backend_dir.parent))

from auth import create_access_token, hash_password
from config import IST
from database import SessionLocal
from main import app
from models import AuditLog, Camera, Detection, DeviceApiKey, Profile, ProfileRole, User, UserRole

client = TestClient(app)


def _admin_headers():
    token = create_access_token({"sub": "admin", "role": "admin", "user_id": "root-admin"})
    return {"Authorization": f"Bearer {token}"}


def _operator_headers():
    token = create_access_token({"sub": "operator_test", "role": "operator", "user_id": "op-123"})
    return {"Authorization": f"Bearer {token}"}


def _viewer_headers():
    token = create_access_token({"sub": "viewer_test", "role": "viewer", "user_id": "vw-123"})
    return {"Authorization": f"Bearer {token}"}


@pytest.fixture(autouse=True)
def _cleanup_test_data():
    client.cookies.clear()
    yield
    client.cookies.clear()
    db = SessionLocal()
    try:
        db.query(AuditLog).delete()
        db.query(DeviceApiKey).delete()
        db.query(User).filter(User.username.like("test_%")).delete()
        db.commit()
    finally:
        db.close()


# ---------------------------------------------------------------- User Management & RBAC Tests

def test_admin_can_create_and_list_users():
    headers = _admin_headers()
    username = f"test_usr_{uuid.uuid4().hex[:6]}"
    payload = {
        "username": username,
        "password": "Password123!",
        "full_name": "Test Operator",
        "role": "operator",
        "is_active": True,
    }

    create_res = client.post("/api/users", json=payload, headers=headers)
    assert create_res.status_code == 201
    created_user = create_res.json()
    assert created_user["username"] == username
    assert created_user["role"] == "operator"
    assert created_user["full_name"] == "Test Operator"
    assert "hashed_password" not in created_user

    # Duplicate username should be rejected with 409 Conflict
    dup_res = client.post("/api/users", json=payload, headers=headers)
    assert dup_res.status_code == 409

    # List users
    list_res = client.get("/api/users", headers=headers)
    assert list_res.status_code == 200
    usernames = [u["username"] for u in list_res.json()]
    assert username in usernames


def test_non_admin_cannot_manage_users():
    viewer_h = _viewer_headers()
    op_h = _operator_headers()

    # Viewer forbidden
    res = client.get("/api/users", headers=viewer_h)
    assert res.status_code == 403

    # Operator forbidden
    res = client.get("/api/users", headers=op_h)
    assert res.status_code == 403

    # Create forbidden for non-admin
    res = client.post(
        "/api/users",
        json={"username": "hacker", "password": "password123", "role": "admin"},
        headers=viewer_h,
    )
    assert res.status_code == 403


def test_database_user_login_flow():
    db = SessionLocal()
    username = f"test_dbuser_{uuid.uuid4().hex[:6]}"
    user = User(
        id=str(uuid.uuid4()),
        username=username,
        hashed_password=hash_password("SecretPass123"),
        full_name="Database User",
        role=UserRole.operator,
        is_active=True,
        created_at=datetime.now(IST),
    )
    db.add(user)
    db.commit()
    db.close()

    # Successful login
    login_res = client.post(
        "/api/auth/login",
        data={"username": username, "password": "SecretPass123"},
    )
    assert login_res.status_code == 200
    login_data = login_res.json()
    assert login_data["username"] == username
    assert login_data["role"] == "operator"
    assert "access_token" in login_data
    assert "sentinel_token" in login_res.cookies

    # Profile me endpoint
    user_token = login_data["access_token"]
    me_res = client.get("/api/users/me", headers={"Authorization": f"Bearer {user_token}"})
    assert me_res.status_code == 200
    me_data = me_res.json()
    assert me_data["username"] == username
    assert me_data["role"] == "operator"

    # Disabled account check
    db = SessionLocal()
    db_u = db.query(User).filter(User.username == username).first()
    db_u.is_active = False
    db.commit()
    db.close()

    disabled_res = client.post(
        "/api/auth/login",
        data={"username": username, "password": "SecretPass123"},
    )
    assert disabled_res.status_code == 401
    assert "disabled" in disabled_res.json()["detail"].lower()


# ---------------------------------------------------------------- RBAC Endpoint Gating Tests

def test_viewer_is_forbidden_from_profile_mutations():
    viewer_h = _viewer_headers()

    # Viewer rejected on create profile
    res = client.post("/api/profiles", data={"name": "Alice Viewer Blocked"}, headers=viewer_h)
    assert res.status_code == 403

    # Viewer rejected on update profile
    res = client.put("/api/profiles/some-id", json={"name": "New Name"}, headers=viewer_h)
    assert res.status_code == 403

    # Viewer rejected on delete profile
    res = client.delete("/api/profiles/some-id", headers=viewer_h)
    assert res.status_code == 403

    # Viewer rejected on retention purge
    res = client.post("/api/system/retention/purge", json={}, headers=viewer_h)
    assert res.status_code == 403


def test_operator_allowed_mutations_but_forbidden_from_admin_actions():
    operator_h = _operator_headers()
    admin_h = _admin_headers()

    # Operator CAN create profile
    p_name = f"Operator Profile {uuid.uuid4().hex[:4]}"
    res = client.post("/api/profiles", data={"name": p_name, "role": "visitor"}, headers=operator_h)
    assert res.status_code == 200
    profile_id = res.json()["id"]

    # Operator CAN update profile
    res = client.put(f"/api/profiles/{profile_id}", json={"name": f"{p_name} Updated"}, headers=operator_h)
    assert res.status_code == 200

    # Operator is FORBIDDEN from deleting profile (admin only)
    del_res = client.delete(f"/api/profiles/{profile_id}", headers=operator_h)
    assert del_res.status_code == 403

    # Operator is FORBIDDEN from triggering retention purge (admin only)
    purge_res = client.post("/api/system/retention/purge", json={}, headers=operator_h)
    assert purge_res.status_code == 403

    # Admin CAN delete profile
    admin_del_res = client.delete(f"/api/profiles/{profile_id}", headers=admin_h)
    assert admin_del_res.status_code == 200
    assert admin_del_res.json()["deleted"] is True


# ---------------------------------------------------------------- Audit Ledger Tests

def test_audit_logs_record_and_filter_sensitive_actions():
    admin_h = _admin_headers()

    # Trigger action: create profile
    p_name = f"Audit Subject {uuid.uuid4().hex[:4]}"
    client.post("/api/profiles", data={"name": p_name, "role": "vip"}, headers=admin_h)

    # Trigger action: retention purge
    client.post("/api/system/retention/purge", json={"retention_days": 90}, headers=admin_h)

    # Fetch audit logs (admin only)
    logs_res = client.get("/api/audit-logs", headers=admin_h)
    assert logs_res.status_code == 200
    logs = logs_res.json()
    actions = [l["action"] for l in logs]
    assert "profile.create" in actions
    assert "retention.purge" in actions

    # Filter audit logs by action
    filtered_res = client.get("/api/audit-logs?action=retention.purge", headers=admin_h)
    assert filtered_res.status_code == 200
    filtered_logs = filtered_res.json()
    assert len(filtered_logs) >= 1
    assert all(l["action"] == "retention.purge" for l in filtered_logs)


# ---------------------------------------------------------------- Scoped Edge Device Keys (S8)

def test_scoped_device_api_key_lifecycle_and_camera_scoping():
    admin_h = _admin_headers()

    # Ensure test cameras exist in DB
    db = SessionLocal()
    for cid in ("cam-gate-a", "cam-vault-x"):
        if not db.query(Camera).filter(Camera.id == cid).first():
            db.add(Camera(id=cid, name=cid.replace("-", " ").title()))
    db.commit()
    db.close()

    # 1. Admin generates a scoped edge key for "cam-gate-a" only
    key_payload = {
        "name": "Gate Camera Node",
        "allowed_cameras": ["cam-gate-a"],
    }
    create_res = client.post("/api/edge-keys", json=key_payload, headers=admin_h)
    assert create_res.status_code == 201
    key_data = create_res.json()
    key_id = key_data["id"]
    secret_key = key_data["key"]
    assert secret_key.startswith("sk_edge_")
    assert key_data["key_prefix"].startswith("sk_edge_")

    # 2. Edge node submits detection for allowed camera "cam-gate-a" -> SUCCESS
    allowed_det = {
        "camera_id": "cam-gate-a",
        "identity": "unknown",
        "confidence": 0.85,
        "bbox": [10, 10, 100, 100],
        "event_id": f"evt_{uuid.uuid4().hex}",
        "timestamp": datetime.now(IST).isoformat(),
    }
    allowed_res = client.post(
        "/api/detections",
        json=allowed_det,
        headers={"X-API-Key": secret_key},
    )
    assert allowed_res.status_code == 200

    # 3. Edge node attempts to submit detection for unauthorized "cam-vault-x" -> 403 FORBIDDEN
    forbidden_det = {
        "camera_id": "cam-vault-x",
        "identity": "unknown",
        "confidence": 0.90,
        "bbox": [10, 10, 100, 100],
        "event_id": f"evt_{uuid.uuid4().hex}",
        "timestamp": datetime.now(IST).isoformat(),
    }
    forbidden_res = client.post(
        "/api/detections",
        json=forbidden_det,
        headers={"X-API-Key": secret_key},
    )
    assert forbidden_res.status_code == 403
    assert "not authorized" in forbidden_res.json()["detail"].lower()

    # 4. Admin revokes the edge key
    revoke_res = client.delete(f"/api/edge-keys/{key_id}", headers=admin_h)
    assert revoke_res.status_code == 200
    assert revoke_res.json()["revoked"] is True

    # 5. Revoked key is rejected immediately on previously authorized camera
    rejected_res = client.post(
        "/api/detections",
        json=allowed_det,
        headers={"X-API-Key": secret_key},
    )
    assert rejected_res.status_code in (401, 403)
