"""
Integration tests for Pocketful API.
"""
import pytest
from fastapi.testclient import TestClient
from app.main import app
from app.storage import storage, Storage
from app.auth.service import AuthService
from app.settlement.service import SettlementService
from app.authorization.service import AuthorizationService
from app.models import Fixture


@pytest.fixture
def client():
    """Create test client."""
    return TestClient(app)


@pytest.fixture(autouse=True)
def reset_storage():
    """Reset global storage before each test."""
    storage.reset()


@pytest.fixture
def auth_service():
    """Create auth service using global storage."""
    return AuthService(storage)


@pytest.fixture
def settlement_service():
    """Create settlement service using global storage."""
    return SettlementService(storage)


@pytest.fixture
def authorization_service():
    """Create authorization service using global storage."""
    return AuthorizationService(storage)


@pytest.fixture
def test_user(auth_service):
    """Create a test user with sufficient balance."""
    from app.auth.schemas import UserCreate
    user = auth_service.signup(UserCreate(
        email="integration@example.com",
        password="password123",
        display_name="Integration Test User",
        handle="integrationuser"
    ))
    # Add balance to user
    auth_service.storage.update_balance(user.id, 10000)
    return user


@pytest.fixture
def test_token(client, test_user):
    """Create a test token via login."""
    response = client.post(
        "/api/v1/auth/login",
        json={
            "email": "integration@example.com",
            "password": "password123"
        }
    )
    return response.json()["token"]


class TestAuthIntegration:
    """Integration tests for authentication."""

    def test_signup_and_login(self, client, auth_service):
        """Test signup and login flow."""
        # Signup
        response = client.post(
            "/api/v1/auth/signup",
            json={
                "email": "newuser@example.com",
                "password": "password123",
                "display_name": "New User",
                "handle": "newuser"
            }
        )
        assert response.status_code == 201
        data = response.json()
        assert "token" in data

        # Login
        response = client.post(
            "/api/v1/auth/login",
            json={
                "email": "newuser@example.com",
                "password": "password123"
            }
        )
        assert response.status_code == 200
        data = response.json()
        assert "token" in data

    def test_protected_endpoint_without_token(self, client):
        """Test protected endpoint without token."""
        response = client.get("/api/v1/auth/me")
        assert response.status_code == 401

    def test_protected_endpoint_with_valid_token(self, client, test_token):
        """Test protected endpoint with valid token."""
        response = client.get(
            "/api/v1/auth/me",
            headers={"Authorization": f"Bearer {test_token}"}
        )
        assert response.status_code == 200
        data = response.json()
        assert data["email"] == "integration@example.com"

    def test_protected_endpoint_with_invalid_token(self, client):
        """Test protected endpoint with invalid token."""
        response = client.get(
            "/api/v1/auth/me",
            headers={"Authorization": "Bearer invalid_token"}
        )
        assert response.status_code == 401


class TestPaymentIntegration:
    """Integration tests for payments."""

    def test_create_payment_without_token(self, client):
        """Test creating payment without token."""
        response = client.post(
            "/api/v1/payments",
            json={
                "from_handle": "user1",
                "to_handle": "user2",
                "amount": 100,
                "note": "Test payment",
                "visibility": "public"
            }
        )
        assert response.status_code == 401

    def test_create_payment_with_token(self, client, test_user, test_token):
        """Test creating payment with token."""
        # Create another user
        another_user = client.post(
            "/api/v1/auth/signup",
            json={
                "email": "payment2@example.com",
                "password": "password123",
                "display_name": "Payment User 2",
                "handle": "payment2"
            }
        )
        another_user_data = another_user.json()
        token = another_user_data["token"]

        # Create payment
        response = client.post(
            "/api/v1/payments",
            json={
                "to_handle": "payment2",
                "amount": 100,
                "note": "Test payment",
                "visibility": "public"
            },
            headers={
                "Authorization": f"Bearer {test_token}",
                "Idempotency-Key": "test_payment_key_1"
            }
        )
        assert response.status_code == 201


