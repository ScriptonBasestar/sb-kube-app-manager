______________________________________________________________________

## type: User Guide audience: End User topics: [workspace, multi-phase, deployment, orchestration] llm_priority: medium last_updated: 2025-11-25

# SBKube Workspace Guide

> **주의**: 이 기능은 v0.9.1 Preview 상태입니다. 프로덕션 사용 전 충분히 테스트하세요.

Workspace enables multi-phase deployment orchestration for complex Kubernetes environments. Deploy infrastructure,
data layers, and applications in proper dependency order with a single command.

## TL;DR

- **Purpose**: Orchestrate multi-phase deployments with dependency ordering
- **Version**: v0.9.1 (Preview)
- **Key Commands**: `workspace validate`, `workspace graph`, `workspace deploy`, `workspace status`
- **Config File**: `workspace.yaml`
- **Related**:
  - **상위 문서**: [SPEC.md](../../SPEC.md) - 기술 명세
  - **스키마 참조**: [workspace-schema.md](../03-configuration/workspace-schema.md)
  - **예제**: [examples/workspace-multi-phase/](../../examples/workspace-multi-phase/)

## Overview

### Problem: Complex Multi-Phase Deployments

Large Kubernetes deployments often require ordered phases:

```
1. Infrastructure (networking, storage)
       ↓
2. Data Layer (databases, caches)
       ↓
3. Applications (backends, frontends)
       ↓
4. Monitoring (Prometheus, Grafana)
```

Managing this manually is error-prone and time-consuming.

### Solution: Workspace Orchestration

Workspace provides:

- **Dependency Resolution**: Automatic topological sorting of phases
- **Validation**: Pre-deployment configuration verification
- **Failure Handling**: Configurable behavior on errors
- **Dry-Run Mode**: Test deployments without making changes

## Quick Start

### 1. Create workspace.yaml

```yaml
version: "1.0"

metadata:
  name: my-deployment
  environment: prod

phases:
  p1-infra:
    description: "Infrastructure"
    source: p1-kube/sources.yaml
    app_groups:
      - a000_network

  p2-data:
    description: "Data layer"
    source: p2-kube/sources.yaml
    app_groups:
      - a100_postgres
    depends_on:
      - p1-infra
```

### 2. Validate Configuration

```bash
sbkube workspace validate workspace.yaml
```

### 3. View Dependency Graph

```bash
sbkube workspace graph workspace.yaml
```

### 4. Deploy (Dry-Run First)

```bash
sbkube workspace deploy workspace.yaml --dry-run
sbkube workspace deploy workspace.yaml
```

## Commands Reference

### workspace validate

Validate workspace.yaml configuration.

```bash
sbkube workspace validate workspace.yaml
```

**Checks**:
- YAML syntax
- Schema validation (Pydantic)
- Phase dependency validation
- Circular dependency detection

### workspace graph

Display phase dependency graph.

```bash
sbkube workspace graph workspace.yaml
```

**Output Example**:
```
Phase Dependency Graph
======================
p1-infra (Infrastructure)
├── p2-data (Data layer)
│   └── p3-app (Applications)
│       └── p4-monitoring (Monitoring)
```

### workspace deploy

Execute multi-phase deployment.

```bash
# Deploy all phases
sbkube workspace deploy workspace.yaml

# Dry-run mode
sbkube workspace deploy workspace.yaml --dry-run

# Deploy specific phase only
sbkube workspace deploy workspace.yaml --phase p2-data

# Force deployment (skip state checks)
sbkube workspace deploy workspace.yaml --force

# Skip validation
sbkube workspace deploy workspace.yaml --skip-validation

# Parallel phase execution
sbkube workspace deploy workspace.yaml --parallel --max-workers 4

# Parallel app-group execution within phases
sbkube workspace deploy workspace.yaml --parallel-apps --max-workers 8

# Full parallel (phases + app-groups)
sbkube workspace deploy workspace.yaml --parallel --parallel-apps --max-workers 4
```

**Options**:
| Option | Description |
|--------|-------------|
| `--dry-run` | Simulate deployment without making changes |
| `--phase <name>` | Deploy only the specified phase |
| `--force` | Force deployment, ignoring previous state |
| `--skip-validation` | Skip sources.yaml file existence check |
| `--parallel` | Execute independent phases in parallel |
| `--parallel-apps` | Execute app groups in parallel within each phase |
| `--max-workers <n>` | Maximum parallel workers (default: 4) |

### workspace status

Display workspace configuration overview.

```bash
sbkube workspace status workspace.yaml
```

**Shows**:
- Metadata (name, environment, tags)
- Global configuration
- Phase summary with dependencies

### workspace init

Create workspace.yaml template.

```bash
sbkube workspace init workspace.yaml
sbkube workspace init workspace.yaml --non-interactive
```

## Configuration Reference

### workspace.yaml Structure

```yaml
version: "1.0"  # Required: Schema version

metadata:       # Required: Workspace metadata
  name: string          # Required: Workspace name
  description: string   # Optional
  environment: string   # Optional: dev, staging, prod
  tags: [string]        # Optional

global:         # Optional: Global defaults
  kubeconfig: string    # Path to kubeconfig
  context: string       # Kubernetes context
  timeout: int          # Default timeout (seconds)
  on_failure: string    # stop | continue | rollback
  helm_repos: {}        # Global Helm repos

phases:         # Required: Phase definitions
  phase-name:
    description: string     # Required
    source: string          # Required: Path to sources.yaml
    app_groups: [string]    # Required: App groups to deploy
    depends_on: [string]    # Optional: Phase dependencies
    app_group_deps: {}      # Optional: Dependencies between app groups
    timeout: int            # Optional: Phase-specific timeout
    on_failure: string      # Optional: Phase-specific behavior
    env: {}                 # Optional: Environment variables
```

