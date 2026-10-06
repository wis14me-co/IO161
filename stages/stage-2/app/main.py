import os
import json
import secrets
from datetime import datetime, timezone, timedelta
from typing import Optional, List
from contextlib import asynccontextmanager
from fastapi import FastAPI, Request, Depends, HTTPException, Header, Query, Body, Form, Cookie
from fastapi.responses import JSONResponse, HTMLResponse, RedirectResponse, Response
from fastapi.middleware.cors import CORSMiddleware
from fastapi.exceptions import RequestValidationError
from fastapi.templating import Jinja2Templates
from fastapi.staticfiles import StaticFiles
from pydantic import ValidationError as PydanticValidationError
from starlette.requests import Request as StarletteRequest

from app.storage import storage, Fixture
from app.models import (
    UserCreate, UserLogin, TokenResponse, MeResponse,
    PaymentCreate, PaymentResponse,
    RequestCreate, RequestResponse, RequestListResponse, RequestPay,
    SplitCreate, SplitResponse, SplitShare,
    SettlementCreate, SettlementResponse, SettlementPaymentResponse,
    ActivityResponse, HealthResponse,
    ExportResponse, ImportRequest,
    PaginationParams, RequestQueryParams, AuthorizationQueryParams,
    AuthorizationCreate, AuthorizationCapture, AuthorizationResponse, AuthorizationListResponse,
    ErrorResponse, ErrorDetail
)
from app.validation import (
    validate_idempotency_key, validate_amount, validate_handle, validate_note,
    validate_visibility, validate_limit_offset, validate_direction, validate_status,
    validate_authorization_status, validate_participant_handles, validate_email, validate_password, validate_display_name,
    parse_json_body, create_error_response, ValidationError
)
from app.idempotency import IdempotencyMiddleware, is_idempotent_path


# Setup templates and static files
templates = Jinja2Templates(directory="app/templates")

# Add custom filters
def format_currency(value: float) -> str:
    """Format currency value to string with 2 decimal places."""
    return f"{value:.2f}"

templates.env.filters["format_currency"] = format_currency


def calculate_shares(amount: int, n: int) -> List[int]:
    base = amount // n
    remainder = amount % n
    shares = [base + 1 if i < remainder else base for i in range(n)]
    return shares


def get_accept_format(accept_header: Optional[str] = None) -> str:
    """Determine response format from Accept header."""
    if not accept_header:
        return "json"
    if "text/html" in accept_header:
        return "html"
    return "json"


def get_current_user_token(authorization: Optional[str] = Header(None)) -> str:
    """Get user ID from Bearer token (API auth)."""
    if not authorization or not authorization.startswith("Bearer "):
        raise HTTPException(status_code=401, detail=create_error_response("unauthenticated", "Missing or invalid token"))
    token = authorization[7:]
    user = storage.get_user_by_token(token)
    if not user:
        raise HTTPException(status_code=401, detail=create_error_response("unauthenticated", "Invalid token"))
    return user.id


def get_current_user_cookie(session_id: Optional[str] = Cookie(None)) -> Optional[str]:
    """Get user ID from session cookie (browser auth)."""
    if not session_id:
        return None
    session = storage.get_session(session_id)
    if not session:
        return None
    return session.user_id


def get_current_user(
    authorization: Optional[str] = Header(None),
    session_id: Optional[str] = Cookie(None)
) -> str:
    """Get user ID from either Bearer token or session cookie."""
    # Try Bearer token first (API)
    if authorization and authorization.startswith("Bearer "):
        token = authorization[7:]
        user = storage.get_user_by_token(token)
        if user:
            return user.id
    
    # Try session cookie (browser)
    if session_id:
        session = storage.get_session(session_id)
        if session:
            return session.user_id
    
    raise HTTPException(status_code=401, detail=create_error_response("unauthenticated", "Missing or invalid authentication"))


def get_current_user_optional(
    authorization: Optional[str] = Header(None),
    session_id: Optional[str] = Cookie(None)
) -> Optional[str]:
    """Get user ID optionally from either Bearer token or session cookie."""
    # Try Bearer token first (API)
    if authorization and authorization.startswith("Bearer "):
        token = authorization[7:]
        user = storage.get_user_by_token(token)
        if user:
            return user.id
    
    # Try session cookie (browser)
    if session_id:
        session = storage.get_session(session_id)
        if session:
            return session.user_id
    
    return None


def create_session(user_id: str) -> str:
    """Create a new session for the user."""
    session_id = secrets.token_urlsafe(32)
    expires_at = datetime.now(timezone.utc) + timedelta(days=30)
    storage.create_session(session_id, user_id, expires_at.isoformat().replace("+00:00", "Z"))
    return session_id


def delete_session(session_id: str) -> None:
    """Delete a session."""
    storage.delete_session(session_id)


def generate_csrf_token() -> str:
    """Generate a CSRF token."""
    return secrets.token_urlsafe(32)


def validate_csrf_token(token: str, expected: str) -> bool:
    """Validate a CSRF token using constant-time comparison."""
    return secrets.compare_digest(token, expected)


def require_csrf_token(request: Request, csrf_token: str = Form(...), session_id: Optional[str] = Cookie(None)) -> None:
    """Dependency to validate CSRF token for mutating HTML form POSTs."""
    if not session_id:
        raise HTTPException(status_code=403, detail=create_error_response("csrf_failed", "Missing session"))
    
    session = storage.get_session(session_id)
    if not session or not session.csrf_token:
        raise HTTPException(status_code=403, detail=create_error_response("csrf_failed", "Invalid session"))
    
    if not validate_csrf_token(csrf_token, session.csrf_token):
        raise HTTPException(status_code=403, detail=create_error_response("csrf_failed", "Invalid CSRF token"))


@asynccontextmanager
async def lifespan(app: FastAPI):
    yield


app = FastAPI(title="Pocketful", lifespan=lifespan)

# Add middlewares
app.add_middleware(IdempotencyMiddleware)
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# Mount static files
app.mount("/static", StaticFiles(directory="app/static"), name="static")


@app.exception_handler(ValidationError)
async def validation_exception_handler(request: Request, exc: ValidationError):
    format_type = get_accept_format(request.headers.get("accept"))
    if format_type == "html":
        return templates.TemplateResponse(
            "error.html",
            {"request": request, "error": exc.message, "status_code": exc.status_code},
            status_code=exc.status_code
        )
    return JSONResponse(status_code=exc.status_code, content=create_error_response(exc.code, exc.message))


