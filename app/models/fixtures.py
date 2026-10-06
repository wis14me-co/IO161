"""Fixture and response models for testing and data import/export."""
from pydantic import BaseModel, Field, EmailStr
from typing import Optional, List, Dict, Any, Literal
from datetime import datetime


class FixtureUser(BaseModel):
    id: str
    email: EmailStr
    password: str = Field(min_length=8)
    display_name: str = Field(min_length=1, max_length=100)
    handle: str = Field(pattern=r"^[a-z0-9_]{1,20}$")
    balance: int = Field(ge=0)


class FixturePayment(BaseModel):
    id: str
    from_user_id: str
    to_user_id: str
    amount: int = Field(ge=1, le=1_000_000_000)
    note: str = Field(default="", max_length=200)
    visibility: Literal["public", "private"] = "public"


class FixtureRequest(BaseModel):
    id: str
    requester_id: str
    payer_id: str
    amount: int = Field(ge=1, le=1_000_000_000)
    note: str = Field(default="", max_length=200)
    status: Literal["pending", "paid", "declined", "cancelled"] = "pending"


class FixtureAuthorization(BaseModel):
    id: str
    from_user_id: str
    to_user_id: str
    amount: int = Field(ge=1, le=1_000_000_000)
    note: str = Field(default="", max_length=200)
    visibility: Literal["public", "private"] = "public"
    expires_at: Optional[str] = None
    created_at: str


class Fixture(BaseModel):
    currency: Literal["EUR", "JPY", "BHD"]
    minor_units: int = Field(ge=0, le=3)
    users: List[FixtureUser]
    payments: List[FixturePayment] = []
    requests: List[FixtureRequest] = []
    authorizations: List[FixtureAuthorization] = []
    settlement_operator_ids: List[str] = []


# Response models
class SplitShare(BaseModel):
    handle: str
    amount: int


class PaymentResponse(BaseModel):
    payment_id: str
    from_user_id: str
    from_handle: str
    to_user_id: str
    to_handle: str
    amount: int
    currency: str
    note: str
    visibility: Literal["public", "private"]
    request_id: Optional[str] = None
    created_at: datetime
    settlement_id: Optional[str] = None


class RequestResponse(BaseModel):
    request_id: str
    requester_id: str
    requester_handle: str
    payer_id: str
    payer_handle: str
    amount: int
    currency: str
    note: str
    status: Literal["pending", "paid", "declined", "cancelled"]
    payment_id: Optional[str] = None
    created_at: datetime


class SplitRequestResponse(BaseModel):
    request_id: str
    requester_id: str
    requester_handle: str
    payer_id: str
    payer_handle: str
    amount: int
    currency: str
    note: str
    status: Literal["pending", "paid", "declined", "cancelled"]
    payment_id: Optional[str] = None
    created_at: datetime


class SplitResponse(BaseModel):
    split_id: str
    amount: int
    currency: str
    note: str
    shares: List[SplitShare]
    requests: List[SplitRequestResponse]
    created_at: datetime


class SettlementPaymentResponse(BaseModel):
    payment_id: str
    from_user_id: str
    from_handle: str
    to_user_id: str
    to_handle: str
    amount: int
    currency: str
    note: str
    visibility: Literal["public", "private"]
    request_id: Optional[str] = None
    created_at: datetime
    settlement_id: str


class SettlementResponse(BaseModel):
    settlement_id: str
    committed_at: datetime
    payments: List[SettlementPaymentResponse]