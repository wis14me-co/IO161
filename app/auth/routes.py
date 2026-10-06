from fastapi import APIRouter, Depends, HTTPException, status, Request, Response, Form, Body
from fastapi.security import OAuth2PasswordBearer, OAuth2PasswordRequestForm
from typing import Optional
from app.auth import service
from app.auth.schemas import UserCreate, UserResponse, Token, TokenData, UserLogin, TokenResponse
from app.storage import storage, User as StorageUser
from app.validation import create_error_response, ValidationError
from app.deps import get_current_user, get_current_user_optional, set_session_cookie, clear_session_cookies, generate_csrf_token, wants_html

router = APIRouter()

oauth2_scheme = OAuth2PasswordBearer(tokenUrl="/api/v1/auth/login")


async def parse_signup_request(request: Request) -> UserCreate:
    """Parse signup request from either JSON or form data."""
    content_type = request.headers.get("content-type", "")
    is_form = "application/x-www-form-urlencoded" in content_type or "multipart/form-data" in content_type
    
    if is_form:
        form = await request.form()
        email = form.get("email")
        password = form.get("password")
        display_name = form.get("display_name")
        if not email or not password or not display_name:
            raise ValidationError("validation_failed", "Email, password, and display name required")
        return UserCreate(email=email, password=password, display_name=display_name, handle=None)
    else:
        body = await request.json()
        try:
            return UserCreate(**body)
        except Exception:
            raise ValidationError("validation_failed", "Invalid request body")


async def parse_login_request(request: Request) -> UserLogin:
    """Parse login request from either JSON or form data."""
    content_type = request.headers.get("content-type", "")
    is_form = "application/x-www-form-urlencoded" in content_type or "multipart/form-data" in content_type
    
    if is_form:
        form = await request.form()
        email = form.get("email")
        password = form.get("password")
        if not email or not password:
            raise ValidationError("validation_failed", "Email and password required")
        return UserLogin(email=email, password=password)
    else:
        body = await request.json()
        try:
            return UserLogin(**body)
        except Exception:
            raise ValidationError("validation_failed", "Invalid request body")


@router.post("/signup", response_model=TokenResponse, status_code=status.HTTP_201_CREATED)
async def signup(request: Request, response: Response, user_in: UserCreate = Depends(parse_signup_request)):
    """Handle signup - supports both JSON API and HTML form submissions."""
    try:
        user = service.auth_service.signup(user_in)
        token = storage.create_token(user.id)
        csrf_token = generate_csrf_token()
        
        # If browser client, set cookies and redirect
        if wants_html(request):
            redirect_response = Response(status_code=status.HTTP_303_SEE_OTHER, headers={"Location": "/"})
            set_session_cookie(redirect_response, token, csrf_token)
            return redirect_response
        
        return TokenResponse(token=token, user_id=str(user.id), display_name=user.display_name)
    except ValidationError as e:
        raise HTTPException(status_code=e.status_code, detail=create_error_response(e.code, e.message))
    except Exception as e:
        if hasattr(e, 'status_code'):
            raise HTTPException(status_code=e.status_code, detail=create_error_response(e.code, e.message))
        raise


@router.post("/login", response_model=TokenResponse)
async def login(request: Request, response: Response, user_in: UserLogin = Depends(parse_login_request)):
    """Handle login - supports both JSON API and HTML form submissions."""
    try:
        token_response = service.auth_service.login(user_in)
        csrf_token = generate_csrf_token()
        
        # If browser client, set cookies and redirect
        if wants_html(request):
            redirect_response = Response(status_code=status.HTTP_303_SEE_OTHER, headers={"Location": "/"})
            set_session_cookie(redirect_response, token_response.token, csrf_token)
            return redirect_response
        
        return token_response
    except ValidationError as e:
        raise HTTPException(status_code=e.status_code, detail=create_error_response(e.code, e.message))
    except Exception as e:
        if hasattr(e, 'status_code'):
            raise HTTPException(status_code=e.status_code, detail=create_error_response(e.code, e.message))
        raise


@router.post("/logout")
async def logout(request: Request, response: Response, user_id: Optional[str] = Depends(get_current_user_optional)):
    """Logout - clear session cookies."""
    # If user is authenticated via token, we could invalidate the token here
    # For now, just clear cookies for browser clients
    if wants_html(request) or user_id:
        clear_session_cookies(response)
    
    if wants_html(request):
        return Response(status_code=status.HTTP_303_SEE_OTHER, headers={"Location": "/login"})
    
    return {"message": "Logged out successfully"}


@router.get("/me", response_model=UserResponse)
def read_users_me(user_id: str = Depends(get_current_user)):
    current_user = storage.get_user_by_id(user_id)
    if not current_user:
        raise HTTPException(status_code=404, detail=create_error_response("not_found", "User not found"))
    # Calculate held (sum of remaining amounts of ALL open authorizations involving the user, both outgoing and incoming)
    auths = storage.get_authorizations_for_user(current_user.id, direction=None, status="open")
    held = sum(a.remaining_amount for a in auths)
    available = max(0, current_user.balance - held)
    
    return UserResponse(
        user_id=current_user.id,
        email=current_user.email,
        display_name=current_user.display_name,
        handle=current_user.handle,
        balance=current_user.balance,
        total=current_user.balance,
        available=available,
        held=held,
        currency=storage.currency,
        minor_units=storage.minor_units
    )