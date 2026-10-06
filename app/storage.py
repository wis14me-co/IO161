import threading
import json
import hashlib
from typing import Optional, Dict, List, Any, Tuple, Set
from datetime import datetime, timezone
from dataclasses import dataclass, field
from app.models import (
    Fixture, FixtureUser, FixturePayment, FixtureRequest, FixtureAuthorization,
    PaymentResponse, RequestResponse, SplitResponse, SplitShare,
    SettlementResponse, SettlementPaymentResponse
)
import bcrypt

# WebSocket notification imports (lazy import to avoid circular dependency)
_websocket_manager = None


@dataclass
class User:
    id: str
    email: str
    password_hash: str
    display_name: str
    handle: str
    balance: int = 0
    tokens: List[str] = field(default_factory=list)


@dataclass
class Payment:
    id: str
    from_user_id: str
    to_user_id: str
    amount: int
    note: str
    visibility: str
    request_id: Optional[str]
    created_at: str
    settlement_id: Optional[str] = None


@dataclass
class Request:
    id: str
    requester_id: str
    payer_id: str
    amount: int
    note: str
    status: str
    payment_id: Optional[str]
    created_at: str


@dataclass
class Authorization:
    id: str
    from_user_id: str
    to_user_id: str
    amount: int
    note: str = ""
    visibility: str = "public"
    status: str = "open"
    expires_at: Optional[str] = None
    created_at: str = field(default_factory=lambda: datetime.now(timezone.utc).isoformat().replace("+00:00", "Z"))
    payment_id: Optional[str] = None
    payment_ids: List[str] = field(default_factory=list)
    captured_amount: int = 0

    @property
    def remaining_amount(self) -> int:
        if self.status != "open":
            return 0
        return max(0, self.amount - self.captured_amount)

    def is_open_and_valid(self) -> bool:
        """Check if authorization is open and not expired."""
        from datetime import datetime, timezone
        if self.status != "open":
            return False
        if self.expires_at:
            try:
                expires = datetime.fromisoformat(self.expires_at.replace("Z", "+00:00"))
                if expires <= datetime.now(timezone.utc):
                    return False
            except ValueError:
                pass
        return True


@dataclass
class IdempotencyRecord:
    key: str
    user_id: str
    method: str
    path: str
    body_hash: str
    response_status: int
    response_body: dict
    created_at: str


