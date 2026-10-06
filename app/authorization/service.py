from typing import List, Optional, Tuple
from datetime import datetime, timezone

from app.storage import storage, User, Payment, Authorization
from app.validation import (
    validate_handle, validate_note, validate_visibility, validate_direction,
    create_error_response, ValidationError, validate_authorization_status
)
from app.authorization.models import Authorization
from app.authorization.schemas import AuthorizationCreate, AuthorizationResponse, AuthorizationListResponse, AuthorizationCapture


class AuthorizationService:
    def __init__(self, storage_instance=None):
        self.storage = storage_instance or storage

    def create_authorization(
        self,
        from_user_id: str,
        to_handle: str,
        amount: int,
        note: str,
        visibility: str,
        expires_at: Optional[str] = None
    ) -> Authorization:
        """Create a new authorization."""
        from_user = self.storage.get_user_by_id(from_user_id)
        if not from_user:
            raise ValidationError("not_found", "User not found", 404)

        to_user = self.storage.get_user_by_handle(to_handle)
        if not to_user:
            raise ValidationError("not_found", "Recipient not found", 404)

        if to_user.id == from_user_id:
            raise ValidationError("self_auth", "Cannot create authorization to yourself", 422)

        if not isinstance(amount, int) or amount <= 0:
            raise ValidationError("validation_failed", "Amount must be a positive integer", 422)

        note = validate_note(note)
        visibility = validate_visibility(visibility)

        # Validate expires_at format if provided (RFC3339)
        if expires_at is not None:
            try:
                datetime.fromisoformat(expires_at.replace("Z", "+00:00"))
            except ValueError:
                raise ValidationError("validation_failed", "expires_at must be a valid RFC 3339 timestamp", 422)

        # Check available funds (balance - held)
        auths = self.storage.get_authorizations_for_user(from_user_id, direction="outgoing", status="open")
        held = sum(a.remaining_amount for a in auths)
        available = max(0, from_user.balance - held)

        if available < amount:
            raise ValidationError("insufficient_funds", "Insufficient funds", 409)

        # Determine expires_at: use provided or calculate from authorization_ttl_seconds
        if expires_at is None:
            ttl = getattr(self.storage, 'authorization_ttl_seconds', 600)
            from datetime import datetime, timezone, timedelta
            expires_at = (datetime.now(timezone.utc) + timedelta(seconds=ttl)).isoformat().replace("+00:00", "Z")

        # Create authorization
        auth = self.storage.create_authorization(
            from_user_id=from_user_id,
            to_user_id=to_user.id,
            amount=amount,
            note=note,
            visibility=visibility,
            expires_at=expires_at
        )

        return auth

    def void_authorization(self, auth_id: str, user_id: str) -> Authorization:
        """Void an authorization (payer only)."""
        auth = self.storage.get_authorization(auth_id)
        if not auth:
            raise ValidationError("not_found", "Authorization not found", 404)

        if auth.status != "open":
            raise ValidationError("authorization_not_open", "Authorization is not open", 409)

        # Only the payer can void
        from_user = self.storage.get_user_by_id(auth.from_user_id)
        if not from_user:
            raise ValidationError("not_found", "Payer not found", 404)

        if from_user.id != user_id:
            raise ValidationError("forbidden", "Not the payer", 403)

        auth = self.storage.update_authorization_status(auth_id, "voided")
        return auth

    def capture_authorization(
        self,
        auth_id: str,
        to_user_id: str,
        capture_data: AuthorizationCapture,
        visibility: str = "public"
    ) -> Tuple[Payment, Authorization]:
        """Capture an authorization (receiver only)."""
        auth = self.storage.get_authorization(auth_id)
        if not auth:
            raise ValidationError("not_found", "Authorization not found", 404)

        if not auth.is_open_and_valid():
            if auth.status != "open":
                raise ValidationError("authorization_not_open", "Authorization is not open", 409)
            else:
                raise ValidationError("authorization_expired", "Authorization has expired", 409)

        # Only the receiver can capture
        if auth.to_user_id != to_user_id:
            raise ValidationError("forbidden", "Not the receiver", 403)

        # Determine capture amount
        remaining = auth.remaining_amount
        capture_amount = capture_data.amount if capture_data.amount is not None else remaining
        is_final = capture_data.final

        if capture_amount > remaining:
            raise ValidationError("capture_exceeds_authorization", "Capture amount exceeds authorization remainder", 422)
        if capture_amount < 1:
            raise ValidationError("validation_failed", "Amount must be at least 1", 422)

        # Check if this would be a final capture (either explicitly or by capturing all remainder)
        will_be_final = is_final or (capture_amount >= remaining)

        # Transfer funds (from payer to receiver)
        try:
            self.storage.atomic_transfer(auth.from_user_id, to_user_id, capture_amount)
        except ValueError as e:
            if str(e) == "insufficient_funds":
                raise ValidationError("insufficient_funds", "Insufficient Funds", 409)
            raise

        # Create payment
        payment_obj = self.storage.create_payment(
            from_user_id=auth.from_user_id,
            to_user_id=to_user_id,
            amount=capture_amount,
            note=auth.note,
            visibility=auth.visibility,
            request_id=auth_id
        )

        # Update authorization - build updated payment_ids list
        new_captured = auth.captured_amount + capture_amount
        new_status = "captured" if will_be_final else "open"
        updated_payment_ids = list(auth.payment_ids)
        if payment_obj.id not in updated_payment_ids:
            updated_payment_ids.append(payment_obj.id)
        
        auth = self.storage.update_authorization_status(
            auth_id,
            new_status,
            captured_amount=new_captured,
            payment_id=payment_obj.id,
            payment_ids=updated_payment_ids
        )

        return payment_obj, auth

    def list_authorizations(
        self,
        user_id: str,
        direction: Optional[str] = None,
        status: Optional[str] = None,
        limit: int = 50,
        offset: int = 0
    ) -> AuthorizationListResponse:
        """List authorizations for a user."""
        validate_direction(direction)
        validate_authorization_status(status)

        auths = self.storage.get_authorizations_for_user(user_id, direction, status, limit, offset)

        result = []
        from datetime import datetime, timezone
        now = datetime.now(timezone.utc)
        
        for auth in auths:
            # Check if expired - expired authorizations must show status=expired
            auth_status = auth.status
            if auth.status == "open" and auth.expires_at:
                try:
                    expires = datetime.fromisoformat(auth.expires_at.replace("Z", "+00:00"))
                    if expires <= now:
                        auth_status = "expired"
                except ValueError:
                    pass
            
            from_user = self.storage.get_user_by_id(auth.from_user_id)
            to_user = self.storage.get_user_by_id(auth.to_user_id)
            result.append(AuthorizationResponse(
                id=auth.id,
                from_user_id=auth.from_user_id,
                to_user_id=auth.to_user_id,
                amount=auth.amount,
                captured_amount=auth.captured_amount,
                note=auth.note,
                visibility=auth.visibility,
                status=auth_status,
                expires_at=auth.expires_at,
                created_at=auth.created_at,
                remaining_amount=auth.remaining_amount,
                payment_id=auth.payment_id,
                payment_ids=auth.payment_ids
            ))

        # Check if there are more items by fetching one extra
        has_more = False
        if len(result) == limit:
            extra_auths = self.storage.get_authorizations_for_user(user_id, direction, status, 1, offset + limit)
            has_more = len(extra_auths) > 0

        return AuthorizationListResponse(authorizations=result, has_more=has_more)


authorization_service = AuthorizationService()