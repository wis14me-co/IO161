"""
Unit tests for authentication service.
"""
import pytest
import bcrypt
from app.auth.service import AuthService
from app.auth.schemas import UserCreate, UserLogin, TokenResponse
from app.validation import ValidationError
from app.storage import User


class TestAuthService:
    """Test AuthService class."""

    def test_auth_service_initialization(self, storage):
        """Should initialize auth service with storage."""
        service = AuthService(storage)
        assert service.storage == storage

    def test_signup_success(self, storage):
        """Should create a new user successfully."""
        service = AuthService(storage)
        user_data = UserCreate(
            email="newuser@example.com",
            password="password123",
            display_name="New User",
            handle="newuser"
        )

        result = service.signup(user_data)

        assert isinstance(result, User)
        assert result.email == "newuser@example.com"
        assert result.display_name == "New User"
        assert result.handle == "newuser"
        assert result.balance == 0
        assert bcrypt.checkpw("password123".encode(), result.password_hash.encode())

    def test_signup_duplicate_email(self, storage):
        """Should fail when email already exists."""
        service = AuthService(storage)
        user_data = UserCreate(
            email="existing@example.com",
            password="password123",
            display_name="Existing User",
            handle="existing"
        )
        service.signup(user_data)

        duplicate_data = UserCreate(
            email="existing@example.com",
            password="password456",
            display_name="Different User",
            handle="different"
        )

        with pytest.raises(ValidationError) as exc_info:
            service.signup(duplicate_data)
        assert exc_info.value.code == "email_already_exists"

    def test_signup_duplicate_handle(self, storage):
        """Should fail when handle already exists."""
        service = AuthService(storage)
        user_data = UserCreate(
            email="user1@example.com",
            password="password123",
            display_name="User 1",
            handle="testuser"
        )
        service.signup(user_data)

        duplicate_data = UserCreate(
            email="user2@example.com",
            password="password456",
            display_name="User 2",
            handle="testuser"
        )

        with pytest.raises(ValidationError) as exc_info:
            service.signup(duplicate_data)
        assert exc_info.value.code == "handle_already_exists"

    def test_login_success(self, storage):
        """Should login successfully with valid credentials."""
        service = AuthService(storage)
        user_data = UserCreate(
            email="login@example.com",
            password="password123",
            display_name="Login User",
            handle="loginuser"
        )
        service.signup(user_data)

        login_data = UserLogin(
            email="login@example.com",
            password="password123"
        )

        result = service.login(login_data)
        assert isinstance(result, TokenResponse)
        assert result.token is not None
        assert len(result.token) > 0

    def test_login_invalid_password(self, storage):
        """Should fail with invalid password."""
        service = AuthService(storage)
        user_data = UserCreate(
            email="invalidpass@example.com",
            password="password123",
            display_name="Invalid Pass",
            handle="invalidpass"
        )
        service.signup(user_data)

        login_data = UserLogin(
            email="invalidpass@example.com",
            password="wrongpassword"
        )

        with pytest.raises(ValidationError) as exc_info:
            service.login(login_data)
        assert exc_info.value.code == "invalid_credentials"

    def test_login_nonexistent_user(self, storage):
        """Should fail with nonexistent user."""
        service = AuthService(storage)
        login_data = UserLogin(
            email="nonexistent@example.com",
            password="password123"
        )

        with pytest.raises(ValidationError) as exc_info:
            service.login(login_data)
        assert exc_info.value.code == "invalid_credentials"

    def test_get_current_user_valid(self, storage):
        """Should get current user with valid token."""
        service = AuthService(storage)
        user_data = UserCreate(
            email="token@example.com",
            password="password123",
            display_name="Token User",
            handle="tokenuser"
        )
        user = service.signup(user_data)
        token = storage.create_token(user.id)

        result = service.get_current_user(token)
        assert result.id == user.id
        assert result.email == user.email

    def test_get_current_user_invalid_token(self, storage):
        """Should fail with invalid token."""
        service = AuthService(storage)

        with pytest.raises(ValidationError) as exc_info:
            service.get_current_user("invalid_token")
        assert exc_info.value.code == "invalid_token"

    def test_get_current_user_expired_token(self, storage):
        """Should fail with expired token."""
        service = AuthService(storage)
        user_data = UserCreate(
            email="expired@example.com",
            password="password123",
            display_name="Expired User",
            handle="expireduser"
        )
        user = service.signup(user_data)

        # Manually expire token
        user.tokens = []
        token = "expired_token_123"

        with pytest.raises(ValidationError) as exc_info:
            service.get_current_user(token)
        assert exc_info.value.code == "invalid_token"
