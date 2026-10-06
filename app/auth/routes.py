from fastapi import APIRouter, Depends, HTTPException, status, Request, Response
from fastapi.security import OAuth2PasswordBearer, OAuth2PasswordRequestForm
from typing import Optional
from app.auth import service
from app.auth.schemas import UserCreate, UserResponse, Token, TokenData, UserLogin, TokenResponse
from app.storage import storage, User as StorageUser
from app.validation import create_error_response
from app.deps import get_current_user, get_current_user_optional, set_session_cookie, clear_session_cookies, generate_csrf_token, wants_html

router = APIRouter()

oauth2_scheme = OAuth2PasswordBearer(tokenUrl="/api/v1/auth/login")


@router.post("/signup", response_model=TokenResponse, status_code=status.HTTP_201_CREATED)
async def signup(request: Request, response: Response, user_in: UserCreate):
    try:
        user = service.auth_service.signup(user_in)
        token = storage.create_token(user.id)
        csrf_token = generate_csrf_token()
        
        # If browser client, set cookies and redirect
        if wants_html(request):
            set_session_cookie(response, token, csrf_token)
            return Response(status_code=status.HTTP_303_SEE_OTHER, headers={"Location": "/"})
        
        return TokenResponse(token=token, user_id=str(user.id), display_name=user.display_name)
    except Exception as e:
        if hasattr(e, 'status_code'):
            raise HTTPException(status_code=e.status_code, detail=create_error_response(e.code, e.message))
        raise


@router.post("/login", response_model=TokenResponse)
async def login(request: Request, response: Response, user_in: UserLogin):
    # DEBUG
    accept_header = request.headers.get("accept", "NO_ACCEPT")
    print(f"DEBUG login: accept_header={accept_header}")
    print(f"DEBUG login: wants_html={wants_html(request)}")
    
    try:
        token_response = service.auth_service.login(user_in)
        csrf_token = generate_csrf_token()
        
        # If browser client, set cookies and redirect
        if wants_html(request):
            set_session_cookie(response, token_response.token, csrf_token)
            return Response(status_code=status.HTTP_303_SEE_OTHER, headers={"Location": "/"})
        
        return token_response
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
    # Calculate held (sum of remaining amounts of open OUTGOING authorizations where user is payer) and available
    auths = storage.get_authorizations_for_user(current_user.id, direction="outgoing", status="open")
    held = sum(a.remaining_amount for a in auths)
    available = max(0, current_user.balance - held)
    
    return UserResponse(
        user_id=current_user.id,
        email=current_user.email,
        display_name=current_user.display_name,
        handle=current_user.handle,
        is_active=True,
        is_superuser=False,
        created_at=None,
        updated_at=None,
        balance=current_user.balance,
        total=current_user.balance,
        available=available,
        held=held,
        currency=storage.currency,
        minor_units=storage.minor_units
    )