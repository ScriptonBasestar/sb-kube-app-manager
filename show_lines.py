#!/usr/bin/env python3
"""Show specific lines from a file"""

file_path = "/Users/archmagece/myopen/scripton/sb-kube-app-manager/sbkube/validators/pre_deployment_validators.py"

# Show lines around the error locations
with open(file_path) as f:
    lines = f.readlines()

print("Lines 175-190:")
for i in range(174, min(190, len(lines))):
    print(f"{i + 1:4d}: {lines[i]}", end="")
