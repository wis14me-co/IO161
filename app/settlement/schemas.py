from pydantic import BaseModel, Field, field_validator
from typing import Optional, List, Literal
from datetime import datetime


class SettlementTransferCreate(BaseModel):
    from_handle: str = Field(..., min_length=1, max_length=20)
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


class SettlementCreate(BaseModel):
    transfers: List[SettlementTransferCreate] = Field(..., min_length=1, max_length=32)


class SettlementPaymentResponse(BaseModel):
    payment_id: str
    from_user_id: str
    from_handle: str
    to_user_id: str
    to_handle: str
    amount: int
    currency: str
    note: str
    visibility: str
    request_id: Optional[str] = None
    settlement_id: Optional[str] = None
    created_at: str


class SettlementResponse(BaseModel):
    settlement_id: str
    committed_at: str
    payments: List[SettlementPaymentResponse]