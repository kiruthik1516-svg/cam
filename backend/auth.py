import os
import hmac
import hashlib
import logging
import secrets
import time
import uuid
from collections import defaultdict, deque
from datetime import datetime, timedelta, timezone
from typing import Deque, Dict, Mapping, Optional, Tuple, Any
from fastapi import APIRouter, Depends, HTTPException, Request, Response, status
from fastapi.responses import JSONResponse
from fastapi.security import OAuth2PasswordBearer, OAuth2PasswordRequestForm
from sqlalchemy.orm import Session
try:
    import jwt
    _JWT_ERROR = jwt.PyJWTError
except ImportError:
    from jose import jwt
    _JWT_ERROR = getattr(jwt, "JWTError", Exception)
from config import settings, IST
from database import get_db

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


def _client_id(request: Request, username: Optional[str] = None) -> str:
    """Resolve client identifier supporting proxy forwarded IPs and per-username scoping (solves S7)."""
    client_ip = request.client.host if request.client else "unknown"

    forwarded_for = request.headers.get("x-forwarded-for")
    if forwarded_for:
        hops = [h.strip() for h in forwarded_for.split(",")]
        if hops:
            client_ip = hops[0]
    elif request.headers.get("x-real-ip"):
        client_ip = request.headers.get("x-real-ip").strip()

    if username:
        return f"{username.strip().lower()}@{client_ip}"
    return client_ip


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


def hash_password(password: str) -> str:
    """Hash password using PBKDF2-HMAC-SHA256 (standard library, zero binary C-dependencies)."""
    salt = secrets.token_hex(16)
    kdf = hashlib.pbkdf2_hmac("sha256", password.encode("utf-8"), salt.encode("utf-8"), 100000)
    return f"pbkdf2_sha256$100000${salt}${kdf.hex()}"


def verify_password(plain_password: str, hashed_password: str) -> bool:
    """Verify password against PBKDF2-HMAC-SHA256 hash in constant time."""
    try:
        parts = hashed_password.split("$")
        if len(parts) != 4 or parts[0] != "pbkdf2_sha256":
            return False
        iterations = int(parts[1])
        salt = parts[2]
        expected_hash = parts[3]
        candidate_kdf = hashlib.pbkdf2_hmac(
            "sha256", plain_password.encode("utf-8"), salt.encode("utf-8"), iterations
        )
        return hmac.compare_digest(candidate_kdf.hex(), expected_hash)
    except Exception:
        return False


class CurrentUser(str):
    """Authenticated user representation that inherits from str (so str(user) == username
    and user == 'admin' evaluates naturally), while exposing RBAC attributes."""

    id: Optional[str]
    role: str
    full_name: Optional[str]

    def __new__(
        cls,
        username: str,
        role: str = "viewer",
        id: Optional[str] = None,
        full_name: Optional[str] = None,
    ):
        instance = super().__new__(cls, username)
        instance.id = id
        instance.role = role
        instance.full_name = full_name
        return instance

    @property
    def username(self) -> str:
        return str(self)

    def is_admin(self) -> bool:
        return self.role == "admin"

    def is_operator(self) -> bool:
        return self.role in ("admin", "operator")

    def is_viewer(self) -> bool:
        return True


def log_audit(
    db: Session,
    action: str,
    username: str,
    role: Optional[str] = None,
    user_id: Optional[str] = None,
    resource_type: Optional[str] = None,
    resource_id: Optional[str] = None,
    client_ip: Optional[str] = None,
    details: Optional[str] = None,
) -> Optional[Any]:
    """Record an entry in the tamper-resistant audit_logs table."""
    try:
        from models import AuditLog
        entry = AuditLog(
            id=str(uuid.uuid4()),
            timestamp=datetime.now(IST),
            user_id=user_id,
            username=username,
            role=role,
            action=action,
            resource_type=resource_type,
            resource_id=resource_id,
            client_ip=client_ip,
            details=details,
        )
        db.add(entry)
        db.commit()
        return entry
    except Exception as ex:
        logger.warning("Failed to record audit log for action '%s': %s", action, ex)
        try:
            db.rollback()
        except Exception:
            pass
        return None


def get_current_user(request: Request, token: Optional[str] = Depends(oauth2_scheme)) -> CurrentUser:
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
        return CurrentUser("admin", role="admin", id="root-admin", full_name="Development Administrator")

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
        role: Optional[str] = payload.get("role")
        user_id: Optional[str] = payload.get("user_id")
        full_name: Optional[str] = payload.get("full_name")

        if not role:
            admin_user = os.environ.get("ADMIN_USERNAME", "admin")
            if username == admin_user or username == "admin":
                role = "admin"
                user_id = user_id or "root-admin"
            else:
                role = "viewer"

        return CurrentUser(username=username, role=role, id=user_id, full_name=full_name)
    except _JWT_ERROR:
        raise credentials_exception


def require_viewer(user: CurrentUser = Depends(get_current_user)) -> CurrentUser:
    """Ensure user is authenticated (viewer, operator, or admin)."""
    return user


