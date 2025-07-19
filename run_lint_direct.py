#!/usr/bin/env python3
"""Direct execution of lint commands."""

import os
import subprocess
from pathlib import Path


def run_command(cmd, description, shell=True):
    """Run a command and capture output."""
    print(f"\n{'=' * 60}")
    print(f"Running: {description}")
    print(f"Command: {cmd}")
    print(f"{'=' * 60}")

    try:
        result = subprocess.run(
            cmd, shell=shell, capture_output=True, text=True, cwd=Path(__file__).parent
        )

        print(f"Exit code: {result.returncode}")

        if result.stdout:
            print(f"\nSTDOUT:\n{result.stdout}")

        if result.stderr:
            print(f"\nSTDERR:\n{result.stderr}")

        return result.returncode == 0, result.stdout, result.stderr

    except Exception as e:
        print(f"Error executing command: {e}")
        return False, "", str(e)


def main():
    """Main function to run lint checks."""
    print("Current working directory:", os.getcwd())

    # Define the lint commands from the Makefile
    commands = [
        (
            "uv run ruff check sbkube tests --diff --exclude migrations --exclude node_modules --exclude examples",
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

    results = []

    for cmd, desc in commands:
        success, stdout, stderr = run_command(cmd, desc)
        results.append((desc, success, stdout, stderr))

        if not success:
            print(f"❌ {desc} FAILED")
        else:
            print(f"✅ {desc} PASSED")

    print("\n" + "=" * 60)
    print("SUMMARY")
    print("=" * 60)

    for desc, success, stdout, stderr in results:
        status = "✅ PASSED" if success else "❌ FAILED"
        print(f"{desc}: {status}")

        if not success and stderr:
            print(f"  Error: {stderr}")

        if stdout and "error" in stdout.lower():
            print("  Issues found in output")


if __name__ == "__main__":
    main()