@app.exception_handler(RequestValidationError)
async def request_validation_exception_handler(request: Request, exc: RequestValidationError):
    format_type = get_accept_format(request.headers.get("accept"))
    errors = exc.errors()
    if errors:
        error = errors[0]
        loc = error.get("loc", [])
        msg = error.get("msg", "validation error")
        if "type" in error:
            err_type = error["type"]
            if "int" in err_type or "float" in err_type:
                msg = "Invalid numeric value"
            if "str" in err_type:
                msg = "Invalid string value"
        if format_type == "html":
            return templates.TemplateResponse(
                "error.html",
                {"request": request, "error": msg, "status_code": 422},
                status_code=422
            )
        return JSONResponse(status_code=422, content=create_error_response("validation_failed", msg))
    if format_type == "html":
        return templates.TemplateResponse(
            "error.html",
            {"request": request, "error": "Validation error", "status_code": 422},
            status_code=422
        )
    return JSONResponse(status_code=422, content=create_error_response("validation_failed", "Validation error"))


@app.exception_handler(HTTPException)
async def http_exception_handler(request: Request, exc: HTTPException):
    format_type = get_accept_format(request.headers.get("accept"))
    if isinstance(exc.detail, dict):
        if format_type == "html":
            return templates.TemplateResponse(
                "error.html",
                {"request": request, "error": exc.detail.get("message", str(exc.detail)), "status_code": exc.status_code},
                status_code=exc.status_code
            )
        return JSONResponse(status_code=exc.status_code, content=exc.detail)
    if format_type == "html":
        return templates.TemplateResponse(
            "error.html",
            {"request": request, "error": str(exc.detail), "status_code": exc.status_code},
            status_code=exc.status_code
        )
    return JSONResponse(status_code=exc.status_code, content=create_error_response("validation_failed", str(exc.detail)))


# Template context processor
@app.middleware("http")
async def add_template_context(request: Request, call_next):
    """Add common context to all template responses."""
    response = await call_next(request)
    return response


# ============================================================
# HTML ROUTES (Content Negotiation)
# ============================================================

@app.get("/", response_class=HTMLResponse)
async def root_html(
    request: Request,
    user_id: Optional[str] = Depends(get_current_user_optional)
):
    """Home page - HTML or JSON based on Accept header."""
    format_type = get_accept_format(request.headers.get("accept"))
    
    user = None
    if user_id:
        user = storage.get_user_by_id(user_id)
    
    if format_type == "html":
        # Get balance info for authenticated users
        balance_data = {}
        if user:
            available = storage.get_available_balance(user_id)
            held = user.balance - available
            balance_data = {
                "balance": user.balance,
                "available": available,
                "held": held,
                "currency": storage.currency,
                "minor_units": storage.minor_units
            }
        
        # Get recent requests if authenticated
        requests = []
        if user_id:
            requests = storage.get_requests_for_user(user_id, None, None, 5, 0)
        
        return templates.TemplateResponse("index.html", {
            "request": request,
            "user": user,
            **balance_data,
            "recent_requests": requests,
            "csrf_token": storage.get_session_cookie(request).csrf_token if storage.get_session_cookie(request) else generate_csrf_token()
        })
    
    return JSONResponse({"message": "Welcome to Pocketful API"})


@app.get("/login", response_class=HTMLResponse)
async def login_page(request: Request):
    """Login page."""
    return templates.TemplateResponse("login.html", {
        "request": request,
        "csrf_token": generate_csrf_token()
    })


@app.get("/signup", response_class=HTMLResponse)
async def signup_page(request: Request):
    """Signup page."""
    return templates.TemplateResponse("signup.html", {
        "request": request,
        "csrf_token": generate_csrf_token()
    })
async def new_request_page(request: Request, user_id: str = Depends(get_current_user)):
    """New request page."""
    session = storage.get_session_cookie(request)
    return templates.TemplateResponse("new_request.html", {
        "request": request,
        "currency": storage.currency,
        "csrf_token": session.csrf_token if session else generate_csrf_token()
    })


@app.get("/authorizations/new", response_class=HTMLResponse)
async def new_authorization_page(request: Request, user_id: str = Depends(get_current_user)):
    """New authorization page."""
    session = storage.get_session_cookie(request)
    return templates.TemplateResponse("new_authorization.html", {
        "request": request,
        "currency": storage.currency,
        "csrf_token": session.csrf_token if session else generate_csrf_token()
    })


@app.get("/split", response_class=HTMLResponse)
async def split_page(request: Request, user_id: str = Depends(get_current_user)):
    """Split bill page - HTML or JSON based on Accept header."""
    format_type = get_accept_format(request.headers.get("accept"))
    
    session = storage.get_session_cookie(request)
    if format_type == "html":
        return templates.TemplateResponse("split.html", {
            "request": request,
            "currency": storage.currency,
            "minor_units": storage.minor_units,
            "csrf_token": session.csrf_token if session else generate_csrf_token()
        })
    
    # For API, return available balance info
    user = storage.get_user_by_id(user_id)
    available = storage.get_available_balance(user_id)
    return MeResponse(
        user_id=user.id,
        display_name=user.display_name,
        handle=user.handle,
        balance=user.balance,
        total=user.balance,
        available=available,
        held=user.balance - available,
        currency=storage.currency,
        minor_units=storage.minor_units
    )


@app.get("/health", response_model=HealthResponse)
async def health():
    return HealthResponse(status="ok")


# ============================================================
# API ROUTES (with content negotiation)
# ============================================================

