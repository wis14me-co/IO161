import httpx

# Test reset endpoint
fixture = {
    "currency": "EUR",
    "minor_units": 2,
    "users": [],
    "payments": [],
    "requests": [],
    "authorizations": [],
    "settlement_operator_ids": []
}

r = httpx.post('http://localhost:8080/_test/reset', json=fixture)
print("Reset:", r.status_code, r.text)

# Test signup
r = httpx.post('http://localhost:8080/auth/signup', json={'email':'test@example.com','password':'password123','display_name':'Test User'})
print("Signup:", r.status_code, r.json())

# Test duplicate
r = httpx.post('http://localhost:8080/auth/signup', json={'email':'test@example.com','password':'password456','display_name':'Test User 2'})
print("Duplicate:", r.status_code, r.json())