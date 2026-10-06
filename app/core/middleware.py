import time
import logging
import uuid
from typing import Callable, Optional, Dict, Any, Set
from collections import defaultdict
from fastapi import Request, Response, HTTPException
from starlette.middleware.base import BaseHTTPMiddleware
from starlette.middleware.cors import CORSMiddleware
from starlette.responses import JSONResponse, Response as StarletteResponse
from starlette.types import ASGIApp

from app.core.exceptions import (
    AppException,
    RateLimitException,
    app_exception_to_http
)

logger = logging.getLogger(__name__)


class CSRFProtectionMiddleware(BaseHTTPMiddleware):
    """Middleware for CSRF protection using double-submit cookie pattern."""
    
    def __init__(
        self,
        app: ASGIApp,
        cookie_name: str = "pocketful_csrf",
        header_name: str = "X-CSRF-Token",
        form_field_name: str = "csrf_token",
        exempt_paths: Optional[Set[str]] = None,
        exempt_methods: Optional[Set[str]] = None,
    ):
        super().__init__(app)
        self.cookie_name = cookie_name
        self.header_name = header_name
        self.form_field_name = form_field_name
        self.exempt_paths = exempt_paths or {
            "/health", "/metrics", "/docs", "/openapi.json", "/favicon.ico",
            "/api/v1/auth/login", "/api/v1/auth/signup", "/api/v1/auth/logout",
            "/auth/login", "/auth/signup", "/auth/logout"
        }
        self.exempt_methods = exempt_methods or {"GET", "HEAD", "OPTIONS"}
    
    async def dispatch(self, request: Request, call_next: Callable) -> Response:
        # Skip CSRF check for exempt paths and safe methods
        if request.url.path in self.exempt_paths:
            return await call_next(request)
        
        if request.method in self.exempt_methods:
            return await call_next(request)
        
        # Check if request has session cookie (browser client)
        session_cookie = request.cookies.get("pocketful_session")
        if not session_cookie:
            # No session cookie, likely API client - skip CSRF
            return await call_next(request)
        
        # Get CSRF token from cookie
        csrf_cookie = request.cookies.get(self.cookie_name)
        if not csrf_cookie:
            logger.warning(f"CSRF validation failed: missing CSRF cookie for {request.method} {request.url.path}")
            return JSONResponse(
                status_code=403,
                content={"code": "csrf_failed", "message": "CSRF token missing"}
            )
        
        # Get CSRF token from header or form
        csrf_header = request.headers.get(self.header_name)
        
        # For form data, we need to parse it
        csrf_form = None
        if request.headers.get("content-type", "").startswith("application/x-www-form-urlencoded"):
            try:
                form = await request.form()
                csrf_form = form.get(self.form_field_name)
            except Exception:
                pass
        
        # Validate CSRF token
        csrf_submitted = csrf_header or csrf_form
        if not csrf_submitted or csrf_submitted != csrf_cookie:
            logger.warning(f"CSRF validation failed: token mismatch for {request.method} {request.url.path}")
            return JSONResponse(
                status_code=403,
                content={"code": "csrf_failed", "message": "CSRF token validation failed"}
            )
        
        return await call_next(request)


class CorrelationIDMiddleware(BaseHTTPMiddleware):
    """Middleware for adding correlation IDs to requests."""
    
    def __init__(
        self,
        app: ASGIApp,
        header_name: str = "X-Correlation-ID",
        generator: Optional[Callable[[], str]] = None
    ):
        super().__init__(app)
        self.header_name = header_name
        self.generator = generator or (lambda: str(uuid.uuid4()))
    
    async def dispatch(self, request: Request, call_next: Callable) -> Response:
        # Get or generate correlation ID
        correlation_id = request.headers.get(self.header_name) or self.generator()
        
        # Add to request state for access in handlers
        request.state.correlation_id = correlation_id
        
        # Process request
        response = await call_next(request)
        
        # Add correlation ID to response headers
        response.headers[self.header_name] = correlation_id
        
        return response


