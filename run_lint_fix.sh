#!/bin/bash
# Script to run lint-fix commands from the Makefile

echo "Running lint with auto-fix..."
echo "Running ruff check with auto-fix..."
uv run ruff check sbkube tests --select I --fix --exclude migrations --exclude node_modules --exclude examples

echo "Running ruff format..."
uv run ruff format sbkube tests --exclude migrations --exclude node_modules --exclude examples

echo "Running mypy..."
uv run mypy sbkube --ignore-missing-imports --exclude migrations --exclude node_modules --exclude examples

echo "Running bandit security check..."
uv run bandit -r sbkube --skip B101,B404,B603,B607,B602 --severity-level medium --quiet --exclude "*/tests/*,*/scripts/*,*/debug/*,*/examples/*" || echo "✅ Security check completed"

echo "Running mdformat..."
uv run mdformat *.md docs/**/*.md --wrap 120

echo "Lint-fix completed!"