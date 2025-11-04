---
type: User Guide
audience: End User, Developer
topics: [troubleshooting, debugging, common-errors]
llm_priority: high
last_updated: 2025-01-04
---

# 🔍 SBKube Troubleshooting Guide

Comprehensive troubleshooting guide for common issues encountered with SBKube.

## TL;DR

- **Quick Fixes**: Check kubectl, Helm, sources.yaml syntax
- **Commands**: `sbkube doctor`, `sbkube validate`
- **Common Errors**: Network, permissions, config validation
- **Related**: [Common Dev Issues](common-dev-issues.md), [Deployment Failures](deployment-failures.md)

______________________________________________________________________

## 📚 Quick Navigation

### Troubleshooting Documents
- **[Common Dev Issues](common-dev-issues.md)** - Development environment problems (test failures, type errors, import errors, uv issues)
- **[Deployment Failures](deployment-failures.md)** - Production deployment specific issues
- **[FAQ](faq.md)** - Frequently asked questions

______________________________________________________________________

## 🚨 Quick Diagnostic Commands

```bash
# System check
sbkube doctor                      # Check all dependencies (future feature)
sbkube validate                     # Validate configuration files

# Version information
sbkube --version                    # SBKube version
python --version                    # Python version
kubectl version --client            # kubectl version
helm version                        # Helm version

# Status checks
kubectl cluster-info                # Kubernetes cluster status
kubectl get nodes                    # Node status
helm list -A                        # All Helm releases
sbkube history                      # Deployment history

# Verbose debugging
sbkube --verbose deploy             # Detailed logging
sbkube template --output-dir debug  # Render templates for inspection
```

______________________________________________________________________

## 📋 Common Error Categories

### 1. Installation and Environment Issues

#### ❌ Python Version Compatibility

```bash
# Error
ERROR: Python 3.12 is required, but you have 3.11
```

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
```

#### ❌ Command Not Found

```bash
# Error
bash: sbkube: command not found
```

**Solution:**

```bash
# Install SBKube
pip install sbkube

# Or using uv
uv tool install sbkube

# Check PATH
echo $PATH
export PATH=$PATH:~/.local/bin
```

#### ❌ Permission Denied

```bash
# Error
Error: Permission denied: '/home/user/.sbkube/state.db'
```

**Solution:**

```bash
# Fix ownership
sudo chown -R $USER:$USER ~/.sbkube/

# Or recreate directory
rm -rf ~/.sbkube/
sbkube history  # Auto-creates directory
```

______________________________________________________________________

### 2. CLI Tools Issues

#### ❌ kubectl Not Found

```bash
# Error
❌ 'kubectl' command not found
```

**Solution:**

```bash
# Install kubectl (Linux)
curl -LO "https://dl.k8s.io/release/$(curl -L -s https://dl.k8s.io/release/stable.txt)/bin/linux/amd64/kubectl"
sudo install -o root -g root -m 0755 kubectl /usr/local/bin/kubectl

# Verify installation
kubectl version --client
```

#### ❌ Helm Not Found

```bash
# Error
❌ 'helm' command not available
```

**Solution:**

```bash
# Install Helm
curl https://raw.githubusercontent.com/helm/helm/main/scripts/get-helm-3 | bash

# Verify installation
helm version
```

______________________________________________________________________

### 3. Kubernetes Connection Issues

#### ❌ Kubeconfig Not Found

```bash
# Error
Kubeconfig file not found (path: ~/.kube/config)
```

**Solution:**

```bash
# Check kubeconfig existence
ls -la ~/.kube/config

# Set environment variable
export KUBECONFIG=/path/to/your/kubeconfig

# Or specify in SBKube
sbkube --kubeconfig /path/to/kubeconfig deploy
```

#### ❌ Context Not Found

```bash
# Error
❌ Kubernetes context 'my-context' not found in kubeconfig: ~/.kube/config

Available contexts in this kubeconfig:
  • k3d-cwrapper-local
  • minikube

📝 Please update sources.yaml with a valid context:
  kubeconfig_context: <valid-context-name>
```

**Solution:**

```bash
# 1. List available contexts
kubectl config get-contexts

# 2. Update sources.yaml
cat > config/sources.yaml <<EOF
cluster: my-cluster
kubeconfig: ~/.kube/config
kubeconfig_context: k3d-cwrapper-local  # Use NAME column value
helm_repos: {}
EOF

