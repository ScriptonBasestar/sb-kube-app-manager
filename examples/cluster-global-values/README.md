# Cluster Global Values Example

This example demonstrates how to use **cluster-level global values** in SBKube v0.7.0+.

## Overview

Cluster global values allow you to define common Helm values that apply to **all apps** in a cluster without duplicating them in each app's values file.

**Use Cases**:
- Shared storage class across all apps
- Common domain/ingress settings
- Environment-wide monitoring/backup configuration
- Global image registry/pull secrets

## Priority Hierarchy

```
1. cluster_values_file (lowest)      # From sources.yaml
2. global_values inline (middle)     # From sources.yaml
3. app values files (higher)         # From config.yaml
4. app set_values (highest)          # From config.yaml
```

## Example Structure

```
cluster-global-values/
├── README.md
├── sources.yaml                    # Cluster configuration + global values
├── cluster-values.yaml             # Cluster-level values file
├── config.yaml                     # App configuration
└── values/
    └── nginx-custom.yaml           # App-specific values
```

## 1. Using cluster_values_file

**sources.yaml**:
```yaml
cluster: production-k3s
kubeconfig: ~/.kube/config
kubeconfig_context: prod-cluster

# Reference to cluster-level values file
cluster_values_file: cluster-values.yaml

helm_repos:
  - name: grafana
    url: https://grafana.github.io/helm-charts
```

**cluster-values.yaml**:
```yaml
global:
  storageClass: nfs-client
  domain: prod.example.com
  monitoring:
    enabled: true
    retention: 30d
  backup:
    enabled: true
    schedule: "0 2 * * *"
```

## 2. Using Inline global_values

**sources.yaml**:
```yaml
cluster: staging-k3s
kubeconfig: ~/.kube/config
kubeconfig_context: staging-cluster

# Inline global values (simpler for small configs)
global_values:
  global:
    storageClass: hostpath
    environment: staging
    replicas: 1

helm_repos:
  - name: grafana
    url: https://grafana.github.io/helm-charts
```

## 3. Combining Both (Recommended)

**sources.yaml**:
```yaml
cluster: production-k3s
kubeconfig: ~/.kube/config
kubeconfig_context: prod-cluster

# File for complex/stable settings
cluster_values_file: cluster-values.yaml

# Inline for quick overrides
global_values:
  global:
    maintenance_mode: false  # Override file setting
    deployment_timestamp: "2025-01-06T10:00:00Z"

helm_repos:
  - name: grafana
    url: https://grafana.github.io/helm-charts
```

## Complete Example

### sources.yaml
```yaml
cluster: production-k3s
kubeconfig: ~/.kube/config
kubeconfig_context: prod-cluster

cluster_values_file: cluster-values.yaml

global_values:
  global:
    environment: production

helm_repos:
  - name: grafana
    url: https://grafana.github.io/helm-charts
```

### cluster-values.yaml
```yaml
global:
  storageClass: nfs-client
  domain: prod.example.com
  imageRegistry: harbor.example.com
  imagePullSecrets:
    - name: harbor-registry-secret
```

### config.yaml
```yaml
namespace: default

apps:
  nginx:
    type: helm
    chart: grafana/nginx
    values:
      - values/nginx-custom.yaml
```

### values/nginx-custom.yaml
```yaml
# App-specific values (override cluster defaults)
global:
  storageClass: ceph-block  # Override cluster default

replicaCount: 3
service:
  type: LoadBalancer
```

## Final Merged Values

When deploying nginx, the final values will be:

```yaml
global:
  storageClass: ceph-block           # From nginx-custom.yaml (highest priority)
  domain: prod.example.com           # From cluster-values.yaml
  environment: production            # From sources.yaml inline
  imageRegistry: harbor.example.com  # From cluster-values.yaml
  imagePullSecrets:
    - name: harbor-registry-secret

replicaCount: 3                      # From nginx-custom.yaml
service:
  type: LoadBalancer                 # From nginx-custom.yaml
```

## Usage

```bash
# Deploy with cluster global values
sbkube apply --app-dir cluster-global-values/

# Template to see final values
sbkube template --app-dir cluster-global-values/

# Validate configuration
sbkube validate --app-dir cluster-global-values/
```

## Benefits

✅ **DRY Principle**: Define common settings once
✅ **Consistency**: All apps share cluster-wide defaults
✅ **Flexibility**: Apps can override when needed
✅ **Maintainability**: Update cluster settings in one place
✅ **Multi-Environment**: Different values per cluster (dev/staging/prod)

## Migration from v0.6.x

**Before (v0.6.x)**: Duplicate values in each app

```yaml
# app1/values.yaml
global:
  storageClass: nfs-client
  domain: example.com

# app2/values.yaml
global:
  storageClass: nfs-client  # Duplicated!
  domain: example.com       # Duplicated!
```

**After (v0.7.0+)**: Centralized cluster values

```yaml
# sources.yaml
cluster_values_file: cluster-values.yaml

# cluster-values.yaml
global:
  storageClass: nfs-client
  domain: example.com

# app1/values.yaml and app2/values.yaml
# (No need to duplicate global settings)
```

## See Also

- [sources-schema.md](../../docs/03-configuration/sources-schema.md) - sources.yaml specification
- [config-schema.md](../../docs/03-configuration/config-schema.md) - config.yaml specification
