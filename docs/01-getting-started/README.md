______________________________________________________________________

## type: User Guide audience: End User topics: [installation, quickstart, first-deployment] llm_priority: high last_updated: 2025-01-04

# 🚀 Getting Started with SBKube

Your quickstart guide to deploying applications with SBKube.

> **Key Features**: Simplified configuration, unified Helm types, chart customization
>
> Previous version users: See the [Migration Guide](../03-configuration/migration-guide.md)

______________________________________________________________________

## TL;DR

- **Install**: `pip install sbkube` or `uv pip install sbkube`
- **Quick Deploy**: Create `sources.yaml` → `sbkube apply`
- **First Steps**: init → validate → apply
- **Related**: [Commands Reference](../02-features/commands.md)

______________________________________________________________________

## 📦 Installation

### Requirements

- **Python 3.14+**
- **kubectl** - Kubernetes cluster access
- **helm** - Helm chart management

### Install from PyPI

```bash
# Install latest stable version
pip install sbkube

# Or using uv (recommended)
uv tool install sbkube

# Verify installation
sbkube version
```

### Development Installation

```bash
# Clone repository
git clone https://github.com/ScriptonBasestar/kube-app-manager.git
cd sb-kube-app-manager

# Install with uv (recommended)
uv venv
source .venv/bin/activate
uv pip install -e .
```

______________________________________________________________________

## 🎯 Quick Start

### Minimal Example

Create two files and deploy in minutes:

**`sources.yaml`** - Define external sources:

```yaml
# Cluster configuration (required since v0.4.10)
kubeconfig: ~/.kube/config
kubeconfig_context: my-cluster

# Helm repositories
helm_repos:
  nginx: https://kubernetes.github.io/ingress-nginx
```

**`config.yaml`** - Define applications:

```yaml
namespace: default

apps:
  nginx-ingress:
    type: helm
    chart: nginx/ingress-nginx
    namespace: ingress-nginx
    release_name: my-nginx
```

**Deploy**:

```bash
# Single command deployment
sbkube apply

# Or with options
sbkube apply --app-dir . --namespace default
```

______________________________________________________________________

## 🚀 First Deployment - Step by Step

### Step 1: Prepare Your Environment

**Create a test cluster** (if needed):

```bash
# Using Kind (recommended)
kind create cluster --name sbkube-tutorial

# Or using Minikube
minikube start --profile sbkube-tutorial

# Verify cluster
kubectl cluster-info
```

### Step 2: Initialize Project

```bash
# Create project directory
mkdir my-sbkube-project
cd my-sbkube-project

# Interactive initialization
sbkube init

# Or non-interactive
sbkube init --name my-app --template basic --non-interactive
```

This creates:

```
my-sbkube-project/
├── config.yaml       # Application definitions
└── sources.yaml      # External sources
```

### Step 3: Configure Your First App

**Edit `sources.yaml`**:

```yaml
# Cluster settings
kubeconfig: ~/.kube/config
kubeconfig_context: kind-sbkube-tutorial
cluster: tutorial  # Optional, for documentation

# Helm repositories
helm_repos:
  grafana: https://grafana.github.io/helm-charts
```

**Edit `config.yaml`**:

```yaml
namespace: tutorial

apps:
  grafana:
    type: helm
    chart: grafana/grafana
    version: 6.50.0
    values:
      - values/grafana.yaml
```

**Create `values/grafana.yaml`**:

```yaml
replicas: 1
adminPassword: "admin"
resources:
  requests:
    cpu: 100m
    memory: 128Mi
  limits:
    cpu: 200m
    memory: 256Mi
```

### Step 4: Validate Configuration

```bash
# Validate configuration files
sbkube validate

# Expected output:
# ✅ Config file validation passed
# ✅ All required fields present
# ✅ No validation errors found
```

### Step 5: Deploy

**Option A - Single Command** (Recommended):

```bash
# Deploy everything
sbkube apply

# With dry-run to preview
sbkube apply --dry-run
```

**Option B - Step by Step**:

```bash
# 1. Prepare external sources
sbkube prepare

# 2. Build (if customization needed)
sbkube build

# 3. Preview generated manifests
sbkube template

# 4. Deploy to cluster
sbkube deploy
```

### Step 6: Verify Deployment

```bash
# Check pods
kubectl get pods -n tutorial

# Check Helm releases
helm list -n tutorial

# Check deployment history
sbkube history

# Access Grafana
kubectl port-forward -n tutorial svc/grafana 3000:80
# Open http://localhost:3000 (admin/admin)
```

