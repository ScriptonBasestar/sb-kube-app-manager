# Architecture Overview - SBKube

> **Quick Reference**: High-level architecture for SBKube v0.9.1
>
> **For Complete Details**: See [SPEC.md](SPEC.md) Section 2 and [System Design](docs/20-architecture/system-design.md) (if exists)

---

## System Overview

SBKube is a **monolithic Python CLI application** that orchestrates Kubernetes deployments through a four-stage workflow: prepare → build → template → deploy.

### Core Architecture

```
┌─────────────────────────────────────────────────────────────┐
│                      SBKube CLI                             │
│               (Click Framework)                             │
└───────────────────────┬─────────────────────────────────────┘
                        │
        ┌───────────────┼───────────────┐
        ▼               ▼               ▼
┌───────────────┐ ┌──────────────┐ ┌──────────────┐
│   Commands    │ │    Models    │ │    State     │
│    Layer      │ │    Layer     │ │  Management  │
├───────────────┤ ├──────────────┤ ├──────────────┤
│ • prepare     │ │ • ConfigModel│ │ • SQLAlchemy │
│ • build       │ │ • SourcesModel│ │ • Tracker   │
│ • template    │ │ • Pydantic   │ │ • History    │
│ • deploy      │ │   Validators │ │ • Rollback   │
│ • apply       │ │              │ │              │
│ • status      │ │              │ │              │
└───────┬───────┘ └──────┬───────┘ └──────┬───────┘
        │                │                │
        └────────────────┼────────────────┘
                         ▼
              ┌──────────────────┐
              │  Utils & Helpers │
              ├──────────────────┤
              │ • helm_util      │
              │ • logger         │
              │ • file_loader    │
              │ • output_formatter│
              └─────────┬────────┘
                        │
        ┌───────────────┼───────────────┐
        ▼               ▼               ▼
┌──────────────┐ ┌─────────────┐ ┌──────────────┐
│   Helm CLI   │ │   kubectl   │ │   Git CLI    │
│   (v3.x)     │ │             │ │              │
└──────────────┘ └─────────────┘ └──────────────┘
        │               │               │
        └───────────────┼───────────────┘
                        ▼
               ┌────────────────┐
               │  Kubernetes    │
               │   Cluster      │
               └────────────────┘
```

---

## Key Components

### 1. CLI Layer (`sbkube/cli.py`)
- **Framework**: Click 8.1+
- **Responsibility**: Command registration, global options, help system
- **Pattern**: Command group with categorization

### 2. Commands Layer (`sbkube/commands/`)
All commands inherit from `EnhancedBaseCommand`:
- **Core Workflow**: prepare, build, template, deploy, apply
- **State Management**: status, history, rollback
- **Utilities**: init, validate, doctor, version
- **Management**: upgrade, delete, check-updates (v0.9.1+)
- **Workspace**: workspace validate/deploy/status/graph/history (v0.9.0+)

### 3. Models Layer (`sbkube/models/`)
- **Pydantic 2.7.1+**: Strict type validation
- **Config Models**: SBKubeConfig, AppConfig, HelmApp, YamlApp, etc.
- **Sources Models**: SourceScheme, HelmSource, GitSource
- **Workspace Models**: WorkspaceConfig, PhaseConfig (v0.9.0+)
- **Validation**: Automatic validation on model instantiation

### 4. State Management (`sbkube/state/`)
- **Database**: SQLite at `~/.sbkube/deployments.db`
- **ORM**: SQLAlchemy 2.0.0+
- **Models**: DeploymentState, AppState, RollbackPoint
- **Tracker**: StateTracker for deployment history
- **Rollback**: Snapshot-based rollback support

### 5. Utilities (`sbkube/utils/`)
- **BaseCommand**: EnhancedBaseCommand for command inheritance
- **Logger**: Rich console logging with color coding
- **HelmUtil**: Helm CLI interactions (chart download, install, query)
- **FileLoader**: Configuration and template file loading
- **OutputFormatter**: Multi-format output (human, llm, json, yaml)
- **VersionCompare**: Semantic version comparison (v0.9.1+)

