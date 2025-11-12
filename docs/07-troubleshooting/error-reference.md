______________________________________________________________________

## type: Error Reference audience: Developer topics: [errors, error-messages, diagnostics, fixes] llm_priority: low load_on_demand: true last_updated: 2025-01-04

# Complete Error Reference

> **Note**: This is a comprehensive error catalog. For common issues and quick fixes, see the
> [Troubleshooting Guide](README.md).

This document contains a complete catalog of all error messages you might encounter in SBKube, organized by category and
command.

______________________________________________________________________

## 📋 Table of Contents

- [Installation and Environment Errors](#installation-and-environment-errors)
- [Configuration Errors](#configuration-errors)
- [Network Errors](#network-errors)
- [Deployment Errors](#deployment-errors)
- [Command-Specific Errors](#command-specific-errors)
- [State Management Errors](#state-management-errors)
- [Platform-Specific Errors](#platform-specific-errors)

______________________________________________________________________

## Installation and Environment Errors

### Python Version Compatibility

```bash
# Error
ERROR: Python 3.12 is required, but you have 3.11
```

**Cause:** SBKube requires Python 3.12 or higher.

**Solution:**

```bash
# Install Python 3.12+
# Ubuntu/Debian
sudo apt update && sudo apt install python3.12

# macOS (Homebrew)
brew install python@3.12

# pyenv
pyenv install 3.12.0
pyenv global 3.12.0

# Windows (Python.org)
# Download from https://www.python.org/downloads/
```

### Command Not Found

```bash
# Error
bash: sbkube: command not found
```

**Possible Causes:**

1. SBKube not installed
1. PATH not configured correctly
1. Virtual environment not activated

**Solutions:**

```bash
# Install SBKube
pip install sbkube

# Or using uv
uv tool install sbkube

# Check PATH
echo $PATH
export PATH=$PATH:~/.local/bin

# Add to shell profile
echo 'export PATH=$PATH:~/.local/bin' >> ~/.bashrc  # or ~/.zshrc
```

### Permission Denied

```bash
# Error variations
Error: Permission denied: '/home/user/.sbkube/state.db'
PermissionError: [Errno 13] Permission denied: '/usr/local/bin/sbkube'
OSError: [Errno 13] Permission denied: '~/.sbkube/'
```

**Solutions:**

```bash
# Fix ownership
sudo chown -R $USER:$USER ~/.sbkube/

# Fix installation permissions
sudo pip install --user sbkube

# Or recreate directory
rm -rf ~/.sbkube/
sbkube history  # Auto-creates directory with correct permissions
```

______________________________________________________________________

## Configuration Errors

### ERR-CFG-001: OCI Protocol in chart Field

```bash
# Error
ValueError: Direct OCI protocol in 'chart' field is not supported.

SBKube requires OCI registries to be defined in sources.yaml:

  sources.yaml:
    oci_registries:
      myregistry:
        registry: oci://registry.example.com/path

  config.yaml:
    apps:
      myapp:
        type: helm
        chart: myregistry/chartname
```

**Cause:** You used `chart: oci://...` directly in config.yaml, which is not supported. SBKube requires a two-step
configuration for OCI registries.

**Why This Design?**

- **Consistency**: All remote sources (Helm repos, OCI registries, Git repos) are defined in sources.yaml
- **Reusability**: Define registry once, use across multiple apps
- **Maintainability**: Central management of registry URLs and credentials

**Solution:**

**Step 1: Add OCI registry to sources.yaml**

```yaml
# sources.yaml
oci_registries:
  bitnami:
    registry: oci://registry-1.docker.io/bitnamicharts

  truecharts:
    registry: oci://tccr.io/truecharts
```

**Step 2: Update config.yaml to use registry name**

```yaml
# config.yaml - BEFORE (❌ Wrong)
apps:
  supabase:
    type: helm
    chart: oci://registry-1.docker.io/bitnamicharts/supabase  # ❌ Error!

# config.yaml - AFTER (✅ Correct)
apps:
  supabase:
    type: helm
    chart: bitnami/supabase  # ✅ Uses registry name from sources.yaml
    version: "1.0.0"
```

**Common OCI Registries:**

- **Docker Hub Bitnami**: `oci://registry-1.docker.io/bitnamicharts`
- **TrueCharts**: `oci://tccr.io/truecharts`
- **GitHub Container Registry**: `oci://ghcr.io/org-name/charts`
- **GitLab Container Registry**: `oci://registry.gitlab.com/project/charts`

**Complete Example:**

```yaml
# sources.yaml
kubeconfig: ~/.kube/config
cluster: production

oci_registries:
  bitnami:
    registry: oci://registry-1.docker.io/bitnamicharts

  private-registry:
    registry: oci://my-registry.com/charts
    username: myuser
    password: ${REGISTRY_PASSWORD}

# config.yaml
namespace: platform

apps:
  supabase:
    type: helm
    chart: bitnami/supabase
    version: "1.0.0"
    values:
      - values/supabase.yaml

  custom-app:
    type: helm
    chart: private-registry/my-app
    version: "2.0.0"
```

**Related:**

- [config-schema.md#oci-registry](../03-configuration/config-schema.md#oci-registry) - Detailed OCI usage guide
- [sources-schema.md](../03-configuration/sources-schema.md) - sources.yaml schema
- [examples/prepare/helm-oci/](../../examples/prepare/helm-oci/) - Complete OCI example

______________________________________________________________________

### sources.yaml Not Found

```bash
# Error variations
Error: sources.yaml not found in: ./sources.yaml, ../sources.yaml, ./sources.yaml
FileNotFoundError: [Errno 2] No such file or directory: 'sources.yaml'
Error: Cannot find sources.yaml in any search path
```

**Search Order (v0.4.7+):**

1. Current directory (.)
1. Parent directory (..)
1. base-dir (--base-dir option)

**Solution:**

```bash
# Create sources.yaml in any of these locations
cat > sources.yaml << 'EOF'
kubeconfig: ~/.kube/config
kubeconfig_context: my-cluster
cluster: production

helm_repos:
  grafana:
    url: https://grafana.github.io/helm-charts
  prometheus-community:
    url: https://prometheus-community.github.io/helm-charts

oci_registries:
  browserless:
    registry: oci://tccr.io/truecharts
  gabe565:
    registry: oci://ghcr.io/gabe565/charts

git_repos:
  my-configs:
    url: https://github.com/user/configs.git
    branch: main
EOF
```

### YAML Syntax Errors

```bash
# Error variations
yaml.scanner.ScannerError: found character '\t' that cannot start any token
yaml.scanner.ScannerError: while scanning a block scalar
yaml.parser.ParserError: expected '<document start>', but found '<scalar>'
yaml.constructor.ConstructorError: could not determine a constructor for tag
```

**Common Causes:**

- Tabs instead of spaces
- Incorrect indentation
- Unclosed quotes
- Invalid special characters

**Solutions:**

```bash
# Validate YAML syntax
python -c "import yaml; yaml.safe_load(open('config.yaml'))"

# Check for tabs (should use spaces)
cat -A config.yaml  # Shows tab characters as ^I

# Convert tabs to spaces
sed -i 's/\t/  /g' config.yaml  # Linux
sed -i '' 's/\t/  /g' config.yaml  # macOS

# Use online validators
# https://yamlchecker.com/
# https://www.yamllint.com/
```

### Schema Validation Failed

```bash
# Error variations
ValidationError: 'invalid-type' is not one of ['exec', 'helm', 'git', 'http', 'kustomize', 'yaml', 'action', 'exec', 'noop']
pydantic.error_wrappers.ValidationError: 1 validation error for AppConfig
ValidationError: field required (type=value_error.missing)
ValidationError: extra fields not permitted (type=value_error.extra)
```

**Supported App Types:**

- `helm` - Helm charts
- `git` - Git repositories
- `http` - HTTP downloads
- `kustomize` - Kustomize configurations
- `yaml` - Raw YAML manifests
- `action` - Action hooks
- `exec` - Execute commands
- `noop` - No operation (placeholder)

**Solution:**

```bash
# Validate configuration
sbkube validate

# Example valid configuration
cat > config.yaml << 'EOF'
apps:
  grafana:
    type: helm  # Must be one of supported types
    chart: grafana/grafana
    version: "6.60.0"
    namespace: monitoring
    values:
      adminPassword: admin
EOF
```

### Circular Dependency Detected

```bash
# Error variations
Error: Circular dependency detected: app-a → app-b → app-a
Error: Dependency cycle found in application graph
RuntimeError: Maximum recursion depth exceeded in dependency resolution
```

**Solution:**

```yaml
# Wrong configuration
apps:
  app-a:
    depends_on: [app-b]
  app-b:
    depends_on: [app-c]
  app-c:
    depends_on: [app-a]  # Creates cycle!

# Fixed configuration - Remove cycle
apps:
  app-a:
    # No depends_on
  app-b:
    depends_on: [app-a]
  app-c:
    depends_on: [app-b]
```

### Invalid Field Values

```bash
# Error variations
ValidationError: Invalid namespace name: 'my_namespace' (must match RFC 1123)
ValidationError: Version string '1.2.3.4' does not match pattern
ValidationError: Port number 99999 is out of range (1-65535)
```

**Kubernetes Naming Rules:**

- Lowercase letters, numbers, hyphens only
- Must start and end with alphanumeric
- Max 63 characters for names
- Max 253 characters for DNS names

**Solution:**

```yaml
# Valid names
namespace: my-namespace  # Good
# namespace: my_namespace  # Bad (underscore)
# namespace: MyNamespace  # Bad (uppercase)
# namespace: -namespace   # Bad (starts with hyphen)
```

______________________________________________________________________

## Network Errors

### Kubernetes Connection Issues

#### Kubeconfig Not Found

```bash
# Error variations
Kubeconfig file not found (path: ~/.kube/config)
FileNotFoundError: [Errno 2] No such file or directory: '/home/user/.kube/config'
Error: kubeconfig validation failed: file does not exist
```

**Solutions:**

```bash
# Check kubeconfig existence
ls -la ~/.kube/config

# Set environment variable
export KUBECONFIG=/path/to/your/kubeconfig

# Specify in SBKube
sbkube --kubeconfig /path/to/kubeconfig deploy

# Copy from remote server
scp user@server:/etc/rancher/k3s/k3s.yaml ~/.kube/config
# Edit server address in ~/.kube/config
```

#### Context Not Found

```bash
# Error variations
❌ Kubernetes context 'my-context' not found in kubeconfig: ~/.kube/config

Available contexts in this kubeconfig:
  • k3d-cwrapper-local
  • minikube

📝 Please update sources.yaml with a valid context:
  kubeconfig_context: <valid-context-name>
```

**Important Context vs Cluster Distinction:**

- `cluster` field: Human-readable label (any name you want)
- `kubeconfig_context`: Actual kubectl context name (must match exactly)

**Solution:**

```bash
# 1. List available contexts
kubectl config get-contexts
# Output:
# CURRENT   NAME                    CLUSTER                 AUTHINFO
# *         k3d-cwrapper-local      k3d-cwrapper-local      admin@k3d-cwrapper-local
#           minikube                minikube                minikube

# 2. Update sources.yaml - use NAME column value
cat > sources.yaml << 'EOF'
cluster: my-cluster  # Any descriptive name
kubeconfig: ~/.kube/config
kubeconfig_context: k3d-cwrapper-local  # Must match NAME exactly
EOF

# 3. Set current context (optional)
kubectl config use-context k3d-cwrapper-local
```

#### Access Forbidden

```bash
# Error variations
Error: Forbidden (403): User cannot access resource
Error: is forbidden: User "system:serviceaccount:default:default" cannot create resource "deployments"
Error from server (Forbidden): deployments.apps is forbidden
```

**Solutions:**

```bash
# Check current user
kubectl auth whoami

# Verify permissions
kubectl auth can-i create deployments
kubectl auth can-i create services
kubectl auth can-i get pods

# Grant permissions (requires admin)
kubectl create clusterrolebinding sbkube-admin \
  --clusterrole=cluster-admin \
  --user=$(kubectl config current-context)

# For service account
kubectl create clusterrolebinding sbkube-sa-admin \
  --clusterrole=cluster-admin \
  --serviceaccount=default:default
```

### CLI Tools Issues

#### kubectl Not Found

```bash
# Error variations
❌ 'kubectl' command not found
bash: kubectl: command not found
FileNotFoundError: [Errno 2] No such file or directory: 'kubectl'
```

**Solution:**

```bash
# Install kubectl (Linux)
curl -LO "https://dl.k8s.io/release/$(curl -L -s https://dl.k8s.io/release/stable.txt)/bin/linux/amd64/kubectl"
sudo install -o root -g root -m 0755 kubectl /usr/local/bin/kubectl

# macOS
brew install kubectl

# Windows (PowerShell as Admin)
choco install kubernetes-cli

# Verify installation
kubectl version --client
```

#### Helm Not Found

```bash
# Error variations
❌ 'helm' command not available
bash: helm: command not found
Error: Cannot find helm binary in PATH
```

**Solution:**

```bash
# Install Helm
curl https://raw.githubusercontent.com/helm/helm/main/scripts/get-helm-3 | bash

# macOS
brew install helm

# Windows
choco install kubernetes-helm

# Verify installation
helm version
```

### Repository Access Issues

#### Git SSL Certificate Problem

```bash
# Error variations
fatal: unable to access 'https://github.com/...': SSL certificate problem
SSL certificate problem: self signed certificate in certificate chain
SSL certificate problem: unable to get local issuer certificate
```

**Solutions:**

```bash
# Temporary: Disable SSL verification (NOT RECOMMENDED)
git config --global http.sslVerify false

# Better: Add certificate to trust store
# Linux
sudo cp /path/to/cert.crt /usr/local/share/ca-certificates/
sudo update-ca-certificates

# macOS
sudo security add-trusted-cert -d -r trustRoot -k /Library/Keychains/System.keychain /path/to/cert.crt

# Best: Use SSH keys
ssh-keygen -t ed25519 -C "your.email@example.com"
# Add public key to GitHub/GitLab
# Use SSH URLs in sources.yaml
```

#### Helm Repository Unreachable

```bash
# Error variations
Error: failed to fetch https://grafana.github.io/helm-charts/index.yaml
Error: Get "https://grafana.github.io/helm-charts/index.yaml": dial tcp: i/o timeout
Error: failed to update cache: failed to fetch index.yaml
```

**Solutions:**

```bash
# Test connectivity
curl -I https://grafana.github.io/helm-charts/index.yaml

# Configure proxy if needed
export HTTP_PROXY=http://proxy.company.com:8080
export HTTPS_PROXY=http://proxy.company.com:8080
export NO_PROXY=localhost,127.0.0.1,.company.com

# Re-add repository
helm repo remove grafana
helm repo add grafana https://grafana.github.io/helm-charts
helm repo update

# Use mirror repository (if available)
helm repo add grafana https://mirror.company.com/helm-charts/grafana
```

______________________________________________________________________

## Deployment Errors

### Helm Chart Issues

#### Chart Not Found

```bash
# Error variations
Error: failed to download chart: chart not found
Error: chart "grafana/grafana" version "6.50.0" not found
Error: failed to fetch chart: 404 Not Found
```

**Solutions:**

```bash
# Update repositories
helm repo update

# Check available versions
helm search repo grafana/grafana --versions | head -20

# Update config.yaml with valid version
# Or remove version for latest
apps:
  grafana:
    chart: grafana/grafana
    version: "6.60.0"  # Or remove this line for latest
```

#### Helm Repository Not in sources.yaml

```bash
# Error
❌ Helm repo 'browserless' not found in sources.yaml
```

**Common Causes:**

1. **OCI Registry**: Should be in `oci_registries` not `helm_repos`
1. **Name Mismatch**: Typo between sources.yaml and config.yaml
1. **Deprecated Repository**: Using old/unsupported repositories

**Solutions:**

**Case 1: OCI Registry Chart**

```yaml
# sources.yaml
oci_registries:
  browserless:
    registry: oci://tccr.io/truecharts
  gabe565:
    registry: oci://ghcr.io/gabe565/charts

# config.yaml
apps:
  browserless:
    type: helm
    chart: browserless/browserless-chrome  # References oci_registries
```

**Case 2: Repository Name Typo**

```yaml
# ✅ Correct - names match
# sources.yaml
helm_repos:
  codecentric:
    url: https://codecentric.github.io/helm-charts

# config.yaml
apps:
  mailhog:
    chart: codecentric/mailhog  # Must match sources.yaml key
```

**Case 3: Deprecated Repository**

```yaml
# ❌ Wrong - Helm Stable deprecated in 2020
helm_repos:
  kubernetes-charts:
    url: https://charts.helm.sh/stable

# ✅ Correct - Use official repository
helm_repos:
  descheduler:
    url: https://kubernetes-sigs.github.io/descheduler/
```

#### Helm Release Conflict

```bash
# Error variations
Error: cannot re-use a name that is still in use
Error: release grafana-my-namespace already exists
Error: a release named grafana already exists
```

**Solutions:**

```bash
# List existing releases
helm list -n my-namespace
helm list -A  # All namespaces

# Delete existing release
helm uninstall grafana-my-namespace -n my-namespace

# Or use sbkube delete
sbkube delete --namespace my-namespace

# Force upgrade (overwrites existing)
helm upgrade --install grafana grafana/grafana -n my-namespace

# Use different release name
apps:
  grafana:
    release_name: grafana-v2  # Custom release name
```

### Namespace Issues

#### Namespace Not Found

```bash
# Error variations
Error: namespaces "my-namespace" not found
Error from server (NotFound): namespaces "my-namespace" not found
Error: the namespace from the provided object "my-namespace" does not exist
```

**Solutions:**

```bash
# Create namespace
kubectl create namespace my-namespace

# Or use YAML
cat <<EOF | kubectl apply -f -
apiVersion: v1
kind: Namespace
metadata:
  name: my-namespace
  labels:
    name: my-namespace
EOF

# Verify namespace exists
kubectl get namespaces
```

### Pod Issues

#### Pod Stuck in Pending

```bash
# Pod status shows Pending indefinitely
NAME                       READY   STATUS    RESTARTS   AGE
grafana-5f7b4c5d9-abcde    0/1     Pending   0          5m
```

**Common Causes & Solutions:**

**1. Insufficient Resources**

```bash
# Check node resources
kubectl top nodes
kubectl describe nodes

# Check pod resource requests
kubectl describe pod grafana-5f7b4c5d9-abcde -n test-namespace | grep -A 5 "Requests:"

# Solution: Reduce resource requests in values.yaml
resources:
  requests:
    cpu: 100m  # Reduce from 500m
    memory: 128Mi  # Reduce from 512Mi
```

**2. PVC Mount Failure**

```bash
# Check PVC status
kubectl get pvc -n test-namespace
kubectl describe pvc grafana-pvc -n test-namespace

# Common issue: No storage class
kubectl get storageclass

# Solution: Create PVC or use emptyDir
persistence:
  enabled: false  # Or configure proper storage class
```

**3. Node Selector/Affinity Mismatch**

```bash
# Check node labels
kubectl get nodes --show-labels

# Check pod node selector
kubectl describe pod grafana-5f7b4c5d9-abcde -n test-namespace | grep -A 5 "Node-Selectors:"

# Solution: Remove or fix node selector
nodeSelector: {}  # Remove node selector
```

#### ImagePullBackOff

```bash
# Pod status
NAME                       READY   STATUS             RESTARTS   AGE
grafana-5f7b4c5d9-abcde    0/1     ImagePullBackOff   0          2m
```

**Solutions:**

```bash
# Check events for details
kubectl describe pod grafana-5f7b4c5d9-abcde -n test-namespace

# Common issues and fixes:

# 1. Wrong image name/tag
# Fix in values.yaml:
image:
  repository: grafana/grafana
  tag: "9.5.3"  # Ensure tag exists

# 2. Private registry - create secret
kubectl create secret docker-registry regcred \
  --docker-server=<registry-url> \
  --docker-username=<username> \
  --docker-password=<password> \
  -n test-namespace

# Add to values.yaml:
imagePullSecrets:
  - name: regcred

# 3. Rate limiting (DockerHub)
# Use mirror or wait
```

#### CrashLoopBackOff

```bash
# Pod keeps restarting
NAME                       READY   STATUS             RESTARTS   AGE
grafana-5f7b4c5d9-abcde    0/1     CrashLoopBackOff   5          3m
```

**Diagnosis and Solutions:**

```bash
# Check logs
kubectl logs grafana-5f7b4c5d9-abcde -n test-namespace
kubectl logs grafana-5f7b4c5d9-abcde -n test-namespace --previous

# Common issues:

# 1. Missing environment variables/secrets
kubectl get secrets -n test-namespace
kubectl get configmaps -n test-namespace

# 2. Permission issues
# Add security context in values.yaml:
securityContext:
  runAsUser: 472
  runAsGroup: 472
  fsGroup: 472

# 3. Liveness probe failing
# Adjust probe settings:
livenessProbe:
  initialDelaySeconds: 120  # Give more time to start
  timeoutSeconds: 10
  failureThreshold: 5

# 4. Debug with shell
kubectl run debug --rm -it --image=grafana/grafana:9.5.3 --command -- /bin/bash
```

______________________________________________________________________

## Command-Specific Errors

### apply Command Errors

```bash
# Various apply command errors
Error: Failed to execute workflow
Error: Configuration validation failed before apply
Error: One or more phases failed during apply
```

**Common Issues:**

1. Configuration validation errors
1. Dependency resolution problems
1. Hook execution failures
1. Resource creation failures

**Solutions:**

```bash
# Debug step by step
sbkube validate
sbkube prepare
sbkube build
sbkube template --output-dir debug/
sbkube deploy --dry-run
sbkube deploy
```

### prepare Command Errors

#### Chart Pull Failed

```bash
# Error variations
Error: chart 'grafana/grafana' version '6.50.0' not found in repository
Error: failed to pull chart: 404 Not Found
Error: failed to download "grafana/grafana" at version "6.50.0"
```

**Solution:**

```bash
# Check available versions
helm search repo grafana/grafana --versions | head -20

# Update repository
helm repo update grafana

# Use valid version or latest
apps:
  grafana:
    chart: grafana/grafana
    version: "6.60.0"  # Or remove for latest
```

#### Git Clone Failed

```bash
# Error variations
Error: failed to clone repository: Authentication required
Error: repository not found
fatal: could not read Username for 'https://github.com': terminal prompts disabled
```

**Solutions:**

```bash
# Use SSH URL in sources.yaml
git_repos:
  my-repo:
    url: git@github.com:user/repo.git

# Or use Personal Access Token
git_repos:
  my-repo:
    url: https://oauth2:TOKEN@github.com/user/repo.git

# Configure git credentials
git config --global credential.helper store

# For private repos, add SSH key
ssh-add ~/.ssh/id_rsa
```

#### Chart Already Exists (v0.4.6+)

```bash
# Info message (not an error)
⏭️  Chart already exists, skipping: grafana
    Use --force to re-download
```

**Solution:**

```bash
# Force re-download if needed
sbkube prepare --force
```

### build Command Errors

#### Override Not Applied

```bash
# Warning
⚠️  Override directory found but not configured: myapp
```

**Cause:** Override files exist in `overrides/myapp/` but not configured in config.yaml

**Solution:**

```yaml
# config.yaml - Add overrides field
apps:
  myapp:
    type: helm
    chart: ingress-nginx/ingress-nginx
    overrides:  # Required to use override files
      - templates/configmap.yaml
      - files/config.txt
```

#### Build Directory Empty

```bash
# Info message
⏭️ Skipping Helm app (no customization): myapp
```

**Explanation:** SBKube skips building when:

- Using local chart (`chart: ./charts/myapp`)
- No `overrides` configured
- No `removes` configured

This is **normal optimization behavior**.

**Solutions if build is needed:**

```yaml
# Option 1: Add overrides
myapp:
  type: helm
  chart: ./charts/myapp
  overrides:
    - templates/configmap.yaml

# Option 2: Use remote chart (always built)
myapp:
  type: helm
  chart: grafana/grafana
  version: "6.50.0"
```

#### .Files.Get Returns Empty

```bash
# Error in Helm template
Error: template: myapp/templates/configmap.yaml:5:20: executing "myapp/templates/configmap.yaml" at <.Files.Get "config.toml">: error calling Get: file not found
```

**Cause:** Files referenced in templates not included in chart

**Solution:**

```yaml
# config.yaml - Include files directory
apps:
  myapp:
    type: helm
    chart: my-chart
    overrides:
      - templates/configmap.yaml
      - files/  # Include entire files directory
      # Or specific files:
      - files/config.toml
      - files/data.json
```

### deploy Command Errors

See [Deployment Errors](#deployment-errors) section above for pod-specific issues.

### template Command Errors

```bash
# Error variations
Error: failed to render templates
Error: template: myapp/templates/deployment.yaml:10: function "invalidFunc" not defined
Error: YAML parse error on myapp/templates/service.yaml
```

**Solutions:**

```bash
# Debug template rendering
helm template test-release charts-built/myapp --debug

# Check for syntax errors
helm lint charts-built/myapp

# Validate rendered YAML
sbkube template --output-dir debug/
kubectl apply -f debug/ --dry-run=client
```

### delete Command Errors

```bash
# Error variations
Error: release not found
Error: uninstall: Release not loaded: grafana: release: not found
```

**Solution:**

```bash
# Check if release exists
helm list -n namespace

# Force delete resources
kubectl delete all -l app=grafana -n namespace

# Clean up manually if needed
kubectl delete deployment,service,configmap,secret -l app=grafana -n namespace
```

______________________________________________________________________

## State Management Errors

### Database Locked

```bash
# Error variations
sqlite3.OperationalError: database is locked
Error: Cannot acquire lock on state database
Error: State database is being used by another process
```

**Solutions:**

```bash
# Check for other sbkube processes
ps aux | grep sbkube

# Kill stuck processes
pkill -f sbkube

# Remove lock file (if safe)
rm ~/.sbkube/deployment.db-lock
rm ~/.sbkube/deployment.db-journal

# Reset database (last resort)
rm ~/.sbkube/deployment.db
sbkube history  # Recreates database
```

### State Inconsistency

```bash
# Symptoms
- sbkube history shows different state than actual cluster
- Deployments fail with "already exists" despite not being visible
```

**Manual State Verification:**

```bash
# Check actual cluster state
kubectl get all -A
helm list -A

# Check sbkube state
sbkube history

# Future feature: Sync state
# sbkube sync-state
```

______________________________________________________________________

## Platform-Specific Errors

### Windows Environment

```powershell
# Path separator issues
Error: The system cannot find the path specified: 'config\app.yaml'
```

**Solutions:**

```powershell
# Run in PowerShell
python -m sbkube.cli deploy

# Use forward slashes in YAML
# Good: paths: "config/app.yaml"
# Bad:  paths: "config\\app.yaml"

# Run PowerShell as Administrator for permissions
Start-Process PowerShell -Verb RunAs
```

### macOS Environment

```bash
# Homebrew permission issues
Error: Permission denied @ rb_sysopen - /usr/local/Homebrew/.github
```

**Solutions:**

```bash
# Fix Homebrew permissions
sudo chown -R $(whoami) /usr/local/Homebrew

# Update PATH for zsh
echo 'export PATH="/usr/local/bin:$PATH"' >> ~/.zshrc
source ~/.zshrc

# For Apple Silicon Macs
echo 'export PATH="/opt/homebrew/bin:$PATH"' >> ~/.zshrc
```

### Linux Environment

```bash
# SELinux issues (RHEL/CentOS/Fedora)
Error: SELinux is preventing /usr/bin/python3.12 from read access
```

**Solutions:**

```bash
# Check SELinux status
getenforce

# Temporary disable (testing only)
sudo setenforce 0

# Permanent fix - add context
sudo semanage fcontext -a -t container_file_t "/home/user/.sbkube(/.*)?"
sudo restorecon -Rv /home/user/.sbkube
```

______________________________________________________________________

## Hooks Related Errors

### Hook Execution Failed

```bash
# Error variations
Error: Hook execution failed
Command: ./scripts/backup.sh
Exit code: 127
Error: pre_deploy hook failed: command not found
Error: post_deploy_tasks validation failed
```

**Solutions:**

```bash
# 1. Check file exists and has execute permission
ls -la ./scripts/backup.sh
chmod +x ./scripts/backup.sh

# 2. Verify environment variables are available
hooks:
  post_deploy:
    - |
      echo "SBKUBE_APP_NAME: $SBKUBE_APP_NAME"
      echo "SBKUBE_NAMESPACE: $SBKUBE_NAMESPACE"
      echo "SBKUBE_CLUSTER: $SBKUBE_CLUSTER"

# 3. Use absolute paths or specify working directory
post_deploy_tasks:
  - type: command
    command: ["./backup.sh"]
    working_dir: "./scripts"

# 4. Check script shebang
# First line should be:
#!/bin/bash
# or
#!/usr/bin/env bash
```

### Manifests Hook File Not Found

```bash
# Error
Error: Manifest file not found: manifests/cluster-issuer.yaml
```

**Solution:**

```bash
# Check relative path from app_dir
ls manifests/cluster-issuer.yaml

# Phase 1 syntax (deprecated)
pre_deploy_manifests:
  - path: manifests/cluster-issuer.yaml

# Phase 2 syntax (current)
pre_deploy_tasks:
  - type: manifests
    paths: ["cluster-issuer.yaml"]
    working_dir: "./manifests"
```

### Task Validation Timeout

```bash
# Error
Error: Validation failed for task 'create-certificate'
Resource certificate/my-cert not ready after 300s
```

**Solution:**

```yaml
# Extend timeout
post_deploy_tasks:
  - type: manifests
    name: create-certificate
    paths: ["certificate.yaml"]
    validation:
      type: resource_ready
      resource: certificate/my-cert
      timeout: 600  # 10 minutes

# Or change failure handling
    on_failure: warn  # Continue on failure
```

**Related Documentation:**

- **[Hooks Reference](../02-features/hooks-reference.md)** - All hook types and environment variables
- **[Hooks Guide](../02-features/hooks-guide.md)** - Practical examples and best practices
- **[Hooks Migration Guide](../02-features/hooks-migration-guide.md)** - Phase transition guide

______________________________________________________________________

## Performance Issues

### Slow Deployments

```bash
# Symptoms
- Deployments taking > 5 minutes
- High CPU usage during sbkube operations
```

**Solutions:**

```bash
# Optimize parallelization
export SBKUBE_MAX_WORKERS=8

# Disable unnecessary apps
apps:
  unused-app:
    enabled: false

# Use Helm cache
export HELM_CACHE_HOME=/tmp/helm-cache

# Process in batches
sbkube build --app app1
sbkube build --app app2
```

### High Memory Usage

```bash
# Symptoms
- Memory usage > 2GB
- Out of memory errors
```

**Solutions:**

```bash
# Monitor memory
top -p $(pgrep -f sbkube)

# Set memory limit
ulimit -v 2097152  # 2GB limit

# Reduce concurrent operations
export SBKUBE_MAX_WORKERS=2

# Process apps individually
for app in app1 app2 app3; do
  sbkube deploy --app $app
done
```

______________________________________________________________________

## See Also

- **[Troubleshooting Guide](README.md)** - Quick fixes and common issues
- **[Common Dev Issues](common-dev-issues.md)** - Development environment problems
- **[Deployment Failures](deployment-failures.md)** - Production deployment issues
- **[FAQ](faq.md)** - Frequently asked questions
- **[Configuration Guide](../03-configuration/)** - Proper configuration methods
- **[Commands Reference](../02-features/commands.md)** - Command usage and examples

______________________________________________________________________

*This document is automatically loaded on-demand when specific error details are needed. For quick troubleshooting,
start with the [Troubleshooting Guide](README.md).*
