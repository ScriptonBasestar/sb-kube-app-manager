#!/usr/bin/env python3
"""Check final lint status"""

import os
import re
import subprocess

os.chdir("/Users/archmagece/myopen/scripton/sb-kube-app-manager")

print("Running final lint check...")
print("=" * 80)

# Run make lint
result = subprocess.run(["make", "lint"], capture_output=True, text=True)

print(f"Exit code: {result.returncode}")
print("\nOutput:")
print(result.stdout)

if result.stderr:
    print("\nStderr:")
    print(result.stderr)

# Count errors
ruff_errors = result.stdout.count("error:")
mypy_errors = result.stdout.count("error:")

print("\n" + "=" * 80)
print("Summary:")
print(f"- Total errors found: {ruff_errors + mypy_errors}")
print(f"- Exit code: {result.returncode}")

if result.returncode == 0:
    print("\n✅ All lint checks passed! 0 errors.")
else:
    print("\n❌ Lint checks failed. There are still errors to fix.")

    # Extract error counts from output
    if "Found" in result.stdout:
        match = re.search(r"Found (\d+) error", result.stdout)
        if match:
            print(f"   Ruff found {match.group(1)} errors")

    if "error:" in result.stdout:
        error_lines = [line for line in result.stdout.split("\n") if "error:" in line]
        print(f"   MyPy found {len(error_lines)} errors")
