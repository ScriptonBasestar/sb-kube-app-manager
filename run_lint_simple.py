#!/usr/bin/env python3
"""
Simple script to run lint commands and write output to file.
"""

import os
import subprocess
from pathlib import Path

# Change to project directory
os.chdir("/Users/archmagece/myopen/scripton/sb-kube-app-manager")


def run_cmd(cmd_str, description):
    """Run a shell command and return the result."""
    print(f"Running: {description}")
    print(f"Command: {cmd_str}")
    print("-" * 60)

    try:
        # Use shell=True to handle the command as a string
        result = subprocess.run(
            cmd_str,
            shell=True,
            capture_output=True,
            text=True,
            timeout=300,
            env=os.environ.copy(),
        )

        return {
            "description": description,
            "command": cmd_str,
            "returncode": result.returncode,
            "stdout": result.stdout,
            "stderr": result.stderr,
        }
    except subprocess.TimeoutExpired:
        return {
            "description": description,
            "command": cmd_str,
            "returncode": 124,
            "stdout": "",
            "stderr": "Command timed out after 300 seconds",
        }
    except Exception as e:
        return {
            "description": description,
            "command": cmd_str,
            "returncode": 1,
            "stdout": "",
            "stderr": f"Error: {e}",
        }


# Commands to run
commands = [
    (
        "uv run ruff check sbkube tests --diff --exclude migrations --exclude node_modules --exclude examples",
        "Ruff check with diff",
    ),
    (
        "uv run mypy sbkube --ignore-missing-imports --exclude migrations --exclude node_modules --exclude examples",
        "MyPy type checking",
    ),
    (
        "uv run bandit -r sbkube --skip B101,B404,B603,B607,B602 --severity-level medium --quiet --exclude '*/tests/*,*/scripts/*,*/debug/*,*/examples/*'",
        "Bandit security check",
    ),
]

results = []

for cmd, desc in commands:
    result = run_cmd(cmd, desc)
    results.append(result)
    print(f"Exit code: {result['returncode']}")
    print()

# Write results to file
output_file = Path("lint-output.txt")
with open(output_file, "w") as f:
    f.write("LINT OUTPUT REPORT\n")
    f.write("=" * 80 + "\n")
    f.write(f"Generated from: {os.getcwd()}\n")
    f.write("=" * 80 + "\n\n")

    for result in results:
        f.write(f"TOOL: {result['description']}\n")
        f.write(f"Command: {result['command']}\n")
        f.write(f"Exit code: {result['returncode']}\n")
        f.write("-" * 60 + "\n")

        if result["stdout"]:
            f.write("STDOUT:\n")
            f.write(result["stdout"])
            f.write("\n")

        if result["stderr"]:
            f.write("STDERR:\n")
            f.write(result["stderr"])
            f.write("\n")

        f.write("=" * 80 + "\n\n")

print(f"Results written to: {output_file.absolute()}")

# Summary
print("SUMMARY:")
print("-" * 40)
for result in results:
    status = "✓ PASS" if result["returncode"] == 0 else "✗ FAIL"
    print(f"{result['description']:25} {status}")
