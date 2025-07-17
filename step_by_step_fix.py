#!/usr/bin/env python3
"""Step by step lint fix"""

import subprocess
import os

os.chdir("/Users/archmagece/myopen/scripton/sb-kube-app-manager")

print("Running lint fixes step by step...")

# First, let's run ruff with auto-fix
print("\n1. Running ruff auto-fix...")
subprocess.call(["uv", "run", "ruff", "check", "sbkube", "tests", "--fix", "--unsafe-fixes", "--exclude", "migrations", "--exclude", "node_modules", "--exclude", "examples"])

# Run ruff format
print("\n2. Running ruff format...")
subprocess.call(["uv", "run", "ruff", "format", "sbkube", "tests", "--exclude", "migrations", "--exclude", "node_modules", "--exclude", "examples"])

# Run mdformat
print("\n3. Running mdformat...")
subprocess.call(["uv", "run", "mdformat", "*.md", "docs/**/*.md", "--wrap", "120"])

print("\nFixes applied!")