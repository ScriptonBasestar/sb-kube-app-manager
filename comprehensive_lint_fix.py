#!/usr/bin/env python3
"""Comprehensive lint fix script"""

import os
import subprocess
from datetime import datetime

os.chdir("/Users/archmagece/myopen/scripton/sb-kube-app-manager")


def run_command(cmd, description, capture=True):
    """Run a command and return the result"""
    print(f"\n{'=' * 80}")
    print(f"🔧 {description}")
    print(f"Command: {' '.join(cmd) if isinstance(cmd, list) else cmd}")
    print(f"Time: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}")

    try:
        if capture:
            result = subprocess.run(
                cmd, capture_output=True, text=True, shell=isinstance(cmd, str)
            )
            print(f"Exit code: {result.returncode}")
            return result
        else:
            # Run without capturing for real-time output
            result = subprocess.run(cmd, shell=isinstance(cmd, str))
            print(f"Exit code: {result.returncode}")
            return result
    except Exception as e:
        print(f"Error: {e}")
        return None


# Step 1: Check initial status
print("🚀 Starting comprehensive lint fix process")
print("=" * 80)

# Mark first todo as in progress
print("\n📌 Step 1: Analyzing current lint status")

# Run make lint to see current status
result = run_command("make lint", "Running make lint to check current errors")
if result and result.stdout:
    error_count = result.stdout.count(": error:")
    print(f"\nFound {error_count} errors in initial check")

    # Save initial output
    with open("lint-initial.txt", "w") as f:
        f.write(result.stdout)
    print("Saved initial lint output to lint-initial.txt")

# Step 2: Run make lint-fix with UNSAFE_FIXES=1
print("\n📌 Step 2: Running auto-fix with unsafe fixes enabled")

# Run the fix command
result = run_command(
    ["make", "lint-fix", "UNSAFE_FIXES=1"],
    "Running make lint-fix UNSAFE_FIXES=1",
    capture=False,
)

# Step 3: Check results
print("\n📌 Step 3: Verifying fixes")

# Run make lint again
result = run_command("make lint", "Running make lint to verify fixes")
if result:
    final_error_count = result.stdout.count(": error:")
    print(f"\nRemaining errors: {final_error_count}")

    if final_error_count == 0:
        print("✅ All lint errors have been fixed!")
    else:
        print(f"❌ Still have {final_error_count} errors")
        # Save final output
        with open("lint-final.txt", "w") as f:
            f.write(result.stdout)
        print("Saved final lint output to lint-final.txt")

# Step 4: List modified files
print("\n📌 Step 4: Listing modified files")

result = run_command("git status --porcelain", "Checking modified files")
if result and result.stdout:
    lines = result.stdout.strip().split("\n")
    modified_files = []

    for line in lines:
        if line.startswith(" M "):
            modified_files.append(line[3:])

    print(f"\n📁 Modified files ({len(modified_files)} total):")
    for f in sorted(modified_files):
        print(f"  - {f}")

    # Save list of modified files
    with open("modified-files.txt", "w") as f:
        f.write("\n".join(sorted(modified_files)))
    print("\nSaved list to modified-files.txt")

print("\n" + "=" * 80)
print("✨ Lint fix process completed!")
print("=" * 80)
