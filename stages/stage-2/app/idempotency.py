from typing import Callable, Optional, Tuple, Dict, Any
import json
import asyncio
from fastapi import Request, Response
from starlette.middleware.base import BaseHTTPMiddleware
from starlette.responses import JSONResponse

from app.storage import storage
from app.validation import validate_idempotency_key, create_error_response


IDEMPOTENT_PATHS = {
    "POST": {
        "/payments",
        "/requests",
        "/splits",
        "/settlements",
        "/authorizations",
    }
}

# Paths that require idempotency with dynamic segments
IDEMPOTENT_PATH_PATTERNS = {
    "POST": [
        "/requests/",  # Will match /requests/{id}/pay
        "/authorizations/",  # Will match /authorizations/{id}/capture
    ]
}


def is_idempotent_path(method: str, path: str) -> bool:
    """Check if a path requires idempotency key."""
    if method != "POST":
        return False
    
    # Check exact matches
    if path in IDEMPOTENT_PATHS.get("POST", set()):
        return True
    
    # Check pattern matches
    for pattern in IDEMPOTENT_PATH_PATTERNS.get("POST", []):
        if path.startswith(pattern):
            if pattern == "/requests/":
                parts = path.split("/")
                # /requests/{id}/pay has 4 parts: ['', 'requests', '{id}', 'pay']
                if len(parts) == 4 and parts[3] == "pay":
                    return True
            elif pattern == "/authorizations/":
                parts = path.split("/")
                # /authorizations/{id}/capture has 4 parts: ['', 'authorizations', '{id}', 'capture']
                if len(parts) == 4 and parts[3] == "capture":
                    return True
    return False


class IdempotencyMiddleware(BaseHTTPMiddleware):
    def __init__(self, app, *args, **kwargs):
        super().__init__(app, *args, **kwargs)
        # Lock per user+key to handle concurrent identical requests
        self._locks: Dict[str, asyncio.Lock] = {}
        self._locks_lock = asyncio.Lock()

    async def _get_lock(self, key: str) -> asyncio.Lock:
        async with self._locks_lock:
            if key not in self._locks:
                self._locks[key] = asyncio.Lock()
            return self._locks[key]

    async def dispatch(self, request: Request, call_next: Callable) -> Response:
        if not is_idempotent_path(request.method, request.url.path):
            return await call_next(request)

        auth_header = request.headers.get("Authorization", "")
        if not auth_header.startswith("Bearer "):
            return await call_next(request)

        token = auth_header[7:]
        user = storage.get_user_by_token(token)
        if not user:
            return await call_next(request)

        idempotency_key = request.headers.get("Idempotency-Key")
        try:
            validate_idempotency_key(idempotency_key)
        except Exception as e:
            return JSONResponse(
                status_code=400,
                content=create_error_response("missing_idempotency_key", str(e))
            )

        # Read and cache the body for later use
        body_bytes = await request.body()
        try:
            body = json.loads(body_bytes) if body_bytes else {}
        except json.JSONDecodeError:
            body = {}

        # Store the parsed body in request state for endpoints to use
        request.state.idempotency_body = body

        # Create a lock for this user+key combination to handle concurrent requests
        lock_key = f"{user.id}:{idempotency_key}"
        lock = await self._get_lock(lock_key)

        async with lock:
            # Check if this request has been processed before
            existing = storage.check_idempotency(user.id, idempotency_key, request.method, request.url.path, body)
            if existing:
                status_code, response_body = existing
                return JSONResponse(status_code=status_code, content=response_body)

            # Process the request normally - endpoints will store their own idempotent responses
            response = await call_next(request)

        return response