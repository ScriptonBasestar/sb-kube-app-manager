# Technology Stack - SBKube

> **Quick Reference**: Technology overview for SBKube v0.11.0
>
> **For Detailed Setup**: See [Development Setup Guide](docs/04-development/README.md)

---

## Overview

SBKube is built with modern Python tooling, focusing on reliability, type safety, and developer experience.

## Core Technologies

### Language & Runtime
- **Python 3.14+** (required)
- **Type Hints**: Full type coverage with mypy strict mode
- **Async/Await**: Modern Python async patterns where applicable

### CLI Framework
- **Click 8.1+**: Command-line interface framework
  - `SbkubeGroup`: Custom click.Group with categorized help display
  - Rich parameter validation
  - Context management
  - Global exception handling with auto-fix prompts

### Configuration & Validation
- **Pydantic 2.11+**: Data validation and settings management
  - Strict type validation (`extra="forbid"`)
  - JSON schema generation
  - Model inheritance for app types
  - Discriminated unions for type-safe app configs
- **PyYAML**: YAML parsing and generation
- **jsonschema 4.23.0+**: Schema validation
- **Jinja2**: Template rendering

### Kubernetes & Helm
- **kubernetes 32.0.0+**: Official Kubernetes Python client
  - Cluster connectivity
  - Resource querying
  - Namespace management
- **Helm 4.x** (external): Chart management via subprocess
  - Repository management (including OCI registries)
  - Chart pulling and templating
  - Release deployment
  - Retry with exponential backoff
- **kubectl** (external): Kubernetes CLI operations

### State Management
- **SQLAlchemy 2.0.0+**: Database ORM
  - Deployment history tracking (`Deployment`, `AppDeployment`)
  - Resource tracking (`DeployedResource`, `HelmRelease`)
  - Workspace tracking (`WorkspaceDeployment`, `PhaseDeployment`)
  - Rollback support
- **Database**: SQLite (~/.sbkube/deployments.db)

### UI & Output
- **Rich**: Terminal output formatting
  - Color-coded console output
  - Progress bars and spinners
  - Table rendering
  - Tree visualization
- **OutputManager**: Unified output lifecycle management
  - Event collection → structured final output
  - Format-aware output (human = immediate, LLM/JSON/YAML = collected + finalized)
- **OutputFormatter**: Multi-format output strategy
  - Multiple formats: human, llm, json, yaml
  - 80-90% token reduction for AI agents

### Utilities
- **GitPython**: Git repository management
- **requests 2.32.0+**: HTTP client for file downloads
- **packaging 25.0+**: Semantic version comparison
- **toml 0.10.2+**: TOML configuration parsing

## Development Tools

### Code Quality
- **ruff 0.7.0+**: Fast Python linter and formatter
  - Replaces flake8, black, isort
  - pyupgrade integration
- **mypy 1.13.0+**: Static type checker
  - Strict mode enabled
  - Full type coverage
- **bandit 1.8.6+**: Security linter
  - Excludes tests and examples

### Testing
- **pytest 8.3.5+**: Test framework
  - Unit, integration, e2e, performance tests
  - Fixtures and parametrization
- **pytest-cov 4.1.0+**: Coverage reporting
  - Branch coverage enabled
  - HTML reports
- **pytest-xdist 3.5.0+**: Parallel test execution
- **pytest-mock 3.12.0+**: Mocking utilities
- **pytest-benchmark 4.0.0+**: Performance benchmarks
- **pytest-timeout 2.2.0+**: Test timeout enforcement
- **pytest-asyncio 0.23.0+**: Async test support
- **testcontainers[k3s] 4.0.0+**: Integration testing with real clusters
- **faker 22.0.0+**: Test data generation

### Documentation
- **mdformat 0.7.22+**: Markdown formatter
- **Type stubs**: types-PyYAML, types-toml, types-requests

### Build & Package Management
- **uv**: Modern Python package manager (**mandatory** — no pip, no requirements.txt)
  - Fast dependency resolution
  - Virtual environment management
  - Lock file support (`uv.lock`)
- **hatchling**: Build backend
  - Modern pyproject.toml-based builds
- **twine 6.1.0+**: PyPI package upload

### Version Control
- **pre-commit 4.0.0+**: Git hooks framework
  - Automatic code formatting
  - Linting on commit
  - Type checking

## External Dependencies

### Required System Tools
- **kubectl**: Kubernetes CLI (tested with v1.32+)
- **helm**: Helm CLI (v4.x required)
- **git**: Version control

### Optional Tools
- **k3s/k3d**: Lightweight Kubernetes (recommended for development)
- **kind**: Kubernetes in Docker (alternative)
- **minikube**: Local Kubernetes (alternative)

