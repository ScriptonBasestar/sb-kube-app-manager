# Usage Guide - SBKube

> **Quick Reference**: Essential commands and workflows for SBKube v0.11.0
>
> **For Complete Details**: See [Commands Reference](docs/02-features/commands.md) and [Features Documentation](docs/02-features/)

---

## Quick Start

### Installation
```bash
# Using pip
pip install sbkube

# Using uv (recommended)
uv tool install sbkube

# Verify installation
sbkube version  # Expected: 0.11.0
```

### First Deployment (5 Minutes)
```bash
# 1. Initialize project
sbkube init

# 2. Validate environment
sbkube doctor

# 3. Preview deployment
sbkube apply --dry-run

# 4. Deploy to cluster
sbkube apply
```

---

## Core Workflow

### The Unified Command: `apply`

SBKube's primary workflow is the `apply` command, which executes all four deployment stages:

```bash
sbkube apply
# Executes: prepare → build → template → deploy
```

**What happens:**
1. **Prepare**: Downloads Helm charts and Git repositories
2. **Build**: Customizes charts with overrides and removes
3. **Template**: Renders Kubernetes manifests
4. **Deploy**: Applies resources to your cluster

### Step-by-Step Workflow

For more control, run each stage individually:

```bash
# 1. Download sources
sbkube prepare

# 2. Customize applications
sbkube build

# 3. Generate manifests
sbkube template

# 4. Deploy to cluster
sbkube deploy
```

---

## Common Use Cases

### Daily Development

```bash
# Validate before deploying
sbkube validate

# Deploy to development
sbkube --profile development apply

# Check status
sbkube status

# View logs (use kubectl)
kubectl logs -n <namespace> <pod>
```

### Managing Updates (v0.9.1+)

```bash
# Check for chart updates
sbkube check-updates

# Example output:
# 📊 Available Updates:
# grafana  6.50.0 → 7.0.0  🔴 major
# redis    18.0.0 → 18.5.1 🟡 minor
# nginx    1.2.3  → 1.2.4  🟢 patch

# Interactively update config.yaml
sbkube check-updates --update-config

# Combined status + update check
sbkube status --check-updates

# Apply updates
sbkube apply
```

### Production Deployment

```bash
# Use production profile
sbkube --profile production --namespace production apply

# Monitor deployment
sbkube status --namespace production

# Check deployment health
sbkube status --unhealthy

# View deployment history
sbkube history --namespace production
```

### Troubleshooting

```bash
# Run system diagnostics
sbkube doctor --detailed

# Check specific component
sbkube doctor --check k8s-connectivity

# Dry-run to preview changes
sbkube apply --dry-run

# View unhealthy resources
sbkube status --unhealthy

# Rollback to previous version
sbkube rollback <deployment-id>
```

### Cleanup

```bash
# Preview deletion
sbkube delete --dry-run

# Delete all applications
sbkube delete

# Delete specific app
sbkube delete --app nginx

# Skip errors for non-existent resources
sbkube delete --skip-not-found
```

---

## Key Features

### 1. Unified Configuration

Single `config.yaml` file defines all applications:

```yaml
namespace: production

apps:
  nginx:
    type: helm
    chart: nginx/nginx-ingress
    version: 4.5.2
    values:
      - nginx-values.yaml

  database:
    type: helm
    chart: bitnami/postgresql
    depends_on:
      - storage
```

**Supported App Types:**
- `helm` - Helm charts (remote or local)
- `yaml` - Raw Kubernetes manifests
- `git` - Git repositories
- `kustomize` - Kustomize applications
- `http` - HTTP-downloadable resources
- `action` - Custom kubectl actions
- `exec` - Shell commands
- `hook` - Deployment hooks
- `noop` - Placeholders

### 2. Multi-Environment Support

Use profiles for different environments:

```bash
# Development
sbkube --profile development apply

# Staging
sbkube --profile staging apply

# Production
sbkube --profile production apply
```

Configuration inheritance:
```
config.yaml (base)
  ↓
config-development.yaml (overrides)
```

### 3. Dependency Management

Automatic ordering based on `depends_on`:

```yaml
apps:
  storage:
    type: helm
    chart: openebs/openebs

  database:
    type: helm
    chart: bitnami/postgresql
    depends_on:
      - storage  # Deploys after storage

  application:
    type: helm
    chart: ./my-app
    depends_on:
      - database  # Deploys after database
```

### 4. Advanced Customization

**Helm Chart Overrides:**
```yaml
apps:
  grafana:
    type: helm
    chart: grafana/grafana
    overrides:
      - path: templates/deployment.yaml
        file: custom-deployment.yaml
```

**Resource Removal:**
```yaml
apps:
  loki:
    type: helm
    chart: grafana/loki
    removes:
      - templates/servicemonitor.yaml
```

### 5. Hooks System

Execute custom scripts at workflow stages:

```yaml
apps:
  myapp:
    type: helm
    chart: ./my-chart
    hooks:
      pre_deploy:
        - command: ./scripts/backup-db.sh
      post_deploy:
        - command: ./scripts/verify-deployment.sh
      on_failure:
        - command: ./scripts/rollback.sh
```

### 6. State Management

Track deployment history and enable rollbacks:

