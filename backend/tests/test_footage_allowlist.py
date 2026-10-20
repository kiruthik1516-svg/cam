"""The footage endpoints may only read inside the configured FOOTAGE_ROOTS."""

import os
import sys
from pathlib import Path

import pytest

backend_dir = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(backend_dir))
sys.path.insert(0, str(backend_dir.parent))

from fastapi.testclient import TestClient

from auth import create_access_token
from main import app

client = TestClient(app)


@pytest.fixture
def headers():
    return {"Authorization": f"Bearer {create_access_token({'sub': 'admin'})}"}


@pytest.fixture
def footage_root(tmp_path, monkeypatch):
    root = tmp_path / "footage"
    (root / "cam1").mkdir(parents=True)
    (root / "cam1" / "clip.mp4").write_bytes(b"")
    (tmp_path / "secret").mkdir()
    (tmp_path / "secret" / "private.txt").write_text("private")
    monkeypatch.setenv("FOOTAGE_ROOTS", str(root))
    return root


def test_browse_lists_only_the_allowed_roots(footage_root, headers):
    data = client.get("/api/video-audit/browse", headers=headers).json()
    assert [Path(item["path"]) for item in data["items"]] == [footage_root.resolve()]


def test_browse_inside_a_root_works_and_stops_at_the_root(footage_root, headers):
    inside = client.get("/api/video-audit/browse", params={"path": str(footage_root)}, headers=headers).json()
    assert inside["parent_path"] is None                      # cannot climb above the root
    assert [item["name"] for item in inside["items"]] == ["cam1"]
    sub = client.get("/api/video-audit/browse", params={"path": str(footage_root / "cam1")}, headers=headers).json()
    assert Path(sub["parent_path"]) == footage_root.resolve()


def test_browse_outside_the_root_is_forbidden(footage_root, headers, tmp_path):
    for target in (str(tmp_path / "secret"), str(tmp_path), str(footage_root / ".." / "secret"), "/etc", "C:\\Windows"):
        response = client.get("/api/video-audit/browse", params={"path": target}, headers=headers)
        assert response.status_code in (403, 404), target
        assert "private.txt" not in response.text


def test_scan_and_ingest_outside_the_root_are_forbidden(footage_root, headers, tmp_path):
    outside = str(tmp_path / "secret")
    assert client.post("/api/video-audit/scan", json={"directory": outside}, headers=headers).status_code == 403
    assert client.post("/api/video-audit/ingest", json={"directory": outside}, headers=headers).status_code == 403
    escape = str(footage_root / ".." / "secret")
    assert client.post("/api/video-audit/scan", json={"directory": escape}, headers=headers).status_code == 403


def test_locate_only_searches_inside_the_roots(footage_root, headers):
    found = client.get("/api/video-audit/locate", params={"name": "cam1"}, headers=headers).json()
    assert found["found"] is True and Path(found["path"]) == (footage_root / "cam1").resolve()
    escaped = client.get("/api/video-audit/locate", params={"name": "../secret"}, headers=headers).json()
    assert escaped["found"] is False


def test_default_root_is_slash_footage(monkeypatch, headers, tmp_path):
    monkeypatch.delenv("FOOTAGE_ROOTS", raising=False)
    response = client.post("/api/video-audit/scan", json={"directory": str(tmp_path)}, headers=headers)
    assert response.status_code == 403
