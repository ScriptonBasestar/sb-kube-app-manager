#!/usr/bin/env python3
"""
Script to run lint commands and capture output
"""
import subprocess
import sys
import os

def run_command(cmd, description):
    """Run a command and capture output"""
    print(f"\n{'='*60}")
    print(f"Running: {description}")
    print(f"Command: {cmd}")
    print('='*60)
    
    try:
        result = subprocess.run(
            cmd,
            shell=True,
            capture_output=True,
            text=True,
            timeout=300  # 5 minutes timeout
        )
        
        print(f"Exit code: {result.returncode}")
        
        if result.stdout:
            print(f"\nSTDOUT:\n{result.stdout}")
        
        if result.stderr:
            print(f"\nSTDERR:\n{result.stderr}")
            
        return result.returncode, result.stdout, result.stderr
        
    except subprocess.TimeoutExpired:
        print(f"Command timed out after 5 minutes")
        return 1, "", "Command timed out"
    except Exception as e:
        print(f"Error running command: {e}")
        return 1, "", str(e)

def main():
    # Change to the project directory
    os.chdir("/Users/archmagece/myopen/scripton/sb-kube-app-manager")
    
    # Commands to run
    commands = [
        (
            "uv run ruff check sbkube tests --diff --exclude migrations --exclude node_modules --exclude examples",
            "Ruff check with diff"
        ),
        (
            "uv run mypy sbkube --ignore-missing-imports --exclude migrations --exclude node_modules --exclude examples",
            "MyPy type checking"
        ),
        (
            "uv run bandit -r sbkube --skip B101,B404,B603,B607,B602 --severity-level medium --quiet --exclude \"*/tests/*,*/scripts/*,*/debug/*,*/examples/*\"",
            "Bandit security check"
        )
    ]
    
    all_output = []
    
    for cmd, desc in commands:
        returncode, stdout, stderr = run_command(cmd, desc)
        all_output.append({
            'command': cmd,
            'description': desc,
            'returncode': returncode,
            'stdout': stdout,
            'stderr': stderr
        })
    
    # Write combined output to file
    with open('lint-output.txt', 'w') as f:
        f.write("LINT OUTPUT REPORT\n")
        f.write("=" * 60 + "\n")
        f.write(f"Generated at: {os.getcwd()}\n")
        f.write("=" * 60 + "\n\n")
        
        for output in all_output:
            f.write(f"COMMAND: {output['description']}\n")
            f.write(f"Command: {output['command']}\n")
            f.write(f"Exit code: {output['returncode']}\n")
            f.write("-" * 40 + "\n")
            
            if output['stdout']:
                f.write("STDOUT:\n")
                f.write(output['stdout'])
                f.write("\n")
            
            if output['stderr']:
                f.write("STDERR:\n")
                f.write(output['stderr'])
                f.write("\n")
            
            f.write("=" * 60 + "\n\n")
    
    print(f"\nAll output saved to: lint-output.txt")
    
    # Also show summary
    print("\nSUMMARY:")
    print("-" * 40)
    for output in all_output:
        status = "✓ PASS" if output['returncode'] == 0 else "✗ FAIL"
        print(f"{status} {output['description']}")

if __name__ == "__main__":
    main()