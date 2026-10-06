"""
Unit tests for settlement service.
"""
import pytest
from app.settlement.service import SettlementService
from app.settlement.schemas import SettlementTransferCreate, SettlementCreate
from app.validation import ValidationError
from app.storage import User, Payment


class TestSettlementService:
    """Test SettlementService class."""

    def test_settlement_service_initialization(self, storage):
        """Should initialize settlement service with storage."""
        service = SettlementService(storage)
        assert service.storage == storage

    def test_verify_operator_success(self, storage):
        """Should verify operator successfully."""
        service = SettlementService(storage)
        operator_id = "operator_1"

        # Add operator
        storage.settlement_operator_ids.add(operator_id)

        result = service.verify_operator(operator_id)
        assert result is True

    def test_verify_operator_failure(self, storage):
        """Should fail to verify non-operator."""
        service = SettlementService(storage)
        operator_id = "operator_1"

        result = service.verify_operator(operator_id)
        assert result is False

    def test_verify_operator_empty_list(self, storage):
        """Should fail when operator list is empty."""
        service = SettlementService(storage)

        result = service.verify_operator("any_user")
        assert result is False

    def test_validate_transfer_valid(self, storage):
        """Should validate transfer successfully."""
        service = SettlementService(storage)
        test_user = storage.create_user(
            email="transfer1@example.com",
            password="password123",
            display_name="Transfer User 1",
            handle="transfer1"
        )
        another_user = storage.create_user(
            email="transfer2@example.com",
            password="password123",
            display_name="Transfer User 2",
            handle="transfer2"
        )

        transfer = SettlementTransferCreate(
            from_handle=test_user.handle,
            to_handle=another_user.handle,
            amount=100,
            note="Test transfer",
            visibility="public"
        )

        result = service.validate_transfer(transfer)
        assert result[0] == test_user.id
        assert result[1] == another_user.id
        assert result[2] == 100
        assert result[3] == "Test transfer"
        assert result[4] == "public"

    def test_validate_transfer_user_not_found(self, storage):
        """Should fail when user not found."""
        service = SettlementService(storage)

        transfer = SettlementTransferCreate(
            from_handle="nonexistent",
            to_handle="another_nonexistent",
            amount=100,
            note="Test transfer"
        )

        with pytest.raises(ValidationError) as exc_info:
            service.validate_transfer(transfer)
        assert exc_info.value.code == "not_found"

    def test_validate_transfer_self_payment(self, storage):
        """Should fail when transferring to self."""
        service = SettlementService(storage)
        test_user = storage.create_user(
            email="selftransfer@example.com",
            password="password123",
            display_name="Self Transfer",
            handle="selftransfer"
        )

        transfer = SettlementTransferCreate(
            from_handle=test_user.handle,
            to_handle=test_user.handle,
            amount=100,
            note="Test transfer"
        )

        with pytest.raises(ValidationError) as exc_info:
            service.validate_transfer(transfer)
        assert exc_info.value.code == "self_payment"

    def test_validate_transfer_invalid_amount(self, storage):
        """Should fail with invalid amount."""
        service = SettlementService(storage)
        test_user = storage.create_user(
            email="amounttest@example.com",
            password="password123",
            display_name="Amount Test",
            handle="amounttest"
        )
        another_user = storage.create_user(
            email="amounttest2@example.com",
            password="password123",
            display_name="Amount Test 2",
            handle="amounttest2"
        )

        transfer = SettlementTransferCreate.model_construct(
            from_handle=test_user.handle,
            to_handle=another_user.handle,
            amount=0,
            note="Test transfer"
        )

        with pytest.raises(ValidationError) as exc_info:
            service.validate_transfer(transfer)
        assert exc_info.value.code == "validation_failed"

    def test_validate_transfer_invalid_note(self, storage):
        """Should fail with invalid note length."""
        service = SettlementService(storage)
        test_user = storage.create_user(
            email="notetest@example.com",
            password="password123",
            display_name="Note Test",
            handle="notetest"
        )
        another_user = storage.create_user(
            email="notetest2@example.com",
            password="password123",
            display_name="Note Test 2",
            handle="notetest2"
        )

        transfer = SettlementTransferCreate.model_construct(
            from_handle=test_user.handle,
            to_handle=another_user.handle,
            amount=100,
            note="a" * 201,
            visibility="public"
        )

        with pytest.raises(ValidationError) as exc_info:
            service.validate_transfer(transfer)
        assert exc_info.value.code == "validation_failed"

    def test_validate_transfer_invalid_visibility(self, storage):
        """Should fail with invalid visibility."""
        service = SettlementService(storage)
        test_user = storage.create_user(
            email="visibilitytest@example.com",
            password="password123",
            display_name="Visibility Test",
            handle="visibilitytest"
        )
        another_user = storage.create_user(
            email="visibilitytest2@example.com",
            password="password123",
            display_name="Visibility Test 2",
            handle="visibilitytest2"
        )

        transfer = SettlementTransferCreate.model_construct(
            from_handle=test_user.handle,
            to_handle=another_user.handle,
            amount=100,
            note="Test transfer",
            visibility="invalid"
        )

        with pytest.raises(ValidationError) as exc_info:
            service.validate_transfer(transfer)
        assert exc_info.value.code == "validation_failed"

    def test_calculate_balances_simple(self, storage):
        """Should calculate balances correctly."""
        service = SettlementService(storage)
        user1 = storage.create_user(
            email="bal1@example.com",
            password="password123",
            display_name="Balance User 1",
            handle="bal1"
        )
        user2 = storage.create_user(
            email="bal2@example.com",
            password="password123",
            display_name="Balance User 2",
            handle="bal2"
        )
        user3 = storage.create_user(
            email="bal3@example.com",
            password="password123",
            display_name="Balance User 3",
            handle="bal3"
        )

        transfers_data = [
            {"from_handle": user1.handle, "to_handle": user2.handle, "amount": 50},
            {"from_handle": user2.handle, "to_handle": user3.handle, "amount": 30},
            {"from_handle": user3.handle, "to_handle": user1.handle, "amount": 20}
        ]

        balances = service.calculate_balances(transfers_data)

        assert balances[user1.id] == -30  # Net: -50 + 20 = -30
        assert balances[user2.id] == 20   # Net: 50 - 30 = 20
        assert balances[user3.id] == 10   # Net: 30 - 20 = 10

    def test_check_affordable_success(self, storage):
        """Should pass affordability check."""
        service = SettlementService(storage)
        user1 = storage.create_user(
            email="aff1@example.com",
            password="password123",
            display_name="Aff User 1",
            handle="aff1"
        )
        user2 = storage.create_user(
            email="aff2@example.com",
            password="password123",
            display_name="Aff User 2",
            handle="aff2"
        )

        user1.balance = 100

        transfers_data = [
            {"from_handle": user1.handle, "to_handle": user2.handle, "amount": 50}
        ]

        balances = service.calculate_balances(transfers_data)
        result = service.check_affordable(balances)
        assert result is True

    def test_check_affordable_failure(self, storage):
        """Should fail affordability check."""
        service = SettlementService(storage)
        user1 = storage.create_user(
            email="afffail1@example.com",
            password="password123",
            display_name="Aff Fail User 1",
            handle="afffail1"
        )
        user2 = storage.create_user(
            email="afffail2@example.com",
            password="password123",
            display_name="Aff Fail User 2",
            handle="afffail2"
        )

        user1.balance = 10

        transfers_data = [
            {"from_handle": user1.handle, "to_handle": user2.handle, "amount": 50}
        ]

        balances = service.calculate_balances(transfers_data)
        result = service.check_affordable(balances)
        assert result is False

    def test_execute_settlement_success(self, storage):
        """Should execute settlement successfully."""
        service = SettlementService(storage)
        operator_id = "operator_1"

        # Add operator
        storage.settlement_operator_ids.add(operator_id)

        user1 = storage.create_user(
            email="settle1@example.com",
            password="password123",
            display_name="Settle User 1",
            handle="settle1"
        )
        user2 = storage.create_user(
            email="settle2@example.com",
            password="password123",
            display_name="Settle User 2",
            handle="settle2"
        )
        user1.balance = 100

        transfers_data = [
            {"from_handle": user1.handle, "to_handle": user2.handle, "amount": 50}
        ]

        result = service.execute_settlement(operator_id, transfers_data)

        assert result[0] is not None  # settlement_id
        assert result[1] is not None  # committed_at
        assert len(result[2]) == 1  # one payment created
        assert result[2][0].amount == 50

    def test_execute_settlement_not_operator(self, storage):
        """Should fail when user is not an operator."""
        service = SettlementService(storage)

        user1 = storage.create_user(
            email="notop1@example.com",
            password="password123",
            display_name="Not Operator",
            handle="notop1"
        )

        transfers_data = [
            {"from_handle": user1.handle, "to_handle": "user2", "amount": 50}
        ]

        with pytest.raises(ValidationError) as exc_info:
            service.execute_settlement(user1.id, transfers_data)
        assert exc_info.value.code == "forbidden"

    def test_execute_settlement_insufficient_funds(self, storage):
        """Should fail with insufficient funds."""
        service = SettlementService(storage)
        operator_id = "operator_1"

        storage.settlement_operator_ids.add(operator_id)

        user1 = storage.create_user(
            email="insuff1@example.com",
            password="password123",
            display_name="Insufficient Funds",
            handle="insuff1"
        )
        user2 = storage.create_user(
            email="insuff2@example.com",
            password="password123",
            display_name="Insufficient Funds 2",
            handle="insuff2"
        )
        user1.balance = 10

        transfers_data = [
            {"from_handle": user1.handle, "to_handle": user2.handle, "amount": 50}
        ]

        with pytest.raises(ValidationError) as exc_info:
            service.execute_settlement(operator_id, transfers_data)
        assert exc_info.value.code == "insufficient_funds"
