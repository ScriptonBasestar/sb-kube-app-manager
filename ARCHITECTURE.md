# Architecture Overview - SBKube

> **Quick Reference**: High-level architecture for SBKube v0.11.0
>
> **상세 아키텍처**: [docs/10-modules/sbkube/ARCHITECTURE.md](docs/10-modules/sbkube/ARCHITECTURE.md)

---

## System Overview

```text
┌────────────────────────────────────────────────────────┐
│                   CLI Layer (cli.py)                    │
│   SbkubeGroup + main_with_exception_handling()         │
├────────────────────────────────────────────────────────┤
│ ┌───────────────┐ ┌──────────────┐ ┌──────────────┐   │
│ │   Commands    │ │    Models    │ │    State     │   │
│ │    Layer      │ │    Layer     │ │  Management  │   │
│ ├───────────────┤ ├──────────────┤ ├──────────────┤   │
│ │ • prepare     │ │ • Unified    │ │ • SQLAlchemy │   │
│ │ • build       │ │   Config     │ │ • Deployment │   │
│ │ • template    │ │ • SBKube     │ │   Tracking   │   │
│ │ • deploy      │ │   Config     │ │ • History    │   │
│ │ • apply       │ │ • Sources    │ │ • Rollback   │   │
│ │ • +11 more    │ │   Model      │ │              │   │
│ └───────────────┘ └──────────────┘ └──────────────┘   │
├────────────────────────────────────────────────────────┤
│ Utils (45 modules) │ Validators (7) │ Diagnostics     │
├────────────────────────────────────────────────────────┤
│              External Tools (Helm, kubectl, Git)       │
└────────────────────────────────────────────────────────┘
```

## Layer Summary

### 1. CLI Layer (`sbkube/cli.py`)

- **SbkubeGroup**: `click.Group` with categorized help display
- **Entry Point**: `main_with_exception_handling()` with auto-fix prompts
- **Categories**: 핵심 워크플로우 / 통합 명령어 / 상태 관리 / 업그레이드·삭제 / 유틸리티

### 2. Command Layer (`sbkube/commands/` — 16 commands)

- All commands inherit `EnhancedBaseCommand`
- Core workflow: `prepare → build → template → deploy`
- Unified: `apply` (4단계 자동 실행)
- State: `status`, `history`, `rollback`

### 3. Model Layer (`sbkube/models/` — 10 files)

- **UnifiedConfig** (`unified_config_model.py`): `sbkube.yaml` — recommended (v0.10.0+)
- **SBKubeConfig** (`config_model.py`): Legacy `config.yaml`
- **SourceScheme** (`sources_model.py`): Legacy `sources.yaml`
- 9 app types: `helm`, `yaml`, `git`, `http`, `action`, `exec`, `kustomize`, `oci`, `noop`

### 4. State Management (`sbkube/state/`)

- **Database**: SQLite at `~/.sbkube/deployments.db`
- **ORM**: SQLAlchemy 2.0.0+
- **Tracking**: Deployment → AppDeployment → DeployedResource / HelmRelease

### 5. Utilities (`sbkube/utils/` — 45 modules)

- Output: `OutputManager` + `OutputFormatter` (human/llm/json/yaml)
- Helm: `helm_util.py`, `helm_command_builder.py`
- Error handling: `error_classifier.py`, `error_suggestions.py`, `diagnostic_system.py`
- Retry, performance profiling, hooks, validation

### 6. Validators (`sbkube/validators/` — 7 files)

- Pre-deployment: cluster, namespace, RBAC, tools
- Post-deployment: pod status, service endpoints
- Environment: disk, network, CLI versions

## Design Patterns

| Pattern        | Implementation                                   |
| -------------- | ------------------------------------------------ |
| **Command**    | `EnhancedBaseCommand` — all CLI commands         |
| **Strategy**   | `OutputFormatter` — multi-format output          |
| **Observer**   | Hook system — pre/post workflow events           |
| **Repository** | `ConfigManager` — configuration access           |
| **Retry**      | Exponential backoff with jitter                  |
| **Hexagonal**  | Clean separation: domain ↔ infrastructure        |

## Exception Hierarchy

```text
SbkubeError (base)
├── ConfigurationError (ConfigFileNotFoundError, ConfigValidationError, ...)
├── ToolError (CliToolNotFoundError, CliToolExecutionError, CliToolVersionError)
├── KubernetesError (KubernetesConnectionError, KubernetesResourceError)
├── HelmError (HelmChartNotFoundError, HelmInstallationError)
├── GitError (GitRepositoryError)
├── FileSystemError (FileOperationError, DirectoryNotFoundError)
└── DeploymentError (RollbackError, DependencyError)
```

## Key Workflows

### Configuration Loading

```text
sbkube.yaml (Unified, v0.10.0+)
  or sources.yaml + config.yaml (Legacy)
    → ConfigManager (Pydantic validation)
    → Validated models
```

### Deployment Pipeline

```text
prepare → build → template → deploy
   ↓        ↓         ↓         ↓
소스준비  커스터마이징 템플릿화  클러스터배포
```

---

## Related Documents

- **상세 아키텍처**: [docs/10-modules/sbkube/ARCHITECTURE.md](docs/10-modules/sbkube/ARCHITECTURE.md)
- **기술 스택**: [TECH_STACK.md](TECH_STACK.md)
- **기술 명세**: [SPEC.md](SPEC.md) Section 2
- **API 참조**: [docs/10-modules/sbkube/API_CONTRACT.md](docs/10-modules/sbkube/API_CONTRACT.md)

---

**Document Version**: 3.0
**Last Updated**: 2026-02-25
**SBKube Version**: 0.11.0
