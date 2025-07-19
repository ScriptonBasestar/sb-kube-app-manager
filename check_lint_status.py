#!/usr/bin/env python3
"""Simple script to check lint status."""

import os
import subprocess
import sys


def run_command(cmd, description):
    """Run a command and return the result."""
    print(f"\n{'=' * 60}")
    print(f"Running: {description}")
    print(f"Command: {cmd}")
    print("=" * 60)

    try:
        result = subprocess.run(
            cmd, shell=True, capture_output=True, text=True, cwd=os.getcwd()
        )

        if result.stdout:
            print("STDOUT:")
            print(result.stdout)

        if result.stderr:
            print("STDERR:")
            print(result.stderr)

        print(f"Return code: {result.returncode}")
        return result.returncode == 0, result.stdout, result.stderr

    except Exception as e:
        print(f"Error running command: {e}")
        return False, "", str(e)


def main():
    """Main function to run all lint checks."""
    os.chdir("/Users/archmagece/myopen/scripton/sb-kube-app-manager")

    commands = [
        (
            "uv run ruff check sbkube tests --exclude migrations --exclude node_modules --exclude examples",
            "Ruff Check",
        ),
        (
            "uv run mypy sbkube --ignore-missing-imports --exclude migrations --exclude node_modules --exclude examples",
            "MyPy Type Check",
        ),
        (
            "uv run bandit -r sbkube --skip B101,B404,B603,B607,B602 --severity-level medium --quiet --exclude '*/tests/*,*/scripts/*,*/debug/*,*/examples/*'",
            "Bandit Security Check",
        ),
    ]

    all_passed = True

    for cmd, desc in commands:
        success, stdout, stderr = run_command(cmd, desc)
        if not success:
            all_passed = False

    print(f"\n{'=' * 60}")
    print("FINAL RESULT:")
    if all_passed:
        print("✅ All lint checks PASSED!")
    else:
        print("❌ Some lint checks FAILED!")
    print("=" * 60)

    return 0 if all_passed else 1


if __name__ == "__main__":
    sys.exit(main())
