______________________________________________________________________

## type: API Reference
audience: End User
topics: [sources, configuration, cluster, helm, oci, git, kubeconfig]
llm_priority: high
last_updated: 2025-01-13

# sources.yaml Schema Guide

> **Complete schema reference for SBKube's cluster configuration file**

## TL;DR

- **Purpose**: Cluster targeting and external source configuration
- **Version**: v0.7.0 (development), v0.6.0 (stable)
- **Key Features**:
  - Explicit cluster configuration (kubeconfig + context)
  - Helm repository management
  - OCI registry support
  - Git repository configuration
  - **Cluster-level global values** (v0.7.0+)
- **Required Fields**: `kubeconfig`, `kubeconfig_context`
- **Related**:
  - [config-schema.md](config-schema.md) - Application configuration
  - [ARCHITECTURE.md](../../ARCHITECTURE.md) - Architecture overview

______________________________________________________________________

## 📂 File Structure Overview

```yaml
# Cluster targeting (required)
cluster: string                      # Cluster identifier (optional, for documentation)
kubeconfig: string                   # Path to kubeconfig file (required)
kubeconfig_context: string           # Kubectl context name (required)

# Cluster-level global values (optional, v0.7.0+)
cluster_values_file: string          # Path to cluster-level Helm values file
global_values: dict                  # Inline global Helm values

# Manifest cleanup settings (optional, v0.7.0+)
cleanup_metadata: bool               # Auto-remove server-managed metadata (default: true)

# App directory control (optional, v0.5.0+)
app_dirs: [string]                   # Explicit list of app directories to deploy

# External sources (all optional)
helm_repos: dict                     # Helm chart repositories
oci_registries: dict                 # OCI (Docker/Harbor) registries
git_repos: dict                      # Git repositories

# Proxy settings (optional)
http_proxy: string
https_proxy: string
no_proxy: [string]
```

______________________________________________________________________

## 🌐 Cluster Configuration (Required)

### kubeconfig (string, required)

Path to the Kubernetes configuration file.

```yaml
kubeconfig: ~/.kube/config
```

**Supported formats**:

- Tilde expansion: `~/kube/config`
- Absolute path: `/home/user/.kube/config`
- Relative path: `./configs/kubeconfig`

**Validation**:

- File must exist
- Must be a valid kubeconfig file

### kubeconfig_context (string, required)

Kubectl context name to use for deployment.

```yaml
kubeconfig_context: prod-cluster
```

**Validation**:

- Context must exist in the kubeconfig file
- Cannot be empty

### cluster (string, optional)

Human-readable cluster identifier for documentation purposes.

```yaml
cluster: production-k3s
```

**Usage**:

- Documentation and logging
- No functional impact on deployment
- Helps identify which cluster you're deploying to

______________________________________________________________________

## 🌐 Cluster-Level Global Values (v0.7.0+)

**New in v0.7.0**: Define Helm values that apply to all apps in the cluster.

### cluster_values_file (string, optional)

Path to a YAML file containing cluster-level Helm values.

```yaml
cluster_values_file: cluster-values.yaml
```

**Example cluster-values.yaml**:

```yaml
global:
  storageClass: nfs-client
  domain: prod.example.com
  imageRegistry: harbor.example.com
  monitoring:
    enabled: true
    retention: 30d
```

**Path resolution**:

- Relative paths: resolved from sources.yaml directory
- Absolute paths: used as-is
- Tilde expansion: supported (`~/configs/values.yaml`)

**Validation**:

- File must exist if specified
- Must be valid YAML

### global_values (dict, optional)

Inline Helm values applied to all apps.

```yaml
global_values:
  global:
    environment: production
    replicas: 3
    storageClass: ceph-block
```

**Priority**:

- `cluster_values_file`: lowest priority
- `global_values`: higher priority (overrides file)
- App-specific values: highest priority (override cluster values)

**Use cases**:

- Quick overrides without editing files
- Environment-specific values
- Temporary settings

### Combining Both (Recommended)

```yaml
# sources.yaml
cluster: production-k3s
kubeconfig: ~/.kube/config
kubeconfig_context: prod-cluster

# File for stable/complex settings
cluster_values_file: cluster-values.yaml

# Inline for quick overrides
global_values:
  global:
    maintenance_mode: false
    deployment_timestamp: "2025-01-06T10:00:00Z"
```

**Merge behavior**:

```
Final values = deep_merge(cluster_values_file, global_values)
```

**See also**:

- [examples/cluster-global-values/](../../examples/cluster-global-values/) - Complete example
- [dict_merge.py](../../sbkube/utils/dict_merge.py) - Merge implementation

______________________________________________________________________

## 🧹 Manifest Metadata Cleanup (v0.7.0+)

