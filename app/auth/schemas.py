from pydantic import BaseModel, EmailStr
from typing import Optional
from datetime import datetime


class UserBase(BaseModel):
    email: EmailStr
    full_name: Optional[str] = None


class UserCreate(UserBase):
    password: str
    display_name: str
    handle: Optional[str] = None


class UserLogin(BaseModel):
    email: EmailStr
    password: str


class UserUpdate(UserBase):
    password: Optional[str] = None
    is_active: Optional[bool] = None


class UserResponse(BaseModel):
    user_id: str
    email: EmailStr
    display_name: str
    handle: str
    balance: int
    total: int
    available: int
    held: int
    currency: str
    minor_units: int
    
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