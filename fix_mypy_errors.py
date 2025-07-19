#!/usr/bin/env python3
"""Fix the remaining MyPy errors based on the error output"""

import os

# Change to the project directory
os.chdir("/Users/archmagece/myopen/scripton/sb-kube-app-manager")

# Define the fixes needed based on the MyPy errors
fixes = [
    # Fix line 181: The function should return str | None, not dict[str, str] | None
    {
        "file": "sbkube/validators/pre_deployment_validators.py",
        "description": "Fix return type issue on line 181",
        "search_pattern": r"def (_get_namespace_config|_extract_namespace_config)\(.*?\) -> .*?:",
        "needs_manual_check": True,
        "line": 181,
    },
    # Fix line 256: Argument type issue with log_verbose
    {
        "file": "sbkube/validators/pre_deployment_validators.py",
        "description": "Fix log_verbose argument type on line 256",
        "line": 256,
        "fix": "Cast namespace to str or handle None case",
    },
    # Fix line 327: Default argument type mismatch
    {
        "file": "sbkube/validators/pre_deployment_validators.py",
        "description": "Fix default argument type on line 327",
        "line": 327,
        "fix": "Change default from None to {}",
    },
    # Fix line 331-332, 339: dict.get() argument type issues
    {
        "file": "sbkube/validators/pre_deployment_validators.py",
        "description": "Fix dict.get() argument types",
        "lines": [331, 332, 339],
        "fix": "Second argument to get() should be same type or None",
    },
    # Fix line 355: int/float assignment
    {
        "file": "sbkube/validators/pre_deployment_validators.py",
        "description": "Fix int assignment to float variable",
        "line": 355,
        "fix": "Cast to float or change variable type",
    },
    # Fix lines 398, 400, 401, 404: dict[str, Any] used as int
    {
        "file": "sbkube/validators/pre_deployment_validators.py",
        "description": "Fix dict being used as int",
        "lines": [398, 400, 401, 404],
        "fix": "Extract integer value from dict",
    },
]

print("MyPy Error Fix Plan")
print("=" * 80)
print("\nIdentified fixes needed:")
for i, fix in enumerate(fixes, 1):
    print(f"\n{i}. {fix['description']}")
    print(f"   File: {fix['file']}")
    if "line" in fix:
        print(f"   Line: {fix['line']}")
    elif "lines" in fix:
        print(f"   Lines: {', '.join(map(str, fix['lines']))}")
    if "fix" in fix:
        print(f"   Fix: {fix['fix']}")

print("\n" + "=" * 80)
print("\nTo fix these errors, we need to:")
print("1. Find functions that return config dicts instead of strings")
print("2. Add proper type handling for optional values")
print("3. Fix type mismatches in assignments")
print("4. Handle dict.get() default values properly")
