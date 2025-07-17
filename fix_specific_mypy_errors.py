#!/usr/bin/env python3
"""Fix specific MyPy errors in pre_deployment_validators.py"""

import re

file_path = "/Users/archmagece/myopen/scripton/sb-kube-app-manager/sbkube/validators/pre_deployment_validators.py"

# Read the file
with open(file_path, 'r') as f:
    lines = f.readlines()

# Print lines around the error locations to understand context
print("Analyzing error locations...")
print("\nLines 175-185 (error on 181, 183):")
for i in range(174, min(185, len(lines))):
    print(f"{i+1:4d}: {lines[i]}", end="")

print("\n\nLines 250-260 (error on 256):")
for i in range(249, min(260, len(lines))):
    print(f"{i+1:4d}: {lines[i]}", end="")

print("\n\nLines 320-335 (errors on 327, 331, 332):")
for i in range(319, min(335, len(lines))):
    print(f"{i+1:4d}: {lines[i]}", end="")

print("\n\nLines 350-360 (error on 355):")
for i in range(349, min(360, len(lines))):
    print(f"{i+1:4d}: {lines[i]}", end="")

print("\n\nLines 395-405 (errors on 398, 400, 401, 404):")
for i in range(394, min(405, len(lines))):
    print(f"{i+1:4d}: {lines[i]}", end="")

# Now let's identify the actual problems
print("\n\n" + "="*80)
print("Identified issues:")
print("\n1. Lines 181, 183: These are inside a subprocess.run call, not a function return")
print("   The error might be about a different function that should return str but returns dict")
print("\n2. Line 256: log_verbose is being called with a potentially None value")
print("\n3. Line 327: Default argument 'analysis' has type None but should be dict")
print("\n4. Lines 331, 332, 339: dict.get() with wrong default type")
print("\n5. Line 355: Assigning int to float variable")
print("\n6. Lines 398, 400, 401, 404: Using dict as int")