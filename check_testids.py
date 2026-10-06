import re

with open('app/templates/signup.html', 'r') as f:
    signup = f.read()
    
with open('app/templates/login.html', 'r') as f:
    login = f.read()

print('=== signup.html data-testid attributes ===')
for pattern in ['signup-email', 'signup-password', 'signup-display-name', 'auth-error', 'current-user', 'current-handle', 'logout-button', 'signup-submit']:
    found = re.search(rf'data-testid="{pattern}"', signup)
    print(f'  {pattern}: {"found" if found else "missing"}')

print()
print('=== login.html data-testid attributes ===')
for pattern in ['login-email', 'login-password', 'login-submit', 'auth-error', 'current-user', 'current-handle', 'logout-button']:
    found = re.search(rf'data-testid="{pattern}"', login)
    print(f'  {pattern}: {"found" if found else "missing"}')