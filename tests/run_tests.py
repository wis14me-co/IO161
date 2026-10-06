"""
Test runner for Pocketful API tests.
"""
import pytest
import sys
import os

def run_tests():
    """Run all tests."""
    # Add the app directory to the path
    sys.path.insert(0, os.path.join(os.path.dirname(__file__), 'app'))

    # Run pytest
    exit_code = pytest.main([
        __file__,
        "-v",
        "--tb=short",
        "tests/unit",
        "tests/integration",
        "stages/stage-2/tests/unit",
        "stages/stage-2/tests/integration",
        "stages/stage-2/tests/conftest.py"
    ])

    return exit_code

if __name__ == "__main__":
    exit_code = run_tests()
    sys.exit(exit_code)
