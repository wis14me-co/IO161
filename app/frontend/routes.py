from fastapi import APIRouter, Request, Depends
from fastapi.responses import HTMLResponse, JSONResponse, RedirectResponse
from fastapi.templating import Jinja2Templates
from app.deps import get_current_user_optional
from app.storage import storage
from pathlib import Path

router = APIRouter()
# Use absolute path for templates to avoid issues with working directory
TEMPLATE_DIR = Path(__file__).parent.parent / "templates"
templates = Jinja2Templates(directory=str(TEMPLATE_DIR))


def get_csrf_token():
    """Simple CSRF token generation for forms."""
    import secrets
    return secrets.token_urlsafe(32)


def wants_html(request: Request) -> bool:
    """Check if client prefers HTML over JSON based on Accept header."""
    accept = request.headers.get("accept", "")
    return "text/html" in accept


@router.get("/", name="index")
async def index(request: Request, user_id: str = Depends(get_current_user_optional)):
    """Serve the home dashboard page or JSON API based on Accept header."""
    if wants_html(request):
        csrf_token = get_csrf_token()
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
        csrf_token = get_csrf_token()
        return templates.TemplateResponse("signup.html", {"request": request, "csrf_token": csrf_token})
    return {"message": "Signup endpoint - POST to /api/v1/auth/signup with email, password, display_name"}


@router.get("/login", response_class=HTMLResponse, name="login")
async def login_page(request: Request):
    """Serve the login page."""
    if wants_html(request):
        csrf_token = get_csrf_token()
        return templates.TemplateResponse("login.html", {"request": request, "csrf_token": csrf_token})
    return {"message": "Login endpoint - POST to /api/v1/auth/login with email, password"}


@router.get("/requests", response_class=HTMLResponse, name="requests")
async def requests_page(request: Request, user_id: str = Depends(get_current_user_optional)):
    """Serve the requests page or JSON for API clients."""
    if wants_html(request):
        if not user_id:
            return RedirectResponse(url="/login")
        csrf_token = get_csrf_token()
        return templates.TemplateResponse("requests.html", {"request": request, "csrf_token": csrf_token})
    
    # JSON response for API clients
    if not user_id:
        return JSONResponse(status_code=401, content={"code": "unauthenticated", "message": "Missing or invalid token"})
    incoming = storage.get_requests_for_user(user_id, "incoming", None, 50, 0)
    outgoing = storage.get_requests_for_user(user_id, "outgoing", None, 50, 0)
    return {
        "incoming": [{"request_id": r.id, "requester_id": r.requester_id, "payer_id": r.payer_id, "amount": r.amount, "note": r.note, "status": r.status, "created_at": r.created_at} for r in incoming],
        "outgoing": [{"request_id": r.id, "requester_id": r.requester_id, "payer_id": r.payer_id, "amount": r.amount, "note": r.note, "status": r.status, "created_at": r.created_at} for r in outgoing],
    }


@router.get("/split", response_class=HTMLResponse, name="split")
async def split_page(request: Request, user_id: str = Depends(get_current_user_optional)):
    """Serve the split bill page."""
    if wants_html(request):
        if not user_id:
            return RedirectResponse(url="/login")
        csrf_token = get_csrf_token()
        return templates.TemplateResponse("split.html", {"request": request, "csrf_token": csrf_token})
    return JSONResponse(status_code=406, content={"code": "not_acceptable", "message": "API endpoint not available at /split, use /api/v1/splits"})


@router.get("/authorizations", response_class=HTMLResponse, name="authorizations")
async def authorizations_page(request: Request, user_id: str = Depends(get_current_user_optional)):
    """Serve the authorizations page."""
    if wants_html(request):
        if not user_id:
            return RedirectResponse(url="/login")
        csrf_token = get_csrf_token()
        return templates.TemplateResponse("authorizations.html", {"request": request, "csrf_token": csrf_token})
    return JSONResponse(status_code=406, content={"code": "not_acceptable", "message": "API endpoint not available at /authorizations, use /api/v1/authorizations"})


@router.get("/index.html", response_class=HTMLResponse)
async def index_html(request: Request, user_id: str = Depends(get_current_user_optional)):
    """Serve the home dashboard page (alternative route)."""
    return await index(request, user_id)