______________________________________________________________________

## type: Troubleshooting Guide audience: Developer topics: [troubleshooting, development, errors, solutions] llm_priority: high last_updated: 2025-01-04

# Common Development Issues

Solutions for frequently encountered development issues in SBKube.

## Test Failures

### 확인된 기존 결함: status watch 테스트의 로그 레벨 의존 (2026-10-26)

`tests/unit/commands/test_status_cmd.py::TestStatusCommandCombinations::test_status_watch_mode_interrupted`는
기본 WARNING 로그 레벨에서 단독 실행하면 출력이 비어 실패한다. `OutputManager.print`의 기본 info 출력이
억제되는데 테스트가 `watch` 안내 문구를 요구하기 때문이다. INFO 레벨을 먼저 설정한 같은 프로세스에서는
통과한다. 따라서 묶음 실행의 선행 로그 설정에 따라 결과가 달라질 수 있다.

자동 access 프로파일 변경 전 master `05a08c7`에서도 단독 실행은 exit 1이고, INFO를 명시한 실행은 exit 0임을
확인했다(Python 3.14.5, macOS, `uv run --frozen --group test pytest -q --no-cov`로 해당 테스트 선택).
자동 프로파일 변경에서도 같은 단독 실패를 확인했다. 클러스터 호출은 테스트에서 모의 처리한다.

기대 동작은 테스트가 자신의 로그 전제를 준비해 독립적으로 통과하는 것이다. 이 결함의 수정은 access
프로파일 작업 범위 밖으로 남긴다. GitHub Issues 등록은 별도 게시 권한이 필요해 수행하지 않았으며,
이 절은 등록 시 옮길 재현 증거다. 검사 실패를 성공으로 바꾸거나 전체 게이트를 생략하는 근거가 아니다.

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
