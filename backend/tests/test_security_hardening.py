"""Tests for authentication, edge-key scoping and CORS hardening."""

import os
import sys
from pathlib import Path

import pytest

backend_dir = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(backend_dir))
sys.path.insert(0, str(backend_dir.parent))

from fastapi.testclient import TestClient
from starlette.websockets import WebSocketDisconnect

import auth
from auth import create_access_token, load_secret_key
from main import app

client = TestClient(app)
EDGE_KEY = os.environ["EDGE_API_KEY"]


def _edge():
    return {"X-API-Key": EDGE_KEY}


def _jwt():
    return create_access_token({"sub": "admin"})


@pytest.fixture(autouse=True)
def _reset_login_limiter():
    client.cookies.clear()
    auth._failed_logins.clear()
    yield
    client.cookies.clear()
    auth._failed_logins.clear()


# ---------------------------------------------------------------- edge key

def test_edge_routes_refuse_when_no_key_is_configured(monkeypatch):
    monkeypatch.delenv("EDGE_API_KEY", raising=False)
    response = client.post("/api/internal/notify_update", headers={"X-API-Key": "anything"})
    assert response.status_code == 503


def test_placeholder_edge_key_is_never_accepted(monkeypatch):
    monkeypatch.setenv("EDGE_API_KEY", "default-dev-key")
    response = client.post("/api/internal/notify_update", headers={"X-API-Key": "default-dev-key"})
    assert response.status_code == 503


def test_websocket_rejects_the_old_default_key(monkeypatch):
    monkeypatch.delenv("EDGE_API_KEY", raising=False)
    with pytest.raises(WebSocketDisconnect) as exc_info:
        with client.websocket_connect("/ws/alerts?api_key=default-dev-key"):
            pass
    assert exc_info.value.code == 4001


def test_video_push_websocket_rejects_a_wrong_key():
    with pytest.raises(WebSocketDisconnect) as exc_info:
        with client.websocket_connect("/ws/video/push/some-cam?api_key=wrong"):
            pass
    assert exc_info.value.code == 4003


def test_edge_key_works_on_ingest_routes_only():
    # Dashboard routes stay closed to the edge key, in a header or in the query string.
    assert client.get("/api/profiles", headers=_edge()).status_code == 401
    assert client.get("/api/kpis", headers=_edge()).status_code == 401
    assert client.get(f"/api/kpis?api_key={EDGE_KEY}").status_code == 401
    # An ingestion route passes authentication (the empty body then fails validation, not auth).
    assert client.post("/api/detections", json={}, headers=_edge()).status_code == 422


def test_wrong_edge_key_is_rejected_on_ingest_routes():
    assert client.post("/api/detections", json={}, headers={"X-API-Key": "wrong"}).status_code == 401


# ---------------------------------------------------------------- JWT in the query string

def test_query_token_is_accepted_for_media_routes_only():
    token = _jwt()
    assert client.get(f"/api/profiles?token={token}").status_code == 401
    assert client.get("/api/cameras/test-cam/stream/snapshot").status_code == 401
    response = client.get(f"/api/cameras/test-cam/stream/snapshot?token={token}")
    assert response.status_code == 200
    assert response.headers["content-type"] == "image/jpeg"


# ---------------------------------------------------------------- login

def test_login_is_refused_when_no_admin_password_is_configured(monkeypatch):
    monkeypatch.delenv("ADMIN_PASSWORD", raising=False)
    response = client.post("/api/auth/login", data={"username": "admin", "password": "admin"})
    assert response.status_code == 503


def test_login_accepts_only_the_configured_password(monkeypatch):
    monkeypatch.setenv("ADMIN_PASSWORD", "correct-horse-battery")
    assert client.post("/api/auth/login", data={"username": "admin", "password": "admin"}).status_code == 401
    ok = client.post("/api/auth/login", data={"username": "admin", "password": "correct-horse-battery"})
    assert ok.status_code == 200 and ok.json()["token_type"] == "bearer"


def test_repeated_failed_logins_are_throttled(monkeypatch):
    monkeypatch.setenv("ADMIN_PASSWORD", "correct-horse-battery")
    for _ in range(auth.MAX_FAILED_LOGINS):
        assert client.post("/api/auth/login", data={"username": "admin", "password": "nope"}).status_code == 401
    locked = client.post("/api/auth/login", data={"username": "admin", "password": "correct-horse-battery"})
    assert locked.status_code == 429
    assert "retry-after" in locked.headers


def test_successful_login_clears_earlier_failures(monkeypatch):
    monkeypatch.setenv("ADMIN_PASSWORD", "correct-horse-battery")
    for _ in range(auth.MAX_FAILED_LOGINS - 1):
        client.post("/api/auth/login", data={"username": "admin", "password": "nope"})
    assert client.post("/api/auth/login", data={"username": "admin", "password": "correct-horse-battery"}).status_code == 200
    assert client.post("/api/auth/login", data={"username": "admin", "password": "nope"}).status_code == 401


# ---------------------------------------------------------------- JWT secret

def test_load_secret_key_rules():
    assert load_secret_key({"SECRET_KEY": "abc"}) == "abc"
    assert load_secret_key({"JWT_SECRET": "xyz", "SECRET_KEY": "abc"}) == "xyz"
    with pytest.raises(RuntimeError):
        load_secret_key({"ENVIRONMENT": "production"})
    with pytest.raises(RuntimeError):  # the old public default is not accepted as a real secret
        load_secret_key({"ENVIRONMENT": "production", "SECRET_KEY": "super-secret-key-change-in-production"})
    first, second = load_secret_key({}), load_secret_key({})
    assert first != second and len(first) >= 32  # random per process, never a fixed string


# ---------------------------------------------------------------- CORS

def test_cors_headers_are_sent_only_to_allowed_origins_even_on_401():
    allowed = client.get("/api/kpis", headers={"Origin": "http://localhost:3000"})
    assert allowed.status_code == 401
    assert allowed.headers.get("access-control-allow-origin") == "http://localhost:3000"
    blocked = client.get("/api/kpis", headers={"Origin": "https://evil.example"})
    assert blocked.status_code == 401
    assert "access-control-allow-origin" not in blocked.headers


def test_wildcard_origin_matches_exactly_one_label():
    def preflight(origin):
        return client.options(
            "/health", headers={"Origin": origin, "Access-Control-Request-Method": "GET"}
        )
    one = preflight("https://my-app.vercel.app")
    assert one.headers.get("access-control-allow-origin") == "https://my-app.vercel.app"
    two = preflight("https://attacker.my-app.vercel.app")
    assert "access-control-allow-origin" not in two.headers
    assert "access-control-allow-origin" not in preflight("https://vercel.app.evil.example").headers
