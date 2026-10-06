from pydantic import BaseModel, Field, field_validator
from typing import Optional, List, Literal
from datetime import datetime
import re


class ErrorResponse(BaseModel):
    error: "ErrorDetail"


class ErrorDetail(BaseModel):
    code: str
    message: str


class UserBase(BaseModel):
    id: str
    email: str
    display_name: str
    handle: str


class UserCreate(BaseModel):
    email: str
    password: str
    display_name: str

    @field_validator("email")
    @classmethod
    def validate_email(cls, v: str) -> str:
        if not re.match(r"^[^@]+@[^@]+\.[^@]+$", v):
            raise ValueError("invalid email format")
        return v.lower()

    @field_validator("password")
    @classmethod
    def validate_password(cls, v: str) -> str:
        if len(v) < 8:
            raise ValueError("password must be at least 8 characters")
        return v

    @field_validator("display_name")
    @classmethod
    def validate_display_name(cls, v: str) -> str:
        if not v or len(v) > 100:
            raise ValueError("display_name must be 1-100 characters")
        return v


class UserLogin(BaseModel):
    email: str
    password: str


class TokenResponse(BaseModel):
    user_id: str
    display_name: str
    token: str


class MeResponse(BaseModel):
    user_id: str
    display_name: str
    handle: str
    balance: int
    total: int
    available: int
    held: int
    currency: str
    minor_units: int


class PaymentCreate(BaseModel):
    to_handle: str
    amount: int
    note: str = ""
    visibility: Literal["public", "private"] = "public"

    @field_validator("amount")
    @classmethod
    def validate_amount(cls, v: int) -> int:
        if not isinstance(v, int) or v < 1 or v > 1_000_000_000:
            raise ValueError("amount must be integer 1..1000000000")
        return v

    @field_validator("note")
    @classmethod
    def validate_note(cls, v: str) -> str:
        if len(v) > 200:
            raise ValueError("note must be at most 200 characters")
        return v

    @field_validator("to_handle")
    @classmethod
    def validate_to_handle(cls, v: str) -> str:
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
    visibility: Literal["public", "private"]
    request_id: Optional[str]
    created_at: str


class RequestCreate(BaseModel):
    payer_handle: str
    amount: int
    note: str = ""

    @field_validator("amount")
    @classmethod
    def validate_amount(cls, v: int) -> int:
        if not isinstance(v, int) or v < 1 or v > 1_000_000_000:
            raise ValueError("amount must be integer 1..1000000000")
        return v

    @field_validator("note")
    @classmethod
    def validate_note(cls, v: str) -> str:
        if len(v) > 200:
            raise ValueError("note must be at most 200 characters")
        return v

    @field_validator("payer_handle")
    @classmethod
    def validate_payer_handle(cls, v: str) -> str:
        if not re.match(r"^[a-z0-9_]{1,20}$", v):
            raise ValueError("invalid handle format")
        return v


class RequestPay(BaseModel):
    visibility: Literal["public", "private"] = "public"


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
    payment_id: Optional[str]
    created_at: str


class RequestListResponse(BaseModel):
    requests: List[RequestResponse]
    has_more: bool


class SplitCreate(BaseModel):
    amount: int
    participant_handles: List[str]
    note: str = ""

    @field_validator("amount")
    @classmethod
    def validate_amount(cls, v: int) -> int:
        if not isinstance(v, int) or v < 1 or v > 1_000_000_000:
            raise ValueError("amount must be integer 1..1000000000")
        return v

    @field_validator("participant_handles")
    @classmethod
    def validate_participant_handles(cls, v: List[str]) -> List[str]:
        if not v:
            raise ValueError("participant_handles cannot be empty")
        if len(v) != len(set(v)):
            raise ValueError("participant_handles contains duplicates")
        for handle in v:
            if not re.match(r"^[a-z0-9_]{1,20}$", handle):
                raise ValueError("invalid handle format")
        return v

    @field_validator("note")
    @classmethod
    def validate_note(cls, v: str) -> str:
        if len(v) > 200:
            raise ValueError("note must be at most 200 characters")
        return v


class SplitShare(BaseModel):
    handle: str
    amount: int


class SplitResponse(BaseModel):
    split_id: str
    amount: int
    currency: str
    note: str
    shares: List[SplitShare]
    requests: List[RequestResponse]
    created_at: str


class ActivityResponse(BaseModel):
    payments: List[PaymentResponse]
    has_more: bool


class SettlementTransfer(BaseModel):
    from_handle: str
    to_handle: str
    amount: int
    note: str = ""
    visibility: Literal["public", "private"] = "public"

    @field_validator("amount")
    @classmethod
    def validate_amount(cls, v: int) -> int:
        if not isinstance(v, int) or v < 1 or v > 1_000_000_000:
            raise ValueError("amount must be integer 1..1000000000")
        return v

    @field_validator("note")
    @classmethod
    def validate_note(cls, v: str) -> str:
        if len(v) > 200:
            raise ValueError("note must be at most 200 characters")
        return v

    @field_validator("from_handle", "to_handle")
    @classmethod
    def validate_handles(cls, v: str) -> str:
        if not re.match(r"^[a-z0-9_]{1,20}$", v):
            raise ValueError("invalid handle format")
        return v