# 3. Retry deployment
sbkube deploy --app-dir config --namespace test
```

**Important:**
- `cluster` field: Human-readable label (any name)
- `kubeconfig_context`: Actual kubectl context name (must match exactly)
- Context names are case-sensitive

#### ❌ Access Forbidden

```bash
# Error
Error: Forbidden (403): User cannot access resource
```

**Solution:**

```bash
# Check current user
kubectl auth whoami

# Verify permissions
kubectl auth can-i create deployments
kubectl auth can-i create services

# Grant permissions (requires admin)
kubectl create clusterrolebinding sbkube-admin \
  --clusterrole=cluster-admin \
  --user=$(kubectl config current-context)
```

______________________________________________________________________

### 4. Configuration File Issues

#### ❌ YAML Syntax Error

```bash
# Error
yaml.scanner.ScannerError: found character '\t' that cannot start any token
```

**Solution:**

```bash
# Validate YAML syntax
python -c "import yaml; yaml.safe_load(open('config.yaml'))"

# Check for tabs (should use spaces)
cat -A config.yaml  # Shows tab characters

# Use online validators
# https://yamlchecker.com/
```

#### ❌ Schema Validation Failed

```bash
# Error
ValidationError: 'invalid-type' is not one of ['exec', 'helm', ...]
```

**Solution:**

```bash
# Validate configuration
sbkube validate

# Check supported app types
sbkube --help

# Supported types: helm, git, http, kustomize, yaml, action, exec, noop
```

#### ❌ sources.yaml Not Found

```bash
# Error
Error: sources.yaml not found in: ./sources.yaml, ../sources.yaml, ./sources.yaml
```

**Solution (v0.4.7+):**

```bash
# Search order (automatic):
# 1. Current directory (.)
# 2. Parent directory (..)
# 3. base-dir (--base-dir option)

# Create sources.yaml
cat > sources.yaml << 'EOF'
kubeconfig: ~/.kube/config
kubeconfig_context: my-cluster
cluster: production

helm_repos:
  grafana:
    url: https://grafana.github.io/helm-charts
EOF
```

#### ❌ Circular Dependency

```bash
# Error
Error: Circular dependency detected: app-a → app-b → app-a
```

**Solution:**

```yaml
# Wrong configuration
apps:
  app-a:
    depends_on: [app-b]
  app-b:
    depends_on: [app-a]  # Circular!

# Fixed configuration
apps:
  app-a:
    # Remove depends_on or adjust
  app-b:
    depends_on: [app-a]
```

______________________________________________________________________

### 5. Deployment Issues

#### ❌ Helm Chart Not Found

```bash
# Error
Error: failed to download chart: chart not found
```

**Solution:**

```bash
# Update Helm repositories
helm repo add grafana https://grafana.github.io/helm-charts
helm repo update

# Verify chart exists
helm search repo grafana/grafana

# Check sources.yaml configuration
cat sources.yaml
```

#### ❌ Helm Repository Not in sources.yaml

```bash
# Error
❌ Helm repo 'browserless' not found in sources.yaml
```

**Common Causes:**

1. **OCI Registry**: Should be in `oci_registries` not `helm_repos`
2. **Name Mismatch**: Typo between sources.yaml and config.yaml
3. **Deprecated Repository**: Using old/unsupported repositories

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
    chart: browserless/browserless-chrome
```

**Case 2: Repository Name Typo**

```yaml
# ✅ Correct - names match
# sources.yaml
helm_repos:
  codecentric: https://codecentric.github.io/helm-charts

# config.yaml
apps:
  mailhog:
    chart: codecentric/mailhog
```

**Case 3: Deprecated Repository**

```yaml
# ❌ Wrong - Helm Stable deprecated in 2020
helm_repos:
  kubernetes-charts: https://charts.helm.sh/stable

# ✅ Correct - Use official repository
helm_repos:
  descheduler: https://kubernetes-sigs.github.io/descheduler/
```

**Verification:**

```bash
# Check OCI registry
helm pull oci://tccr.io/truecharts/browserless-chrome --version 1.0.0

# Check Helm repository
helm repo add codecentric https://codecentric.github.io/helm-charts
helm repo update
helm search repo codecentric/

# Verify sources.yaml structure
cat sources.yaml | grep -A 5 "oci_registries:"
cat sources.yaml | grep -A 5 "helm_repos:"
```

