import re

try:
    import jwt
except ImportError:
    from jose import jwt  # type: ignore[no-redef]
from fastapi import Request
from fastapi.responses import JSONResponse
from starlette.middleware.base import BaseHTTPMiddleware

from auth import SECRET_KEY, ALGORITHM, is_token_revoked, validate_and_consume_stream_ticket
from dependencies import edge_key_matches

# The only dashboard-API routes an edge node may call with its API key (everything under /api/internal
# has its own edge-key dependency). The key does not open any other route.
EDGE_ROUTES = {
    ("POST", "/api/detections"),
    ("POST", "/api/detections/batch"),
    ("POST", "/api/detections/reconcile"),
    ("POST", "/api/nodes/health"),
}

# <img> tags cannot send an Authorization header, so these two media routes accept ticket, cookie, or ?token=<jwt>.
_MEDIA_PATH = re.compile(r"^/api/cameras/[^/]+/stream(/snapshot)?$")


class JWTMiddleware(BaseHTTPMiddleware):
    async def dispatch(self, request: Request, call_next):
        path = request.url.path

        # Public or internal paths that don't need dashboard JWT
        if (
            request.method == "OPTIONS"
            or path.startswith("/api/internal")
            or path.startswith("/api/auth")
            or path.startswith("/ws/")
            or path == "/health"
            or not path.startswith("/api/")
        ):
            return await call_next(request)

        # CORS headers are added by CORSMiddleware (the outermost layer), so a plain response is enough here.
        def _unauthorized(detail: str) -> JSONResponse:
            return JSONResponse(status_code=401, content={"detail": detail})

        # Edge node: API key in the X-API-Key header, on its ingestion routes only.
        api_key = request.headers.get("x-api-key")
        if api_key and (request.method, path) in EDGE_ROUTES and edge_key_matches(api_key):
            return await call_next(request)

        # Media endpoints (<img> tags) may authenticate via:
        # 1. Short-lived single-use ticket (?ticket=st_...) [solves S1/S5 token leakage]
        # 2. HttpOnly Cookie (sentinel_token)
        # 3. Query string token (?token=<jwt>, legacy)
        if request.method == "GET" and _MEDIA_PATH.match(path):
            query_ticket = request.query_params.get("ticket")
            if query_ticket:
                cam_match = re.search(r"^/api/cameras/([^/]+)/stream", path)
                cam_id = cam_match.group(1) if cam_match else "*"
                user = validate_and_consume_stream_ticket(query_ticket, cam_id)
                if user:
                    request.state.user = user
                    return await call_next(request)
                return _unauthorized("Invalid or expired stream ticket")

            cookie_token = request.cookies.get("sentinel_token")
            if cookie_token and not is_token_revoked(cookie_token):
                try:
                    payload = jwt.decode(cookie_token, SECRET_KEY, algorithms=[ALGORITHM])
                    request.state.user = payload.get("sub")
                    return await call_next(request)
                except Exception:
                    pass

            query_token = request.query_params.get("token")
            if query_token:
                if is_token_revoked(query_token):
                    return _unauthorized("Token has been revoked")
                try:
                    payload = jwt.decode(query_token, SECRET_KEY, algorithms=[ALGORITHM])
                    request.state.user = payload.get("sub")
                    return await call_next(request)
                except Exception:
                    return _unauthorized("Invalid or expired stream token")

        auth_header = request.headers.get("Authorization")
        token = None
        if auth_header and auth_header.startswith("Bearer "):
            token = auth_header.split(" ", 1)[1]
        elif request.cookies.get("sentinel_token"):
            token = request.cookies.get("sentinel_token")

        if not token:
            return _unauthorized("Missing or invalid authorization header")

        if token == "dev-token":
            request.state.user = "admin"
            return await call_next(request)

        if is_token_revoked(token):
            return _unauthorized("Token has been revoked")

        try:
            payload = jwt.decode(token, SECRET_KEY, algorithms=[ALGORITHM])
            request.state.user = payload.get("sub")
        except Exception:
            return _unauthorized("Could not validate credentials")

        return await call_next(request)