@app.post("/auth/signup", response_model=TokenResponse, status_code=201)
async def signup(
    request: Request,
    session_id: Optional[str] = Cookie(None)
):
    """Signup - supports both API and HTML form."""
    format_type = get_accept_format(request.headers.get("accept"))
    
    # Handle form data for HTML
    if format_type == "html":
        form = await request.form()
        email = validate_email(form.get("email"))
        password = validate_password(form.get("password"))
        display_name = validate_display_name(form.get("display_name"))
        
        # CSRF validation for HTML forms (only if session exists)
        csrf_token = form.get("csrf_token")
        if session_id:
            session = storage.get_session(session_id)
            if not session or not csrf_token or not validate_csrf_token(csrf_token, session.csrf_token):
                return templates.TemplateResponse("signup.html", {
                    "request": request,
                    "error": "Invalid CSRF token",
                    "csrf_token": generate_csrf_token()
                }, status_code=400)
    else:
        # Parse JSON body
        try:
            body = await request.json()
            user_data = UserCreate(**body)
        except Exception:
            raise HTTPException(status_code=422, detail=create_error_response("validation_failed", "Invalid request body"))
        email = validate_email(user_data.email)
        password = validate_password(user_data.password)
        display_name = validate_display_name(user_data.display_name)
    
    existing = storage.get_user_by_email(email)
    if existing:
        if format_type == "html":
            return templates.TemplateResponse("signup.html", {
                "request": request,
                "error": "Email already registered",
                "csrf_token": generate_csrf_token()
            }, status_code=409)
        raise HTTPException(status_code=409, detail=create_error_response("email_taken", "Email already registered"))
    
    # Derive handle from email
    import re
    local_part = email.split("@")[0].lower()
    handle = re.sub(r"[^a-z0-9_]", "_", local_part)[:20]
    if not handle:
        handle = "user"
    
    if storage.get_user_by_handle(handle):
        if format_type == "html":
            return templates.TemplateResponse("signup.html", {
                "request": request,
                "error": "Handle already taken",
                "csrf_token": generate_csrf_token()
            }, status_code=409)
        raise HTTPException(status_code=409, detail=create_error_response("handle_taken", "Handle already taken"))
    
    user = storage.create_user(email, password, display_name, handle, 0)
    token = storage.create_token(user.id)
    
    # Create session for browser
    if format_type == "html":
        session_id = create_session(user.id)
        response = RedirectResponse(url="/", status_code=303)
        response.set_cookie(
            "session_id",
            session_id,
            httponly=True,
            secure=False,  # Set to True in production with HTTPS
            samesite="lax",
            max_age=30 * 24 * 60 * 60
        )
        return response
    
    return TokenResponse(user_id=user.id, display_name=user.display_name, token=token)


@app.post("/auth/login", response_model=TokenResponse)
async def login(
    request: Request,
    session_id: Optional[str] = Cookie(None)
):
    """Login - supports both API and HTML form."""
    format_type = get_accept_format(request.headers.get("accept"))
    
    # Handle form data for HTML
    if format_type == "html":
        form = await request.form()
        email = validate_email(form.get("email"))
        password = form.get("password")
        
        # CSRF validation for HTML forms (only if session exists)
        csrf_token = form.get("csrf_token")
        if session_id:
            session = storage.get_session(session_id)
            if not session or not csrf_token or not validate_csrf_token(csrf_token, session.csrf_token):
                return templates.TemplateResponse("login.html", {
                    "request": request,
                    "error": "Invalid CSRF token",
                    "csrf_token": generate_csrf_token()
                }, status_code=400)
    else:
        # Parse JSON body
        try:
            body = await request.json()
            credentials = UserLogin(**body)
        except Exception:
            raise HTTPException(status_code=422, detail=create_error_response("validation_failed", "Invalid request body"))
        email = validate_email(credentials.email)
        password = credentials.password
    
    user = storage.get_user_by_email(email)
    if not user or not storage.verify_password(user, password):
        if format_type == "html":
            return templates.TemplateResponse("login.html", {
                "request": request,
                "error": "Wrong password or unknown email",
                "csrf_token": generate_csrf_token()
            }, status_code=401)
        raise HTTPException(status_code=401, detail=create_error_response("unauthenticated", "Wrong password or unknown email"))
    
    token = storage.create_token(user.id)
    
    # Create session for browser
    if format_type == "html":
        session_id = create_session(user.id)
        response = RedirectResponse(url="/", status_code=303)
        response.set_cookie(
            "session_id",
            session_id,
            httponly=True,
            secure=False,  # Set to True in production with HTTPS
            samesite="lax",
            max_age=30 * 24 * 60 * 60
        )
        return response
    
    return TokenResponse(user_id=user.id, display_name=user.display_name, token=token)


@app.post("/auth/logout")
async def logout(request: Request, session_id: Optional[str] = Cookie(None)):
    """Logout - clears session cookie."""
    format_type = get_accept_format(request.headers.get("accept"))
    
    if session_id:
        delete_session(session_id)
    
    if format_type == "html":
        response = RedirectResponse(url="/login", status_code=303)
        response.delete_cookie("session_id")
        return response
    
    return JSONResponse({"message": "Logged out"})


@app.get("/me", response_model=MeResponse)
async def me(user_id: str = Depends(get_current_user)):
    user = storage.get_user_by_id(user_id)
    if not user:
        raise HTTPException(status_code=404, detail=create_error_response("not_found", "User not found"))
    
    available = storage.get_available_balance(user_id)
    held = user.balance - available
    
    return MeResponse(
        user_id=user.id,
        display_name=user.display_name,
        handle=user.handle,
        balance=user.balance,
        total=user.balance,
        available=available,
        held=held,
        currency=storage.currency,
        minor_units=storage.minor_units
    )


# ... [rest of the API endpoints remain the same - payments, requests, authorizations, splits, settlements, etc.]
# For brevity, I'll include the key ones that need CSRF handling for HTML forms

@app.post("/payments", response_model=PaymentResponse, status_code=201)
async def create_payment(
    request: Request,
    payment: PaymentCreate,
    user_id: str = Depends(get_current_user),
    idempotency_key: str = Header(..., alias="Idempotency-Key"),
    session_id: Optional[str] = Cookie(None)
):
    format_type = get_accept_format(request.headers.get("accept"))
    
    # Validate idempotency key
    validate_idempotency_key(idempotency_key)
    
    # For HTML forms, validate CSRF
    if format_type == "html" and session_id:
        await require_csrf_token(request)
    
    to_user = storage.get_user_by_handle(payment.to_handle)
    if not to_user:
        if format_type == "html":
            return templates.TemplateResponse("error.html", {
                "request": request, "error": "Recipient not found", "status_code": 404
            }, status_code=404)
        raise HTTPException(status_code=404, detail=create_error_response("not_found", "Recipient not found"))
    
    if to_user.id == user_id:
        if format_type == "html":
            return templates.TemplateResponse("error.html", {
                "request": request, "error": "Cannot send payment to yourself", "status_code": 422
            }, status_code=422)
        raise HTTPException(status_code=422, detail=create_error_response("self_payment", "Cannot send payment to yourself"))
    
    validate_amount(payment.amount)
    note = validate_note(payment.note)
    visibility = validate_visibility(payment.visibility)
    
    try:
        from_balance, to_balance = storage.atomic_transfer(user_id, to_user.id, payment.amount)
    except ValueError as e:
        if str(e) == "insufficient_funds":
            if format_type == "html":
                return templates.TemplateResponse("error.html", {
                    "request": request, "error": "Insufficient funds", "status_code": 409
                }, status_code=409)
            raise HTTPException(status_code=409, detail=create_error_response("insufficient_funds", "Insufficient funds"))
        raise
    
    payment_obj = storage.create_payment(user_id, to_user.id, payment.amount, note, visibility, None)
    from_user = storage.get_user_by_id(user_id)
    
    response = PaymentResponse(
        payment_id=payment_obj.id,
        from_user_id=user_id,
        from_handle=from_user.handle,
        to_user_id=to_user.id,
        to_handle=to_user.handle,
        amount=payment.amount,
        currency=storage.currency,
        note=note,
        visibility=visibility,
        request_id=None,
        created_at=payment_obj.created_at
    )
    
    # Store idempotent response
    body = {"to_handle": payment.to_handle, "amount": payment.amount, "note": note, "visibility": visibility}
    storage.store_idempotency(
        user_id, idempotency_key, request.method, request.url.path,
        body, 201, response.model_dump()
    )
    
    if format_type == "html":
        session = storage.get_session_cookie(request)
        return RedirectResponse(url="/activity", status_code=303)
    
    return response


