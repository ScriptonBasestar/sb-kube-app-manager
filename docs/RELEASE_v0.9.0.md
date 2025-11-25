# Release v0.9.0 - Workspace Multi-Phase Deployment

**Release Date**: 2025-11-25

## 🎉 Highlights

This release introduces **Workspace**, a major feature for orchestrating multi-phase deployments with dependency ordering across different configurations.

## ✨ New Features

### Workspace Multi-Phase Deployment

Workspace enables complex deployment scenarios where multiple phases need to be executed in a specific order with dependency management.

**New Commands:**

| Command | Description |
|---------|-------------|
| `sbkube workspace validate` | Validate workspace.yaml configuration |
| `sbkube workspace graph` | Visualize phase dependency graph |
| `sbkube workspace deploy` | Execute multi-phase deployments |
| `sbkube workspace status` | Display workspace configuration overview |
| `sbkube workspace history` | View deployment history for workspace phases |

**Key Capabilities:**

- **Phase Dependency Resolution**: Automatic ordering using Kahn's algorithm
- **Parallel Execution**: Independent phases run concurrently
- **State Tracking**: Per-phase deployment history
- **Rollback Support**: Workspace-level rollback capabilities
- **Flexible Configuration**: Per-phase timeouts, failure handling, and environment variables

### Configuration Example

```yaml
# workspace.yaml
version: "1.0"

metadata:
  name: production-deployment
  description: "Production infrastructure deployment"
  environment: prod

global:
  kubeconfig: ~/.kube/config
  context: production-cluster
  timeout: 600
  on_failure: stop

phases:
  p1-infra:
    description: "Network and storage infrastructure"
    source: p1-kube/sources.yaml
    app_groups:
      - a000_network
      - a001_storage

  p2-data:
    description: "Database and caching layer"
    source: p2-kube/sources.yaml
    app_groups:
      - a100_postgres
      - a101_redis
    depends_on:
      - p1-infra

  p3-app:
    description: "Application services"
    source: p3-kube/sources.yaml
    depends_on:
      - p2-data
```

### Usage

```bash
# Validate configuration
sbkube workspace validate workspace.yaml

# View dependency graph
sbkube workspace graph workspace.yaml

# Deploy (dry-run)
sbkube workspace deploy workspace.yaml --dry-run

# Deploy all phases
sbkube workspace deploy workspace.yaml

# Deploy specific phase
sbkube workspace deploy workspace.yaml --phase p2-data

# Check status
sbkube workspace status workspace.yaml
```

## 📚 Documentation

- **Workspace Guide**: [docs/02-features/workspace-guide.md](docs/02-features/workspace-guide.md)
- **Workspace Schema**: [docs/03-configuration/workspace-schema.md](docs/03-configuration/workspace-schema.md)
- **Example Project**: [examples/workspace-multi-phase/](examples/workspace-multi-phase/)

## 🔄 Migration

No breaking changes from v0.8.x. The workspace feature is additive.

If upgrading from v0.7.x or earlier, see [v0.8.0 Migration Guide](docs/MIGRATION_v0.8.0.md).

## 📊 Statistics

- **Tests**: 1242 passed, 9 skipped
- **Coverage**: 63%
- **New Files**: 15+ (workspace implementation, models, tests)

## 🙏 Acknowledgments

Thanks to all contributors and users who provided feedback for this release.

---

**Full Changelog**: [CHANGELOG.md](CHANGELOG.md)

**Installation**:
```bash
pip install sbkube==0.9.0
# or
uv add sbkube==0.9.0
```
