"""Simple test to verify the setup."""

import sys
import os

# Add the app directory to the path
sys.path.insert(0, os.path.join(os.path.dirname(__file__), "..", ".."))

print("Testing Pocketful Client Setup")
print("="*60)

# Test 1: Import the client
try:
    from src.client import PocketfulClient
    print("[OK] Successfully imported PocketfulClient")
except Exception as e:
    print(f"[FAIL] Failed to import PocketfulClient: {e}")
    sys.exit(1)

# Test 2: Create a client
try:
    client = PocketfulClient(base_url="http://localhost:8080")
    print("[OK] Successfully created PocketfulClient")
except Exception as e:
    print(f"[FAIL] Failed to create PocketfulClient: {e}")
    sys.exit(1)

# Test 3: Check health endpoint
try:
    import httpx
    response = httpx.get("http://localhost:8080/health", timeout=5)
    if response.status_code == 200:
        print("[OK] Health endpoint is working")
    else:
        print(f"[FAIL] Health endpoint returned status {response.status_code}")
except Exception as e:
    print(f"[FAIL] Health endpoint failed: {e}")
    sys.exit(1)

print("\n" + "="*60)
print("Setup verification completed successfully!")
