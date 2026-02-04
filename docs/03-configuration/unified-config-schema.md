______________________________________________________________________

## type: API Reference audience: End User topics: [configuration, unified-config, sbkube-yaml] llm_priority: high last_updated: 2025-02-04

# 📋 Unified Configuration Schema (v0.10.0+)

> **SBKube v0.10.0+** introduces a unified configuration format (`sbkube.yaml`) that replaces the previous
> multi-file configuration approach (`sources.yaml` + `config.yaml`).

## TL;DR

- **Purpose**: Single-file configuration for all deployment settings
- **Version**: v0.10.0+ (Unified Config), v0.11.0+ (Recursive Execution)
- **Key Points**:
  - Single `sbkube.yaml` file replaces `sources.yaml` + `config.yaml`
  - Settings inheritance: global → phase → app
  - Phase-based organization with dependencies
  - Recursive execution for nested phases
  - Backward compatible with legacy formats (with deprecation warnings)
- **Related**:
  - **Legacy Config**: [config-schema.md](config-schema.md)
  - **Legacy Sources**: [sources-schema.md](sources-schema.md)
  - **Migration Guide**: [migration-guide.md](migration-guide.md)
  - **Workspace**: [workspace-schema.md](workspace-schema.md)

______________________________________________________________________

## Configuration File Priority

SBKube detects configuration files in the following order:

1. `sbkube.yaml` - **Unified Config** (recommended, v0.10.0+)
2. `workspace.yaml` - Workspace Config (v0.9.x, deprecated)
3. `sources.yaml` + `config.yaml` - Legacy Config (deprecated)

When multiple formats exist, the highest priority format is used with a deprecation warning.

______________________________________________________________________

## Basic Structure

```yaml
# sbkube.yaml
apiVersion: sbkube/v1

metadata:
  name: my-deployment
  environment: production
  description: Production k3s cluster deployment

settings:
  kubeconfig: ~/.kube/config
  kubeconfig_context: production
  namespace: default
  timeout: 600
  on_failure: stop
  rollback_scope: app

apps:
  nginx:
    type: helm
    chart: bitnami/nginx
    version: "15.0.0"

phases:
  p1-infra:
    source: p1-infra/sbkube.yaml
  p2-app:
    source: p2-app/sbkube.yaml
    depends_on: [p1-infra]
```

______________________________________________________________________

## Settings Reference

### UnifiedSettings

| Field | Type | Default | Description |
|-------|------|---------|-------------|
| `kubeconfig` | string | null | Path to kubeconfig file |
| `kubeconfig_context` | string | null | Kubernetes context to use |
| `namespace` | string | `"default"` | Default namespace for deployments |
| `timeout` | int | `600` | Deployment timeout in seconds (1-7200) |
| `on_failure` | string | `"stop"` | Failure behavior: `stop`, `continue`, `rollback` |
| `rollback_scope` | string | `"app"` | Rollback scope: `app`, `phase`, `all` |
| `execution_order` | string | `"apps_first"` | Execution order: `apps_first`, `phases_first` |
| `parallel` | bool | `false` | Enable parallel phase execution |
| `parallel_apps` | bool | `false` | Enable parallel app execution within phases |
| `max_workers` | int | `4` | Maximum parallel workers (1-32) |
| `helm_label_injection` | bool | `true` | Enable Helm label injection |
| `incompatible_charts` | list | `[]` | Charts incompatible with label injection |
| `force_label_injection` | list | `[]` | Charts to force label injection |
| `helm_repos` | dict | `{}` | Helm repository definitions |
| `oci_registries` | dict | `{}` | OCI registry definitions |
| `git_repos` | dict | `{}` | Git repository definitions |

### on_failure Options

- **stop**: Stop execution on first failure (default)
- **continue**: Continue with remaining apps/phases
- **rollback**: Trigger rollback based on `rollback_scope`

### rollback_scope Options (v0.11.0+)

- **app**: Rollback only the failed app (default)
- **phase**: Rollback all apps in the failed phase
- **all**: Rollback entire deployment

### execution_order Options

- **apps_first**: Execute root-level apps before phases (default)
- **phases_first**: Execute phases before root-level apps

______________________________________________________________________

## Phase Reference

Phases can reference external config files or define apps inline:

### External Source

```yaml
phases:
  p1-infra:
    description: Infrastructure components
    source: p1-infra/sbkube.yaml
    depends_on: []
```

### Inline Apps

```yaml
phases:
  p1-infra:
    description: Infrastructure components
    apps:
      traefik:
        type: helm
        chart: traefik/traefik
        version: "25.0.0"
```

### Phase Options

| Field | Type | Required | Description |
|-------|------|----------|-------------|
| `description` | string | No | Phase description |
| `source` | string | No* | Path to external sbkube.yaml |
| `apps` | dict | No* | Inline app definitions |
| `depends_on` | list | No | List of phase dependencies |
| `settings` | object | No | Phase-specific settings override |

\* Either `source` or `apps` must be specified, but not both.

______________________________________________________________________

## Settings Inheritance

Settings are inherited from parent to child with the following merge rules:

- **Scalars** (strings, numbers, booleans): Child overrides parent
- **Lists**: Merged and deduplicated
- **Dicts**: Deep merged

