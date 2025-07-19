#!/usr/bin/env python3
"""
Comprehensive lint checker for sbkube project.
This script runs all lint tools and provides a detailed report.
"""

import os
import subprocess
import sys
import time
from pathlib import Path


def ensure_project_root():
    """Ensure we're in the project root directory."""
    project_root = Path("/Users/archmagece/myopen/scripton/sb-kube-app-manager")
    if not project_root.exists():
        raise FileNotFoundError(f"Project root not found: {project_root}")

    os.chdir(project_root)
    return project_root


def run_command_with_timeout(
    cmd: list[str], timeout: int = 300, cwd: str = None
) -> tuple[int, str, str]:
    """
    Run a command with timeout and return results.

    Args:
        cmd: Command to run as list of strings
        timeout: Timeout in seconds
        cwd: Working directory

    Returns:
        Tuple of (return_code, stdout, stderr)
    """
    try:
        result = subprocess.run(
            cmd, capture_output=True, text=True, timeout=timeout, cwd=cwd
        )
        return result.returncode, result.stdout, result.stderr
    except subprocess.TimeoutExpired:
        return 124, "", f"Command timed out after {timeout} seconds"
    except FileNotFoundError as e:
        return 127, "", f"Command not found: {e}"
    except Exception as e:
        return 1, "", f"Error running command: {e}"


def check_tool_availability() -> dict[str, bool]:
    """Check if required tools are available."""
    tools = {
        "uv": ["uv", "--version"],
        "ruff": ["uv", "run", "ruff", "--version"],
        "mypy": ["uv", "run", "mypy", "--version"],
        "bandit": ["uv", "run", "bandit", "--version"],
    }

    availability = {}
    for tool, cmd in tools.items():
        returncode, _, _ = run_command_with_timeout(cmd, timeout=10)
        availability[tool] = returncode == 0

    return availability


def run_ruff_check() -> dict[str, str]:
    """Run ruff check with different modes."""
    results = {}

    # Basic ruff check
    cmd = [
        "uv",
        "run",
        "ruff",
        "check",
        "sbkube",
        "tests",
        "--diff",
        "--exclude",
        "migrations",
        "--exclude",
        "node_modules",
        "--exclude",
        "examples",
    ]

    returncode, stdout, stderr = run_command_with_timeout(cmd)
    results["ruff_check"] = {
        "command": " ".join(cmd),
        "returncode": returncode,
        "stdout": stdout,
        "stderr": stderr,
    }

    # Ruff check with all rules (strict)
    cmd_strict = [
        "uv",
        "run",
        "ruff",
        "check",
        "sbkube",
        "tests",
        "--select",
        "ALL",
        "--ignore",
        "E501,B008,C901,COM812,B904,B017,B007,D100,D101,D102,D103,D104,D105,D106,D107",
        "--exclude",
        "migrations",
        "--exclude",
        "node_modules",
        "--exclude",
        "examples",
        "--output-format",
        "full",
    ]

    returncode, stdout, stderr = run_command_with_timeout(cmd_strict)
    results["ruff_strict"] = {
        "command": " ".join(cmd_strict),
        "returncode": returncode,
        "stdout": stdout,
        "stderr": stderr,
    }

    return results


def run_mypy_check() -> dict[str, str]:
    """Run mypy type checking."""
    cmd = [
        "uv",
        "run",
        "mypy",
        "sbkube",
        "--ignore-missing-imports",
        "--exclude",
        "migrations",
        "--exclude",
        "node_modules",
        "--exclude",
        "examples",
    ]

    returncode, stdout, stderr = run_command_with_timeout(cmd)

    return {
        "mypy_check": {
            "command": " ".join(cmd),
            "returncode": returncode,
            "stdout": stdout,
            "stderr": stderr,
        }
    }


def run_bandit_check() -> dict[str, str]:
    """Run bandit security check."""
    cmd = [
        "uv",
        "run",
        "bandit",
        "-r",
        "sbkube",
        "--skip",
        "B101,B404,B603,B607,B602",
        "--severity-level",
        "medium",
        "--exclude",
        "*/tests/*,*/scripts/*,*/debug/*,*/examples/*",
    ]

    returncode, stdout, stderr = run_command_with_timeout(cmd)

    return {
        "bandit_check": {
            "command": " ".join(cmd),
            "returncode": returncode,
            "stdout": stdout,
            "stderr": stderr,
        }
    }


