# K3scode Example

This example demonstrates multi-domain K3s deployments for different use cases.

## Structure

```
k3scode/
├── sbkube.yaml              # Shared Helm repos for all domains
├── ai/                       # AI/ML infrastructure
│   ├── sbkube.yaml
│   └── values/
│       ├── redis.yaml
│       └── qdrant.yaml
├── devops/                   # DevOps monitoring stack
│   ├── sbkube.yaml
│   └── values/
│       ├── prometheus.yaml
│       └── grafana.yaml
├── memory/                   # In-memory caching
│   ├── sbkube.yaml
│   └── values/
│       └── redis.yaml
└── rdb/                      # Relational database
    ├── sbkube.yaml
    └── values/
        └── postgresql.yaml
```

## Domains

### AI (`ai/`)
- **Redis**: High-performance caching for AI inference
- **Qdrant**: Vector database for similarity search

### DevOps (`devops/`)
- **Prometheus**: Metrics collection and monitoring
- **Grafana**: Visualization dashboards (depends on Prometheus)

### Memory (`memory/`)
- **Redis**: Standalone cache instance

### RDB (`rdb/`)
- **PostgreSQL**: Primary relational database

## Usage

```bash
# Validate configuration
sbkube validate --app-dir examples/k3scode/ai --source examples/k3scode/sbkube.yaml

# Deploy AI infrastructure
sbkube apply --app-dir examples/k3scode/ai --source examples/k3scode/sbkube.yaml

# Deploy DevOps stack
sbkube apply --app-dir examples/k3scode/devops --source examples/k3scode/sbkube.yaml

# Or run steps individually
sbkube prepare --app-dir examples/k3scode/ai --source examples/k3scode/sbkube.yaml --force
sbkube build --app-dir examples/k3scode/ai
sbkube template --app-dir examples/k3scode/ai
sbkube deploy --app-dir examples/k3scode/ai --dry-run
```

## Shared Configuration

All domains share the same `sbkube.yaml` which defines:
- Helm repository URLs (Bitnami, Grafana, Prometheus, etc.)
- Cluster configuration
- Default kubeconfig settings

## Requirements

- kubectl configured with cluster access
- Helm 3.x installed
- K3s or any Kubernetes cluster
