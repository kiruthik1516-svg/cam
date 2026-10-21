"""Shared authentication helpers for edge nodes (cameras / recognition processes)."""
import hashlib
import hmac
import logging
import os
from datetime import datetime
from typing import Optional, Any

from fastapi import Header, HTTPException

from config import IST

logger = logging.getLogger(__name__)

# Values that ship in examples and must never be accepted as a real key.
_PLACEHOLDER_KEYS = {"default-dev-key", "change-me", "change-me-to-a-long-random-string"}


def configured_edge_key() -> Optional[str]:
    """The server's edge API key, or None when it is missing or still a placeholder."""
    key = os.environ.get("EDGE_API_KEY", "").strip()
    if not key or key.lower() in _PLACEHOLDER_KEYS:
        return None
    return key


def has_active_device_keys() -> bool:
    """Check if any active device API keys exist in the database."""
    try:
        from database import SessionLocal
        from models import DeviceApiKey
        with SessionLocal() as db:
            return db.query(DeviceApiKey).filter(DeviceApiKey.is_active == True).count() > 0
    except Exception:
        return False


def get_active_device_key(candidate: Optional[str]) -> Optional[Any]:
    """Look up active DeviceApiKey by hashing presented secret."""
    if not candidate or candidate in _PLACEHOLDER_KEYS:
        return None
    try:
        from database import SessionLocal
        from models import DeviceApiKey
        key_hash = hashlib.sha256(candidate.encode("utf-8")).hexdigest()
        with SessionLocal() as db:
            device_key = db.query(DeviceApiKey).filter(
                DeviceApiKey.key_hash == key_hash,
                DeviceApiKey.is_active == True
            ).first()
            if device_key:
                device_key.last_used_at = datetime.now(IST)
                db.commit()
                return {
                    "id": device_key.id,
                    "name": device_key.name,
                    "allowed_cameras": device_key.allowed_cameras,
                }
            return None
    except Exception as ex:
        logger.debug("Device API key lookup error: %s", ex)
        return None


def edge_key_matches(candidate: Optional[str]) -> bool:
    """Check candidate against root EDGE_API_KEY or active database DeviceApiKey."""
    if not candidate or candidate in _PLACEHOLDER_KEYS:
        return False

    expected = configured_edge_key()
    if expected and hmac.compare_digest(str(candidate).encode("utf-8"), expected.encode("utf-8")):
        return True

    return get_active_device_key(candidate) is not None


def verify_camera_access(candidate: Optional[str], camera_id: str) -> bool:
    """Enforce camera-level authorization scope for device keys (S8)."""
    if not candidate or candidate in _PLACEHOLDER_KEYS:
        raise HTTPException(status_code=403, detail="Invalid API Key")

    expected = configured_edge_key()
    if expected and hmac.compare_digest(str(candidate).encode("utf-8"), expected.encode("utf-8")):
        return True

    dev_key = get_active_device_key(candidate)
    if not dev_key:
        raise HTTPException(status_code=403, detail="Invalid API Key")

    allowed_cameras_str = dev_key.get("allowed_cameras")
    if allowed_cameras_str:
        allowed = [c.strip() for c in allowed_cameras_str.split(",") if c.strip()]
        if allowed and camera_id not in allowed and "*" not in allowed:
            raise HTTPException(
                status_code=403,
                detail=f"Edge key is not authorized for camera '{camera_id}'"
            )

    return True


def verify_edge_node(x_api_key: str = Header(..., alias="X-API-Key")):
    """Authorize edge node via root EDGE_API_KEY or database DeviceApiKey."""
    if edge_key_matches(x_api_key):
        return x_api_key

    # If key did not match, check if any authentication mechanism is configured on server
    if configured_edge_key() is None and not has_active_device_keys():
        raise HTTPException(status_code=503, detail="EDGE_API_KEY is not configured on the server")

    raise HTTPException(status_code=403, detail="Invalid API Key")
