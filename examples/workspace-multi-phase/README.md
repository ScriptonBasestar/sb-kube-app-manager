# Workspace Multi-Phase Deployment Example

This example demonstrates multi-phase deployment using the workspace feature.

## Overview

The workspace feature enables orchestrating multiple deployment phases with dependency ordering.
Each phase can target different app groups and has its own configuration.

## Directory Structure

```
workspace-multi-phase/
├── workspace.yaml         # Workspace orchestration config
├── p1-kube/               # Phase 1: Infrastructure
│   ├── sources.yaml
│   └── a000_network/
│       └── config.yaml
├── p2-kube/               # Phase 2: Data layer
│   ├── sources.yaml
│   └── a100_postgres/
│       └── config.yaml
├── p3-kube/               # Phase 3: Application
│   ├── sources.yaml
│   └── a200_backend/
│       └── config.yaml
└── p4-kube/               # Phase 4: Monitoring
    ├── sources.yaml
    └── a300_prometheus/
        └── config.yaml
```

## Phase Dependencies

```
p1-infra (Infrastructure)
    │
    ▼
p2-data (Database/Cache)
    │
    ▼
p3-app (Applications)
    │
    ▼
p4-monitoring (Observability)
```

## Usage

### Validate workspace configuration

```bash
sbkube workspace validate workspace.yaml
```

### View phase dependency graph

```bash
sbkube workspace graph workspace.yaml
```

### Deploy all phases (dry-run)

```bash
sbkube workspace deploy workspace.yaml --dry-run
```

### Deploy all phases

```bash
sbkube workspace deploy workspace.yaml
```

### Deploy specific phase only

```bash
sbkube workspace deploy workspace.yaml --phase p2-data --dry-run
```

### Check workspace status

```bash
sbkube workspace status workspace.yaml
```

### Parallel execution

```bash
# Execute independent phases in parallel
sbkube workspace deploy workspace.yaml --parallel --max-workers 4

# Execute app groups in parallel within each phase
sbkube workspace deploy workspace.yaml --parallel-apps --max-workers 8

# Full parallel (phases + app groups)
sbkube workspace deploy workspace.yaml --parallel --parallel-apps --max-workers 4
```

## Configuration Options

### Phase-level options

| Option | Description | Default |
|--------|-------------|---------|
| `source` | Path to sources.yaml for this phase | Required |
| `app_groups` | List of app groups to deploy | Required |
| `depends_on` | Phase dependencies (list) | `[]` |
| `app_group_deps` | Dependencies between app groups within this phase | `{}` |
| `timeout` | Phase timeout in seconds | Global default |
| `on_failure` | Failure behavior: stop, continue, rollback | Global default |
| `env` | Phase-level environment variables | `{}` |

### Global defaults

| Option | Description | Default |
|--------|-------------|---------|
| `kubeconfig` | Path to kubeconfig | `~/.kube/config` |
| `context` | Kubernetes context | Current context |
| `timeout` | Default timeout | `600` |
| `on_failure` | Default failure behavior | `stop` |
| `helm_repos` | Global Helm repositories | `{}` |

## Features

- **Dependency Resolution**: Phases execute in topological order (Kahn's algorithm)
- **Circular Dependency Detection**: Prevents invalid configurations
- **Failure Handling**: Configurable per-phase behavior on failure
- **Dry-Run Mode**: Test deployments without making changes
- **Single Phase Execution**: Deploy specific phases only
- **Parallel Phases**: Execute independent phases concurrently (`--parallel`)
- **Parallel App Groups**: Execute app groups in parallel within phases (`--parallel-apps`)
- **App Group Dependencies**: Define execution order within phases via `app_group_deps`
