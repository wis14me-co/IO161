from typing import Optional, Tuple
from fastapi import Request, HTTPException, Query
from pydantic import ValidationError
import json
import re


class ValidationError(Exception):
    def __init__(self, code: str, message: str, status_code: int = 422):
        self.code = code
        self.message = message
        self.status_code = status_code
        super().__init__(message)


# Strict integer pattern for query parameters (plain decimal digits only)
STRICT_INT_PATTERN = re.compile(r"^[0-9]+$")


def validate_strict_int(value: str, field_name: str) -> int:
    """Validate query parameter is a plain decimal integer."""
    if not isinstance(value, str) or not STRICT_INT_PATTERN.match(value):
        raise ValidationError("validation_failed", f"{field_name} must be a plain decimal integer", 422)
    try:
        return int(value)
    except ValueError:
        raise ValidationError("validation_failed", f"{field_name} must be a valid integer", 422)


def validate_idempotency_key(key: Optional[str]) -> str:
    if not key or not key.strip():
        raise ValidationError("missing_idempotency_key", "Idempotency-Key header is required", 400)
    if len(key) > 255:
        raise ValidationError("validation_failed", "Idempotency-Key must be at most 255 characters", 422)
    return key.strip()


def validate_amount(amount: int) -> int:
    if not isinstance(amount, int) or amount < 1 or amount > 1_000_000_000:
        raise ValidationError("validation_failed", "amount must be integer 1..1000000000", 422)
    return amount


def validate_handle(handle: str) -> str:
    if not isinstance(handle, str) or not handle:
        raise ValidationError("validation_failed", "handle is required", 422)
    import re
    if not re.match(r"^[a-z0-9_]{1,20}$", handle):
        raise ValidationError("validation_failed", "invalid handle format", 422)
    return handle


def validate_note(note: str) -> str:
    if note is None:
        return ""
    if not isinstance(note, str):
        raise ValidationError("validation_failed", "note must be a string", 422)
    if len(note) > 200:
        raise ValidationError("validation_failed", "note must be at most 200 characters", 422)
    return note


def validate_visibility(visibility: str) -> str:
    if visibility not in ("public", "private"):
        raise ValidationError("validation_failed", "visibility must be public or private", 422)
    return visibility


def validate_limit_offset(limit: int, offset: int) -> Tuple[int, int]:
    if not isinstance(limit, int) or limit < 1 or limit > 200:
        raise ValidationError("validation_failed", "limit must be integer 1..200", 422)
    if not isinstance(offset, int) or offset < 0:
        raise ValidationError("validation_failed", "offset must be integer >= 0", 422)
    return limit, offset


def validate_direction(direction: Optional[str]) -> Optional[str]:
    if direction is not None and direction not in ("incoming", "outgoing"):
        raise ValidationError("validation_failed", "direction must be incoming or outgoing", 422)
    return direction


def validate_status(status: Optional[str]) -> Optional[str]:
    if status is not None and status not in ("pending", "paid", "declined", "cancelled"):
        raise ValidationError("validation_failed", "status must be pending, paid, declined, or cancelled", 422)
    return status


def validate_authorization_status(status: Optional[str]) -> Optional[str]:
    if status is not None and status not in ("open", "captured", "voided", "expired"):
        raise ValidationError("validation_failed", "status must be open, captured, voided, or expired", 422)
    return status


def validate_participant_handles(handles: list) -> list:
    if not handles or not isinstance(handles, list):
        raise ValidationError("validation_failed", "participant_handles must be a non-empty array", 422)
    if len(handles) != len(set(handles)):
        raise ValidationError("validation_failed", "participant_handles contains duplicates", 422)
    import re
    for h in handles:
        if not isinstance(h, str) or not re.match(r"^[a-z0-9_]{1,20}$", h):
            raise ValidationError("validation_failed", "invalid handle format", 422)
    return handles


def validate_email(email: str) -> str:
    if not isinstance(email, str) or not email:
        raise ValidationError("validation_failed", "email is required", 422)
    import re
    if not re.match(r"^[^@]+@[^@]+\.[^@]+$", email):
        raise ValidationError("validation_failed", "invalid email format", 422)
    return email.lower()


def validate_password(password: str) -> str:
    if not isinstance(password, str) or len(password) < 8:
        raise ValidationError("validation_failed", "password must be at least 8 characters", 422)
    return password


def validate_display_name(display_name: str) -> str:
    if not isinstance(display_name, str) or not display_name or len(display_name) > 100:
        raise ValidationError("validation_failed", "display_name must be 1-100 characters", 422)
    return display_name


def parse_json_body(request: Request) -> dict:
    try:
        return request.json()
    except json.JSONDecodeError:
        raise ValidationError("malformed_request", "Invalid JSON body", 400)
    except Exception:
        raise ValidationError("malformed_request", "Invalid request body", 400)


def create_error_response(code: str, message: str, status_code: int = 422) -> dict:
    return {"error": {"code": code, "message": message}}