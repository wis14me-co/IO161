from fastapi import APIRouter, Request, Depends, Response
from fastapi.responses import HTMLResponse, JSONResponse, RedirectResponse
from fastapi.templating import Jinja2Templates
from app.deps import get_current_user_optional, get_csrf_token, wants_html
from app.storage import storage
from pathlib import Path

router = APIRouter()
# Use absolute path for templates to avoid issues with working directory
TEMPLATE_DIR = Path(__file__).parent.parent / "templates"
templates = Jinja2Templates(directory=str(TEMPLATE_DIR))


@router.get("/", name="index")
async def index(request: Request, response: Response, user_id: str = Depends(get_current_user_optional)):
    """Serve the home dashboard page or JSON API based on Accept header."""
    if wants_html(request):
        csrf_token = get_csrf_token(request)
        # Get user data for held amount if authenticated
        held = 0
        if user_id:
            auths = storage.get_authorizations_for_user(user_id, direction="outgoing", status="open")
            held = sum(a.amount for a in auths)
        template_response = templates.TemplateResponse("index.html", {
            "request": request, 
            "csrf_token": csrf_token,
            "held": held
        })
        # Set CSRF cookie if not already present
        if not request.cookies.get("pocketful_csrf"):
            template_response.set_cookie(
                key="pocketful_csrf",
                value=csrf_token,
                httponly=False,
                secure=False,  # DEBUG mode
                samesite="lax",
                max_age=60 * 60 * 24 * 30,
                path="/"
            )
        return template_response
    return JSONResponse(content={"message": "Welcome to Pocketful API"})


@router.get("/signup", response_class=HTMLResponse, name="signup")
async def signup_page(request: Request, response: Response):
    """Serve the signup page."""
    if wants_html(request):
        csrf_token = get_csrf_token(request)
        template_response = templates.TemplateResponse("signup.html", {"request": request, "csrf_token": csrf_token})
        if not request.cookies.get("pocketful_csrf"):
            template_response.set_cookie(
                key="pocketful_csrf",
                value=csrf_token,
                httponly=False,
                secure=False,
                samesite="lax",
                max_age=60 * 60 * 24 * 30,
                path="/"
            )
        return template_response
    return JSONResponse(content={"message": "Signup endpoint - POST to /auth/signup with email, password, display_name"})


@router.get("/login", response_class=HTMLResponse, name="login")
async def login_page(request: Request, response: Response):
    """Serve the login page."""
    if wants_html(request):
        csrf_token = get_csrf_token(request)
        template_response = templates.TemplateResponse("login.html", {"request": request, "csrf_token": csrf_token})
        if not request.cookies.get("pocketful_csrf"):
            template_response.set_cookie(
                key="pocketful_csrf",
                value=csrf_token,
                httponly=False,
                secure=False,
                samesite="lax",
                max_age=60 * 60 * 24 * 30,
                path="/"
            )
        return template_response
    return JSONResponse(content={"message": "Login endpoint - POST to /auth/login with email, password"})


@router.get("/requests", response_class=HTMLResponse, name="requests")
async def requests_page(request: Request, response: Response, user_id: str = Depends(get_current_user_optional)):
    """Serve the requests page or JSON for API clients."""
    print(f"DEBUG: requests_page hit, path={request.url.path}")
    if wants_html(request):
        if not user_id:
            return RedirectResponse(url="/login")
        csrf_token = get_csrf_token(request)
        template_response = templates.TemplateResponse("requests.html", {"request": request, "csrf_token": csrf_token})
        if not request.cookies.get("pocketful_csrf"):
            template_response.set_cookie(
                key="pocketful_csrf",
                value=csrf_token,
                httponly=False,
                secure=False,
                samesite="lax",
                max_age=60 * 60 * 24 * 30,
                path="/"
            )
        return template_response
    
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
async def split_page(request: Request, response: Response, user_id: str = Depends(get_current_user_optional)):
    """Serve the split bill page."""
    if wants_html(request):
        if not user_id:
            return RedirectResponse(url="/login")
        csrf_token = get_csrf_token(request)
        template_response = templates.TemplateResponse("split.html", {"request": request, "csrf_token": csrf_token})
        if not request.cookies.get("pocketful_csrf"):
            template_response.set_cookie(
                key="pocketful_csrf",
                value=csrf_token,
                httponly=False,
                secure=False,
                samesite="lax",
                max_age=60 * 60 * 24 * 30,
                path="/"
            )
        return template_response
    return JSONResponse(status_code=406, content={"code": "not_acceptable", "message": "API endpoint not available at /split, use /api/v1/splits"})


@router.get("/authorizations", response_class=HTMLResponse, name="authorizations")
async def authorizations_page(request: Request, response: Response, user_id: str = Depends(get_current_user_optional)):
    """Serve the authorizations page."""
    print(f"DEBUG: authorizations_page hit, path={request.url.path}")
    if wants_html(request):
        if not user_id:
            return RedirectResponse(url="/login")
        csrf_token = get_csrf_token(request)
        template_response = templates.TemplateResponse("authorizations.html", {"request": request, "csrf_token": csrf_token})
        if not request.cookies.get("pocketful_csrf"):
            template_response.set_cookie(
                key="pocketful_csrf",
                value=csrf_token,
                httponly=False,
                secure=False,
                samesite="lax",
                max_age=60 * 60 * 24 * 30,
                path="/"
            )
        return template_response
    return JSONResponse(status_code=406, content={"code": "not_acceptable", "message": "API endpoint not available at /authorizations, use /api/v1/authorizations"})


@router.get("/index.html", response_class=HTMLResponse)
async def index_html(request: Request, response: Response, user_id: str = Depends(get_current_user_optional)):
    """Serve the home dashboard page (alternative route)."""
    return await index(request, response, user_id)