# Environment-Based Configuration Pattern

**Manage dev, staging, and production environments using value file layering and configuration inheritance**

## 📋 Overview

This example demonstrates how to use SBKube to manage multiple environments (development, staging, production) with environment-specific configurations while maintaining a shared base configuration. This pattern is essential for:

- **Environment parity** - Keep environments similar but with appropriate resource scaling
- **Configuration management** - Centralize common settings, override only what differs
- **Progressive deployment** - Test in dev → staging → production pipeline
- **Cost optimization** - Scale resources appropriately per environment
- **Security isolation** - Use different secrets/credentials per environment

## 🏗️ Architecture

```
┌─────────────────────────────────────────────────────────────┐
│                Environment Configuration Layers              │
├─────────────────────────────────────────────────────────────┤
│                                                             │
│  ┌────────────────────────────────────────────────────┐   │
│  │           Base Configuration (config.yaml)          │   │
│  │  • Common app definitions                           │   │
│  │  • Shared labels and settings                       │   │
│  │  • Base Helm values (values/*-base.yaml)            │   │
│  └────────────────────────────────────────────────────┘   │
│                           ↓                                 │
│  ┌─────────────┬──────────────┬──────────────────────┐    │
│  │config-dev   │config-staging│config-production      │    │
│  │             │              │                       │    │
│  │• Dev values │• Staging vals│• Production values    │    │
│  │• Minimal    │• Mid-sized   │• Full-scale           │    │
│  │• No persist │• Persistence │• HA + Backup          │    │
│  └─────────────┴──────────────┴──────────────────────┘    │
│                                                             │
└─────────────────────────────────────────────────────────────┘
```

## 📁 Directory Structure

```
06-environment-configs/
├── sources.yaml                    # Cluster connection config (shared)
├── config.yaml                     # Base configuration (optional, for reference)
├── config-dev.yaml                 # Development environment config
├── config-staging.yaml             # Staging environment config
├── config-production.yaml          # Production environment config
├── values/
│   ├── redis-base.yaml             # Base Redis config
│   ├── redis-dev.yaml              # Dev overrides
│   ├── redis-staging.yaml          # Staging overrides
│   ├── redis-production.yaml       # Production overrides
│   ├── postgresql-base.yaml        # Base PostgreSQL config
│   ├── postgresql-dev.yaml         # Dev overrides
│   ├── postgresql-staging.yaml     # Staging overrides
│   ├── postgresql-production.yaml  # Production overrides
│   ├── backend-base.yaml           # Base backend config
│   ├── backend-dev.yaml            # Dev overrides
│   ├── backend-staging.yaml        # Staging overrides
│   └── backend-production.yaml     # Production overrides
├── deploy.sh                       # Deployment automation script
└── README.md                       # This file
```

## 🎯 Key Concepts

### 1. Base + Override Pattern

**Base values** (`values/*-base.yaml`): Common configuration shared across environments

```yaml
# redis-base.yaml
architecture: standalone
auth:
  enabled: true
  # Password will be overridden per environment
metrics:
  enabled: false  # Enabled in staging/prod only
```

**Environment overrides** (`values/*-dev.yaml`): Environment-specific settings

```yaml
# redis-dev.yaml
auth:
  password: "dev-redis-password"
master:
  persistence:
    enabled: false  # No persistence in dev
  resources:
    limits:
      cpu: 100m
      memory: 128Mi
```

### 2. Value File Layering

Helm merges values files in order, with later files overriding earlier ones:

```yaml
# config-production.yaml
apps:
  redis:
    values:
      - values/redis-base.yaml        # 1. Base config
      - values/redis-production.yaml  # 2. Override with prod settings
```

### 3. Environment-Specific Namespaces

Each environment deploys to its own namespace for isolation:

```yaml
# config-dev.yaml
namespace: myapp-dev

# config-staging.yaml
namespace: myapp-staging

# config-production.yaml
namespace: myapp-production
```

### 4. Progressive Resource Scaling

Resources scale from dev → staging → production:

```
Development:   Redis: 100m CPU, 128Mi RAM, no persistence
Staging:       Redis: 300m CPU, 256Mi RAM, 4Gi storage
Production:    Redis: 1000m CPU, 1Gi RAM, 10Gi storage
```

