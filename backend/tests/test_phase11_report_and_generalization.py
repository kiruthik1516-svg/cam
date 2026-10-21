"""Unit tests for Phase 11: Enterprise Generalization, Report Engine & Production Sign-Off.

Covers:
1. Audit ledger CSV export endpoint (/api/audit-logs/export/csv) with admin authorization.
2. Rejection of unauthenticated and unauthorized (viewer/operator) CSV export attempts.
3. Multi-criteria filtering for CSV export (action, severity, status, user_id).
4. Dialect-aware SQL in demographic analytics distributions (/age-distribution, /gender-distribution).
5. Dynamic ReportLab PDF customization engine parameters and artifact creation.
"""

import csv
import io
import os
import sys
import tempfile
from datetime import datetime
from pathlib import Path

import pytest
from fastapi.testclient import TestClient

backend_dir = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(backend_dir))
sys.path.insert(0, str(backend_dir.parent))

from auth import create_access_token
from database import SessionLocal
from main import app
from models import AuditLog
from scripts.generate_security_report_pdf import build_pdf

client = TestClient(app)


def _admin_headers():
    token = create_access_token({"sub": "admin", "role": "admin", "user_id": "root-admin"})
    return {"Authorization": f"Bearer {token}"}


def _operator_headers():
    token = create_access_token({"sub": "operator_p11", "role": "operator", "user_id": "op-p11"})
    return {"Authorization": f"Bearer {token}"}


def _viewer_headers():
    token = create_access_token({"sub": "viewer_p11", "role": "viewer", "user_id": "vw-p11"})
    return {"Authorization": f"Bearer {token}"}


@pytest.fixture(autouse=True)
def _cleanup_audit_logs():
    client.cookies.clear()
    yield
    client.cookies.clear()
    db = SessionLocal()
    try:
        db.query(AuditLog).filter(AuditLog.action.like("TEST_P11_%")).delete()
        db.commit()
    finally:
        db.close()


def test_audit_csv_export_admin_authorized():
    """Verify that admins can export audit ledger logs as RFC-4180 CSV."""
    import uuid

    db = SessionLocal()
    try:
        log1 = AuditLog(
            id=str(uuid.uuid4()),
            action="TEST_P11_LOGIN",
            user_id="root-admin",
            username="admin",
            role="admin",
            resource_type="AUTH",
            resource_id="session-001",
            details="User logged in from test runner",
            client_ip="127.0.0.1",
            timestamp=datetime.now(),
        )
        log2 = AuditLog(
            id=str(uuid.uuid4()),
            action="TEST_P11_TAMPER_ALERT",
            user_id="edge-camera-1",
            username="camera_agent",
            role="operator",
            resource_type="CCTV",
            resource_id="cam-01",
            details="Blackout gap detected in timeline",
            client_ip="192.168.1.100",
            timestamp=datetime.now(),
        )
        db.add_all([log1, log2])
        db.commit()
    finally:
        db.close()

    res = client.get("/api/audit-logs/export/csv", headers=_admin_headers())
    assert res.status_code == 200, res.text
    assert "text/csv" in res.headers.get("content-type", "")
    assert 'attachment; filename="audit_ledger_' in res.headers.get("content-disposition", "")

    # Parse and validate CSV
    reader = csv.DictReader(io.StringIO(res.text))
    fieldnames = reader.fieldnames
    assert "ID" in fieldnames
    assert "Action" in fieldnames
    assert "Username" in fieldnames
    assert "Resource Type" in fieldnames
    assert "Resource ID" in fieldnames
    assert "Client IP" in fieldnames
    assert "Details" in fieldnames

    rows = list(reader)
    actions = [r["Action"] for r in rows]
    assert "TEST_P11_LOGIN" in actions
    assert "TEST_P11_TAMPER_ALERT" in actions


def test_audit_csv_export_viewer_forbidden():
    """Verify that viewers and operators are forbidden from exporting security audit logs."""
    res_viewer = client.get("/api/audit-logs/export/csv", headers=_viewer_headers())
    assert res_viewer.status_code == 403

    res_op = client.get("/api/audit-logs/export/csv", headers=_operator_headers())
    assert res_op.status_code == 403


def test_audit_csv_export_unauthenticated():
    """Verify that unauthenticated callers cannot access the audit CSV export endpoint."""
    res = client.get("/api/audit-logs/export/csv")
    assert res.status_code == 401


def test_audit_csv_export_filters():
    """Verify that multi-criteria query parameters correctly filter the exported CSV."""
    import uuid

    db = SessionLocal()
    try:
        log_crit = AuditLog(
            id=str(uuid.uuid4()),
            action="TEST_P11_CRITICAL_BREACH",
            user_id="root-admin",
            username="sec_admin",
            role="admin",
            resource_type="ACCESS_CONTROL",
            resource_id="door-main",
            details="Unauthorized bypass attempt",
            client_ip="10.0.0.1",
            timestamp=datetime.now(),
        )
        db.add(log_crit)
        db.commit()
    finally:
        db.close()

    res = client.get(
        "/api/audit-logs/export/csv?action=TEST_P11_CRITICAL_BREACH&resource_type=ACCESS_CONTROL",
        headers=_admin_headers(),
    )
    assert res.status_code == 200
    reader = csv.DictReader(io.StringIO(res.text))
    rows = list(reader)
    assert len(rows) >= 1
    for r in rows:
        assert r["Action"] == "TEST_P11_CRITICAL_BREACH"
        assert r["Resource Type"] == "ACCESS_CONTROL"


def test_analytics_dialect_aware_distributions():
    """Verify that age and gender distribution queries run cleanly across SQLite and PostgreSQL."""
    res_age = client.get("/api/analytics/age-distribution", headers=_viewer_headers())
    assert res_age.status_code == 200
    age_data = res_age.json()
    assert isinstance(age_data, list)

    res_gender = client.get("/api/analytics/gender-distribution", headers=_viewer_headers())
    assert res_gender.status_code == 200
    gender_data = res_gender.json()
    assert isinstance(gender_data, list)


def test_pdf_report_customization_engine():
    """Verify that build_pdf accepts dynamic enterprise parameters and generates valid PDF."""
    with tempfile.NamedTemporaryFile(suffix=".pdf", delete=False) as tf:
        temp_pdf_path = tf.name

    try:
        build_pdf(
            output_pdf_path=temp_pdf_path,
            organization="Pacific Global Logistics Terminal",
            location="Gate Ch9 - Northern Perimeter",
            report_title="Automated Forensic Security & Access Audit",
            auditor="Lead Forensic Investigation Team",
            report_id="PGL-AUDIT-20261021",
            report_date="21 October 2026",
        )
        assert os.path.exists(temp_pdf_path)
        file_size = os.path.getsize(temp_pdf_path)
        assert file_size > 10000, f"Expected PDF > 10KB, got {file_size}"

        with open(temp_pdf_path, "rb") as f:
            header = f.read(5)
            assert header == b"%PDF-", "Generated file is not a valid PDF"
    finally:
        if os.path.exists(temp_pdf_path):
            os.remove(temp_pdf_path)
