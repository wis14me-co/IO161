import httpx

# First signup to create the user
r = httpx.post('http://localhost:8080/auth/signup', json={'email':'test@example.com','password':'password123','display_name':'Test User'})
print("First signup:", r.status_code, r.json())

# Second signup with same email
r = httpx.post('http://localhost:8080/auth/signup', json={'email':'test@example.com','password':'password456','display_name':'Test User 2'})
print("Second signup status:", r.status_code)
print("Second signup headers:", dict(r.headers))
print("Second signup text:", r.text)
print("Second signup json:", r.json())