## 🚀 Quick Start

### Prerequisites

- Kubernetes cluster (k3s, minikube, or cloud provider)
- kubectl configured with cluster access
- helm 3+ installed
- SBKube v0.5.0+ installed

### 1. Review Base Configuration

Check base values to understand shared settings:

```bash
# Review base configurations
cat values/redis-base.yaml
cat values/postgresql-base.yaml
cat values/backend-base.yaml
```

### 2. Customize Environment Settings

Edit environment-specific values:

```bash
# Development values
vim values/redis-dev.yaml
vim values/postgresql-dev.yaml
vim values/backend-dev.yaml

# Staging values
vim values/redis-staging.yaml
vim values/postgresql-staging.yaml
vim values/backend-staging.yaml

# Production values
vim values/redis-production.yaml
vim values/postgresql-production.yaml
vim values/backend-production.yaml
```

**Key settings to customize per environment**:
- Passwords and credentials
- Resource limits (CPU, memory)
- Replica counts
- Storage sizes and persistence
- Autoscaling thresholds
- Monitoring and backup settings

### 3. Deploy to Development

```bash
# Validate dev configuration
sbkube validate config-dev.yaml --schema-type config

# Deploy to dev
sbkube apply --app-dir . --config config-dev.yaml

# Or use deployment script
chmod +x deploy.sh
./deploy.sh dev
```

### 4. Deploy to Staging

After testing in development:

```bash
# Validate staging configuration
sbkube validate config-staging.yaml --schema-type config

# Deploy to staging
sbkube apply --app-dir . --config config-staging.yaml

# Or use deployment script
./deploy.sh staging
```

### 5. Deploy to Production

After successful staging validation:

```bash
# Validate production configuration
sbkube validate config-production.yaml --schema-type config

# Deploy to production
sbkube apply --app-dir . --config config-production.yaml

# Or use deployment script
./deploy.sh production
```

### 6. Verify Deployment

Check status for each environment:

```bash
# Dev status
sbkube status --app-dir . --config config-dev.yaml

# Staging status
sbkube status --app-dir . --config config-staging.yaml

# Production status
sbkube status --app-dir . --config config-production.yaml
```

## 🔧 Advanced Usage

### CI/CD Pipeline Integration

**GitHub Actions example**:

```yaml
name: Deploy to Environment

on:
  push:
    branches:
      - develop  # Deploy to dev/staging
      - main     # Deploy to production

jobs:
  deploy:
    runs-on: ubuntu-latest
    steps:
      - uses: actions/checkout@v3

      - name: Determine environment
        id: env
        run: |
          if [[ "${{ github.ref }}" == "refs/heads/main" ]]; then
            echo "environment=production" >> $GITHUB_OUTPUT
          elif [[ "${{ github.ref }}" == "refs/heads/develop" ]]; then
            echo "environment=staging" >> $GITHUB_OUTPUT
          else
            echo "environment=dev" >> $GITHUB_OUTPUT
          fi

      - name: Configure kubectl
        uses: azure/k8s-set-context@v3
        with:
          kubeconfig: ${{ secrets.KUBECONFIG }}

      - name: Install SBKube
        run: |
          curl -fsSL https://github.com/yourusername/sbkube/releases/latest/download/install.sh | bash

      - name: Deploy to ${{ steps.env.outputs.environment }}
        run: |
          cd examples/patterns/06-environment-configs
          sbkube apply --app-dir . --config config-${{ steps.env.outputs.environment }}.yaml
```

### Progressive Rollout Strategy

Use a safe progressive rollout process:

```bash
#!/bin/bash
# progressive-deploy.sh - Deploy through environments progressively

set -e

echo "=== Phase 1: Development Deployment ==="
./deploy.sh dev
read -p "✅ Dev deployment successful. Continue to staging? (y/n) " -n 1 -r
echo
if [[ ! $REPLY =~ ^[Yy]$ ]]; then exit 0; fi

echo "=== Phase 2: Staging Deployment ==="
./deploy.sh staging
read -p "✅ Staging deployment successful. Continue to production? (y/n) " -n 1 -r
echo
if [[ ! $REPLY =~ ^[Yy]$ ]]; then exit 0; fi

echo "=== Phase 3: Production Deployment ==="
./deploy.sh production
echo "✅ ✅ ✅ All environments deployed successfully!"
```

