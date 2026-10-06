"""
Unit tests for storage class.
"""
import pytest
from app.storage import Storage, User, Payment, Request, Authorization, IdempotencyRecord
import bcrypt


class TestStorage:
    """Test Storage class."""

    def test_storage_initialization(self):
        """Should initialize storage with default values."""
        storage = Storage()
        assert storage.currency == "EUR"
        assert storage.minor_units == 2
        assert len(storage.users) == 0
        assert len(storage.payments) == 0
        assert len(storage.settlement_operator_ids) == 0

    def test_create_user(self, storage):
        """Should create a user successfully."""
        user = storage.create_user(
            email="test@example.com",
            password="password123",
            display_name="Test User",
            handle="testuser"
        )

        assert user.id is not None
        assert user.email == "test@example.com"
        assert user.display_name == "Test User"
        assert user.handle == "testuser"
        assert user.balance == 0
        assert bcrypt.checkpw("password123".encode(), user.password_hash.encode())

    def test_create_user_duplicate_email(self, storage):
        """Should fail when creating user with duplicate email."""
        storage.create_user(
            email="duplicate@example.com",
            password="password123",
            display_name="User 1",
            handle="user1"
        )

        with pytest.raises(ValueError) as exc_info:
            storage.create_user(
                email="duplicate@example.com",
                password="password456",
                display_name="User 2",
                handle="user2"
            )
        assert "email already exists" in str(exc_info.value)

    def test_create_user_duplicate_handle(self, storage):
        """Should fail when creating user with duplicate handle."""
        storage.create_user(
            email="user1@example.com",
            password="password123",
            display_name="User 1",
            handle="duplicatehandle"
        )

        with pytest.raises(ValueError) as exc_info:
            storage.create_user(
                email="user2@example.com",
                password="password456",
                display_name="User 2",
                handle="duplicatehandle"
            )
        assert "handle already exists" in str(exc_info.value)

    def test_get_user_by_id(self, storage):
        """Should get user by ID successfully."""
        user = storage.create_user(
            email="getid@example.com",
            password="password123",
            display_name="Get ID User",
            handle="getiduser"
        )

        result = storage.get_user_by_id(user.id)
        assert result is not None
        assert result.id == user.id

    def test_get_user_by_id_not_found(self, storage):
        """Should return None when user not found."""
        result = storage.get_user_by_id("nonexistent")
        assert result is None

    def test_get_user_by_handle(self, storage):
        """Should get user by handle successfully."""
        user = storage.create_user(
            email="gethandle@example.com",
            password="password123",
            display_name="Get Handle User",
            handle="gethandleuser"
        )

        result = storage.get_user_by_handle("gethandleuser")
        assert result is not None
        assert result.id == user.id

    def test_get_user_by_handle_not_found(self, storage):
        """Should return None when user not found by handle."""
        result = storage.get_user_by_handle("nonexistent")
        assert result is None

    def test_update_balance_success(self, storage):
        """Should update balance successfully."""
        user = storage.create_user(
            email="balance@example.com",
            password="password123",
            display_name="Balance User",
            handle="balanceuser"
        )

        new_balance = storage.update_balance(user.id, 50)
        assert new_balance == 50

    def test_update_balance_negative(self, storage):
        """Should fail with negative balance."""
        user = storage.create_user(
            email="negbalance@example.com",
            password="password123",
            display_name="Neg Balance User",
            handle="negbalanceuser"
        )

        with pytest.raises(ValueError) as exc_info:
            storage.update_balance(user.id, -10)
        assert "insufficient_funds" in str(exc_info.value)

    def test_atomic_transfer_success(self, storage):
        """Should execute atomic transfer successfully."""
        user1 = storage.create_user(
            email="transfer1@example.com",
            password="password123",
            display_name="Transfer User 1",
            handle="transfer1"
        )
        user2 = storage.create_user(
            email="transfer2@example.com",
            password="password123",
            display_name="Transfer User 2",
            handle="transfer2"
        )

        user1.balance = 100

        result = storage.atomic_transfer(user1.id, user2.id, 50)
        assert result[0] == 50  # user1 new balance
        assert result[1] == 50  # user2 new balance

        user1 = storage.get_user_by_id(user1.id)
        user2 = storage.get_user_by_id(user2.id)
        assert user1.balance == 50
        assert user2.balance == 50

    def test_atomic_transfer_insufficient_funds(self, storage):
        """Should fail atomic transfer with insufficient funds."""
        user1 = storage.create_user(
            email="insufftransfer1@example.com",
            password="password123",
            display_name="Insuff Transfer User 1",
            handle="insufftransfer1"
        )
        user2 = storage.create_user(
            email="insufftransfer2@example.com",
            password="password123",
            display_name="Insuff Transfer User 2",
            handle="insufftransfer2"
        )

        user1.balance = 10

        with pytest.raises(ValueError) as exc_info:
            storage.atomic_transfer(user1.id, user2.id, 50)
        assert "insufficient_funds" in str(exc_info.value)

    def test_create_payment(self, storage):
        """Should create a payment successfully."""
        user1 = storage.create_user(
            email="pay1@example.com",
            password="password123",
            display_name="Pay User 1",
            handle="pay1"
        )
        user2 = storage.create_user(
            email="pay2@example.com",
            password="password123",
            display_name="Pay User 2",
            handle="pay2"
        )

        payment = storage.create_payment(
            from_user_id=user1.id,
            to_user_id=user2.id,
            amount=100,
            note="Test payment",
            visibility="public",
            request_id=None
        )

        assert payment.id is not None
        assert payment.amount == 100
        assert payment.note == "Test payment"
        assert payment.visibility == "public"

    def test_create_request(self, storage):
        """Should create a request successfully."""
        user1 = storage.create_user(
            email="req1@example.com",
            password="password123",
            display_name="Req User 1",
            handle="req1"
        )
        user2 = storage.create_user(
            email="req2@example.com",
            password="password123",
            display_name="Req User 2",
            handle="req2"
        )

        request = storage.create_request(
            requester_id=user1.id,
            payer_id=user2.id,
            amount=50,
            note="Test request"
        )

        assert request.id is not None
        assert request.amount == 50
        assert request.note == "Test request"
        assert request.status == "pending"

    def test_create_authorization(self, storage):
        """Should create an authorization successfully."""
        user1 = storage.create_user(
            email="auth1@example.com",
            password="password123",
            display_name="Auth User 1",
            handle="auth1"
        )
        user2 = storage.create_user(
            email="auth2@example.com",
            password="password123",
            display_name="Auth User 2",
            handle="auth2"
        )

        auth = storage.create_authorization(
            from_user_id=user1.id,
            to_user_id=user2.id,
            amount=100,
            note="Test authorization",
            visibility="public"
        )

        assert auth.id is not None
        assert auth.amount == 100
        assert auth.status == "open"
        assert auth.captured_amount == 0

    def test_get_authorization(self, storage):
        """Should get authorization successfully."""
        user1 = storage.create_user(
            email="getauth1@example.com",
            password="password123",
            display_name="Get Auth User 1",
            handle="getauth1"
        )
        user2 = storage.create_user(
            email="getauth2@example.com",
            password="password123",
            display_name="Get Auth User 2",
            handle="getauth2"
        )

        auth = storage.create_authorization(
            from_user_id=user1.id,
            to_user_id=user2.id,
            amount=100,
            note="Test authorization"
        )

        result = storage.get_authorization(auth.id)
        assert result is not None
        assert result.id == auth.id

    def test_get_authorization_not_found(self, storage):
        """Should return None when authorization not found."""
        result = storage.get_authorization("nonexistent")
        assert result is None

    def test_update_authorization_status(self, storage):
        """Should update authorization status successfully."""
        user1 = storage.create_user(
            email="updateauth1@example.com",
            password="password123",
            display_name="Update Auth User 1",
            handle="updateauth1"
        )
        user2 = storage.create_user(
            email="updateauth2@example.com",
            password="password123",
            display_name="Update Auth User 2",
            handle="updateauth2"
        )

        auth = storage.create_authorization(
            from_user_id=user1.id,
            to_user_id=user2.id,
            amount=100,
            note="Test authorization"
        )

        result = storage.update_authorization_status(auth.id, "voided")
        assert result is not None
        assert result.status == "voided"

    def test_create_idempotency_record(self, storage):
        """Should create idempotency record successfully."""
        body = {"key": "value"}
        record = storage.store_idempotency(
            user_id="user1",
            key="test_key",
            method="POST",
            path="/test",
            body=body,
            response_status=200,
            response_body={"result": "success"}
        )

        assert record is not None
        assert record.key == "test_key"
        assert record.user_id == "user1"
        assert record.method == "POST"
        assert record.path == "/test"
        assert record.body_hash == storage._hash_body(body)

    def test_check_idempotency_hit(self, storage):
        """Should return existing record for idempotency key."""
        body = {"key": "value"}
        storage.store_idempotency(
            user_id="user1",
            key="test_key",
            method="POST",
            path="/test",
            body=body,
            response_status=200,
            response_body={"result": "success"}
        )

        result = storage.check_idempotency(
            user_id="user1",
            key="test_key",
            method="POST",
            path="/test",
            body=body
        )

        assert result is not None
        assert result[0] == 200
        assert result[1] == {"result": "success"}

    def test_check_idempotency_miss(self, storage):
        """Should return None for non-existent idempotency key."""
        body = {"key": "value"}
        result = storage.check_idempotency(
            user_id="user1",
            key="nonexistent_key",
            method="POST",
            path="/test",
            body=body
        )

        assert result is None

    def test_export_state(self, storage):
        """Should export storage state successfully."""
        user = storage.create_user(
            email="export@example.com",
            password="password123",
            display_name="Export User",
            handle="exportuser"
        )

        state = storage.export_state()
        assert state["currency"] == "EUR"
        assert state["minor_units"] == 2
        assert state["users"][user.id]["email"] == "export@example.com"
        assert len(state["users"]) == 1

    def test_import_state(self, storage):
        """Should import storage state successfully."""
        user = storage.create_user(
            email="import@example.com",
            password="password123",
            display_name="Import User",
            handle="importuser"
        )

        state = storage.export_state()
        new_storage = Storage()

        new_storage.import_state(state)

        assert len(new_storage.users) == 1
        assert new_storage.users[user.id].email == "import@example.com"
        assert new_storage.users[user.id].balance == 0

    def test_reset(self, storage):
        """Should reset storage successfully."""
        user = storage.create_user(
            email="reset@example.com",
            password="password123",
            display_name="Reset User",
            handle="resetuser"
        )
        payment = storage.create_payment(
            from_user_id=user.id,
            to_user_id="other",
            amount=100,
            note="Test",
            visibility="public",
            request_id=None
        )

        storage.reset(None)

        assert len(storage.users) == 0
        assert len(storage.payments) == 0
        assert len(storage.requests) == 0
