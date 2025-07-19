#!/usr/bin/env python3
"""Simple script to check if basic Python imports work and syntax is valid."""

import ast
import glob
import os
import sys
from pathlib import Path


def check_python_syntax(file_path):
    """Check if a Python file has valid syntax."""
    try:
        with open(file_path, encoding="utf-8") as f:
            source = f.read()

        # Try to parse the AST
        ast.parse(source)
        return True, None
    except SyntaxError as e:
        return False, f"Syntax error at line {e.lineno}: {e.msg}"
    except Exception as e:
        return False, f"Error reading file: {e}"


def check_imports(file_path):
    """Check if imports in a file are accessible."""
    try:
        with open(file_path, encoding="utf-8") as f:
            source = f.read()

        tree = ast.parse(source)
        imports = []

        for node in ast.walk(tree):
            if isinstance(node, ast.Import):
                for alias in node.names:
                    imports.append(alias.name)
            elif isinstance(node, ast.ImportFrom):
                module = node.module or ""
                for alias in node.names:
                    imports.append(f"{module}.{alias.name}")

        return imports
    except Exception:
        return []


def main():
    """Main function to check Python files."""
    project_root = Path("/Users/archmagece/myopen/scripton/sb-kube-app-manager")
    os.chdir(project_root)

    # Find all Python files in sbkube directory
    python_files = []
    for pattern in ["sbkube/**/*.py", "tests/**/*.py"]:
        python_files.extend(glob.glob(pattern, recursive=True))

    print(f"Found {len(python_files)} Python files")
    print("=" * 60)

    syntax_errors = []
    valid_files = []

    for file_path in python_files:
        if (
            "migrations" in file_path
            or "node_modules" in file_path
            or "examples" in file_path
        ):
            continue

        is_valid, error = check_python_syntax(file_path)
        if is_valid:
            valid_files.append(file_path)
            print(f"✅ {file_path}")
        else:
            syntax_errors.append((file_path, error))
            print(f"❌ {file_path}: {error}")

    print("\n" + "=" * 60)
    print("SUMMARY:")
    print(f"Total files checked: {len(python_files)}")
    print(f"Valid files: {len(valid_files)}")
    print(f"Files with syntax errors: {len(syntax_errors)}")

    if syntax_errors:
        print("\nSYNTAX ERRORS:")
        for file_path, error in syntax_errors:
            print(f"  {file_path}: {error}")
        return 1
    else:
        print("\n✅ All Python files have valid syntax!")

        # Check for common issues by looking at a few key files
        key_files = [
            "sbkube/cli.py",
            "sbkube/exceptions.py",
            "sbkube/validators/basic_validators.py",
            "sbkube/commands/deploy.py",
        ]

        print("\nCHECKING KEY FILES FOR COMMON ISSUES:")
        for file_path in key_files:
            if os.path.exists(file_path):
                print(f"\n📁 {file_path}:")

                # Check file length
                with open(file_path) as f:
                    lines = f.readlines()

                long_lines = []
                for i, line in enumerate(lines, 1):
                    if len(line.rstrip()) > 88:
                        long_lines.append((i, len(line.rstrip())))

                if long_lines:
                    print(f"  ⚠️  Lines exceeding 88 characters: {len(long_lines)}")
                    for line_num, length in long_lines[:3]:  # Show first 3
                        print(f"    Line {line_num}: {length} chars")
                    if len(long_lines) > 3:
                        print(f"    ... and {len(long_lines) - 3} more")
                else:
                    print("  ✅ No lines exceeding 88 characters")

                # Check imports
                imports = check_imports(file_path)
                if imports:
                    print(f"  📦 Found {len(imports)} imports")

        return 0


if __name__ == "__main__":
    sys.exit(main())
