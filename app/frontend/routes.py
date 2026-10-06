from fastapi import APIRouter, Request
from fastapi.responses import HTMLResponse
from fastapi.templating import Jinja2Templates

router = APIRouter()
templates = Jinja2Templates(directory="app/templates")


def get_csrf_token():
    """Simple CSRF token generation for forms."""
    import secrets
    return secrets.token_urlsafe(32)


@router.get("/", response_class=HTMLResponse, name="index")
async def index(request: Request):
    """Serve the home dashboard page."""
    return templates.TemplateResponse("index.html", {"request": request, "csrf_token": get_csrf_token(), "held": 0})


@router.get("/signup", response_class=HTMLResponse, name="signup")
async def signup_page(request: Request):
    """Serve the signup page."""
    return templates.TemplateResponse("signup.html", {"request": request, "csrf_token": get_csrf_token()})


@router.get("/login", response_class=HTMLResponse, name="login")
async def login_page(request: Request):
    """Serve the login page."""
    return templates.TemplateResponse("login.html", {"request": request, "csrf_token": get_csrf_token()})


@router.get("/requests", response_class=HTMLResponse, name="requests")
async def requests_page(request: Request):
    """Serve the requests page."""
    return templates.TemplateResponse("requests.html", {"request": request, "csrf_token": get_csrf_token()})


@router.get("/split", response_class=HTMLResponse, name="split")
async def split_page(request: Request):
    """Serve the split bill page."""
    return templates.TemplateResponse("split.html", {"request": request, "csrf_token": get_csrf_token()})


@router.get("/authorizations", response_class=HTMLResponse, name="authorizations")
async def authorizations_page(request: Request):
    """Serve the authorizations page."""
    return templates.TemplateResponse("authorizations.html", {"request": request, "csrf_token": get_csrf_token()})


@router.get("/index.html", response_class=HTMLResponse)
async def index_html(request: Request):
    """Serve the home dashboard page (alternative route)."""
    return templates.TemplateResponse("index.html", {"request": request, "csrf_token": get_csrf_token(), "held": 0})