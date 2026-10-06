import httpx

BASE_URL = "http://localhost:8000"

# Test user registration
print("Testing user registration...")
response = httpx.post(f"{BASE_URL}/api/v1/auth/register", json={
    "email": "test@example.com",
    "password": "password123",
    "full_name": "Test User"
})
print(f"Register: {response.status_code} - {response.json()}")

# Test login
print("\nTesting login...")
response = httpx.post(f"{BASE_URL}/api/v1/auth/login", data={
    "username": "test@example.com",
    "password": "password123"
})
print(f"Login: {response.status_code} - {response.json()}")
token = response.json()["access_token"]

# Test protected route
print("\nTesting /me endpoint...")
headers = {"Authorization": f"Bearer {token}"}
response = httpx.get(f"{BASE_URL}/api/v1/auth/me", headers=headers)
print(f"Me: {response.status_code} - {response.json()}")

# Test duplicate registration
print("\nTesting duplicate registration...")
response = httpx.post(f"{BASE_URL}/api/v1/auth/register", json={
    "email": "test@example.com",
    "password": "password123",
    "full_name": "Test User 2"
})
print(f"Duplicate register: {response.status_code} - {response.json()}")

# Test wrong password
print("\nTesting wrong password...")
response = httpx.post(f"{BASE_URL}/api/v1/auth/login", data={
    "username": "test@example.com",
    "password": "wrongpassword"
})
print(f"Wrong password: {response.status_code} - {response.json()}")