#### ❌ Namespace Not Found

```bash
# Error
Error: namespaces "my-namespace" not found
```

**Solution:**

```bash
# Create namespace
kubectl create namespace my-namespace

# Or use YAML
cat <<EOF | kubectl apply -f -
apiVersion: v1
kind: Namespace
metadata:
  name: my-namespace
EOF
```

#### ❌ Helm Release Conflict

```bash
# Error
Error: cannot re-use a name that is still in use
```

**Solution:**

```bash
# List existing releases
helm list -n my-namespace

# Delete existing release
helm uninstall grafana-my-namespace -n my-namespace

# Or use sbkube delete
sbkube delete --namespace my-namespace

# Redeploy
sbkube deploy
```

______________________________________________________________________

### 6. Command-Specific Issues

#### prepare Command Errors

##### ❌ Chart Pull Failed

```bash
# Error
Error: chart 'grafana/grafana' version '6.50.0' not found
```

**Solution:**

```bash
# Check available versions
helm search repo grafana/grafana --versions | head -20

# Update config.yaml with valid version
apps:
  grafana:
    chart: grafana/grafana
    version: 6.60.0  # Or remove for latest
```

##### ❌ Git Clone Failed

```bash
# Error
Error: failed to clone repository: Authentication required
```

**Solution:**

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
```

##### ❌ Chart Already Exists (v0.4.6+)

```bash
# Info
⏭️  Chart already exists, skipping: grafana
    Use --force to re-download
```

**Solution:**

```bash
# Force re-download
sbkube prepare --force
```

#### build Command Errors

##### ❌ Override Not Applied

```bash
# Warning
⚠️  Override directory found but not configured: myapp
```

**Solution:**

```yaml
# config.yaml - Add overrides field
apps:
  myapp:
    type: helm
    chart: ingress-nginx/ingress-nginx
    overrides:  # Required!
      - templates/configmap.yaml
      - files/config.txt
```

##### ❌ Build Directory Empty

```bash
# Info
⏭️ Skipping Helm app (no customization): myapp
```

**Explanation:** SBKube skips building when:
- Using local chart (`chart: ./charts/myapp`)
- No `overrides` configured
- No `removes` configured

This is **normal behavior** for optimization.

**Solutions:**

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

##### ❌ .Files.Get Returns Empty

```bash
# Error
Error: template: ... error calling Get: file not found
```

**Solution:**

```yaml
# config.yaml - Include files directory
apps:
  myapp:
    type: helm
    chart: my-chart
    overrides:
      - templates/configmap.yaml
      - files/config.toml  # Must include files!
```

#### deploy Command Errors

##### ❌ Pod Stuck in Pending

```bash
# Status
NAME                       READY   STATUS    RESTARTS   AGE
grafana-5f7b4c5d9-abcde    0/1     Pending   0          2m
```

**Diagnosis:**

```bash
# Check pod events
kubectl describe pod grafana-5f7b4c5d9-abcde -n test-namespace

# Common causes:
# 1. Resource shortage
kubectl top nodes
kubectl describe nodes

# 2. PVC mount failure
kubectl get pvc -n test-namespace
kubectl describe pvc <pvc-name> -n test-namespace

# 3. Node selector mismatch
kubectl get nodes --show-labels
```

##### ❌ ImagePullBackOff

```bash
# Status
NAME                       READY   STATUS             RESTARTS   AGE
grafana-5f7b4c5d9-abcde    0/1     ImagePullBackOff   0          1m
```

**Solution:**

```bash
# Check events
kubectl describe pod grafana-5f7b4c5d9-abcde -n test-namespace

# Verify image name/tag in values.yaml
image:
  repository: grafana/grafana
  tag: 9.5.3  # Correct tag?

# For private registry, create secret
kubectl create secret docker-registry regcred \
  --docker-server=<registry-url> \
  --docker-username=<username> \
  --docker-password=<password> \
  -n test-namespace

# Add to values.yaml
imagePullSecrets:
  - name: regcred