### Example

```yaml
# Root sbkube.yaml
settings:
  timeout: 600
  namespace: default
  helm_repos:
    bitnami: https://charts.bitnami.com/bitnami

phases:
  p1-infra:
    source: p1-infra/sbkube.yaml
    settings:
      timeout: 300  # Override timeout for this phase
```

```yaml
# p1-infra/sbkube.yaml
settings:
  namespace: kube-system  # Override namespace for this phase
  helm_repos:
    traefik: https://helm.traefik.io/traefik  # Added to parent repos

apps:
  traefik:
    type: helm
    chart: traefik/traefik
    # Effective settings:
    # - timeout: 300 (from phase override)
    # - namespace: kube-system (from local override)
    # - helm_repos: {bitnami: ..., traefik: ...} (merged)
```

______________________________________________________________________

## Helm Repository Configuration

### Simple Format

```yaml
settings:
  helm_repos:
    bitnami: https://charts.bitnami.com/bitnami
```

### Detailed Format

```yaml
settings:
  helm_repos:
    bitnami:
      url: https://charts.bitnami.com/bitnami
      username: myuser
      password: ${BITNAMI_PASSWORD}
```

### OCI Registry

```yaml
settings:
  oci_registries:
    ghcr:
      url: ghcr.io/myorg
      username: ${GITHUB_USER}
      password: ${GITHUB_TOKEN}
```

______________________________________________________________________

## App Configuration

App configuration follows the same schema as the legacy `config.yaml`:

```yaml
apps:
  nginx:
    type: helm
    chart: bitnami/nginx
    version: "15.0.0"
    namespace: web
    values:
      replicaCount: 3
      service:
        type: LoadBalancer
    enabled: true
```

See [config-schema.md](config-schema.md) for detailed app configuration options.

______________________________________________________________________

## Recursive Execution (v0.11.0+)

The RecursiveExecutor enables nested phase execution with proper settings inheritance:

```
sbkube.yaml (root)
├── apps (root-level apps)
└── phases
    ├── p1-infra/sbkube.yaml
    │   ├── apps
    │   └── phases (nested)
    └── p2-app/sbkube.yaml
        └── apps
```

### Execution Flow

1. Merge parent settings with current settings
2. Based on `execution_order`:
   - `apps_first`: Execute root apps → Execute phases
   - `phases_first`: Execute phases → Execute root apps
3. For each phase (in dependency order):
   - Load referenced config file (if `source` specified)
   - Recursively execute with inherited settings

______________________________________________________________________

## Migration from Legacy Format

### Legacy Format (sources.yaml + config.yaml)

```yaml
# sources.yaml
kubeconfig: ~/.kube/config
helm_repos:
  bitnami:
    url: https://charts.bitnami.com/bitnami

# config.yaml
namespace: production
apps:
  nginx:
    type: helm
    chart: bitnami/nginx
```

### Unified Format (sbkube.yaml)

```yaml
# sbkube.yaml
apiVersion: sbkube/v1

settings:
  kubeconfig: ~/.kube/config
  namespace: production
  helm_repos:
    bitnami:
      url: https://charts.bitnami.com/bitnami

apps:
  nginx:
    type: helm
    chart: bitnami/nginx
```

### Migration Tool (v1.0.0, planned)

```bash
# Future command to auto-migrate
sbkube migrate --input sources.yaml --input config.yaml --output sbkube.yaml
```

______________________________________________________________________

## Complete Example

```yaml
# sbkube.yaml - Complete example
apiVersion: sbkube/v1

metadata:
  name: production-cluster
  environment: production
  version: "1.0.0"

settings:
  kubeconfig: ~/.kube/config
  kubeconfig_context: production-k3s
  namespace: default
  timeout: 600
  on_failure: rollback
  rollback_scope: phase
  execution_order: phases_first
  parallel: true
  max_workers: 4

  helm_repos:
    bitnami:
      url: https://charts.bitnami.com/bitnami
    traefik:
      url: https://helm.traefik.io/traefik

  incompatible_charts:
    - traefik/traefik
    - jetstack/cert-manager

apps:
  # Root-level apps (executed based on execution_order)
  monitoring-crd:
    type: helm
    chart: prometheus-community/kube-prometheus-stack-crds

phases:
  p1-infra:
    description: Core infrastructure components
    source: phases/p1-infra/sbkube.yaml

  p2-networking:
    description: Networking components
    source: phases/p2-networking/sbkube.yaml
    depends_on: [p1-infra]

  p3-apps:
    description: Application deployments
    source: phases/p3-apps/sbkube.yaml
    depends_on: [p1-infra, p2-networking]

  p4-monitoring:
    description: Monitoring and observability
    apps:
      prometheus:
        type: helm
        chart: prometheus-community/kube-prometheus-stack
        namespace: monitoring
    depends_on: [p1-infra]
```

______________________________________________________________________

## Version History

| Version | Feature |
|---------|---------|
| v0.10.0 | Unified Config (sbkube.yaml) |
| v0.11.0 | Recursive Executor, rollback_scope |
| v1.0.0 | Legacy removal, migration tool (planned) |
