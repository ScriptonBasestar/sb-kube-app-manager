#!/usr/bin/env python3
"""Find the function around line 181 that has return type issues"""

import ast

file_path = "/Users/archmagece/myopen/scripton/sb-kube-app-manager/sbkube/validators/pre_deployment_validators.py"

with open(file_path) as f:
    source = f.read()

# Parse the AST
tree = ast.parse(source)

# Find all function definitions
functions = []
for node in ast.walk(tree):
    if isinstance(node, ast.FunctionDef) or isinstance(node, ast.AsyncFunctionDef):
        # Get the line range
        start_line = node.lineno
        end_line = node.end_lineno if hasattr(node, "end_lineno") else start_line + 10

        # Check if line 181 or 183 is within this function
        if start_line <= 181 <= end_line or start_line <= 183 <= end_line:
            functions.append(
                {
                    "name": node.name,
                    "start": start_line,
                    "end": end_line,
                    "is_async": isinstance(node, ast.AsyncFunctionDef),
                }
            )

print("Functions containing lines 181 or 183:")
for func in functions:
    print(f"\n{func['name']} ({'async ' if func['is_async'] else ''}function)")
    print(f"  Lines: {func['start']}-{func['end']}")

# Now let's look at the actual lines
print("\n" + "=" * 80)
print("Lines 175-190:")
lines = source.split("\n")
for i in range(174, min(190, len(lines))):
    print(f"{i + 1:4d}: {lines[i]}")
