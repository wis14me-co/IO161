from typing import List, Dict, Tuple, Optional
from datetime import datetime, timezone

from app.storage import storage, User, Payment, FixturePayment
from app.validation import (
    validate_handle, validate_note, validate_visibility,
    create_error_response, ValidationError
)
from app.settlement.models import SettlementTransfer, SettlementPayment, Settlement, calculate_shares
from app.settlement.schemas import SettlementTransferCreate, SettlementCreate, SettlementResponse, SettlementPaymentResponse


class SettlementService:
    def __init__(self, storage_instance=None):
        self.storage = storage_instance or storage

    def verify_operator(self, user_id: str) -> bool:
        """Verify if user is a settlement operator."""
        return user_id in self.storage.settlement_operator_ids

    def validate_transfer(self, transfer: SettlementTransferCreate) -> Tuple[str, str, int, str, str]:
        """Validate a single transfer and return processed values."""
        from_user = self.storage.get_user_by_handle(transfer.from_handle)
        if not from_user:
            raise ValidationError("not_found", f"User {transfer.from_handle} not found", 404)

        to_user = self.storage.get_user_by_handle(transfer.to_handle)
        if not to_user:
            raise ValidationError("not_found", f"User {transfer.to_handle} not found", 404)

        if from_user.id == to_user.id:
            raise ValidationError("self_payment", "Cannot transfer to yourself", 422)

        amount = transfer.amount
        if not isinstance(amount, int) or amount <= 0:
            raise ValidationError("validation_failed", "Amount must be a positive integer", 422)

        note = validate_note(transfer.note)
        visibility = validate_visibility(transfer.visibility)

        return from_user.id, to_user.id, amount, note, visibility

    def calculate_balances(self, transfers_data: List[dict]) -> Dict[str, int]:
        """Calculate net balance changes for each user from transfers."""
        balance_changes: Dict[str, int] = {}
        for t in transfers_data:
            from_user = self.storage.get_user_by_handle(t["from_handle"])
            to_user = self.storage.get_user_by_handle(t["to_handle"])
            if from_user and to_user:
                balance_changes[from_user.id] = balance_changes.get(from_user.id, 0) - t["amount"]
                balance_changes[to_user.id] = balance_changes.get(to_user.id, 0) + t["amount"]
        return balance_changes

    def check_affordable(self, balance_changes: Dict[str, int]) -> bool:
        """Check if all users can afford their net debits."""
        for user_id, change in balance_changes.items():
            if change < 0:  # net debit
                user = self.storage.get_user_by_id(user_id)
                if user and user.balance + change < 0:
                    return False
        return True

    def execute_settlement(self, user_id: str, transfers_data: List[dict]) -> Tuple[str, str, List[Payment]]:
        """Execute an atomic settlement."""
        from app.idempotency import IdempotencyMiddleware
        
        # Verify operator
        if not self.verify_operator(user_id):
            raise ValidationError("forbidden", "Not a settlement operator", 403)

        # Validate all transfers
        validated_transfers = []
        for transfer_data in transfers_data:
            transfer = SettlementTransferCreate(**transfer_data)
            from_user_id, to_user_id, amount, note, visibility = self.validate_transfer(transfer)
            validated_transfers.append({
                "from_user_id": from_user_id,
                "to_user_id": to_user_id,
                "amount": amount,
                "note": note,
                "visibility": visibility,
                "from_handle": transfer.from_handle,
                "to_handle": transfer.to_handle,
            })

        # Check affordability
        balance_changes = self.calculate_balances(validated_transfers)
        if not self.check_affordable(balance_changes):
            raise ValidationError("insufficient_funds", "Insufficient collective funds", 409)

        # Execute atomic settlement
        settlement_id, committed_at, created_payments = self.storage.atomic_settlement(user_id, validated_transfers)
        return settlement_id, committed_at, created_payments

    def build_response(self, settlement_id: str, committed_at: str, created_payments: List[Payment]) -> SettlementResponse:
        """Build the settlement response."""
        payments = []
        for p in created_payments:
            from_user = self.storage.get_user_by_id(p.from_user_id)
            to_user = self.storage.get_user_by_id(p.to_user_id)
            payments.append(SettlementPaymentResponse(
                payment_id=p.id,
                from_user_id=p.from_user_id,
                from_handle=from_user.handle if from_user else "",
                to_user_id=p.to_user_id,
                to_handle=to_user.handle if to_user else "",
                amount=p.amount,
                currency=self.storage.currency,
                note=p.note,
                visibility=p.visibility,
                request_id=p.request_id,
                settlement_id=settlement_id,
                created_at=p.created_at
            ))

        return SettlementResponse(
            settlement_id=settlement_id,
            committed_at=committed_at,
            payments=payments
        )


settlement_service = SettlementService()