def analyze_python_files() -> dict[str, list[str]]:
    """Analyze Python files for common issues."""
    issues = {"import_issues": [], "syntax_issues": [], "encoding_issues": []}

    python_files = list(Path("sbkube").rglob("*.py"))

    for file_path in python_files:
        try:
            with open(file_path, encoding="utf-8") as f:
                content = f.read()

                # Check for common import issues
                if "import *" in content:
                    issues["import_issues"].append(
                        f"{file_path}: Contains wildcard imports"
                    )

                # Check for syntax (basic)
                try:
                    compile(content, str(file_path), "exec")
                except SyntaxError as e:
                    issues["syntax_issues"].append(
                        f"{file_path}: Syntax error at line {e.lineno}: {e.msg}"
                    )

        except UnicodeDecodeError:
            issues["encoding_issues"].append(f"{file_path}: Encoding issues")
        except Exception as e:
            issues["syntax_issues"].append(f"{file_path}: Error reading file: {e}")

    return issues


def generate_report(
    tool_availability: dict[str, bool],
    ruff_results: dict[str, str],
    mypy_results: dict[str, str],
    bandit_results: dict[str, str],
    file_analysis: dict[str, list[str]],
) -> str:
    """Generate comprehensive lint report."""

    report = []
    report.append("=" * 80)
    report.append("SBKUBE LINT REPORT")
    report.append("=" * 80)
    report.append(f"Generated at: {time.strftime('%Y-%m-%d %H:%M:%S')}")
    report.append(f"Working directory: {os.getcwd()}")
    report.append("")

    # Tool availability
    report.append("TOOL AVAILABILITY")
    report.append("-" * 40)
    for tool, available in tool_availability.items():
        status = "✓ Available" if available else "✗ Not available"
        report.append(f"{tool:15} {status}")
    report.append("")

    # File analysis
    report.append("PYTHON FILE ANALYSIS")
    report.append("-" * 40)
    for category, issues in file_analysis.items():
        report.append(f"{category}:")
        if issues:
            for issue in issues:
                report.append(f"  - {issue}")
        else:
            report.append("  - No issues found")
        report.append("")

    # Detailed results
    all_results = {**ruff_results, **mypy_results, **bandit_results}

    for tool_name, result in all_results.items():
        report.append(f"TOOL: {tool_name.upper()}")
        report.append("-" * 40)
        report.append(f"Command: {result['command']}")
        report.append(f"Exit code: {result['returncode']}")
        report.append("")

        if result["stdout"]:
            report.append("STDOUT:")
            report.append(result["stdout"])
            report.append("")

        if result["stderr"]:
            report.append("STDERR:")
            report.append(result["stderr"])
            report.append("")

        report.append("=" * 80)
        report.append("")

    # Summary
    report.append("SUMMARY")
    report.append("-" * 40)

    total_issues = sum(len(issues) for issues in file_analysis.values())

    for tool_name, result in all_results.items():
        status = "✓ PASS" if result["returncode"] == 0 else "✗ FAIL"
        report.append(f"{tool_name:15} {status}")

    report.append(f"File analysis:  {total_issues} issues found")
    report.append("")

    return "\n".join(report)


def main():
    """Main function to run all lint checks."""
    print("Starting comprehensive lint check...")

    try:
        # Ensure we're in the right directory
        project_root = ensure_project_root()
        print(f"Working in: {project_root}")

        # Check tool availability
        print("Checking tool availability...")
        tool_availability = check_tool_availability()

        # Run lint tools
        print("Running ruff check...")
        ruff_results = run_ruff_check()

        print("Running mypy check...")
        mypy_results = run_mypy_check()

        print("Running bandit check...")
        bandit_results = run_bandit_check()

        print("Analyzing Python files...")
        file_analysis = analyze_python_files()

        # Generate report
        print("Generating report...")
        report = generate_report(
            tool_availability, ruff_results, mypy_results, bandit_results, file_analysis
        )

        # Write report to file
        with open("lint-output.txt", "w") as f:
            f.write(report)

        print("Report saved to: lint-output.txt")

        # Print summary to console
        print("\n" + "=" * 60)
        print("QUICK SUMMARY")
        print("=" * 60)

        all_results = {**ruff_results, **mypy_results, **bandit_results}
        for tool_name, result in all_results.items():
            status = "✓ PASS" if result["returncode"] == 0 else "✗ FAIL"
            print(f"{tool_name:15} {status}")

        total_issues = sum(len(issues) for issues in file_analysis.values())
        print(f"File analysis:  {total_issues} issues found")

    except Exception as e:
        print(f"Error during lint check: {e}")
        sys.exit(1)


if __name__ == "__main__":
    main()
