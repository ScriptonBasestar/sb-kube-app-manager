# Multi-Cluster Deployment Pattern

**Deploy the same application stack across multiple Kubernetes clusters with environment-specific configurations**

## 📋 Overview

This example demonstrates how to use SBKube to deploy identical application stacks to multiple Kubernetes clusters while maintaining cluster-specific configurations. This pattern is essential for:

- **Multi-region deployments** - Deploy to clusters in different geographic regions
- **High availability** - Maintain redundant deployments across clusters
- **Disaster recovery** - Quick failover to backup clusters
- **Blue-green at cluster level** - Switch traffic between entire clusters
- **Environment isolation** - Separate production, staging, and development clusters

## 🏗️ Architecture

```
┌─────────────────────────────────────────────────────────────┐
│                    Multi-Cluster Setup                      │
├─────────────────────────────────────────────────────────────┤
│                                                             │
│  ┌──────────────────────┐      ┌──────────────────────┐  │
│  │   Cluster A          │      │   Cluster B          │  │
│  │   (us-west)          │      │   (us-east)          │  │
│  │                      │      │                      │  │
│  │  ┌────────────────┐  │      │  ┌────────────────┐  │  │
│  │  │ Nginx (3 pods) │  │      │  │ Nginx (3 pods) │  │  │
│  │  └────────────────┘  │      │  └────────────────┘  │  │
│  │         ↓            │      │         ↓            │  │
│  │  ┌──────┬──────┐    │      │  ┌──────┬──────┐    │  │
│  │  │Redis │ PG   │    │      │  │Redis │ PG   │    │  │
│  │  └──────┴──────┘    │      │  └──────┴──────┘    │  │
│  └──────────────────────┘      └──────────────────────┘  │
│                                                             │
└─────────────────────────────────────────────────────────────┘
```

## 📁 Directory Structure

```
05-multi-cluster/
├── sources-cluster-a.yaml          # Cluster A connection config
├── sources-cluster-b.yaml          # Cluster B connection config
├── config-cluster-a.yaml           # Cluster A app config
├── config-cluster-b.yaml           # Cluster B app config
├── values/
│   ├── redis-cluster-a.yaml        # Redis values for Cluster A
│   ├── redis-cluster-b.yaml        # Redis values for Cluster B
│   ├── postgresql-cluster-a.yaml   # PostgreSQL values for Cluster A
│   ├── postgresql-cluster-b.yaml   # PostgreSQL values for Cluster B
│   ├── nginx-cluster-a.yaml        # Nginx values for Cluster A
│   └── nginx-cluster-b.yaml        # Nginx values for Cluster B
├── deploy.sh                       # Deployment automation script
└── README.md                       # This file
```

## 🎯 Key Concepts

### 1. Separate Sources Files

Each cluster has its own `sources.yaml` file with cluster-specific connection details:

**sources-cluster-a.yaml**:
```yaml
clusters:
  - name: cluster-a
    context: cluster-a-context
    kubeconfig: ~/.kube/config-cluster-a
```

**sources-cluster-b.yaml**:
```yaml
clusters:
  - name: cluster-b
    context: cluster-b-context
    kubeconfig: ~/.kube/config-cluster-b
```

### 2. Separate Config Files

Each cluster has its own `config.yaml` with environment-specific settings:

```yaml
# config-cluster-a.yaml
namespace: app-cluster-a
global_labels:
  cluster: cluster-a
  region: us-west

# config-cluster-b.yaml
namespace: app-cluster-b
global_labels:
  cluster: cluster-b
  region: us-east
```

### 3. Cluster-Specific Values

Each application has cluster-specific Helm values files:

```
values/
├── redis-cluster-a.yaml      # Different passwords, settings
├── redis-cluster-b.yaml
├── postgresql-cluster-a.yaml
└── postgresql-cluster-b.yaml
```

### 4. Consistent Application Stack

Despite cluster-specific configurations, the application stack remains consistent:
- Same Helm chart versions
- Same application dependencies
- Same deployment order

## 🚀 Quick Start

