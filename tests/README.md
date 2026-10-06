# Pocketful API Tests

This directory contains the test suite for the Pocketful API, including unit tests, integration tests, and fixtures.

## Test Structure

```
tests/
├── conftest.py                 # Global test fixtures
├── run_tests.py                # Test runner script
├── unit/                       # Unit tests
│   ├── test_auth.py
│   ├── test_settlement.py
│   ├── test_authorization.py
│   └── test_storage.py
├── integration/                # Integration tests
│   └── test_integration.py
└── README.md                   # This file

stages/stage-2/tests/
├── conftest.py                 # Stage 2 test fixtures
├── unit/
│   └── test_client.py
└── integration/
    └── test_integration.py
```

## Running Tests

### Run all tests
```bash
python tests/run_tests.py
```

### Run with pytest directly
```bash
# Run all tests
pytest tests/ -v

# Run unit tests only
pytest tests/unit/ -v

# Run integration tests only
pytest tests/integration/ -v

# Run with coverage
pytest tests/ --cov=app --cov-report=html
```

### Run tests for a specific file
```bash
pytest tests/unit/test_auth.py -v
```

## Test Fixtures

The test fixtures in `conftest.py` provide common test data:

- `storage`: A fresh Storage instance
- `test_user`: A test user
- `authenticated_user`: A user with a valid token
- `another_user`: A second test user
- `payment`: A test payment
- `request_payment`: A test payment request
- `authorization`: A test authorization
- `split_data`: Test split data
- `settlement_transfers`: Test settlement transfers
- `websocket_manager`: Mock WebSocket manager
- `mock_websocket`: Mock WebSocket object

## Test Categories

### Unit Tests
Unit tests verify individual components in isolation:
- `test_auth.py`: Authentication service tests
- `test_settlement.py`: Settlement service tests
- `test_authorization.py`: Authorization service tests
- `test_storage.py`: Storage class tests

### Integration Tests
Integration tests verify the complete system flow:
- `test_integration.py`: End-to-end API tests

## Test Coverage

To generate a coverage report:
```bash
pytest tests/ --cov=app --cov-report=html --cov-report=term
```

Open `htmlcov/index.html` in a browser to view the detailed coverage report.

## Best Practices

1. Each test should be independent and not rely on other test execution order
2. Use fixtures for test data to avoid duplication
3. Test both success and error cases
4. Keep tests focused on a single behavior
5. Use descriptive test names that clearly state what is being tested