______________________________________________________________________

## 🔄 Managing Applications

### Check for Updates (v0.9.1+)

```bash
# Check for available chart updates
sbkube check-updates

# Example output:
# 📊 Available Updates:
# grafana  6.50.0 → 7.0.0  🔴 major
# redis    18.0.0 → 18.5.1 🟡 minor

# Interactive config.yaml update
sbkube check-updates --update-config

# Combined with status
sbkube status --check-updates
```

### Update Application

```bash
# Edit values/grafana.yaml
# Then apply changes
sbkube apply

# Or use upgrade command
sbkube upgrade --namespace tutorial
```

### View History

```bash
# View deployment history
sbkube history --namespace tutorial

# Example output:
# ID  App      Version  Status    Deployed At
# 2   grafana  6.50.0   success   2025-01-04 10:35:20
# 1   grafana  6.50.0   success   2025-01-04 10:30:45
```

### Delete Application

```bash
# Preview deletion
sbkube delete --dry-run

# Delete application
sbkube delete

# Clean up namespace
kubectl delete namespace tutorial
```

______________________________________________________________________

## 📚 Common Deployment Patterns

### Pattern 1: Remote Helm Chart

```yaml
apps:
  prometheus:
    type: helm
    chart: prometheus-community/prometheus
    version: 25.0.0
    values:
      - values/prometheus.yaml
```

### Pattern 2: Local Helm Chart

```yaml
apps:
  my-app:
    type: helm
    chart: ./charts/my-app
    values:
      - values/my-app.yaml
```

### Pattern 3: YAML Manifests

```yaml
apps:
  simple-app:
    type: yaml
    files:
      - manifests/deployment.yaml
      - manifests/service.yaml
```

### Pattern 4: Git Repository

```yaml
# In sources.yaml
git_repos:
  my-repo:
    url: https://github.com/example/charts.git
    branch: main

# In config.yaml
apps:
  from-git:
    type: git
    repo: my-repo
    path: charts/app
```

### Pattern 5: Chart Customization

```yaml
apps:
  custom-app:
    type: helm
    chart: prometheus-community/kube-state-metrics
    overrides:
      templates/secret.yaml: custom/secret.yaml
    removes:
      - templates/networkpolicy.yaml
```

______________________________________________________________________

## 💡 Tips and Best Practices

### Development Workflow

```bash
# Deploy specific app only
sbkube apply --app grafana

# Always validate first
sbkube validate

# Use dry-run for safety
sbkube deploy --dry-run

# Skip build when not needed
sbkube apply --skip-build
```

### Configuration Management

- **Environment Separation**: Use different config directories for dev/staging/prod
- **Values Organization**: Keep Helm values in `values/` directory
- **Namespace Strategy**: Use meaningful namespaces for logical separation
- **Version Pinning**: Always specify chart versions for reproducibility

### Troubleshooting Quick Fixes

| Problem | Solution | |---------|----------| | Helm repo unreachable | Run `helm repo add` manually | | Pod not
starting | Check `kubectl describe pod` for events | | sbkube apply fails | Run `sbkube doctor` for diagnostics | |
Permission denied | Verify RBAC with `kubectl auth can-i` |

______________________________________________________________________

## 📖 Next Steps

### Learn More

- **[Commands Reference](../02-features/commands.md)** - Detailed command options
- **[Application Types](../02-features/application-types.md)** - All 10 supported app types
- **[Configuration Guide](../03-configuration/)** - Advanced configuration

### Explore Examples

- **[Example Scenarios](../06-examples/)** - Real-world deployment patterns
- **[examples/ Directory](../../examples/)** - Runnable examples

### Get Help

- **[Troubleshooting Guide](../07-troubleshooting/)** - Common issues and solutions
- **[FAQ](../07-troubleshooting/faq.md)** - Frequently asked questions
- **[GitHub Issues](https://github.com/ScriptonBasestar/kube-app-manager/issues)** - Report bugs

______________________________________________________________________

## 🚨 Important Notes

### Security

- Always review Helm values before deployment
- Use RBAC to limit permissions
- Store secrets securely (not in Git)

### Production Readiness

- Test in staging environment first
- Set resource limits appropriately
- Configure health checks and probes
- Plan for backup and disaster recovery

### Resource Management

- Monitor cluster resources before deployment
- Set appropriate requests and limits
- Use horizontal pod autoscaling when needed

______________________________________________________________________

*Thank you for using SBKube! For issues or questions, visit our
[GitHub repository](https://github.com/ScriptonBasestar/kube-app-manager).*
