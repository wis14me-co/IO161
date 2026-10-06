import httpx
from src.client import PocketfulClient, PocketfulError

# Test the client with debug
client = PocketfulClient(base_url="http://localhost:8080")

# Monkey-patch to add debug
original_request = client._request

def debug_request(method, path, idempotency_key=None, **kwargs):
    print(f"Request: {method} {path}")
    print(f"Headers: {client._headers(idempotency_key)}")
    print(f"Kwargs: {kwargs}")
    try:
        result = original_request(method, path, idempotency_key, **kwargs)
        print(f"Response: {result.status_code}")
        return result
    except Exception as e:
        print(f"Exception: {type(e)}: {e}")
        raise

client._request = debug_request

# First signup
try:
    auth = client.signup("test@example.com", "password123", "Test User")
    print("First signup:", auth)
except PocketfulError as e:
    print("First signup error:", e.code, e.message)

# Second signup with same email
try:
    auth = client.signup("test@example.com", "password456", "Test User 2")
    print("Second signup:", auth)
except PocketfulError as e:
    print("Second signup error:", e.code, e.message, e.status_code)
except Exception as e:
    print("Second signup exception:", type(e), e)