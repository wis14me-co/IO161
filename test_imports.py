#!/usr/bin/env python
"""Test script to verify all imports work correctly."""
import sys
import os

# Add the app directory to the path
sys.path.insert(0, os.path.join(os.path.dirname(__file__), 'app'))

try:
    # Test WebSocket imports
    from app.websocket.manager import ConnectionManager
    print("[OK] WebSocket manager imported successfully")

    from app.websocket.routes import router as websocket_router
    print("[OK] WebSocket routes imported successfully")

    # Test storage with WebSocket
    from app.storage import Storage, storage
    print("[OK] Storage imported successfully")

    # Test all service imports
    from app.settlement.service import SettlementService
    print("[OK] Settlement service imported successfully")

    from app.settlement.schemas import SettlementCreate, SettlementTransferCreate
    print("[OK] Settlement schemas imported successfully")

    from app.authorization.service import AuthorizationService
    print("[OK] Authorization service imported successfully")

    from app.authorization.schemas import AuthorizationCreate, AuthorizationCapture
    print("[OK] Authorization schemas imported successfully")

    from app.auth.service import AuthService
    print("[OK] Auth service imported successfully")

    from app.auth.schemas import UserCreate, UserLogin
    print("[OK] Auth schemas imported successfully")

    # Test validation
    from app.validation import validate_amount, validate_handle, validate_note
    print("[OK] Validation functions imported successfully")

    # Test models
    from app.settlement.models import SettlementTransfer, SettlementPayment, Settlement
    print("[OK] Settlement models imported successfully")

    from app.authorization.models import Authorization
    print("[OK] Authorization models imported successfully")

    print("\n[OK] All imports verified successfully!")
    sys.exit(0)

except ImportError as e:
    print(f"\n[ERROR] Import error: {e}")
    import traceback
    traceback.print_exc()
    sys.exit(1)
except Exception as e:
    print(f"\n[ERROR] Error: {e}")
    import traceback
    traceback.print_exc()
    sys.exit(1)
