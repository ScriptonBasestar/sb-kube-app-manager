# Helm Label Injection Example

**SBKube v0.7.1+** automatically injects global labels and annotations into Helm charts via `commonLabels` and `commonAnnotations` in values. This feature simplifies label management across multiple apps.

## 📋 Overview

This example demonstrates:
- **Default behavior**: Automatic label/annotation injection (`helm_label_injection: true`)
- **Disabled injection**: For charts with strict schema validation (`helm_label_injection: false`)
- **When to use each approach**

## 🎯 Key Concepts

### Automatic Label Injection (v0.7.1+)

When `helm_label_injection: true` (default), SBKube automatically:

1. Merges `global_labels` + app-specific `labels`
2. Merges `global_annotations` + app-specific `annotations`
3. Injects them into Helm values as:
   ```yaml
   commonLabels:
     environment: development
     managed-by: sbkube
     team: platform
     app: grafana  # from app-specific labels

   commonAnnotations:
     contact: platform-team@example.com
     documentation: https://docs.example.com
     description: "..."  # from app-specific annotations
   ```

### When to Disable Injection

Set `helm_label_injection: false` for charts that:

- ❌ Have **strict schema validation** (e.g., Authelia, some operators)
- ❌ Don't support `commonLabels`/`commonAnnotations` fields
- ❌ Require custom labeling strategy
- ❌ Reject unknown fields in values

**Examples of strict charts**:
- `authelia/authelia` - Strict JSON schema validation
- Some Kubernetes operators with CRD-based configuration
- Charts with `additionalProperties: false` in values schema

## 📁 File Structure

```
04-helm-label-injection/
├── sbkube.yaml                # Main configuration with 3 apps
├── sbkube.yaml               # Cluster and Helm repo configuration
├── grafana-values.yaml        # Grafana config (injection enabled)
├── redis-values.yaml          # Redis config (injection disabled)
├── prometheus-values.yaml     # Prometheus config (injection enabled)
└── README.md
```

## 🔧 Configuration Breakdown

### sbkube.yaml Structure

```yaml
namespace: label-injection-demo

# Global labels applied to ALL apps (if injection enabled)
global_labels:
  environment: development
  managed-by: sbkube
  team: platform

global_annotations:
  contact: platform-team@example.com
  documentation: https://docs.example.com

apps:
  # App 1: Default behavior (injection enabled)
  grafana:
    type: helm
    chart: grafana/grafana
    # helm_label_injection: true (default - not specified)
    labels:
      app: grafana  # Merged with global_labels
    annotations:
      description: "Grafana dashboard"  # Merged with global_annotations

  # App 2: Injection disabled (strict schema chart)
  redis:
    type: helm
    chart: bitnami/redis
    helm_label_injection: false  # Disable automatic injection
    labels:
      app: redis  # NOT injected into Helm values
    annotations:
      schema-strict: "true"  # NOT injected into Helm values
```

### Resulting Helm Values

**Grafana (injection enabled)**:
```yaml
# grafana-values.yaml (as SBKube sees it)
adminPassword: admin123
service:
  type: ClusterIP

# Automatically injected by SBKube:
commonLabels:
  environment: development
  managed-by: sbkube
  team: platform
  app: grafana
  component: monitoring

commonAnnotations:
  contact: platform-team@example.com
  documentation: https://docs.example.com
  description: "Grafana dashboard for metrics visualization"
```

**Redis (injection disabled)**:
```yaml
# redis-values.yaml (unmodified)
auth:
  enabled: false
master:
  persistence:
    enabled: false

# NO automatic injection
# Labels are only stored in SBKube metadata, not passed to Helm
```

## 🚀 Usage

### 1. Validate Configuration

```bash
sbkube validate -f sbkube.yaml examples/advanced-features/04-helm-label-injection/sbkube.yaml
```

### 2. Deploy (Dry Run)

```bash
sbkube apply --app-dir examples/advanced-features/04-helm-label-injection --dry-run
```

**Expected Output**:
```
[1/4] prepare: Preparing Helm charts...
  ✓ grafana - helm_label_injection: enabled
  ✓ redis - helm_label_injection: disabled
  ✓ prometheus - helm_label_injection: enabled

[2/4] build: Building...
  ✓ Injecting commonLabels into grafana
  ✓ Injecting commonLabels into prometheus
  ⓘ Skipping label injection for redis (helm_label_injection: false)
```

### 3. Deploy (Actual)

```bash
sbkube apply --app-dir examples/advanced-features/04-helm-label-injection
```

### 4. Verify Label Injection

```bash
# Check Grafana labels (should have injected labels)
kubectl get deployment -n label-injection-demo grafana -o yaml | grep -A 10 "labels:"

# Check Redis labels (should NOT have injected labels)
kubectl get deployment -n label-injection-demo redis-master -o yaml | grep -A 10 "labels:"
```

### 5. Cleanup

```bash
sbkube delete --app-dir examples/advanced-features/04-helm-label-injection
```

## 📊 Comparison Table