## Architecture Patterns

### Design Principles
- **Hexagonal Architecture**: Clean separation of concerns
- **Command Pattern**: EnhancedBaseCommand for all CLI commands
- **Repository Pattern**: ConfigManager for configuration access
- **Strategy Pattern**: OutputFormatter + OutputManager for output
- **Observer Pattern**: Hook system for workflow events
- **Retry Pattern**: Exponential backoff with jitter for external tool calls
- **Error Classification**: Three-tier error handling (classify → suggest → format)

### Key Components
- **CLI Layer**: Click-based commands with SbkubeGroup (`sbkube/cli.py`)
- **Command Layer**: Business logic (`sbkube/commands/` — 16 commands)
- **Model Layer**: Pydantic models (`sbkube/models/` — 10 files, 9 app types)
- **State Layer**: SQLAlchemy ORM (`sbkube/state/` — 5 files)
- **Utilities**: Cross-cutting concerns (`sbkube/utils/` — 45 modules)
- **Validators**: Multi-layer validation (`sbkube/validators/` — 7 files)
- **Diagnostics**: Runtime checks (`sbkube/diagnostics/`)
- **Exceptions**: Comprehensive hierarchy (`sbkube/exceptions.py` — 20+ types)

## Configuration Files

### Project Configuration
- `pyproject.toml`: Project metadata, dependencies, tool configuration
- `ruff.toml`: Linting and formatting rules
- `mypy.ini`: Type checking configuration
- `.pre-commit-config.yaml`: Pre-commit hooks
- `pytest.ini`: Test configuration and markers

### Runtime Configuration
- `sbkube.yaml`: Unified config (v0.10.0+ — **recommended**)
  - `apiVersion: sbkube/v1`
  - Consolidates settings, apps, and phases in a single file
- `sources.yaml` + `config.yaml`: Legacy split configuration (backward compatible)

## Version Compatibility

### Python Support
- **Minimum**: Python 3.14
- **Recommended**: Python 3.14 (latest stable)
- **Testing**: CI tested on Python 3.14

### Kubernetes Support
- **Minimum**: Kubernetes 1.28+
- **Recommended**: Kubernetes 1.32+
- **Tested**: k3s v1.32+, k3d, kind

### Operating Systems
- **Primary**: Linux (POSIX)
- **Testing**: Manjaro, Ubuntu, Debian-based distributions
- **Development**: Full support on Linux

## Performance Characteristics

### Resource Usage

- **Memory**: ~50-100 MB typical usage
- **Disk**: SQLite database (<10 MB for typical deployments)
- **Network**: Minimal (Helm repo queries, chart downloads)

### Scalability

- **Apps per deployment**: Tested with 50+ apps
- **Concurrent operations**: Parallel phase execution (workspace mode)
- **Database**: SQLite sufficient for single-user workflows

### Profiling

- **Built-in**: `SBKUBE_PERF=1` enables subprocess timing and summary
- **Output**: JSONL event log at `tmp/perf/`

## Licenses

All dependencies use permissive licenses compatible with SBKube's MIT license:

| Package | License |
|---------|---------|
| click | BSD-3-Clause |
| pyyaml | MIT |
| pydantic | MIT |
| rich | MIT |
| sqlalchemy | MIT |
| requests | Apache-2.0 |
| gitpython | BSD-3-Clause |
| jinja2 | BSD-3-Clause |

## Dependency Troubleshooting

### Pydantic v1/v2 Conflict

**Symptom**: `ImportError: cannot import name 'BaseModel' from 'pydantic'`

```bash
uv pip install "pydantic>=2.11"
```

### SQLAlchemy 2.0 Migration

**Symptom**: `AttributeError: 'Engine' object has no attribute 'execute'`

```bash
uv pip install "sqlalchemy>=2.0.40"
```

### macOS ARM64 (Apple Silicon)

```bash
arch -arm64 uv pip install sbkube
```

### Linux Alpine (musl libc)

```bash
apk add gcc musl-dev python3-dev libffi-dev openssl-dev
```

## Related Documentation

- **Detailed Setup**: [Development Environment](docs/04-development/README.md)
- **Coding Standards**: [Coding Standards](docs/04-development/coding-standards.md)
- **Testing Guide**: [Testing Documentation](docs/04-development/testing.md)
- **Architecture Details**: [ARCHITECTURE.md](ARCHITECTURE.md)
- **API Reference**: [API Contract](docs/10-modules/sbkube/API_CONTRACT.md)

---

**Document Version**: 3.0
**Last Updated**: 2026-02-25
**SBKube Version**: 0.11.0
