"""Shared authentication helpers for edge nodes (cameras / recognition processes)."""
import hmac
import os
from typing import Optional

from fastapi import Header, HTTPException

# Values that ship in examples and must never be accepted as a real key.
_PLACEHOLDER_KEYS = {"default-dev-key", "change-me", "change-me-to-a-long-random-string"}


def configured_edge_key() -> Optional[str]:
    """The server's edge API key, or None when it is missing or still a placeholder."""
    key = os.environ.get("EDGE_API_KEY", "").strip()
    if not key or key.lower() in _PLACEHOLDER_KEYS:
        return None
    return key


def edge_key_matches(candidate: Optional[str]) -> bool:
    """Constant-time check of a presented key against the configured one. False if none is configured."""
    expected = configured_edge_key()
    if not expected or not candidate:
        return False
    return hmac.compare_digest(str(candidate).encode("utf-8"), expected.encode("utf-8"))


def verify_edge_node(x_api_key: str = Header(..., alias="X-API-Key")):
    if configured_edge_key() is None:
        raise HTTPException(status_code=503, detail="EDGE_API_KEY is not configured on the server")
    if not edge_key_matches(x_api_key):
        raise HTTPException(status_code=403, detail="Invalid API Key")
    return x_api_key