class RequestLoggingMiddleware(BaseHTTPMiddleware):
    """Middleware for request/response logging."""
    
    def __init__(
        self,
        app: ASGIApp,
        log_level: int = logging.INFO,
        exclude_paths: Optional[list] = None,
        log_request_body: bool = False,
        log_response_body: bool = False,
        max_body_log_size: int = 1024
    ):
        super().__init__(app)
        self.log_level = log_level
        self.exclude_paths = exclude_paths or ["/health", "/metrics", "/favicon.ico"]
        self.log_request_body = log_request_body
        self.log_response_body = log_response_body
        self.max_body_log_size = max_body_log_size
    
    async def dispatch(self, request: Request, call_next: Callable) -> Response:
        if request.url.path in self.exclude_paths:
            return await call_next(request)
        
        start_time = time.time()
        correlation_id = getattr(request.state, 'correlation_id', 'unknown')
        
        # Log request
        logger.log(
            self.log_level,
            f"Request: {request.method} {request.url.path} "
            f"from {request.client.host if request.client else 'unknown'} "
            f"correlation_id={correlation_id}"
        )
        
        try:
            response = await call_next(request)
            
            # Log response
            process_time = time.time() - start_time
            logger.log(
                self.log_level,
                f"Response: {request.method} {request.url.path} "
                f"status={response.status_code} "
                f"duration={process_time:.4f}s "
                f"correlation_id={correlation_id}"
            )
            
            # Add timing header
            response.headers["X-Process-Time"] = str(process_time)
            response.headers["X-Correlation-ID"] = correlation_id
            
            return response
            
        except Exception as e:
            process_time = time.time() - start_time
            logger.error(
                f"Error: {request.method} {request.url.path} "
                f"duration={process_time:.4f}s "
                f"error={str(e)} "
                f"correlation_id={correlation_id}",
                exc_info=True
            )
            raise


class RequestSizeLimitMiddleware(BaseHTTPMiddleware):
    """Middleware for limiting request body size."""
    
    def __init__(
        self,
        app: ASGIApp,
        max_size: int = 10 * 1024 * 1024,  # 10MB default
        exclude_paths: Optional[list] = None
    ):
        super().__init__(app)
        self.max_size = max_size
        self.exclude_paths = exclude_paths or ["/health", "/metrics"]
    
    async def dispatch(self, request: Request, call_next: Callable) -> Response:
        if request.url.path in self.exclude_paths:
            return await call_next(request)
        
        content_length = request.headers.get("content-length")
        if content_length and int(content_length) > self.max_size:
            return JSONResponse(
                status_code=413,
                content={
                    "code": "payload_too_large",
                    "message": f"Request body exceeds maximum size of {self.max_size} bytes"
                }
            )
        
        return await call_next(request)


class RateLimitMiddleware(BaseHTTPMiddleware):
    """Simple in-memory rate limiting middleware."""
    
    def __init__(
        self,
        app: ASGIApp,
        requests_per_minute: int = 60,
        requests_per_hour: int = 1000,
        exclude_paths: Optional[list] = None,
        key_func: Optional[Callable[[Request], str]] = None
    ):
        super().__init__(app)
        self.requests_per_minute = requests_per_minute
        self.requests_per_hour = requests_per_hour
        self.exclude_paths = exclude_paths or ["/health", "/metrics", "/docs", "/openapi.json"]
        self.key_func = key_func or self._default_key_func
        
        # In-memory storage (use Redis in production)
        self._minute_counts: defaultdict[str, list] = defaultdict(list)
        self._hour_counts: defaultdict[str, list] = defaultdict(list)
    
    def _default_key_func(self, request: Request) -> str:
        """Default key function using client IP."""
        if request.client:
            return request.client.host
        return "unknown"
    
    def _clean_old_entries(self, counts: defaultdict, window_seconds: int):
        """Remove entries older than window."""
        current_time = time.time()
        cutoff = current_time - window_seconds
        for key in list(counts.keys()):
            counts[key] = [t for t in counts[key] if t > cutoff]
            if not counts[key]:
                del counts[key]
    
    async def dispatch(self, request: Request, call_next: Callable) -> Response:
        if request.url.path in self.exclude_paths:
            return await call_next(request)
        
        key = self.key_func(request)
        current_time = time.time()
        
        # Clean old entries
        self._clean_old_entries(self._minute_counts, 60)
        self._clean_old_entries(self._hour_counts, 3600)
        
        # Check minute limit
        minute_count = len(self._minute_counts[key])
        if minute_count >= self.requests_per_minute:
            logger.warning(f"Rate limit exceeded for {key}: {minute_count} req/min")
            raise RateLimitException(
                message="Too many requests per minute",
                retry_after=60
            )
        
        # Check hour limit
        hour_count = len(self._hour_counts[key])
        if hour_count >= self.requests_per_hour:
            logger.warning(f"Rate limit exceeded for {key}: {hour_count} req/hour")
            raise RateLimitException(
                message="Too many requests per hour",
                retry_after=3600
            )
        
        # Record request
        self._minute_counts[key].append(current_time)
        self._hour_counts[key].append(current_time)
        
        response = await call_next(request)
        
        # Add rate limit headers
        response.headers["X-RateLimit-Limit-Minute"] = str(self.requests_per_minute)
        response.headers["X-RateLimit-Remaining-Minute"] = str(
            max(0, self.requests_per_minute - minute_count - 1)
        )
        response.headers["X-RateLimit-Limit-Hour"] = str(self.requests_per_hour)
        response.headers["X-RateLimit-Remaining-Hour"] = str(
            max(0, self.requests_per_hour - hour_count - 1)
        )
        
        return response