```

##### ❌ CrashLoopBackOff

```bash
# Status
NAME                       READY   STATUS             RESTARTS   AGE
grafana-5f7b4c5d9-abcde    0/1     CrashLoopBackOff   5          3m
```

**Solution:**

```bash
# Check logs
kubectl logs grafana-5f7b4c5d9-abcde -n test-namespace
kubectl logs grafana-5f7b4c5d9-abcde -n test-namespace --previous

# Common issues:
# 1. Check environment variables
kubectl describe pod grafana-5f7b4c5d9-abcde -n test-namespace | grep -A 10 "Environment:"

# 2. Verify secrets/configmaps exist
kubectl get secrets -n test-namespace
kubectl get configmaps -n test-namespace

# 3. Debug with ephemeral container
kubectl debug grafana-5f7b4c5d9-abcde -n test-namespace -it --image=busybox
```

______________________________________________________________________

### 7. Hooks Related Issues

#### ❌ Hook Execution Failed

```bash
# Error
Error: Hook execution failed
Command: ./scripts/backup.sh
Exit code: 127
```

**Solution:**

```bash
# 1. Check file exists
ls -la ./scripts/backup.sh

# 2. Grant execute permission
chmod +x ./scripts/backup.sh

# 3. Verify environment variables
hooks:
  post_deploy:
    - |
      echo "SBKUBE_APP_NAME: $SBKUBE_APP_NAME"
      echo "SBKUBE_NAMESPACE: $SBKUBE_NAMESPACE"

# 4. Specify working directory
post_deploy_tasks:
  - type: command
    command: ["./backup.sh"]
    working_dir: "./scripts"
```

#### ❌ Manifests Hook File Not Found

```bash
# Error
Error: Manifest file not found: manifests/cluster-issuer.yaml
```

**Solution:**

```bash
# Check relative path
ls manifests/cluster-issuer.yaml

# Phase 1: app_dir relative
pre_deploy_manifests:
  - path: manifests/cluster-issuer.yaml

# Phase 2: working_dir configurable
pre_deploy_tasks:
  - type: manifests
    paths: ["cluster-issuer.yaml"]
    working_dir: "./manifests"
```

#### ❌ Task Validation Timeout

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
    on_failure: warn
```

**Related Documentation:**
- **[Hooks Reference](../02-features/hooks-reference.md)** - All hook types and environment variables
- **[Hooks Guide](../02-features/hooks.md)** - Practical examples and best practices
- **[Hooks Migration Guide](../02-features/hooks-migration-guide.md)** - Phase transition guide

______________________________________________________________________

### 8. Network Related Issues

#### ❌ Git SSL Certificate Problem

```bash
# Error
fatal: unable to access 'https://github.com/...': SSL certificate problem
```

**Solution:**

```bash
# Temporary: Disable SSL verification
git config --global http.sslVerify false

# Better: Use SSH keys
ssh-keygen -t rsa -b 4096 -C "your.email@example.com"
# Add public key to GitHub and use SSH URLs
```

#### ❌ Helm Repository Unreachable

```bash
# Error
Error: failed to fetch https://grafana.github.io/helm-charts/index.yaml
```

**Solution:**

```bash
# Test connectivity
curl -I https://grafana.github.io/helm-charts/index.yaml

# Configure proxy if needed
export HTTP_PROXY=http://proxy.company.com:8080
export HTTPS_PROXY=http://proxy.company.com:8080

# Re-add repository
helm repo remove grafana
helm repo add grafana https://grafana.github.io/helm-charts
helm repo update
```

______________________________________________________________________

### 9. State Management Issues

#### ❌ Database Locked

```bash
# Error
sqlite3.OperationalError: database is locked
```

**Solution:**

```bash
# Check state database location
ls -la ~/.sbkube/

# Remove lock file (if safe)
rm ~/.sbkube/deployment.db-lock

# Future feature: Reset database
# sbkube reset-db
```

#### ❌ State Inconsistency

```bash
# Manual state verification
kubectl get all -A
helm list -A
sbkube history

# Future feature: Sync state
# sbkube sync-state
```

______________________________________________________________________

## 🔧 Advanced Debugging

### Step-by-Step Execution

```bash
# Execute each phase individually
sbkube validate       # Configuration validation
sbkube prepare        # Source preparation
sbkube build          # App building
sbkube template       # Template generation
sbkube deploy         # Deployment execution
```

