import httpx

print('=== FRONTEND PAGES ===')
headers = {'Accept': 'text/html'}
pages = ['/signup', '/login', '/', '/index.html', '/authorizations', '/requests', '/split']
for page in pages:
    r = httpx.get('http://127.0.0.1:8000' + page, headers=headers, timeout=10.0, follow_redirects=True)
    print(page, ':', r.status_code, '- len:', len(r.text))

print()
print('=== API ENDPOINTS ===')
r = httpx.post('http://127.0.0.1:8000/api/v1/auth/signup', json={
    'email': 'finaltest@example.com',
    'password': 'password123',
    'display_name': 'Final Test',
    'handle': 'finaltest'
})
print('Signup:', r.status_code)

r = httpx.post('http://127.0.0.1:8000/api/v1/auth/login', json={
    'email': 'finaltest@example.com',
    'password': 'password123'
})
print('Login:', r.status_code)
token = r.json().get('token')
headers = {'Authorization': 'Bearer ' + token}

r = httpx.get('http://127.0.0.1:8000/api/v1/auth/me', headers=headers)
print('Me:', r.status_code, '- balance:', r.json().get('balance'))

r = httpx.post('http://127.0.0.1:8000/api/v1/payments', json={
    'to_handle': 'finaltest',
    'amount': 1000,
    'note': 'test payment',
    'visibility': 'public'
}, headers={**headers, 'Idempotency-Key': 'test-payment-1'})
print('Payment:', r.status_code, '-', r.json())

r = httpx.get('http://127.0.0.1:8000/api/v1/authorizations', headers=headers)
print('Authorizations:', r.status_code, '-', r.json())

r = httpx.post('http://127.0.0.1:8000/api/v1/requests', json={
    'to_handle': 'finaltest',
    'amount': 500,
    'note': 'test request'
}, headers={**headers, 'Idempotency-Key': 'test-request-1'})
print('Create request:', r.status_code, '-', r.json())

r = httpx.get('http://127.0.0.1:8000/api/v1/requests', headers=headers)
print('List requests:', r.status_code, '-', r.json())

r = httpx.post('http://127.0.0.1:8000/api/v1/split', json={
    'amount': 3000,
    'participant_handles': ['finaltest'],
    'note': 'split test'
}, headers={**headers, 'Idempotency-Key': 'test-split-1'})
print('Create split:', r.status_code, '-', r.json())

r = httpx.get('http://127.0.0.1:8000/api/v1/settlements/operators')
print('Settlement operators:', r.status_code, '-', r.json())

r = httpx.get('http://127.0.0.1:8000/health')
print('Health:', r.status_code, '-', r.json())