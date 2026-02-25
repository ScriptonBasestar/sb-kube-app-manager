______________________________________________________________________

## type: User Guide audience: End User, Developer topics: [troubleshooting, debugging, common-errors] llm_priority: high last_updated: 2025-01-04

# 🔍 SBKube Troubleshooting Guide

Quick reference guide for common issues encountered with SBKube.

## TL;DR

- **Quick Fixes**: Check kubectl, Helm, sources.yaml syntax
- **Commands**: `sbkube doctor`, `sbkube validate`
- **Common Errors**: Network, permissions, config validation
- **Related**: [Complete Error Reference](error-reference.md), [Common Dev Issues](common-dev-issues.md),
  [Deployment Failures](deployment-failures.md)

______________________________________________________________________

## 📚 Quick Navigation

### Troubleshooting Documents

- **[Complete Error Reference](error-reference.md)** - Full catalog of all error messages and solutions
- **[Common Dev Issues](common-dev-issues.md)** - Development environment problems (test failures, type errors, import
  errors, uv issues)
- **[Deployment Failures](deployment-failures.md)** - Production deployment specific issues
- **[FAQ](faq.md)** - Frequently asked questions

______________________________________________________________________

## 🚨 Quick Diagnostic Commands

```bash
# System check
sbkube doctor                      # Check all dependencies (future feature)
sbkube validate                     # Validate configuration files

# Version information
sbkube version                    # SBKube version
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

## 📋 Common Issues & Quick Fixes

### Configuration Errors

#### ❌ sources.yaml Not Found

```bash
# Error
Error: sources.yaml not found in: ./sources.yaml, ../sources.yaml
```

**Quick Fix:**

```bash
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

#### ❌ YAML Syntax Error

```bash
# Error
yaml.scanner.ScannerError: found character '\t' that cannot start any token
```

**Quick Fix:**

```bash
# Validate YAML syntax
python -c "import yaml; yaml.safe_load(open('config.yaml'))"

# Check for tabs (should use spaces)
cat -A config.yaml  # Shows tab characters
```

#### ❌ Schema Validation Failed

```bash
# Error
ValidationError: 'invalid-type' is not one of ['exec', 'helm', ...]
```

**Quick Fix:**

```bash
# Validate configuration
sbkube validate

# Supported types: helm, git, http, kustomize, yaml, action, exec, noop
```

> **For all configuration errors**: See [Complete Error Reference](error-reference.md#configuration-errors)

### Network/Connection Issues

#### ❌ Kubeconfig Not Found

```bash
# Error
Kubeconfig file not found (path: ~/.kube/config)
```

**Quick Fix:**

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
❌ Kubernetes context 'my-context' not found in kubeconfig
```

**Quick Fix:**

```bash
# List available contexts
kubectl config get-contexts

# Update sources.yaml with correct context
vim sources.yaml  # Change kubeconfig_context field
```

#### ❌ Access Forbidden

```bash
# Error
Error: Forbidden (403): User cannot access resource
```

**Quick Fix:**

```bash
# Check current user
kubectl auth whoami

# Verify permissions
kubectl auth can-i create deployments
kubectl auth can-i create services
```

> **For all network errors**: See [Complete Error Reference](error-reference.md#network-errors)

### Deployment Failures

#### ❌ Helm Chart Not Found

```bash
# Error
Error: failed to download chart: chart not found
```

**Quick Fix:**

```bash
# Update Helm repositories
helm repo add grafana https://grafana.github.io/helm-charts
helm repo update

# Verify chart exists
helm search repo grafana/grafana
```

#### ❌ Namespace Not Found

```bash
# Error
Error: namespaces "my-namespace" not found
```

**Quick Fix:**

```bash
# Create namespace
kubectl create namespace my-namespace
```

#### ❌ Pod Stuck in Pending/CrashLoopBackOff

```bash
# Check pod events
kubectl describe pod <pod-name> -n <namespace>

# Check logs
kubectl logs <pod-name> -n <namespace>
kubectl logs <pod-name> -n <namespace> --previous
```

> **For all deployment errors**: See [Complete Error Reference](error-reference.md#deployment-errors)

______________________________________________________________________

## 🔍 Troubleshooting Workflow

### 1. Information Gathering

```bash
sbkube version
kubectl cluster-info
kubectl get nodes
helm version
sbkube history
```

### 2. Log Analysis

```bash
sbkube --verbose <command>
kubectl logs <pod-name> -n <namespace>
kubectl describe <resource> <name> -n <namespace>
```

### 3. Configuration Validation

```bash
sbkube validate
yamllint config.yaml
helm lint charts-built/<chart>
```

### 4. Step-by-Step Testing

```bash
sbkube prepare
sbkube build
sbkube template --output-dir /tmp/test
sbkube deploy --dry-run
sbkube deploy
```

______________________________________________________________________

## 📋 Command-Specific Issues

### apply Command

Common issues with `sbkube apply`:

- Configuration validation errors
- Dependency resolution problems
- Hook execution failures

> **Detailed errors**: See [Complete Error Reference](error-reference.md#apply-command-errors)

### prepare Command

Common issues with `sbkube prepare`:

- Chart pull failures
- Git clone authentication
- Repository access problems

> **Detailed errors**: See [Complete Error Reference](error-reference.md#prepare-command-errors)

### build Command

Common issues with `sbkube build`:

- Override not applied warnings
- Build directory empty
- Template compilation errors

> **Detailed errors**: See [Complete Error Reference](error-reference.md#build-command-errors)

### deploy Command

Common issues with `sbkube deploy`:

- Pod scheduling issues
- Image pull failures
- Resource constraints

> **Detailed errors**: See [Complete Error Reference](error-reference.md#deploy-command-errors)

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

# Debug container
kubectl debug <pod-name> -n test-namespace -it --image=busybox
```

______________________________________________________________________

## 📞 Getting Help

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

### Support Resources

- **[Issue Tracker](https://github.com/ScriptonBasestar/kube-app-manager/issues)** - Bug reports and feature requests
- **[GitHub Discussions](https://github.com/ScriptonBasestar/kube-app-manager/discussions)** - Usage questions
- **[FAQ](faq.md)** - Frequently asked questions

______________________________________________________________________

## 📚 See Also

- **[Complete Error Reference](error-reference.md)** - Full catalog of all errors and solutions
- **[Common Dev Issues](common-dev-issues.md)** - Development environment specific issues
- **[Deployment Failures](deployment-failures.md)** - Production deployment issues
- **[FAQ](faq.md)** - Frequently asked questions
- **[Configuration Guide](../03-configuration/)** - Proper configuration methods
- **[Commands Reference](../02-features/commands.md)** - Command usage and examples

______________________________________________________________________

*If your issue is not resolved, please check the [Complete Error Reference](error-reference.md) or contact us via the
[issue tracker](https://github.com/ScriptonBasestar/kube-app-manager/issues).*
