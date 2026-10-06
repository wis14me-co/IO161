import threading
import json
import hashlib
import secrets
from typing import Optional, Dict, List, Any, Tuple
from datetime import datetime, timezone
from dataclasses import dataclass, field
from app.models import (
    Fixture, FixtureUser, FixturePayment, FixtureRequest,
    FixtureAuthorization,
    PaymentResponse, RequestResponse, SplitResponse, SplitShare,
    SettlementResponse, SettlementPaymentResponse
)
from starlette.requests import Request
import bcrypt


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
    captured_amount: int
    note: str
    visibility: str
    status: str
    expires_at: Optional[str]
    payment_id: Optional[str]
    payment_ids: List[str]
    remaining_amount: int
    created_at: str


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


@dataclass
class Session:
    id: str
    user_id: str
    csrf_token: str
    expires_at: str
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
        self.authorizations: Dict[str, Authorization] = {}
        self.authorizations_by_user: Dict[str, List[str]] = {}
        self.idempotency_keys: Dict[str, IdempotencyRecord] = {}
        self.sessions: Dict[str, Session] = {}
        self.splits: Dict[str, dict] = {}
        self.settlements: Dict[str, dict] = {}
        self.currency: str = "EUR"
        self.minor_units: int = 2
        self.settlement_operator_ids: List[str] = []
        self.authorization_ttl_seconds: Optional[int] = None
        self._id_counter = 0

    def _generate_id(self, prefix: str) -> str:
        self._id_counter += 1
        return f"{prefix}_{self._id_counter}"

    def _now_iso(self) -> str:
        return datetime.now(timezone.utc).isoformat().replace("+00:00", "Z")

    def _hash_body(self, body: dict) -> str:
        return hashlib.sha256(json.dumps(body, sort_keys=True, separators=(',', ':')).encode()).hexdigest()

    def _is_expired(self, authorization: Authorization) -> bool:
        if authorization.expires_at is None:
            return False
        try:
            expires = datetime.fromisoformat(authorization.expires_at.replace("Z", "+00:00"))
            return expires <= datetime.now(timezone.utc)
        except ValueError:
            return False

    def _get_authorization_status(self, authorization: Authorization) -> str:
        if authorization.status in ("captured", "voided"):
            return authorization.status
        if self._is_expired(authorization):
            return "expired"
        return "open"

    # User operations
    def create_user(self, email: str, password: str, display_name: str, handle: str, balance: int = 0) -> User:
        with self._lock:
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
            self.authorizations_by_user[user.id] = []
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

    def get_available_balance(self, user_id: str) -> int:
        with self._lock:
            user = self.users.get(user_id)
            if not user:
                raise ValueError("user_not_found")
            held = 0
            for auth_id in self.authorizations_by_user.get(user_id, []):
                auth = self.authorizations.get(auth_id)
                if auth and auth.from_user_id == user_id:
                    status = self._get_authorization_status(auth)
                    if status == "open":
                        held += auth.remaining_amount
            available = user.balance - held
            return max(0, available)

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
            return payment

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

    # Authorization operations
    def create_authorization(self, from_user_id: str, to_user_id: str, amount: int, note: str,
                             visibility: str, expires_at: Optional[str]) -> Authorization:
        with self._lock:
            authorization = Authorization(
                id=self._generate_id("auth"),
                from_user_id=from_user_id,
                to_user_id=to_user_id,
                amount=amount,
                captured_amount=0,
                note=note,
                visibility=visibility,
                status="open",
                expires_at=expires_at,
                payment_id=None,
                payment_ids=[],
                remaining_amount=amount,
                created_at=self._now_iso()
            )
            self.authorizations[authorization.id] = authorization
            self.authorizations_by_user.setdefault(from_user_id, []).append(authorization.id)
            self.authorizations_by_user.setdefault(to_user_id, []).append(authorization.id)
            return authorization

    def get_authorization(self, authorization_id: str) -> Optional[Authorization]:
        with self._lock:
            return self.authorizations.get(authorization_id)

    def get_authorizations_for_user(self, user_id: str, direction: Optional[str], status: Optional[str],
                                     limit: int, offset: int) -> List[Authorization]:
        with self._lock:
            auth_ids = self.authorizations_by_user.get(user_id, [])
            authorizations = [self.authorizations[aid] for aid in auth_ids if aid in self.authorizations]
            
            if direction == "incoming":
                authorizations = [a for a in authorizations if a.to_user_id == user_id]
            elif direction == "outgoing":
                authorizations = [a for a in authorizations if a.from_user_id == user_id]
            
            # Compute effective status for filtering
            if status:
                filtered = []
                for a in authorizations:
                    effective_status = self._get_authorization_status(a)
                    if effective_status == status:
                        filtered.append(a)
                authorizations = filtered
            
            authorizations.sort(key=lambda a: a.created_at, reverse=True)
            return authorizations[offset:offset + limit]

    def capture_authorization(self, authorization_id: str, user_id: str, amount: Optional[int], final: bool) -> Tuple[Authorization, Optional[Payment]]:
        with self._lock:
            auth = self.authorizations.get(authorization_id)
            if not auth:
                raise ValueError("not_found")
            
            if auth.to_user_id != user_id:
                raise ValueError("forbidden")
            
            effective_status = self._get_authorization_status(auth)
            if effective_status != "open":
                raise ValueError("authorization_not_open")
            
            capture_amount = amount if amount is not None else auth.remaining_amount
            if capture_amount > auth.remaining_amount:
                raise ValueError("capture_exceeds_remaining")
            
            # Atomic transfer from payer to receiver
            from_user = self.users.get(auth.from_user_id)
            to_user = self.users.get(auth.to_user_id)
            if not from_user or not to_user:
                raise ValueError("user_not_found")
            
            # Update authorization
            auth.captured_amount += capture_amount
            auth.remaining_amount -= capture_amount
            auth.payment_ids.append("")  # placeholder, will update after payment creation
            
            if auth.remaining_amount == 0 or final:
                auth.status = "captured"
            else:
                auth.status = "open"
            
            # Create payment
            payment = Payment(
                id=self._generate_id("p"),
                from_user_id=auth.from_user_id,
                to_user_id=auth.to_user_id,
                amount=capture_amount,
                note=auth.note,
                visibility=auth.visibility,
                request_id=None,
                created_at=self._now_iso(),
                settlement_id=None
            )
            self.payments[payment.id] = payment
            self.payments_by_user.setdefault(auth.from_user_id, []).append(payment.id)
            self.payments_by_user.setdefault(auth.to_user_id, []).append(payment.id)
            
            # Update authorization with payment info
            auth.payment_id = payment.id
            auth.payment_ids[-1] = payment.id
            
            # Transfer balance
            from_user.balance -= capture_amount
            to_user.balance += capture_amount
            
            return auth, payment

    def void_authorization(self, authorization_id: str, user_id: str) -> Authorization:
        with self._lock:
            auth = self.authorizations.get(authorization_id)
            if not auth:
                raise ValueError("not_found")
            
            if auth.from_user_id != user_id:
                raise ValueError("forbidden")
            
            effective_status = self._get_authorization_status(auth)
            if effective_status != "open":
                raise ValueError("authorization_not_open")
            
            auth.status = "voided"
            auth.remaining_amount = 0
            return auth

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
            return split_id

    # Settlement operations
    def create_settlement(self, settlement_id: str, transfers: List[Payment], committed_at: str) -> SettlementResponse:
        with self._lock:
            self.settlements[settlement_id] = {
                "settlement_id": settlement_id,
                "committed_at": committed_at,
                "payments": [p.id for p in transfers]
            }
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
            
            # Check all balances would be non-negative (using available balance for senders)
            for uid, delta in net_changes.items():
                if delta < 0:  # sender
                    available = self.get_available_balance(uid)
                    if available + delta < 0:
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
                          response_status: int, response_body: dict) -> None:
        with self._lock:
            record_key = f"{user_id}:{key}:{method}:{path}"
            body_hash = self._hash_body(body)
            self.idempotency_keys[record_key] = IdempotencyRecord(
                key=key,
                user_id=user_id,
                method=method,
                path=path,
                body_hash=body_hash,
                response_status=response_status,
                response_body=response_body,
                created_at=self._now_iso()
            )

    # Session operations
    def create_session(self, session_id: str, user_id: str, expires_at: str) -> Session:
        with self._lock:
            csrf_token = secrets.token_urlsafe(32)
            session = Session(
                id=session_id,
                user_id=user_id,
                csrf_token=csrf_token,
                expires_at=expires_at,
                created_at=self._now_iso()
            )
            self.sessions[session_id] = session
            return session

    def get_session(self, session_id: str) -> Optional[Session]:
        with self._lock:
            session = self.sessions.get(session_id)
            if session:
                # Check if session is expired
                try:
                    expires = datetime.fromisoformat(session.expires_at.replace("Z", "+00:00"))
                    if expires <= datetime.now(timezone.utc):
                        del self.sessions[session_id]
                        return None
                except ValueError:
                    pass
            return session

    def delete_session(self, session_id: str) -> None:
        with self._lock:
            self.sessions.pop(session_id, None)

    def get_session_cookie(self, request: Request) -> Optional[Session]:
        """Get session from request cookies."""
        session_id = request.cookies.get("session_id")
        if session_id:
            return self.get_session(session_id)
        return None

    # Fixture operations
    def reset(self, fixture: Fixture) -> None:
        with self._lock:
            self.users.clear()
            self.users_by_handle.clear()
            self.users_by_email.clear()
            self.payments.clear()
            self.payments_by_user.clear()
            self.requests.clear()
            self.requests_by_user.clear()
            self.authorizations.clear()
            self.authorizations_by_user.clear()
            self.idempotency_keys.clear()
            self.sessions.clear()
            self.splits.clear()
            self.settlements.clear()
            self._id_counter = 0

            self.currency = fixture.currency
            self.minor_units = fixture.minor_units
            self.settlement_operator_ids = fixture.settlement_operator_ids or []
            self.authorization_ttl_seconds = fixture.authorization_ttl_seconds

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
                self.authorizations_by_user[user.id] = []

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
                authorization = Authorization(
                    id=fa.id,
                    from_user_id=fa.from_user_id,
                    to_user_id=fa.to_user_id,
                    amount=fa.amount,
                    captured_amount=fa.captured_amount,
                    note=fa.note,
                    visibility=fa.visibility,
                    status=fa.status,
                    expires_at=fa.expires_at,
                    payment_id=fa.payment_id,
                    payment_ids=fa.payment_ids,
                    remaining_amount=fa.remaining_amount,
                    created_at=fa.created_at
                )
                self.authorizations[authorization.id] = authorization
                self.authorizations_by_user.setdefault(fa.from_user_id, []).append(authorization.id)
                self.authorizations_by_user.setdefault(fa.to_user_id, []).append(authorization.id)

    def export_state(self) -> dict:
        with self._lock:
            return {
                "currency": self.currency,
                "minor_units": self.minor_units,
                "settlement_operator_ids": self.settlement_operator_ids,
                "authorization_ttl_seconds": self.authorization_ttl_seconds,
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
                        "payment_id": a.payment_id,
                        "payment_ids": a.payment_ids,
                        "remaining_amount": a.remaining_amount,
                        "created_at": a.created_at
                    } for aid, a in self.authorizations.items()
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
                "sessions": {
                    sid: {
                        "id": s.id,
                        "user_id": s.user_id,
                        "csrf_token": s.csrf_token,
                        "expires_at": s.expires_at,
                        "created_at": s.created_at
                    } for sid, s in self.sessions.items()
                },
                "splits": self.splits,
                "settlements": self.settlements,
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
            self.authorizations.clear()
            self.authorizations_by_user.clear()
            self.idempotency_keys.clear()
            self.splits.clear()
            self.settlements.clear()

            self.currency = state["currency"]
            self.minor_units = state["minor_units"]
            self.settlement_operator_ids = state["settlement_operator_ids"]
            self.authorization_ttl_seconds = state.get("authorization_ttl_seconds")
            self._id_counter = state.get("_id_counter", 0)

            for uid, udata in state["users"].items():
                user = User(**udata)
                self.users[uid] = user
                self.users_by_handle[user.handle] = uid
                self.users_by_email[user.email] = uid
                self.payments_by_user[uid] = []
                self.requests_by_user[uid] = []
                self.authorizations_by_user[uid] = []

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

            for aid, adata in state.get("authorizations", {}).items():
                authorization = Authorization(**adata)
                self.authorizations[aid] = authorization
                self.authorizations_by_user.setdefault(adata["from_user_id"], []).append(aid)
                self.authorizations_by_user.setdefault(adata["to_user_id"], []).append(aid)

            for k, vdata in state["idempotency_keys"].items():
                self.idempotency_keys[k] = IdempotencyRecord(**vdata)

            for sid, sdata in state.get("sessions", {}).items():
                self.sessions[sid] = Session(**sdata)

            self.splits = state.get("splits", {})
            self.settlements = state.get("settlements", {})

    def validate_fixture(self, fixture: Fixture) -> List[str]:
        errors = []
        # Check currency/minor_units
        if fixture.minor_units not in (0, 2, 3):
            errors.append("minor_units must be 0, 2, or 3")
        if not fixture.currency or len(fixture.currency) != 3:
            errors.append("currency must be 3-letter code")

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

        # Check seeded authorizations
        for a in fixture.authorizations:
            if a.from_user_id not in user_ids or a.to_user_id not in user_ids:
                errors.append(f"authorization {a.id} references unknown user")
            if a.amount <= 0 or a.amount > 1_000_000_000:
                errors.append(f"authorization {a.id} has invalid amount")
            if a.captured_amount < 0 or a.captured_amount > a.amount:
                errors.append(f"authorization {a.id} has invalid captured_amount")
            if a.remaining_amount < 0 or a.remaining_amount > a.amount:
                errors.append(f"authorization {a.id} has invalid remaining_amount")
            if a.captured_amount + a.remaining_amount != a.amount:
                errors.append(f"authorization {a.id} captured + remaining != amount")
            if a.visibility not in ("public", "private"):
                errors.append(f"authorization {a.id} has invalid visibility")
            if a.status not in ("open", "captured", "voided", "expired"):
                errors.append(f"authorization {a.id} has invalid status")

        # Check settlement operators
        for op_id in fixture.settlement_operator_ids:
            if op_id not in user_ids:
                errors.append(f"settlement operator {op_id} not found")

        return errors


storage = Storage()