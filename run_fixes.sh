#!/bin/bash
set -e

echo "🚀 Running lint fixes..."
echo "=================================================================================="

cd /Users/archmagece/myopen/scripton/sb-kube-app-manager

# Step 1: Run make lint-fix with unsafe fixes
echo -e "\n📌 Step 1: Running make lint-fix with UNSAFE_FIXES=1"
make lint-fix UNSAFE_FIXES=1

# Step 2: Check the results
echo -e "\n📌 Step 2: Checking results with make lint"
make lint || true

echo -e "\n✨ Lint fix process completed!"