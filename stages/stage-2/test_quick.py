import sys
import os
sys.path.insert(0, os.path.join(os.path.dirname(__file__)))

from fastapi.testclient import TestClient
from app.main import app

client = TestClient(app)

print("=" * 60)
print("TEST 1: HTML Content Negotiation (Accept: text/html)")
print("=" * 60)

# Test root endpoint with HTML accept header
response = client.get("/", headers={"Accept": "text/html"})
print(f"GET / with Accept: text/html: {response.status_code}")
if response.status_code == 200:
    content = response.text[:100]
    print(f"  Content preview: {content}")

# Test root endpoint with JSON accept header
response = client.get("/", headers={"Accept": "application/json"})
print(f"GET / with Accept: application/json: {response.status_code} - {response.json()}")

# Test signup with HTML accept header
response = client.post("/auth/signup", json={"email": "htmluser@example.com", "password": "password123", "display_name": "HTML User"})
print(f"POST /auth/signup with Accept: text/html: {response.status_code}")

# Test login with HTML accept header
response = client.post("/auth/login", json={"email": "htmluser@example.com", "password": "password123"})
print(f"POST /auth/login with Accept: text/html: {response.status_code}")

print()
print("=" * 60)
print("TEST 2: Session/Cookie Auth")
print("=" * 60)

# After login, we get a redirect with a session cookie
# Let's test the me endpoint without auth first
response = client.get("/me")
print(f"GET /me (no auth): {response.status_code} - {response.json() if response.status_code != 401 else '401 Unauthorized'}")

# Test with Bearer token
login_resp = client.post("/auth/login", json={"email": "htmluser@example.com", "password": "password123"})
token = login_resp.json().get("token")
print(f"Login token: {token[:20]}...")
response = client.get("/me", headers={"Authorization": f"Bearer {token}"})
print(f"GET /me (Bearer token): {response.status_code} - {response.json()['user_id']}")

# Test with session cookie - need to follow redirects
login_resp = client.post("/auth/login", json={"email": "htmluser@example.com", "password": "password123"}, follow_redirects=False)
print(f"Login redirect location: {login_resp.headers.get('location')}")

print()
print("=" * 60)
print("TEST 3: CSRF Protection")
print("=" * 60)

# Check if CSRF token is generated
response = client.get("/login")
print(f"GET /login: {response.status_code}")
if 'csrf_token' in response.text.lower() or 'csrf' in response.text.lower():
    print("  CSRF token found in login page")

# Test creating a payment with HTML form pattern
# First create user2
client.post("/auth/signup", json={"email": "user2@example.com", "password": "password123", "display_name": "User 2"})
# Login as user2
login_resp = client.post("/auth/login", json={"email": "user2@example.com", "password": "password123"}, follow_redirects=False)
print(f"Login status: {login_resp.status_code}")

# Now try to create a payment
# The test client doesn't support cookies the same way, let me check
response = client.post("/payments", json={"to_handle": "user1", "amount": 100, "note": "test", "visibility": "public"})
print(f"POST /payments: {response.status_code}")