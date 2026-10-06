import httpx

# Test authorization endpoints
fixture = {
    "currency": "EUR",
    "minor_units": 2,
    "users": [
        {"id": "u_1", "email": "payer@example.com", "password": "password123", "display_name": "Payer", "handle": "payer", "balance": 10000},
        {"id": "u_2", "email": "receiver@example.com", "password": "password123", "display_name": "Receiver", "handle": "receiver", "balance": 0}
    ],
    "payments": [],
    "requests": [],
    "authorizations": [],
    "settlement_operator_ids": []
}

BASE = 'http://localhost:8080/api/v1'

r = httpx.post(f'{BASE}/_test/reset', json=fixture)
print("Reset:", r.status_code)

# Login as payer
r = httpx.post(f'{BASE}/auth/login', json={'email':'payer@example.com','password':'password123'})
print("Payer login:", r.status_code, r.json())
payer_token = r.json()['token']

# Login as receiver
r = httpx.post(f'{BASE}/auth/login', json={'email':'receiver@example.com','password':'password123'})
print("Receiver login:", r.status_code, r.json())
receiver_token = r.json()['token']

# Test create authorization
headers = {"Authorization": f"Bearer {payer_token}", "Idempotency-Key": "test-key-1"}
r = httpx.post(f'{BASE}/authorizations', json={
    'to_handle': 'receiver',
    'amount': 5000,
    'note': 'test auth',
    'visibility': 'public'
}, headers=headers)
print("Create auth:", r.status_code, r.json())
auth_id = r.json()['id']

# Test get authorizations
headers = {"Authorization": f"Bearer {payer_token}"}
r = httpx.get(f'{BASE}/authorizations', headers=headers)
print("List auths (payer):", r.status_code, r.json())

headers = {"Authorization": f"Bearer {receiver_token}"}
r = httpx.get(f'{BASE}/authorizations', headers=headers)
print("List auths (receiver):", r.status_code, r.json())

# Test capture authorization (by receiver)
headers = {"Authorization": f"Bearer {receiver_token}", "Idempotency-Key": "test-capture-1"}
r = httpx.post(f'{BASE}/authorizations/{auth_id}/capture', json={
    'amount': 3000,
    'final': False
}, headers=headers)
print("Capture auth:", r.status_code, r.json())

# Test get authorizations after partial capture
headers = {"Authorization": f"Bearer {payer_token}"}
r = httpx.get(f'{BASE}/authorizations', headers=headers)
print("List auths after capture (payer):", r.status_code, r.json())

# Test final capture
headers = {"Authorization": f"Bearer {receiver_token}", "Idempotency-Key": "test-capture-2"}
r = httpx.post(f'{BASE}/authorizations/{auth_id}/capture', json={
    'final': True
}, headers=headers)
print("Final capture:", r.status_code, r.json())

# Test void authorization (new auth)
headers = {"Authorization": f"Bearer {payer_token}", "Idempotency-Key": "test-key-2"}
r = httpx.post(f'{BASE}/authorizations', json={
    'to_handle': 'receiver',
    'amount': 2000,
    'note': 'test void',
    'visibility': 'public'
}, headers=headers)
print("Create auth for void:", r.status_code, r.json())
auth_id2 = r.json()['id']

# Void by payer
headers = {"Authorization": f"Bearer {payer_token}", "Idempotency-Key": "test-void-1"}
r = httpx.post(f'{BASE}/authorizations/{auth_id2}/void', headers=headers)
print("Void auth:", r.status_code, r.json())

# Test me endpoint shows held/available
headers = {"Authorization": f"Bearer {payer_token}"}
r = httpx.get(f'{BASE}/auth/me', headers=headers)
print("Me (payer):", r.status_code, r.json())

headers = {"Authorization": f"Bearer {receiver_token}"}
r = httpx.get(f'{BASE}/auth/me', headers=headers)
print("Me (receiver):", r.status_code, r.json())