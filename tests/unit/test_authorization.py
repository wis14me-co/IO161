"""
Unit tests for authorization service.
"""
import pytest
from datetime import datetime, timezone, timedelta
from app.authorization.service import AuthorizationService
from app.authorization.schemas import AuthorizationCreate, AuthorizationCapture
from app.validation import ValidationError
from app.storage import User, Payment, Authorization


class TestAuthorizationService:
    """Test AuthorizationService class."""

    def test_authorization_service_initialization(self, storage):
        """Should initialize authorization service with storage."""
        service = AuthorizationService(storage)
        assert service.storage == storage

    def test_create_authorization_success(self, storage):
        """Should create authorization successfully."""
        service = AuthorizationService(storage)
        user1 = storage.create_user(
            email="auth1@example.com",
            password="password123",
            display_name="Auth User 1",
            handle="auth1",
            balance=1000
        )
        user2 = storage.create_user(
            email="auth2@example.com",
            password="password123",
            display_name="Auth User 2",
            handle="auth2"
        )

        auth_data = AuthorizationCreate(
            to_handle=user2.handle,
            amount=100,
            note="Test authorization",
            visibility="public"
        )

        result = service.create_authorization(
            from_user_id=user1.id,
            to_handle=user2.handle,
            amount=100,
            note="Test authorization",
            visibility="public"
        )

        assert result is not None
        assert result.from_user_id == user1.id
        assert result.to_user_id == user2.id
        assert result.amount == 100
        assert result.status == "open"
        assert result.captured_amount == 0

    def test_create_authorization_to_self(self, storage):
        """Should fail when creating authorization to self."""
        service = AuthorizationService(storage)
        user1 = storage.create_user(
            email="selfauth1@example.com",
            password="password123",
            display_name="Self Auth",
            handle="selfauth",
            balance=1000
        )

        auth_data = AuthorizationCreate(
            to_handle=user1.handle,
            amount=100,
            note="Test authorization",
            visibility="public"
        )

        with pytest.raises(ValidationError) as exc_info:
            service.create_authorization(
                from_user_id=user1.id,
                to_handle=user1.handle,
                amount=100,
                note="Test authorization",
                visibility="public"
            )
        assert exc_info.value.code == "self_auth"

    def test_create_authorization_invalid_amount(self, storage):
        """Should fail with invalid amount."""
        service = AuthorizationService(storage)
        user1 = storage.create_user(
            email="amountauth1@example.com",
            password="password123",
            display_name="Amount Auth",
            handle="amountauth",
            balance=1000
        )
        user2 = storage.create_user(
            email="amountauth2@example.com",
            password="password123",
            display_name="Amount Auth 2",
            handle="amountauth2"
        )

        with pytest.raises(ValidationError) as exc_info:
            service.create_authorization(
                from_user_id=user1.id,
                to_handle=user2.handle,
                amount=0,
                note="Test authorization",
                visibility="public"
            )
        assert exc_info.value.code == "validation_failed"

    def test_create_authorization_insufficient_funds(self, storage):
        """Should fail with insufficient funds."""
        service = AuthorizationService(storage)
        user1 = storage.create_user(
            email="insuffauth1@example.com",
            password="password123",
            display_name="Insufficient Auth",
            handle="insuffauth"
        )
        user2 = storage.create_user(
            email="insuffauth2@example.com",
            password="password123",
            display_name="Insufficient Auth 2",
            handle="insuffauth2"
        )

        auth_data = AuthorizationCreate(
            to_handle=user2.handle,
            amount=100,
            note="Test authorization",
            visibility="public"
        )

        with pytest.raises(ValidationError) as exc_info:
            service.create_authorization(
                from_user_id=user1.id,
                to_handle=user2.handle,
                amount=100,
                note="Test authorization",
                visibility="public"
            )
        assert exc_info.value.code == "insufficient_funds"

    def test_void_authorization_success(self, storage):
        """Should void authorization successfully."""
        service = AuthorizationService(storage)
        user1 = storage.create_user(
            email="voidauth1@example.com",
            password="password123",
            display_name="Void Auth",
            handle="voidauth",
            balance=1000
        )
        user2 = storage.create_user(
            email="voidauth2@example.com",
            password="password123",
            display_name="Void Auth 2",
            handle="voidauth2"
        )

        auth = service.create_authorization(
            from_user_id=user1.id,
            to_handle=user2.handle,
            amount=100,
            note="Test authorization",
            visibility="public"
        )

        result = service.void_authorization(auth.id, user1.id)

        assert result is not None
        assert result.status == "voided"

    def test_void_authorization_not_payer(self, storage):
        """Should fail when non-payer tries to void."""
        service = AuthorizationService(storage)
        user1 = storage.create_user(
            email="voidnotpayer1@example.com",
            password="password123",
            display_name="Void Not Payer",
            handle="voidnotpayer",
            balance=1000
        )
        user2 = storage.create_user(
            email="voidnotpayer2@example.com",
            password="password123",
            display_name="Void Not Payer 2",
            handle="voidnotpayer2"
        )

        auth = service.create_authorization(
            from_user_id=user1.id,
            to_handle=user2.handle,
            amount=100,
            note="Test authorization",
            visibility="public"
        )

        with pytest.raises(ValidationError) as exc_info:
            service.void_authorization(auth.id, user2.id)
        assert exc_info.value.code == "forbidden"

    def test_void_authorization_already_voided(self, storage):
        """Should fail when trying to void already voided authorization."""
        service = AuthorizationService(storage)
        user1 = storage.create_user(
            email="alreadyvoid1@example.com",
            password="password123",
            display_name="Already Void",
            handle="alreadyvoid",
            balance=1000
        )
        user2 = storage.create_user(
            email="alreadyvoid2@example.com",
            password="password123",
            display_name="Already Void 2",
            handle="alreadyvoid2"
        )

        auth = service.create_authorization(
            from_user_id=user1.id,
            to_handle=user2.handle,
            amount=100,
            note="Test authorization",
            visibility="public"
        )

        service.void_authorization(auth.id, user1.id)

        with pytest.raises(ValidationError) as exc_info:
            service.void_authorization(auth.id, user1.id)
        assert exc_info.value.code == "authorization_not_open"

    def test_capture_authorization_success(self, storage):
        """Should capture authorization successfully."""
        service = AuthorizationService(storage)
        user1 = storage.create_user(
            email="captureauth1@example.com",
            password="password123",
            display_name="Capture Auth",
            handle="captureauth",
            balance=1000
        )
        user2 = storage.create_user(
            email="captureauth2@example.com",
            password="password123",
            display_name="Capture Auth 2",
            handle="captureauth2"
        )

        # Create authorization with 100
        auth = service.create_authorization(
            from_user_id=user1.id,
            to_handle=user2.handle,
            amount=100,
            note="Test authorization",
            visibility="public"
        )

        # Capture 50
        capture_data = AuthorizationCapture(amount=50, final=False)
        payment, result = service.capture_authorization(auth.id, user2.id, capture_data)

        assert result is not None
        assert result.status == "open"  # Still open (not final)
        assert result.captured_amount == 50

    def test_capture_authorization_final(self, storage):
        """Should capture authorization as final."""
        service = AuthorizationService(storage)
        user1 = storage.create_user(
            email="finalcapture1@example.com",
            password="password123",
            display_name="Final Capture",
            handle="finalcapture",
            balance=1000
        )
        user2 = storage.create_user(
            email="finalcapture2@example.com",
            password="password123",
            display_name="Final Capture 2",
            handle="finalcapture2"
        )

        # Create authorization with 100
        auth = service.create_authorization(
            from_user_id=user1.id,
            to_handle=user2.handle,
            amount=100,
            note="Test authorization",
            visibility="public"
        )

        # Capture 100 (final)
        capture_data = AuthorizationCapture(amount=100, final=True)
        payment, result = service.capture_authorization(auth.id, user2.id, capture_data)

        assert result is not None
        assert result.status == "captured"  # Final capture
        assert result.captured_amount == 100

    def test_capture_authorization_not_receiver(self, storage):
        """Should fail when non-receiver tries to capture."""
        service = AuthorizationService(storage)
        user1 = storage.create_user(
            email="notreceiver1@example.com",
            password="password123",
            display_name="Not Receiver",
            handle="notreceiver",
            balance=1000
        )
        user2 = storage.create_user(
            email="notreceiver2@example.com",
            password="password123",
            display_name="Not Receiver 2",
            handle="notreceiver2"
        )
        user3 = storage.create_user(
            email="notreceiver3@example.com",
            password="password123",
            display_name="Not Receiver 3",
            handle="notreceiver3"
        )

        auth = service.create_authorization(
            from_user_id=user1.id,
            to_handle=user2.handle,
            amount=100,
            note="Test authorization",
            visibility="public"
        )

        with pytest.raises(ValidationError) as exc_info:
            service.capture_authorization(auth.id, user3.id, AuthorizationCapture())
        assert exc_info.value.code == "forbidden"

    def test_capture_authorization_exceeds_amount(self, storage):
        """Should fail when capture exceeds authorization amount."""
        service = AuthorizationService(storage)
        user1 = storage.create_user(
            email="exceedcapture1@example.com",
            password="password123",
            display_name="Exceed Capture",
            handle="exceedcapture",
            balance=1000
        )
        user2 = storage.create_user(
            email="exceedcapture2@example.com",
            password="password123",
            display_name="Exceed Capture 2",
            handle="exceedcapture2"
        )

        auth = service.create_authorization(
            from_user_id=user1.id,
            to_handle=user2.handle,
            amount=100,
            note="Test authorization",
            visibility="public"
        )

        with pytest.raises(ValidationError) as exc_info:
            service.capture_authorization(auth.id, user2.id, AuthorizationCapture(amount=150))
        assert exc_info.value.code == "capture_exceeds_authorization"

    def test_capture_authorization_zero_amount(self, storage):
        """Should fail with zero amount."""
        service = AuthorizationService(storage)
        user1 = storage.create_user(
            email="zerocapture1@example.com",
            password="password123",
            display_name="Zero Capture",
            handle="zerocapture",
            balance=1000
        )
        user2 = storage.create_user(
            email="zerocapture2@example.com",
            password="password123",
            display_name="Zero Capture 2",
            handle="zerocapture2"
        )

        auth = service.create_authorization(
            from_user_id=user1.id,
            to_handle=user2.handle,
            amount=100,
            note="Test authorization",
            visibility="public"
        )

        with pytest.raises(ValidationError) as exc_info:
            # Pass a dict to bypass pydantic validation, test service validation
            service.capture_authorization(auth.id, user2.id, AuthorizationCapture.model_construct(amount=0))
        assert exc_info.value.code == "validation_failed"

    def test_capture_authorization_not_open(self, storage):
        """Should fail when trying to capture non-open authorization."""
        service = AuthorizationService(storage)
        user1 = storage.create_user(
            email="notopen1@example.com",
            password="password123",
            display_name="Not Open",
            handle="notopen",
            balance=1000
        )
        user2 = storage.create_user(
            email="notopen2@example.com",
            password="password123",
            display_name="Not Open 2",
            handle="notopen2"
        )

        auth = service.create_authorization(
            from_user_id=user1.id,
            to_handle=user2.handle,
            amount=100,
            note="Test authorization",
            visibility="public"
        )

        # Void it first
        service.void_authorization(auth.id, user1.id)

        with pytest.raises(ValidationError) as exc_info:
            service.capture_authorization(auth.id, user2.id, AuthorizationCapture())
        assert exc_info.value.code == "authorization_not_open"

    def test_list_authorizations_success(self, storage):
        """Should list authorizations successfully."""
        service = AuthorizationService(storage)
        user1 = storage.create_user(
            email="listauth1@example.com",
            password="password123",
            display_name="List Auth",
            handle="listauth",
            balance=1000
        )
        user2 = storage.create_user(
            email="listauth2@example.com",
            password="password123",
            display_name="List Auth 2",
            handle="listauth2"
        )
        user3 = storage.create_user(
            email="listauth3@example.com",
            password="password123",
            display_name="List Auth 3",
            handle="listauth3"
        )

        auth1 = service.create_authorization(
            from_user_id=user1.id,
            to_handle=user2.handle,
            amount=100,
            note="Auth 1",
            visibility="public"
        )
        auth2 = service.create_authorization(
            from_user_id=user1.id,
            to_handle=user3.handle,
            amount=200,
            note="Auth 2",
            visibility="public"
        )

        result = service.list_authorizations(user1.id)

        assert len(result.authorizations) == 2
        assert result.has_more is False
