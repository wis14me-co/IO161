from fastapi.testclient import TestClient
from app.main import app
import uuid

client = TestClient(app, follow_redirects=False)

print('=== COMPREHENSIVE STAGE 2 TEST ===')
print()

# 1. Reset with fixture
print('1. Testing /_test/reset with fixture...')
fixture = {
    'currency': 'EUR',
    'minor_units': 2,
    'users': [
        {'id': 'u_ada', 'email': 'ada@example.com', 'password': 'correct horse', 'display_name': 'Ada', 'handle': 'ada', 'balance': 10000},
        {'id': 'u_bob', 'email': 'bob@example.com', 'password': 'correct horse', 'display_name': 'Bob', 'handle': 'bob', 'balance': 2500}
    ],
    'payments': [
        {'id': 'p_1', 'from_user_id': 'u_ada', 'to_user_id': 'u_bob', 'amount': 500, 'note': 'coffee', 'visibility': 'public'}
    ],
    'requests': [
        {'id': 'rq_1', 'requester_id': 'u_bob', 'payer_id': 'u_ada', 'amount': 1200, 'note': 'taxi', 'status': 'pending'}
    ]
}
resp = client.post('/_test/reset', json=fixture)
assert resp.status_code == 204, f'Reset failed: {resp.status_code}'
print('   PASS')

# 2. Login
print('2. Testing login...')
resp = client.post('/api/v1/auth/login', json={'email': 'ada@example.com', 'password': 'correct horse'})
assert resp.status_code == 200, f'Login failed: {resp.status_code}'
token = resp.json().get('token')
headers = {'Authorization': f'Bearer {token}'}
print('   PASS')

# 3. HTML content negotiation
print('3. Testing HTML content negotiation...')
for path in ['/', '/signup', '/login', '/requests', '/split', '/authorizations']:
    resp = client.get(path, headers={**headers, 'Accept': 'text/html'})
    assert resp.status_code == 200, f'{path} HTML failed: {resp.status_code}'
    assert 'text/html' in resp.headers.get('content-type', ''), f'{path} not HTML'
print('   PASS')

# 4. JSON content negotiation
print('4. Testing JSON content negotiation...')
resp = client.get('/', headers={**headers, 'Accept': 'application/json'})
assert resp.status_code == 200, f'JSON failed: {resp.status_code}'
assert resp.json()['message'] == 'Welcome to Pocketful API'
print('   PASS')

# 5. Test auth pages redirect when unauthenticated
print('5. Testing auth redirect...')
client2 = TestClient(app, follow_redirects=False)
for path in ['/requests', '/split', '/authorizations']:
    resp = client2.get(path, headers={'Accept': 'text/html'})
    assert resp.status_code in [302, 307], f'{path} redirect failed: {resp.status_code}'
    assert '/login' in resp.headers.get('location', ''), f'{path} not redirecting to login'
print('   PASS')

# 6. Test payments API
print('6. Testing payments API...')
key = str(uuid.uuid4())
resp = client.post('/api/v1/payments', headers={**headers, 'Idempotency-Key': key}, json={'to_handle': 'bob', 'amount': 1000, 'note': 'lunch', 'visibility': 'public'})
assert resp.status_code == 201, f'Payment failed: {resp.status_code}'
payment_id = resp.json()['payment_id']
print('   PASS')

# 7. Test requests API
print('7. Testing requests API...')
resp = client.post('/api/v1/requests', headers={**headers, 'Idempotency-Key': str(uuid.uuid4())}, json={'payer_handle': 'bob', 'amount': 2000, 'note': 'rent'})
assert resp.status_code == 201, f'Request failed: {resp.status_code}'
print('   PASS')

# 8. Test splits API
print('8. Testing splits API...')
resp = client.post('/api/v1/splits', headers={**headers, 'Idempotency-Key': str(uuid.uuid4())}, json={'amount': 3000, 'participant_handles': ['bob'], 'note': 'dinner'})
assert resp.status_code == 201, f'Split failed: {resp.status_code}'
print('   PASS')

# 9. Test authorizations API
print('9. Testing authorizations API...')
resp = client.post('/api/v1/authorizations', headers={**headers, 'Idempotency-Key': str(uuid.uuid4())}, json={'to_handle': 'bob', 'amount': 2000, 'note': 'deposit', 'visibility': 'private'})
assert resp.status_code == 201, f'Auth failed: {resp.status_code}'
auth_id = resp.json()['id']

# Capture authorization
resp = client.post('/api/v1/auth/login', json={'email': 'bob@example.com', 'password': 'correct horse'})
bob_token = resp.json().get('token')
bob_headers = {'Authorization': f'Bearer {bob_token}'}
resp = client.post(f'/api/v1/authorizations/{auth_id}/capture', headers={**bob_headers, 'Idempotency-Key': str(uuid.uuid4())}, json={'amount': 1000, 'final': True})
assert resp.status_code == 201, f'Capture failed: {resp.status_code}'
print('   PASS')

# 10. Test export/import
print('10. Testing export/import...')
resp = client.get('/_test/export')
assert resp.status_code == 200
export_data = resp.json()
resp = client.post('/_test/import', json=export_data)
assert resp.status_code == 200
print('   PASS')

# 11. Test idempotency
print('11. Testing idempotency...')
key = str(uuid.uuid4())
resp1 = client.post('/api/v1/payments', headers={**headers, 'Idempotency-Key': key}, json={'to_handle': 'bob', 'amount': 500, 'note': 'test', 'visibility': 'public'})
resp2 = client.post('/api/v1/payments', headers={**headers, 'Idempotency-Key': key}, json={'to_handle': 'bob', 'amount': 500, 'note': 'test', 'visibility': 'public'})
assert resp1.status_code == 201
assert resp2.status_code == 201
assert resp1.json()['payment_id'] == resp2.json()['payment_id']
print('   PASS')

# 12. Test HTML page data-testid attributes
print('12. Testing HTML data-testid attributes...')
resp = client.get('/', headers={**headers, 'Accept': 'text/html'})
required_testids = ['wallet-balance', 'wallet-available', 'pay-handle', 'pay-amount', 'pay-submit', 'request-handle', 'request-amount', 'request-submit', 'activity-list', 'wallet-refresh']
for testid in required_testids:
    assert f'data-testid="{testid}"' in resp.text, f'Missing {testid} in /'
print('   PASS')

print()
print('=== ALL TESTS PASSED! ===')