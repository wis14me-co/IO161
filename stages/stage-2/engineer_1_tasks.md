# Stage 2 Tasks - Engineer 1 (Backend Extensions)

## Task 1: Authorization Data Model & Storage
Add authorization entity: id, from_user, to_user, amount, captured_amount, note, visibility, status (open/captured/voided/expired), expires_at, created_at, payment_id, payment_ids[], remaining_amount. Extend fixture loading for authorizations array and authorization_ttl_seconds.

## Task 2: Authorization Endpoints
Implement POST /authorizations (idempotent, payer creates, checks available balance), POST /authorizations/{id}/capture (idempotent, receiver only, amount optional, final flag), POST /authorizations/{id}/void (payer only, no idempotency), GET /authorizations with direction/status pagination.

## Task 3: Balance Model Updates
Update GET /me to return balance=total, total, available, held. Held = sum of open authorization amounts. Available = total - held (never negative). All existing insufficient_funds checks now use available.

## Task 4: Capture Payment Creation
On capture, create payment with authorization_id link, request_id=null, note/visibility copied from authorization. Update authorization captured_amount, payment_id (latest), payment_ids[], remaining_amount. Final capture releases remainder to payer available.

## Task 5: Authorization Expiry Handling
Implement automatic expiry check: authorization with expires_at <= now is expired, holds no funds. GET /authorizations shows expired status. GET /me reflects released funds in available. No background job needed - check on read.

## Task 6: Stage 1 Export/Import Compatibility
Extend export/import to include authorizations, captured_amount, payment_ids, remaining_amount, expires_at. Import must restore open holds correctly. Stage 2 service accepts Stage 1 exports (authorizations optional/empty).

## Task 7: Idempotency for New Write Paths
Extend idempotency middleware to cover authorizations and captures (7 total write paths). Same replay rules: same key+body=200 with original response, different body=409.