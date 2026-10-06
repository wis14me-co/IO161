import httpx
import re

# Test signup with HTML - check for redirect and session cookie
client = httpx.Client(follow_redirects=False)
r = client.post('http://localhost:8080/auth/signup', 
    data={'email': 'test9@example.com', 'password': 'password123', 'display_name': 'Test User', 'csrf_token': 'test'},
    headers={'Accept': 'text/html', 'Content-Type': 'application/x-www-form-urlencoded'},
    follow_redirects=False
)
print('Signup HTML:', r.status_code)
print('Session cookie:', dict(r.cookies))
print('Location:', r.headers.get('location'))

# Debug - let's see the cookies in the client jar
print('Client cookies before requests:', dict(client.cookies))

# Test accessing protected page with session (using same client to preserve cookies)
r = client.get('http://localhost:8080/requests', headers={'Accept': 'text/html'})
print('Requests page:', r.status_code)
print('Client cookies after requests:', dict(client.cookies))
print('Request cookies sent:', r.request.headers.get('cookie'))

match = re.search(r'data-testid="error-message">(.*?)</div>', r.text)
if match:
    print('Error:', match.group(1))
else:
    print('Success - got requests page')
    # Check for content
    if 'Requests' in r.text:
        print('Page has Requests header')
    if 'New Request' in r.text:
        print('Page has New Request button')