| Feature | `helm_label_injection: true` | `helm_label_injection: false` |
|---------|------------------------------|-------------------------------|
| **Behavior** | Auto-inject labels/annotations | No injection |
| **Use Case** | Standard Helm charts | Strict schema charts |
| **global_labels** | ✅ Injected as commonLabels | ❌ Not injected |
| **App labels** | ✅ Merged and injected | ❌ Metadata only |
| **Helm values** | Modified with labels | Unmodified |
| **Chart Compatibility** | Most charts | Charts rejecting unknown fields |
| **Examples** | Grafana, Prometheus, NGINX | Authelia, some operators |

## 💡 Best Practices

### 1. Default to Enabled

Use `helm_label_injection: true` (default) for most charts:
```yaml
apps:
  my-app:
    type: helm
    chart: stable/nginx
    # helm_label_injection: true (default)
    labels:
      app: nginx
```

### 2. Disable Only When Necessary

Only set `helm_label_injection: false` if you encounter:
- Helm install errors about unknown fields
- Schema validation failures
- Charts explicitly documented as incompatible

```yaml
apps:
  strict-app:
    type: helm
    chart: authelia/authelia
    helm_label_injection: false  # Required for Authelia
```

### 3. Document Strict Charts

Add annotations to document why injection is disabled:
```yaml
apps:
  authelia:
    type: helm
    chart: authelia/authelia
    helm_label_injection: false
    annotations:
      reason: "Authelia uses strict JSON schema validation"
      workaround: "Labels applied via chart's own labelOverride field"
```

### 4. Test Before Production

Always test label injection behavior in dev/staging:
```bash
# Dry-run to see if labels are injected correctly
sbkube apply -f sbkube.yaml --dry-run

# Check rendered Helm values
sbkube template -f sbkube.yaml | grep -A 5 "commonLabels"
```

### 5. Use Global Labels Wisely

Global labels should be:
- **Stable**: Don't change frequently
- **Universal**: Apply to all apps in namespace
- **Meaningful**: Used for filtering, monitoring, cost tracking

```yaml
# ✅ Good global labels
global_labels:
  environment: production
  team: platform
  cost-center: engineering

# ❌ Avoid app-specific labels globally
global_labels:
  app: grafana  # This should be app-specific!
```

## 🔍 Troubleshooting

### Error: "unknown field 'commonLabels'"

**Symptom**:
```
Error: INSTALLATION FAILED: values don't meet the specifications of the schema
```

**Solution**:
```yaml
apps:
  my-app:
    helm_label_injection: false  # Disable injection
```

### Labels Not Appearing on Resources

**Possible Causes**:
1. Chart doesn't support `commonLabels`
2. `helm_label_injection: false` is set
3. Chart overrides labels internally

**Debug**:
```bash
# Check if labels were passed to Helm
sbkube template -f sbkube.yaml | grep -A 10 "commonLabels"

# Check actual resource labels
kubectl get deployment <name> -o jsonpath='{.metadata.labels}' | jq
```

### Conflicting Labels

If app-specific labels conflict with global labels, **app-specific labels win**:

```yaml
global_labels:
  environment: production

apps:
  dev-grafana:
    labels:
      environment: development  # Overrides global "production"
```

Result:
```yaml
commonLabels:
  environment: development  # App-specific value
```

## 🎓 Advanced Scenarios

### Mixed Injection Strategy

```yaml
apps:
  # Standard chart - injection enabled
  nginx:
    type: helm
    chart: nginx/nginx
    # Default: helm_label_injection: true

  # Strict chart - injection disabled, manual labels
  authelia:
    type: helm
    chart: authelia/authelia
    helm_label_injection: false
    values:
      - authelia-values.yaml  # Add labels manually here

  # Chart with custom label field - injection disabled
  custom-operator:
    type: helm
    chart: operator/custom
    helm_label_injection: false
    values:
      - custom-values.yaml  # Use chart's own label mechanism
```

### Conditional Injection via Environment

```yaml
# Production: Use injection for consistency
# config-prod.yaml
global_labels:
  environment: production

apps:
  grafana:
    helm_label_injection: true

# Development: Disable for faster iteration
# config-dev.yaml
apps:
  grafana:
    helm_label_injection: false  # Skip injection overhead
```

## 🔗 Related Documentation

- [Helm Chart Customization](../../03-configuration/config-schema.md)
- [Global Labels/Annotations](../../03-configuration/config-schema.md#global-labels)
- [Application Types](../../02-features/application-types.md#helm)
- [Cluster Global Values](../../cluster-global-values/README.md)

## ⚠️ Important Notes

1. **v0.7.1+ Feature**: `helm_label_injection` is only available in SBKube v0.7.1 and later
2. **Default is Enabled**: If not specified, `helm_label_injection: true` is assumed
3. **No Helm Upgrade Impact**: Changing this field does NOT trigger a Helm upgrade (it's a build-time setting)
4. **Metadata Only When Disabled**: Labels are still stored in SBKube's deployment state for tracking
5. **Chart Compatibility**: Always check chart documentation for `commonLabels` support

## 📝 Summary

| When to Use | Setting | Behavior |
|-------------|---------|----------|
| **Most charts** | `helm_label_injection: true` (default) | Auto-inject labels via commonLabels |
| **Strict schema charts** | `helm_label_injection: false` | No injection, manual labels if needed |
| **Mixed environment** | Both in same config | Fine-grained control per app |

**Key Takeaway**: Use automatic injection by default, disable only when you encounter schema validation errors.
