from typing import Optional
from app.storage import storage, Payment
from app.validation import ValidationError, validate_handle, validate_note, validate_visibility


class PaymentService:
    def __init__(self, storage_instance=None):
        self.storage = storage_instance or storage

    def create_payment(
        self,
        from_user_id: str,
        to_handle: str,
        amount: int,
        note: str,
        visibility: str
    ) -> Payment:
        """Create a new payment."""
        from_user = self.storage.get_user_by_id(from_user_id)
        if not from_user:
            raise ValidationError("not_found", "User not found", 404)

        to_user = self.storage.get_user_by_handle(to_handle)
        if not to_user:
            raise ValidationError("not_found", "Recipient not found", 404)

        if to_user.id == from_user_id:
            raise ValidationError("self_payment", "Cannot pay yourself", 422)

        note = validate_note(note)
        visibility = validate_visibility(visibility)

        # Check balance
        if from_user.balance < amount:
            raise ValidationError("insufficient_funds", "Insufficient funds", 409)

        # Transfer funds
        try:
            self.storage.atomic_transfer(from_user_id, to_user.id, amount)
        except ValueError as e:
            if str(e) == "insufficient_funds":
                raise ValidationError("insufficient_funds", "Insufficient Funds", 409)
            raise

        # Create payment record
        payment_obj = self.storage.create_payment(
            from_user_id=from_user_id,
            to_user_id=to_user.id,
            amount=amount,
            note=note,
            visibility=visibility,
            request_id=None
        )

        return payment_obj


payment_service = PaymentService()