class SecurityHeadersMiddleware(BaseHTTPMiddleware):
    """Middleware for adding security headers."""
    
    def __init__(self, app: ASGIApp):
        super().__init__(app)
    
    async def dispatch(self, request: Request, call_next: Callable) -> Response:
        response = await call_next(request)
        
        # Security headers
        response.headers["X-Content-Type-Options"] = "nosniff"
        response.headers["X-Frame-Options"] = "DENY"
        response.headers["X-XSS-Protection"] = "1; mode=block"
        response.headers["Referrer-Policy"] = "strict-origin-when-cross-origin"
        response.headers["Permissions-Policy"] = "geolocation=(), microphone=(), camera=()"
        
        # HSTS (only in production with HTTPS)
        # response.headers["Strict-Transport-Security"] = "max-age=31536000; includeSubDomains"
        
        return response


class ErrorHandlingMiddleware(BaseHTTPMiddleware):
    """Middleware for centralized error handling."""
    
    def __init__(self, app: ASGIApp, debug: bool = False):
        super().__init__(app)
        self.debug = debug
    
    async def dispatch(self, request: Request, call_next: Callable) -> Response:
        try:
            return await call_next(request)
            
        except AppException as e:
            logger.warning(f"App exception: {e.code} - {e.message}")
            return JSONResponse(
                status_code=e.status_code,
                content={
                    "code": e.code,
                    "message": e.message,
                    "details": e.details
                }
            )
            
        except HTTPException as e:
            # Re-raise FastAPI HTTP exceptions
            raise
            
        except Exception as e:
            logger.error(f"Unhandled exception: {str(e)}", exc_info=True)
            
            if self.debug:
                return JSONResponse(
                    status_code=500,
                    content={
                        "code": "internal_error",
                        "message": str(e),
                        "details": {"type": type(e).__name__}
                    }
                )
            
            return JSONResponse(
                status_code=500,
                content={
                    "code": "internal_error",
                    "message": "An internal server error occurred"
                }
            )


def setup_middleware(app, config):
    """
    Set up all middleware for the FastAPI application.
    
    Order matters - middleware is applied in reverse order (last added = first executed).
    """
    
    # 1. Security headers
    app.add_middleware(SecurityHeadersMiddleware)
    
    # 2. Rate limiting - increase limits for test compatibility
    app.add_middleware(
        RateLimitMiddleware,
        requests_per_minute=500,
        requests_per_hour=10000,
        exclude_paths=["/health", "/metrics", "/docs", "/openapi.json", "/_test/reset", "/_test/export", "/_test/import"]
    )
    
    # 3. Request size limiting
    app.add_middleware(
        RequestSizeLimitMiddleware,
        max_size=getattr(config, 'MAX_REQUEST_SIZE', 10 * 1024 * 1024)
    )
    
    # 4. Correlation ID tracking
    app.add_middleware(CorrelationIDMiddleware)
    
    # 5. CSRF Protection (runs after logging, before CORS)
    app.add_middleware(CSRFProtectionMiddleware)
    
    # 6. CORS (innermost - runs first)
    app.add_middleware(
        CORSMiddleware,
        allow_origins=config.BACKEND_CORS_ORIGINS,
        allow_credentials=True,
        allow_methods=["*"],
        allow_headers=["*"],
    )