______________________________________________________________________

## type: User Guide audience: End User, Developer topics: [migration, upgrade, breaking-changes] llm_priority: medium last_updated: 2025-01-04

# SBKube Migration Guide

Comprehensive guide for migrating SBKube configuration across different versions.

______________________________________________________________________

## TL;DR

- **Current Version**: v0.6.1
- **Major Changes**: v0.5 (working directory), v0.6 (state management)
- **Migration Tool**: `sbkube validate` checks compatibility
- **Related**: [Config Schema](config-schema.md)

______________________________________________________________________

## Table of Contents

- [Overview](#overview)
- [General Migration Process](#general-migration-process)
- [Version-Specific Guides](#version-specific-guides)
  - [Migration to v0.5.0](#migration-to-v050)
  - [Migration to v0.6.0](#migration-to-v060)
  - [Migration to v0.6.1](#migration-to-v061)
- [Breaking Changes Summary](#breaking-changes-summary)
- [FAQ](#faq)

______________________________________________________________________

## Overview

SBKube follows semantic versioning with clear upgrade paths between releases. Each major or minor version may introduce
breaking changes that require configuration migration.

### Version History

| Version | Release Date | Major Changes | |---------|-------------|---------------| | v0.6.1 | 2025-01-03 | LLM output
integration | | v0.6.0 | 2024-12-15 | State management, helm format | | v0.5.0 | 2024-11-01 | Working directory
consolidation | | v0.4.x | 2024-09-01 | Initial stable release |

______________________________________________________________________

## General Migration Process

### Pre-Migration Checklist

1. **Backup Configuration**:

   ```bash
   cp -r config/ config.backup/
   cp sources.yaml sources.yaml.backup
   ```

1. **Check Current Version**:

   ```bash
   sbkube --version
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
sbkube --version
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
    chart: bitnami/redis    # Same chart
  redis-queue:
    chart: bitnami/redis    # Different app name
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
sbkube --version  # Should show 0.6.0+
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
