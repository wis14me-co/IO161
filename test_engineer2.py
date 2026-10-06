from app.main import app
from fastapi.testclient import TestClient
from app.storage import storage
client = TestClient(app, follow_redirects=False)

# Create test user
try:
    storage.create_user(
        email="test@example.com",
        password="password123",
        display_name="Test User",
        handle="testuser"
    )
except Exception:
    pass  # User might already exist

# Test HTML content negotiation
print('=== HTML Content Negotiation ===')
r = client.get('/', headers={'Accept': 'text/html'})
print(f'GET / with Accept: text/html: {r.status_code}')
if r.status_code == 200:
    print('  HTML returned')

r = client.get('/', headers={'Accept': 'application/json'})
print(f'GET / with Accept: application/json: {r.status_code} - {r.json()}')

print()
print('=== Session/Cookie Auth ===')
# Login via API (JSON) - no CSRF needed for API clients
r = client.post('/api/v1/auth/login', json={'email': 'test@example.com', 'password': 'password123'})
print(f'Login (API): {r.status_code}')
if r.status_code == 200:
    print(f'  Token: {r.json().get("token", "")[:20]}...')

# Login via form (browser) - needs CSRF
print()
print('=== CSRF Protection for Login Form ===')
# First get the login page to get CSRF cookie
r = client.get('/login', headers={'Accept': 'text/html'})
csrf_cookie = client.cookies.get('pocketful_csrf')
print(f'GET /login: {r.status_code}, CSRF cookie: {csrf_cookie[:20] if csrf_cookie else "none"}')

# Now post login form with CSRF token
if csrf_cookie:
    r = client.post('/api/v1/auth/login', data={'email': 'test@example.com', 'password': 'password123', 'csrf_token': csrf_cookie})
    print(f'Login (form with CSRF): {r.status_code}')
    if r.status_code == 303:
        print(f'  Redirect location: {r.headers.get("location")}')
        set_cookie = r.headers.get('set-cookie', '')
        print(f'  Set-Cookie: {set_cookie[:100] if set_cookie else "none"}')

# Test login form without CSRF - should fail
print()
print('=== CSRF Protection - Missing Token ===')
# Reset client
client2 = TestClient(app, follow_redirects=False)
r = client2.get('/login', headers={'Accept': 'text/html'})
csrf_cookie = client2.cookies.get('pocketful_csrf')
if csrf_cookie:
    r = client2.post('/api/v1/auth/login', data={'email': 'test@example.com', 'password': 'password123'})
    print(f'Login (form without CSRF): {r.status_code}')
    print(f'  Response: {r.json()}')

# Test me without auth
r = client.get('/me')
print(f'GET /me (no auth): {r.status_code}')

print()
print('=== CSRF Protection ===')
r = client.get('/login', headers={'Accept': 'text/html'})
print(f'GET /login: {r.status_code}')
csrf_found = 'csrf_token' in r.text.lower() or 'csrf' in r.text.lower()
print(f'  CSRF token found: {csrf_found}')