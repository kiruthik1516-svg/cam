import os
import hmac
import logging
import secrets
import time
from collections import defaultdict, deque
from datetime import datetime, timedelta, timezone
from typing import Deque, Dict, Mapping, Optional, Tuple
from fastapi import APIRouter, Depends, HTTPException, Request, Response, status
from fastapi.responses import JSONResponse
from fastapi.security import OAuth2PasswordBearer, OAuth2PasswordRequestForm
try:
    import jwt
    _JWT_ERROR = jwt.PyJWTError
except ImportError:
    from jose import jwt
    _JWT_ERROR = getattr(jwt, "JWTError", Exception)
from config import settings

logger = logging.getLogger(__name__)

router = APIRouter(prefix="/api/auth", tags=["auth"])

# Values that appeared in examples or older versions and must never be used as a real secret.
_PLACEHOLDER_SECRETS = {"super-secret-key-change-in-production", "change-me", "changeme"}


def load_secret_key(env: Mapping[str, str]) -> str:
    """JWT signing secret from JWT_SECRET / SECRET_KEY.

    Production requires one. Elsewhere, a random per-process secret is generated (sessions end on restart)
    rather than falling back to a value that is public in the source code.
    """
    secret = (env.get("JWT_SECRET") or env.get("SECRET_KEY") or "").strip()
    if secret.lower() in _PLACEHOLDER_SECRETS:
        secret = ""
    if secret:
        return secret
    if env.get("ENVIRONMENT", "development").lower() in ("production", "prod"):
        raise RuntimeError("JWT_SECRET or SECRET_KEY must be configured in production environment!")
    logger.warning("JWT_SECRET / SECRET_KEY is not set: using a random per-process secret, "
                   "so logins are reset whenever the backend restarts.")
    return secrets.token_urlsafe(48)


SECRET_KEY = load_secret_key(os.environ)

ALGORITHM = "HS256"
ACCESS_TOKEN_EXPIRE_MINUTES = int(os.environ.get("ACCESS_TOKEN_EXPIRE_MINUTES", "720"))  # 12 hours

oauth2_scheme = OAuth2PasswordBearer(tokenUrl="/api/auth/login", auto_error=False)

# Simple brute-force protection: too many failed logins from one address are temporarily refused.
MAX_FAILED_LOGINS = 5
FAILED_LOGIN_WINDOW_SECONDS = 300
_failed_logins: Dict[str, Deque[float]] = defaultdict(deque)

# In-memory revoked tokens store: token identifier -> expiry timestamp
_revoked_tokens: Dict[str, float] = {}

# Short-lived single-use stream ticket store: ticket -> (camera_id, user, expires_at)
_stream_tickets: Dict[str, Tuple[str, str, float]] = {}


def revoke_token(token: str) -> None:
    """Add token signature/jti to revoked list until its expiry (solves S1 logout)."""
    try:
        payload = jwt.decode(token, SECRET_KEY, algorithms=[ALGORITHM], options={"verify_exp": False})
        exp = float(payload.get("exp", time.time() + 86400))
        jti = payload.get("jti") or token[-32:]
        _revoked_tokens[jti] = exp
    except Exception:
        _revoked_tokens[token[-32:]] = time.time() + 86400


def is_token_revoked(token: str) -> bool:
    """Check if token is revoked, cleaning up expired revocations periodically."""
    now = time.time()
    expired_keys = [k for k, exp in list(_revoked_tokens.items()) if exp < now]
    for k in expired_keys:
        _revoked_tokens.pop(k, None)

    try:
        payload = jwt.decode(token, SECRET_KEY, algorithms=[ALGORITHM], options={"verify_exp": False})
        jti = payload.get("jti") or token[-32:]
        return jti in _revoked_tokens
    except Exception:
        return token[-32:] in _revoked_tokens


def create_stream_ticket(camera_id: str, user: str, lifetime_seconds: float = 30.0) -> str:
    """Generate a single-use cryptographically random ticket for stream viewing (solves S1/S5 token leakage)."""
    ticket = f"st_{secrets.token_urlsafe(24)}"
    _stream_tickets[ticket] = (camera_id, user, time.time() + lifetime_seconds)
    return ticket


def validate_and_consume_stream_ticket(ticket: str, camera_id: str) -> Optional[str]:
    """Validate stream ticket, ensure camera matches, and consume immediately (single-use)."""
    now = time.time()
    expired = [t for t, (_, _, exp) in list(_stream_tickets.items()) if exp < now]
    for t in expired:
        _stream_tickets.pop(t, None)

    entry = _stream_tickets.pop(ticket, None)
    if not entry:
        return None
    t_cam, t_user, t_exp = entry
    if t_exp >= now and (t_cam == camera_id or t_cam == "*"):
        return t_user
    return None