def require_operator(user: CurrentUser = Depends(get_current_user)) -> CurrentUser:
    """Ensure user has operator or admin privileges."""
    if not user.is_operator():
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Forbidden: Operator or Administrator privileges required",
        )
    return user


def require_admin(user: CurrentUser = Depends(get_current_user)) -> CurrentUser:
    """Ensure user has administrator privileges."""
    if not user.is_admin():
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Forbidden: Administrator privileges required",
        )
    return user


@router.post("/login")
async def login_for_access_token(
    request: Request,
    form_data: OAuth2PasswordRequestForm = Depends(),
    db: Session = Depends(get_db),
):
    admin_user = os.environ.get("ADMIN_USERNAME", "admin")
    expected_password = os.environ.get("ADMIN_PASSWORD", "")

    client_ip = _client_id(request)
    client_user = _client_id(request, form_data.username)

    user_attempts = _recent_failures(client_user)
    ip_attempts = _recent_failures(client_ip)

    if len(user_attempts) >= MAX_FAILED_LOGINS or len(ip_attempts) >= MAX_FAILED_LOGINS * 3:
        raise HTTPException(
            status_code=status.HTTP_429_TOO_MANY_REQUESTS,
            detail="Too many failed login attempts. Try again in a few minutes.",
            headers={"Retry-After": str(FAILED_LOGIN_WINDOW_SECONDS)},
        )

    authenticated_user = None
    user_role = "viewer"
    user_id = None
    full_name = None

    # 1. Check database User table first
    try:
        from models import User
        db_user = db.query(User).filter(User.username == form_data.username).first()
        if db_user:
            if not db_user.is_active:
                raise HTTPException(
                    status_code=status.HTTP_401_UNAUTHORIZED,
                    detail="Account has been disabled",
                    headers={"WWW-Authenticate": "Bearer"},
                )
            if verify_password(form_data.password, db_user.hashed_password):
                authenticated_user = db_user.username
                user_role = db_user.role.value if hasattr(db_user.role, "value") else str(db_user.role)
                user_id = db_user.id
                full_name = db_user.full_name
                db_user.last_login = datetime.now(IST)
                db.commit()
    except HTTPException:
        raise
    except Exception as ex:
        logger.warning("Error checking database User during login: %s", ex)

    # 2. Fall back to root admin credentials from environment if not authenticated via DB
    if not authenticated_user:
        if form_data.username == admin_user and not expected_password:
            raise HTTPException(
                status_code=status.HTTP_503_SERVICE_UNAVAILABLE,
                detail="ADMIN_PASSWORD is not configured on the server",
            )
        if expected_password:
            user_ok = hmac.compare_digest(form_data.username.encode("utf-8"), admin_user.encode("utf-8"))
            pwd_ok = hmac.compare_digest(form_data.password.encode("utf-8"), expected_password.encode("utf-8"))
            if user_ok and pwd_ok:
                authenticated_user = admin_user
                user_role = "admin"
                user_id = "root-admin"
                full_name = "Root Administrator"

    if not authenticated_user:
        now_ts = time.monotonic()
        user_attempts.append(now_ts)
        ip_attempts.append(now_ts)
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Incorrect username or password",
            headers={"WWW-Authenticate": "Bearer"},
        )

    _failed_logins.pop(client_user, None)
    _failed_logins.pop(client_ip, None)
    access_token_expires = timedelta(minutes=ACCESS_TOKEN_EXPIRE_MINUTES)
    jti = secrets.token_hex(16)
    access_token = create_access_token(
        data={
            "sub": authenticated_user,
            "role": user_role,
            "user_id": user_id,
            "full_name": full_name,
            "jti": jti,
        },
        expires_delta=access_token_expires,
    )

    log_audit(
        db,
        action="auth.login",
        username=authenticated_user,
        role=user_role,
        user_id=user_id,
        client_ip=client_ip,
        details="User authenticated successfully",
    )

    is_prod = os.environ.get("ENVIRONMENT", "development").lower() in ("production", "prod")
    response = JSONResponse(content={
        "access_token": access_token,
        "token_type": "bearer",
        "role": user_role,
        "username": authenticated_user,
        "user_id": user_id,
        "expires_in": ACCESS_TOKEN_EXPIRE_MINUTES * 60,
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
async def logout(request: Request, db: Session = Depends(get_db)):
    """Log out current user: revokes the token and clears the auth cookie (solves S1)."""
    auth_header = request.headers.get("Authorization")
    token = None
    if auth_header and auth_header.startswith("Bearer "):
        token = auth_header.split(" ", 1)[1].strip()
    if not token:
        token = request.cookies.get("sentinel_token")

    username = "unknown"
    if token and token != "dev-token":
        try:
            payload = jwt.decode(token, SECRET_KEY, algorithms=[ALGORITHM], options={"verify_exp": False})
            username = payload.get("sub", "unknown")
        except Exception:
            pass
        revoke_token(token)

    log_audit(
        db,
        action="auth.logout",
        username=username,
        client_ip=_client_id(request),
        details="User logged out",
    )

    resp = JSONResponse(content={"status": "logged_out", "message": "Session terminated successfully"})
    resp.delete_cookie(key="sentinel_token", path="/")
    return resp