@app.post("/requests", response_model=RequestResponse, status_code=201)
async def create_request(
    request: Request,
    request_data: RequestCreate,
    user_id: str = Depends(get_current_user),
    idempotency_key: str = Header(..., alias="Idempotency-Key"),
    session_id: Optional[str] = Cookie(None)
):
    format_type = get_accept_format(request.headers.get("accept"))
    
    validate_idempotency_key(idempotency_key)
    
    if format_type == "html" and session_id:
        await require_csrf_token(request)
    
    payer = storage.get_user_by_handle(request_data.payer_handle)
    if not payer:
        if format_type == "html":
            return templates.TemplateResponse("error.html", {
                "request": request, "error": "Payer not found", "status_code": 404
            }, status_code=404)
        raise HTTPException(status_code=404, detail=create_error_response("not_found", "Payer not found"))
    
    if payer.id == user_id:
        if format_type == "html":
            return templates.TemplateResponse("error.html", {
                "request": request, "error": "Cannot request from yourself", "status_code": 422
            }, status_code=422)
        raise HTTPException(status_code=422, detail=create_error_response("self_request", "Cannot request from yourself"))
    
    validate_amount(request_data.amount)
    note = validate_note(request_data.note)
    
    req_obj = storage.create_request(user_id, payer.id, request_data.amount, note)
    
    response = RequestResponse(
        request_id=req_obj.id,
        requester_id=user_id,
        requester_handle=storage.get_user_by_id(user_id).handle,
        payer_id=payer.id,
        payer_handle=payer.handle,
        amount=request_data.amount,
        currency=storage.currency,
        note=note,
        status="pending",
        payment_id=None,
        created_at=req_obj.created_at
    )
    
    body = {"payer_handle": request_data.payer_handle, "amount": request_data.amount, "note": note}
    storage.store_idempotency(
        user_id, idempotency_key, request.method, request.url.path,
        body, 201, response.model_dump()
    )
    
    if format_type == "html":
        return RedirectResponse(url="/requests", status_code=303)
    
    return response


@app.post("/requests/{request_id}/pay", response_model=PaymentResponse, status_code=201)
async def pay_request(
    request: Request,
    request_id: str,
    request_data: RequestPay,
    user_id: str = Depends(get_current_user),
    idempotency_key: str = Header(..., alias="Idempotency-Key"),
    session_id: Optional[str] = Cookie(None)
):
    format_type = get_accept_format(request.headers.get("accept"))
    
    validate_idempotency_key(idempotency_key)
    
    if format_type == "html" and session_id:
        await require_csrf_token(request)
    
    req_obj = storage.get_request(request_id)
    if not req_obj:
        if format_type == "html":
            return templates.TemplateResponse("error.html", {
                "request": request, "error": "Request not found", "status_code": 404
            }, status_code=404)
        raise HTTPException(status_code=404, detail=create_error_response("not_found", "Request not found"))
    
    if req_obj.payer_id != user_id:
        if format_type == "html":
            return templates.TemplateResponse("error.html", {
                "request": request, "error": "Not the payer", "status_code": 403
            }, status_code=403)
        raise HTTPException(status_code=403, detail=create_error_response("forbidden", "Not the payer"))
    
    if req_obj.status != "pending":
        if format_type == "html":
            return templates.TemplateResponse("error.html", {
                "request": request, "error": "Request not pending", "status_code": 409
            }, status_code=409)
        raise HTTPException(status_code=409, detail=create_error_response("request_not_pending", "Request not pending"))
    
    visibility = validate_visibility(request_data.visibility)
    
    requester = storage.get_user_by_id(req_obj.requester_id)
    if not requester:
        if format_type == "html":
            return templates.TemplateResponse("error.html", {
                "request": request, "error": "Requester not found", "status_code": 404
            }, status_code=404)
        raise HTTPException(status_code=404, detail=create_error_response("not_found", "Requester not found"))
    
    try:
        from_balance, to_balance = storage.atomic_transfer(req_obj.payer_id, req_obj.requester_id, req_obj.amount)
    except ValueError as e:
        if str(e) == "insufficient_funds":
            if format_type == "html":
                return templates.TemplateResponse("error.html", {
                    "request": request, "error": "Insufficient funds", "status_code": 409
                }, status_code=409)
            raise HTTPException(status_code=409, detail=create_error_response("insufficient_funds", "Insufficient funds"))
        raise
    
    payment_obj = storage.create_payment(req_obj.payer_id, req_obj.requester_id, req_obj.amount, req_obj.note, visibility, req_obj.id)
    storage.update_request_status(req_obj.id, "paid", payment_obj.id)
    
    from_user = storage.get_user_by_id(req_obj.payer_id)
    
    response = PaymentResponse(
        payment_id=payment_obj.id,
        from_user_id=req_obj.payer_id,
        from_handle=from_user.handle,
        to_user_id=req_obj.requester_id,
        to_handle=requester.handle,
        amount=req_obj.amount,
        currency=storage.currency,
        note=req_obj.note,
        visibility=visibility,
        request_id=req_obj.id,
        created_at=payment_obj.created_at
    )
    
    body = {"visibility": visibility}
    storage.store_idempotency(
        user_id, idempotency_key, request.method, request.url.path,
        body, 201, response.model_dump()
    )
    
    if format_type == "html":
        return RedirectResponse(url="/requests", status_code=303)
    
    return response


