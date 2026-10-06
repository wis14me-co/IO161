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
# Login
r = client.post('/auth/login', json={'email': 'test@example.com', 'password': 'password123'})
print(f'Login: {r.status_code}')
if r.status_code == 303:
    print(f'  Redirect location: {r.headers.get("location")}')
    # Check for set-cookie
    set_cookie = r.headers.get('set-cookie', '')
    print(f'  Set-Cookie: {set_cookie[:100] if set_cookie else "none"}')

# Test me without auth
r = client.get('/me')
print(f'GET /me (no auth): {r.status_code}')

print()
print('=== CSRF Protection ===')
r = client.get('/login', headers={'Accept': 'text/html'})
print(f'GET /login: {r.status_code}')
csrf_found = 'csrf_token' in r.text.lower() or 'csrf' in r.text.lower()
print(f'  CSRF token found: {csrf_found}')