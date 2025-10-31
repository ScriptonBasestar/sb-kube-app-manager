# SBKube Migration Guide

This guide helps you migrate your SBKube configuration from older versions to the latest format.

______________________________________________________________________

## Table of Contents

- [v0.2.x → v0.5.0](#v02x--v050)
  - [Breaking Changes](#breaking-changes)
  - [Automated Migration](#automated-migration)
  - [Manual Migration](#manual-migration)
- [Quick Migration Checklist](#quick-migration-checklist)
- [Troubleshooting](#troubleshooting)

______________________________________________________________________

## v0.2.x → v0.5.0

### Breaking Changes

#### 1. Helm Chart Format

**Before (v0.2.x)**:

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

**Rationale**: Simplifies configuration and aligns with Helm's native `chart` parameter format.

______________________________________________________________________

#### 2. CLI Options Renamed

| v0.2.x | v0.6.0+ | Purpose | |--------|---------|---------| | `--env` | `--profile` | Environment profile selection |
| `--sources` | `--source` | Source configuration file | | `--config` | `--config` | Main configuration file (unchanged)
|

**Example**:

```bash
# Before (v0.2.x)
sbkube deploy --env production --sources sources.yaml

# After (v0.6.0+)
sbkube deploy --profile production --source sources.yaml
```

______________________________________________________________________

#### 3. Deprecated Fields Removed

The following deprecated fields are no longer supported:

- `chart_patches` → Use `overrides` instead
- `app.specs.repo` + `app.specs.chart` → Use single `app.specs.chart: repo/chart`

______________________________________________________________________

### Automated Migration

SBKube v0.5.0 includes a built-in migration command:

```bash
# Migrate all config files in a directory
sbkube migrate --app-dir <path>

# Dry run (preview changes without modifying files)
sbkube migrate --app-dir <path> --dry-run

# Migrate specific file
sbkube migrate --config <path>/config.yaml
```

**Migration Process**:

1. Backs up original files to `config.yaml.backup`
1. Converts `repo:` + `chart:` → `chart: repo/chart`
1. Updates deprecated field names
1. Validates new format with Pydantic models

**Example Output**:

```
✅ Migrating: examples/basic/config.yaml
  - Converted grafana: repo='grafana', chart='grafana' → chart='grafana/grafana'
  - Converted prometheus: repo='prometheus-community', chart='prometheus' → chart='prometheus-community/prometheus'
  - Backup created: config.yaml.backup
✅ Migration completed: 2 apps updated
```

______________________________________________________________________

### Manual Migration

If you prefer to migrate manually, follow these steps:

#### Step 1: Update Chart References

Find all Helm apps with separate `repo:` and `chart:` fields:

```bash
# Search for apps using old format
grep -r "repo:" --include="config.yaml" your-project/
```

Replace with combined format:

```yaml
# Before
apps:
  nginx:
    repo: bitnami
    chart: nginx
    version: "18.2.4"

# After
apps:
  nginx:
    chart: bitnami/nginx
    version: "18.2.4"
```

#### Step 2: Update CLI Commands

Update your scripts/documentation that use deprecated flags:

```bash
# Before
sbkube prepare --env staging --sources sources.yaml
sbkube deploy --env production

# After
sbkube prepare --profile staging --source sources.yaml
sbkube deploy --profile production
```

#### Step 3: Update sources.yaml (if using)

Ensure your `sources.yaml` uses the correct repository name format:

**sources.yaml**:

```yaml
helm_sources:
  bitnami:
    type: helm
    url: https://charts.bitnami.com/bitnami

  grafana:
    type: helm
    url: https://grafana.github.io/helm-charts
```

**config.yaml** references:

```yaml
apps:
  nginx:
    chart: bitnami/nginx  # Matches 'bitnami' in sources.yaml

  grafana:
    chart: grafana/grafana  # Matches 'grafana' in sources.yaml
```

#### Step 4: Validate Configuration

Run validation to ensure your migrated config is correct:

```bash
sbkube validate --app-dir <path>
```

Expected output:

```
✅ Configuration is valid
  - Namespace: default
  - Apps: 3
  - Helm charts: 3
  - YAML apps: 0
```

______________________________________________________________________

## Quick Migration Checklist

### Pre-Migration

- [ ] Backup your config files: `cp -r config/ config.backup/`
- [ ] Review changelog: [CHANGELOG.md](../../CHANGELOG.md)
- [ ] Check SBKube version: `sbkube --version`

### Migration Steps

- [ ] Run automated migration: `sbkube migrate --app-dir <path> --dry-run`
- [ ] Review migration preview
- [ ] Apply migration: `sbkube migrate --app-dir <path>`
- [ ] Validate configuration: `sbkube validate --app-dir <path>`
- [ ] Update CI/CD scripts (if using deprecated CLI options)
- [ ] Test deployment: `sbkube apply --app-dir <path> --dry-run --namespace test`

### Post-Migration

- [ ] Run full deployment test in staging environment
- [ ] Update documentation/runbooks with new CLI syntax
- [ ] Remove backup files after successful migration

______________________________________________________________________

## Troubleshooting

### Issue: "Unknown field 'repo'"

**Error**:

```
ValidationError: Extra inputs are not permitted
  - Field: apps.grafana.repo
```

**Solution**: You're using the old format. Combine `repo` and `chart` into a single `chart` field:

```yaml
# Wrong
repo: grafana
chart: grafana

# Correct
chart: grafana/grafana
```

______________________________________________________________________

### Issue: "Chart not found in repository"

**Error**:

```
Error: chart "grafana" not found in grafana repository
```

**Solution**: Ensure your `sources.yaml` contains the repository definition:

```yaml
helm_sources:
  grafana:
    type: helm
    url: https://grafana.github.io/helm-charts
```

And your chart reference matches:

```yaml
apps:
  my-grafana:
    chart: grafana/grafana  # ✅ Correct
    # Not: chart: grafana   # ❌ Wrong
```

______________________________________________________________________

### Issue: Migration command not found

**Error**:

```
Error: No such command 'migrate'
```

**Solution**: You're running an older version of SBKube. Update to v0.6.0+:

```bash
# Using uv
uv pip install --upgrade sbkube

# Using pip
pip install --upgrade sbkube

# Verify version
sbkube --version  # Should show 0.5.0 or higher
```

______________________________________________________________________

### Issue: OCI Registry Charts

**Before (v0.2.x)**:

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
    chart: browserless/browserless-chrome  # Same format as HTTP registries
```

**sources.yaml**:

```yaml
helm_sources:
  browserless:
    type: oci
    url: oci://tccr.io/truecharts
```

______________________________________________________________________

### Issue: Multiple Apps with Same Chart

**Before**:

```yaml
apps:
  redis-cache:
    repo: bitnami
    chart: redis
  redis-queue:
    repo: bitnami
    chart: redis
```

**After**:

```yaml
apps:
  redis-cache:
    chart: bitnami/redis  # ✅ Same repo/chart, different app names
  redis-queue:
    chart: bitnami/redis  # ✅ This is fine
```

No issues here - SBKube distinguishes apps by their key (`redis-cache`, `redis-queue`), not by chart name.

______________________________________________________________________

## Need Help?

- **Documentation**: [docs/](../)
- **Examples**: [examples/](../../examples/)
- **Issues**: [GitHub Issues](https://github.com/ScriptonBasestar-io/sb-kube-app-manager/issues)
- **Changelog**: [CHANGELOG.md](../../CHANGELOG.md)

______________________________________________________________________

**Last Updated**: 2025-10-31 **Target Version**: v0.6.0+