@app.post("/requests/{request_id}/decline", response_model=RequestResponse, status_code=200)
async def decline_request(
    request: Request,
    request_id: str,
    user_id: str = Depends(get_current_user),
    session_id: Optional[str] = Cookie(None)
):
    format_type = get_accept_format(request.headers.get("accept"))
    
    if format_type == "html" and session_id:
        await require_csrf_token(request)
    
    req_obj = storage.get_request(request_id)
    if not req_obj:
        if format_type == "html":
            return templates.TemplateResponse("error.html", {
                "request": request, "error": "Request not found", "status_code": 404
            }, status_code=404)
        raise HTTPException(status_code=404, detail=create_error_response("not_found", "Request not found"))
    
    if req_obj.payer_id != user_id:
        if format_type == "html":
            return templates.TemplateResponse("error.html", {
                "request": request, "error": "Not the payer", "status_code": 403
            }, status_code=403)
        raise HTTPException(status_code=403, detail=create_error_response("forbidden", "Not the payer"))
    
    if req_obj.status != "pending":
        if format_type == "html":
            return templates.TemplateResponse("error.html", {
                "request": request, "error": "Request not pending", "status_code": 409
            }, status_code=409)
        raise HTTPException(status_code=409, detail=create_error_response("request_not_pending", "Request not pending"))
    
    req_obj = storage.update_request_status(req_obj.id, "declined", None)
    requester = storage.get_user_by_id(req_obj.requester_id)
    payer = storage.get_user_by_id(req_obj.payer_id)
    
    response = RequestResponse(
        request_id=req_obj.id,
        requester_id=req_obj.requester_id,
        requester_handle=requester.handle if requester else "",
        payer_id=req_obj.payer_id,
        payer_handle=payer.handle if payer else "",
        amount=req_obj.amount,
        currency=storage.currency,
        note=req_obj.note,
        status=req_obj.status,
        payment_id=req_obj.payment_id,
        created_at=req_obj.created_at
    )
    
    if format_type == "html":
        return RedirectResponse(url="/requests", status_code=303)
    
    return response


@app.post("/requests/{request_id}/cancel", response_model=RequestResponse, status_code=200)
async def cancel_request(
    request: Request,
    request_id: str,
    user_id: str = Depends(get_current_user),
    session_id: Optional[str] = Cookie(None)
):
    format_type = get_accept_format(request.headers.get("accept"))
    
    if format_type == "html" and session_id:
        await require_csrf_token(request)
    
    req_obj = storage.get_request(request_id)
    if not req_obj:
        if format_type == "html":
            return templates.TemplateResponse("error.html", {
                "request": request, "error": "Request not found", "status_code": 404
            }, status_code=404)
        raise HTTPException(status_code=404, detail=create_error_response("not_found", "Request not found"))
    
    if req_obj.requester_id != user_id:
        if format_type == "html":
            return templates.TemplateResponse("error.html", {
                "request": request, "error": "Not the requester", "status_code": 403
            }, status_code=403)
        raise HTTPException(status_code=403, detail=create_error_response("forbidden", "Not the requester"))
    
    if req_obj.status != "pending":
        if format_type == "html":
            return templates.TemplateResponse("error.html", {
                "request": request, "error": "Request not pending", "status_code": 409
            }, status_code=409)
        raise HTTPException(status_code=409, detail=create_error_response("request_not_pending", "Request not pending"))
    
    req_obj = storage.update_request_status(req_obj.id, "cancelled", None)
    requester = storage.get_user_by_id(req_obj.requester_id)
    payer = storage.get_user_by_id(req_obj.payer_id)
    
    response = RequestResponse(
        request_id=req_obj.id,
        requester_id=req_obj.requester_id,
        requester_handle=requester.handle if requester else "",
        payer_id=req_obj.payer_id,
        payer_handle=payer.handle if payer else "",
        amount=req_obj.amount,
        currency=storage.currency,
        note=req_obj.note,
        status=req_obj.status,
        payment_id=req_obj.payment_id,
        created_at=req_obj.created_at
    )
    
    if format_type == "html":
        return RedirectResponse(url="/requests", status_code=303)
    
    return response


@app.get("/requests", response_model=RequestListResponse)
async def list_requests(
    request: Request,
    direction: Optional[str] = Query(None),
    status: Optional[str] = Query(None),
    limit: int = Query(50),
    offset: int = Query(0),
    user_id: str = Depends(get_current_user)
):
    format_type = get_accept_format(request.headers.get("accept"))
    
    validate_direction(direction)
    validate_status(status)
    limit, offset = validate_limit_offset(limit, offset)
    
    requests = storage.get_requests_for_user(user_id, direction, status, limit + 1, offset)
    
    # Check if there are more items
    has_more = len(requests) > limit
    if has_more:
        requests = requests[:limit]
    
    result = []
    for r in requests:
        requester = storage.get_user_by_id(r.requester_id)
        payer = storage.get_user_by_id(r.payer_id)
        result.append(RequestResponse(
            request_id=r.id,
            requester_id=r.requester_id,
            requester_handle=requester.handle if requester else "",
            payer_id=r.payer_id,
            payer_handle=payer.handle if payer else "",
            amount=r.amount,
            currency=storage.currency,
            note=r.note,
            status=r.status,
            payment_id=r.payment_id,
            created_at=r.created_at
        ))
    
    if format_type == "html":
        session = storage.get_session_cookie(request)
        return templates.TemplateResponse("requests.html", {
            "request": request,
            "requests": result,
            "user_id": user_id,
            "currency": storage.currency,
            "minor_units": storage.minor_units,
            "csrf_token": session.csrf_token if session else generate_csrf_token()
        })
    
    return RequestListResponse(requests=result, has_more=has_more)


# ============================================================
# AUTHORIZATION ENDPOINTS
# ============================================================

