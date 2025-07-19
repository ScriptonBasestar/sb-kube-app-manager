#!/usr/bin/env python3
"""Automatically fix all lint errors"""

import os
import subprocess

os.chdir("/Users/archmagece/myopen/scripton/sb-kube-app-manager")


def run_command(cmd, description):
    """Run a command and show the result"""
    print(f"\n🔧 {description}")
    print(f"Command: {cmd}")
    try:
        result = subprocess.run(cmd, shell=True, capture_output=True, text=True)
        if result.returncode == 0:
            print("✅ Success")
        else:
            print(f"❌ Failed (exit code: {result.returncode})")
            if result.stdout:
                print("Output:", result.stdout[:500])
            if result.stderr:
                print("Error:", result.stderr[:500])
        return result.returncode
    except Exception as e:
        print(f"❌ Error: {e}")
        return 1


print("🚀 Starting automatic lint fix process...")
print("=" * 80)

# Step 1: Run ruff with auto-fix
print("\n📌 Step 1: Running ruff auto-fix")
run_command(
    "uv run ruff check sbkube tests --fix --exclude migrations --exclude node_modules --exclude examples",
    "Fixing auto-fixable issues with ruff",
)

# Step 2: Run ruff with unsafe fixes
print("\n📌 Step 2: Running ruff with unsafe fixes")
run_command(
    "uv run ruff check sbkube tests --fix --unsafe-fixes --exclude migrations --exclude node_modules --exclude examples",
    "Fixing unsafe issues with ruff",
)

# Step 3: Run ruff format
print("\n📌 Step 3: Running ruff format")
run_command(
    "uv run ruff format sbkube tests --exclude migrations --exclude node_modules --exclude examples",
    "Formatting code with ruff",
)

# Step 4: Run mdformat
print("\n📌 Step 4: Running mdformat")
run_command("uv run mdformat *.md docs/**/*.md --wrap 120", "Formatting markdown files")

# Step 5: Check the results
print("\n📌 Step 5: Checking results")
print("\nRunning final lint check...")

# Check ruff
ruff_result = subprocess.run(
    "uv run ruff check sbkube tests --exclude migrations --exclude node_modules --exclude examples",
    shell=True,
    capture_output=True,
    text=True,
)

# Check mypy (it has ignore_errors for most modules)
mypy_result = subprocess.run(
    "uv run mypy sbkube --ignore-missing-imports --exclude migrations --exclude node_modules --exclude examples",
    shell=True,
    capture_output=True,
    text=True,
)

# Check bandit
bandit_result = subprocess.run(
    "uv run bandit -r sbkube --skip B101,B404,B603,B607,B602 --severity-level medium --quiet --exclude '*/tests/*,*/scripts/*,*/debug/*,*/examples/*'",
    shell=True,
    capture_output=True,
    text=True,
)

# Check mdformat
md_result = subprocess.run(
    "uv run mdformat --check *.md docs/**/*.md --wrap 120",
    shell=True,
    capture_output=True,
    text=True,
)

print("\n" + "=" * 80)
print("📊 Final Results:")
print(f"- Ruff: {'✅ PASS' if ruff_result.returncode == 0 else '❌ FAIL'}")
print(f"- MyPy: {'✅ PASS' if mypy_result.returncode == 0 else '❌ FAIL'}")
print(f"- Bandit: {'✅ PASS' if bandit_result.returncode == 0 else '❌ FAIL'}")
print(f"- Markdown: {'✅ PASS' if md_result.returncode == 0 else '❌ FAIL'}")

all_pass = all(
    r.returncode == 0 for r in [ruff_result, mypy_result, bandit_result, md_result]
)
print(
    f"\nOverall: {'✅ All checks passed!' if all_pass else '❌ Some checks still failing'}"
)

if not all_pass:
    print("\nRemaining issues:")
    if ruff_result.returncode != 0:
        print(f"- Ruff: {ruff_result.stdout.count('Found')} issues")
    if mypy_result.returncode != 0:
        print(f"- MyPy: {mypy_result.stdout.count('error:')} errors")
    if bandit_result.returncode != 0:
        print("- Bandit: Security issues found")
    if md_result.returncode != 0:
        print("- Markdown: Formatting issues")

# List modified files
print("\n📁 Modified files:")
git_result = subprocess.run(
    "git status --porcelain", shell=True, capture_output=True, text=True
)
if git_result.returncode == 0:
    modified_files = [
        line[3:]
        for line in git_result.stdout.strip().split("\n")
        if line.startswith(" M ")
    ]
    for f in sorted(modified_files):
        print(f"  - {f}")
    print(f"\nTotal: {len(modified_files)} files modified")
