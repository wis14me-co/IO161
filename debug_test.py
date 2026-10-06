import httpx

headers = {'Accept': 'text/html'}
for page in ['/authorizations', '/requests', '/split']:
    r = httpx.get('http://127.0.0.1:8000' + page, headers=headers, timeout=10.0, follow_redirects=False)
    print(page, ':', r.status_code)
    print('  text:', r.text[:200])
    print('  headers:', dict(r.headers))
    print()