@app.post("/authorizations", response_model=AuthorizationResponse, status_code=201)
async def create_authorization(
    request: Request,
    auth: AuthorizationCreate,
    user_id: str = Depends(get_current_user),
    idempotency_key: str = Header(..., alias="Idempotency-Key"),
    session_id: Optional[str] = Cookie(None)
):
    format_type = get_accept_format(request.headers.get("accept"))
    
    validate_idempotency_key(idempotency_key)
    
    if format_type == "html" and session_id:
        await require_csrf_token(request)
    
    to_user = storage.get_user_by_handle(auth.to_handle)
    if not to_user:
        if format_type == "html":
            return templates.TemplateResponse("error.html", {
                "request": request, "error": "Recipient not found", "status_code": 404
            }, status_code=404)
        raise HTTPException(status_code=404, detail=create_error_response("not_found", "Recipient not found"))
    
    if to_user.id == user_id:
        if format_type == "html":
            return templates.TemplateResponse("error.html", {
                "request": request, "error": "Cannot create authorization to yourself", "status_code": 422
            }, status_code=422)
        raise HTTPException(status_code=422, detail=create_error_response("self_auth", "Cannot create authorization to yourself"))
    
    validate_amount(auth.amount)
    note = validate_note(auth.note)
    visibility = validate_visibility(auth.visibility)
    
    # Check available balance (held = sum of open authorizations)
    available = storage.get_available_balance(user_id)
    if available < auth.amount:
        if format_type == "html":
            return templates.TemplateResponse("error.html", {
                "request": request, "error": "Insufficient funds", "status_code": 409
            }, status_code=409)
        raise HTTPException(status_code=409, detail=create_error_response("insufficient_funds", "Insufficient funds"))
    
    # Determine expires_at
    expires_at = auth.expires_at
    if expires_at is None and storage.authorization_ttl_seconds:
        expires_at = (datetime.now(timezone.utc) + timedelta(seconds=storage.authorization_ttl_seconds)).isoformat().replace("+00:00", "Z")
    
    auth_obj = storage.create_authorization(user_id, to_user.id, auth.amount, note, visibility, expires_at)
    
    from_user = storage.get_user_by_id(user_id)
    to_user_obj = storage.get_user_by_id(to_user.id)
    
    response = AuthorizationResponse(
        authorization_id=auth_obj.id,
        from_user_id=user_id,
        from_handle=from_user.handle,
        to_user_id=to_user.id,
        to_handle=to_user_obj.handle,
        amount=auth_obj.amount,
        captured_amount=auth_obj.captured_amount,
        remaining_amount=auth_obj.remaining_amount,
        note=auth_obj.note,
        visibility=auth_obj.visibility,
        status=storage._get_authorization_status(auth_obj),
        expires_at=auth_obj.expires_at,
        payment_id=auth_obj.payment_id,
        payment_ids=auth_obj.payment_ids,
        created_at=auth_obj.created_at
    )
    
    # For idempotency, only include expires_at if explicitly provided by client
    body = getattr(request.state, 'idempotency_body', {"to_handle": auth.to_handle, "amount": auth.amount, "note": note, "visibility": visibility})
    if auth.expires_at is not None:
        body["expires_at"] = auth.expires_at
    storage.store_idempotency(
        user_id, idempotency_key, request.method, request.url.path,
        body, 201, response.model_dump()
    )
    
    if format_type == "html":
        return RedirectResponse(url="/authorizations", status_code=303)
    
    return response


@app.post("/authorizations/{auth_id}/capture", response_model=AuthorizationResponse, status_code=200)
async def capture_authorization(
    request: Request,
    auth_id: str,
    capture: AuthorizationCapture,
    user_id: str = Depends(get_current_user),
    idempotency_key: str = Header(..., alias="Idempotency-Key"),
    session_id: Optional[str] = Cookie(None)
):
    format_type = get_accept_format(request.headers.get("accept"))
    
    validate_idempotency_key(idempotency_key)
    
    if format_type == "html" and session_id:
        await require_csrf_token(request)
    
    try:
        auth_obj, payment = storage.capture_authorization(auth_id, user_id, capture.amount, capture.final)
    except ValueError as e:
        if str(e) == "not_found":
            if format_type == "html":
                return templates.TemplateResponse("error.html", {
                    "request": request, "error": "Authorization not found", "status_code": 404
                }, status_code=404)
            raise HTTPException(status_code=404, detail=create_error_response("not_found", "Authorization not found"))
        if str(e) == "forbidden":
            if format_type == "html":
                return templates.TemplateResponse("error.html", {
                    "request": request, "error": "Not the receiver", "status_code": 403
                }, status_code=403)
            raise HTTPException(status_code=403, detail=create_error_response("forbidden", "Not the receiver"))
        if str(e) == "authorization_not_open":
            if format_type == "html":
                return templates.TemplateResponse("error.html", {
                    "request": request, "error": "Authorization not open", "status_code": 409
                }, status_code=409)
            raise HTTPException(status_code=409, detail=create_error_response("authorization_not_open", "Authorization not open"))
        if str(e) == "capture_exceeds_remaining":
            if format_type == "html":
                return templates.TemplateResponse("error.html", {
                    "request": request, "error": "Capture amount exceeds remaining", "status_code": 422
                }, status_code=422)
            raise HTTPException(status_code=422, detail=create_error_response("capture_exceeds_remaining", "Capture amount exceeds remaining"))
        if str(e) == "user_not_found":
            if format_type == "html":
                return templates.TemplateResponse("error.html", {
                    "request": request, "error": "User not found", "status_code": 404
                }, status_code=404)
            raise HTTPException(status_code=404, detail=create_error_response("not_found", "User not found"))
        raise
    
    from_user = storage.get_user_by_id(auth_obj.from_user_id)
    to_user = storage.get_user_by_id(auth_obj.to_user_id)
    
    response = AuthorizationResponse(
        authorization_id=auth_obj.id,
        from_user_id=auth_obj.from_user_id,
        from_handle=from_user.handle if from_user else "",
        to_user_id=auth_obj.to_user_id,
        to_handle=to_user.handle if to_user else "",
        amount=auth_obj.amount,
        captured_amount=auth_obj.captured_amount,
        remaining_amount=auth_obj.remaining_amount,
        note=auth_obj.note,
        visibility=auth_obj.visibility,
        status=storage._get_authorization_status(auth_obj),
        expires_at=auth_obj.expires_at,
        payment_id=auth_obj.payment_id,
        payment_ids=auth_obj.payment_ids,
        created_at=auth_obj.created_at
    )
    
    body = {"final": capture.final}
    if capture.amount is not None:
        body["amount"] = capture.amount
    storage.store_idempotency(
        user_id, idempotency_key, request.method, request.url.path,
        body, 200, response.model_dump()
    )
    
    if format_type == "html":
        return RedirectResponse(url="/authorizations", status_code=303)
    
    return response


