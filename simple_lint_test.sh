#!/bin/bash
cd /Users/archmagece/myopen/scripton/sb-kube-app-manager

echo "Running make lint..."
make lint 2>&1 | tee lint_output.txt

echo ""
echo "Exit code: $?"
echo ""
echo "Checking for errors..."
grep -c "error:" lint_output.txt || echo "0 errors found"