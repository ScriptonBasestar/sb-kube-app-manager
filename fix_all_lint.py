#!/usr/bin/env python3
"""Fix all lint errors using make commands"""

import os
import subprocess

os.chdir("/Users/archmagece/myopen/scripton/sb-kube-app-manager")

print("🚀 Running lint fixes...")
print("=" * 80)

# Run make lint-fix with unsafe fixes
print("\n1. Running make lint-fix with UNSAFE_FIXES=1...")
result = subprocess.run(
    ["make", "lint-fix", "UNSAFE_FIXES=1"], capture_output=True, text=True
)

print(f"Exit code: {result.returncode}")
if result.stdout:
    print("Output preview:")
    lines = result.stdout.split("\n")
    for line in lines[:20]:  # Show first 20 lines
        print(line)
    if len(lines) > 20:
        print(f"... ({len(lines) - 20} more lines)")

# Save full output
with open("lint-fix-output.txt", "w") as f:
    f.write(f"Exit code: {result.returncode}\n")
    f.write(f"\n=== STDOUT ===\n{result.stdout}")
    if result.stderr:
        f.write(f"\n=== STDERR ===\n{result.stderr}")

print("\nOutput saved to lint-fix-output.txt")

# Check final status
print("\n" + "=" * 80)
print("Checking final lint status...")

# Run make lint to check
check_result = subprocess.run(["make", "lint"], capture_output=True, text=True)

if check_result.returncode == 0:
    print("✅ All lint checks passed!")
else:
    print(f"❌ Some lint checks still failing (exit code: {check_result.returncode})")
    # Count remaining errors
    error_count = check_result.stdout.count(": error:")
    print(f"Remaining errors: {error_count}")

# List modified files
print("\n📁 Modified files:")
git_result = subprocess.run(
    ["git", "status", "--porcelain"], capture_output=True, text=True
)
if git_result.returncode == 0:
    for line in git_result.stdout.strip().split("\n"):
        if line.startswith(" M "):
            print(f"  - {line[3:]}")

print("\n✨ Lint fix process completed!")