### Prerequisites

- 2+ Kubernetes clusters (k3s, EKS, GKE, AKS, etc.)
- kubectl configured with access to both clusters
- helm 3+ installed
- SBKube v0.5.0+ installed

### 1. Configure Cluster Access

**Option A: Separate kubeconfig files** (Recommended):

```bash
# Cluster A kubeconfig
export KUBECONFIG_CLUSTER_A=~/.kube/config-cluster-a

# Cluster B kubeconfig
export KUBECONFIG_CLUSTER_B=~/.kube/config-cluster-b
```

**Option B: Single kubeconfig with multiple contexts**:

```bash
# List available contexts
kubectl config get-contexts

# Update sources files with correct context names
vim sources-cluster-a.yaml  # Set context: your-cluster-a-context
vim sources-cluster-b.yaml  # Set context: your-cluster-b-context
```

### 2. Customize Configurations

Edit cluster-specific values:

```bash
# Cluster A values
vim values/redis-cluster-a.yaml
vim values/postgresql-cluster-a.yaml
vim values/nginx-cluster-a.yaml

# Cluster B values
vim values/redis-cluster-b.yaml
vim values/postgresql-cluster-b.yaml
vim values/nginx-cluster-b.yaml
```

**Key settings to customize**:
- Passwords and secrets
- Resource limits
- Storage sizes
- Replica counts
- Region-specific annotations

### 3. Validate Configurations

Validate before deploying:

```bash
# Validate Cluster A config
sbkube validate config-cluster-a.yaml

# Validate Cluster B config
sbkube validate config-cluster-b.yaml
```

### 4. Deploy to Clusters

**Option A: Using the deployment script**:

```bash
# Make script executable
chmod +x deploy.sh

# Deploy to both clusters
./deploy.sh all

# Or deploy to specific cluster
./deploy.sh cluster-a
./deploy.sh cluster-b
```

**Option B: Manual deployment**:

```bash
# Deploy to Cluster A
sbkube apply \
    --app-dir . \
    --config config-cluster-a.yaml \
    --sources sources-cluster-a.yaml

# Deploy to Cluster B
sbkube apply \
    --app-dir . \
    --config config-cluster-b.yaml \
    --sources sources-cluster-b.yaml
```

### 5. Verify Deployments

Check status on each cluster:

```bash
# Cluster A status
sbkube status --app-dir . --config config-cluster-a.yaml

# Cluster B status
sbkube status --app-dir . --config config-cluster-b.yaml
```

## 🔧 Advanced Usage

### Parallel Deployment

Deploy to multiple clusters in parallel using background jobs:

```bash
#!/bin/bash
# Deploy to Cluster A in background
sbkube apply --app-dir . --config config-cluster-a.yaml &
PID_A=$!

# Deploy to Cluster B in background
sbkube apply --app-dir . --config config-cluster-b.yaml &
PID_B=$!

# Wait for both to complete
wait $PID_A && echo "✅ Cluster A done"
wait $PID_B && echo "✅ Cluster B done"
```

### Environment-Based Deployment

Use environment variables for dynamic configuration:

```bash
#!/bin/bash
export CLUSTER_ENV="${1:-production}"

case "${CLUSTER_ENV}" in
    production)
        CLUSTERS=("cluster-a" "cluster-b")
        ;;
    staging)
        CLUSTERS=("cluster-staging")
        ;;
    development)
        CLUSTERS=("cluster-dev")
        ;;
esac

for cluster in "${CLUSTERS[@]}"; do
    sbkube apply --app-dir . --config "config-${cluster}.yaml"
done
```

### CI/CD Integration

**GitHub Actions example**:

