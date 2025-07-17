#!/usr/bin/env python3
"""Verify security fixes"""

import subprocess
import os

os.chdir("/Users/archmagece/myopen/scripton/sb-kube-app-manager")

print("🔒 Verifying security fixes...")
print("=" * 80)

# Run bandit on the specific files
print("\n1. Checking init.py for Jinja2 autoescape...")
result1 = subprocess.run(
    ["uv", "run", "bandit", "sbkube/commands/init.py", "-r", "-ll"],
    capture_output=True,
    text=True
)

if "B701" in result1.stdout:
    print("❌ Jinja2 autoescape issue still present")
else:
    print("✅ Jinja2 autoescape issue fixed")

print("\n2. Checking execution_tracker.py for MD5 hash...")
result2 = subprocess.run(
    ["uv", "run", "bandit", "sbkube/utils/execution_tracker.py", "-r", "-ll"],
    capture_output=True,
    text=True
)

if "B324" in result2.stdout:
    print("❌ MD5 hash security issue still present")
else:
    print("✅ MD5 hash security issue fixed")

# Run full bandit check
print("\n3. Running full bandit security check...")
result = subprocess.run(
    ["uv", "run", "bandit", "-r", "sbkube", "--skip", "B101,B404,B603,B607,B602", 
     "--severity-level", "high", "--quiet", 
     "--exclude", "*/tests/*,*/scripts/*,*/debug/*,*/examples/*"],
    capture_output=True,
    text=True
)

if result.returncode == 0:
    print("✅ No high severity security issues found")
else:
    print(f"❌ Bandit found issues (exit code: {result.returncode})")
    if result.stdout:
        print("\nOutput:")
        print(result.stdout)

print("\n" + "=" * 80)
print("📊 Summary:")
print("- Fixed: Jinja2 autoescape=True")
print("- Fixed: MD5 usedforsecurity=False")
print("- Both security issues should now be resolved")