### Environment-Specific Secrets

Use Kubernetes secrets per environment:

```bash
# Create dev secrets
kubectl create secret generic app-secrets \
  --namespace=myapp-dev \
  --from-literal=redis-password=dev-redis-pass \
  --from-literal=pg-password=dev-pg-pass

# Create staging secrets
kubectl create secret generic app-secrets \
  --namespace=myapp-staging \
  --from-literal=redis-password=staging-redis-pass \
  --from-literal=pg-password=staging-pg-pass

# Create production secrets (use external secret manager)
kubectl create secret generic app-secrets \
  --namespace=myapp-production \
  --from-literal=redis-password=$(vault kv get -field=password secret/prod/redis) \
  --from-literal=pg-password=$(vault kv get -field=password secret/prod/postgresql)
```

### Compare Configurations

Diff between environments to understand differences:

```bash
# Compare dev vs staging
diff config-dev.yaml config-staging.yaml

# Compare values files
diff values/redis-dev.yaml values/redis-production.yaml
```

### Environment Promotion

Promote tested configurations:

```bash
# Copy staging config to production (with manual review)
cp config-staging.yaml config-production.yaml
# Edit config-production.yaml to update:
# - namespace: myapp-production
# - global_labels.environment: production
# - values files to use *-production.yaml

# Deploy to production
./deploy.sh production
```

## 📊 Configuration Differences

### Resource Scaling

| Resource | Development | Staging | Production |
|----------|------------|---------|------------|
| **Redis CPU** | 100m | 300m | 1000m |
| **Redis Memory** | 128Mi | 256Mi | 1Gi |
| **Redis Replicas** | 0 | 1 | 2 |
| **Redis Persistence** | Disabled | 4Gi | 10Gi |
| **PostgreSQL CPU** | 200m | 500m | 2000m |
| **PostgreSQL Memory** | 256Mi | 512Mi | 2Gi |
| **PostgreSQL Persistence** | Disabled | 8Gi | 20Gi |
| **Backend Replicas** | 1 | 2 | 3 |
| **Backend CPU** | 100m | 300m | 1000m |
| **Backend Memory** | 128Mi | 256Mi | 1Gi |
| **Autoscaling** | Disabled | 2-5 pods | 3-20 pods |

### Feature Enablement

| Feature | Development | Staging | Production |
|---------|------------|---------|------------|
| **Persistence** | ❌ | ✅ | ✅ |
| **Metrics** | ❌ | ✅ | ✅ |
| **Backup** | ❌ | ❌ | ✅ |
| **Autoscaling** | ❌ | ✅ | ✅ |
| **High Availability** | ❌ | ⚠️ (partial) | ✅ |
| **Monitoring** | ❌ | ✅ | ✅ |

### Cost Estimation

Based on typical cloud pricing (AWS):

- **Development**: ~$50/month
  - Minimal resources, no persistence
  - Single replicas, no HA

- **Staging**: ~$200/month
  - Moderate resources, persistence enabled
  - Some redundancy, autoscaling

- **Production**: ~$800/month
  - Full resources, HA enabled
  - Backup, monitoring, autoscaling
  - Multiple replicas across zones

## 🎓 Use Cases

### 1. Development Environment

Minimal resources for local/dev testing:

```yaml
# config-dev.yaml
- No persistence (fast pod restart)
- Single replica (no HA)
- Small resource limits
- NodePort service (easy access)
```

**Benefits**:
- Fast iteration cycles
- Low cost
- Easy debugging

### 2. Staging Environment

Production-like environment for QA:

```yaml
# config-staging.yaml
- Persistence enabled
- Some redundancy (1 replica)
- Moderate resources
- LoadBalancer service
- Metrics enabled
```

**Benefits**:
- Validates production configs
- Performance testing
- Integration testing
- Cost-effective pre-production

### 3. Production Environment

Full-scale, highly available deployment:

```yaml
# config-production.yaml
- Full persistence with backup
- High availability (2+ replicas)
- Full resource allocation
- Monitoring and alerting
- Autoscaling enabled
```

**Benefits**:
- Reliable and resilient
- Handles production load
- Quick recovery
- Performance optimized

