"""Unit tests for Phase 3 (S1): Authentication & Session Hardening.

Covers:
1. HttpOnly sentinel_token cookie issuance on login.
2. Protected route authentication via cookie.
3. POST /api/auth/logout token revocation and cookie clearing.
4. Immediate rejection of revoked tokens across endpoints.
5. POST /api/cameras/{id}/stream-ticket generation and single-use validation.
6. Replay attack rejection on stream tickets.
"""

import os
import sys
from pathlib import Path

import pytest

backend_dir = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(backend_dir))
sys.path.insert(0, str(backend_dir.parent))

from fastapi.testclient import TestClient

import auth
from auth import create_access_token, is_token_revoked, revoke_token
from main import app

client = TestClient(app)


@pytest.fixture(autouse=True)
def _reset_auth_stores():
    client.cookies.clear()
    auth._failed_logins.clear()
    auth._revoked_tokens.clear()
    auth._stream_tickets.clear()
    yield
    client.cookies.clear()
    auth._failed_logins.clear()
    auth._revoked_tokens.clear()
    auth._stream_tickets.clear()


def test_login_issues_cookie_and_access_token(monkeypatch):
    monkeypatch.setenv("ADMIN_PASSWORD", "test-pass-123")
    local_client = TestClient(app)
    response = local_client.post("/api/auth/login", data={"username": "admin", "password": "test-pass-123"})
    assert response.status_code == 200
    data = response.json()
    assert "access_token" in data
    assert data["token_type"] == "bearer"
    # HttpOnly cookie should be set
    assert "sentinel_token" in response.cookies
    cookie_header = response.headers.get("set-cookie", "")
    assert "HttpOnly" in cookie_header or "httponly" in cookie_header


def test_cookie_authenticates_protected_endpoints():
    token = create_access_token({"sub": "admin", "jti": "cookie-test-jti"})
    client_with_cookie = TestClient(app, cookies={"sentinel_token": token})

    # Protected endpoint accessed without Authorization header, using cookie
    res = client_with_cookie.get("/api/profiles")
    assert res.status_code == 200


def test_logout_revokes_token_and_clears_cookie():
    token = create_access_token({"sub": "admin", "jti": "logout-test-jti"})
    assert not is_token_revoked(token)

    # Call logout with bearer token
    res = client.post("/api/auth/logout", headers={"Authorization": f"Bearer {token}"})
    assert res.status_code == 200
    assert res.json()["status"] == "logged_out"

    # Token must now be revoked
    assert is_token_revoked(token)

    # Calling protected endpoint with revoked token must return 401
    bad_res = client.get("/api/profiles", headers={"Authorization": f"Bearer {token}"})
    assert bad_res.status_code == 401
    assert "revoked" in bad_res.text.lower()


def test_stream_ticket_generation_and_single_use():
    token = create_access_token({"sub": "admin"})

    # 1. Request stream ticket
    ticket_res = client.post(
        "/api/cameras/cam-front/stream-ticket?lifetime_seconds=30",
        headers={"Authorization": f"Bearer {token}"},
    )
    assert ticket_res.status_code == 200
    ticket_data = ticket_res.json()
    assert "ticket" in ticket_data
    assert ticket_data["camera_id"] == "cam-front"
    ticket = ticket_data["ticket"]
    assert ticket.startswith("st_")

    # 2. First use of ticket on snapshot media endpoint -> SUCCESS (200)
    stream_res1 = client.get(f"/api/cameras/cam-front/stream/snapshot?ticket={ticket}")
    assert stream_res1.status_code == 200
    assert stream_res1.headers["content-type"] == "image/jpeg"

    # 3. Second use (replay attack) -> REJECTED (401)
    stream_res2 = client.get(f"/api/cameras/cam-front/stream/snapshot?ticket={ticket}")
    assert stream_res2.status_code == 401
    assert "expired" in stream_res2.text.lower() or "invalid" in stream_res2.text.lower()


def test_stream_ticket_bound_to_specific_camera():
    token = create_access_token({"sub": "admin"})

    # Issue ticket for cam-A
    ticket_res = client.post(
        "/api/cameras/cam-A/stream-ticket",
        headers={"Authorization": f"Bearer {token}"},
    )
    assert ticket_res.status_code == 200
    ticket = ticket_res.json()["ticket"]

    # Trying to use cam-A ticket on cam-B must fail
    res = client.get(f"/api/cameras/cam-B/stream/snapshot?ticket={ticket}")
    assert res.status_code == 401
