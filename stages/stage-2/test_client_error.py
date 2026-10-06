import httpx
from src.client import PocketfulClient, PocketfulError

# Test the client directly
client = PocketfulClient(base_url="http://localhost:8080")

# First signup to create the user
try:
    auth = client.signup("test@example.com", "password123", "Test User")
    print("First signup:", auth)
except PocketfulError as e:
    print("First signup error:", e.code, e.message)

# Second signup with same email - should fail with email_taken
try:
    auth = client.signup("test@example.com", "password456", "Test User 2")
    print("Second signup:", auth)
except PocketfulError as e:
    print("Second signup error:", e.code, e.message, e.status_code)
except Exception as e:
    print("Second signup exception:", type(e), e)