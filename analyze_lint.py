#!/usr/bin/env python3
"""Analyze and fix lint errors"""

import os
import subprocess

os.chdir("/Users/archmagece/myopen/scripton/sb-kube-app-manager")


def run_command(cmd):
    """Run a command and return the result"""
    try:
        result = subprocess.run(cmd, shell=True, capture_output=True, text=True)
        return result.returncode, result.stdout, result.stderr
    except Exception as e:
        print(f"Error running command: {e}")
        return 1, "", str(e)


print("🔍 Running lint analysis...")
print("=" * 80)

# Run ruff check first
print("\n1. Running ruff check...")
exit_code, stdout, stderr = run_command(
    "uv run ruff check sbkube tests --diff --exclude migrations --exclude node_modules --exclude examples"
)

if exit_code != 0:
    print(f"Ruff found issues (exit code: {exit_code})")
    # Count errors
    error_lines = [line for line in stdout.split("\n") if line.strip()]
    print(f"Found {len(error_lines)} lines of diff output")

    # Save ruff output
    with open("ruff-errors.txt", "w") as f:
        f.write(stdout)
    print("Saved ruff errors to ruff-errors.txt")
else:
    print("✅ Ruff check passed!")

# Run mypy
print("\n2. Running mypy...")
exit_code, stdout, stderr = run_command(
    "uv run mypy sbkube --ignore-missing-imports --exclude migrations --exclude node_modules --exclude examples"
)

if exit_code != 0:
    print(f"MyPy found issues (exit code: {exit_code})")
    # Count errors
    error_count = stdout.count(": error:")
    print(f"Found {error_count} type errors")

    # Save mypy output
    with open("mypy-errors.txt", "w") as f:
        f.write(stdout)
    print("Saved mypy errors to mypy-errors.txt")
else:
    print("✅ MyPy check passed!")

# Run bandit
print("\n3. Running bandit...")
exit_code, stdout, stderr = run_command(
    "uv run bandit -r sbkube --skip B101,B404,B603,B607,B602 --severity-level medium --quiet --exclude '*/tests/*,*/scripts/*,*/debug/*,*/examples/*'"
)

if exit_code != 0:
    print(f"Bandit found security issues (exit code: {exit_code})")
    print("Output:", stdout[:500] + "..." if len(stdout) > 500 else stdout)
else:
    print("✅ Bandit security check passed!")

# Run mdformat check
print("\n4. Running mdformat check...")
exit_code, stdout, stderr = run_command(
    "uv run mdformat --check --diff *.md docs/**/*.md --wrap 120"
)

if exit_code != 0:
    print(f"Markdown formatting issues found (exit code: {exit_code})")
    print("Files needing formatting:", stderr if stderr else stdout[:200])
else:
    print("✅ Markdown format check passed!")

print("\n" + "=" * 80)
print("📊 Summary:")
print("Run 'make lint-fix' to automatically fix most issues")
print("For unsafe fixes, run 'make lint-fix UNSAFE_FIXES=1'")
