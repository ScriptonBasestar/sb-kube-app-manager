#!/usr/bin/env python3
"""Check git status and current lint state"""

import os
import subprocess

os.chdir("/Users/archmagece/myopen/scripton/sb-kube-app-manager")

# Check git status
print("📁 Current git status:")
result = subprocess.run(
    ["git", "status", "--porcelain"], capture_output=True, text=True
)
if result.returncode == 0:
    lines = result.stdout.strip().split("\n")
    modified_count = 0
    for line in lines[:30]:  # Show first 30 files
        if line.strip():
            print(line)
            if line.startswith(" M "):
                modified_count += 1
    if len(lines) > 30:
        print(f"... and {len(lines) - 30} more files")
    print(f"\nTotal modified files: {modified_count}")
else:
    print("Error checking git status")

# Quick lint check
print("\n🔍 Quick lint check:")
print("\n1. Ruff check:")
ruff_result = subprocess.run(
    ["uv", "run", "ruff", "check", "sbkube", "--statistics"],
    capture_output=True,
    text=True,
)
if ruff_result.returncode == 0:
    print("✅ Ruff: No issues found")
else:
    print("❌ Ruff: Found issues")
    if ruff_result.stdout:
        print(ruff_result.stdout[:300])

print("\n2. MyPy check:")
mypy_result = subprocess.run(
    ["uv", "run", "mypy", "sbkube", "--ignore-missing-imports"],
    capture_output=True,
    text=True,
)
if mypy_result.returncode == 0:
    print("✅ MyPy: No issues found")
else:
    error_count = mypy_result.stdout.count(": error:")
    print(f"❌ MyPy: Found {error_count} errors")
    # Note: Most modules have ignore_errors = true in mypy.ini