## 🐛 Troubleshooting

### Issue: Wrong Environment Deployed

**Problem**: Accidentally deployed production config to dev namespace

**Solution**: Always verify config before deploying:

```bash
# Check which namespace is in the config
grep "^namespace:" config-production.yaml

# Dry run to verify
sbkube apply --app-dir . --config config-production.yaml --dry-run
```

### Issue: Value File Not Found

**Problem**: `values/redis-production.yaml: No such file`

**Solution**: Ensure all referenced value files exist:

```bash
# List all value files
ls -la values/

# Check config references
grep "values:" config-production.yaml
```

### Issue: Unexpected Configuration

**Problem**: Production using dev passwords

**Solution**: Verify value file layering order:

```yaml
# Ensure correct order (base first, override last)
apps:
  redis:
    values:
      - values/redis-base.yaml        # ✅ Base first
      - values/redis-production.yaml  # ✅ Override last
```

### Issue: Resource Limits Too Low

**Problem**: Pods getting OOMKilled in staging

**Solution**: Gradually increase limits:

```yaml
# Start conservative, then increase based on actual usage
resources:
  limits:
    memory: 512Mi  # Try doubling if OOMKilled
```

## 📝 Best Practices

### 1. Start with Base Configuration

Define common settings in base values:

```yaml
# redis-base.yaml - Settings shared across all environments
architecture: standalone
auth:
  enabled: true
```

### 2. Override Only What Differs

Keep environment overrides minimal:

```yaml
# redis-production.yaml - Only production-specific changes
auth:
  password: "production-specific-password"
master:
  persistence:
    size: 10Gi  # Larger than staging
```

### 3. Use Consistent Naming

Follow clear naming conventions:

```
Pattern: <app>-<env>.yaml
Examples:
- redis-dev.yaml
- redis-staging.yaml
- redis-production.yaml
```

### 4. Document Differences

Add comments explaining why environments differ:

```yaml
# redis-production.yaml
master:
  persistence:
    size: 10Gi  # Larger due to production data volume
  resources:
    limits:
      cpu: 1000m  # Higher CPU for production load
```

### 5. Test in Lower Environments First

Always deploy in order: dev → staging → production

```bash
# Never skip environments
./deploy.sh dev      # ✅ Test first
./deploy.sh staging  # ✅ Validate
./deploy.sh prod     # ✅ Deploy to prod
```

### 6. Use Version Control

Track environment configurations in Git:

```bash
git add config-*.yaml values/
git commit -m "feat: add production environment config"
git tag v1.0.0-prod
```

### 7. Separate Secrets

Never commit secrets to Git:

```yaml
# ❌ Bad - hardcoded password
auth:
  password: "my-secret-password"

# ✅ Good - reference external secret
auth:
  existingSecret: app-secrets
  existingSecretPasswordKey: redis-password
```

## 🔗 Related Examples

- **[05-multi-cluster](../05-multi-cluster/)** - Multi-cluster deployment pattern
- **[07-canary-deployment](../07-canary-deployment/)** - Canary deployment pattern
- **[08-blue-green](../08-blue-green/)** - Blue-green deployment pattern
- **[01-dev-environment](../../use-cases/01-dev-environment/)** - Complete dev environment
- **[03-monitoring-stack](../../use-cases/03-monitoring-stack/)** - Monitoring setup

## 📚 Additional Resources

- [SBKube Configuration Schema](../../../docs/03-configuration/config-schema.md)
- [Helm Chart Customization](../../../docs/03-configuration/chart-customization.md)
- [Best Practices](../../../docs/05-best-practices/directory-structure.md)
- [Helm Values Merging](https://helm.sh/docs/chart_template_guide/values_files/)

## 🎯 Summary

This example demonstrates:

- ✅ Base + Override configuration pattern
- ✅ Environment-specific resource scaling
- ✅ Value file layering (Helm merge behavior)
- ✅ Progressive deployment pipeline (dev → staging → prod)
- ✅ Cost optimization per environment
- ✅ Security isolation with separate namespaces
- ✅ CI/CD integration for automated deployments

**Key Takeaway**: SBKube's value file layering makes it simple to maintain environment parity while scaling resources appropriately for each stage of the deployment pipeline.
