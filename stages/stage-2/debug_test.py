import httpx

# Test creating request and paying it
client1 = httpx.Client()
client2 = httpx.Client()

# Reset fixture with user1 having balance
fixture = {
    "currency": "EUR",
    "minor_units": 2,
    "users": [
        {
            "id": "u_1",
            "email": "user1@example.com",
            "password": "password123",
            "display_name": "User 1",
            "handle": "user1",
            "balance": 10000
        },
        {
            "id": "u_2",
            "email": "user2@example.com",
            "password": "password123",
            "display_name": "User 2",
            "handle": "user2",
            "balance": 0
        }
    ],
    "payments": [],
    "requests": [],
    "authorizations": [],
    "settlement_operator_ids": []
}
r = client1.post('http://localhost:8080/_test/reset', json=fixture)
print('Reset fixture:', r.status_code)

# Login user1
r = client1.post('http://localhost:8080/auth/login', 
    json={'email': 'user1@example.com', 'password': 'password123'})
print('Login user1:', r.status_code, r.json())
client1.headers['Authorization'] = f"Bearer {r.json()['token']}"

# Login user2
r = client2.post('http://localhost:8080/auth/login', 
    json={'email': 'user2@example.com', 'password': 'password123'})
print('Login user2:', r.status_code, r.json())
client2.headers['Authorization'] = f"Bearer {r.json()['token']}"

# User2 creates request
r = client2.post('http://localhost:8080/requests', 
    json={'payer_handle': 'user1', 'amount': 500, 'note': 'test request'},
    headers={'Idempotency-Key': 'key1'})
print('Create request:', r.status_code, r.json())
request_id = r.json()['request_id']

# User1 pays request
r = client1.post(f'http://localhost:8080/requests/{request_id}/pay', 
    json={'visibility': 'public'},
    headers={'Idempotency-Key': 'key2'})
print('Pay request:', r.status_code, r.json())