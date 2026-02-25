______________________________________________________________________

## type: User Guide audience: End User, Developer topics: [migration, upgrade, breaking-changes] llm_priority: medium last_updated: 2026-02-25

# SBKube Migration Guide

Comprehensive guide for migrating SBKube configuration across different versions.

______________________________________________________________________

## TL;DR

- **Current Version**: v0.11.0
- **Latest Stable**: v0.11.0
- **Major Changes**: v0.11.0 (unified apply workflow), v0.10.0 (unified config), v0.7.1 (cluster global values)
- **Migration Tool**: `sbkube migrate` converts legacy configs to unified format
- **Recommended Format**: `sbkube.yaml` (unified config)
- **Related**: [Unified Config Schema](unified-config-schema.md), [Config Schema](config-schema.md)

> **⚠️ Important**: Starting with v0.10.0, the legacy configuration format (`sources.yaml` + `config.yaml`)
> is deprecated. Use `sbkube migrate` to convert to the new unified format (`sbkube.yaml`).
> Starting with v0.11.0, multi-phase deployment is handled through `sbkube apply -f sbkube.yaml`.

______________________________________________________________________

## Quick Migration (v0.11.0+)

Convert your legacy configuration to the new unified format:

```bash
# Preview migration (dry-run)
sbkube migrate --dry-run

# Migrate current directory
sbkube migrate

# Migrate from specific directory
sbkube migrate -s ./my-project -o ./my-project/sbkube.yaml

# Force overwrite existing file
sbkube migrate -o sbkube.yaml --force
```

______________________________________________________________________

## Table of Contents