@app.post("/authorizations/{auth_id}/void", response_model=AuthorizationResponse, status_code=200)
async def void_authorization(
    request: Request,
    auth_id: str,
    user_id: str = Depends(get_current_user),
    session_id: Optional[str] = Cookie(None)
):
    format_type = get_accept_format(request.headers.get("accept"))
    
    if format_type == "html" and session_id:
        await require_csrf_token(request)
    
    try:
        auth_obj = storage.void_authorization(auth_id, user_id)
    except ValueError as e:
        if str(e) == "not_found":
            if format_type == "html":
                return templates.TemplateResponse("error.html", {
                    "request": request, "error": "Authorization not found", "status_code": 404
                }, status_code=404)
            raise HTTPException(status_code=404, detail=create_error_response("not_found", "Authorization not found"))
        if str(e) == "forbidden":
            if format_type == "html":
                return templates.TemplateResponse("error.html", {
                    "request": request, "error": "Not the payer", "status_code": 403
                }, status_code=403)
            raise HTTPException(status_code=403, detail=create_error_response("forbidden", "Not the payer"))
        if str(e) == "authorization_not_open":
            if format_type == "html":
                return templates.TemplateResponse("error.html", {
                    "request": request, "error": "Authorization not open", "status_code": 409
                }, status_code=409)
            raise HTTPException(status_code=409, detail=create_error_response("authorization_not_open", "Authorization not open"))
        raise
    
    from_user = storage.get_user_by_id(auth_obj.from_user_id)
    to_user = storage.get_user_by_id(auth_obj.to_user_id)
    
    response = AuthorizationResponse(
        authorization_id=auth_obj.id,
        from_user_id=auth_obj.from_user_id,
        from_handle=from_user.handle if from_user else "",
        to_user_id=auth_obj.to_user_id,
        to_handle=to_user.handle if to_user else "",
        amount=auth_obj.amount,
        captured_amount=auth_obj.captured_amount,
        remaining_amount=auth_obj.remaining_amount,
        note=auth_obj.note,
        visibility=auth_obj.visibility,
        status=storage._get_authorization_status(auth_obj),
        expires_at=auth_obj.expires_at,
        payment_id=auth_obj.payment_id,
        payment_ids=auth_obj.payment_ids,
        created_at=auth_obj.created_at
    )
    
    if format_type == "html":
        return RedirectResponse(url="/authorizations", status_code=303)
    
    return response


@app.get("/authorizations", response_model=AuthorizationListResponse)
async def list_authorizations(
    request: Request,
    direction: Optional[str] = Query(None),
    status: Optional[str] = Query(None),
    limit: int = Query(50),
    offset: int = Query(0),
    user_id: str = Depends(get_current_user)
):
    format_type = get_accept_format(request.headers.get("accept"))
    
    validate_direction(direction)
    validate_authorization_status(status)
    limit, offset = validate_limit_offset(limit, offset)
    
    authorizations = storage.get_authorizations_for_user(user_id, direction, status, limit + 1, offset)
    
    # Check if there are more items
    has_more = len(authorizations) > limit
    if has_more:
        authorizations = authorizations[:limit]
    
    result = []
    for a in authorizations:
        from_user = storage.get_user_by_id(a.from_user_id)
        to_user = storage.get_user_by_id(a.to_user_id)
        effective_status = storage._get_authorization_status(a)
        result.append(AuthorizationResponse(
            authorization_id=a.id,
            from_user_id=a.from_user_id,
            from_handle=from_user.handle if from_user else "",
            to_user_id=a.to_user_id,
            to_handle=to_user.handle if to_user else "",
            amount=a.amount,
            captured_amount=a.captured_amount,
            remaining_amount=a.remaining_amount,
            note=a.note,
            visibility=a.visibility,
            status=effective_status,
            expires_at=a.expires_at,
            payment_id=a.payment_id,
            payment_ids=a.payment_ids,
            created_at=a.created_at
        ))
    
    if format_type == "html":
        session = storage.get_session_cookie(request)
        return templates.TemplateResponse("authorizations.html", {
            "request": request,
            "authorizations": result,
            "user_id": user_id,
            "currency": storage.currency,
            "minor_units": storage.minor_units,
            "csrf_token": session.csrf_token if session else generate_csrf_token()
        })
    
    return AuthorizationListResponse(authorizations=result, has_more=has_more)


@app.post("/splits", response_model=SplitResponse, status_code=201)
async def create_split(
    request: Request,
    split_data: SplitCreate,
    user_id: str = Depends(get_current_user),
    idempotency_key: str = Header(..., alias="Idempotency-Key"),
    session_id: Optional[str] = Cookie(None)
):
    format_type = get_accept_format(request.headers.get("accept"))
    
    validate_idempotency_key(idempotency_key)
    
    if format_type == "html" and session_id:
        await require_csrf_token(request)
    
    # Validate participant handles and get users
    participant_users = []
    for handle in split_data.participant_handles:
        user = storage.get_user_by_handle(handle)
        if not user:
            if format_type == "html":
                return templates.TemplateResponse("error.html", {
                    "request": request, "error": f"Participant {handle} not found", "status_code": 404
                }, status_code=404)
            raise HTTPException(status_code=404, detail=create_error_response("not_found", f"Participant {handle} not found"))
        participant_users.append(user)
    
    # Calculate equal shares
    n = len(participant_users)
    shares = calculate_shares(split_data.amount, n)
    
    # Create requests for each participant (except the caller)
    requests_created = []
    for i, user in enumerate(participant_users):
        if user.id != user_id:
            req_obj = storage.create_request(user_id, user.id, shares[i], split_data.note)
            requests_created.append(req_obj)
    
    # Build response shares
    share_objects = [SplitShare(handle=user.handle, amount=shares[i]) for i, user in enumerate(participant_users)]
    
    # Build response requests
    request_responses = []
    for req in requests_created:
        requester = storage.get_user_by_id(req.requester_id)
        payer = storage.get_user_by_id(req.payer_id)
        request_responses.append(RequestResponse(
            request_id=req.id,
            requester_id=req.requester_id,
            requester_handle=requester.handle if requester else "",
            payer_id=req.payer_id,
            payer_handle=payer.handle if payer else "",
            amount=req.amount,
            currency=storage.currency,
            note=req.note,
            status=req.status,
            payment_id=req.payment_id,
            created_at=req.created_at
        ))
    
    split_id = storage.create_split(user_id, split_data.amount, split_data.participant_handles, split_data.note, share_objects, requests_created)
    
    response = SplitResponse(
        split_id=split_id,
        amount=split_data.amount,
        currency=storage.currency,
        note=split_data.note,
        shares=share_objects,
        requests=request_responses,
        created_at=storage._now_iso()
    )
    
    body = {"amount": split_data.amount, "participant_handles": split_data.participant_handles, "note": split_data.note}
    storage.store_idempotency(
        user_id, idempotency_key, request.method, request.url.path,
        body, 201, response.model_dump()
    )
    
    if format_type == "html":
        session = storage.get_session_cookie(request)
        return templates.TemplateResponse("split.html", {
            "request": request,
            "currency": storage.currency,
            "minor_units": storage.minor_units,
            "shares": [{"handle": s.handle, "amount": s.amount} for s in share_objects],
            "amount": split_data.amount,
            "csrf_token": session.csrf_token if session else generate_csrf_token()
        })
    
    return response


