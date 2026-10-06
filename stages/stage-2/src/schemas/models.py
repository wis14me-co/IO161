"""Pydantic validation schemas for all API endpoints."""

from datetime import datetime
from typing import List, Optional, Literal, Dict, Any
from pydantic import BaseModel, Field, field_validator, model_validator
from typing_extensions import Annotated

from src.utils.currency import CURRENCY_MINOR_UNITS, parse_amount, format_amount, CurrencyError


# Shared validators and types
HandleStr = Annotated[str, Field(pattern=r"^[a-z0-9_]{1,20}$")]
NoteStr = Annotated[str, Field(max_length=200)]
VisibilityStr = Literal["public", "private"]
IdempotencyKeyStr = Annotated[str, Field(min_length=1, max_length=255)]
AmountInt = Annotated[int, Field(ge=1, le=1_000_000_000)]
LimitInt = Annotated[int, Field(ge=1, le=200)]
OffsetInt = Annotated[int, Field(ge=0)]


class ErrorResponse(BaseModel):
    """Standard error response format."""
    error: Dict[str, str] = Field(..., example={"code": "insufficient_funds", "message": "Insufficient funds"})


# Auth schemas
class SignupRequest(BaseModel):
    email: str = Field(..., pattern=r"^[^@]+@[^@]+\.[^@]+$")
    password: str = Field(..., min_length=8)
    display_name: str = Field(..., min_length=1, max_length=100)
    
    @field_validator("email")
    @classmethod
    def validate_email(cls, v: str) -> str:
        if v.count("@") != 1:
            raise ValueError("Invalid email format")
        local, domain = v.split("@")
        if not local or not domain or "." not in domain:
            raise ValueError("Invalid email format")
        return v.lower()


class LoginRequest(BaseModel):
    email: str = Field(..., pattern=r"^[^@]+@[^@]+\.[^@]+$")
    password: str
    
    @field_validator("email")
    @classmethod
    def validate_email(cls, v: str) -> str:
        return v.lower()


class AuthResponse(BaseModel):
    user_id: str
    display_name: str
    token: str


# User schemas
class UserResponse(BaseModel):
    user_id: str
    display_name: str
    handle: str
    balance: int
    currency: str
    minor_units: int


# Payment schemas
class PaymentRequest(BaseModel):
    to_handle: HandleStr
    amount: AmountInt
    note: NoteStr = ""
    visibility: VisibilityStr = "public"
    
    @model_validator(mode="after")
    def validate_self_payment(self) -> "PaymentRequest":
        # Self-payment validation happens at endpoint level with current user
        return self


class PaymentResponse(BaseModel):
    payment_id: str
    from_user_id: str
    from_handle: str
    to_user_id: str
    to_handle: str
    amount: int
    currency: str
    note: str
    visibility: VisibilityStr
    request_id: Optional[str] = None
    created_at: datetime
    settlement_id: Optional[str] = None


# Request schemas
class RequestCreate(BaseModel):
    payer_handle: HandleStr
    amount: AmountInt
    note: NoteStr = ""
    
    @model_validator(mode="after")
    def validate_self_request(self) -> "RequestCreate":
        # Self-request validation happens at endpoint level with current user
        return self


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


class RequestListParams(BaseModel):
    direction: Optional[Literal["incoming", "outgoing"]] = None
    status: Optional[Literal["pending", "paid", "declined", "cancelled"]] = None
    limit: LimitInt = 50
    offset: OffsetInt = 0


class RequestListResponse(BaseModel):
    requests: List[RequestResponse]
    has_more: bool


class RequestActionResponse(BaseModel):
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


class PayRequestRequest(BaseModel):
    visibility: VisibilityStr = "public"


# Split schemas
class SplitRequest(BaseModel):
    amount: AmountInt
    participant_handles: List[HandleStr] = Field(..., min_length=1)
    note: NoteStr = ""
    
    @field_validator("participant_handles")
    @classmethod
    def validate_unique_handles(cls, v: List[str]) -> List[str]:
        if len(v) != len(set(v)):
            raise ValueError("Duplicate handles in participant_handles")
        return v


class SplitShare(BaseModel):
    handle: str
    amount: int


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


# Settlement schemas
class SettlementTransfer(BaseModel):
    from_handle: HandleStr
    to_handle: HandleStr
    amount: AmountInt
    note: NoteStr = ""
    visibility: VisibilityStr = "public"
    
    @model_validator(mode="after")
    def validate_self_transfer(self) -> "SettlementTransfer":
        if self.from_handle == self.to_handle:
            raise ValueError("Self transfer not allowed")
        return self


class SettlementRequest(BaseModel):
    transfers: List[SettlementTransfer] = Field(..., min_length=1, max_length=32)


class SettlementPaymentResponse(BaseModel):
    payment_id: str
    from_user_id: str
    from_handle: str
    to_user_id: str
    to_handle: str
    amount: int
    currency: str
    note: str
    visibility: VisibilityStr
    request_id: Optional[str] = None
    created_at: datetime
    settlement_id: str


