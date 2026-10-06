from fastapi import APIRouter, Depends, HTTPException, status
from fastapi.security import OAuth2PasswordBearer, OAuth2PasswordRequestForm
from typing import Optional
from app.auth import service
from app.auth.schemas import UserCreate, UserResponse, Token, TokenData, UserLogin, TokenResponse
from app.storage import storage, User as StorageUser
from app.validation import create_error_response
from app.deps import get_current_user

router = APIRouter()

oauth2_scheme = OAuth2PasswordBearer(tokenUrl="/api/v1/auth/login")


@router.post("/signup", response_model=TokenResponse, status_code=status.HTTP_201_CREATED)
def signup(user_in: UserCreate):
    try:
        user = service.auth_service.signup(user_in)
        access_token = service.create_access_token(data={"sub": user.id, "email": user.email})
        return TokenResponse(token=access_token, user_id=str(user.id), display_name=user.display_name)
    except Exception as e:
        if hasattr(e, 'status_code'):
            raise HTTPException(status_code=e.status_code, detail=create_error_response(e.code, e.message))
        raise


@router.post("/login", response_model=TokenResponse)
def login(user_in: UserLogin):
    try:
        token_response = service.auth_service.login(user_in)
        return token_response
    except Exception as e:
        if hasattr(e, 'status_code'):
            raise HTTPException(status_code=e.status_code, detail=create_error_response(e.code, e.message))
        raise


@router.get("/me", response_model=UserResponse)
def read_users_me(user_id: str = Depends(get_current_user)):
    current_user = storage.get_user_by_id(user_id)
    if not current_user:
        raise HTTPException(status_code=404, detail=create_error_response("not_found", "User not found"))
    # Calculate held (sum of open OUTGOING authorizations where user is payer) and available
    auths = storage.get_authorizations_for_user(current_user.id, direction="outgoing", status="open")
    held = sum(a.amount for a in auths)
    available = max(0, current_user.balance - held)
    
    return UserResponse(
        id=current_user.id,
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
        held=held
    )