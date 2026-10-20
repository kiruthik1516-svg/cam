#!/usr/bin/env python
"""End-to-end smoke test for a running Sentinel stack (standard library only).

Usage (stack already running):
    ADMIN_PASSWORD=... EDGE_API_KEY=... python scripts/smoke_test.py

Environment:
    BASE_URL       backend URL            (default http://127.0.0.1:1223)
    DASHBOARD_URL  dashboard URL, optional (default http://127.0.0.1:3000; set empty to skip)
    ADMIN_PASSWORD, EDGE_API_KEY           required
Exits non-zero if any check fails.
Note: it registers one throw-away camera named smoke-<timestamp>; against a long-lived database you can delete that row.
"""
from __future__ import annotations

import json
import os
import sys
import time
import urllib.error
import urllib.parse
import urllib.request

BASE = os.environ.get("BASE_URL", "http://127.0.0.1:1223").rstrip("/")
DASHBOARD = os.environ.get("DASHBOARD_URL", "http://127.0.0.1:3000").rstrip("/")
ADMIN_PASSWORD = os.environ.get("ADMIN_PASSWORD", "")
EDGE_API_KEY = os.environ.get("EDGE_API_KEY", "")

failures = []


def call(url, method="GET", headers=None, data=None, timeout=20):
    """Return (status, body_bytes); HTTP errors are returned, not raised."""
    request = urllib.request.Request(url, method=method, headers=headers or {}, data=data)
    try:
        with urllib.request.urlopen(request, timeout=timeout) as response:
            return response.status, response.read()
    except urllib.error.HTTPError as error:
        return error.code, error.read()


def check(name, ok, detail=""):
    print(f"[{'PASS' if ok else 'FAIL'}] {name}{(' - ' + detail) if detail and not ok else ''}")
    if not ok:
        failures.append(name)


def wait_for(url, seconds=120):
    deadline = time.time() + seconds
    while time.time() < deadline:
        try:
            if call(url, timeout=5)[0] == 200:
                return True
        except OSError:
            pass
        time.sleep(3)
    return False


def main() -> int:
    if not ADMIN_PASSWORD or not EDGE_API_KEY:
        print("ADMIN_PASSWORD and EDGE_API_KEY must be set in the environment.")
        return 2

    check("backend /health", wait_for(f"{BASE}/health"))

    login = urllib.parse.urlencode({"username": "admin", "password": ADMIN_PASSWORD}).encode()
    status, body = call(f"{BASE}/api/auth/login", "POST", {"Content-Type": "application/x-www-form-urlencoded"}, login)
    check("login with the configured password", status == 200, f"HTTP {status}")
    token = json.loads(body)["access_token"] if status == 200 else ""
    bearer = {"Authorization": f"Bearer {token}"}

    bad = urllib.parse.urlencode({"username": "admin", "password": "definitely-not-the-password"}).encode()
    status, _ = call(f"{BASE}/api/auth/login", "POST", {"Content-Type": "application/x-www-form-urlencoded"}, bad)
    check("login with a wrong password is refused", status == 401, f"HTTP {status}")

    check("dashboard API needs a login", call(f"{BASE}/api/kpis")[0] == 401)
    status, body = call(f"{BASE}/api/kpis?source=live", headers=bearer)
    kpis = json.loads(body) if status == 200 else {}
    check("KPIs with a login", status == 200 and "system_health" in kpis, f"HTTP {status}")

    check("edge key does not open dashboard routes", call(f"{BASE}/api/kpis", headers={"X-API-Key": EDGE_API_KEY})[0] == 401)
    check("old default edge key is refused", call(f"{BASE}/api/internal/notify_update", "POST", {"X-API-Key": "default-dev-key"})[0] in (403, 503))
    check("edge key works on an edge route", call(f"{BASE}/api/internal/notify_update", "POST", {"X-API-Key": EDGE_API_KEY})[0] == 200)

    camera_id = f"smoke-{int(time.time())}"
    status, _ = call(
        f"{BASE}/api/internal/cameras/{camera_id}/frame", "POST",
        {"X-API-Key": EDGE_API_KEY, "Content-Type": "image/jpeg"}, b"\xff\xd8smoke\xff\xd9",
    )
    check("edge camera frame accepted", status == 204, f"HTTP {status}")
    status, body = call(f"{BASE}/api/cameras?source=live", headers=bearer)
    live = {c["id"]: c for c in json.loads(body)} if status == 200 else {}
    check("pushed camera is listed as live and online", live.get(camera_id, {}).get("status") == "online")

    status, _ = call(f"{BASE}/api/video-audit/browse?path=/etc", headers=bearer)
    check("footage browser refuses folders outside the allowed roots", status in (403, 404), f"HTTP {status}")

    if DASHBOARD:
        check("dashboard login page", call(f"{DASHBOARD}/login")[0] == 200)

    print(f"\n{len(failures)} check(s) failed" if failures else "\nAll checks passed")
    return 1 if failures else 0


if __name__ == "__main__":
    sys.exit(main())
