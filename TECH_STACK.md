# Technology Stack - SBKube

> **Quick Reference**: Technology overview for SBKube v0.9.1
>
> **For Detailed Setup**: See [Development Setup Guide](docs/04-development/README.md)

---

## Overview

SBKube is built with modern Python tooling, focusing on reliability, type safety, and developer experience.

## Core Technologies

### Language & Runtime
- **Python 3.12+** (required)
- **Type Hints**: Full type coverage with mypy strict mode
- **Async/Await**: Modern Python async patterns where applicable

### CLI Framework
- **Click 8.1+**: Command-line interface framework
  - Categorized help system
  - Rich parameter validation
  - Context management

### Configuration & Validation
- **Pydantic 2.7.1+**: Data validation and settings management
  - Strict type validation
  - JSON schema generation
  - Model inheritance for app types
- **PyYAML**: YAML parsing and generation
- **jsonschema 4.23.0+**: Schema validation

### Kubernetes & Helm
- **kubernetes 28.1.0+**: Official Kubernetes Python client
  - Cluster connectivity
  - Resource querying
  - Namespace management
- **Helm 3.x** (external): Chart management via subprocess
  - Repository management
  - Chart pulling and templating
  - Release deployment
- **kubectl** (external): Kubernetes CLI operations

### State Management
- **SQLAlchemy 2.0.0+**: Database ORM
  - Deployment history tracking
  - State persistence
  - Rollback support
- **Database**: SQLite (~/.sbkube/deployments.db)

### UI & Output
- **Rich**: Terminal output formatting
  - Color-coded console output
  - Progress bars and spinners
  - Table rendering
  - Tree visualization
- **OutputFormatter**: Custom LLM-friendly output system
  - Multiple formats: human, llm, json, yaml
  - 80-90% token reduction for AI agents

### Utilities
- **GitPython**: Git repository management
- **Jinja2**: Template rendering
- **requests 2.31.0+**: HTTP client for file downloads
- **packaging 25.0+**: Semantic version comparison (v0.9.1+)

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
- **testcontainers[k3s] 4.0.0+**: Integration testing with real clusters
- **faker 22.0.0+**: Test data generation

### Documentation
- **mdformat 0.7.22+**: Markdown formatter
- **Type stubs**: types-PyYAML, types-toml, types-requests

### Build & Package Management
- **uv**: Modern Python package manager (recommended)
  - Fast dependency resolution
  - Virtual environment management
  - Lock file support
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
- **kubectl**: Kubernetes CLI (tested with v1.28+)
- **helm**: Helm CLI (v3.x required)
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
- **Strategy Pattern**: Multiple output formats (OutputFormatter)
- **Observer Pattern**: Hook system for workflow events

### Key Components
- **CLI Layer**: Click-based commands (`sbkube/cli.py`)
- **Command Layer**: Business logic (`sbkube/commands/`)
- **Model Layer**: Pydantic models (`sbkube/models/`)
- **State Layer**: SQLAlchemy ORM (`sbkube/state/`)
- **Utilities**: Cross-cutting concerns (`sbkube/utils/`)
- **Validators**: Multi-layer validation (`sbkube/validators/`)

## Configuration Files

### Project Configuration
- `pyproject.toml`: Project metadata, dependencies, tool configuration
- `ruff.toml`: Linting and formatting rules
- `mypy.ini`: Type checking configuration (if exists)
- `.pre-commit-config.yaml`: Pre-commit hooks

### Runtime Configuration
- `sources.yaml`: Cluster and repository configuration
- `config.yaml`: Application definitions
- `workspace.yaml`: Multi-phase deployment orchestration (v0.9.0+)

## Version Compatibility

### Python Support
- **Minimum**: Python 3.12
- **Recommended**: Python 3.12 (latest stable)
- **Testing**: CI tested on Python 3.12

### Kubernetes Support
- **Minimum**: Kubernetes 1.24+
- **Recommended**: Kubernetes 1.28+
- **Tested**: k3s v1.28+, k3d, kind

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
- **Concurrent operations**: Parallel phase execution (v0.9.0+)
- **Database**: SQLite sufficient for single-user workflows

## Related Documentation

- **Detailed Setup**: [Development Environment](docs/04-development/README.md)
- **Coding Standards**: [Coding Standards](docs/04-development/coding-standards.md)
- **Testing Guide**: [Testing Documentation](docs/04-development/testing.md)
- **Architecture Details**: [ARCHITECTURE.md](ARCHITECTURE.md)
- **API Reference**: [API Contract](docs/10-modules/sbkube/API_CONTRACT.md)

---

**Document Version**: 1.0
**Last Updated**: 2025-12-01
**SBKube Version**: 0.9.1