### Phase Dependencies

Phases execute in topological order based on `depends_on`:

```yaml
phases:
  p1-infra:
    # No dependencies - executes first
    app_groups: [a000_network]

  p2-data:
    depends_on: [p1-infra]  # Waits for p1-infra
    app_groups: [a100_postgres]

  p3-app:
    depends_on: [p2-data]   # Waits for p2-data
    app_groups: [a200_backend]
```

**Execution order**: p1-infra → p2-data → p3-app

### Parallel Execution

Workspace supports two levels of parallel execution:

#### Phase-Level Parallelism (`--parallel`)

Independent phases (no mutual dependencies) execute concurrently:

```yaml
phases:
  p1-infra:
    app_groups: [network]
  p2-monitoring:        # Independent of p1
    app_groups: [prometheus]
  p3-app:
    depends_on: [p1-infra]  # Waits for p1
```

With `--parallel`, p1-infra and p2-monitoring run simultaneously.

#### App-Group Parallelism (`--parallel-apps`)

Within a phase, app groups can run in parallel based on `app_group_deps`:

```yaml
phases:
  p1-infra:
    app_groups:
      - network
      - storage
      - database
      - cache
    app_group_deps:
      storage: [network]      # storage depends on network
      database: [storage]     # database depends on storage
      cache: [network]        # cache depends on network (not storage)
```

**Execution with `--parallel-apps`**:
```
Level 0: network          ← runs first
Level 1: storage, cache   ← run in parallel (both depend on network)
Level 2: database         ← runs last (depends on storage)
```

Groups without dependencies run in the first level. Groups at the same level can run concurrently.

#### Combined Parallelism

Use both options for maximum parallelism:

```bash
sbkube workspace deploy workspace.yaml --parallel --parallel-apps --max-workers 8
```

This executes independent phases in parallel, and within each phase, executes app groups in parallel based on their dependencies.

### Failure Handling

Configure behavior when deployment fails:

| Mode | Description |
|------|-------------|
| `stop` | Stop all deployments immediately (default) |
| `continue` | Continue with remaining phases |
| `rollback` | Attempt rollback of failed phase |

```yaml
global:
  on_failure: stop  # Global default

phases:
  p3-app:
    on_failure: continue  # Override for this phase
```

## Directory Structure

Recommended workspace directory structure:

```
my-workspace/
├── workspace.yaml          # Workspace orchestration
├── p1-kube/                # Phase 1
│   ├── sources.yaml
│   └── a000_network/
│       └── config.yaml
├── p2-kube/                # Phase 2
│   ├── sources.yaml
│   └── a100_postgres/
│       └── config.yaml
└── p3-kube/                # Phase 3
    ├── sources.yaml
    └── a200_backend/
        └── config.yaml
```

## Best Practices

### 1. Use Meaningful Phase Names

```yaml
# Good
phases:
  p1-infrastructure:
  p2-data-layer:
  p3-applications:

# Avoid
phases:
  phase1:
  phase2:
```

### 2. Keep Phases Focused

Each phase should have a clear, single responsibility:
- Infrastructure: networking, storage
- Data: databases, caches, message queues
- Applications: backends, frontends, workers
- Monitoring: observability, alerting

### 3. Always Dry-Run First

```bash
# Test deployment plan
sbkube workspace deploy workspace.yaml --dry-run

# Then execute
sbkube workspace deploy workspace.yaml
```

### 4. Use Environment Variables for Secrets

```yaml
phases:
  p2-data:
    env:
      DB_PASSWORD: "${DB_PASSWORD}"
```

### 5. Document Phase Dependencies

```yaml
phases:
  p3-app:
    description: |
      Application services.
      Depends on p2-data for database connectivity.
    depends_on: [p2-data]
```

## Troubleshooting

### Circular Dependency Detected

**Error**: `Circular dependency detected involving phase 'p2-data'`

**Cause**: Phases depend on each other in a cycle.

**Solution**: Review `depends_on` fields and remove circular references.

### Phase Not Found

**Error**: `Phase 'p2-data' depends on non-existent phase 'p1-infra'`

**Cause**: Typo in `depends_on` or missing phase definition.

**Solution**: Check phase names match exactly.

### Sources File Not Found

**Error**: `sources.yaml not found at p1-kube/sources.yaml`

**Cause**: The `source` path is incorrect.

**Solution**:
1. Verify path is relative to workspace.yaml location
2. Use `--skip-validation` if files will be created later

## Limitations

- **v0.9.1 Preview**: API may change before stable release
- **Single Cluster**: Currently supports one cluster per workspace
- **No State Persistence**: Deployment history not yet tracked in database
- **Parallel Execution**: Requires careful dependency configuration to avoid race conditions

## See Also

- [Workspace Schema Reference](../03-configuration/workspace-schema.md)
- [Workspace Example](../../examples/workspace-multi-phase/)
- [Commands Reference](commands.md)
- [SPEC.md](../../SPEC.md) - Technical specification
