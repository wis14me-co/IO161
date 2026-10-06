from pydantic import BaseModel, Field, field_validator
from typing import Literal


class PaymentCreate(BaseModel):
    to_handle: str = Field(..., min_length=1, max_length=20)
    amount: int = Field(..., ge=1, le=1000000000)
    note: str = ""
    visibility: Literal["public", "private"] = "public"

    @field_validator("note")
    @classmethod
    def validate_note(cls, v: str) -> str:
        if len(v) > 200:
            raise ValueError("note must be at most 200 characters")
        return v

    @field_validator("to_handle")
    @classmethod
    def validate_to_handle(cls, v: str) -> str:
        import re
        if not re.match(r"^[a-z0-9_]{1,20}$", v):
            raise ValueError("invalid handle format")
        return v


class PaymentResponse(BaseModel):
    payment_id: str
    from_user_id: str
    from_handle: str
    to_user_id: str
    to_handle: str
    amount: int
    currency: str
    note: str
    visibility: str
    request_id: str | None
    created_at: str