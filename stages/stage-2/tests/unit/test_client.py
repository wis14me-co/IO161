"""Unit tests for PocketfulClient."""

import pytest
from src.client import PocketfulClient, PocketfulError


class TestPocketfulClient:
    """Test PocketfulClient class."""

    def test_client_creation(self):
        """Should create a client successfully."""
        client = PocketfulClient(base_url="http://localhost:8080")
        assert client.base_url == "http://localhost:8080"
        assert client.timeout == 5.0

    def test_client_with_custom_timeout(self):
        """Should create a client with custom timeout."""
        client = PocketfulClient(base_url="http://localhost:8080", timeout=10.0)
        assert client.timeout == 10.0

    def test_headers_without_token(self):
        """Should build headers without authentication token."""
        client = PocketfulClient(base_url="http://localhost:8080")
        headers = client._headers()
        assert "Authorization" not in headers
        assert "Content-Type" in headers

    def test_headers_with_token(self):
        """Should build headers with authentication token."""
        client = PocketfulClient(base_url="http://localhost:8080")
        client._token = "test_token"
        headers = client._headers()
        assert "Authorization" in headers
        assert headers["Authorization"] == "Bearer test_token"

    def test_headers_with_idempotency_key(self):
        """Should build headers with idempotency key."""
        client = PocketfulClient(base_url="http://localhost:8080")
        headers = client._headers(idempotency_key="test_key")
        assert "Idempotency-Key" in headers
        assert headers["Idempotency-Key"] == "test_key"

    def test_error_creation(self):
        """Should create PocketfulError."""
        error = PocketfulError("test_code", "test message", 404)
        assert error.code == "test_code"
        assert error.message == "test message"
        assert error.status_code == 404
        assert str(error) == "test_code: test message"

    def test_error_without_status_code(self):
        """Should create PocketfulError without status code."""
        error = PocketfulError("test_code", "test message")
        assert error.code == "test_code"
        assert error.message == "test message"
        assert error.status_code == 500
        assert str(error) == "test_code: test message"
