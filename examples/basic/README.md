# Basic Example

This is the simplest SBKube configuration demonstrating the most common use case: deploying Helm charts.

## Files

- `config.yaml` - Main configuration file defining applications
- `sources.yaml` - Helm repository definitions
- `redis.yaml` - Redis chart values override
- `postgres.yaml` - PostgreSQL chart values override
- `local-chart/` - Example local Helm chart

## Quick Start

```bash
# 1. Prepare (download/clone sources)
sbkube prepare --app-dir examples/basic

# 2. Build (assemble charts)
sbkube build --app-dir examples/basic

# 3. Template (generate manifests)
sbkube template --app-dir examples/basic --output-dir /tmp/manifests

# 4. Deploy (apply to cluster)
sbkube deploy --app-dir examples/basic --namespace demo

# Or use the unified apply command
sbkube apply --app-dir examples/basic --namespace demo
```

## What's Demonstrated

- **Helm Charts**: Deploy from remote repositories (Bitnami)
- **Values Override**: Customize chart values with YAML files
- **Namespace**: Global and per-app namespace configuration
- **Dependencies**: Control deployment order with `depends_on`
- **Local Charts**: Use charts from local directories
- **Enabled Flag**: Conditionally enable/disable applications

## Key Features

### Remote Helm Chart (redis)
```yaml
redis:
  type: helm
  chart: bitnami/redis    # repo/chart format
  version: "17.13.2"      # Pin to specific version
  values:
    - redis.yaml          # Override file
```

### Local Helm Chart (my-local-app)
```yaml
my-local-app:
  type: helm
  chart: ./local-chart    # Relative path
  enabled: false          # Disabled by default
```

### Deployment Order (postgresql)
```yaml
postgresql:
  type: helm
  chart: bitnami/postgresql
  depends_on:
    - redis               # Deploy after redis
```

## Next Steps

- See [complete-workflow](../complete-workflow/) for advanced features
- See [deploy/](../deploy/) for other application types (yaml, action, exec, http)
- See [overrides/](../overrides/) for advanced overrides and removes
