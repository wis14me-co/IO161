from pydantic import BaseModel, EmailStr
from typing import Optional
from datetime import datetime


class UserBase(BaseModel):
    email: EmailStr
    full_name: Optional[str] = None


class UserCreate(UserBase):
    password: str
    display_name: str
    handle: str


class UserLogin(BaseModel):
    email: EmailStr
    password: str


class UserUpdate(UserBase):
    password: Optional[str] = None
    is_active: Optional[bool] = None


class UserResponse(UserBase):
    id: str
    is_active: bool = True
    is_superuser: bool = False
    created_at: Optional[str] = None
    updated_at: Optional[str] = None
    balance: int
    total: int
    available: int
    held: int
    
    class Config:
        from_attributes = True


class Token(BaseModel):
    access_token: str
    token_type: str = "bearer"


class TokenResponse(BaseModel):
    token: str
    user_id: str
    display_name: str


class TokenData(BaseModel):
    user_id: Optional[int] = None
    email: Optional[str] = None