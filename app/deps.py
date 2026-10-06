from typing import Optional
from fastapi import Depends, HTTPException, Header
from app.storage import storage
from app.validation import create_error_response


def get_current_user(authorization: Optional[str] = Header(None)) -> str:
    if not authorization or not authorization.startswith("Bearer "):
        raise HTTPException(status_code=401, detail=create_error_response("unauthenticated", "Missing or invalid token"))
    token = authorization[7:]
    user = storage.get_user_by_token(token)
    if not user:
        raise HTTPException(status_code=401, detail=create_error_response("unauthenticated", "Invalid token"))
    return user.id


def get_current_user_optional(authorization: Optional[str] = Header(None)) -> Optional[str]:
    if not authorization or not authorization.startswith("Bearer "):
        return None
    token = authorization[7:]
    user = storage.get_user_by_token(token)
    return user.id if user else None