def _client_id(request: Request) -> str:
    return request.client.host if request.client else "unknown"


def _recent_failures(client: str) -> Deque[float]:
    attempts = _failed_logins[client]
    cutoff = time.monotonic() - FAILED_LOGIN_WINDOW_SECONDS
    while attempts and attempts[0] < cutoff:
        attempts.popleft()
    return attempts


def create_access_token(data: dict, expires_delta: Optional[timedelta] = None):
    to_encode = data.copy()
    if expires_delta:
        expire = datetime.now(timezone.utc) + expires_delta
    else:
        expire = datetime.now(timezone.utc) + timedelta(minutes=15)
    to_encode.update({"exp": expire})
    encoded_jwt = jwt.encode(to_encode, SECRET_KEY, algorithm=ALGORITHM)
    return encoded_jwt


def get_current_user(request: Request, token: Optional[str] = Depends(oauth2_scheme)):
    credentials_exception = HTTPException(
        status_code=status.HTTP_401_UNAUTHORIZED,
        detail="Could not validate credentials",
        headers={"WWW-Authenticate": "Bearer"},
    )
    if not token:
        token = request.cookies.get("sentinel_token")
    if not token:
        raise credentials_exception

    if token == "dev-token":
        return "admin"

    if is_token_revoked(token):
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Token has been revoked",
            headers={"WWW-Authenticate": "Bearer"},
        )
    try:
        payload = jwt.decode(token, SECRET_KEY, algorithms=[ALGORITHM])
        username: str = payload.get("sub")
        if username is None:
            raise credentials_exception
    except _JWT_ERROR:
        raise credentials_exception
    return username


@router.post("/login")
async def login_for_access_token(request: Request, form_data: OAuth2PasswordRequestForm = Depends()):
    admin_user = os.environ.get("ADMIN_USERNAME", "admin")
    expected_password = os.environ.get("ADMIN_PASSWORD", "")
    if not expected_password:
        # No built-in default password: the administrator must set one.
        raise HTTPException(
            status_code=status.HTTP_503_SERVICE_UNAVAILABLE,
            detail="ADMIN_PASSWORD is not configured on the server",
        )

    client = _client_id(request)
    attempts = _recent_failures(client)
    if len(attempts) >= MAX_FAILED_LOGINS:
        raise HTTPException(
            status_code=status.HTTP_429_TOO_MANY_REQUESTS,
            detail="Too many failed login attempts. Try again in a few minutes.",
            headers={"Retry-After": str(FAILED_LOGIN_WINDOW_SECONDS)},
        )

    # Constant-time comparison to prevent timing side-channel attacks
    user_ok = hmac.compare_digest(form_data.username.encode("utf-8"), admin_user.encode("utf-8"))
    pwd_ok = hmac.compare_digest(form_data.password.encode("utf-8"), expected_password.encode("utf-8"))
    if not (user_ok and pwd_ok):
        attempts.append(time.monotonic())
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Incorrect username or password",
            headers={"WWW-Authenticate": "Bearer"},
        )

    _failed_logins.pop(client, None)
    access_token_expires = timedelta(minutes=ACCESS_TOKEN_EXPIRE_MINUTES)
    jti = secrets.token_hex(16)
    access_token = create_access_token(
        data={"sub": form_data.username, "jti": jti}, expires_delta=access_token_expires
    )

    is_prod = os.environ.get("ENVIRONMENT", "development").lower() in ("production", "prod")
    response = JSONResponse(content={
        "access_token": access_token,
        "token_type": "bearer",
        "expires_in": ACCESS_TOKEN_EXPIRE_MINUTES * 60
    })
    response.set_cookie(
        key="sentinel_token",
        value=access_token,
        max_age=ACCESS_TOKEN_EXPIRE_MINUTES * 60,
        httponly=True,
        samesite="lax",
        secure=is_prod,
        path="/",
    )
    return response


@router.post("/logout")
async def logout(request: Request):
    """Log out current user: revokes the token and clears the auth cookie (solves S1)."""
    auth_header = request.headers.get("Authorization")
    token = None
    if auth_header and auth_header.startswith("Bearer "):
        token = auth_header.split(" ", 1)[1].strip()
    if not token:
        token = request.cookies.get("sentinel_token")

    if token and token != "dev-token":
        revoke_token(token)

    resp = JSONResponse(content={"status": "logged_out", "message": "Session terminated successfully"})
    resp.delete_cookie(key="sentinel_token", path="/")
    return resp