@app.post("/settlements", response_model=SettlementResponse, status_code=201)
async def create_settlement(
    request: Request,
    settlement: SettlementCreate,
    user_id: str = Depends(get_current_user),
    idempotency_key: str = Header(..., alias="Idempotency-Key"),
    session_id: Optional[str] = Cookie(None)
):
    format_type = get_accept_format(request.headers.get("accept"))
    
    validate_idempotency_key(idempotency_key)
    
    if format_type == "html" and session_id:
        await require_csrf_token(request)
    
    # Check if user is a settlement operator
    if user_id not in storage.settlement_operator_ids:
        if format_type == "html":
            return templates.TemplateResponse("error.html", {
                "request": request, "error": "Not a settlement operator", "status_code": 403
            }, status_code=403)
        raise HTTPException(status_code=403, detail=create_error_response("forbidden", "Not a settlement operator"))
    
    try:
        settlement_id, committed_at, payments = storage.atomic_settlement(user_id, [t.model_dump() for t in settlement.transfers])
    except ValueError as e:
        if str(e) == "not_found":
            if format_type == "html":
                return templates.TemplateResponse("error.html", {
                    "request": request, "error": "User not found", "status_code": 404
                }, status_code=404)
            raise HTTPException(status_code=404, detail=create_error_response("not_found", "User not found"))
        if str(e) == "self_payment":
            if format_type == "html":
                return templates.TemplateResponse("error.html", {
                    "request": request, "error": "Cannot send payment to yourself", "status_code": 422
                }, status_code=422)
            raise HTTPException(status_code=422, detail=create_error_response("self_payment", "Cannot send payment to yourself"))
        if str(e) == "validation_failed":
            if format_type == "html":
                return templates.TemplateResponse("error.html", {
                    "request": request, "error": "Validation failed", "status_code": 422
                }, status_code=422)
            raise HTTPException(status_code=422, detail=create_error_response("validation_failed", "Validation failed"))
        if str(e) == "insufficient_funds":
            if format_type == "html":
                return templates.TemplateResponse("error.html", {
                    "request": request, "error": "Insufficient funds", "status_code": 409
                }, status_code=409)
            raise HTTPException(status_code=409, detail=create_error_response("insufficient_funds", "Insufficient funds"))
        raise
    
    response = storage.create_settlement(settlement_id, payments, committed_at)
    
    body = {"transfers": [t.model_dump() for t in settlement.transfers]}
    storage.store_idempotency(
        user_id, idempotency_key, request.method, request.url.path,
        body, 201, response.model_dump()
    )
    
    if format_type == "html":
        return RedirectResponse(url="/activity", status_code=303)
    
    return response


@app.get("/activity", response_model=ActivityResponse)
async def get_activity(
    request: Request,
    limit: int = Query(50),
    offset: int = Query(0),
    user_id: str = Depends(get_current_user)
):
    format_type = get_accept_format(request.headers.get("accept"))
    
    limit, offset = validate_limit_offset(limit, offset)
    
    all_payments = storage.get_all_payments()
    user = storage.get_user_by_id(user_id)
    
    visible = []
    for p in all_payments:
        if p.visibility == "public" or p.from_user_id == user_id or p.to_user_id == user_id:
            visible.append(p)
    
    visible.sort(key=lambda p: p.created_at, reverse=True)
    # Check if there are more items beyond the current page
    has_more = len(visible) > offset + limit
    page = visible[offset:offset + limit]
    
    result = []
    for p in page:
        from_user = storage.get_user_by_id(p.from_user_id)
        to_user = storage.get_user_by_id(p.to_user_id)
        result.append(PaymentResponse(
            payment_id=p.id,
            from_user_id=p.from_user_id,
            from_handle=from_user.handle if from_user else "",
            to_user_id=p.to_user_id,
            to_handle=to_user.handle if to_user else "",
            amount=p.amount,
            currency=storage.currency,
            note=p.note,
            visibility=p.visibility,
            request_id=p.request_id,
            created_at=p.created_at
        ))
    
    if format_type == "html":
        session = storage.get_session_cookie(request)
        return templates.TemplateResponse("activity.html", {
            "request": request,
            "payments": result,
            "currency": storage.currency,
            "minor_units": storage.minor_units,
            "csrf_token": session.csrf_token if session else generate_csrf_token()
        })
    
    return ActivityResponse(payments=result, has_more=has_more)


# Include remaining endpoints from the original file...
# For brevity, I'm showing the key modifications for HTML support.
# The rest of the API endpoints (pay_request, authorizations, splits, settlements, etc.)
# follow the same pattern - check format_type and redirect for HTML.

# ============================================================
# TEST ENDPOINTS
# ============================================================

from starlette.responses import Response

@app.post("/_test/reset", status_code=204)
async def reset(fixture: Fixture):
    errors = storage.validate_fixture(fixture)
    if errors:
        raise HTTPException(status_code=422, detail=create_error_response("validation_failed", "; ".join(errors)))
    
    storage.reset(fixture)
    return Response(status_code=204)


@app.get("/_test/export", response_model=ExportResponse)
async def export_state():
    state = storage.export_state()
    return ExportResponse(track="pocketful", format_version=1, state=state)


@app.post("/_test/import", status_code=204)
async def import_state(import_req: ImportRequest):
    if import_req.track != "pocketful" or import_req.format_version != 1:
        raise HTTPException(status_code=422, detail=create_error_response("validation_failed", "Invalid track or format version"))
    
    try:
        storage.import_state(import_req.state)
    except Exception as e:
        raise HTTPException(status_code=422, detail=create_error_response("validation_failed", str(e)))
    
    return Response(status_code=204)


if __name__ == "__main__":
    import uvicorn
    port = int(os.environ.get("PORT", 8080))
    uvicorn.run(app, host="0.0.0.0", port=port)