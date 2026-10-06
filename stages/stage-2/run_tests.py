#!/usr/bin/env python3
"""Run integration tests for Stage 1 Pocketful API."""

import subprocess
import sys
import os


def run_command(cmd, description):
    """Run a command and report results."""
    print(f"\n{'='*60}")
    print(f"Running: {description}")
    print(f"Command: {' '.join(cmd)}")
    print('='*60)

    result = subprocess.run(cmd, capture_output=False, text=True)

    if result.returncode == 0:
        print(f"\n[OK] {description} PASSED")
        return True
    else:
        print(f"\n[FAIL] {description} FAILED")
        return False


def main():
    """Main test runner."""
    print("Pocketful Stage 1 Integration Test Runner")

    # Get the directory of this script
    script_dir = os.path.dirname(os.path.abspath(__file__))

    # If we're in the root directory, go to stages/stage-1
    if "stages" not in script_dir:
        os.chdir(os.path.join(script_dir, "stages", "stage-1"))
    else:
        os.chdir(script_dir)

    results = []

    # Check if pytest is installed
    try:
        subprocess.run([sys.executable, "-m", "pytest", "--version"], capture_output=True, check=True)
    except (subprocess.CalledProcessError, FileNotFoundError):
        print("\n[X] pytest is not installed")
        print("Please install test dependencies: pip install -r test_requirements.txt")
        return 1

    # Check if the service is running
    print("\nChecking if Pocketful service is running...")
    try:
        subprocess.run(
            ["curl", "-s", "http://localhost:8080/health"],
            capture_output=True,
            check=True,
            timeout=5
        )
        print("[OK] Pocketful service is running")
    except (subprocess.CalledProcessError, FileNotFoundError, subprocess.TimeoutExpired):
        print("[X] Pocketful service is not running")
        print("\nPlease start the service first:")
        print("  python -m app.main")
        return 1

    # Run all integration tests
    results.append(run_command(
        [sys.executable, "-m", "pytest", "tests/integration/", "-v", "--tb=short"],
        "All integration tests"
    ))

    # Run with coverage (optional)
    print("\n" + "="*60)
    print("Running tests with coverage report...")
    print("="*60)
    results.append(run_command(
        [sys.executable, "-m", "pytest", "tests/integration/", "--cov=app", "--cov-report=term-missing"],
        "Integration tests with coverage"
    ))

    # Summary
    print("\n" + "="*60)
    print("TEST SUMMARY")
    print("="*60)
    passed = sum(results)
    total = len(results)
    print(f"Passed: {passed}/{total}")

    if passed == total:
        print("\n[OK] All tests PASSED")
        return 0
    else:
        print(f"\n[X] {total - passed} test(s) FAILED")
        return 1


if __name__ == "__main__":
    sys.exit(main())
