#!/usr/bin/env python3
"""Analyze MyPy errors from the previous lint run"""

import re

# The MyPy errors from the previous run
mypy_errors = """
sbkube/exceptions.py:18: error: "type: ignore" comment without error code (currently ignored: [arg-type])  [no-untyped-def]
sbkube/exceptions.py:21: error: Function is missing a type annotation  [no-untyped-def]
sbkube/exceptions.py:35: error: Function is missing a type annotation  [no-untyped-def]
sbkube/exceptions.py:41: error: Function is missing a type annotation  [no-untyped-def]
sbkube/exceptions.py:47: error: Function is missing a type annotation  [no-untyped-def]
sbkube/exceptions.py:53: error: Function is missing a type annotation  [no-untyped-def]
sbkube/exceptions.py:59: error: Function is missing a type annotation  [no-untyped-def]
sbkube/exceptions.py:65: error: Function is missing a type annotation  [no-untyped-def]
sbkube/exceptions.py:71: error: Function is missing a type annotation  [no-untyped-def]
sbkube/exceptions.py:77: error: Function is missing a type annotation  [no-untyped-def]
sbkube/exceptions.py:83: error: Function is missing a type annotation  [no-untyped-def]
sbkube/exceptions.py:89: error: Function is missing a type annotation  [no-untyped-def]
sbkube/exceptions.py:95: error: Function is missing a type annotation  [no-untyped-def]
sbkube/cli.py:26: error: Function is missing a return type annotation  [no-untyped-def]
sbkube/cli.py:52: error: Function is missing a return type annotation  [no-untyped-def]
sbkube/cli.py:70: error: Function is missing a return type annotation  [no-untyped-def]
sbkube/cli.py:86: error: Function is missing a return type annotation  [no-untyped-def]
sbkube/cli.py:90: error: Function is missing a return type annotation  [no-untyped-def]
sbkube/cli.py:106: error: Function is missing a return type annotation  [no-untyped-def]
sbkube/validators/pre_deployment_validators.py:100: error: Cannot find implementation or library stub for module named "requests"  [import-not-found]
sbkube/validators/pre_deployment_validators.py:100: note: See https://mypy.readthedocs.io/en/stable/running_mypy.html#missing-imports
sbkube/validators/pre_deployment_validators.py:106: error: Cannot find implementation or library stub for module named "requests.exceptions"  [import-not-found]
sbkube/validators/pre_deployment_validators.py:181: error: Incompatible return value type (got "dict[str, str] | None", expected "str | None")  [return-value]
sbkube/validators/pre_deployment_validators.py:183: error: Incompatible return value type (got "dict[str, str]", expected "str | None")  [return-value]
sbkube/validators/pre_deployment_validators.py:256: error: Argument 2 to "log_verbose" has incompatible type "str | None"; expected "str"  [arg-type]
sbkube/validators/pre_deployment_validators.py:327: error: Incompatible default for argument "analysis" (default has type "None", argument has type "dict[str, Any]")  [assignment]
sbkube/validators/pre_deployment_validators.py:331: error: Argument 2 to "get" of "dict" has incompatible type "dict[str, Any]"; expected "Any | None"  [arg-type]
sbkube/validators/pre_deployment_validators.py:332: error: Argument 2 to "get" of "dict" has incompatible type "dict[str, Any]"; expected "Any | None"  [arg-type]
sbkube/validators/pre_deployment_validators.py:336: error: Incompatible types in assignment (expression has type "Any | None", variable has type "dict[str, Any]")  [assignment]
sbkube/validators/pre_deployment_validators.py:339: error: Argument 2 to "get" of "dict" has incompatible type "dict[str, Any]"; expected "Any | None"  [arg-type]
sbkube/validators/pre_deployment_validators.py:355: error: Incompatible types in assignment (expression has type "int", variable has type "float")  [assignment]
sbkube/validators/pre_deployment_validators.py:373: error: Incompatible default for argument "analysis" (default has type "None", argument has type "dict[str, Any]")  [assignment]
sbkube/validators/pre_deployment_validators.py:398: error: Incompatible types in assignment (expression has type "dict[str, Any]", variable has type "int")  [assignment]
sbkube/validators/pre_deployment_validators.py:400: error: Incompatible types in assignment (expression has type "dict[str, Any]", variable has type "int")  [assignment]
sbkube/validators/pre_deployment_validators.py:401: error: Unsupported operand types for * ("dict[str, Any]" and "int")  [operator]
sbkube/validators/pre_deployment_validators.py:404: error: Unsupported operand types for > ("dict[str, Any]" and "int")  [operator]
sbkube/validators/pre_deployment_validators.py:432: error: Incompatible default for argument "analysis" (default has type "None", argument has type "dict[str, Any]")  [assignment]
sbkube/validators/pre_deployment_validators.py:442: error: Argument 2 to "get" of "dict" has incompatible type "dict[str, Any]"; expected "Any | None"  [arg-type]
sbkube/validators/pre_deployment_validators.py:466: error: Argument 1 to "len" has incompatible type "Any | None"; expected "Sized"  [arg-type]
sbkube/validators/pre_deployment_validators.py:475: error: Value of type "Any | None" is not indexable  [index]
sbkube/validators/pre_deployment_validators.py:502: error: Incompatible default for argument "analysis" (default has type "None", argument has type "dict[str, Any]")  [assignment]
"""

# Parse errors by file
errors_by_file = {}
for line in mypy_errors.strip().split('\n'):
    if ': error:' in line:
        parts = line.split(':', 3)
        if len(parts) >= 4:
            file_name = parts[0]
            line_num = parts[1]
            error_msg = parts[3].strip()
            
            if file_name not in errors_by_file:
                errors_by_file[file_name] = []
            errors_by_file[file_name].append((line_num, error_msg))

# Print summary
print("MyPy Error Summary")
print("=" * 80)
for file_name, errors in errors_by_file.items():
    print(f"\n{file_name}: {len(errors)} errors")
    
    # Group by error type
    error_types = {}
    for line_num, error_msg in errors:
        error_type = error_msg.split('[')[-1].rstrip(']') if '[' in error_msg else 'other'
        if error_type not in error_types:
            error_types[error_type] = []
        error_types[error_type].append((line_num, error_msg))
    
    for error_type, type_errors in error_types.items():
        print(f"  - {error_type}: {len(type_errors)} occurrences")
        if len(type_errors) <= 3:
            for line_num, msg in type_errors:
                print(f"    Line {line_num}: {msg}")

print("\n" + "=" * 80)
print("Total errors:", sum(len(errors) for errors in errors_by_file.values()))
print("\nPriority fixes:")
print("1. Add return type annotations to functions in sbkube/cli.py")
print("2. Add type annotations to __init__ methods in sbkube/exceptions.py")
print("3. Fix type mismatches in sbkube/validators/pre_deployment_validators.py")
print("4. Fix import errors for requests module (types-requests should fix this)")