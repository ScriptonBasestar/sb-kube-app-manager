#!/usr/bin/env python3
"""Simulate make lint by running the commands directly"""

import subprocess
import os

os.chdir("/Users/archmagece/myopen/scripton/sb-kube-app-manager")

print("Simulating make lint...")
print("=" * 80)

# Run ruff check
print("\n1. Running ruff check...")
ruff_result = subprocess.run(
    ["uv", "run", "ruff", "check", "sbkube", "tests", "--diff", 
     "--exclude", "migrations", "--exclude", "node_modules", "--exclude", "examples"],
    capture_output=True,
    text=True
)
print(f"Ruff exit code: {ruff_result.returncode}")
if ruff_result.stdout:
    print("Ruff output (first 500 chars):")
    print(ruff_result.stdout[:500])
    if len(ruff_result.stdout) > 500:
        print("... (truncated)")

# Run mypy
print("\n\n2. Running mypy...")
mypy_result = subprocess.run(
    ["uv", "run", "mypy", "sbkube", "--ignore-missing-imports",
     "--exclude", "migrations", "--exclude", "node_modules", "--exclude", "examples"],
    capture_output=True,
    text=True
)
print(f"MyPy exit code: {mypy_result.returncode}")
if mypy_result.stdout:
    print("MyPy output (first 1000 chars):")
    print(mypy_result.stdout[:1000])
    if len(mypy_result.stdout) > 1000:
        print("... (truncated)")

# Run bandit
print("\n\n3. Running bandit...")
bandit_result = subprocess.run(
    ["uv", "run", "bandit", "-r", "sbkube", 
     "--skip", "B101,B404,B603,B607,B602", 
     "--severity-level", "medium", "--quiet",
     "--exclude", "*/tests/*,*/scripts/*,*/debug/*,*/examples/*"],
    capture_output=True,
    text=True
)
print(f"Bandit exit code: {bandit_result.returncode}")
if bandit_result.stdout:
    print("Bandit output:")
    print(bandit_result.stdout)

# Summary
print("\n" + "=" * 80)
print("Summary:")
print(f"- Ruff: {'PASS' if ruff_result.returncode == 0 else 'FAIL'}")
print(f"- MyPy: {'PASS' if mypy_result.returncode == 0 else 'FAIL'}")
print(f"- Bandit: {'PASS' if bandit_result.returncode == 0 else 'FAIL'}")

overall_pass = all(r.returncode == 0 for r in [ruff_result, mypy_result, bandit_result])
print(f"\nOverall: {'✅ PASS - 0 errors' if overall_pass else '❌ FAIL - errors found'}")