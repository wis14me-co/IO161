from app.main import app
from fastapi.testclient import TestClient

client = TestClient(app)

# Test health
r = client.get('/health')
print('Health:', r.status_code, '-', r.json())

# Test frontend pages
pages = ['/signup', '/login', '/', '/index.html', '/authorizations', '/requests', '/split']
for page in pages:
    r = client.get(page)
    print(page, ':', r.status_code, '- len:', len(r.text))

# Test API endpoints
r = client.post('/api/v1/auth/signup', json={
    'email': 'test6@example.com',
    'password': 'password123',
    'display_name': 'Test User 6',
    'handle': 'testuser6'
})
print('Signup:', r.status_code)

r = client.post('/api/v1/auth/login', json={
    'email': 'test6@example.com',
    'password': 'password123'
})
print('Login:', r.status_code)
token = r.json().get('token')
headers = {'Authorization': 'Bearer ' + token}

r = client.get('/api/v1/auth/me', headers=headers)
print('Me:', r.status_code, '- balance:', r.json().get('balance'))

r = client.post('/api/v1/payments', json={
    'to_handle': 'testuser6',
    'amount': 1000,
    'note': 'test payment',
    'visibility': 'public'
}, headers={**headers, 'Idempotency-Key': 'test-key-3'})
print('Create payment:', r.status_code, '-', r.json())

r = client.get('/api/v1/authorizations', headers=headers)
print('Authorizations:', r.status_code, '-', r.json())

r = client.post('/api/v1/requests', json={
    'to_handle': 'testuser6',
    'amount': 500,
    'note': 'test request'
}, headers={**headers, 'Idempotency-Key': 'test-key-1'})
print('Create request:', r.status_code, '-', r.json())

r = client.get('/api/v1/requests', headers=headers)
print('List requests:', r.status_code, '-', r.json())

r = client.post('/api/v1/split', json={
    'amount': 3000,
    'participant_handles': ['testuser6'],
    'note': 'split test'
}, headers={**headers, 'Idempotency-Key': 'test-key-2'})
print('Create split:', r.status_code, '-', r.json())

r = client.get('/api/v1/settlements/operators')
print('Settlement operators:', r.status_code, '-', r.json())