class Storage:
    def __init__(self):
        self._lock = threading.RLock()
        self.users: Dict[str, User] = {}
        self.users_by_handle: Dict[str, str] = {}
        self.users_by_email: Dict[str, str] = {}
        self.payments: Dict[str, Payment] = {}
        self.payments_by_user: Dict[str, List[str]] = {}
        self.requests: Dict[str, Request] = {}
        self.requests_by_user: Dict[str, List[str]] = {}
        self.idempotency_keys: Dict[str, IdempotencyRecord] = {}
        self.splits: Dict[str, dict] = {}
        self.settlements: Dict[str, dict] = {}
        self.authorizations: Dict[str, Authorization] = {}
        self.refunds: Dict[str, Payment] = {}  # Track refund payments
        self.correction_batches: Dict[str, dict] = {}  # Track correction batches
        self.currency: str = "EUR"
        self.minor_units: int = 2
        self.settlement_operator_ids: Set[str] = set()
        self._id_counter = 0

    @classmethod
    def set_websocket_manager(cls, manager):
        """Set the WebSocket manager for sending notifications."""
        global _websocket_manager
        _websocket_manager = manager

    def _generate_id(self, prefix: str) -> str:
        self._id_counter += 1
        return f"{prefix}_{self._id_counter}"

    def _now_iso(self) -> str:
        return datetime.now(timezone.utc).isoformat().replace("+00:00", "Z")

    def _hash_body(self, body: dict) -> str:
        return hashlib.sha256(json.dumps(body, sort_keys=True, separators=(',', ':')).encode()).hexdigest()

    # User operations
    def create_user(self, email: str, password: str, display_name: str, handle: str, balance: int = 0) -> User:
        with self._lock:
            # Check for duplicate email
            if email.lower() in self.users_by_email:
                raise ValueError("email already exists")
            # Check for duplicate handle
            if handle in self.users_by_handle:
                raise ValueError("handle already exists")
            
            password_hash = bcrypt.hashpw(password.encode(), bcrypt.gensalt()).decode()
            user = User(
                id=self._generate_id("u"),
                email=email.lower(),
                password_hash=password_hash,
                display_name=display_name,
                handle=handle,
                balance=balance
            )
            self.users[user.id] = user
            self.users_by_handle[handle] = user.id
            self.users_by_email[email.lower()] = user.id
            self.payments_by_user[user.id] = []
            self.requests_by_user[user.id] = []
            return user

    def get_user_by_id(self, user_id: str) -> Optional[User]:
        with self._lock:
            return self.users.get(user_id)

    def get_user_by_handle(self, handle: str) -> Optional[User]:
        with self._lock:
            user_id = self.users_by_handle.get(handle)
            if user_id:
                return self.users.get(user_id)
            return None

    def get_user_by_email(self, email: str) -> Optional[User]:
        with self._lock:
            user_id = self.users_by_email.get(email.lower())
            if user_id:
                return self.users.get(user_id)
            return None

    def verify_password(self, user: User, password: str) -> bool:
        return bcrypt.checkpw(password.encode(), user.password_hash.encode())

    def create_token(self, user_id: str) -> str:
        with self._lock:
            token = f"tok_{self._generate_id('')}"
            user = self.users.get(user_id)
            if user:
                user.tokens.append(token)
            return token

    def get_user_by_token(self, token: str) -> Optional[User]:
        with self._lock:
            for user in self.users.values():
                if token in user.tokens:
                    return user
            return None

    def update_balance(self, user_id: str, delta: int) -> int:
        with self._lock:
            user = self.users.get(user_id)
            if user:
                new_balance = user.balance + delta
                if new_balance < 0:
                    raise ValueError("insufficient_funds")
                user.balance = new_balance
                return user.balance
            raise ValueError("user_not_found")

    def atomic_transfer(self, from_user_id: str, to_user_id: str, amount: int) -> Tuple[int, int]:
        with self._lock:
            from_user = self.users.get(from_user_id)
            to_user = self.users.get(to_user_id)
            if not from_user or not to_user:
                raise ValueError("user_not_found")
            if from_user.balance < amount:
                raise ValueError("insufficient_funds")
            from_user.balance -= amount
            to_user.balance += amount
            return from_user.balance, to_user.balance

    # Payment operations
    def create_payment(self, from_user_id: str, to_user_id: str, amount: int, note: str,
                       visibility: str, request_id: Optional[str], settlement_id: Optional[str] = None) -> Payment:
        with self._lock:
            payment = Payment(
                id=self._generate_id("p"),
                from_user_id=from_user_id,
                to_user_id=to_user_id,
                amount=amount,
                note=note,
                visibility=visibility,
                request_id=request_id,
                created_at=self._now_iso(),
                settlement_id=settlement_id
            )
            self.payments[payment.id] = payment
            self.payments_by_user.setdefault(from_user_id, []).append(payment.id)
            self.payments_by_user.setdefault(to_user_id, []).append(payment.id)

            # Send WebSocket notification
            self._notify_payment_created(payment)

            return payment

    def create_refund(self, user_id: str, from_user_id: str, to_user_id: str, amount: int, note: str,
                      visibility: str, original_payment_id: str) -> Payment:
        """Create a refund payment from receiver to original sender."""
        with self._lock:
            payment = Payment(
                id=self._generate_id("p"),
                from_user_id=user_id,
                to_user_id=from_user_id,  # refund goes back to original sender
                amount=amount,
                note=note,
                visibility=visibility,
                request_id=original_payment_id,  # link to original payment
                created_at=self._now_iso()
            )
            self.payments[payment.id] = payment
            self.payments_by_user.setdefault(user_id, []).append(payment.id)
            self.payments_by_user.setdefault(to_user_id, []).append(payment.id)
            # Also track in refunds dict
            self.refunds[payment.id] = {
                "original_payment_id": original_payment_id,
                "refunded_amount": amount
            }
            return payment

    def get_refund(self, payment_id: str) -> Optional[dict]:
        """Get refund information for a payment."""
        with self._lock:
            return self.refunds.get(payment_id)

    def get_payment(self, payment_id: str) -> Optional[Payment]:
        with self._lock:
            return self.payments.get(payment_id)

    def get_payments_for_user(self, user_id: str, limit: int, offset: int) -> List[Payment]:
        with self._lock:
            payment_ids = self.payments_by_user.get(user_id, [])
            payments = [self.payments[pid] for pid in payment_ids if pid in self.payments]
            payments.sort(key=lambda p: p.created_at, reverse=True)
            return payments[offset:offset + limit]

    def get_all_payments(self) -> List[Payment]:
        with self._lock:
            return list(self.payments.values())

    # Request operations
    def create_request(self, requester_id: str, payer_id: str, amount: int, note: str) -> Request:
        with self._lock:
            request = Request(
                id=self._generate_id("rq"),
                requester_id=requester_id,
                payer_id=payer_id,
                amount=amount,
                note=note,
                status="pending",
                payment_id=None,
                created_at=self._now_iso()
            )
            self.requests[request.id] = request
            self.requests_by_user.setdefault(requester_id, []).append(request.id)
            self.requests_by_user.setdefault(payer_id, []).append(request.id)
            return request

    def get_request(self, request_id: str) -> Optional[Request]:
        with self._lock:
            return self.requests.get(request_id)

    def update_request_status(self, request_id: str, status: str, payment_id: Optional[str] = None) -> Optional[Request]:
        with self._lock:
            request = self.requests.get(request_id)
            if request:
                request.status = status
                if payment_id:
                    request.payment_id = payment_id
            return request

    def get_requests_for_user(self, user_id: str, direction: Optional[str], status: Optional[str],
                               limit: int, offset: int) -> List[Request]:
        with self._lock:
            request_ids = self.requests_by_user.get(user_id, [])
            requests = [self.requests[rid] for rid in request_ids if rid in self.requests]
            if direction == "incoming":
                requests = [r for r in requests if r.payer_id == user_id]
            elif direction == "outgoing":
                requests = [r for r in requests if r.requester_id == user_id]
            if status:
                requests = [r for r in requests if r.status == status]
            requests.sort(key=lambda r: r.created_at, reverse=True)
            return requests[offset:offset + limit]

    # Split operations
    def create_split(self, caller_id: str, amount: int, participant_handles: List[str], note: str,
                     shares: List[SplitShare], requests: List[Request]) -> str:
        with self._lock:
            split_id = self._generate_id("sp")
            self.splits[split_id] = {
                "split_id": split_id,
                "amount": amount,
                "currency": self.currency,
                "note": note,
                "shares": [{"handle": s.handle, "amount": s.amount} for s in shares],
                "requests": [{"request_id": r.id, "requester_id": r.requester_id, "payer_id": r.payer_id,
                              "amount": r.amount, "note": r.note, "status": r.status,
                              "created_at": r.created_at} for r in requests],
                "created_at": self._now_iso()
            }

            # Get all user IDs involved in the split
            user_ids = set()
            for s in shares:
                user = self.get_user_by_handle(s.handle)
                if user:
                    user_ids.add(user.id)
            for r in requests:
                user_ids.add(r.requester_id)
                user_ids.add(r.payer_id)

            # Send WebSocket notification
            self._notify_split_created(split_id, amount, note, user_ids)

            return split_id

    # Settlement operations
    def create_settlement(self, settlement_id: str, transfers: List[Payment], committed_at: str) -> SettlementResponse:
        with self._lock:
            self.settlements[settlement_id] = {
                "settlement_id": settlement_id,
                "committed_at": committed_at,
                "payments": [p.id for p in transfers]
            }

            # Send WebSocket notification
            user_ids = set()
            for p in transfers:
                user_ids.add(p.from_user_id)
                user_ids.add(p.to_user_id)
            self._notify_settlement_created(settlement_id, user_ids)

            return SettlementResponse(
                settlement_id=settlement_id,
                committed_at=committed_at,
                payments=[
                    SettlementPaymentResponse(
                        payment_id=p.id,
                        from_user_id=p.from_user_id,
                        from_handle=self.users[p.from_user_id].handle,
                        to_user_id=p.to_user_id,
                        to_handle=self.users[p.to_user_id].handle,
                        amount=p.amount,
                        currency=self.currency,
                        note=p.note,
                        visibility=p.visibility,
                        request_id=p.request_id,
                        created_at=p.created_at,
                        settlement_id=settlement_id
                    ) for p in transfers
                ]
            )

    def atomic_settlement(self, operator_id: str, transfers_data: List[dict]) -> Tuple[str, str, List[Payment]]:
        """
        Atomically execute a settlement: validate all transfers, check balances,
        execute transfers, and create payment records - all under a single lock.
        Returns (settlement_id, committed_at, payments_list)
        """
        with self._lock:
            # Validate all handles and calculate net changes
            net_changes = {}
            transfer_objects = []
            
            for t in transfers_data:
                from_user = self.get_user_by_handle(t["from_handle"])
                to_user = self.get_user_by_handle(t["to_handle"])
                
                if not from_user or not to_user:
                    raise ValueError("not_found")
                
                if from_user.id == to_user.id:
                    raise ValueError("self_payment")
                
                amount = t["amount"]
                if not isinstance(amount, int) or amount < 1 or amount > 1_000_000_000:
                    raise ValueError("validation_failed")
                
                note = t.get("note", "")
                if len(note) > 200:
                    raise ValueError("validation_failed")
                
                visibility = t.get("visibility", "public")
                if visibility not in ("public", "private"):
                    raise ValueError("validation_failed")
                
                net_changes[from_user.id] = net_changes.get(from_user.id, 0) - amount
                net_changes[to_user.id] = net_changes.get(to_user.id, 0) + amount
                
                transfer_objects.append((from_user, to_user, amount, note, visibility))
            
            # Check all balances would be non-negative
            for uid, delta in net_changes.items():
                user = self.users.get(uid)
                if user and user.balance + delta < 0:
                    raise ValueError("insufficient_funds")
            
            # Execute all transfers atomically
            committed_at = self._now_iso()
            settlement_id = self._generate_id("st")
            
            created_payments = []
            for from_user, to_user, amount, note, visibility in transfer_objects:
                from_user.balance -= amount
                to_user.balance += amount
                payment = Payment(
                    id=self._generate_id("p"),
                    from_user_id=from_user.id,
                    to_user_id=to_user.id,
                    amount=amount,
                    note=note,
                    visibility=visibility,
                    request_id=None,
                    created_at=committed_at,
                    settlement_id=settlement_id
                )
                self.payments[payment.id] = payment
                self.payments_by_user.setdefault(from_user.id, []).append(payment.id)
                self.payments_by_user.setdefault(to_user.id, []).append(payment.id)
                created_payments.append(payment)
            
            self.settlements[settlement_id] = {
                "settlement_id": settlement_id,
                "committed_at": committed_at,
                "payments": [p.id for p in created_payments]
            }
            
            return settlement_id, committed_at, created_payments

    # Authorization operations
    def create_authorization(self, from_user_id: str, to_user_id: str, amount: int, note: str,
                             visibility: str = "public", expires_at: Optional[str] = None) -> Authorization:
        with self._lock:
            auth = Authorization(
                id=self._generate_id("auth"),
                from_user_id=from_user_id,
                to_user_id=to_user_id,
                amount=amount,
                note=note,
                visibility=visibility,
                expires_at=expires_at,
                created_at=self._now_iso(),
            )
            self.authorizations[auth.id] = auth

            # Send WebSocket notification
            self._notify_authorization_created(auth)

            return auth

    def get_authorization(self, auth_id: str) -> Optional[Authorization]:
        """Get authorization by ID, checking for expiry."""
        from datetime import datetime, timezone
        
        with self._lock:
            auth = self.authorizations.get(auth_id)
            if auth and auth.status == "open" and auth.expires_at:
                now = datetime.now(timezone.utc)
                try:
                    expires = datetime.fromisoformat(auth.expires_at.replace("Z", "+00:00"))
                    if expires <= now:
                        # Auto-update expired authorization
                        auth.status = "expired"
                except ValueError:
                    pass
            return auth

    def get_authorizations_for_user(self, user_id: str, direction: Optional[str] = None, status: Optional[str] = None,
                                     limit: int = 50, offset: int = 0) -> List[Authorization]:
        """Get authorizations for a user with optional direction and status filtering.
        Also checks for expired authorizations and auto-updates them."""
        from datetime import datetime, timezone
        
        with self._lock:
            now = datetime.now(timezone.utc)
            
            # Filter by user involvement
            auths = [a for a in self.authorizations.values() if a.from_user_id == user_id or a.to_user_id == user_id]
            
            # Filter by direction
            if direction == "incoming":
                auths = [a for a in auths if a.to_user_id == user_id]
            elif direction == "outgoing":
                auths = [a for a in auths if a.from_user_id == user_id]
            
            # Check for expired authorizations and auto-update
            for auth in auths:
                if auth.status == "open" and auth.expires_at:
                    try:
                        expires = datetime.fromisoformat(auth.expires_at.replace("Z", "+00:00"))
                        if expires <= now:
                            # Auto-update expired authorization
                            auth.status = "expired"
                            # Release held funds by reducing captured_amount tracking
                            # The held amount is implicitly released when status changes
                    except ValueError:
                        pass
            
            # Filter by status (after expiry check)
            if status:
                auths = [a for a in auths if a.status == status]
            
            auths.sort(key=lambda a: a.created_at, reverse=True)
            return auths[offset:offset + limit]

    def update_authorization_status(self, auth_id: str, status: str, captured_amount: int = 0, payment_id: Optional[str] = None, payment_ids: Optional[List[str]] = None) -> Optional[Authorization]:
        with self._lock:
            auth = self.authorizations.get(auth_id)
            if auth:
                auth.status = status
                if captured_amount is not None:
                    auth.captured_amount = captured_amount
                if payment_id is not None:
                    auth.payment_id = payment_id
                    # Add to payment_ids list if not already present
                    if payment_id not in auth.payment_ids:
                        auth.payment_ids.append(payment_id)
                # Also handle explicit payment_ids list
                if payment_ids is not None:
                    auth.payment_ids = payment_ids
            return auth

    # Correction batch operations
    def create_correction_batch(self, operator_id: str, corrections: List[dict]) -> str:
        """Create a correction batch with the given corrections."""
        with self._lock:
            correction_batch_id = self._generate_id("bc")
            
            # Validate corrections
            payment_ids = []
            for item in corrections:
                payment_id = item.get("payment_id")
                expected_revision = item.get("expected_revision")
                amount = item.get("amount")
                effective_at = item.get("effective_at")
                reason = item.get("reason", "")

                if not payment_id:
                    raise ValueError("payment_id is required")
                if expected_revision is None:
                    raise ValueError("expected_revision is required")
                if not isinstance(amount, int) or amount < 1:
                    raise ValueError("amount must be positive integer")
                if effective_at is None:
                    raise ValueError("effective_at is required")
                
                payment_ids.append(payment_id)

            # Check that all payment_ids are distinct
            if len(payment_ids) != len(set(payment_ids)):
                raise ValueError("payment_ids must be distinct")

            # Store the correction batch
            self.correction_batches[correction_batch_id] = {
                "correction_batch_id": correction_batch_id,
                "operator_id": operator_id,
                "corrections": corrections,
                "status": "processed",
                "created_at": self._now_iso()
            }
            
            return correction_batch_id

    def get_correction_batch(self, batch_id: str) -> Optional[dict]:
        """Get correction batch information."""
        with self._lock:
            return self.correction_batches.get(batch_id)

    def update_correction_batch_status(self, batch_id: str, status: str) -> Optional[dict]:
        """Update correction batch status."""
        with self._lock:
            if batch_id in self.correction_batches:
                self.correction_batches[batch_id]["status"] = status
                return self.correction_batches[batch_id]
            return None

    # Idempotency operations
    def check_idempotency(self, user_id: str, key: str, method: str, path: str, body: dict) -> Optional[Tuple[int, dict]]:
        with self._lock:
            record_key = f"{user_id}:{key}:{method}:{path}"
            record = self.idempotency_keys.get(record_key)
            if not record:
                return None
            body_hash = self._hash_body(body)
            if record.body_hash != body_hash:
                return (409, {"error": {"code": "idempotency_key_reuse", "message": "idempotency key reused with different body"}})
            return (record.response_status, record.response_body)

    def store_idempotency(self, user_id: str, key: str, method: str, path: str, body: dict,
                          response_status: int, response_body: dict) -> IdempotencyRecord:
        with self._lock:
            record_key = f"{user_id}:{key}:{method}:{path}"
            body_hash = self._hash_body(body)
            record = IdempotencyRecord(
                key=key,
                user_id=user_id,
                method=method,
                path=path,
                body_hash=body_hash,
                response_status=response_status,
                response_body=response_body,
                created_at=self._now_iso()
            )
            self.idempotency_keys[record_key] = record
            return record

    # Fixture operations
    def reset(self, fixture: Optional[Fixture] = None) -> None:
        with self._lock:
            self.users.clear()
            self.users_by_handle.clear()
            self.users_by_email.clear()
            self.payments.clear()
            self.payments_by_user.clear()
            self.requests.clear()
            self.requests_by_user.clear()
            self.idempotency_keys.clear()
            self.splits.clear()
            self.settlements.clear()
            self.refunds.clear()
            self.correction_batches.clear()
            self.authorizations.clear()
            self._id_counter = 0

            if fixture:
                self.currency = fixture.currency
                self.minor_units = fixture.minor_units
                self.settlement_operator_ids = set(fixture.settlement_operator_ids or [])

                # Create users
                for fu in fixture.users:
                    user = User(
                        id=fu.id,
                        email=fu.email.lower(),
                        password_hash=bcrypt.hashpw(fu.password.encode(), bcrypt.gensalt()).decode(),
                        display_name=fu.display_name,
                        handle=fu.handle,
                        balance=fu.balance
                    )
                    self.users[user.id] = user
                    self.users_by_handle[user.handle] = user.id
                    self.users_by_email[user.email] = user.id
                    self.payments_by_user[user.id] = []
                    self.requests_by_user[user.id] = []

                # Create payments
                for fp in fixture.payments:
                    payment = Payment(
                        id=fp.id,
                        from_user_id=fp.from_user_id,
                        to_user_id=fp.to_user_id,
                        amount=fp.amount,
                        note=fp.note,
                        visibility=fp.visibility,
                        request_id=None,
                        created_at=self._now_iso()
                    )
                    self.payments[payment.id] = payment
                    self.payments_by_user.setdefault(fp.from_user_id, []).append(payment.id)
                    self.payments_by_user.setdefault(fp.to_user_id, []).append(payment.id)

                # Create requests
                for fr in fixture.requests:
                    request = Request(
                        id=fr.id,
                        requester_id=fr.requester_id,
                        payer_id=fr.payer_id,
                        amount=fr.amount,
                        note=fr.note,
                        status=fr.status,
                        payment_id=None,
                        created_at=self._now_iso()
                    )
                    self.requests[request.id] = request
                    self.requests_by_user.setdefault(fr.requester_id, []).append(request.id)
                    self.requests_by_user.setdefault(fr.payer_id, []).append(request.id)

                # Create authorizations
                for fa in fixture.authorizations:
                    auth = Authorization(
                        id=fa.id,
                        from_user_id=fa.from_user_id,
                        to_user_id=fa.to_user_id,
                        amount=fa.amount,
                        note=fa.note,
                        visibility=fa.visibility,
                        expires_at=fa.expires_at,
                        created_at=self._now_iso()
                    )
                    self.authorizations[auth.id] = auth

    def export_state(self) -> dict:
        with self._lock:
            return {
                "currency": self.currency,
                "minor_units": self.minor_units,
                "settlement_operator_ids": self.settlement_operator_ids,
                "users": {
                    uid: {
                        "id": u.id,
                        "email": u.email,
                        "password_hash": u.password_hash,
                        "display_name": u.display_name,
                        "handle": u.handle,
                        "balance": u.balance,
                        "tokens": u.tokens
                    } for uid, u in self.users.items()
                },
                "payments": {
                    pid: {
                        "id": p.id,
                        "from_user_id": p.from_user_id,
                        "to_user_id": p.to_user_id,
                        "amount": p.amount,
                        "note": p.note,
                        "visibility": p.visibility,
                        "request_id": p.request_id,
                        "created_at": p.created_at,
                        "settlement_id": p.settlement_id
                    } for pid, p in self.payments.items()
                },
                "refunds": {
                    rid: {
                        "original_payment_id": v["original_payment_id"],
                        "refunded_amount": v["refunded_amount"]
                    } for rid, v in self.refunds.items()
                },
                "correction_batches": self.correction_batches,
                "requests": {
                    rid: {
                        "id": r.id,
                        "requester_id": r.requester_id,
                        "payer_id": r.payer_id,
                        "amount": r.amount,
                        "note": r.note,
                        "status": r.status,
                        "payment_id": r.payment_id,
                        "created_at": r.created_at
                    } for rid, r in self.requests.items()
                },
                "idempotency_keys": {
                    k: {
                        "key": v.key,
                        "user_id": v.user_id,
                        "method": v.method,
                        "path": v.path,
                        "body_hash": v.body_hash,
                        "response_status": v.response_status,
                        "response_body": v.response_body,
                        "created_at": v.created_at
                    } for k, v in self.idempotency_keys.items()
                },
                "splits": self.splits,
                "settlements": self.settlements,
                "authorizations": {
                    aid: {
                        "id": a.id,
                        "from_user_id": a.from_user_id,
                        "to_user_id": a.to_user_id,
                        "amount": a.amount,
                        "captured_amount": a.captured_amount,
                        "note": a.note,
                        "visibility": a.visibility,
                        "status": a.status,
                        "expires_at": a.expires_at,
                        "created_at": a.created_at,
                        "payment_id": a.payment_id,
                        "payment_ids": a.payment_ids,
                    } for aid, a in self.authorizations.items()
                },
                "_id_counter": self._id_counter
            }

    def import_state(self, state: dict) -> None:
        with self._lock:
            self.users.clear()
            self.users_by_handle.clear()
            self.users_by_email.clear()
            self.payments.clear()
            self.payments_by_user.clear()
            self.requests.clear()
            self.requests_by_user.clear()
            self.idempotency_keys.clear()
            self.splits.clear()
            self.settlements.clear()
            self.refunds.clear()
            self.correction_batches.clear()

            self.currency = state["currency"]
            self.minor_units = state["minor_units"]
            self.settlement_operator_ids = set(state["settlement_operator_ids"])
            self._id_counter = state.get("_id_counter", 0)

            for uid, udata in state["users"].items():
                user = User(**udata)
                self.users[uid] = user
                self.users_by_handle[user.handle] = uid
                self.users_by_email[user.email] = uid
                self.payments_by_user[uid] = []

            for pid, pdata in state["payments"].items():
                payment = Payment(**pdata)
                self.payments[pid] = payment
                self.payments_by_user.setdefault(pdata["from_user_id"], []).append(pid)
                self.payments_by_user.setdefault(pdata["to_user_id"], []).append(pid)

            for rid, rdata in state["requests"].items():
                request = Request(**rdata)
                self.requests[rid] = request
                self.requests_by_user.setdefault(rdata["requester_id"], []).append(rid)
                self.requests_by_user.setdefault(rdata["payer_id"], []).append(rid)

            for k, vdata in state["idempotency_keys"].items():
                self.idempotency_keys[k] = IdempotencyRecord(**vdata)

            for rid, rdata in state.get("refunds", {}).items():
                self.refunds[rid] = {
                    "original_payment_id": rdata.get("original_payment_id"),
                    "refunded_amount": rdata.get("refunded_amount")
                }

            self.splits = state.get("splits", {})
            self.settlements = state.get("settlements", {})
            for bid, bdata in state.get("correction_batches", {}).items():
                self.correction_batches[bid] = bdata

            # Restore authorizations
            for aid, adata in state.get("authorizations", {}).items():
                auth = Authorization(**adata)
                self.authorizations[aid] = auth

    def validate_fixture(self, fixture: Fixture) -> List[str]:
        errors = []
        # Check currency/minor_units
        if fixture.minor_units not in (0, 2, 3):
            errors.append("minor_units must be 0, 2, or 3")
        if not fixture.currency or len(fixture.currency) != 3:
            errors.append("currency must be 3-letter code")

        # Check currency/minor_units consistency
        expected_minor = {"EUR": 2, "JPY": 0, "BHD": 3}.get(fixture.currency)
        if expected_minor is not None and fixture.minor_units != expected_minor:
            errors.append(f"minor_units must be {expected_minor} for {fixture.currency}")

        # Check handle uniqueness
        handles = [u.handle for u in fixture.users]
        if len(handles) != len(set(handles)):
            errors.append("handles must be unique")

        # Check user balances non-negative
        for u in fixture.users:
            if u.balance < 0:
                errors.append(f"user {u.id} has negative balance")

        # Check seeded payments consistency
        user_ids = {u.id for u in fixture.users}
        for p in fixture.payments:
            if p.from_user_id not in user_ids or p.to_user_id not in user_ids:
                errors.append(f"payment {p.id} references unknown user")
            if p.amount <= 0 or p.amount > 1_000_000_000:
                errors.append(f"payment {p.id} has invalid amount")
            if p.visibility not in ("public", "private"):
                errors.append(f"payment {p.id} has invalid visibility")

        # Check seeded requests
        for r in fixture.requests:
            if r.requester_id not in user_ids or r.payer_id not in user_ids:
                errors.append(f"request {r.id} references unknown user")
            if r.amount <= 0 or r.amount > 1_000_000_000:
                errors.append(f"request {r.id} has invalid amount")
            if r.status not in ("pending", "paid", "declined", "cancelled"):
                errors.append(f"request {r.id} has invalid status")

        # Check settlement operators
        for op_id in fixture.settlement_operator_ids:
            if op_id not in user_ids:
                errors.append(f"settlement operator {op_id} not found")

        # Check seeded authorizations
        if fixture.authorizations:
            from datetime import datetime, timezone
            now = datetime.now(timezone.utc)
            user_balances = {u.id: u.balance for u in fixture.users}
            open_holds = {uid: 0 for uid in user_ids}
            
            for fa in fixture.authorizations:
                if fa.from_user_id not in user_ids or fa.to_user_id not in user_ids:
                    errors.append(f"authorization {fa.id} references unknown user")
                if fa.amount <= 0 or fa.amount > 1_000_000_000:
                    errors.append(f"authorization {fa.id} has invalid amount")
                if fa.visibility not in ("public", "private"):
                    errors.append(f"authorization {fa.id} has invalid visibility")
                if fa.status not in ("open", "captured", "voided", "expired"):
                    errors.append(f"authorization {fa.id} has invalid status")
                
                # Check if authorization is open and not expired
                is_open_and_valid = False
                if fa.status == "open" and fa.expires_at:
                    try:
                        expires = datetime.fromisoformat(fa.expires_at.replace("Z", "+00:00"))
                        if expires > now:
                            is_open_and_valid = True
                    except ValueError:
                        pass
                elif fa.status == "open" and not fa.expires_at:
                    is_open_and_valid = True
                
                if is_open_and_valid:
                    open_holds[fa.from_user_id] = open_holds.get(fa.from_user_id, 0) + fa.amount
            
            # Check that open holds don't exceed user balance
            for uid, held_amount in open_holds.items():
                if held_amount > user_balances.get(uid, 0):
                    errors.append(f"user {uid} has open holds ({held_amount}) exceeding balance ({user_balances.get(uid, 0)})")

        return errors

    def _notify_payment_created(self, payment: Payment) -> None:
        """Send payment creation notification to relevant users."""
        if _websocket_manager:
            notification_data = {
                "payment_id": payment.id,
                "from_user_id": payment.from_user_id,
                "to_user_id": payment.to_user_id,
                "amount": payment.amount,
                "currency": self.currency,
                "note": payment.note,
                "visibility": payment.visibility,
                "created_at": payment.created_at
            }
            # Notify both sender and receiver
            user_ids = {payment.from_user_id, payment.to_user_id}
            try:
                import asyncio
                loop = asyncio.get_running_loop()
                loop.create_task(_websocket_manager.send_payment_update(notification_data, user_ids))
            except RuntimeError:
                # No event loop running, skip notification
                pass

    def _notify_split_created(self, split_id: str, amount: int, note: str, user_ids: Set[str]) -> None:
        """Send split creation notification to relevant users."""
        if _websocket_manager:
            notification_data = {
                "split_id": split_id,
                "amount": amount,
                "note": note,
                "created_at": self._now_iso()
            }
            try:
                import asyncio
                loop = asyncio.get_running_loop()
                loop.create_task(_websocket_manager.send_split_notification(notification_data, user_ids))
            except RuntimeError:
                # No event loop running, skip notification
                pass

    def _notify_settlement_created(self, settlement_id: str, user_ids: Set[str]) -> None:
        """Send settlement creation notification to relevant users."""
        if _websocket_manager:
            notification_data = {
                "settlement_id": settlement_id,
                "created_at": self._now_iso()
            }
            try:
                import asyncio
                loop = asyncio.get_running_loop()
                loop.create_task(_websocket_manager.send_settlement_alert(notification_data, user_ids))
            except RuntimeError:
                # No event loop running, skip notification
                pass

    def _notify_authorization_created(self, auth: Authorization) -> None:
        """Send authorization creation notification to relevant users."""
        if _websocket_manager:
            notification_data = {
                "authorization_id": auth.id,
                "from_user_id": auth.from_user_id,
                "to_user_id": auth.to_user_id,
                "amount": auth.amount,
                "note": auth.note,
                "visibility": auth.visibility,
                "created_at": auth.created_at
            }
            # Notify both sender and receiver
            user_ids = {auth.from_user_id, auth.to_user_id}
            try:
                import asyncio
                loop = asyncio.get_running_loop()
                loop.create_task(_websocket_manager.send_authorization_update(notification_data, user_ids))
            except RuntimeError:
                # No event loop running, skip notification
                pass


storage = Storage()