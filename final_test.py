import httpx

print('=== FRONTEND PAGES ===')
headers = {'Accept': 'text/html'}
pages = ['/signup', '/login', '/', '/index.html', '/authorizations', '/requests', '/split']
for page in pages:
    r = httpx.get('http://127.0.0.1:8000' + page, headers=headers, timeout=10.0, follow_redirects=True)
    print(page, ':', r.status_code, '- len:', len(r.text))

print()
print('=== API ENDPOINTS ===')
api_headers = {'Accept': 'application/json'}

# Reset with fixture containing users with balances
fixture = {
    "currency": "EUR",
    "minor_units": 2,
    "users": [
        {"id": "u_ada", "email": "ada@example.com", "password": "correct horse", "display_name": "Ada", "handle": "ada", "balance": 10000},
        {"id": "u_bob", "email": "bob@example.com", "password": "correct horse", "display_name": "Bob", "handle": "bob", "balance": 2500},
        {"id": "u_cy", "email": "cy@example.com", "password": "correct horse", "display_name": "Cy", "handle": "cy", "balance": 500}
    ],
    "payments": [],
    "requests": [],
    "authorizations": [],
    "settlement_operator_ids": []
}
r = httpx.post('http://127.0.0.1:8000/_test/reset', json=fixture, headers=api_headers)
print('Reset state:', r.status_code)

# Login as Ada
r = httpx.post('http://127.0.0.1:8000/auth/login', json={
    'email': 'ada@example.com',
    'password': 'correct horse'
}, headers=api_headers)
print('Login Ada:', r.status_code)
token_ada = r.json().get('token')
headers_ada = {'Authorization': 'Bearer ' + token_ada, 'Accept': 'application/json'}

# Login as Bob
r = httpx.post('http://127.0.0.1:8000/auth/login', json={
    'email': 'bob@example.com',
    'password': 'correct horse'
}, headers=api_headers)
print('Login Bob:', r.status_code)
token_bob = r.json().get('token')
headers_bob = {'Authorization': 'Bearer ' + token_bob, 'Accept': 'application/json'}

# Login as Cy
r = httpx.post('http://127.0.0.1:8000/auth/login', json={
    'email': 'cy@example.com',
    'password': 'correct horse'
}, headers=api_headers)
print('Login Cy:', r.status_code)
token_cy = r.json().get('token')
headers_cy = {'Authorization': 'Bearer ' + token_cy, 'Accept': 'application/json'}

r = httpx.get('http://127.0.0.1:8000/auth/me', headers=headers_ada)
print('Me Ada:', r.status_code, '- balance:', r.json().get('balance'))

r = httpx.get('http://127.0.0.1:8000/auth/me', headers=headers_bob)
print('Me Bob:', r.status_code, '- balance:', r.json().get('balance'))

r = httpx.get('http://127.0.0.1:8000/auth/me', headers=headers_cy)
print('Me Cy:', r.status_code, '- balance:', r.json().get('balance'))

# Ada pays Bob
r = httpx.post('http://127.0.0.1:8000/payments', json={
    'to_handle': 'bob',
    'amount': 1000,
    'note': 'test payment',
    'visibility': 'public'
}, headers={**headers_ada, 'Idempotency-Key': 'test-payment-1'})
print('Payment Ada->Bob:', r.status_code, '-', r.json())

# Check balances after payment
r = httpx.get('http://127.0.0.1:8000/auth/me', headers=headers_ada)
print('Me Ada after payment:', r.status_code, '- balance:', r.json().get('balance'))

r = httpx.get('http://127.0.0.1:8000/auth/me', headers=headers_bob)
print('Me Bob after payment:', r.status_code, '- balance:', r.json().get('balance'))

r = httpx.get('http://127.0.0.1:8000/authorizations', headers=headers_ada)
print('Authorizations:', r.status_code, '-', r.json())

# Bob requests from Ada
r = httpx.post('http://127.0.0.1:8000/requests', json={
    'to_handle': 'ada',
    'amount': 500,
    'note': 'test request'
}, headers={**headers_bob, 'Idempotency-Key': 'test-request-1'})
print('Create request Bob->Ada:', r.status_code, '-', r.json())

request_id = r.json().get('request_id')

r = httpx.get('http://127.0.0.1:8000/requests', headers=headers_ada)
print('List requests Ada:', r.status_code, '-', r.json())

r = httpx.get('http://127.0.0.1:8000/requests', headers=headers_bob)
print('List requests Bob:', r.status_code, '-', r.json())

# Ada pays the request
r = httpx.post(f'http://127.0.0.1:8000/requests/{request_id}/pay', json={
    'visibility': 'public'
}, headers={**headers_ada, 'Idempotency-Key': 'test-payment-2'})
print('Ada pays request:', r.status_code, '-', r.json())

# Check balances after paying request
r = httpx.get('http://127.0.0.1:8000/auth/me', headers=headers_ada)
print('Me Ada after paying request:', r.status_code, '- balance:', r.json().get('balance'))

r = httpx.get('http://127.0.0.1:8000/auth/me', headers=headers_bob)
print('Me Bob after paying request:', r.status_code, '- balance:', r.json().get('balance'))

# Create split
r = httpx.post('http://127.0.0.1:8000/splits', json={
    'amount': 3000,
    'participant_handles': ['ada', 'bob', 'cy'],
    'note': 'split test'
}, headers={**headers_ada, 'Idempotency-Key': 'test-split-1'})
print('Create split:', r.status_code, '-', r.json())

r = httpx.get('http://127.0.0.1:8000/settlements/operators', headers=headers_ada)
print('Settlement operators:', r.status_code, '-', r.json())

r = httpx.get('http://127.0.0.1:8000/health')
print('Health:', r.status_code, '-', r.json())