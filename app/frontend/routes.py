from fastapi import APIRouter, Request, Depends, Form, Response
from fastapi.responses import HTMLResponse, JSONResponse, RedirectResponse
from fastapi.templating import Jinja2Templates
from app.deps import get_current_user_optional, get_csrf_token, wants_html, set_session_cookie, clear_session_cookies, generate_csrf_token
from app.auth import service
from app.auth.schemas import UserLogin, UserCreate
from app.validation import create_error_response
from app.storage import storage
from pathlib import Path

router = APIRouter()
# Use absolute path for templates to avoid issues with working directory
TEMPLATE_DIR = Path(__file__).parent.parent / "templates"
templates = Jinja2Templates(directory=str(TEMPLATE_DIR))


@router.get("/", name="index")
async def index(request: Request, user_id: str = Depends(get_current_user_optional)):
    """Serve the home dashboard page or JSON API based on Accept header."""
    if wants_html(request):
        csrf_token = get_csrf_token(request)
        # Get user data for held amount if authenticated
        held = 0
        if user_id:
            auths = storage.get_authorizations_for_user(user_id, direction="outgoing", status="open")
            held = sum(a.amount for a in auths)
        return templates.TemplateResponse("index.html", {
            "request": request, 
            "csrf_token": csrf_token,
            "held": held
        })
    return JSONResponse(content={"message": "Welcome to Pocketful API"})


@router.get("/signup", response_class=HTMLResponse, name="signup")
async def signup_page(request: Request):
    """Serve the signup page."""
    if wants_html(request):
        csrf_token = get_csrf_token(request)
        return templates.TemplateResponse("signup.html", {"request": request, "csrf_token": csrf_token})
    return JSONResponse(content={"message": "Signup endpoint - POST to /api/v1/auth/signup with email, password, display_name"})


@router.get("/login", response_class=HTMLResponse, name="login")
async def login_page(request: Request):
    """Serve the login page."""
    if wants_html(request):
        csrf_token = get_csrf_token(request)
        return templates.TemplateResponse("login.html", {"request": request, "csrf_token": csrf_token})
    return JSONResponse(content={"message": "Login endpoint - POST to /api/v1/auth/login with email, password"})


@router.post("/auth/login", name="login_form")
async def login_form(request: Request, response: Response, email: str = Form(None), password: str = Form(None), csrf_token: str = Form(None)):
    """Handle form-based login for browser clients."""
    # Check if request is JSON
    content_type = request.headers.get("content-type", "")
    is_json = "application/json" in content_type
    
    if is_json:
        # Parse JSON body
        try:
            body = await request.json()
            email = body.get("email")
            password = body.get("password")
        except Exception:
            return JSONResponse(status_code=400, content={"code": "validation_failed", "message": "Invalid JSON"})
    else:
        # Validate CSRF token for form submissions
        cookie_csrf = request.cookies.get("pocketful_csrf")
        if not cookie_csrf or csrf_token != cookie_csrf:
            return templates.TemplateResponse("login.html", {
                "request": request, 
                "csrf_token": generate_csrf_token(),
                "error": "Invalid CSRF token"
            }, status_code=400)
    
    if not email or not password:
        if is_json:
            return JSONResponse(status_code=422, content={"code": "validation_failed", "message": "Email and password required"})
        return templates.TemplateResponse("login.html", {
            "request": request, 
            "csrf_token": generate_csrf_token(),
            "error": "Email and password required"
        }, status_code=400)
    
    try:
        user_in = UserLogin(email=email, password=password)
        token_response = service.auth_service.login(user_in)
        new_csrf_token = generate_csrf_token()
        
        # Create redirect response and set cookies on it
        redirect_response = RedirectResponse(url="/", status_code=303)
        set_session_cookie(redirect_response, token_response.token, new_csrf_token)
        
        return redirect_response
    except Exception as e:
        if hasattr(e, 'status_code'):
            if is_json:
                return JSONResponse(status_code=e.status_code, content={"code": e.code, "message": e.message})
            return templates.TemplateResponse("login.html", {
                "request": request, 
                "csrf_token": generate_csrf_token(),
                "error": e.message
            }, status_code=e.status_code)
        if is_json:
            return JSONResponse(status_code=400, content={"code": "login_failed", "message": "Login failed"})
        return templates.TemplateResponse("login.html", {
            "request": request, 
            "csrf_token": generate_csrf_token(),
            "error": "Login failed"
        }, status_code=400)


@router.get("/requests", response_class=HTMLResponse, name="requests")
async def requests_page(request: Request, user_id: str = Depends(get_current_user_optional)):
    """Serve the requests page or JSON for API clients."""
    if wants_html(request):
        if not user_id:
            return RedirectResponse(url="/login")
        csrf_token = get_csrf_token(request)
        return templates.TemplateResponse("requests.html", {"request": request, "csrf_token": csrf_token})
    
    # JSON response for API clients
    if not user_id:
        return JSONResponse(status_code=401, content={"code": "unauthenticated", "message": "Missing or invalid token"})
    incoming = storage.get_requests_for_user(user_id, "incoming", None, 50, 0)
    outgoing = storage.get_requests_for_user(user_id, "outgoing", None, 50, 0)
    return JSONResponse(content={
        "incoming": [{"request_id": r.id, "requester_id": r.requester_id, "payer_id": r.payer_id, "amount": r.amount, "note": r.note, "status": r.status, "created_at": r.created_at} for r in incoming],
        "outgoing": [{"request_id": r.id, "requester_id": r.requester_id, "payer_id": r.payer_id, "amount": r.amount, "note": r.note, "status": r.status, "created_at": r.created_at} for r in outgoing],
    })


@router.get("/split", response_class=HTMLResponse, name="split")
async def split_page(request: Request, user_id: str = Depends(get_current_user_optional)):
    """Serve the split bill page."""
    if wants_html(request):
        if not user_id:
            return RedirectResponse(url="/login")
        csrf_token = get_csrf_token(request)
        return templates.TemplateResponse("split.html", {"request": request, "csrf_token": csrf_token})
    return JSONResponse(status_code=406, content={"code": "not_acceptable", "message": "API endpoint not available at /split, use /api/v1/splits"})


@router.get("/authorizations", response_class=HTMLResponse, name="authorizations")
async def authorizations_page(request: Request, user_id: str = Depends(get_current_user_optional)):
    """Serve the authorizations page."""
    if wants_html(request):
        if not user_id:
            return RedirectResponse(url="/login")
        csrf_token = get_csrf_token(request)
        return templates.TemplateResponse("authorizations.html", {"request": request, "csrf_token": csrf_token})
    return JSONResponse(status_code=406, content={"code": "not_acceptable", "message": "API endpoint not available at /authorizations, use /api/v1/authorizations"})


@router.get("/index.html", response_class=HTMLResponse)
async def index_html(request: Request, user_id: str = Depends(get_current_user_optional)):
    """Serve the home dashboard page (alternative route)."""
    return await index(request, user_id)