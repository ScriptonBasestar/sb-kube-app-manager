# Complete Workflow Example

This example demonstrates the full SBKube workflow from prepare through deploy.

## Structure

```
complete-workflow/
├── config.yaml           # App definitions
├── sources.yaml          # Helm repos and cluster config
├── values/
│   ├── redis.yaml        # Redis values override
│   └── nginx.yaml        # Nginx values override
└── manifests/
    └── configmap.yaml    # YAML manifest example
```

## App Types Demonstrated

1. **Helm** (`redis`, `nginx`): Remote Helm charts from Bitnami repository
2. **YAML** (`configmap`): Direct Kubernetes manifest application

## Usage

```bash
# Validate configuration
sbkube validate config.yaml

# Run complete workflow
sbkube apply --app-dir examples/complete-workflow

# Or run steps individually
sbkube prepare --app-dir examples/complete-workflow --force
sbkube build --app-dir examples/complete-workflow
sbkube template --app-dir examples/complete-workflow
sbkube deploy --app-dir examples/complete-workflow --dry-run
```

## Dependencies

- `nginx` depends on `redis` (deployed after redis is ready)
- `configmap` has no dependencies (deployed in parallel with others)

## Requirements

- kubectl configured with cluster access
- Helm 3.x installed
- Target namespace will be created automatically
