from typing import Optional
from fastapi import Depends, HTTPException, Header, Request, Response
from app.storage import storage
from app.validation import create_error_response
from app.config import get_settings
import secrets

settings = get_settings()

# Session cookie name
SESSION_COOKIE_NAME = "pocketful_session"
CSRF_COOKIE_NAME = "pocketful_csrf"
CSRF_HEADER_NAME = "X-CSRF-Token"

def generate_csrf_token() -> str:
    """Generate a secure CSRF token."""
    return secrets.token_urlsafe(32)

def set_session_cookie(response: Response, token: str, csrf_token: str) -> None:
    """Set session and CSRF cookies with secure settings."""
    # Session cookie - HttpOnly, Secure, SameSite=Lax
    response.set_cookie(
        key=SESSION_COOKIE_NAME,
        value=token,
        httponly=True,
        secure=not settings.DEBUG,  # Secure in production
        samesite="lax",
        max_age=60 * 60 * 24 * 30,  # 30 days
        path="/"
    )
    # CSRF cookie - not HttpOnly so JavaScript can read it for double-submit
    response.set_cookie(
        key=CSRF_COOKIE_NAME,
        value=csrf_token,
        httponly=False,  # JavaScript needs to read this
        secure=not settings.DEBUG,
        samesite="lax",
        max_age=60 * 60 * 24 * 30,
        path="/"
    )

def clear_session_cookies(response: Response) -> None:
    """Clear session and CSRF cookies."""
    response.delete_cookie(SESSION_COOKIE_NAME, path="/")
    response.delete_cookie(CSRF_COOKIE_NAME, path="/")

def get_current_user(
    request: Request,
    authorization: Optional[str] = Header(None)
) -> str:
    """
    Get current user from either Bearer token or session cookie.
    Priority: Bearer token > Session cookie
    """
    # Try Bearer token first
    if authorization and authorization.startswith("Bearer "):
        token = authorization[7:]
        user = storage.get_user_by_token(token)
        if user:
            return user.id
    
    # Try session cookie
    session_token = request.cookies.get(SESSION_COOKIE_NAME)
    if session_token:
        user = storage.get_user_by_token(session_token)
        if user:
            return user.id
    
    raise HTTPException(
        status_code=401, 
        detail=create_error_response("unauthenticated", "Missing or invalid token")
    )

def get_current_user_optional(
    request: Request,
    authorization: Optional[str] = Header(None)
) -> Optional[str]:
    """
    Get current user from either Bearer token or session cookie (optional).
    Returns None if not authenticated.
    """
    # Try Bearer token first
    if authorization and authorization.startswith("Bearer "):
        token = authorization[7:]
        user = storage.get_user_by_token(token)
        if user:
            return user.id
    
    # Try session cookie
    session_token = request.cookies.get(SESSION_COOKIE_NAME)
    if session_token:
        user = storage.get_user_by_token(session_token)
        if user:
            return user.id
    
    return None

def get_csrf_token(request: Request) -> str:
    """
    Get CSRF token from request - either from cookie or header.
    For double-submit cookie pattern, token should be in both cookie and header/form.
    """
    # Check header first (for AJAX requests)
    csrf_header = request.headers.get(CSRF_HEADER_NAME)
    if csrf_header:
        return csrf_header
    
    # Check cookie (for form submissions)
    csrf_cookie = request.cookies.get(CSRF_COOKIE_NAME)
    if csrf_cookie:
        return csrf_cookie
    
    # Generate new token if none exists
    return generate_csrf_token()

def validate_csrf_token(request: Request) -> bool:
    """
    Validate CSRF token using double-submit cookie pattern.
    Token must be present in both cookie and header/form.
    """
    # Skip CSRF validation for safe methods
    if request.method in ("GET", "HEAD", "OPTIONS"):
        return True
    
    csrf_cookie = request.cookies.get(CSRF_COOKIE_NAME)
    if not csrf_cookie:
        return False
    
    # Check header
    csrf_header = request.headers.get(CSRF_HEADER_NAME)
    if csrf_header and csrf_header == csrf_cookie:
        return True
    
    # Check form data (for form submissions)
    # This will be checked in form parsing
    return False

async def get_csrf_from_form(request: Request) -> Optional[str]:
    """Extract CSRF token from form data."""
    try:
        form = await request.form()
        return form.get("csrf_token")
    except Exception:
        return None


def wants_html(request: Request) -> bool:
    """Check if client explicitly prefers HTML over JSON.
    Only return True if text/html is explicitly in Accept header.
    """
    accept = request.headers.get("accept", "")
    # DEBUG
    print(f"DEBUG wants_html: path={request.url.path}, accept={accept}")
    # Only treat as HTML request if explicitly requesting text/html
    # Default to JSON for API clients
    result = "text/html" in accept and "application/json" not in accept
    print(f"DEBUG wants_html: result={result}")
    return result