```bash
# View deployment history
sbkube history

# Show specific deployment
sbkube history --show <deployment-id>

# Compare deployments
sbkube history --diff <id1> <id2>

# Rollback to previous state
sbkube rollback <deployment-id>
```

### 7. LLM-Friendly Output (v0.7.0+)

Optimized output for AI agents and automation:

```bash
# LLM-optimized output (80-90% token reduction)
sbkube --format llm apply

# JSON format
sbkube --format json status

# YAML format
sbkube --format yaml status

# Environment variable
export SBKUBE_OUTPUT_FORMAT=llm
sbkube apply  # Uses LLM format
```

### 8. Multi-Phase Orchestration (v0.11.0+)

Multi-phase deployment for complex environments:

```bash
# Validate + preview workflow
sbkube apply -f sbkube.yaml --dry-run

# Deploy phases in dependency order
sbkube apply -f sbkube.yaml

# Deploy specific phase (with dependencies)
sbkube apply -f sbkube.yaml --phase p2-data

# Check runtime status/history
sbkube status
sbkube history
```

---

## Command Quick Reference

### Essential Commands

| Command | Purpose | Example |
|---------|---------|---------|
| `apply` | Complete workflow | `sbkube apply` |
| `validate` | Check configuration | `sbkube validate` |
| `status` | Check deployment status | `sbkube status --managed` |
| `history` | View deployment history | `sbkube history` |
| `check-updates` | Check chart updates | `sbkube check-updates` |

### Utility Commands

| Command | Purpose | Example |
|---------|---------|---------|
| `init` | Initialize project | `sbkube init --template basic` |
| `doctor` | System diagnostics | `sbkube doctor --detailed` |
| `version` | Show version | `sbkube version` |

### Management Commands

| Command | Purpose | Example |
|---------|---------|---------|
| `upgrade` | Upgrade releases | `sbkube upgrade` |
| `delete` | Remove deployments | `sbkube delete --dry-run` |
| `rollback` | Revert to previous | `sbkube rollback <id>` |

### Advanced Commands

| Command | Purpose | Example |
|---------|---------|---------|
| `prepare` | Download sources | `sbkube prepare --force` |
| `build` | Customize apps | `sbkube build --app nginx` |
| `template` | Render manifests | `sbkube template --output-dir /tmp` |
| `deploy` | Apply to cluster | `sbkube deploy --dry-run` |

---

## Common Options

### Global Options (All Commands)
- `--kubeconfig PATH` - Kubernetes config file
- `--context NAME` - Kubernetes context
- `--namespace NS` - Default namespace
- `--format {human|llm|json|yaml}` - Output format
- `-v, --verbose` - Verbose logging

### Workflow Options
- `--app-dir PATH` - Configuration directory
- `--app NAME` - Process specific app
- `--profile NAME` - Environment profile
- `--dry-run` - Preview without applying

---

## Target Users

### DevOps Engineers
- **Need**: Consistent, repeatable deployments across environments
- **Use**: Profiles, dependency management, state tracking
- **Benefit**: Reduced deployment errors, automated workflows

### Platform Engineers
- **Need**: Infrastructure automation and multi-cluster management
- **Use**: Multi-phase orchestration (`sbkube.yaml`), hooks system, LLM integration
- **Benefit**: Scalable deployment pipelines

### Solo Developers
- **Need**: Simple k3s deployment without complexity
- **Use**: Single `apply` command, init templates
- **Benefit**: 5-minute setup to production

### AI Agents
- **Need**: Automated deployment and monitoring
- **Use**: `--format llm`, JSON output, status commands
- **Benefit**: Token-efficient, machine-readable output

---

## Example Workflows

### Simple Web App
```bash
# Initialize
sbkube init --template webapp

# Edit config.yaml to add nginx, postgresql

# Deploy
sbkube apply
```

### Microservices Stack
```bash
# Use unified config for phased deployment
cat > sbkube.yaml << EOF
apiVersion: sbkube/v1
metadata:
  name: microservices-stack
phases:
  infrastructure:
    source: infra/sbkube.yaml
  databases:
    source: data/sbkube.yaml
    depends_on: [infrastructure]
  applications:
    source: apps/sbkube.yaml
    depends_on: [databases]
EOF

# Deploy all phases
sbkube apply -f sbkube.yaml
```

### GitOps Workflow
```bash
# In CI/CD pipeline
sbkube validate
sbkube apply --dry-run
sbkube --profile production apply
sbkube status --unhealthy && exit 1
```

---

## Next Steps

- **Configuration Guide**: [Config Schema](docs/03-configuration/config-schema.md)
- **Complete Command Reference**: [Commands Documentation](docs/02-features/commands.md)
- **Application Types**: [App Types Guide](docs/02-features/application-types.md)
- **Hooks System**: [Hooks Guide](docs/02-features/hooks-guide.md)
- **Unified Multi-Phase Guide**: [Config Schema](docs/03-configuration/config-schema.md)
- **Troubleshooting**: [Common Issues](docs/07-troubleshooting/README.md)
- **Examples**: [Example Configurations](examples/)

---

**Document Version**: 1.0
**Last Updated**: 2026-02-25
**SBKube Version**: 0.11.0