### 6. Validators (`sbkube/validators/`)
- **ConfigValidator**: Configuration file validation
- **DependencyValidator**: App dependency graph validation
- **EnvironmentValidator**: System requirements check
- **StorageValidator**: PV/PVC validation (v0.8.0+)

---

## Architecture Patterns

### Design Patterns

#### 1. **Command Pattern**
All CLI commands implement a consistent interface through `EnhancedBaseCommand`:
```python
class EnhancedBaseCommand:
    def __init__(self, base_dir, app_config_dir, output_format):
        self.BASE_DIR = base_dir
        self.APP_CONFIG_DIR = app_config_dir
        self.formatter = OutputFormatter(output_format)
        self.config_manager = ConfigManager(...)
        self.hook_executor = HookExecutor(...)
```

#### 2. **Repository Pattern**
`ConfigManager` abstracts configuration access:
- Hierarchical configuration loading
- Profile-based inheritance
- Validation on load

#### 3. **Strategy Pattern**
`OutputFormatter` supports multiple output formats:
- Human: Rich console output (default)
- LLM: Token-optimized text (80-90% reduction)
- JSON: Structured data
- YAML: YAML format

#### 4. **Observer Pattern**
Hooks system for workflow events:
- pre_deploy, post_deploy, on_failure
- Global and app-level hooks
- Inline commands and script files

#### 5. **Dependency Injection**
Commands receive dependencies via constructor:
- OutputFormatter for consistent output
- ConfigManager for configuration
- HookExecutor for hook execution

### Hexagonal Architecture Principles

```
┌─────────────────────────────────────────┐
│            CLI Interface                │  ← Adapters (Click commands)
├─────────────────────────────────────────┤
│         Application Core                │
│  ┌─────────────────────────────────┐   │
│  │   Commands (Use Cases)          │   │  ← Business Logic
│  │   • apply, deploy, status       │   │
│  └─────────────────────────────────┘   │
│  ┌─────────────────────────────────┐   │
│  │   Models (Domain)               │   │  ← Domain Models
│  │   • AppConfig, SourceScheme     │   │
│  └─────────────────────────────────┘   │
├─────────────────────────────────────────┤
│          Infrastructure                 │
│  • Helm CLI (subprocess)                │  ← Ports
│  • kubectl CLI (subprocess)             │
│  • SQLAlchemy (database)                │
│  • File I/O                             │
└─────────────────────────────────────────┘
```

**Benefits:**
- Business logic isolated from external dependencies
- Easy to test (mock external dependencies)
- Flexible infrastructure (can swap Helm for alternative)

---

## Data Flow

### 1. Configuration Loading
```
sources.yaml + config.yaml + config-{profile}.yaml
         ↓
    ConfigManager (Pydantic validation)
         ↓
   SBKubeConfig (validated model)
```

### 2. Deployment Workflow
```
User Command (sbkube apply)
         ↓
    CLI Layer (Click)
         ↓
  ApplyCommand (prepare → build → template → deploy)
         ↓
   ┌─────────┬─────────┬──────────┬─────────┐
   ▼         ▼         ▼          ▼         ▼
prepare   build   template   deploy   hooks
   │         │         │          │         │
   └─────────┴─────────┴──────────┴─────────┘
                  ↓
           StateTracker (SQLite)
                  ↓
         Kubernetes Cluster
```

### 3. State Management
```
Deployment Start
    ↓
StateTracker.start_deployment()
    ↓
For each app:
    ↓
StateTracker.update_app_status()
    ↓
StateTracker.complete_deployment()
    ↓
Database Persistence (~/.sbkube/deployments.db)
```

---

## Module Structure

