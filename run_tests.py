#!/usr/bin/env python3
"""
Test runner script for Personal Assistant Bot

This script runs the test suite with proper configuration and
generates coverage reports.
"""

import subprocess
import sys
import os
from pathlib import Path


def run_command(command, description):
    """Run a command and handle errors"""
    print(f"\n{'='*60}")
    print(f"Running: {description}")
    print(f"Command: {command}")
    print(f"{'='*60}")
    
    result = subprocess.run(command, shell=True, capture_output=True, text=True)
    
    if result.stdout:
        print("STDOUT:")
        print(result.stdout)
    
    if result.stderr:
        print("STDERR:")
        print(result.stderr)
    
    if result.returncode != 0:
        print(f"❌ {description} failed with return code {result.returncode}")
        return False
    else:
        print(f"✅ {description} completed successfully")
        return True


def main():
    """Main test runner"""
    print("🧪 Personal Assistant Bot Test Suite")
    print("=" * 60)
    
    # Change to project directory
    project_root = Path(__file__).parent
    os.chdir(project_root)
    
    # Install dependencies if needed
    print("📦 Installing test dependencies...")
    install_cmd = "pip install -r requirements.txt"
    if not run_command(install_cmd, "Installing dependencies"):
        sys.exit(1)
    
    # Run code quality checks
    print("\n🔍 Running code quality checks...")
    
    # Black formatting check
    black_cmd = "black --check --diff ."
    run_command(black_cmd, "Black formatting check")
    
    # Ruff linting
    ruff_cmd = "ruff check ."
    run_command(ruff_cmd, "Ruff linting")
    
    # Detect secrets
    secrets_cmd = "detect-secrets scan --all-files --baseline .secrets.baseline"
    run_command(secrets_cmd, "Secret detection")
    
    # Run unit tests
    print("\n🧪 Running unit tests...")
    unit_cmd = "python -m pytest tests/unit/ -v --cov=. --cov-report=term-missing --cov-report=html:htmlcov/unit"
    if not run_command(unit_cmd, "Unit tests"):
        print("❌ Unit tests failed")
        sys.exit(1)
    
    # Run integration tests
    print("\n🔗 Running integration tests...")
    integration_cmd = "python -m pytest tests/integration/ -v --cov=. --cov-append --cov-report=term-missing --cov-report=html:htmlcov/integration"
    if not run_command(integration_cmd, "Integration tests"):
        print("❌ Integration tests failed")
        sys.exit(1)
    
    # Run all tests with coverage
    print("\n📊 Running full test suite with coverage...")
    full_cmd = "python -m pytest tests/ -v --cov=. --cov-report=term-missing --cov-report=html:htmlcov/full --cov-fail-under=80"
    if not run_command(full_cmd, "Full test suite"):
        print("❌ Full test suite failed or coverage below 80%")
        sys.exit(1)
    
    # Generate coverage report
    print("\n📈 Generating coverage report...")
    coverage_cmd = "coverage report --show-missing"
    run_command(coverage_cmd, "Coverage report")
    
    print("\n" + "=" * 60)
    print("🎉 All tests passed successfully!")
    print("📊 Coverage reports generated in htmlcov/ directory")
    print("=" * 60)


if __name__ == "__main__":
    main()