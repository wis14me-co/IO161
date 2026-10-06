"""Minimal Python client for integration testing."""

import httpx
from typing import Optional, Dict, Any, List
from dataclasses import dataclass
import json


@dataclass
class AuthResponse:
    """Response from signup/login."""
    user_id: str
    display_name: str
    token: str


@dataclass
class UserResponse:
    """User information."""
    user_id: str
    display_name: str
    handle: str
    balance: int
    total: int
    available: int
    held: int
    currency: str
    minor_units: int


@dataclass
class PaymentResponse:
    """Payment response."""
    payment_id: str
    from_user_id: str
    from_handle: str
    to_user_id: str
    to_handle: str
    amount: int
    currency: str
    note: str
    visibility: str
    request_id: Optional[str]
    created_at: str


@dataclass
class RequestResponse:
    """Request response."""
    request_id: str
    requester_id: str
    requester_handle: str
    payer_id: str
    payer_handle: str
    amount: int
    currency: str
    note: str
    status: str
    payment_id: Optional[str]
    created_at: str


@dataclass
class RequestListResponse:
    """List of requests."""
    requests: List[RequestResponse]
    has_more: bool


@dataclass
class ActivityResponse:
    """Activity feed."""
    payments: List[PaymentResponse]
    has_more: bool


@dataclass
class SplitResponse:
    """Split response."""
    split_id: str
    amount: int
    currency: str
    note: str
    shares: List[Dict[str, Any]]
    requests: List[RequestResponse]
    created_at: str


@dataclass
class SettlementResponse:
    """Settlement response."""
    settlement_id: str
    committed_at: str
    payments: List[Dict[str, Any]]


@dataclass
class AuthorizationResponse:
    """Authorization response."""
    authorization_id: str
    from_user_id: str
    from_handle: str
    to_user_id: str
    to_handle: str
    amount: int
    captured_amount: int
    remaining_amount: int
    note: str
    visibility: str
    status: str
    expires_at: Optional[str]
    payment_id: Optional[str]
    payment_ids: List[str]
    created_at: str


@dataclass
class AuthorizationListResponse:
    """List of authorizations."""
    authorizations: List[AuthorizationResponse]
    has_more: bool


import uuid

