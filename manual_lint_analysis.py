#!/usr/bin/env python3
"""
Manual lint analysis script.
Since we can't run the actual lint tools, we'll analyze the code manually.
"""

import os
import re
from pathlib import Path


def analyze_file(file_path: Path) -> dict[str, list[str]]:
    """Analyze a single Python file for common issues."""
    issues = {
        "import_issues": [],
        "style_issues": [],
        "potential_bugs": [],
        "type_issues": [],
        "docstring_issues": [],
    }

    try:
        with open(file_path, encoding="utf-8") as f:
            lines = f.readlines()
    except Exception as e:
        issues["import_issues"].append(f"Could not read file: {e}")
        return issues

    for i, line in enumerate(lines, 1):
        line_stripped = line.strip()

        # Import issues
        if line_stripped.startswith("from ") and " import *" in line_stripped:
            issues["import_issues"].append(f"Line {i}: Wildcard import")

        # Style issues
        if len(line.rstrip()) > 88:
            issues["style_issues"].append(
                f"Line {i}: Line too long ({len(line.rstrip())} > 88)"
            )

        if line_stripped.endswith(","):
            # Check for trailing comma issues
            pass

        # Potential bugs
        if "except:" in line_stripped:
            issues["potential_bugs"].append(f"Line {i}: Bare except clause")

        if "print(" in line_stripped and "logger" not in "".join(lines[:i]):
            issues["potential_bugs"].append(
                f"Line {i}: Direct print() usage (should use logger)"
            )

        # Type issues
        if re.search(r"def \w+\([^)]*\):", line_stripped) and "->" not in line_stripped:
            if not line_stripped.startswith("def __"):  # Skip dunder methods
                issues["type_issues"].append(
                    f"Line {i}: Function missing return type annotation"
                )

    # Check for docstrings
    content = "".join(lines)
    if "class " in content:
        # Check if classes have docstrings
        class_matches = re.finditer(r"class\s+(\w+)", content)
        for match in class_matches:
            class_name = match.group(1)
            # Simple check - this is not perfect but gives an idea
            if '"""' not in content[match.end() : match.end() + 200]:
                issues["docstring_issues"].append(
                    f"Class {class_name} missing docstring"
                )

    return issues


def analyze_project() -> dict[str, dict[str, list[str]]]:
    """Analyze the entire project."""
    project_root = Path("/Users/archmagece/myopen/scripton/sb-kube-app-manager")
    if not project_root.exists():
        return {}

    python_files = list(project_root.glob("sbkube/**/*.py"))
    results = {}

    for file_path in python_files:
        relative_path = file_path.relative_to(project_root)
        results[str(relative_path)] = analyze_file(file_path)

    return results


def generate_summary(results: dict[str, dict[str, list[str]]]) -> str:
    """Generate a summary report."""
    total_files = len(results)
    total_issues = 0
    issue_categories = {
        "import_issues": 0,
        "style_issues": 0,
        "potential_bugs": 0,
        "type_issues": 0,
        "docstring_issues": 0,
    }

    report = []
    report.append("MANUAL LINT ANALYSIS REPORT")
    report.append("=" * 80)
    report.append(f"Analyzed {total_files} Python files")
    report.append("")

    for file_path, file_issues in results.items():
        file_total = sum(len(issues) for issues in file_issues.values())
        if file_total > 0:
            report.append(f"FILE: {file_path} ({file_total} issues)")
            report.append("-" * 60)

            for category, issues in file_issues.items():
                if issues:
                    report.append(f"  {category}:")
                    for issue in issues:
                        report.append(f"    - {issue}")
                    report.append("")
                    issue_categories[category] += len(issues)
                    total_issues += len(issues)

            report.append("")

    # Summary
    report.append("SUMMARY BY CATEGORY")
    report.append("-" * 40)
    for category, count in issue_categories.items():
        report.append(f"{category:20} {count:6} issues")

    report.append(f"{'TOTAL':20} {total_issues:6} issues")
    report.append("")

    # Common issues that might be found by actual linters
    report.append("LIKELY RUFF ISSUES:")
    report.append("- Import sorting (isort)")
    report.append("- Line length violations")
    report.append("- Trailing commas")
    report.append("- Unused imports")
    report.append("- Unused variables")
    report.append("")

    report.append("LIKELY MYPY ISSUES:")
    report.append("- Missing type annotations")
    report.append("- Any type usage")
    report.append("- Untyped function definitions")
    report.append("- Import type issues")
    report.append("")

    report.append("LIKELY BANDIT ISSUES:")
    report.append("- Subprocess usage without shell=False")
    report.append("- Hardcoded passwords/secrets")
    report.append("- Insecure random usage")
    report.append("- SQL injection risks")
    report.append("")

    return "\n".join(report)


def main():
    """Main function."""
    print("Running manual lint analysis...")

    os.chdir("/Users/archmagece/myopen/scripton/sb-kube-app-manager")

    results = analyze_project()

    if not results:
        print("No Python files found or could not access project")
        return

    summary = generate_summary(results)

    # Write to file
    with open("lint-output.txt", "w") as f:
        f.write(summary)

    print("Analysis complete. Report saved to: lint-output.txt")

    # Print quick summary
    total_issues = sum(
        sum(len(issues) for issues in file_issues.values())
        for file_issues in results.values()
    )
    print(f"Total issues found: {total_issues}")
    print(f"Files analyzed: {len(results)}")


if __name__ == "__main__":
    main()
