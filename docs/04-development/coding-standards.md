______________________________________________________________________

## type: Developer Guide audience: Developer topics: [coding-standards, style-guide, conventions] llm_priority: high last_updated: 2025-01-04

# Coding Standards

This document defines coding standards and conventions for SBKube development.

## Python Style

- **Language**: Python 3.14+
- **Formatter**: black (line-length: 120)
- **Linter**: ruff (configuration: [ruff.toml](../../ruff.toml))
- **Type Checker**: mypy (configuration: [mypy.ini](../../mypy.ini))
- **Convention**: PEP 8
  - Functions/Variables: `snake_case`
  - Classes: `PascalCase`
  - Constants: `UPPER_SNAKE_CASE`

## Import Order

Follow this three-tier import structure:

```python
# 1. Standard library
import os
from pathlib import Path

# 2. Third-party libraries
import click
from pydantic import BaseModel

# 3. Local modules
from sbkube.utils.logger import console
from sbkube.models.config_model import SBKubeConfig
```

## Docstring Convention

All public functions and classes MUST have docstrings:

```python
def deploy_application(app_name: str, namespace: str) -> bool:
    """애플리케이션을 Kubernetes 클러스터에 배포합니다.

    Args:
        app_name: 배포할 애플리케이션 이름
        namespace: 배포 대상 네임스페이스

    Returns:
        bool: 배포 성공 시 True, 실패 시 False

    Raises:
        DeploymentError: 배포 중 오류 발생 시
    """
```

## Error Handling

Use custom exceptions from [sbkube/exceptions.py](../../sbkube/exceptions.py):

```python
from sbkube.exceptions import SbkubeError

try:
    result = risky_operation()
except SbkubeError as e:
    console.print(f"[red]Error: {e}[/red]")
    raise
```

## Code Quality Tools

### Linting

```bash
# Check only
make lint-check

# Auto-fix
make lint-fix

# Strict mode
make lint-strict
```

### Type Checking

```bash
# Check all
uv run mypy sbkube/

# Check specific file
uv run mypy sbkube/commands/deploy.py
```

### Security Scanning

```bash
# Security check
uv run bandit -r sbkube/
```

## Pre-commit Hooks

```bash
# Install hooks
pre-commit install

# Run manually
pre-commit run --all-files
```

## Related Documents

- [Testing Guide](testing.md)
- [Architecture](../10-modules/sbkube/ARCHITECTURE.md)
- [Development Setup](README.md)
