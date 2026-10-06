import re

def check_file(filepath, patterns, label):
    with open(filepath, 'r') as f:
        content = f.read()
    print(f'=== {label} ===')
    for pattern in patterns:
        found = re.search(rf'data-testid="{pattern}"', content)
        print(f'  {pattern}: {"found" if found else "missing"}')
    print()

# Check signup.html
with open('app/templates/signup.html', 'r') as f:
    signup = f.read()

check_file('app/templates/signup.html', [
    'signup-email', 'signup-password', 'signup-display-name', 
    'auth-error', 'current-user', 'current-handle', 
    'logout-button', 'signup-submit'
], 'signup.html')

# Check login.html
check_file('app/templates/login.html', [
    'login-email', 'login-password', 'login-submit', 
    'auth-error', 'current-user', 'current-handle', 
    'logout-button'
], 'login.html')

# Check index.html
check_file('app/templates/index.html', [
    'wallet-balance', 'wallet-available', 'wallet-held',
    'pay-handle', 'pay-amount', 'pay-note', 'pay-visibility', 'pay-submit', 'pay-error', 'pay-uncertain',
    'request-handle', 'request-amount', 'request-note', 'request-submit', 'request-error',
    'activity-list', 'empty-activity',
    'wallet-refresh'
], 'index.html')

# Check requests.html
check_file('app/templates/requests.html', [
    'incoming-list', 'outgoing-list', 'empty-requests'
], 'requests.html')

# Check split.html
check_file('app/templates/split.html', [
    'split-amount', 'split-handles', 'split-note', 'split-submit',
    'split-preview', 'split-error', 'empty-splits'
], 'split.html')

# Check authorizations.html
check_file('app/templates/authorizations.html', [
    'authorize-handle', 'authorize-amount', 'authorize-note', 'authorize-visibility', 'authorize-submit',
    'authorize-error', 'authorization-list', 'empty-authorizations'
], 'authorizations.html')

print("=== Dynamic elements (rendered by JavaScript) ===")
print("These are checked in the browser after rendering:")
print("  Authorization items: authorization-item-{id}, authorization-amount-{id},")
print("    authorization-captured-{id}, authorization-expires-{id},")
print("    authorization-capture-amount-{id}, authorization-capture-{id},")
print("    authorization-void-{id}, authorization-error-{id}")
print("  Activity items: activity-item-{id}, activity-parties-{id},")
print("    activity-amount-{id}, activity-note-{id}")
print("  Request items: request-item-{id}, request-amount-{id},")
print("    request-pay-{id}, request-decline-{id}, request-cancel-{id},")
print("    request-error-{id}")
print("  Split shares: split-share-{handle}")