---
type: Troubleshooting Guide
audience: Developer
topics: [troubleshooting, development, errors, solutions]
llm_priority: high
last_updated: 2025-01-04
---

# Common Development Issues

Solutions for frequently encountered development issues in SBKube.

## Test Failures

### 1. k3s/testcontainers Issues

**Symptom**: testcontainers-related errors, k3s cluster creation failures

**Cause**: Docker not installed or not running

**Solution**:

```bash
# Check Docker installation
docker --version

# Check Docker is running
docker ps

# Check Docker daemon
echo $DOCKER_HOST

# Restart Docker Desktop (macOS)
# Or restart docker service (Linux)
sudo systemctl restart docker
```

### 2. Test Timeout Issues

**Symptom**: Tests hang or timeout

**Solution**:

```bash
# Use quick tests to skip slow E2E tests
make test-quick

# Run specific test with timeout
pytest tests/unit/commands/test_deploy.py -v --timeout=30

# Skip E2E tests
pytest -v -m "not e2e"
```

## Type Errors (mypy)

### Common Type Issues

**Symptom**: mypy validation failures

**Solutions**:

```python
# Use reveal_type() for debugging
from typing import reveal_type
reveal_type(my_variable)

# Pydantic models: use model_validate()
config = SBKubeConfig.model_validate(data)

# Optional types: explicit handling
from typing import Optional
def func(arg: Optional[str] = None) -> str:
    return arg or "default"

# Type narrowing for Union types
if isinstance(value, str):
    # mypy knows value is str here
    result = value.upper()
```

## Import Errors

**Symptom**: ModuleNotFoundError, import failures

**Causes**: Package structure, PYTHONPATH issues

**Solutions**:

```bash
# Use relative imports
from . import utils
from .models import SBKubeConfig

# Check __init__.py exists
ls sbkube/__init__.py

# Check PYTHONPATH
echo $PYTHONPATH

# Reinstall in editable mode
uv pip install -e .

# Clear Python cache
find . -type d -name __pycache__ -exec rm -rf {} +
find . -type f -name "*.pyc" -delete
```

## uv Package Manager Issues

### Dependency Installation Failures

**Symptom**: uv sync fails, dependency conflicts

**Solutions**:

```bash
# Update uv
pip install --upgrade uv

# Clear uv cache
rm -rf ~/.cache/uv

# Recreate virtual environment
rm -rf .venv
uv venv
source .venv/bin/activate
uv sync
```

### requirements.txt Issues

**Important**: SBKube uses `uv`, NOT `requirements.txt`

```bash
# ❌ WRONG - Don't create requirements.txt
pip freeze > requirements.txt

# ✅ CORRECT - Use uv add
uv add package_name
uv add --group dev package_name
uv add --group test package_name
```

## Kubernetes Deployment Issues

### 1. kubeconfig Problems

**Symptom**: Cannot connect to Kubernetes cluster

**Solution**:

```bash
# Check kubeconfig location
echo $KUBECONFIG
kubectl config view

# Check cluster access
kubectl cluster-info
kubectl get nodes

# Switch context
kubectl config use-context <context-name>
```

### 2. Helm Version Issues

**Symptom**: Helm commands fail

**Solution**:

```bash
# Check Helm version (v3.x required)
helm version

# Update Helm
brew upgrade helm  # macOS
# Or download from https://helm.sh/docs/intro/install/
```

### 3. Namespace Issues

**Symptom**: Resources not found, namespace doesn't exist

**Solution**:

```bash
# Create namespace
kubectl create namespace <namespace>

# Check resources in namespace
kubectl get all -n <namespace>

# Set default namespace
kubectl config set-context --current --namespace=<namespace>
```

## Debugging Tips

### Enable Verbose Logging

```bash
# SBKube verbose mode
sbkube --verbose prepare --app-dir config
```

### Python Debugger

```python
# Add breakpoint in code
def my_function():
    breakpoint()  # Execution stops here
    result = some_operation()
    return result
```

### Rich Console Debugging

```python
from rich import print as rprint
from rich.traceback import install

install()  # Enhanced tracebacks

rprint(f"Debug: {my_variable}")  # Colored output
```

### Check SBKube State

```bash
# View deployment history
sbkube history

# Check cluster status
sbkube status --by-group

# View specific deployment
sbkube history --show <deployment-id>
```

## Performance Issues

### Slow Tests

```bash
# Use parallel testing
make test-parallel

# Run only fast tests
pytest -v -m "not slow"

# Run specific test directories
make test-commands  # Only command tests
make test-models    # Only model tests
```

### Slow Builds

```bash
# Clean build artifacts
make clean

# Rebuild from scratch
make clean-all
uv pip install -e .
```

## Linting Issues

### Ruff Errors

```bash
# Auto-fix safe issues
make lint-fix

# Auto-fix including unsafe changes
make lint-fix UNSAFE_FIXES=1

# Check specific file
uv run ruff check sbkube/commands/deploy.py
```

### Black Formatting

```bash
# Format all files
uv run black sbkube/

# Check only
uv run black --check sbkube/
```

## Database Issues

### State Database Corruption

```bash
# Clean and recreate database
make clean-db

# Location of database
ls ~/.sbkube/deployments.db
```

## Related Documents

- [Troubleshooting Index](README.md) - Main troubleshooting guide
- [Development Guide](../04-development/README.md) - Setup and configuration
- [Testing Guide](../04-development/testing.md) - Test execution
- [Quick Commands](../04-development/quick-commands.md) - Common commands
