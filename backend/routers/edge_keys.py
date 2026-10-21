"""Scoped Edge Device API Key management router (solves S8)."""
import hashlib
import secrets
import uuid
from datetime import datetime
from typing import List

from fastapi import APIRouter, Depends, HTTPException, Request, status
from sqlalchemy.orm import Session

from auth import CurrentUser, log_audit, require_admin
from config import IST
from database import get_db
from models import DeviceApiKey
from schemas import (
    DeviceApiKeyCreatedResponse,
    DeviceApiKeyCreateRequest,
    DeviceApiKeyResponse,
)

router = APIRouter(prefix="/api/edge-keys", tags=["Edge Device Keys"])


@router.get("", response_model=List[DeviceApiKeyResponse])
def list_edge_keys(
    db: Session = Depends(get_db),
    current_user: CurrentUser = Depends(require_admin),
):
    """List all registered edge device API keys (Administrator only)."""
    keys = db.query(DeviceApiKey).order_by(DeviceApiKey.created_at.desc()).all()
    return [DeviceApiKeyResponse.model_validate(k) for k in keys]


@router.post("", response_model=DeviceApiKeyCreatedResponse, status_code=status.HTTP_201_CREATED)
def create_edge_key(
    req: DeviceApiKeyCreateRequest,
    request: Request,
    db: Session = Depends(get_db),
    current_user: CurrentUser = Depends(require_admin),
):
    """
    Generate and register a new scoped edge device credentials key (Administrator only).
    The full secret key is returned ONCE upon generation and cannot be retrieved again.
    """
    name = req.name.strip()
    if not name or len(name) > 100:
        raise HTTPException(
            status_code=status.HTTP_422_UNPROCESSABLE_ENTITY,
            detail="Key name must be between 1 and 100 characters",
        )

    # Format comma-separated allowed cameras or None for unrestricted
    allowed_str = None
    if req.allowed_cameras:
        cleaned_cams = [c.strip() for c in req.allowed_cameras if c and c.strip()]
        if cleaned_cams:
            allowed_str = ",".join(cleaned_cams)

    raw_secret = f"sk_edge_{secrets.token_urlsafe(32)}"
    key_hash = hashlib.sha256(raw_secret.encode("utf-8")).hexdigest()
    key_prefix = f"{raw_secret[:12]}..."

    new_key = DeviceApiKey(
        id=str(uuid.uuid4()),
        name=name,
        key_hash=key_hash,
        key_prefix=key_prefix,
        allowed_cameras=allowed_str,
        is_active=True,
        created_at=datetime.now(IST),
    )
    db.add(new_key)
    db.commit()
    db.refresh(new_key)

    client_ip = request.client.host if request.client else None
    log_audit(
        db=db,
        action="edge_key.create",
        username=current_user.username,
        role=current_user.role,
        user_id=current_user.id,
        resource_type="device_api_key",
        resource_id=new_key.id,
        client_ip=client_ip,
        details=f"Created edge key '{new_key.name}' (prefix: {key_prefix}, scope: {allowed_str or 'all cameras'})",
    )

    return DeviceApiKeyCreatedResponse(
        id=new_key.id,
        name=new_key.name,
        key=raw_secret,
        key_prefix=key_prefix,
        allowed_cameras=new_key.allowed_cameras,
        is_active=new_key.is_active,
        created_at=new_key.created_at,
    )


@router.delete("/{key_id}")
def revoke_edge_key(
    key_id: str,
    request: Request,
    db: Session = Depends(get_db),
    current_user: CurrentUser = Depends(require_admin),
):
    """Revoke an edge device key immediately (Administrator only)."""
    key = db.query(DeviceApiKey).filter(DeviceApiKey.id == key_id).first()
    if not key:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Device API key not found")

    key.is_active = False
    db.commit()

    client_ip = request.client.host if request.client else None
    log_audit(
        db=db,
        action="edge_key.revoke",
        username=current_user.username,
        role=current_user.role,
        user_id=current_user.id,
        resource_type="device_api_key",
        resource_id=key_id,
        client_ip=client_ip,
        details=f"Revoked edge key '{key.name}' (prefix: {key.key_prefix})",
    )

    return {"revoked": True, "key_id": key_id, "name": key.name}
