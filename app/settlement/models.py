from dataclasses import dataclass, field
from typing import Optional, List
from datetime import datetime, timezone


@dataclass
class SettlementTransfer:
    from_handle: str
    to_handle: str
    amount: int
    note: str = ""
    visibility: str = "public"


@dataclass
class SettlementPayment:
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
    created_at: str = ""

    def to_dict(self) -> dict:
        return {
            "payment_id": self.payment_id,
            "from_user_id": self.from_user_id,
            "from_handle": self.from_handle,
            "to_user_id": self.to_user_id,
            "to_handle": self.to_handle,
            "amount": self.amount,
            "currency": self.currency,
            "note": self.note,
            "visibility": self.visibility,
            "request_id": self.request_id,
            "settlement_id": self.settlement_id,
            "created_at": self.created_at,
        }


@dataclass
class Settlement:
    settlement_id: str
    committed_at: str
    payments: List[SettlementPayment] = field(default_factory=list)


def calculate_shares(amount: int, n: int) -> List[int]:
    """Calculate equal shares that sum to amount, with larger shares first."""
    base = amount // n
    remainder = amount % n
    return [base + 1 if i < remainder else base for i in range(n)]