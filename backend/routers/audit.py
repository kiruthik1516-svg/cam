"""Audit ledger router providing tamper-resistant tracking of security events."""
from datetime import datetime
from typing import List, Optional

from fastapi import APIRouter, Depends, Query
from sqlalchemy.orm import Session

from auth import CurrentUser, require_admin
from database import get_db
from models import AuditLog
from schemas import AuditLogResponse

router = APIRouter(prefix="/api/audit-logs", tags=["Audit Logs"])


@router.get("", response_model=List[AuditLogResponse])
def get_audit_logs(
    action: Optional[str] = Query(None, description="Filter by event action (e.g. auth.login, profile.delete)"),
    username: Optional[str] = Query(None, description="Filter by executing username"),
    resource_type: Optional[str] = Query(None, description="Filter by resource type (e.g. user, profile, system)"),
    start_time: Optional[datetime] = Query(None, description="Earliest event timestamp (inclusive)"),
    end_time: Optional[datetime] = Query(None, description="Latest event timestamp (inclusive)"),
    limit: int = Query(100, ge=1, le=500, description="Max records to return"),
    offset: int = Query(0, ge=0, description="Number of records to skip"),
    db: Session = Depends(get_db),
    current_user: CurrentUser = Depends(require_admin),
):
    """Retrieve security audit ledger events with multi-criteria filtering (Administrator only)."""
    query = db.query(AuditLog)

    if action:
        query = query.filter(AuditLog.action == action)
    if username:
        query = query.filter(AuditLog.username == username)
    if resource_type:
        query = query.filter(AuditLog.resource_type == resource_type)
    if start_time:
        query = query.filter(AuditLog.timestamp >= start_time)
    if end_time:
        query = query.filter(AuditLog.timestamp <= end_time)

    records = query.order_by(AuditLog.timestamp.desc()).offset(offset).limit(limit).all()
    return [AuditLogResponse.model_validate(r) for r in records]
