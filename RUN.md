# Pocketful - Stage 1 Service

## Build

```bash
docker build -t pocketful .
```

## Run

```bash
docker run -p 8080:8080 -e PORT=8080 pocketful
```

The service will be available at `http://localhost:8080`

## Health Check

```bash
curl http://localhost:8080/health
```

Returns: `{"status":"ok"}`

## Test Endpoints

### Reset with Fixture

```bash
curl -X POST http://localhost:8080/_test/reset \
  -H "Content-Type: application/json" \
  -d '{
    "currency": "EUR",
    "minor_units": 2,
    "users": [
      {"id": "u_ada", "email": "ada@example.com", "password": "correct horse", "display_name": "Ada", "handle": "ada", "balance": 10000},
      {"id": "u_bob", "email": "bob@example.com", "password": "correct horse", "display_name": "Bob", "handle": "bob", "balance": 2500}
    ],
    "payments": [
      {"id": "p_1", "from_user_id": "u_ada", "to_user_id": "u_bob", "amount": 500, "note": "coffee", "visibility": "public"}
    ],
    "requests": [
      {"id": "rq_1", "requester_id": "u_bob", "payer_id": "u_ada", "amount": 1200, "note": "taxi", "status": "pending"}
    ]
  }'
```

Returns: `204 No Content`

### Export State

```bash
curl http://localhost:8080/_test/export
```

Returns: `{"track":"pocketful","format_version":1,"state":{...}}`

### Import State

```bash
curl -X POST http://localhost:8080/_test/import \
  -H "Content-Type: application/json" \
  -d '{"track":"pocketful","format_version":1,"state":{...}}'
```

Returns: `204 No Content`

## Fixture Format

The fixture JSON for `/_test/reset` must contain:

- `currency`: 3-letter currency code (e.g., "EUR", "JPY", "BHD")
- `minor_units`: 0, 2, or 3
- `users`: Array of user objects with:
  - `id`: unique user identifier
  - `email`: valid email format
  - `password`: at least 8 characters
  - `display_name`: 1-100 characters
  - `handle`: unique, matches `^[a-z0-9_]{1,20}$`
  - `balance`: non-negative integer (after seeded payments applied)
- `payments` (optional): Array of payment objects with:
  - `id`: unique payment identifier
  - `from_user_id`: must reference a user in fixture
  - `to_user_id`: must reference a user in fixture
  - `amount`: integer 1..1000000000
  - `note`: string, max 200 chars
  - `visibility`: "public" or "private"
- `requests` (optional): Array of request objects with:
  - `id`: unique request identifier
  - `requester_id`: must reference a user in fixture
  - `payer_id`: must reference a user in fixture
  - `amount`: integer 1..1000000000
  - `note`: string, max 200 chars
  - `status`: "pending", "paid", "declined", or "cancelled"
- `settlement_operator_ids` (optional): Array of user IDs who can execute settlements

## Idempotency

All write endpoints require `Idempotency-Key` header (1-255 chars):
- `POST /payments`
- `POST /requests`
- `POST /requests/{id}/pay`
- `POST /splits`
- `POST /settlements`

## Authentication

All endpoints except `/health`, `/_test/reset`, `/_test/export`, `/_test/import`, `/auth/signup`, `/auth/login` require `Authorization: Bearer <token>` header.

## Port

The service listens on `0.0.0.0` port from `PORT` environment variable (default 8080).