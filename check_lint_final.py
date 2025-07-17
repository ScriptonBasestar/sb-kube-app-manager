#!/usr/bin/env python3
"""Check final lint status after fixes"""

import subprocess
import os

os.chdir("/Users/archmagece/myopen/scripton/sb-kube-app-manager")

print("🔍 Checking final lint status...")
print("=" * 80)

# Run make lint
result = subprocess.run(["make", "lint"], capture_output=True, text=True)

print(f"Exit code: {result.returncode}")

if result.returncode == 0:
    print("\n✅ SUCCESS! All lint checks passed!")
    print("make lint returned 0 errors")
else:
    print(f"\n❌ Some lint checks failed (exit code: {result.returncode})")
    
    # Show the output
    if result.stdout:
        print("\nOutput:")
        print(result.stdout)
    
    # Count errors
    error_count = result.stdout.count(": error:") if result.stdout else 0
    print(f"\nTotal errors found: {error_count}")

# List modified files
print("\n" + "=" * 80)
print("📁 Modified files:")
git_result = subprocess.run(["git", "status", "--porcelain"], capture_output=True, text=True)
if git_result.returncode == 0:
    modified = []
    for line in git_result.stdout.strip().split('\n'):
        if line.startswith(' M '):
            modified.append(line[3:])
    
    for f in sorted(modified):
        print(f"  - {f}")
    print(f"\nTotal: {len(modified)} files modified")

print("\n✨ Lint check completed!")