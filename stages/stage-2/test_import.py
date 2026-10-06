import sys
import os
sys.path.insert(0, os.path.join(os.path.dirname(__file__)))

from fastapi.testclient import TestClient
from app.main import app

print("=" * 60)
print("TEST: Stage 1 Import/Export Compatibility")
print("=" * 60)

# Create a test client
client = TestClient(app)

# Step 1: Signup a user
signup_resp = client.post("/auth/signup", json={"email": "importtest@example.com", "password": "password123", "display_name": "Import Test User"})
print(f"Signup: {signup_resp.status_code}")
assert signup_resp.status_code == 201, f"Signup failed: {signup_resp.status_code} - {signup_resp.json()}"
user_id = signup_resp.json()["user_id"]
token = signup_resp.json()["token"]
print(f"User ID: {user_id}")

# Step 2: Login
login_resp = client.post("/auth/login", json={"email": "importtest@example.com", "password": "password123"})
print(f"Login: {login_resp.status_code}")
assert login_resp.status_code == 200, f"Login failed: {login_resp.status_code} - {login_resp.json()}"
token = login_resp.json()["token"]
print(f"Token: {token[:20]}...")

# Step 3: Create a payment
payment_resp = client.post("/payments", json={"to_handle": "testuser", "amount": 100, "note": "test payment", "visibility": "public"}, headers={"Authorization": f"Bearer {token}"})
print(f"Create payment: {payment_resp.status_code}")
if payment_resp.status_code != 201:
    print(f"  Response: {payment_resp.status_code} - {payment_resp.json() if payment_resp.status_code < 500 else 'N/A'}")

# Step 4: Get current state (export)
export_resp = client.get("/_test/export", headers={"Authorization": f"Bearer {token}"})
print(f"Export state: {export_resp.status_code}")
if export_resp.status_code == 200:
    state = export_resp.json()
    print(f"  Currency: {state.get('currency')}")
    print(f"  Minor units: {state.get('minor_units')}")
    print(f"  Users count: {len(state.get('users', {}))}")
    print(f"  Payments count: {len(state.get('payments', {}))}")
    print(f"  Requests count: {len(state.get('requests', {}))}")
    print(f"  Authorizations count: {len(state.get('authorizations', {}))}")
else:
    print(f"  Export failed: {export_resp.status_code}")
    state = None

# Step 5: Reset and import the state
if state:
    client.post("/_test/reset", json={})  # Simple reset
    
    # Step 6: Import the state
    import_resp = client.post("/_test/import", json={
        "track": "pocketful",
        "format_version": 1,
        "state": state
    })
    print(f"Import state: {import_resp.status_code}")
    assert import_resp.status_code == 204, f"Import failed: {import_resp.status_code} - {import_resp.json()}"
    
    # Step 7: Verify state after import
    me_resp = client.get("/me", headers={"Authorization": f"Bearer {token}"})
    print(f"Me after import: {me_resp.status_code}")
    if me_resp.status_code == 200:
        me_data = me_resp.json()
        print(f"  Balance: {me_data.get('balance')}")
        print(f"  Available: {me_data.get('available')}")
        print(f"  Held: {me_data.get('held')}")

print()
print("=" * 60)
print("TEST COMPLETED")
print("=" * 60)