class SettlementResponse(BaseModel):
    settlement_id: str
    committed_at: datetime
    payments: List[SettlementPaymentResponse]


# Activity schemas
class ActivityParams(BaseModel):
    limit: LimitInt = 50
    offset: OffsetInt = 0


class ActivityResponse(BaseModel):
    payments: List[PaymentResponse]
    has_more: bool


# Test fixture schemas
class FixtureUser(BaseModel):
    id: str
    email: str
    password: str
    display_name: str
    handle: HandleStr
    balance: Annotated[int, Field(ge=0)]
    
    @field_validator("password")
    @classmethod
    def validate_password(cls, v: str) -> str:
        if len(v) < 8:
            raise ValueError("Password must be at least 8 characters")
        return v


class FixturePayment(BaseModel):
    id: str
    from_user_id: str
    to_user_id: str
    amount: AmountInt
    note: NoteStr = ""
    visibility: VisibilityStr = "public"


class FixtureRequest(BaseModel):
    id: str
    requester_id: str
    payer_id: str
    amount: AmountInt
    note: NoteStr = ""
    status: Literal["pending", "paid", "declined", "cancelled"] = "pending"


class FixtureResetRequest(BaseModel):
    currency: Literal["EUR", "JPY", "BHD"]
    minor_units: int
    users: List[FixtureUser] = Field(..., min_length=1)
    payments: List[FixturePayment] = []
    requests: List[FixtureRequest] = []
    settlement_operator_ids: List[str] = []
    
    @model_validator(mode="after")
    def validate_currency_minor_units(self) -> "FixtureResetRequest":
        expected_minor = CURRENCY_MINOR_UNITS.get(self.currency)
        if expected_minor is None:
            raise ValueError(f"Unsupported currency: {self.currency}")
        if self.minor_units != expected_minor:
            raise ValueError(f"minor_units must be {expected_minor} for {self.currency}")
        return self
    
    @model_validator(mode="after")
    def validate_balances_non_negative(self) -> "FixtureResetRequest":
        # Check all user balances are non-negative
        for user in self.users:
            if user.balance < 0:
                raise ValueError(f"User {user.id} has negative balance")
        return self


# Export/Import schemas
class ExportResponse(BaseModel):
    track: Literal["pocketful"] = "pocketful"
    format_version: int = 1
    state: Dict[str, Any]


class ImportRequest(BaseModel):
    track: Literal["pocketful"] = "pocketful"
    format_version: int = 1
    state: Dict[str, Any]
    
    @field_validator("track")
    @classmethod
    def validate_track(cls, v: str) -> str:
        if v != "pocketful":
            raise ValueError("Invalid track")
        return v
    
    @field_validator("format_version")
    @classmethod
    def validate_version(cls, v: int) -> int:
        if v != 1:
            raise ValueError("Unsupported format version")
        return v


# Health check
class HealthResponse(BaseModel):
    status: Literal["ok"] = "ok"


# Utility functions for validation
def validate_idempotency_key(key: Optional[str]) -> str:
    """Validate and return idempotency key."""
    if not key or not key.strip():
        raise ValueError("missing_idempotency_key")
    if len(key) > 255:
        raise ValueError("validation_failed")
    return key


def validate_amount_field(amount: Any, field_name: str = "amount") -> int:
    """Validate amount field is integer in valid range."""
    if not isinstance(amount, int):
        raise ValueError(f"{field_name} must be an integer")
    if amount < 1 or amount > 1_000_000_000:
        raise ValueError(f"{field_name} out of range")
    return amount


def validate_handle(handle: str) -> str:
    """Validate handle format."""
    if not isinstance(handle, str):
        raise ValueError("Handle must be a string")
    if not handle or len(handle) > 20:
        raise ValueError("Invalid handle length")
    if not all(c.islower() or c.isdigit() or c == "_" for c in handle):
        raise ValueError("Invalid handle characters")
    return handle


def validate_note(note: Any) -> str:
    """Validate note field."""
    if not isinstance(note, str):
        raise ValueError("Note must be a string")
    if len(note) > 200:
        raise ValueError("Note too long")
    return note


def validate_visibility(visibility: Any) -> str:
    """Validate visibility field."""
    if not isinstance(visibility, str):
        raise ValueError("Visibility must be a string")
    if visibility not in ("public", "private"):
        raise ValueError("Invalid visibility")
    return visibility


def validate_limit_offset(limit: Any, offset: Any) -> tuple[int, int]:
    """Validate limit and offset query parameters."""
    try:
        limit_int = int(limit) if limit is not None else 50
        offset_int = int(offset) if offset is not None else 0
    except (ValueError, TypeError):
        raise ValueError("validation_failed")
    
    if not (1 <= limit_int <= 200):
        raise ValueError("validation_failed")
    if offset_int < 0:
        raise ValueError("validation_failed")
    
    return limit_int, offset_int