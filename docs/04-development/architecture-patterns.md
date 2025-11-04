---
type: Technical Documentation
audience: Developer
topics: [architecture, patterns, design, best-practices]
llm_priority: medium
last_updated: 2025-01-04
---

# Core Architecture Patterns

This document describes essential architectural patterns used in SBKube.

## Command Implementation Pattern

All commands inherit from `EnhancedBaseCommand` or `BaseCommand`:

```python
# sbkube/commands/my_command.py
from sbkube.utils.base_command import EnhancedBaseCommand

class MyCommand(EnhancedBaseCommand):
    def __init__(self, base_dir: str, app_config_dir: str, ...):
        super().__init__(base_dir, app_config_dir, ...)
        # Additional initialization

    def execute(self):
        """명령어 실행 로직"""
        self.load_configuration()  # 설정 로딩
        self.validate()            # 검증
        # 실제 작업 수행
        return result
```

### CLI Registration

Register commands in [sbkube/cli.py](../../sbkube/cli.py):

```python
@click.command()
@click.option("--base-dir", default=".", help="Base directory")
def my_command(base_dir: str):
    """명령어 설명"""
    cmd = MyCommand(base_dir=base_dir)
    cmd.execute()
```

### Command Categories

New commands must be added to appropriate category in `SbkubeGroup.COMMAND_CATEGORIES`:

```python
# sbkube/cli.py
class SbkubeGroup(click.Group):
    COMMAND_CATEGORIES = {
        "핵심 워크플로우": ["prepare", "build", "template", "deploy"],
        "통합 명령어": ["apply"],
        "상태 관리": ["status", "history", "rollback"],
        "업그레이드/삭제": ["upgrade", "delete"],
        "유틸리티": ["init", "validate", "doctor", "version"],
    }
```

## Configuration Model Pattern

Use Pydantic for strong-typed configuration validation:

```python
# sbkube/models/config_model.py
from pydantic import BaseModel, Field

class AppConfig(BaseModel):
    name: str = Field(..., description="App name")
    type: str = Field(..., pattern="^(helm|yaml|git|http|action|exec)$")
    enabled: bool = True
    specs: dict = Field(default_factory=dict)

class SBKubeConfig(BaseModel):
    namespace: str
    apps: list[AppConfig]
```

### Configuration Loading

```python
# Automatic validation with EnhancedBaseCommand
cmd = MyCommand(base_dir=".", validate_on_load=True)
# config_manager handles validation automatically
```

## State Management Pattern

Use SQLAlchemy for deployment history tracking:

```python
# sbkube/state/tracker.py
from sbkube.state.database import DeploymentState

def track_deployment(app_name: str, namespace: str, status: str):
    state = DeploymentState(
        app_name=app_name,
        namespace=namespace,
        status=status
    )
    session.add(state)
    session.commit()
```

### State Database

- Location: `~/.sbkube/deployments.db`
- Schema: See [sbkube/state/database.py](../../sbkube/state/database.py)
- Rollback: Supported via `sbkube rollback` command

## Key Utility Modules

### Helm Operations

[sbkube/utils/helm_util.py](../../sbkube/utils/helm_util.py) - Helm CLI wrapper

```python
from sbkube.utils.helm_util import HelmUtil

helm = HelmUtil()
helm.install_release(name="my-app", chart="./charts/app", namespace="prod")
```

### Logging

[sbkube/utils/logger.py](../../sbkube/utils/logger.py) - Rich Console logging

```python
from sbkube.utils.logger import console

console.print("[green]✅ Success[/green]")
console.print("[red]❌ Error[/red]")
console.print("[yellow]⚠️  Warning[/yellow]")
```

### Validation System

[sbkube/utils/validation_system.py](../../sbkube/utils/validation_system.py) - Integrated validation

```python
from sbkube.utils.validation_system import ValidationSystem

validator = ValidationSystem()
result = validator.validate_config(config_path)
```

### Configuration Manager

[sbkube/models/config_manager.py](../../sbkube/models/config_manager.py) - Config inheritance

```python
from sbkube.models.config_manager import ConfigManager

manager = ConfigManager(base_dir=".", schema_dir="./schemas")
config = manager.load_config("config.yaml")
```

## Rich Console Pattern

All user-facing output uses Rich for consistent formatting:

```python
from sbkube.utils.logger import console
from rich.table import Table

# Simple output
console.print("[green]Deployment successful[/green]")

# Tables
table = Table(title="Applications")
table.add_column("Name")
table.add_column("Status")
table.add_row("app1", "✅ Running")
console.print(table)
```

## Related Documents

- [ARCHITECTURE.md](../10-modules/sbkube/ARCHITECTURE.md) - Full architecture documentation
- [API Contract](../10-modules/sbkube/API_CONTRACT.md) - API specifications
- [Coding Standards](coding-standards.md) - Code style guide
