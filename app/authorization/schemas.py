from pydantic import BaseModel, Field, field_validator
from typing import Optional, List, Literal
from datetime import datetime


class AuthorizationCreate(BaseModel):
    to_handle: str = Field(..., min_length=1, max_length=20)
    amount: int = Field(..., ge=1, le=1000000000)
    note: str = ""
    visibility: Literal["public", "private"] = "public"
    expires_at: Optional[str] = None

    @field_validator("note")
    @classmethod
    def validate_note(cls, v: str) -> str:
        if len(v) > 200:
            raise ValueError("note must be at most 200 characters")
        return v

    @field_validator("expires_at")
    @classmethod
    def validate_expires_at(cls, v: Optional[str]) -> Optional[str]:
        if v is not None:
            try:
                datetime.fromisoformat(v.replace("Z", "+00:00"))
            except ValueError:
                raise ValueError("expires_at must be a valid RFC 3339 timestamp")
        return v


class AuthorizationCapture(BaseModel):
    amount: Optional[int] = Field(None, ge=1)
    final: bool = True


class AuthorizationResponse(BaseModel):
    id: str
    from_user_id: str
    to_user_id: str
    amount: int
    captured_amount: int
    note: str
    visibility: str
    status: str
    expires_at: Optional[str] = None
    created_at: str
    remaining_amount: int
    payment_id: Optional[str] = None
    payment_ids: List[str] = []


class AuthorizationListResponse(BaseModel):
    authorizations: List[AuthorizationResponse]
    has_more: bool