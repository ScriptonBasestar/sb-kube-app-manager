---
type: External Reference
audience: AI Agent
topics: [quickstart, commands, configuration, examples]
llm_priority: high
external_reference: true
last_updated: 2025-01-04
---

# SBKube LLM Guide

> **AI-Optimized Documentation for Using SBKube in Other Projects**
>
> **Target Audience**: AI assistants helping developers use SBKube
> **Format**: Token-optimized, section-based reference
> **Version**: v0.6.1
> **Last Updated**: 2025-01-04

---

## 📋 Table of Contents

- [Quick Start](#quick-start) (~500 tokens)
- [Commands Reference](#commands-reference) (~2000 tokens)
- [Configuration Guide](#configuration-guide) (~2000 tokens)
- [Examples](#examples) (~3000 tokens)
- [Troubleshooting](#troubleshooting) (~1000 tokens)

**Total**: ~10KB, 3500 tokens

---

## Quick Start

### What is SBKube?

SBKube is a Kubernetes deployment automation CLI for k3s that simplifies the process of deploying applications using a unified workflow: `prepare → build → template → deploy`.

### Core Workflow

```bash
# All-in-one command (most common)
sbkube apply

# Or step-by-step
sbkube prepare   # Download sources (Helm charts, Git repos)
sbkube build     # Customize and build
sbkube template  # Render Kubernetes manifests
sbkube deploy    # Deploy to k3s cluster
```

### Minimal Setup

**1. Install SBKube**:
```bash
pip install sbkube
# or
uv pip install sbkube
```

**2. Create `sources.yaml`** (defines what to deploy):
```yaml
apps:
  - name: myapp
    type: web
    git: https://github.com/user/repo
    dockerfile_path: ./Dockerfile
    helm_chart: ./charts/app
```

**3. Deploy**:
```bash
sbkube apply
```

### Key Concepts

- **sources.yaml**: Defines applications and their sources (Git, Helm, etc.)
- **.sbkube/**: Working directory (auto-created, gitignored)
  - `charts/`: Downloaded Helm charts
  - `repos/`: Cloned Git repositories
  - `build/`: Built artifacts
  - `rendered/`: Final Kubernetes manifests
- **App Types**: `web`, `worker`, `scheduled`, `helm`, `yaml`, `git`, `http`, `kustomize`

---

## Commands Reference

### Core Workflow Commands

#### `sbkube apply`

**Purpose**: Execute complete deployment workflow (most commonly used)

**Usage**:
```bash
sbkube apply [OPTIONS]
```

**Key Options**:
- `--dry-run`: Preview deployment without applying
- `--quiet`: Minimal output
- `--format {human|llm|json|yaml}`: Output format (default: human)
- `--profile PROFILE`: Use specific configuration profile

**Example**:
```bash
# Standard deployment
sbkube apply

# Preview deployment
sbkube apply --dry-run

# Deploy with LLM-friendly output
sbkube apply --format llm --quiet
```

---

#### `sbkube prepare`

**Purpose**: Download and prepare sources (Helm charts, Git repos)

**Supported Sources**:
- Helm charts (from remote repos or local paths)
- Git repositories
- HTTP(S) URLs
- Kustomize directories

**Usage**:
```bash
sbkube prepare [OPTIONS]
```

**Output**: `.sbkube/charts/`, `.sbkube/repos/`

---

#### `sbkube build`

**Purpose**: Build and customize applications

**Capabilities**:
- Apply Helm chart overrides
- Extract specific paths from Git repos
- Run Kustomize builds
- Docker image builds (if configured)

**Usage**:
```bash
sbkube build [OPTIONS]
```

**Output**: `.sbkube/build/`

---

#### `sbkube template`

**Purpose**: Render Kubernetes manifests with environment-specific values

**Supported Formats**:
- Helm chart rendering
- YAML template processing (Jinja2)
- Kustomize overlays

**Usage**:
```bash
sbkube template [OPTIONS]
```

**Output**: `.sbkube/rendered/`

---

#### `sbkube deploy`

**Purpose**: Deploy rendered manifests to k3s cluster

**Methods**:
- Helm releases
- kubectl apply
- Kustomize apply

**Usage**:
```bash
sbkube deploy [OPTIONS]
```

---

### Utility Commands

#### `sbkube init`

**Purpose**: Initialize new project (run once)

**Usage**:
```bash
sbkube init [OPTIONS]
```

**Creates**:
- `sources.yaml` template
- `.sbkube/` directory structure
- Example configuration files

---

#### `sbkube validate`

**Purpose**: Validate configuration files

**Usage**:
```bash
sbkube validate [OPTIONS]
```

**Checks**:
- YAML syntax
- Pydantic schema validation
- Dependency resolution
- Required fields

---

#### `sbkube doctor`

**Purpose**: System diagnostic and health check

**Usage**:
```bash
sbkube doctor [OPTIONS]
```

**Checks**:
- kubectl connectivity
- Helm installation
- Network access
- Configuration validity
- Dependency directories (for app-group deps)

**Example**:
```bash
sbkube doctor --detailed
```

---

#### `sbkube status`

**Purpose**: Check deployment status (v0.6.0+)

**Usage**:
```bash
sbkube status [OPTIONS]
```

**Features**:
- Real-time cluster state
- Cached state for performance
- Health checks

---

#### `sbkube history`

**Purpose**: View deployment history (v0.6.0+)

**Usage**:
```bash
sbkube history [OPTIONS]
```

**Features**:
- Deployment timeline
- Diff between revisions
- Values diff

---

### Management Commands

#### `sbkube upgrade`

**Purpose**: Upgrade Helm releases

**Usage**:
```bash
sbkube upgrade [APP_NAME] [OPTIONS]
```

---

#### `sbkube delete`

**Purpose**: Delete deployed resources

**Usage**:
```bash
sbkube delete [OPTIONS]

# Preview deletion
sbkube delete --dry-run
```

---

#### `sbkube rollback`

**Purpose**: Rollback to previous deployment

**Usage**:
```bash
sbkube rollback [APP_NAME] [REVISION] [OPTIONS]
```

---

### Common Options (All Commands)

- `--app-dir PATH`: Configuration directory (default: current directory)
- `--base-dir PATH`: Working directory (default: .)
- `--app NAME`: Process specific app only
- `--help`: Show command help

---

## Configuration Guide

### sources.yaml Schema

**Location**: Project root (defines location of `.sbkube/` working directory)

**Basic Structure**:
```yaml
apps:
  - name: app-name          # Required: Application name
    type: {app-type}        # Required: Application type
    enabled: true           # Optional: Enable/disable (default: true)
    namespace: default      # Optional: Kubernetes namespace
    depends_on: []          # Optional: App dependencies

    # Type-specific fields below
```

---

### Application Types

#### 1. `web` - Web Application

```yaml
apps:
  - name: myapp
    type: web
    git: https://github.com/user/repo
    dockerfile_path: ./Dockerfile
    helm_chart: ./charts/app
    values:
      - values.yaml
```

**Fields**:
- `git`: Git repository URL
- `dockerfile_path`: Path to Dockerfile (for build)
- `helm_chart`: Path to Helm chart in repo
- `values`: List of values files

---

#### 2. `worker` - Background Worker

```yaml
apps:
  - name: worker
    type: worker
    git: https://github.com/user/worker
    dockerfile_path: ./Dockerfile
    helm_chart: ./charts/worker
```

**Use Case**: Celery workers, queue processors, background jobs

---

#### 3. `scheduled` - Scheduled Job (CronJob)

```yaml
apps:
  - name: backup
    type: scheduled
    git: https://github.com/user/backup
    dockerfile_path: ./Dockerfile
    helm_chart: ./charts/cronjob
    schedule: "0 2 * * *"
```

**Fields**:
- `schedule`: Cron expression

---

#### 4. `helm` - Pure Helm Chart

```yaml
apps:
  - name: grafana
    type: helm
    helm:
      repo: grafana
      chart: grafana
      version: "6.50.0"
      release_name: grafana
      values:
        - grafana-values.yaml
```

**Use Case**: Deploy existing Helm charts (Prometheus, Grafana, etc.)

---

#### 5. `yaml` - Plain YAML Manifests

```yaml
apps:
  - name: config
    type: yaml
    yaml:
      path: manifests/
```

**Use Case**: Deploy raw Kubernetes YAML files

---

#### 6. `git` - Git Repository

```yaml
apps:
  - name: templates
    type: git
    git:
      url: https://github.com/user/templates
      branch: main
      path: k8s/
```

---

#### 7. `kustomize` - Kustomize

```yaml
apps:
  - name: overlays
    type: kustomize
    kustomize:
      path: overlays/production
```

---

### Advanced Configuration

#### App Dependencies

```yaml
apps:
  - name: database
    type: helm
    helm:
      repo: bitnami
      chart: postgresql

  - name: backend
    type: web
    depends_on:
      - database  # Deploy database first
    git: https://github.com/user/backend
```

---

#### App-Group Dependencies (v0.6.0+)

**Directory Structure**:
```
project/
├── a000_infra_network/
│   └── sources.yaml
├── a101_data_rdb/
│   └── sources.yaml
└── a302_devops/
    └── sources.yaml (this group)
```

**sources.yaml** (in `a302_devops/`):
```yaml
namespace: devops
deps:
  - a000_infra_network  # Requires network infra
  - a101_data_rdb       # Requires database

apps:
  - name: harbor
    type: helm
    helm:
      repo: harbor
      chart: harbor
```

**Validation**:
- `sbkube doctor`: Checks if dependency directories exist
- `sbkube apply`: Verifies dependencies are deployed before proceeding

---

#### Helm Chart Overrides

```yaml
apps:
  - name: customized-chart
    type: helm
    helm:
      repo: stable
      chart: nginx
      overrides:
        remove_files:
          - templates/ingress.yaml
        add_files:
          - source: custom-ingress.yaml
            target: templates/ingress.yaml
      values:
        - custom-values.yaml
```

---

#### Environment Profiles

```yaml
# sources.yaml
apps:
  - name: app
    type: web
    profiles:
      dev:
        replicas: 1
      prod:
        replicas: 3
```

**Usage**:
```bash
sbkube apply --profile prod
```

---

## Examples

### Example 1: Simple Web Application

**Scenario**: Deploy a Python Flask app with PostgreSQL

**Directory Structure**:
```
myproject/
├── sources.yaml
└── values/
    ├── db-values.yaml
    └── app-values.yaml
```

**sources.yaml**:
```yaml
apps:
  - name: database
    type: helm
    helm:
      repo: bitnami
      chart: postgresql
      version: "12.0.0"
      release_name: myapp-db
      values:
        - values/db-values.yaml

  - name: backend
    type: web
    depends_on:
      - database
    git: https://github.com/user/flask-app
    dockerfile_path: ./Dockerfile
    helm_chart: ./charts/web
    values:
      - values/app-values.yaml
```

**values/db-values.yaml**:
```yaml
auth:
  username: appuser
  password: changeme
  database: appdb
```

**values/app-values.yaml**:
```yaml
image:
  repository: myregistry/flask-app
  tag: latest
env:
  - name: DATABASE_URL
    value: postgresql://appuser:changeme@myapp-db:5432/appdb
```

**Deploy**:
```bash
sbkube apply
```

---

### Example 2: Multi-Tier Application with Dependencies

**Scenario**: Deploy monitoring stack (Prometheus + Grafana)

**sources.yaml**:
```yaml
apps:
  - name: prometheus
    type: helm
    helm:
      repo: prometheus-community
      chart: prometheus
      version: "15.0.0"
      release_name: prometheus
      values:
        - prometheus-values.yaml

  - name: grafana
    type: helm
    depends_on:
      - prometheus
    helm:
      repo: grafana
      chart: grafana
      version: "6.50.0"
      release_name: grafana
      values:
        - grafana-values.yaml
```

**grafana-values.yaml**:
```yaml
datasources:
  datasources.yaml:
    apiVersion: 1
    datasources:
      - name: Prometheus
        type: prometheus
        url: http://prometheus-server
        isDefault: true
```

---

### Example 3: App-Group Management (v0.6.0+)

**Scenario**: Deploy Harbor registry with infrastructure dependencies

**Directory Structure**:
```
k8s-apps/
├── a000_infra_network/
│   └── sources.yaml (Cilium CNI)
├── a101_data_rdb/
│   └── sources.yaml (PostgreSQL)
└── a302_devops/
    └── sources.yaml (Harbor)
```

**a302_devops/sources.yaml**:
```yaml
namespace: devops
deps:
  - a000_infra_network
  - a101_data_rdb

apps:
  - name: harbor
    type: helm
    helm:
      repo: harbor
      chart: harbor
      version: "1.13.0"
      release_name: harbor
      values:
        - harbor-values.yaml
```

**Deploy**:
```bash
cd k8s-apps/a302_devops
sbkube doctor  # Verifies dependency dirs exist
sbkube apply   # Verifies dependencies are deployed
```

---

### Example 4: Customizing Existing Helm Chart

**Scenario**: Remove default Ingress and add custom one

**sources.yaml**:
```yaml
apps:
  - name: nginx
    type: helm
    helm:
      repo: bitnami
      chart: nginx
      version: "13.0.0"
      overrides:
        remove_files:
          - templates/ingress.yaml
        add_files:
          - source: ./custom-manifests/custom-ingress.yaml
            target: templates/custom-ingress.yaml
      values:
        - nginx-values.yaml
```

**custom-manifests/custom-ingress.yaml**:
```yaml
apiVersion: networking.k8s.io/v1
kind: Ingress
metadata:
  name: {{ .Release.Name }}-custom
spec:
  rules:
    - host: custom.example.com
      http:
        paths:
          - path: /
            pathType: Prefix
            backend:
              service:
                name: {{ .Release.Name }}
                port:
                  number: 80
```

---

### Example 5: LLM-Friendly Output

**Scenario**: Get deployment status in structured format for AI processing

**Command**:
```bash
sbkube status --format llm --quiet
```

**Output**:
```yaml
status: success
apps:
  - name: myapp
    state: deployed
    replicas: 3/3
    health: healthy
  - name: database
    state: deployed
    replicas: 1/1
    health: healthy
```

**Use Case**: Parse output in AI workflows, automation scripts

---

## Troubleshooting

### Common Errors

#### Error: "sources.yaml not found"

**Cause**: Running `sbkube` in wrong directory

**Fix**:
```bash
cd /path/to/project  # Directory containing sources.yaml
sbkube apply
```

---

#### Error: "kubectl not found"

**Cause**: kubectl not installed or not in PATH

**Fix**:
```bash
# Install kubectl
curl -LO "https://dl.k8s.io/release/$(curl -L -s https://dl.k8s.io/release/stable.txt)/bin/linux/amd64/kubectl"
chmod +x kubectl
sudo mv kubectl /usr/local/bin/

# Verify
sbkube doctor
```

---

#### Error: "Helm chart not found"

**Cause**: Helm repository not added

**Fix**:
```bash
# Add repository
helm repo add bitnami https://charts.bitnami.com/bitnami
helm repo update

# Retry
sbkube prepare
```

---

#### Error: "Dependency not deployed"

**Cause**: App-group dependency validation failed (v0.6.0+)

**Error Message**:
```
❌ Error: 2 dependencies not deployed:
  - a101_data_rdb (never deployed)
  - a100_data_memory (last status: failed)
```

**Fix**:
```bash
# Option 1: Deploy missing dependencies first
cd ../a101_data_rdb
sbkube apply

cd ../a100_data_memory
sbkube apply

# Option 2: Deploy all in order
cd k8s-apps
for dir in a000_* a100_* a101_* a302_*; do
  cd $dir && sbkube apply && cd ..
done
```

---

#### Error: "Invalid sources.yaml schema"

**Cause**: Configuration validation failed

**Fix**:
```bash
# Check validation errors
sbkube validate

# Common issues:
# - Missing required fields (name, type)
# - Invalid app type
# - YAML syntax errors
```

---

### Diagnostic Commands

**Full system check**:
```bash
sbkube doctor --detailed
```

**Validate configuration**:
```bash
sbkube validate
```

**Preview deployment**:
```bash
sbkube apply --dry-run
```

**Check deployment status**:
```bash
sbkube status
```

**View deployment history**:
```bash
sbkube history
```

---

### Best Practices

1. **Always run `sbkube doctor` first** when setting up new environment
2. **Use `--dry-run`** before actual deployment
3. **Version Helm charts explicitly** (avoid `latest`)
4. **Use app dependencies** for proper deployment order
5. **Use app-group dependencies** for cross-directory dependencies (v0.6.0+)
6. **Keep `.sbkube/` in `.gitignore`** (working directory, not source)
7. **Use `--format llm`** for structured output in automation

---

## Additional Resources

- **Full Documentation**: [docs/](https://github.com/USER/sb-kube-app-manager/tree/master/docs)
- **Product Spec**: [PRODUCT.md](https://github.com/USER/sb-kube-app-manager/blob/master/PRODUCT.md)
- **Examples**: [examples/](https://github.com/USER/sb-kube-app-manager/tree/master/examples)
- **Troubleshooting**: [docs/07-troubleshooting/](https://github.com/USER/sb-kube-app-manager/tree/master/docs/07-troubleshooting)

---

## Usage from Other Projects

### For AI Assistants

When a user asks about SBKube in another project:

1. **Fetch this guide**:
   ```
   WebFetch("https://raw.githubusercontent.com/USER/sb-kube-app-manager/master/LLM_GUIDE.md")
   ```

2. **Reference specific sections** by searching for markdown headers

3. **Provide concise answers** using examples from this guide

### For Developers

Add this to your project's `CLAUDE.md`:

```markdown
## External Tools

### SBKube (Kubernetes Deployment)
**Documentation**: https://raw.githubusercontent.com/USER/sb-kube-app-manager/master/LLM_GUIDE.md

**Quick Reference**:
- `sbkube apply` - Complete workflow
- Config: `sources.yaml` in project root
- See full docs at URL above
```

---

**Document Version**: 1.0
**SBKube Version**: v0.6.1+
**Last Updated**: 2025-01-04
