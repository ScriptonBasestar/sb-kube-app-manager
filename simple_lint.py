import os
import sys
import subprocess

os.chdir("/Users/archmagece/myopen/scripton/sb-kube-app-manager")

# Test if uv is available
try:
    result = subprocess.run(["uv", "--version"], capture_output=True, text=True)
    print(f"UV version: {result.stdout.strip()}")
except Exception as e:
    print(f"UV not available: {e}")

# Test ruff
try:
    result = subprocess.run(["uv", "run", "ruff", "--version"], capture_output=True, text=True)
    print(f"Ruff version: {result.stdout.strip()}")
except Exception as e:
    print(f"Ruff not available: {e}")

# Test simple ruff check
try:
    result = subprocess.run(["uv", "run", "ruff", "check", "sbkube", "--diff"], capture_output=True, text=True)
    print(f"Ruff check exit code: {result.returncode}")
    print(f"Ruff stdout: {result.stdout}")
    print(f"Ruff stderr: {result.stderr}")
except Exception as e:
    print(f"Ruff check failed: {e}")