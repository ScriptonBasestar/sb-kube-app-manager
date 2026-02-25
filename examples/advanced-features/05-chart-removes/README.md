# Chart Removes Field Example

**SBKube v0.4.0+** supports the `removes` field to clean up unwanted files from Helm charts during the build phase. This reduces chart size, improves deployment time, and removes unnecessary clutter.

## 📋 Overview

This example demonstrates:
- Removing test files and examples
- Removing specific chart components
- Pattern-based file removal
- Comparison with default behavior (no removal)

## 🎯 Key Concepts

### The `removes` Field

The `removes` field accepts a list of file/directory patterns to delete from the Helm chart after download:

```yaml
apps:
  my-app:
    type: helm
    chart: grafana/grafana
    removes:
      - "templates/tests/*"   # Remove test directory
      - "ci/*"                # Remove CI files
      - "*.md"                # Remove markdown files
      - "**/*.md"             # Remove all markdown files recursively
```

### Pattern Syntax

Supports glob patterns:
- `*` - Matches any characters within a directory
- `**` - Matches any characters across directories (recursive)
- `?` - Matches single character
- `[abc]` - Matches any character in brackets

### When Files Are Removed

Files are removed during the **build phase**, after chart download but before template rendering:

```
prepare → build (removes applied here) → template → deploy
```

## 📁 File Structure

```
05-chart-removes/
├── sbkube.yaml                # Main configuration with 4 apps
├── sbkube.yaml               # Cluster and Helm repo configuration
├── grafana-values.yaml        # Grafana minimal config
├── redis-values.yaml          # Redis core-only config
├── prometheus-values.yaml     # Prometheus compact config
├── nginx-values.yaml          # NGINX full config (no removal)
└── README.md
```

## 🔧 Configuration Examples

### Example 1: Remove Tests and Examples

```yaml
grafana-minimal:
  type: helm
  chart: grafana/grafana
  removes:
    - "templates/tests/*"      # All test templates
    - "ci/*"                   # CI configuration
    - "examples/*"             # Example files
    - "*.md"                   # Top-level markdown files
    - "OWNERS"                 # OWNERS file
    - ".helmignore"            # Helmignore file
```

**Before removal** (typical Grafana chart):
```
grafana-10.1.2/
├── Chart.yaml
├── README.md
├── values.yaml
├── templates/
│   ├── deployment.yaml
│   ├── service.yaml
│   └── tests/
│       ├── test-podsecuritypolicy.yaml
│       └── test-serviceaccount.yaml
├── ci/
│   └── default-values.yaml
└── examples/
    └── custom-values.yaml
```

**After removal**:
```
grafana-10.1.2/
├── Chart.yaml
├── values.yaml
└── templates/
    ├── deployment.yaml
    └── service.yaml
```

### Example 2: Remove Optional Components

```yaml
redis-core-only:
  type: helm
  chart: bitnami/redis
  removes:
    - "templates/metrics/*"           # Metrics exporter
    - "templates/serviceaccount.yaml" # ServiceAccount
    - "templates/networkpolicy.yaml"  # NetworkPolicy
    - "templates/tls-secret.yaml"     # TLS secrets
    - "ci/*"                          # CI files
    - "*.md"                          # Documentation
```

**Use Case**: Deploy only core Redis functionality, excluding optional components like metrics exporters or network policies.

### Example 3: Pattern-Based Removal

```yaml
prometheus-compact:
  type: helm
  chart: grafana/prometheus
  removes:
    - "**/*.md"                # All markdown files (recursive)
    - "**/*test*.yaml"         # All test YAML files
    - "**/examples/**"         # All example directories
    - "ci/**"                  # All CI directory contents
    - "docs/**"                # All documentation
```

**Pattern Breakdown**:
- `**/*.md` - Finds and removes ALL markdown files in any subdirectory
- `**/*test*.yaml` - Removes any YAML file containing "test" in the name
- `**/examples/**` - Removes entire examples directory tree
- `ci/**` - Removes all contents of ci/ directory
- `docs/**` - Removes all contents of docs/ directory

### Example 4: No Removal (Default)

```yaml
nginx-full:
  type: helm
  chart: bitnami/nginx
  # No 'removes' field - keep all chart files
```

**Use Case**: Keep all chart files for debugging, documentation reference, or when chart size is not a concern.

## 🚀 Usage

### 1. Validate Configuration

```bash
sbkube validate -f sbkube.yaml examples/advanced-features/05-chart-removes/sbkube.yaml
```

### 2. Build and Check Removal

```bash
# Run build phase to see which files are removed
sbkube build --app-dir examples/advanced-features/05-chart-removes

# Check chart size before/after removal
du -sh .sbkube/charts/grafana/grafana-10.1.2
```

### 3. Deploy (Dry Run)

```bash
sbkube apply --app-dir examples/advanced-features/05-chart-removes --dry-run
```

**Expected Output**:
```
[2/4] build: Building Helm charts...
  ✓ grafana-minimal
    - Removed: templates/tests/* (2 files)
    - Removed: ci/* (1 file)
    - Removed: examples/* (1 file)
    - Removed: *.md (3 files)
    - Removed: OWNERS (1 file)
    - Total saved: ~15 KB

  ✓ redis-core-only
    - Removed: templates/metrics/* (4 files)
    - Removed: templates/serviceaccount.yaml
    - Total saved: ~8 KB

  ✓ prometheus-compact
    - Removed: **/*.md (12 files)
    - Removed: docs/** (8 files)
    - Total saved: ~25 KB

  ✓ nginx-full
    - No files removed
```

### 4. Deploy (Actual)

```bash
sbkube apply --app-dir examples/advanced-features/05-chart-removes
```

### 5. Verify Deployment

