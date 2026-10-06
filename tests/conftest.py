"""
Pytest configuration and fixtures for Pocketful API tests.
"""
import pytest
import sys
import os
from pathlib import Path

# Add the app directory to the path
sys.path.insert(0, str(Path(__file__).parent.parent / "app"))

from app.storage import Storage, User, Payment, Request, Authorization
import bcrypt


@pytest.fixture
def storage():
    """Create a fresh storage instance for each test."""
    storage = Storage()
    return storage


@pytest.fixture
def test_user(storage):
    """Create a test user."""
    return storage.create_user(
        email="test@example.com",
        password="password123",
        display_name="Test User",
        handle="testuser"
    )


@pytest.fixture
def authenticated_user(storage):
    """Create and return a user with a valid token."""
    user = storage.create_user(
        email="authenticated@example.com",
        password="password123",
        display_name="Authenticated User",
        handle="authenticated"
    )
    token = storage.create_token(user.id)
    return user, token


@pytest.fixture
def another_user(storage):
    """Create a second test user."""
    return storage.create_user(
        email="another@example.com",
        password="password123",
        display_name="Another User",
        handle="anotheruser"
    )


@pytest.fixture
def payment(storage, test_user, another_user):
    """Create a test payment."""
    return storage.create_payment(
        from_user_id=test_user.id,
        to_user_id=another_user.id,
        amount=100,
        note="Test payment",
        visibility="public",
        request_id=None
    )


@pytest.fixture
def request_payment(storage, test_user, another_user):
    """Create a test payment request."""
    return storage.create_request(
        requester_id=test_user.id,
        payer_id=another_user.id,
        amount=50,
        note="Test request"
    )


@pytest.fixture
def authorization(storage, test_user, another_user):
    """Create a test authorization."""
    return storage.create_authorization(
        from_user_id=test_user.id,
        to_user_id=another_user.id,
        amount=75,
        note="Test authorization",
        visibility="public"
    )


@pytest.fixture
def split_data():
    """Return test split data."""
    return {
        "amount": 300,
        "participant_handles": ["user1", "user2", "user3"],
        "note": "Test split",
        "shares": [
            {"handle": "user1", "amount": 100},
            {"handle": "user2", "amount": 100},
            {"handle": "user3", "amount": 100}
        ]
    }


@pytest.fixture
def settlement_transfers(storage, test_user, another_user):
    """Return test settlement transfers."""
    return [
        {
            "from_handle": test_user.handle,
            "to_handle": another_user.handle,
            "amount": 50,
            "note": "Settlement payment",
            "visibility": "public"
        }
    ]


@pytest.fixture
def websocket_manager():
    """Create a mock WebSocket manager for testing."""
    from app.websocket.manager import ConnectionManager
    return ConnectionManager()


@pytest.fixture
def mock_websocket():
    """Create a mock WebSocket object for testing."""
    class MockWebSocket:
        def __init__(self):
            self.accepted = False
            self.messages = []
            self.closed = False

        async def accept(self):
            self.accepted = True

        async def send_json(self, data):
            self.messages.append(data)

        async def receive_json(self):
            return self.messages.pop(0) if self.messages else {}

        def close(self):
            self.closed = True

    return MockWebSocket()