### Template Rendering

```bash
# Render templates for inspection
sbkube template --output-dir /tmp/rendered

# Specific app only
sbkube template --app redis --output-dir /tmp/rendered

# Direct Helm template
helm template test-release charts-built/redis \
  --namespace test-namespace \
  --values redis-values.yaml \
  --debug
```

### Kubernetes Debugging

```bash
# Dry-run resource creation
kubectl apply -f manifest.yaml --dry-run=client
kubectl apply -f manifest.yaml --dry-run=server

# Watch namespace events
kubectl get events -n test-namespace --sort-by='.lastTimestamp'

# Real-time logs
kubectl logs -f <pod-name> -n test-namespace

# Previous logs (after restart)
kubectl logs --previous <pod-name> -n test-namespace

# All containers in pod
kubectl logs <pod-name> -n test-namespace --all-containers

# Debug container
kubectl debug <pod-name> -n test-namespace -it --image=busybox

# Node debugging
kubectl debug node/<node-name> -it --image=busybox
```

______________________________________________________________________

## 🚀 Performance Issues

### Slow Deployments

```bash
# Optimize parallelization
export SBKUBE_MAX_WORKERS=8

# Disable unnecessary apps in config.yaml
apps:
  unused-app:
    enabled: false

# Use Helm cache
export HELM_CACHE_HOME=/tmp/helm-cache
```

### High Memory Usage

```bash
# Monitor memory
top -p $(pgrep -f sbkube)

# Set memory limit
ulimit -v 2097152  # 2GB limit

# Process in batches
sbkube build --app app1
sbkube build --app app2
```

______________________________________________________________________

## 📱 Platform-Specific Issues

### Windows Environment

```powershell
# Run in PowerShell
python -m sbkube.cli deploy

# Use forward slashes in YAML
# paths: "config/app.yaml"  # Good
# paths: "config\\app.yaml" # Avoid

# Run PowerShell as Administrator for permissions
```

### macOS Environment

```bash
# Fix Homebrew permissions
sudo chown -R $(whoami) /usr/local/Homebrew

# Update PATH
echo 'export PATH="/usr/local/bin:$PATH"' >> ~/.zshrc
source ~/.zshrc
```

______________________________________________________________________

## 📊 Troubleshooting Checklist

### General Resolution Order

1. **Information Gathering**
   ```bash
   sbkube --version
   kubectl cluster-info
   kubectl get nodes
   helm version
   sbkube history
   ```

2. **Log Analysis**
   ```bash
   sbkube --verbose <command>
   kubectl logs <pod-name> -n <namespace>
   kubectl describe <resource> <name> -n <namespace>
   ```

3. **Configuration Validation**
   ```bash
   sbkube validate
   yamllint config.yaml
   helm lint charts-built/<chart>
   ```

4. **Step-by-Step Testing**
   ```bash
   sbkube prepare
   sbkube build
   sbkube template --output-dir /tmp/test
   sbkube deploy --dry-run
   sbkube deploy
   ```

______________________________________________________________________

## 📞 Support and Resources

### Collecting Debug Information

When reporting issues, include:

```bash
# Environment information
sbkube version
python --version
kubectl version --client
helm version

# Detailed logs
sbkube --verbose deploy > sbkube.log 2>&1

# Configuration files (remove sensitive data)
cat config.yaml
cat sources.yaml
```

### Community Support

- **[Issue Tracker](https://github.com/ScriptonBasestar/kube-app-manager/issues)** - Bug reports and feature requests
- **[FAQ](faq.md)** - Frequently asked questions
- **[GitHub Discussions](https://github.com/ScriptonBasestar/kube-app-manager/discussions)** - Usage questions

______________________________________________________________________

## 📚 Related Documentation

- **[Common Issues](common-issues.md)** - Specific resolution cases
- **[FAQ](faq.md)** - Frequently asked questions
- **[Debugging Guide](debugging.md)** - Advanced debugging methods
- **[Configuration Guide](../03-configuration/)** - Proper configuration methods
- **[Commands Reference](../02-features/commands.md)** - Command usage and examples

______________________________________________________________________

*If your issue is not resolved, please feel free to contact us via the [issue tracker](https://github.com/ScriptonBasestar/kube-app-manager/issues). We'll help you as soon as possible!*