class PocketfulClient:
    """Minimal client for integration testing."""

    def __init__(self, base_url: str = "http://localhost:8080", timeout: float = 5.0):
        """Initialize the client."""
        self.base_url = base_url.rstrip("/")
        self.timeout = timeout
        self._token: Optional[str] = None

    def _generate_idempotency_key(self) -> str:
        """Generate a random idempotency key."""
        return str(uuid.uuid4())

    def _headers(self, idempotency_key: Optional[str] = None, method: str = "GET", path: str = "") -> Dict[str, str]:
        """Build request headers."""
        headers = {"Content-Type": "application/json"}
        if self._token:
            headers["Authorization"] = f"Bearer {self._token}"
        # Auto-generate idempotency key for write endpoints if not provided
        if idempotency_key is None and method == "POST":
            # Check if path is a write endpoint that requires idempotency
            write_paths = {
                "/payments",
                "/requests",
                "/splits",
                "/settlements",
                "/authorizations",
            }
            if path in write_paths or path.startswith("/requests/") or path.startswith("/authorizations/"):
                idempotency_key = self._generate_idempotency_key()
        if idempotency_key:
            headers["Idempotency-Key"] = idempotency_key
        return headers

    def _request(
        self,
        method: str,
        path: str,
        idempotency_key: Optional[str] = None,
        **kwargs
    ) -> httpx.Response:
        """Make an HTTP request."""
        url = f"{self.base_url}{path}"
        try:
            response = httpx.request(
                method,
                url,
                headers=self._headers(idempotency_key, method, path),
                timeout=self.timeout,
                **kwargs
            )
            response.raise_for_status()
            return response
        except httpx.HTTPError as e:
            # Convert to a more user-friendly error
            if hasattr(e, "response"):
                response = e.response
                if response.status_code >= 400:
                    try:
                        error_data = response.json()
                        if "error" in error_data:
                            error = error_data["error"]
                            raise PocketfulError(
                                error.get("code", "unknown_error"),
                                error.get("message", str(e)),
                                response.status_code
                            )
                    except PocketfulError:
                        raise
                    except Exception:
                        pass
            raise PocketfulError("unknown_error", str(e), 500)

    def signup(
        self,
        email: str,
        password: str,
        display_name: str
    ) -> AuthResponse:
        """Sign up a new user."""
        response = self._request(
            "POST",
            "/auth/signup",
            json={"email": email, "password": password, "display_name": display_name}
        )
        data = response.json()
        self._token = data["token"]
        return AuthResponse(
            user_id=data["user_id"],
            display_name=data["display_name"],
            token=data["token"]
        )

    def login(self, email: str, password: str) -> AuthResponse:
        """Login a user."""
        response = self._request(
            "POST",
            "/auth/login",
            json={"email": email, "password": password}
        )
        data = response.json()
        self._token = data["token"]
        return AuthResponse(
            user_id=data["user_id"],
            display_name=data["display_name"],
            token=data["token"]
        )

    def get_me(self) -> UserResponse:
        """Get current user information."""
        response = self._request("GET", "/me")
        data = response.json()
        return UserResponse(**data)

    def create_payment(
        self,
        to_handle: str,
        amount: int,
        note: str = "",
        visibility: str = "public",
        idempotency_key: Optional[str] = None
    ) -> PaymentResponse:
        """Create a payment."""
        response = self._request(
            "POST",
            "/payments",
            idempotency_key=idempotency_key,
            json={"to_handle": to_handle, "amount": amount, "note": note, "visibility": visibility}
        )
        data = response.json()
        return PaymentResponse(**data)

    def create_request(
        self,
        payer_handle: str,
        amount: int,
        note: str = "",
        idempotency_key: Optional[str] = None
    ) -> RequestResponse:
        """Create a money request."""
        response = self._request(
            "POST",
            "/requests",
            idempotency_key=idempotency_key,
            json={"payer_handle": payer_handle, "amount": amount, "note": note}
        )
        data = response.json()
        return RequestResponse(**data)

    def pay_request(
        self,
        request_id: str,
        visibility: str = "public",
        idempotency_key: Optional[str] = None
    ) -> PaymentResponse:
        """Pay a request."""
        response = self._request(
            "POST",
            f"/requests/{request_id}/pay",
            idempotency_key=idempotency_key,
            json={"visibility": visibility}
        )
        data = response.json()
        return PaymentResponse(**data)

    def decline_request(self, request_id: str) -> RequestResponse:
        """Decline a request."""
        response = self._request("POST", f"/requests/{request_id}/decline")
        data = response.json()
        return RequestResponse(**data)

    def cancel_request(self, request_id: str) -> RequestResponse:
        """Cancel a request."""
        response = self._request("POST", f"/requests/{request_id}/cancel")
        data = response.json()
        return RequestResponse(**data)

    def list_requests(
        self,
        direction: Optional[str] = None,
        status: Optional[str] = None,
        limit: int = 50,
        offset: int = 0
    ) -> RequestListResponse:
        """List requests."""
        params = {"limit": limit, "offset": offset}
        if direction:
            params["direction"] = direction
        if status:
            params["status"] = status
        response = self._request("GET", "/requests", params=params)
        data = response.json()
        return RequestListResponse(
            requests=[RequestResponse(**r) for r in data["requests"]],
            has_more=data["has_more"]
        )

    def create_split(
        self,
        amount: int,
        participant_handles: List[str],
        note: str = "",
        idempotency_key: Optional[str] = None
    ) -> SplitResponse:
        """Create a split."""
        response = self._request(
            "POST",
            "/splits",
            idempotency_key=idempotency_key,
            json={
                "amount": amount,
                "participant_handles": participant_handles,
                "note": note
            }
        )
        data = response.json()
        return SplitResponse(**data)

    def get_activity(self, limit: int = 50, offset: int = 0) -> ActivityResponse:
        """Get activity feed."""
        response = self._request("GET", "/activity", params={"limit": limit, "offset": offset})
        data = response.json()
        return ActivityResponse(
            payments=[PaymentResponse(**p) for p in data["payments"]],
            has_more=data["has_more"]
        )

    def create_settlement(
        self,
        transfers: List[Dict[str, Any]],
        idempotency_key: Optional[str] = None
    ) -> SettlementResponse:
        """Create a settlement."""
        response = self._request(
            "POST",
            "/settlements",
            idempotency_key=idempotency_key,
            json={"transfers": transfers}
        )
        data = response.json()
        return SettlementResponse(**data)

    # Authorization methods
    def create_authorization(
        self,
        to_handle: str,
        amount: int,
        note: str = "",
        visibility: str = "public",
        expires_at: Optional[str] = None,
        idempotency_key: Optional[str] = None
    ) -> AuthorizationResponse:
        """Create an authorization."""
        body = {"to_handle": to_handle, "amount": amount, "note": note, "visibility": visibility}
        if expires_at:
            body["expires_at"] = expires_at
        response = self._request(
            "POST",
            "/authorizations",
            idempotency_key=idempotency_key,
            json=body
        )
        data = response.json()
        return AuthorizationResponse(**data)

    def capture_authorization(
        self,
        authorization_id: str,
        amount: Optional[int] = None,
        final: bool = False,
        idempotency_key: Optional[str] = None
    ) -> AuthorizationResponse:
        """Capture an authorization."""
        body = {"final": final}
        if amount is not None:
            body["amount"] = amount
        response = self._request(
            "POST",
            f"/authorizations/{authorization_id}/capture",
            idempotency_key=idempotency_key,
            json=body
        )
        data = response.json()
        return AuthorizationResponse(**data)

    def void_authorization(
        self,
        authorization_id: str,
        idempotency_key: Optional[str] = None
    ) -> AuthorizationResponse:
        """Void an authorization."""
        response = self._request(
            "POST",
            f"/authorizations/{authorization_id}/void",
            idempotency_key=idempotency_key
        )
        data = response.json()
        return AuthorizationResponse(**data)

    def list_authorizations(
        self,
        direction: Optional[str] = None,
        status: Optional[str] = None,
        limit: int = 50,
        offset: int = 0
    ) -> AuthorizationListResponse:
        """List authorizations."""
        params = {"limit": limit, "offset": offset}
        if direction:
            params["direction"] = direction
        if status:
            params["status"] = status
        response = self._request("GET", "/authorizations", params=params)
        data = response.json()
        return AuthorizationListResponse(
            authorizations=[AuthorizationResponse(**a) for a in data["authorizations"]],
            has_more=data["has_more"]
        )

    def reset_fixture(self, fixture: Dict[str, Any]) -> None:
        """Reset the fixture."""
        self._request("POST", "/_test/reset", json=fixture)

    def export_state(self) -> Dict[str, Any]:
        """Export the current state."""
        response = self._request("GET", "/_test/export")
        data = response.json()
        return data["state"]

    def import_state(self, state: Dict[str, Any]) -> None:
        """Import a state."""
        self._request("POST", "/_test/import", json={
            "track": "pocketful",
            "format_version": 1,
            "state": state
        })


class PocketfulError(Exception):
    """Pocketful API error."""

    def __init__(self, code: str, message: str, status_code: int = 500):
        self.code = code
        self.message = message
        self.status_code = status_code
        super().__init__(f"{code}: {message}")


# Convenience functions for testing

def create_test_user(client: PocketfulClient, email: str, password: str, display_name: str) -> AuthResponse:
    """Create a test user."""
    try:
        return client.signup(email, password, display_name)
    except PocketfulError as e:
        if e.code == "email_taken":
            return client.login(email, password)
        raise


def get_user_by_handle(client: PocketfulClient, handle: str) -> UserResponse:
    """Get a user by handle."""
    users = client.list_requests()
    for user in users.requests:
        if user.payer_handle == handle:
            return UserResponse(
                user_id=user.payer_id,
                display_name=user.payer_handle,
                handle=handle,
                balance=user.amount,
                currency="EUR",
                minor_units=2
            )
    raise PocketfulError("not_found", f"User {handle} not found")