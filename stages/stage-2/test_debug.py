import httpx

# Test the exact same flow as the client
url = "http://localhost:8080/auth/signup"
headers = {"Content-Type": "application/json"}
json_data = {"email": "test@example.com", "password": "password456", "display_name": "Test User 2"}

try:
    response = httpx.request("POST", url, headers=headers, timeout=5.0, json=json_data)
    response.raise_for_status()
    print("Success:", response.json())
except httpx.HTTPError as e:
    print("Caught HTTPError:", type(e))
    print("Has response:", hasattr(e, "response"))
    if hasattr(e, "response"):
        resp = e.response
        print("Response status:", resp.status_code)
        print("Response headers:", dict(resp.headers))
        print("Response text:", resp.text)
        try:
            error_data = resp.json()
            print("Response json:", error_data)
        except Exception as je:
            print("JSON decode error:", type(je), je)
    print("Exception str:", str(e))