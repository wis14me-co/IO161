#!/usr/bin/env python3
"""
Verification script for frontend JavaScript implementation.
This script checks that all required functionality is implemented.
"""

import re

def check_js_file(filepath, required_patterns):
    """Check a JavaScript file for required patterns."""
    try:
        with open(filepath, 'r', encoding='utf-8') as f:
            content = f.read()

        missing = []
        for pattern_name, pattern in required_patterns.items():
            if not re.search(pattern, content, re.MULTILINE | re.DOTALL):
                missing.append(pattern_name)

        return missing
    except Exception as e:
        print(f"  [ERROR] Error reading {filepath}: {e}")
        return ["Error reading file"]

def main():
    print("Verifying Frontend Implementation\n")
    print("=" * 60)

    # Check api.js
    print("\n1. Checking app/static/js/api.js...")
    api_patterns = {
        "listAuthorizations method": r'async listAuthorizations\(direction, status, limit, offset\)',
        "captureAuthorization parameters": r'async captureAuthorization\(authId, amount, final, idempotencyKey\)',
    }
    api_missing = check_js_file("app/static/js/api.js", api_patterns)
    if api_missing:
        print(f"  [MISSING] Missing: {', '.join(api_missing)}")
    else:
        print("  [OK] All patterns found")

    # Check app.js
    print("\n2. Checking app/static/js/app.js...")
    app_patterns = {
        "loadAuthorizations method": r'async loadAuthorizations\(\)',
        "handleAuthorizationAction method": r'async handleAuthorizationAction\(action, authId, button\)',
        "getStatusClass method": r'getStatusClass\(status\)',
        "refreshWallet with latest-refresh-wins": r'refreshId.*Date\.now\(\)',
        'inFlightRefresh tracking': r'inFlightRefresh',
    }
    app_missing = check_js_file("app/static/js/app.js", app_patterns)
    if app_missing:
        print(f"  [MISSING] Missing: {', '.join(app_missing)}")
    else:
        print("  [OK] All patterns found")

    # Check index.html
    print("\n3. Checking app/templates/index.html...")
    index_patterns = {
        "wallet-refresh button": r'<button id="wallet-refresh"',
    }
    index_missing = check_js_file("app/templates/index.html", index_patterns)
    if index_missing:
        print(f"  [MISSING] Missing: {', '.join(index_missing)}")
    else:
        print("  [OK] All patterns found")

    # Check authorizations.html
    print("\n4. Checking app/templates/authorizations.html...")
    auth_patterns = {
        "authorization-list container": r'<div id="authorization-list"',
        "empty-authorizations element": r'empty-authorizations',
    }
    auth_missing = check_js_file("app/templates/authorizations.html", auth_patterns)
    if auth_missing:
        print(f"  [MISSING] Missing: {', '.join(auth_missing)}")
    else:
        print("  [OK] All patterns found")

    print("\n" + "=" * 60)
    print("Verification complete!")

if __name__ == "__main__":
    main()