```yaml
name: Multi-Cluster Deploy

on:
  push:
    branches: [main]

jobs:
  deploy:
    runs-on: ubuntu-latest
    strategy:
      matrix:
        cluster: [cluster-a, cluster-b]
    steps:
      - uses: actions/checkout@v3

      - name: Configure kubectl
        uses: azure/k8s-set-context@v3
        with:
          kubeconfig: ${{ secrets[format('KUBECONFIG_{0}', matrix.cluster)] }}

      - name: Install SBKube
        run: |
          curl -fsSL https://github.com/yourusername/sbkube/releases/latest/download/install.sh | bash

      - name: Deploy to ${{ matrix.cluster }}
        run: |
          cd examples/patterns/05-multi-cluster
          sbkube apply \
            --app-dir . \
            --config config-${{ matrix.cluster }}.yaml \
            --sources sources-${{ matrix.cluster }}.yaml
```

### Diff Between Clusters

Compare configurations before deploying:

```bash
# Compare config files
diff config-cluster-a.yaml config-cluster-b.yaml

# Compare values files
diff values/redis-cluster-a.yaml values/redis-cluster-b.yaml
```

### Rollback Strategy

Rollback specific cluster:

```bash
# Check deployment history for Cluster A
sbkube history --app-dir . --config config-cluster-a.yaml

# Rollback Cluster A to previous version
sbkube rollback --app-dir . --config config-cluster-a.yaml

# Cluster B remains unchanged
```

## 📊 Configuration Differences

### Global Labels

Cluster A uses `region: us-west`, Cluster B uses `region: us-east`:

```yaml
# config-cluster-a.yaml
global_labels:
  cluster: cluster-a
  region: us-west
  environment: production

# config-cluster-b.yaml
global_labels:
  cluster: cluster-b
  region: us-east
  environment: production
```

### Namespaces

Each cluster deploys to a different namespace for isolation:

```yaml
# config-cluster-a.yaml
namespace: app-cluster-a

# config-cluster-b.yaml
namespace: app-cluster-b
```

### Passwords and Secrets

Each cluster uses different credentials:

```yaml
# values/redis-cluster-a.yaml
auth:
  password: "cluster-a-redis-pass"

# values/redis-cluster-b.yaml
auth:
  password: "cluster-b-redis-pass"
```

### Resource Limits

Adjust based on cluster capacity:

```yaml
# Cluster A (larger nodes)
resources:
  limits:
    cpu: 1000m
    memory: 1Gi

# Cluster B (smaller nodes)
resources:
  limits:
    cpu: 500m
    memory: 512Mi
```

## 🎓 Use Cases

### 1. Multi-Region High Availability

Deploy to clusters in different AWS regions:

```bash
# US West (Cluster A)
sbkube apply --config config-us-west.yaml

# US East (Cluster B)
sbkube apply --config config-us-east.yaml
```

Benefits:
- Geographic redundancy
- Lower latency for regional users
- Compliance with data residency requirements

### 2. Blue-Green at Cluster Level

Maintain two identical clusters for zero-downtime upgrades:

```bash
# Deploy new version to "green" cluster
sbkube apply --config config-cluster-b.yaml

# Verify green cluster
sbkube status --config config-cluster-b.yaml

# Switch DNS/load balancer to green cluster
# Then update blue cluster
sbkube apply --config config-cluster-a.yaml
```

### 3. Development → Staging → Production

Progressive deployment across environments:

```bash
# 1. Deploy to dev cluster
sbkube apply --config config-dev.yaml

# 2. Test and validate

# 3. Deploy to staging cluster
sbkube apply --config config-staging.yaml

# 4. More testing

# 5. Deploy to production clusters
./deploy.sh all  # Deploys to cluster-a and cluster-b
```

### 4. Disaster Recovery

Maintain hot standby cluster:

```bash
# Primary cluster (active)
sbkube apply --config config-primary.yaml

# Standby cluster (passive, receives same deployments)
sbkube apply --config config-standby.yaml

# In case of disaster, just switch traffic to standby
```

## 🐛 Troubleshooting

### Issue: Different Cluster Versions

**Problem**: Clusters running different Kubernetes versions

**Solution**: Use compatible Helm chart versions:

```yaml
# config-cluster-a.yaml (k8s 1.28)
apps:
  nginx:
    chart: bitnami/nginx
    version: "15.0.0"  # Compatible with k8s 1.28

# config-cluster-b.yaml (k8s 1.26)
apps:
  nginx:
    chart: bitnami/nginx
    version: "14.0.0"  # Compatible with k8s 1.26
```