class SettlementCreate(BaseModel):
    transfers: List[SettlementTransfer]

    @field_validator("transfers")
    @classmethod
    def validate_transfers(cls, v: List[SettlementTransfer]) -> List[SettlementTransfer]:
        if not v or len(v) > 32:
            raise ValueError("transfers must have 1..32 entries")
        return v


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
    request_id: Optional[str]
    created_at: str
    settlement_id: str


class SettlementResponse(BaseModel):
    settlement_id: str
    committed_at: str
    payments: List[SettlementPaymentResponse]


class HealthResponse(BaseModel):
    status: Literal["ok"]


# Authorization models
class AuthorizationCreate(BaseModel):
    to_handle: str
    amount: int
    note: str = ""
    visibility: Literal["public", "private"] = "public"
    expires_at: Optional[str] = None

    @field_validator("amount")
    @classmethod
    def validate_amount(cls, v: int) -> int:
        if not isinstance(v, int) or v < 1 or v > 1_000_000_000:
            raise ValueError("amount must be integer 1..1000000000")
        return v

    @field_validator("note")
    @classmethod
    def validate_note(cls, v: str) -> str:
        if len(v) > 200:
            raise ValueError("note must be at most 200 characters")
        return v

    @field_validator("to_handle")
    @classmethod
    def validate_to_handle(cls, v: str) -> str:
        if not re.match(r"^[a-z0-9_]{1,20}$", v):
            raise ValueError("invalid handle format")
        return v

    @field_validator("expires_at")
    @classmethod
    def validate_expires_at(cls, v: Optional[str]) -> Optional[str]:
        if v is None:
            return v
        try:
            datetime.fromisoformat(v.replace("Z", "+00:00"))
        except ValueError:
            raise ValueError("expires_at must be valid ISO 8601 datetime")
        return v


class AuthorizationCapture(BaseModel):
    amount: Optional[int] = None
    final: bool = False

    @field_validator("amount")
    @classmethod
    def validate_amount(cls, v: Optional[int]) -> Optional[int]:
        if v is not None and (not isinstance(v, int) or v < 1 or v > 1_000_000_000):
            raise ValueError("amount must be integer 1..1000000000")
        return v


class AuthorizationResponse(BaseModel):
    authorization_id: str
    from_user_id: str
    from_handle: str
    to_user_id: str
    to_handle: str
    amount: int
    captured_amount: int
    remaining_amount: int
    note: str
    visibility: Literal["public", "private"]
    status: Literal["open", "captured", "voided", "expired"]
    expires_at: Optional[str]
    payment_id: Optional[str]
    payment_ids: List[str]
    created_at: str


class AuthorizationListResponse(BaseModel):
    authorizations: List[AuthorizationResponse]
    has_more: bool


class FixtureUser(BaseModel):
    id: str
    email: str
    password: str
    display_name: str
    handle: str
    balance: int


class FixturePayment(BaseModel):
    id: str
    from_user_id: str
    to_user_id: str
    amount: int
    note: str
    visibility: Literal["public", "private"]


class FixtureRequest(BaseModel):
    id: str
    requester_id: str
    payer_id: str
    amount: int
    note: str
    status: Literal["pending", "paid", "declined", "cancelled"]


class FixtureAuthorization(BaseModel):
    id: str
    from_user_id: str
    to_user_id: str
    amount: int
    captured_amount: int
    note: str
    visibility: Literal["public", "private"]
    status: Literal["open", "captured", "voided", "expired"]
    expires_at: Optional[str]
    payment_id: Optional[str]
    payment_ids: List[str]
    remaining_amount: int
    created_at: str


class Fixture(BaseModel):
    currency: str
    minor_units: int
    users: List[FixtureUser]
    payments: List[FixturePayment] = []
    requests: List[FixtureRequest] = []
    authorizations: List[FixtureAuthorization] = []
    settlement_operator_ids: List[str] = []
    authorization_ttl_seconds: Optional[int] = None

    @field_validator("minor_units")
    @classmethod
    def validate_minor_units(cls, v: int) -> int:
        if v not in (0, 2, 3):
            raise ValueError("minor_units must be 0, 2, or 3")
        return v

    @field_validator("currency")
    @classmethod
    def validate_currency(cls, v: str) -> str:
        if not v or len(v) != 3:
            raise ValueError("currency must be 3-letter code")
        return v.upper()


class ExportResponse(BaseModel):
    track: Literal["pocketful"]
    format_version: int
    state: dict


class ImportRequest(BaseModel):
    track: Literal["pocketful"]
    format_version: int
    state: dict


# Pagination params
class PaginationParams(BaseModel):
    limit: int = 50
    offset: int = 0

    @field_validator("limit")
    @classmethod
    def validate_limit(cls, v: int) -> int:
        if not isinstance(v, int) or v < 1 or v > 200:
            raise ValueError("limit must be integer 1..200")
        return v

    @field_validator("offset")
    @classmethod
    def validate_offset(cls, v: int) -> int:
        if not isinstance(v, int) or v < 0:
            raise ValueError("offset must be integer >= 0")
        return v


class RequestQueryParams(PaginationParams):
    direction: Optional[Literal["incoming", "outgoing"]] = None
    status: Optional[Literal["pending", "paid", "declined", "cancelled"]] = None


class AuthorizationQueryParams(PaginationParams):
    direction: Optional[Literal["incoming", "outgoing"]] = None
    status: Optional[Literal["open", "captured", "voided", "expired"]] = None