**New in v0.7.0**: Automatically remove server-managed metadata fields from rendered manifests.

### cleanup_metadata (bool, optional)

Controls automatic removal of Kubernetes server-managed metadata fields during the `template` stage.

**Default**: `true` (recommended)

```yaml
cleanup_metadata: true  # Enable automatic cleanup (recommended)
```

**What gets removed**:

When enabled, the following fields are automatically removed from all rendered manifests:

- `metadata.managedFields` - Server-Side Apply field ownership tracking
- `metadata.creationTimestamp` - Auto-generated creation timestamp
- `metadata.resourceVersion` - Cluster-specific resource version
- `metadata.uid` - Unique resource identifier
- `metadata.generation` - Resource modification counter
- `metadata.selfLink` - Deprecated API endpoint link (Kubernetes 1.20+)
- `status` - Entire status section (managed by controllers)

**Why this matters**:

These fields are automatically managed by the Kubernetes API server and should not be included in user-provided manifests. Including them can cause deployment failures:

```text
Error: admission webhook denied the request: metadata.managedFields is not allowed
Error: metadata.creationTimestamp is not allowed
```

**Common causes**:

- Using `kubectl get -o yaml` output directly in chart templates
- Copying existing resources as templates
- Including server-managed fields in Kustomize patches

**App type behavior**:

- **Helm apps**: All rendered manifests cleaned
- **YAML apps**: All manifest files cleaned
- **HTTP apps**: Only YAML files (`.yaml`, `.yml`) cleaned, other files unchanged

**When to disable**:

```yaml
cleanup_metadata: false  # Preserve all metadata fields
```

Use `false` only when:

- Debugging deployment issues and need to inspect server-managed fields
- Testing with pre-rendered manifests that include metadata
- Special use cases requiring metadata preservation (rare)

**Warning message**:

When disabled, SBKube shows a warning:

```
⚠️  Manifest metadata cleanup is disabled
```

**Example - Standard usage (recommended)**:

```yaml
# sources.yaml
cluster: production-k3s
kubeconfig: ~/.kube/config
kubeconfig_context: prod-cluster

# cleanup_metadata defaults to true, no need to specify
```

**Example - Disable for debugging**:

```yaml
# sources.yaml
cluster: development-k3s
kubeconfig: ~/.kube/config
kubeconfig_context: dev-cluster
cleanup_metadata: false  # Disable for debugging
```

**See also**:

- [docs/02-features/commands.md](../02-features/commands.md) - Template command documentation
- [docs/07-troubleshooting/deployment-failures.md](../07-troubleshooting/deployment-failures.md) - ManifestMetadataError troubleshooting
- [sbkube/utils/manifest_cleaner.py](../../sbkube/utils/manifest_cleaner.py) - Implementation

______________________________________________________________________

## 📦 App Directory Control (v0.5.0+)

### app_dirs (list[string], optional)

Explicit list of app directories to deploy.

```yaml
app_dirs:
  - redis
  - postgres
  - nginx
```

**Behavior**:

- **If specified**: Only deploy listed directories (strict mode)
- **If not specified**: Auto-discover all directories with `config.yaml`

**Validation**:

- Directory names only (no paths: `../app` ❌)
- No hidden directories (`.hidden` ❌)
- No duplicates
- All directories must exist

**Use cases**:

- Selective deployment in large projects
- CI/CD pipelines
- Staged rollouts

______________________________________________________________________

## 📚 Helm Repositories

### helm_repos (dict[string, HelmRepoScheme], optional)

Helm chart repository configuration.

**String shorthand** (simple):

```yaml
helm_repos:
  grafana: https://grafana.github.io/helm-charts
  prometheus-community: https://prometheus-community.github.io/helm-charts
```

**Object format** (with authentication):

```yaml
helm_repos:
  private-repo:
    url: https://charts.example.com
    username: myuser
    password: mypassword

  tls-repo:
    url: https://secure-charts.example.com
    ca_file: /path/to/ca.crt
    cert_file: /path/to/client.crt
    key_file: /path/to/client.key

  insecure-repo:
    url: https://self-signed.example.com
    insecure_skip_tls_verify: true
```

**Fields**:

- `url` (required): Repository URL
- `username` (optional): Basic auth username
- `password` (optional): Basic auth password
- `ca_file` (optional): CA certificate file
- `cert_file` (optional): Client certificate file
- `key_file` (optional): Client key file
- `insecure_skip_tls_verify` (optional): Skip TLS verification (default: false)

**Validation**:

- URL must start with `http://` or `https://`
- TLS files must be specified together (all 3 or none)
- Cannot use both `insecure_skip_tls_verify` and TLS files

______________________________________________________________________

## 🐳 OCI Registries

### oci_registries (dict[string, OciRepoScheme], optional)