- [Overview](#overview)
- [General Migration Process](#general-migration-process)
- [Version-Specific Guides](#version-specific-guides)
  - [Migration to v0.11.0 (Unified Apply Workflow)](#migration-to-v0110)
  - [Migration to v0.10.0 (Unified Config)](#migration-to-v0100)
  - [Migration to v0.9.0 (Multi-Phase)](#migration-to-v090)
  - [Migration to v0.7.1](#migration-to-v071)
  - [Migration to v0.7.0](#migration-to-v070)
  - [Migration to v0.6.1](#migration-to-v061)
  - [Migration to v0.6.0](#migration-to-v060)
  - [Migration to v0.5.0](#migration-to-v050)
- [Label Migration Guide](#label-migration-guide)
- [Breaking Changes Summary](#breaking-changes-summary)
- [FAQ](#faq)

______________________________________________________________________

## Overview

SBKube follows semantic versioning with clear upgrade paths between releases. Each major or minor version may introduce
breaking changes that require configuration migration.

### Version History

| Version | Release Date | Major Changes |
|---------|--------------|---------------|
| v0.11.0 | 2026-02-25 | Unified apply workflow for multi-phase deployments |
| v0.10.0 | 2025-02-04 | Unified config (sbkube.yaml), recursive executor, rollback_scope |
| v0.9.0 | 2025-01-20 | Early multi-phase deployment support |
| v0.7.1 | 2025-01-06 | Cluster global values, helm_label_injection, error handling |
| v0.7.0 | 2025-01-03 | LLM output integration |
| v0.6.1 | 2025-01-03 | Enhanced error handling |
| v0.6.0 | 2024-12-15 | State management, helm format |
| v0.5.0 | 2024-11-01 | Working directory consolidation |
| v0.4.x | 2024-09-01 | Initial stable release |

______________________________________________________________________

## General Migration Process

### Migration to v0.11.0

이전 multi-phase 서브커맨드는 제거되었으며, 다음 명령으로 전환하세요.

```bash
# Old (removed)
sbkube apply -f sbkube.yaml

# New
sbkube apply -f sbkube.yaml
sbkube apply -f sbkube.yaml --phase p2-data
sbkube apply -f sbkube.yaml --dry-run
```

### Pre-Migration Checklist

1. **Backup Configuration**:

   ```bash
   cp -r config/ config.backup/
   cp sources.yaml sources.yaml.backup
   ```

1. **Check Current Version**:

   ```bash
   sbkube version
   ```

1. **Review Changelog**:

   ```bash
   cat CHANGELOG.md | head -50
   ```

### Migration Steps

1. **Validate Current Config**:

   ```bash
   sbkube validate --app-dir <path>
   ```

1. **Run Migration** (if available):

   ```bash
   # Dry run first
   sbkube migrate --app-dir <path> --dry-run

   # Apply migration
   sbkube migrate --app-dir <path>
   ```

1. **Test Deployment**:

   ```bash
   sbkube apply --dry-run --namespace test
   ```

### Post-Migration Verification

1. **Check Doctor**:

   ```bash
   sbkube doctor
   ```

1. **Run Tests**:

   ```bash
   make test-quick
   ```

1. **Deploy to Staging**:

   ```bash
   sbkube deploy --profile staging --dry-run
   ```

______________________________________________________________________

## Version-Specific Guides

### Migration to v0.10.0

**Release Date**: 2025-02-04
**Type**: Major Release
**Breaking Changes**: Configuration format (backward compatible with warnings)

#### What's New

- **Unified Configuration**: Single `sbkube.yaml` file replaces `sources.yaml` + `config.yaml`
- **Recursive Executor**: Support for nested phases with settings inheritance
- **Rollback Scope**: Control rollback at app, phase, or deployment level
- **Migration Tool**: `sbkube migrate` command for automatic conversion

#### Migration Steps

**1. Run the Migration Tool**

```bash
# Preview the migration (recommended first)
sbkube migrate --dry-run

# Perform the migration
sbkube migrate -o sbkube.yaml

# Or specify source directory
sbkube migrate -s ./my-config -o ./my-config/sbkube.yaml
```

**2. Review the Generated File**

The migration tool converts:
- `sources.yaml` settings → `settings` section
- `config.yaml` apps → `apps` section
- legacy phase file phases → `phases` section

**3. Verify the Configuration**

```bash
sbkube apply -f sbkube.yaml --dry-run
```

**4. Test with Dry-Run**

```bash
sbkube apply -f sbkube.yaml --dry-run
```

**5. Remove Legacy Files (Optional)**

After verifying the migration:
```bash
# Backup first
mkdir legacy-backup
mv sources.yaml config.yaml legacy-backup/

# Or for legacy phase format
mv legacy-phase.yaml legacy-backup/
```

#### Configuration Mapping

| Legacy Format | Unified Format |
|---------------|----------------|
| `sources.yaml` | `settings:` section |
| `config.yaml` | `apps:` section |
| `legacy-phase.yaml` | `metadata:` + `phases:` sections |
| `helm_repos:` (list) | `settings.helm_repos:` (dict) |
| `repos:` | `settings.helm_repos:` |

#### New Features in v0.10.0

**1. Settings Inheritance**

```yaml
settings:
  namespace: default  # Global default

phases:
  p1-prod:
    settings:
      namespace: production  # Phase override
    apps:
      nginx:
        namespace: nginx-ns  # App override (highest priority)
```

**2. Rollback Scope**

```yaml
settings:
  on_failure: rollback
  rollback_scope: phase  # app | phase | all
```

**3. Execution Order**

```yaml
settings:
  execution_order: apps_first  # apps_first | phases_first
```

______________________________________________________________________

### Migration to v0.9.0

**Release Date**: 2025-01-20
**Type**: Feature Release
**Breaking Changes**: None

#### What's New

- **Multi-Phase Support**: Deployment orchestration via unified apply workflow
- **Parallel Execution**: Execute phases and apps in parallel
- **App Group Dependencies**: Define dependencies between app groups

See [Unified Config Schema](unified-config-schema.md) for details.

______________________________________________________________________

### Migration to v0.7.1

**Release Date**: 2025-01-06 **Type**: Feature Release **Breaking Changes**: None

#### New Features

**1. Cluster Global Values**

Add cluster-level values that apply to all Helm apps:

```yaml
# sources.yaml
kubeconfig: ~/.kube/config
kubeconfig_context: prod-cluster

# New in v0.7.1: Cluster global values
cluster_values_file: cluster-values.yaml  # External file (lowest priority)
global_values:  # Inline values (higher priority)
  global:
    environment: production
    monitoring:
      enabled: true
```

**Values Priority** (low to high):

1. `cluster_values_file` - External YAML file
1. `global_values` - Inline in sources.yaml
1. App-specific `values` files

**Migration Steps**:

1. **(Optional)** Create `cluster-values.yaml` for cluster-wide settings:

   ```yaml
   # cluster-values.yaml
   global:
     storageClass: local-path
     timezone: Asia/Seoul
   ```

1. **(Optional)** Add `cluster_values_file` or `global_values` to `sources.yaml`:

   ```yaml
   # sources.yaml
   cluster_values_file: cluster-values.yaml
   global_values:
     global:
       environment: production
   ```

1. Verify values inheritance:

   ```bash
   sbkube template --app-dir <path> --app <app-name>
   # Check rendered YAML for cluster global values
   ```

**See:** [sources-schema.md](sources-schema.md#cluster-global-values),
[examples/cluster-global-values/](../../examples/cluster-global-values/)

**2. helm_label_injection Control**

Disable automatic label injection for strict Helm charts:

```yaml
# config.yaml
apps:
  authelia:
    type: helm
    chart: authelia/authelia
    helm_label_injection: false  # New in v0.7.1
```

**When to use**:

- Charts with strict schema validation (e.g., Authelia)
- Charts that reject unknown labels
- Apps where you want manual label control

**Default**: `true` (labels injected automatically)

**Migration Steps**:

1. Check if you have apps failing with "unknown field" errors

1. Add `helm_label_injection: false` to those apps

1. Re-deploy:

   ```bash
   sbkube apply --app-dir <path> --app <app-name>
   ```

**3. Enhanced Error Messages**

No migration needed. Improved error messages for:

- Helm deployment timeouts (shows troubleshooting steps)
- Ctrl+C interruptions (shows status check commands)

**Example error message**:

```
❌ Helm deployment timed out after 300 seconds (5 minutes).

Possible causes:
  - Pod image pull is slow or failing
  - Pod is failing health checks
  - Insufficient cluster resources

Troubleshooting:
  1. Check pod status: kubectl get pods -n auth
  2. Check pod logs: kubectl logs -n auth <pod-name>
  3. Describe pod: kubectl describe pod -n auth <pod-name>
  4. Increase timeout: add 'timeout: 10m' to app config
```

#### Backward Compatibility

✅ **Fully backward compatible** with v0.7.0 and v0.6.x configurations.

- `cluster_values_file` and `global_values` are optional
- `helm_label_injection` defaults to `true` (existing behavior)
- All existing configs work without changes

#### Recommended Actions

1. Review new features in [CHANGELOG.md](../../CHANGELOG.md#071---2025-01-06)
1. Consider using cluster global values for multi-app clusters
1. Update configs for apps with strict schemas

______________________________________________________________________

### Migration to v0.7.0

**Release Date**: 2025-01-03 **Type**: Feature Release **Breaking Changes**: None

#### New Features

**LLM-Friendly Output System**

- `--format` option: `human`, `llm`, `json`, `yaml`
- `SBKUBE_OUTPUT_FORMAT` environment variable
- 80-90% token savings for LLM agents

**Migration Steps**:

No migration needed. New feature is opt-in.

**Usage**:

```bash
# LLM-optimized output
sbkube --format llm apply
sbkube --format llm status

# JSON output
sbkube --format json status

# Environment variable
export SBKUBE_OUTPUT_FORMAT=llm
sbkube apply
```

**See:** [llm-friendly-output.md](../02-features/llm-friendly-output.md)

______________________________________________________________________

### Migration to v0.6.1

**Release Date**: 2025-01-03 **Type**: Bug Fix Release **Breaking Changes**: None

#### Improvements

- Enhanced error handling and classification
- Better deployment failure messages
- Context-aware suggestions

______________________________________________________________________

### Migration to v0.5.0

**Major Change**: Working directory consolidation to `.sbkube/`

#### Directory Structure Change

**Before (v0.4.x)**:

```
project/
├── charts/          # Helm charts
├── repos/           # Git repositories
├── build/           # Build output
├── rendered/        # Template output
├── config.yaml
└── sources.yaml
```

**After (v0.5.0+)**:

```
project/
├── .sbkube/         # All working directories consolidated
│   ├── charts/      # Helm charts
│   ├── repos/       # Git repositories
│   ├── build/       # Build output
│   └── rendered/    # Template output
├── config.yaml
└── sources.yaml
```

#### Migration Steps

**Option 1: Automatic Migration**

```bash
# Create .sbkube directory
mkdir -p .sbkube

# Move existing directories
[ -d charts ] && mv charts .sbkube/
[ -d repos ] && mv repos .sbkube/
[ -d build ] && mv build .sbkube/
[ -d rendered ] && mv rendered .sbkube/

# Update .gitignore
echo ".sbkube/" >> .gitignore
```

**Option 2: Clean Regeneration**

```bash
# Remove old directories
rm -rf charts repos build rendered

# Update .gitignore
echo ".sbkube/" >> .gitignore

# Regenerate (automatically creates in .sbkube/)
sbkube prepare
sbkube build
```

#### CI/CD Updates

Update pipeline scripts that reference old paths:

**Before**:

```yaml
- name: Check rendered files
  run: ls -la rendered/
```

**After**:

```yaml
- name: Check rendered files
  run: ls -la .sbkube/rendered/
```

______________________________________________________________________

### Migration to v0.6.0

**Major Changes**:

- Helm chart format simplification
- CLI option renaming
- State management introduction

#### 1. Helm Chart Format

**Before (v0.2.x-v0.5.x)**:

```yaml
apps:
  grafana:
    type: helm
    repo: grafana        # ❌ Separate repo field
    chart: grafana       # ❌ Chart name only
    version: "10.1.2"
```

**After (v0.6.0+)**:

```yaml
apps:
  grafana:
    type: helm
    chart: grafana/grafana    # ✅ Combined repo/chart format
    version: "10.1.2"
```

#### 2. CLI Options Renamed

| Old (v0.5.x) | New (v0.6.0+) | Purpose | |--------------|---------------|---------| | `--env` | `--profile` |
Environment profile selection | | `--sources` | `--source` | Source configuration file |

**Example**:

```bash
# Before
sbkube deploy --env production --sources sources.yaml

# After
sbkube deploy --profile production --source sources.yaml
```

#### 3. State Management

New state tracking system introduced:

```bash
# Check deployment state
sbkube status

# Force rebuild with state reset
sbkube build --force

# View state history
sbkube state history
```

#### Automated Migration

```bash
# Run migration command
sbkube migrate --app-dir <path>

# Preview changes
sbkube migrate --app-dir <path> --dry-run

# Migrate specific file
sbkube migrate --config <path>/config.yaml
```

The migration tool will:

1. Back up original files to `.backup`
1. Convert `repo:` + `chart:` → `chart: repo/chart`
1. Update deprecated field names
1. Validate new format

______________________________________________________________________

### Migration to v0.6.1

**Major Changes**:

- LLM-friendly output formatting
- Enhanced command base class
- Improved error messages

#### New Features (No Breaking Changes)

1. **LLM Output Support**:

   ```bash
   # Human-readable (default)
   sbkube status

   # LLM-optimized output
   sbkube status --format llm

   # JSON output
   sbkube status --format json
   ```

1. **Enhanced Commands**: All commands now support:

   - `--quiet` for minimal output
   - `--format` for output formatting
   - Better error context

No configuration migration required for v0.6.1.

______________________________________________________________________

## Label Migration Guide

### Overview

SBKube v0.6.1+ automatically injects labels into all Kubernetes resources deployed via sbkube (Helm, YAML, Action,
Kustomize). This enables proper app-group classification and status tracking via `sbkube status --by-group`.

**Important**: Existing kubectl-deployed resources are **not affected**. Labels are only injected for new deployments
via sbkube.

### Automatic Label Injection

When you deploy applications using sbkube, labels are automatically added:

```yaml
metadata:
  labels:
    app.kubernetes.io/managed-by: sbkube
    sbkube.io/app-group: app_000_infra_network
    sbkube.io/app-name: traefik
  annotations:
    sbkube.io/deployment-id: dep_20250131_143022
    sbkube.io/deployed-at: 2025-01-31T14:30:22Z
    sbkube.io/deployed-by: archmagece
```

**Requirements**:

- Application directory must follow naming pattern: `app_XXX_category_subcategory`
- Example: `app_000_infra_network/traefik/`

### Disabling Label Injection for Strict Schema Charts (v0.7.1+)

Some Helm charts (e.g., Authelia, cert-manager) use strict schema validation and reject
`commonLabels`/`commonAnnotations`. For these charts, you can disable automatic label injection:

**config.yaml**:

```yaml
apps:
  authelia:
    type: helm
    chart: authelia/authelia
    helm_label_injection: false  # Disable automatic label injection
    values:
      - authelia.yaml
```

**Alternative: Add labels via values file** (optional):

```yaml
# authelia.yaml
labels:  # Use chart's native label support
  app.kubernetes.io/managed-by: sbkube
  sbkube.io/app-group: app_405_security_auth
  sbkube.io/app-name: authelia
```

**Impact**:

- `sbkube status`: App tracking still works via State DB and name patterns
- `sbkube history`: State DB-based tracking (fully functional)
- `sbkube rollback`: State DB-based rollback (fully functional)

**Why it works**: SBKube uses a priority-based classification system:

1. Labels (sbkube.io/app-group) - Recommended
1. **State DB** - Falls back when labels are disabled
1. Release name pattern - `app_XXX_*` matching
1. Namespace pattern - `app_XXX_*` matching

**When to disable**:

- Charts with strict schema validation (Authelia, cert-manager, some operator charts)
- Charts that don't support `commonLabels`/`commonAnnotations`
- OCI registry charts with limited customization

**Error symptoms**:

```
Error: values don't meet the specifications of the schema(s):
  authelia:
    - at '': additional properties 'commonAnnotations', 'commonLabels' not allowed
```

### Migration Path

#### For Manual kubectl Users (Existing Resources)

If you have existing resources deployed directly with `kubectl apply`, they won't be automatically relabeled. To enable
proper status tracking:

**Option 1: Re-deploy via sbkube** (Recommended)

```bash
# Create sbkube config for existing resources
sbkube init

# Add your apps to config.yaml
# Then re-deploy
sbkube --profile production apply
```

**Option 2: Manual Label Patching** (For non-sbkube resources)

If you want to label existing resources without re-deploying:

```bash
# Add labels to existing deployment
kubectl patch deployment myapp -n default \
  -p '{"metadata":{"labels":{"sbkube.io/app-group":"app_000_infra_network","sbkube.io/app-name":"myapp","app.kubernetes.io/managed-by":"sbkube"}}}'

# Add labels to existing statefulset
kubectl patch statefulset mydb -n default \
  -p '{"metadata":{"labels":{"sbkube.io/app-group":"app_010_database","sbkube.io/app-name":"postgres","app.kubernetes.io/managed-by":"sbkube"}}}'
```

**Option 3: Using kustomize to Add Labels** (For multiple resources)

Create a `kustomization.yaml`:

```yaml
apiVersion: kustomize.config.k8s.io/v1beta1
kind: Kustomization

resources:
  - deployment.yaml
  - service.yaml

commonLabels:
  app.kubernetes.io/managed-by: sbkube
  sbkube.io/app-group: app_000_infra_network
  sbkube.io/app-name: myapp
```

Then apply:

```bash
kubectl apply -k .
```

#### For Helm Users

If you deployed via Helm directly:

```bash
# Upgrade existing Helm release with sbkube labels
helm upgrade myrelease ./chart \
  --set-string commonLabels.app\\.kubernetes\\.io/managed-by=sbkube \
  --set-string commonLabels.sbkube\\.io/app-group=app_000_infra_network \
  --set-string commonLabels.sbkube\\.io/app-name=myapp
```

Or use sbkube for future deployments:

```bash
# Configure in config.yaml
apps:
  myapp:
    type: helm
    chart: myrepo/myapp

# Deploy with labels
sbkube apply
```

### Verifying Labels

Check that resources have the correct labels:

```bash
# Check deployment labels
kubectl get deployment -n default -o jsonpath='{.items[0].metadata.labels}'

# View with app-group classification
sbkube status --by-group

# Check specific app-group
sbkube status app_000_infra_network
```

### Label Classification Priority

When `sbkube status` groups releases, it uses this priority:

1. **`sbkube.io/app-group` label** (most reliable)
1. State DB records from previous sbkube deployments
1. Release/resource name pattern matching (`app_XXX_...`)
1. Namespace name pattern matching

### FAQ

**Q: Do I need to relabel existing resources?**

A: No, existing resources continue to work. Labels are only needed for proper `sbkube status --by-group` grouping and
cluster status tracking.

**Q: Can I mix sbkube and kubectl deployments?**

A: Yes! Non-sbkube resources without labels will appear in `unmanaged_releases` in status output.

**Q: What if my app directory doesn't follow `app_XXX_*` naming?**

A: Labels won't be injected. Consider renaming your directory to match the pattern, or manually add labels.

**Q: How do I remove sbkube labels?**

A: Use kubectl patch to remove specific labels:

```bash
kubectl patch deployment myapp --type='json' -p='[{"op": "remove", "path": "/metadata/labels/sbkube.io~1app-group"}]'
```

______________________________________________________________________

## Breaking Changes Summary

### v0.6.0 Breaking Changes

1. **Configuration Format**:

   - `repo` + `chart` fields → single `chart: repo/chart`
   - Removed deprecated `chart_patches` (use `overrides`)

1. **CLI Options**:

   - `--env` → `--profile`
   - `--sources` → `--source`

1. **Working Directory**:

   - Inherited from v0.5.0: `.sbkube/` consolidation

### v0.5.0 Breaking Changes

1. **Directory Structure**:

   - All working directories moved to `.sbkube/`
   - Simplified `.gitignore` requirements

1. **Default Paths**:

   - `template` output: `rendered/` → `.sbkube/rendered/`
   - `build` output: `build/` → `.sbkube/build/`

______________________________________________________________________

## FAQ

### Q: How do I check my current version?

```bash
sbkube version
```

### Q: Can I skip versions during upgrade?

Yes, but review all intermediate breaking changes. The migration tool handles multi-version jumps.

### Q: What if migration fails?

1. Restore from backup:

   ```bash
   cp config.yaml.backup config.yaml
   ```

1. Manually fix issues based on error messages

1. Use `sbkube validate` to check configuration

### Q: How to handle OCI registries?

**Before (v0.5.x)**:

```yaml
apps:
  browserless:
    repo: browserless
    chart: browserless-chrome
```

**After (v0.6.0+)**:

```yaml
apps:
  browserless:
    chart: browserless/browserless-chrome
```

With `sources.yaml`:

```yaml
helm_sources:
  browserless:
    type: oci
    url: oci://tccr.io/truecharts
```

### Q: Multiple apps with same chart?

This works fine - apps are distinguished by their key:

```yaml
apps:
  redis-cache:
    chart: grafana/loki    # Same chart
  redis-queue:
    chart: grafana/loki    # Different app name
```

### Q: How to rollback a migration?

1. **Downgrade SBKube**:

   ```bash
   uv pip install sbkube==0.4.9  # or desired version
   ```

1. **Restore configuration**:

   ```bash
   cp config.yaml.backup config.yaml
   ```

1. **For v0.5.0 directory changes**:

   ```bash
   # Move directories back
   mv .sbkube/charts ./
   mv .sbkube/repos ./
   mv .sbkube/build ./
   mv .sbkube/rendered ./
   rm -rf .sbkube
   ```

### Q: CI/CD pipeline updates needed?

Yes, if your pipelines reference:

- File paths (charts/, repos/, etc.)
- CLI options (--env vs --profile)
- Output locations

Update scripts to use new paths and options.

______________________________________________________________________

## Troubleshooting

### Issue: "Unknown field 'repo'"

**Cause**: Using old format in v0.6.0+

**Solution**: Combine repo and chart:

```yaml
# Wrong
repo: grafana
chart: grafana

# Correct
chart: grafana/grafana
```

### Issue: "Chart not found in repository"

**Cause**: Missing repository definition

**Solution**: Ensure `sources.yaml` contains:

```yaml
helm_sources:
  grafana:
    type: helm
    url: https://grafana.github.io/helm-charts
```

### Issue: Migration command not found

**Cause**: Running older version

**Solution**: Update SBKube:

```bash
uv pip install --upgrade sbkube
sbkube version  # Should show 0.6.0+
```

### Issue: State database errors

**Cause**: Corrupted state in v0.6.0+

**Solution**: Reset state:

```bash
rm -f .sbkube/state.db
sbkube doctor  # Reinitialize
```

______________________________________________________________________

## Need Help?

- **Documentation**: [docs/](../)
- **Examples**: [examples/](../../examples/)
- **Issues**: [GitHub Issues](https://github.com/ScriptonBasestar-io/sb-kube-app-manager/issues)
- **Changelog**: [CHANGELOG.md](../../CHANGELOG.md)

______________________________________________________________________

**Document Version**: 1.0 **Last Updated**: 2025-01-04 **Target Version**: v0.6.1+
