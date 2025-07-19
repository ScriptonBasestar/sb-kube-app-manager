#!/usr/bin/env python3
"""Simple script to check lint issues."""

import os
import subprocess


def run_command(cmd, description):
    """Run a command and return output."""
    print(f"\n=== {description} ===")
    print(f"Command: {cmd}")
    try:
        result = subprocess.run(
            cmd, shell=True, capture_output=True, text=True, cwd=os.getcwd()
        )
        print(f"Return code: {result.returncode}")
        if result.stdout:
            print("STDOUT:")
            print(result.stdout)
        if result.stderr:
            print("STDERR:")
            print(result.stderr)
        return result.returncode == 0
    except Exception as e:
        print(f"Error running command: {e}")
        return False


def main():
    """Run lint checks."""
    print("Current directory:", os.getcwd())

    # Check if uv is available
    if not run_command("which uv", "Check UV availability"):
        print("UV not found, trying python -m commands...")

    # Try the lint commands
    commands = [
        (
            "uv run ruff check sbkube tests --diff --exclude migrations --exclude node_modules --exclude examples",
            "Ruff check",
        ),
        (
            "uv run mypy sbkube --ignore-missing-imports --exclude migrations --exclude node_modules --exclude examples",
            "MyPy check",
        ),
        (
            "uv run bandit -r sbkube --skip B101,B404,B603,B607,B602 --severity-level medium --quiet --exclude '*/tests/*,*/scripts/*,*/debug/*,*/examples/*'",
            "Bandit security check",
        ),
    ]

    for cmd, desc in commands:
        success = run_command(cmd, desc)
        if not success:
            print(f"✗ {desc} failed")
        else:
            print(f"✓ {desc} passed")

    # Also try make lint
    run_command("make lint", "Make lint")


if __name__ == "__main__":
    main()