OCI (Docker/Harbor) registry configuration for Helm charts.

**String shorthand**:

```yaml
oci_registries:
  ghcr: ghcr.io
  harbor: harbor.example.com
```

**Object format** (with authentication):

```yaml
oci_registries:
  private-harbor:
    registry: harbor.example.com
    username: admin
    password: Harbor12345
```

**Fields**:

- `registry` (required): Registry URL
- `username` (optional): Registry username
- `password` (optional): Registry password

**Auto-prefixing**:

- Input: `ghcr.io` → Stored as: `oci://ghcr.io`

______________________________________________________________________

## 📂 Git Repositories

### git_repos (dict[string, GitRepoScheme], optional)

Git repository configuration for pulling charts/manifests.

**String shorthand**:

```yaml
git_repos:
  my-charts: https://github.com/example/helm-charts.git
```

**Object format**:

```yaml
git_repos:
  my-charts:
    url: https://github.com/example/helm-charts.git
    branch: main

  private-repo:
    url: https://github.com/example/private-charts.git
    branch: develop
    username: myuser
    password: ghp_xxxxxxxxxxxxx

  ssh-repo:
    url: git@github.com:example/charts.git
    branch: main
    ssh_key: ~/.ssh/id_rsa
```

**Fields**:

- `url` (required): Git repository URL
- `branch` (optional): Branch name (default: `main`)
- `username` (optional): HTTP auth username
- `password` (optional): HTTP auth password (token)
- `ssh_key` (optional): SSH private key path

**Validation**:

- URL must start with: `http://`, `https://`, `git://`, `ssh://`, or `git@`
- Cannot use both username/password and ssh_key
- Branch cannot be empty

______________________________________________________________________

## 🌐 Proxy Configuration

### http_proxy, https_proxy, no_proxy (optional)

Proxy settings for external resource access.

```yaml
http_proxy: http://proxy.example.com:8080
https_proxy: https://proxy.example.com:8080
no_proxy:
  - localhost
  - 127.0.0.1
  - .example.com
```

**Applied to**:

- Helm repository access
- Git cloning
- HTTP file downloads

______________________________________________________________________

## 📝 Complete Examples

### Basic Configuration

```yaml
cluster: production-k3s
kubeconfig: ~/.kube/config
kubeconfig_context: prod-cluster

helm_repos:
  grafana: https://grafana.github.io/helm-charts
```

### With Cluster Global Values

```yaml
cluster: production-k3s
kubeconfig: ~/.kube/config
kubeconfig_context: prod-cluster

# Cluster-level values (v0.7.0+)
cluster_values_file: cluster-values.yaml
global_values:
  global:
    environment: production

helm_repos:
  grafana: https://grafana.github.io/helm-charts
```

### Advanced Configuration

```yaml
cluster: production-k3s
kubeconfig: ~/.kube/prod-kubeconfig
kubeconfig_context: prod-cluster

# Cluster global values
cluster_values_file: cluster-values.yaml
global_values:
  global:
    environment: production
    deployment_timestamp: "2025-01-06T10:00:00Z"

# Selective deployment
app_dirs:
  - database
  - backend
  - frontend

# Helm repositories
helm_repos:
  grafana: https://grafana.github.io/helm-charts

  private-charts:
    url: https://charts.example.com
    username: admin
    password: secret123

# OCI registries
oci_registries:
  harbor:
    registry: harbor.example.com
    username: admin
    password: Harbor12345

# Git repositories
git_repos:
  my-charts:
    url: https://github.com/example/charts.git
    branch: main
    username: bot
    password: ghp_xxxxx

# Proxy settings
http_proxy: http://proxy.example.com:8080
https_proxy: https://proxy.example.com:8080
no_proxy:
  - localhost
  - .example.com
```

______________________________________________________________________

## ⚠️ Validation

SBKube validates sources.yaml using Pydantic models:

```bash
# Validate sources file
sbkube validate --app-dir your-config-dir/

# Doctor command (includes sources validation)
sbkube doctor --app-dir your-config-dir/
```

**Common validation errors**:

- Missing required fields (`kubeconfig`, `kubeconfig_context`)
- Invalid file paths (`cluster_values_file` not found)
- Invalid URL formats
- Invalid Git repository URLs
- TLS configuration inconsistencies

______________________________________________________________________

## Related Documentation

- [config-schema.md](config-schema.md) - Application configuration
- [PRODUCT.md](../../PRODUCT.md) - Product overview
- [ARCHITECTURE.md](../../ARCHITECTURE.md) - Architecture overview
- [examples/cluster-global-values/](../../examples/cluster-global-values/) - Cluster values example

______________________________________________________________________

**Document Version**: 1.0 **Last Updated**: 2025-01-06 **Author**: archmagece@users.noreply.github.com
