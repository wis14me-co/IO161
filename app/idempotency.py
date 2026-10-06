from typing import Callable, Optional, Tuple, Dict, Any, AsyncIterator
import json
import asyncio
from fastapi import Request, Response
from starlette.middleware.base import BaseHTTPMiddleware
from starlette.responses import JSONResponse, StreamingResponse

from app.storage import storage
from app.validation import validate_idempotency_key, create_error_response


IDEMPOTENT_PATHS = {
    "POST": {
        "/payments",
        "/requests",
        "/splits",
        "/settlements",
        "/authorizations",
        "/authorizations/{auth_id}/capture",
        "/authorizations/{auth_id}/void",
        "/correction-batches",
    }
}

# Paths that require idempotency with dynamic segments
IDEMPOTENT_PATH_PATTERNS = {
    "POST": [
        "/requests/",  # Will match /requests/{id}/pay
        "/payments/{payment_id}/refunds",  # Will match /payments/{id}/refunds
    ]
}


def is_idempotent_path(method: str, path: str) -> bool:
    """Check if a path requires idempotency key."""
    if method != "POST":
        return False
    
    # Check exact matches
    if path in IDEMPOTENT_PATHS.get("POST", set()):
        return True
    
    # Check pattern matches for dynamic paths
    for pattern in IDEMPOTENT_PATH_PATTERNS.get("POST", []):
        # Handle patterns with dynamic segments like /payments/{payment_id}/refunds
        if "{" in pattern and "}" in pattern:
            # Split pattern and path by "/" for comparison
            pattern_parts = pattern.split("/")
            path_parts = path.split("/")
            
            # Check if lengths match (accounting for dynamic segment)
            if len(pattern_parts) != len(path_parts):
                continue
            
            # Compare each part
            match = True
            for p_part, path_part in zip(pattern_parts, path_parts):
                # Dynamic segment {name} matches any non-empty value
                if "{" in p_part and "}" in p_part:
                    # The dynamic part should capture a non-empty ID
                    if not path_part or path_part == "":
                        match = False
                        break
                elif p_part != path_part:
                    match = False
                    break
            
            if match:
                return True
        else:
            # Static pattern
            if not pattern.endswith("/"):
                if path == pattern:
                    return True
            elif path.startswith(pattern):
                # For patterns ending with /, check the format
                # /requests/ should only match /requests/{id}/pay, not /requests/{id}/decline or /requests/{id}/cancel
                if pattern == "/requests/":
                    parts = path.split("/")
                    # /requests/{id}/pay has 4 parts: ['', 'requests', '{id}', 'pay']
                    if len(parts) == 4 and parts[3] == "pay":
                        return True
                else:
                    return True
    return False


class IdempotencyMiddleware(BaseHTTPMiddleware):
    def __init__(self, app, *args, **kwargs):
        super().__init__(app, *args, **kwargs)
        # Lock per user+key+method+path to handle concurrent identical requests
        self._locks: Dict[str, asyncio.Lock] = {}
        self._locks_lock = asyncio.Lock()

    async def _get_lock(self, key: str) -> asyncio.Lock:
        async with self._locks_lock:
            if key not in self._locks:
                self._locks[key] = asyncio.Lock()
            return self._locks[key]

    async def _read_body(self, request: Request) -> bytes:
        """Read and return the request body, caching it for later use."""
        if not hasattr(request.state, '_body'):
            request.state._body = await request.body()
        return request.state._body

    async def _get_json_body(self, request: Request) -> dict:
        """Parse JSON body."""
        body_bytes = await self._read_body(request)
        if not body_bytes:
            return {}
        try:
            return json.loads(body_bytes.decode('utf-8'))
        except json.JSONDecodeError:
            return {}

    def _hash_body(self, body: dict) -> str:
        """Create a deterministic hash of the request body."""
        return storage._hash_body(body)

    async def _create_buffered_request(self, request: Request, body_bytes: bytes) -> Request:
        """Create a new request with buffered body for FastAPI parsing."""
        # Create a new receive function that returns our buffered body
        async def receive():
            return {"type": "http.request", "body": body_bytes, "more_body": False}
        
        # Create a new request scope with our receive
        new_scope = request.scope.copy()
        new_request = Request(new_scope, receive)
        # Copy state - State object stores attributes in __dict__
        for key, value in request.state.__dict__.items():
            setattr(new_request.state, key, value)
        return new_request

    async def dispatch(self, request: Request, call_next: Callable) -> Response:
        # Skip idempotency check for non-POST or non-idempotent paths
        if not is_idempotent_path(request.method, request.url.path):
            return await call_next(request)

        # Check for Bearer token
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

        # Read and parse body
        body_bytes = await self._read_body(request)
        body = await self._get_json_body(request)
        
        # Create lock key for this user+key+method+path combination
        lock_key = f"{user.id}:{idempotency_key}:{request.method}:{request.url.path}"
        lock = await self._get_lock(lock_key)

        async with lock:
            # Check for existing idempotency record
            existing = storage.check_idempotency(user.id, idempotency_key, request.method, request.url.path, body)
            if existing is not None:
                status_code, response_body = existing
                return JSONResponse(status_code=status_code, content=response_body)

            # No existing record - create buffered request for endpoint
            buffered_request = await self._create_buffered_request(request, body_bytes)
            
            # Execute the endpoint
            response = await call_next(buffered_request)
            
            # Only store successful responses (2xx) - failed 4xx don't consume the key per spec
            if 200 <= response.status_code < 300:
                # Read the full response body
                response_body = b""
                async for chunk in response.body_iterator:
                    response_body += chunk
                
                # Parse response JSON for storage
                try:
                    response_data = json.loads(response_body.decode('utf-8')) if response_body else {}
                except json.JSONDecodeError:
                    response_data = {}
                
                # Store idempotency record
                storage.store_idempotency(
                    user.id, idempotency_key, request.method, request.url.path,
                    body, response.status_code, response_data
                )
                
                # Return new response with captured body - remove content-length to avoid mismatch
                headers = dict(response.headers)
                headers.pop("content-length", None)
                if response.status_code == 204:
                    return Response(status_code=204, headers=headers)
                return JSONResponse(
                    status_code=response.status_code,
                    content=response_data,
                    headers=headers
                )
            else:
                # For 4xx errors, don't store the key - it remains reusable
                # Read body and return
                response_body = b""
                async for chunk in response.body_iterator:
                    response_body += chunk
                headers = dict(response.headers)
                headers.pop("content-length", None)
                return Response(
                    content=response_body,
                    status_code=response.status_code,
                    headers=headers,
                    media_type=response.media_type
                )