```
sbkube/
├── cli.py                    # CLI entry point
├── commands/                 # Command implementations
│   ├── apply.py             # Unified workflow
│   ├── prepare.py           # Source preparation
│   ├── build.py             # App building
│   ├── template.py          # Manifest rendering
│   ├── deploy.py            # Deployment execution
│   ├── status.py            # Status queries
│   ├── history.py           # History management
│   ├── rollback.py          # Rollback operations
│   ├── validate.py          # Configuration validation
│   ├── check_updates.py     # Update checking (v0.9.1+)
│   └── workspace.py         # Workspace commands (v0.9.0+)
├── models/                  # Data models
│   ├── config_model.py      # config.yaml models
│   ├── sources_model.py     # sources.yaml models
│   ├── workspace_model.py   # workspace.yaml models (v0.9.0+)
│   └── config_manager.py    # Configuration management
├── state/                   # State management
│   ├── database.py          # SQLAlchemy setup
│   ├── tracker.py           # Deployment tracking
│   └── models.py            # State models
├── utils/                   # Utilities
│   ├── base_command.py      # Command base class
│   ├── logger.py            # Rich logging
│   ├── helm_util.py         # Helm utilities
│   ├── file_loader.py       # File loading
│   ├── output_formatter.py  # Output formatting
│   ├── version_compare.py   # Version comparison (v0.9.1+)
│   └── hook_executor.py     # Hook execution
└── validators/              # Validation system
    ├── basic_validators.py
    ├── dependency_validators.py
    ├── environment_validators.py
    └── storage_validators.py
```

---

## Key Design Decisions

### 1. **Monolithic CLI vs. Microservices**
- **Choice**: Monolithic CLI
- **Rationale**: Single-user workflows, no concurrency needs, simpler deployment
- **Trade-off**: Not suitable for multi-tenant scenarios (future: API server mode)

### 2. **SQLite vs. Cloud Database**
- **Choice**: SQLite (~/.sbkube/deployments.db)
- **Rationale**: Local state, no external dependencies, simple backup
- **Trade-off**: Single-user only (future: PostgreSQL for multi-user)

### 3. **Subprocess vs. SDK**
- **Choice**: Subprocess calls to Helm/kubectl
- **Rationale**: Leverage existing CLI tools, avoid SDK version conflicts
- **Trade-off**: Slower than native SDKs, parsing output complexity

### 4. **Pydantic vs. Dataclasses**
- **Choice**: Pydantic 2.7.1+
- **Rationale**: Automatic validation, JSON schema generation, type coercion
- **Trade-off**: Heavier dependency, learning curve

### 5. **Click vs. argparse**
- **Choice**: Click 8.1+
- **Rationale**: Better UX (help formatting, colors), plugin system, decorator syntax
- **Trade-off**: External dependency (not stdlib)

---

## Scalability Considerations

### Current Limits
- **Apps per deployment**: Tested with 50+ apps
- **Concurrent users**: Single-user (SQLite limitation)
- **Cluster size**: Tested with small k3s clusters

### Future Enhancements (v1.0+)
- **API Server Mode**: REST API for remote management
- **PostgreSQL Support**: Multi-user state management
- **Kubernetes Operator**: Native Kubernetes controller
- **Distributed Locks**: Prevent concurrent deployment conflicts

---

## Security Architecture

### 1. **Credentials Management**
- Uses existing kubeconfig (no custom auth)
- Respects KUBECONFIG environment variable
- Supports context switching

### 2. **Input Validation**
- Pydantic for schema validation
- Path traversal prevention
- Command injection prevention (no shell=True)

### 3. **State Isolation**
- Per-user SQLite database (~/.sbkube/)
- File permissions (user-only access)

### 4. **Secrets Handling**
- No secret storage (relies on Kubernetes secrets)
- Helm values files can reference secrets
- Future: Sealed Secrets, Vault integration

---

## Related Documentation

- **Complete Specification**: [SPEC.md](SPEC.md) - Comprehensive technical details
- **Module Details**: [docs/10-modules/sbkube/](docs/10-modules/sbkube/)
- **API Contract**: [docs/10-modules/sbkube/API_CONTRACT.md](docs/10-modules/sbkube/API_CONTRACT.md)
- **Development Guide**: [docs/04-development/](docs/04-development/)
- **Technology Stack**: [TECH_STACK.md](TECH_STACK.md)

---

**Document Version**: 1.0
**Last Updated**: 2025-12-01
**SBKube Version**: 0.9.1
