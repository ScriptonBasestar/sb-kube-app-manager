#!/usr/bin/env python3
"""Run make lint and capture output"""

import subprocess
import os
import sys

os.chdir("/Users/archmagece/myopen/scripton/sb-kube-app-manager")

print("Running make lint...")
result = subprocess.run(
    ["make", "lint"],
    capture_output=True,
    text=True
)

# Save output to file
with open("lint-output.txt", "w") as f:
    f.write(f"Exit code: {result.returncode}\n")
    f.write(f"\n=== STDOUT ===\n{result.stdout}")
    if result.stderr:
        f.write(f"\n=== STDERR ===\n{result.stderr}")

print(f"Exit code: {result.returncode}")
print("\nOutput saved to lint-output.txt")

# Parse errors
if result.stdout:
    lines = result.stdout.split('\n')
    error_count = sum(1 for line in lines if ': error:' in line)
    print(f"\nFound {error_count} errors")