### Issue: Cluster Authentication Fails

**Problem**: Cannot connect to one of the clusters

**Solution**: Verify kubeconfig and context:

```bash
# Test Cluster A access
kubectl --kubeconfig ~/.kube/config-cluster-a get nodes

# Test Cluster B access
kubectl --kubeconfig ~/.kube/config-cluster-b get nodes

# Check context names
kubectl config get-contexts
```

### Issue: Different Storage Classes

**Problem**: Clusters have different storage class names

**Solution**: Use cluster-specific storage class in values:

```yaml
# values/postgresql-cluster-a.yaml
primary:
  persistence:
    storageClass: "gp2"  # AWS EBS

# values/postgresql-cluster-b.yaml
primary:
  persistence:
    storageClass: "standard-rwo"  # GKE standard
```

### Issue: Deployment Order

**Problem**: Need to deploy to primary cluster first

**Solution**: Use sequential deployment:

```bash
# Deploy to primary first
sbkube apply --config config-primary.yaml
# Wait for successful deployment

# Then deploy to secondary
sbkube apply --config config-secondary.yaml
```

## 📝 Best Practices

### 1. Use Consistent Chart Versions

Keep chart versions synchronized across clusters:

```yaml
# Both clusters use same versions
apps:
  redis:
    chart: bitnami/redis
    version: "18.0.0"  # ✅ Same version
```

### 2. Separate Secrets Per Cluster

Never share passwords between clusters:

```yaml
# cluster-a uses different passwords
auth:
  password: "unique-cluster-a-password"

# cluster-b uses different passwords
auth:
  password: "unique-cluster-b-password"
```

### 3. Label Resources by Cluster

Use global labels to identify cluster:

```yaml
global_labels:
  cluster: cluster-a
  region: us-west
  environment: production
```

### 4. Test Before Production

Always validate in non-production cluster first:

```bash
# 1. Deploy to dev cluster
sbkube apply --config config-dev.yaml

# 2. Run tests

# 3. Deploy to production clusters
sbkube apply --config config-prod-a.yaml
sbkube apply --config config-prod-b.yaml
```

### 5. Automate Deployment

Use scripts or CI/CD for consistency:

```bash
# Automated deployment to all clusters
./deploy.sh all
```

### 6. Monitor All Clusters

Set up monitoring for each cluster:

```bash
# Check status of all clusters
for cluster in cluster-a cluster-b; do
    echo "=== ${cluster} Status ==="
    sbkube status --config "config-${cluster}.yaml"
done
```

## 🔗 Related Examples

- **[06-environment-configs](../06-environment-configs/)** - Environment-based configuration management
- **[07-canary-deployment](../07-canary-deployment/)** - Canary deployment pattern
- **[08-blue-green](../08-blue-green/)** - Blue-green deployment pattern
- **[03-monitoring-stack](../../use-cases/03-monitoring-stack/)** - Monitoring across clusters
- **[09-backup-restore](../../use-cases/09-backup-restore/)** - Backup/restore for multi-cluster

## 📚 Additional Resources

- [SBKube Configuration Schema](../../../docs/03-configuration/config-schema.md)
- [Helm Chart Customization](../../../docs/03-configuration/chart-customization.md)
- [Multi-Cluster Best Practices](../../../docs/05-best-practices/directory-structure.md)
- [Deployment Guide](../../../docs/06-deployment/deployment-guide.md)

## 🎯 Summary

This example demonstrates:

- ✅ Deploying to multiple clusters with SBKube
- ✅ Cluster-specific configurations and secrets
- ✅ Automated multi-cluster deployment
- ✅ Environment isolation and labeling
- ✅ High availability and disaster recovery patterns
- ✅ CI/CD integration for multi-cluster deployments

**Key Takeaway**: SBKube makes multi-cluster deployments simple by using separate config and sources files for each cluster while maintaining consistency in application definitions.
