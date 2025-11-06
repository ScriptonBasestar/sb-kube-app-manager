______________________________________________________________________

## type: Quick Reference audience: Developer topics: [commands, development, shortcuts, make] llm_priority: high last_updated: 2025-01-04

# Quick Command Reference

Most commonly used commands for SBKube development.

**Primary Source**: [Makefile](../../Makefile) - Run `make help` for complete list

## Development Setup

```bash
# Complete development environment setup
make install-all          # Install sbkube with dev + test dependencies

# Manual installation
uv venv                   # Create virtual environment
source .venv/bin/activate # Activate (Windows: .venv\Scripts\activate)
uv sync                   # Install dependencies
uv pip install -e .       # Install in editable mode
```

## Code Quality

```bash
# Quick syntax + type check (fastest, like build compile)
make check

# Auto-fix linting issues (recommended)
make lint-fix

# Check only (no changes)
make lint-check

# Strict mode (all rules)
make lint-strict

# With unsafe fixes
make lint-fix UNSAFE_FIXES=1
```

## Testing

```bash
# Quick tests (excludes E2E and slow tests)
make test-quick

# All tests
make test

# With coverage
make test-coverage

# Specific test file
pytest tests/unit/commands/test_deploy.py -v

# Specific test category
make test-unit            # Unit tests only
make test-integration     # Integration tests
make test-e2e             # End-to-end tests
```

## CI Simulation

```bash
# Full CI check (lint + test + coverage)
make ci

# CI with auto-fix
make ci-fix
```

## SBKube CLI Usage

```bash
# Unified workflow (recommended)
sbkube apply --app-dir config --namespace production

# Step-by-step execution
sbkube prepare --app-dir config
sbkube build --app-dir config
sbkube template --app-dir config
sbkube deploy --app-dir config --namespace production

# State management (v0.6.0+)
sbkube status --by-group
sbkube history
sbkube rollback <deployment-id>
```

## Cleanup

```bash
# Clean build artifacts
make clean

# Clean database
make clean-db

# Clean Docker test containers
make clean-docker

# Full clean
make clean-all
```

## Building and Release

```bash
# Build package
uv build

# Upload to PyPI
uv run -m twine upload dist/*

# Version management
make version              # Show current version
make bump-patch           # 0.6.1 → 0.6.2
make bump-minor           # 0.6.1 → 0.7.0
```

## Kubernetes Testing

```bash
# Create test cluster
kind create cluster --name sbkube-test
kubectl config use-context kind-sbkube-test

# Run SBKube commands
sbkube apply --app-dir examples/basic --namespace test

# Delete test cluster
kind delete cluster --name sbkube-test
```

## Related Documents

- [Makefile](../../Makefile) - Complete command list with `make help`
- [Development Guide](README.md) - Development environment setup
- [Testing Guide](testing.md) - Detailed testing strategies
- [Coding Standards](coding-standards.md) - Code style and conventions
