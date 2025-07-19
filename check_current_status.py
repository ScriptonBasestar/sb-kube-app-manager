#!/usr/bin/env python3
"""Check current lint status"""

import os
import subprocess

os.chdir("/Users/archmagece/myopen/scripton/sb-kube-app-manager")

# First install types-requests
print("Installing types-requests...")
subprocess.run(["uv", "add", "--dev", "types-requests"], capture_output=True)

# Run make lint
print("\nRunning make lint...")
result = subprocess.run(["make", "lint"], capture_output=True, text=True)

print("Exit code:", result.returncode)
print("\nOutput:")
print(result.stdout)
if result.stderr:
    print("\nErrors:")
    print(result.stderr)
