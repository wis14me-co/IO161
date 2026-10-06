from dataclasses import dataclass, field
from typing import Optional, List
from datetime import datetime, timezone


@dataclass
class Authorization:
    id: str
    from_user_id: str
    to_user_id: str
    amount: int
    captured_amount: int = 0
    note: str = ""
    visibility: str = "public"
    status: str = "open"  # open, captured, voided, expired
    expires_at: str = ""
    created_at: str = ""
    payment_id: Optional[str] = None
    payment_ids: List[str] = field(default_factory=list)

    @property
    def remaining_amount(self) -> int:
        return self.amount - self.captured_amount

    def to_dict(self) -> dict:
        return {
            "id": self.id,
            "from_user_id": self.from_user_id,
            "to_user_id": self.to_user_id,
            "amount": self.amount,
            "captured_amount": self.captured_amount,
            "note": self.note,
            "visibility": self.visibility,
            "status": self.status,
            "expires_at": self.expires_at,
            "created_at": self.created_at,
            "remaining_amount": self.remaining_amount,
            "payment_id": self.payment_id,
            "payment_ids": self.payment_ids,
        }

    def is_open_and_valid(self) -> bool:
        """Check if authorization is open and not expired."""
        if self.status != "open":
            return False
        if self.expires_at:
            try:
                expires = datetime.fromisoformat(self.expires_at.replace("Z", "+00:00"))
                if expires <= datetime.now(timezone.utc):
                    return False
            except ValueError:
                pass
        return True