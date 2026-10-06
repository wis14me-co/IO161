with open('D:\THE FACTORY\Project\dark-factory-result-skeleton\app\main.py', 'r') as f:
    content = f.read()

old = '@app.post("/splits", response_model=SplitResponse, status_code=201)\nasync def create_split(\n    split: SplitCreate,\n    user_id: str = Depends(get_current_user),\n    idempotency_key: str = Header(..., alias="Idempotency-Key"):\n)'
new = '@app.post("/splits", response_model=SplitResponse, status_code=201)\nasync def create_split(\n    split: SplitCreate,\n    user_id: str = Depends(get_current_user),\n    idempotency_key: str = Header(..., alias="Idempotency-Key"),\n    accept: str = Header(default="application/json")\n):\n    format_type = get_accept_format(accept)\n'

if old in content:
    content = content.replace(old, new)
    with open('D:\THE FACTORY\Project\dark-factory-result-skeleton\app\main.py', 'w') as f:
        f.write(content)
    print('Replacement 1 successful')
else:
    print('Replacement 1 failed - old string not found')
    # Try to find what's actually there
    idx = content.find('@app.post("/splits"')
    if idx >= 0:
        print('Found at index:', idx)
        print(content[idx:idx+200])