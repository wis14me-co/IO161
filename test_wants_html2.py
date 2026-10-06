from app.deps import wants_html
from fastapi import Request

# Test various Accept headers
test_headers = [
    '*/*',
    'application/json',
    'text/html',
    'text/html, application/json',
    'application/json, text/html',
    '',  # no accept header
]

for accept in test_headers:
    req = Request(scope={'type': 'http', 'headers': [(b'accept', accept.encode()) if accept else (b'accept', b'')]})
    result = wants_html(req)
    print(f'wants_html(accept="{accept}"): {result}')

# Also test with TestClient-like headers
print("\n--- TestClient-like ---")
for accept in ['*/*', 'application/json', 'text/html']:
    req = Request(scope={'type': 'http', 'headers': [(b'accept', accept.encode())]})
    result = wants_html(req)
    print(f'wants_html(accept="{accept}"): {result}')