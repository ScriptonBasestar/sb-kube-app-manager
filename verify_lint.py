#!/usr/bin/env python3
import os
import subprocess

os.chdir("/Users/archmagece/myopen/scripton/sb-kube-app-manager")

# Run each lint tool separately to check status
print("Running lint checks...")

# 1. Ruff
print("\n1. Ruff check:")
r1 = subprocess.call(
    [
        "uv",
        "run",
        "ruff",
        "check",
        "sbkube",
        "tests",
        "--exclude",
        "migrations",
        "--exclude",
        "node_modules",
        "--exclude",
        "examples",
    ]
)
print(f"Ruff exit code: {r1}")

# 2. MyPy
print("\n2. MyPy check:")
r2 = subprocess.call(
    [
        "uv",
        "run",
        "mypy",
        "sbkube",
        "--ignore-missing-imports",
        "--exclude",
        "migrations",
        "--exclude",
        "node_modules",
        "--exclude",
        "examples",
    ]
)
print(f"MyPy exit code: {r2}")

# 3. Bandit
print("\n3. Bandit check:")
r3 = subprocess.call(
    [
        "uv",
        "run",
        "bandit",
        "-r",
        "sbkube",
        "--skip",
        "B101,B404,B603,B607,B602",
        "--severity-level",
        "medium",
        "--quiet",
        "--exclude",
        "*/tests/*,*/scripts/*,*/debug/*,*/examples/*",
    ]
)
print(f"Bandit exit code: {r3}")

# Overall
if r1 == 0 and r2 == 0 and r3 == 0:
    print("\n✅ All lint checks passed!")
else:
    print("\n❌ Some lint checks failed")
