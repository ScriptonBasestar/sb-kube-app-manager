#!/usr/bin/env python3
"""Execute all lint fixes and report results"""

import os
import subprocess
from pathlib import Path

# Change to project directory
project_dir = Path("/Users/archmagece/myopen/scripton/sb-kube-app-manager")
os.chdir(project_dir)


def run_cmd(cmd, description):
    """Run a command and return result"""
    print(f"\n{'=' * 80}")
    print(f"🔧 {description}")
    print(f"Command: {cmd}")

    result = subprocess.run(cmd, shell=True, capture_output=True, text=True)
    print(f"Exit code: {result.returncode}")

    if result.returncode != 0 and result.stderr:
        print(f"Error: {result.stderr[:500]}")

    return result


# Start the lint fix process
print("🚀 Starting Lint Fix Process")
print("=" * 80)

# Step 1: Check initial lint status
print("\n📌 Step 1: Checking initial lint status")
initial_result = run_cmd("make lint", "Running initial lint check")

# Count initial errors
initial_errors = initial_result.stdout.count(": error:") if initial_result.stdout else 0
print(f"\nInitial error count: {initial_errors}")

# Step 2: Run auto-fixes
print("\n📌 Step 2: Running auto-fixes")

# Run ruff with fixes
run_cmd(
    "uv run ruff check sbkube tests --fix --unsafe-fixes --exclude migrations --exclude node_modules --exclude examples",
    "Running ruff with auto-fix and unsafe-fixes",
)

# Run ruff format
run_cmd(
    "uv run ruff format sbkube tests --exclude migrations --exclude node_modules --exclude examples",
    "Running ruff format",
)

# Run mdformat
run_cmd(
    "uv run mdformat *.md docs/**/*.md --wrap 120", "Running mdformat on markdown files"
)

# Step 3: Check final status
print("\n📌 Step 3: Checking final lint status")
final_result = run_cmd("make lint", "Running final lint check")

# Count final errors
final_errors = final_result.stdout.count(": error:") if final_result.stdout else 0
print(f"\nFinal error count: {final_errors}")

# Step 4: List modified files
print("\n📌 Step 4: Listing modified files")
git_result = run_cmd("git status --porcelain", "Checking git status")

if git_result.stdout:
    modified_files = []
    for line in git_result.stdout.split("\n"):
        if line.startswith(" M "):
            modified_files.append(line[3:])

    print(f"\n📁 Modified files ({len(modified_files)} total):")
    for f in sorted(modified_files):
        print(f"  - {f}")

# Summary
print("\n" + "=" * 80)
print("📊 Summary:")
print(f"  - Initial errors: {initial_errors}")
print(f"  - Final errors: {final_errors}")
print(f"  - Errors fixed: {initial_errors - final_errors}")

if final_errors == 0:
    print("\n✅ All lint errors have been fixed!")
else:
    print(f"\n⚠️  {final_errors} errors remain")
    print("Note: Some errors may require manual intervention")

print("\n✨ Lint fix process completed!")
print("=" * 80)