class TestSettlementIntegration:
    """Integration tests for settlements."""

    def test_create_settlement_without_token(self, client):
        """Test creating settlement without token."""
        response = client.post(
            "/api/v1/settlements",
            json={
                "transfers": [
                    {
                        "from_handle": "user1",
                        "to_handle": "user2",
                        "amount": 100,
                        "note": "Test settlement",
                        "visibility": "public"
                    }
                ]
            }
        )
        assert response.status_code == 401

    def test_create_settlement_with_operator(self, client, auth_service, settlement_service):
        """Test creating settlement with operator."""
        from app.auth.schemas import UserCreate
        # Create operator
        operator = auth_service.signup(UserCreate(
            email="operator@example.com",
            password="password123",
            display_name="Operator",
            handle="operator"
        ))

        # Add to settlement operators
        storage = auth_service.storage
        storage.settlement_operator_ids.add(operator.id)

        # Create users
        user1 = auth_service.signup(UserCreate(
            email="settle1@example.com",
            password="password123",
            display_name="Settle User 1",
            handle="settle1"
        ))
        user2 = auth_service.signup(UserCreate(
            email="settle2@example.com",
            password="password123",
            display_name="Settle User 2",
            handle="settle2"
        ))

        # Give user1 sufficient balance for the settlement
        auth_service.storage.update_balance(user1.id, 1000)

        # Login as operator to get JWT token
        operator_login = client.post(
            "/api/v1/auth/login",
            json={"email": "operator@example.com", "password": "password123"}
        )
        operator_token = operator_login.json()["token"]

        # Create settlement
        response = client.post(
            "/api/v1/settlements",
            json={
                "transfers": [
                    {
                        "from_handle": user1.handle,
                        "to_handle": user2.handle,
                        "amount": 100,
                        "note": "Test settlement",
                        "visibility": "public"
                    }
                ]
            },
            headers={
                "Authorization": f"Bearer {operator_token}",
                "Idempotency-Key": "test_key_1"
            }
        )
        assert response.status_code == 201
        data = response.json()
        assert "settlement_id" in data
        assert "committed_at" in data
        assert len(data["payments"]) == 1


class TestAuthorizationIntegration:
    """Integration tests for authorizations."""

    def test_create_authorization_without_token(self, client):
        """Test creating authorization without token."""
        response = client.post(
            "/api/v1/authorizations",
            json={
                "to_handle": "user2",
                "amount": 100,
                "note": "Test authorization",
                "visibility": "public"
            }
        )
        assert response.status_code == 401

    def test_create_authorization_with_token(self, client, test_user, test_token):
        """Test creating authorization with token."""
        # Create another user
        another_user = client.post(
            "/api/v1/auth/signup",
            json={
                "email": "auth2@example.com",
                "password": "password123",
                "display_name": "Auth User 2",
                "handle": "auth2"
            }
        )
        another_user_data = another_user.json()
        token = another_user_data["token"]

        # Create authorization as payer
        response = client.post(
            "/api/v1/authorizations",
            json={
                "to_handle": "auth2",
                "amount": 100,
                "note": "Test authorization",
                "visibility": "public"
            },
            headers={
                "Authorization": f"Bearer {test_token}",
                "Idempotency-Key": "test_auth_key_1"
            }
        )
        assert response.status_code == 201
        data = response.json()
        assert "id" in data
        assert data["status"] == "open"

    def test_capture_authorization_as_receiver(self, client, test_user, test_token, auth_service):
        """Test capturing authorization as receiver."""
        from app.auth.schemas import UserCreate
        # Create receiver user with balance
        user2 = auth_service.signup(UserCreate(
            email="capture2@example.com",
            password="password123",
            display_name="Capture User 2",
            handle="capture2"
        ))
        # Give test_user (payer) sufficient balance
        auth_service.storage.update_balance(test_user.id, 1000)

        # Login as receiver
        user2_login = client.post(
            "/api/v1/auth/login",
            json={"email": "capture2@example.com", "password": "password123"}
        )
        token2 = user2_login.json()["token"]

        # Create authorization (test_user is payer)
        auth_response = client.post(
            "/api/v1/authorizations",
            json={
                "to_handle": "capture2",
                "amount": 100,
                "note": "Test authorization",
                "visibility": "public"
            },
            headers={
                "Authorization": f"Bearer {test_token}",
                "Idempotency-Key": "test_auth_key_2"
            }
        )
        auth_id = auth_response.json()["id"]

        # Capture as receiver
        response = client.post(
            f"/api/v1/authorizations/{auth_id}/capture",
            json={"amount": 50, "final": False},
            headers={
                "Authorization": f"Bearer {token2}",
                "Idempotency-Key": "test_key_2"
            }
        )
        assert response.status_code == 201


class TestHealthIntegration:
    """Integration tests for health check."""

    def test_health_check(self, client):
        """Test health check endpoint."""
        response = client.get("/health")
        assert response.status_code == 200
        data = response.json()
        assert data["status"] == "ok"
