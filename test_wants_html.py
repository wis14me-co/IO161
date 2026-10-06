from app.deps import wants_html

class MockHeaders:
    def __init__(self, accept):
        self.accept = accept
    def get(self, key, default=''):
        if key.lower() == 'accept':
            return self.accept
        return default

class MockRequest:
    def __init__(self, accept):
        self.headers = MockHeaders(accept)

test_headers = [
    'application/json',
    'application/json; charset=utf-8',
    'text/html',
    'text/html, application/json',
    'application/json, text/html',
    '',  # no accept header
    '*/*',
]

for accept in test_headers:
    req = MockRequest(accept)
    result = wants_html(req)
    print(f'wants_html(accept="{accept}"): {result}')