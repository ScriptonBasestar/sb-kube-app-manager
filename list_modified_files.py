#!/usr/bin/env python3
"""List all modified files"""

import subprocess
import os

os.chdir("/Users/archmagece/myopen/scripton/sb-kube-app-manager")

# Get git status
result = subprocess.run(
    ["git", "status", "--porcelain"],
    capture_output=True,
    text=True
)

if result.returncode != 0:
    print("Error running git status")
    exit(1)

# Parse the output
modified_files = []
for line in result.stdout.strip().split('\n'):
    if line.strip():
        # Status codes: M = modified, A = added, D = deleted, etc.
        status = line[:2]
        filename = line[3:]
        
        if 'M' in status:
            modified_files.append(filename)

print("Modified files:")
print("=" * 80)
for file in sorted(modified_files):
    print(f"  {file}")

print(f"\nTotal: {len(modified_files)} files modified")