```bash
# All apps should deploy successfully despite file removal
kubectl get pods -n chart-removes-demo
```

### 6. Cleanup

```bash
sbkube delete --app-dir examples/advanced-features/05-chart-removes
```

## 📊 Comparison Table

| Aspect | With `removes` | Without `removes` |
|--------|----------------|-------------------|
| **Chart Size** | Smaller (10-30% reduction) | Full size |
| **Build Time** | Slightly faster | Standard |
| **Deploy Time** | Faster (less data to template) | Standard |
| **Debugging** | Less reference material | Full documentation |
| **Use Case** | Production, size-sensitive | Development, debugging |

## 💡 Best Practices

### 1. Remove Tests in Production

Tests are useful for chart development but unnecessary in production:
```yaml
removes:
  - "templates/tests/*"
  - "**/*test*.yaml"
```

### 2. Remove CI/CD Files

CI/CD configuration is not needed at deployment time:
```yaml
removes:
  - "ci/*"
  - ".github/**"
  - ".gitlab-ci.yml"
  - "Jenkinsfile"
```

### 3. Remove Documentation

Save space by removing markdown and docs:
```yaml
removes:
  - "**/*.md"
  - "docs/**"
  - "OWNERS"
  - "LICENSE"
```

### 4. Remove Examples

Example files are useful for learning but not for deployment:
```yaml
removes:
  - "examples/**"
  - "sample-values.yaml"
```

### 5. Be Cautious with Wildcards

Avoid overly broad patterns that might remove required files:

```yaml
# ❌ Too broad - might remove important files
removes:
  - "**/*"  # DON'T DO THIS!

# ✅ Specific patterns
removes:
  - "templates/tests/*"
  - "ci/*"
  - "*.md"
```

### 6. Test Before Production

Always test chart removal in dev/staging:
```bash
# Build and verify chart still works
sbkube build -f sbkube.yaml
sbkube template -f sbkube.yaml
sbkube apply -f sbkube.yaml --dry-run
```

## 🔍 Common Removal Patterns

### Minimal Chart (Production)

```yaml
removes:
  - "templates/tests/*"
  - "ci/*"
  - "examples/*"
  - "**/*.md"
  - "OWNERS"
  - ".helmignore"
```

### Ultra-Compact Chart

```yaml
removes:
  - "**/*test*"
  - "**/*example*"
  - "**/*.md"
  - "ci/**"
  - "docs/**"
  - "**/OWNERS"
  - "**/.helmignore"
  - "**/LICENSE*"
```

### Remove Specific Components

```yaml
# Remove metrics exporter
removes:
  - "templates/metrics/*"
  - "templates/*exporter*"

# Remove network policies
removes:
  - "templates/networkpolicy.yaml"
  - "templates/*network*"

# Remove ingress
removes:
  - "templates/ingress.yaml"
```

## 🐛 Troubleshooting

### Error: "Required file removed"

**Symptom**:
```
Error: template: grafana/templates/deployment.yaml:12:4:
executing "grafana/templates/deployment.yaml" at <include "grafana.labels" .>:
error calling include: template: grafana/templates/_helpers.tpl:2:3:
no template "_helpers.tpl" associated with template "gotpl"
```

**Cause**: Removed a required template file (like `_helpers.tpl`)

**Solution**:
```yaml
# ❌ Don't remove helper files
removes:
  - "templates/*.tpl"  # BAD!

# ✅ Be specific
removes:
  - "templates/tests/*"
```

### Chart Still Large After Removal

**Check**:
```bash
# List remaining files
ls -lah .sbkube/charts/grafana/grafana-10.1.2/

# Check if patterns matched
sbkube build -f sbkube.yaml --verbose
```

**Solution**: Use more specific or additional patterns

### Wildcard Not Matching

**Issue**: `*.md` doesn't match `docs/README.md`

**Reason**: Single `*` doesn't cross directory boundaries

**Solution**: Use `**/*.md` for recursive matching

## 📈 Size Reduction Examples

Real-world size reductions from popular charts:

| Chart | Original Size | After Removal | Reduction |
|-------|---------------|---------------|-----------|
| Grafana | ~500 KB | ~350 KB | 30% |
| Prometheus | ~1.2 MB | ~900 KB | 25% |
| Redis | ~300 KB | ~250 KB | 17% |
| NGINX | ~200 KB | ~170 KB | 15% |

**Typical savings**: 15-30% chart size reduction

## 🔗 Related Documentation

- [Helm Chart Customization](../../03-configuration/config-schema.md)
- [Chart Overrides](../../03-configuration/config-schema.md#overrides)
- [Application Types](../../02-features/application-types.md#helm)
- [Build Phase](../../02-features/commands.md#build)

## ⚠️ Important Notes

1. **v0.4.0+ Feature**: `removes` field is only available in SBKube v0.4.0 and later
2. **Build Phase Only**: Files are removed during build, not from the original chart source
3. **No Impact on Helm**: Removed files don't affect Helm's chart validation or rendering
4. **Permanent Removal**: Files are deleted from `.sbkube/charts/` until next chart download
5. **Pattern Matching**: Uses Python's `pathlib.Path.glob()` for pattern matching

## 📝 Summary

| Pattern Type | Example | Use Case |
|-------------|---------|----------|
| **Specific file** | `OWNERS`, `LICENSE` | Remove known files |
| **Directory** | `ci/*`, `examples/*` | Remove entire directories |
| **Extension** | `*.md`, `*.txt` | Remove by file type |
| **Recursive** | `**/*.md` | Remove across all subdirectories |
| **Wildcard** | `*test*` | Remove files matching pattern |

**Key Takeaway**: Use `removes` to optimize chart size in production while keeping full charts in development for debugging and reference.
