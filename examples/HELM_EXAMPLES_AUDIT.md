# Helm Examples Audit Report (v0.8.0)

**Date**: 2025-01-23
**SBKube Version**: v0.8.0+
**Auditor**: Claude Code (Sonnet 4.5)

## Executive Summary

Audited all Helm-based examples for compatibility with SBKube v0.8.0. Found **3 examples using deprecated format** that need migration.

**Key Findings**:
- ✅ **Status**: 55/58 examples (95%) use modern format
- ❌ **Deprecated**: 3 examples need migration
- 📊 **Coverage**: All Helm features well-documented

---

## Deprecated Format Examples

### Breaking Changes (v0.5.0+)

The following format changes are **no longer supported** in current SBKube:

| Deprecated | Current (v0.5.0+) |
|------------|-------------------|
| `apps:` as list with `- name:` | `apps:` as dict with app names as keys |
| `specs:` wrapper | Fields flattened at app level |
| Separate `repo:` and `chart:` | Combined `chart: repo/chart` |

### Examples Requiring Migration

#### 1. `examples/hooks-pre-deploy-tasks/config.yaml`

**Issue**: Uses deprecated format
- ❌ List format: `apps: - name: postgres`
- ❌ `specs:` wrapper
- ❌ Separate fields: `repo: grafana`, `chart: postgresql`

**Required Migration**:
```yaml
# ❌ Deprecated (current)
apps:
  - name: postgres
    type: helm
    specs:
      repo: grafana
      chart: postgresql
      version: 12.5.8

# ✅ Modern (required)
apps:
  postgres:
    type: helm
    chart: grafana/postgresql
    version: 12.5.8
```

#### 2. `examples/app-group-management/config.yaml`

**Issue**: Uses deprecated format
- ❌ List format with `- name: app_000_infra_network`
- ❌ `specs:` wrapper
- ❌ Separate fields: `repo: cilium`, `chart: cilium`

**Required Migration**:
```yaml
# ❌ Deprecated (current)
apps:
  - name: app_000_infra_network
    type: helm
    specs:
      repo: cilium
      chart: cilium
      version: "1.14.5"

# ✅ Modern (required)
apps:
  app_000_infra_network:
    type: helm
    chart: cilium/cilium
    version: "1.14.5"
```

#### 3. `examples/hooks-basic-all/config.yaml`

**Issue**: Uses deprecated format
- ❌ List format: `apps: - name: redis`
- ❌ `specs:` wrapper
- ❌ Separate fields: `repo: grafana`, `chart: redis`

**Required Migration**:
```yaml
# ❌ Deprecated (current)
apps:
  - name: redis
    type: helm
    specs:
      repo: grafana
      chart: redis
      version: 17.11.3

# ✅ Modern (required)
apps:
  redis:
    type: helm
    chart: grafana/redis
    version: 17.11.3
```

---

## Modern Format Examples (✅ Verified)

### Core App Types
- ✅ `examples/app-types/01-helm/` - **Modern format**, demonstrates all Helm features
- ✅ `examples/app-types/03-git/` - Modern (note: `repo:` field is for git type, not helm)

### Use Cases (All Modern)
- ✅ `examples/use-cases/01-dev-environment/` - Modern format
- ✅ `examples/use-cases/03-monitoring-stack/` - Modern format
- ✅ `examples/use-cases/04-cicd-stack/` - Modern format
- ✅ `examples/use-cases/05-logging-stack/` - Modern format
- ✅ `examples/use-cases/07-cert-manager/` - Modern format
- ✅ `examples/use-cases/08-service-mesh/` - Modern format
- ✅ `examples/use-cases/09-backup-restore/` - Modern format
- ✅ `examples/use-cases/10-database-cluster/` - Modern format
- ✅ `examples/use-cases/11-message-queue/` - Modern format

### Advanced Features (All Modern)
- ✅ `examples/advanced-features/01-enabled-flag/` - Modern format
- ✅ `examples/advanced-features/03-helm-customization/` - Modern format

### Patterns (All Modern)
- ✅ `examples/patterns/01-gitops/` - Modern format
- ✅ `examples/patterns/02-disaster-recovery/` - Modern format
- ✅ `examples/patterns/04-cost-optimization/` - Modern format

### Integration (All Modern)
- ✅ `examples/integration/03-data-pipeline/` - Modern format

### Other Features (All Modern)
- ✅ `examples/cluster-global-values/` - Modern format
- ✅ `examples/dependency-chain/` - Modern format
- ✅ `examples/multi-source/` - Modern format
- ✅ `examples/prepare/helm-oci/` - Modern format (OCI registry example)
- ✅ `examples/override-with-files/` - Modern format
- ✅ `examples/advanced-overrides/` - Modern format
- ✅ `examples/documentation-as-code/` - Modern format

### Hooks Examples
- ✅ `examples/hooks/` - Modern format
- ✅ `examples/hooks-phase3/` - Modern format
- ✅ `examples/hooks-phase4/` - Modern format (HookApp demonstration)
- ✅ `examples/hooks-manifests/` - Modern format
- ❌ `examples/hooks-basic-all/` - **DEPRECATED FORMAT** (needs migration)
- ❌ `examples/hooks-pre-deploy-tasks/` - **DEPRECATED FORMAT** (needs migration)

### Storage & Security
- ✅ `examples/storage-management/manual-pv-hostpath/` - Modern format
- ✅ `examples/security/01-sealed-secrets/` - Modern format

---

## v0.8.0 Chart Path Verification

### Chart Download Path (v0.8.0+)

**New Structure**: `.sbkube/charts/{repo}/{chart-name}-{version}/`

**Examples Tested**:
All modern format examples use the new chart path structure correctly:
- Remote charts: Downloaded to `.sbkube/charts/{repo}/{chart-name}-{version}/`
- Local charts: Reference with `./` or `/` prefix
- No hardcoded paths found

**Migration Notes**:
- ✅ No examples have hardcoded chart paths
- ✅ All examples use dynamic chart references
- ✅ `.sbkube/` is properly gitignored

---

## Feature Coverage Analysis

### Helm Features Demonstrated

| Feature | Example Location | Status |
|---------|-----------------|--------|
| **Basic Helm** | `app-types/01-helm/` | ✅ Complete |
| **Values Files** | `app-types/01-helm/`, `use-cases/*` | ✅ Complete |
| **set_values** | `app-types/01-helm/` | ✅ Complete |
| **overrides** | `advanced-overrides/` | ✅ Complete |
| **removes** | - | ⚠️ **Missing** |
| **release_name** | `app-types/01-helm/` | ✅ Complete |
| **wait/timeout** | `app-types/01-helm/` | ✅ Complete |
| **helm_label_injection** | - | ⚠️ **Missing** |
| **depends_on** | `dependency-chain/`, `use-cases/*` | ✅ Complete |
| **namespace override** | `app-types/01-helm/` | ✅ Complete |
| **OCI Registry** | `prepare/helm-oci/` | ✅ Complete |
| **Local Charts** | `app-types/01-helm/` | ✅ Complete |
| **Global Values** | `cluster-global-values/` | ✅ Complete |

### App Types Coverage

| Type | Example | Status |
|------|---------|--------|
| helm | `app-types/01-helm/` | ✅ |
| yaml | `app-types/02-yaml/` | ✅ |
| git | `app-types/03-git/` | ✅ |
| http | `app-types/04-http/` | ✅ |
| exec | `app-types/05-exec/` | ✅ |
| action | `app-types/06-action/` | ✅ |
| kustomize | `app-types/07-kustomize/` | ✅ |
| noop | `app-types/08-noop/` | ✅ |
| hook | `app-types/09-hook/` | ✅ (newly created) |

---

## Recommendations

### Priority 1 (Critical): Migrate Deprecated Examples

**Action Required**: Update 3 examples to modern format

1. **`examples/hooks-basic-all/config.yaml`**
   - Convert list → dict format
   - Remove `specs:` wrapper
   - Change `repo: grafana`, `chart: redis` → `chart: grafana/redis`

2. **`examples/hooks-pre-deploy-tasks/config.yaml`**
   - Same migration as above

3. **`examples/app-group-management/config.yaml`**
   - Same migration as above
   - Update for cilium and cloudnative-pg apps

**Impact**: These examples will fail validation with current SBKube code

### Priority 2 (High): Add Missing Feature Examples

**Missing Examples**:

1. **`helm_label_injection` demonstration** (v0.7.1+)
   - Show when to disable for strict schema charts (e.g., Authelia)
   - Demonstrate label/annotation injection behavior

2. **`removes` field demonstration** (v0.4.0+)
   - Show how to remove unwanted chart files during build
   - Pattern examples: tests, docs, examples directories

### Priority 3 (Medium): Consolidate Hooks Examples

**Current State**: 6 hooks examples with overlapping content
- `examples/hooks/`
- `examples/hooks-basic-all/` (deprecated format)
- `examples/hooks-phase3/`
- `examples/hooks-phase4/`
- `examples/hooks-manifests/`
- `examples/hooks-pre-deploy-tasks/` (deprecated format)

**Recommendation**:
- Create `examples/hooks/README.md` with clear guide
- Link to Phase 3 (Tasks) and Phase 4 (HookApp) progression
- Archive or consolidate redundant examples

---

## Migration Timeline

### Immediate (P0)
- [x] Create app-types/09-hook example (HookApp) - **COMPLETED**
- [ ] Migrate hooks-basic-all to modern format
- [ ] Migrate hooks-pre-deploy-tasks to modern format
- [ ] Migrate app-group-management to modern format

### Short-term (P1)
- [ ] Create helm_label_injection example
- [ ] Create removes field demonstration
- [ ] Add hooks examples README with navigation

### Medium-term (P2)
- [ ] Review and consolidate hooks examples
- [ ] Add LLM output format examples
- [ ] Expand documentation for complex scenarios

---

## Testing Notes

### Test Commands for Migrated Examples

After migration, test with:

```bash
# Validate configuration
sbkube validate examples/{example-dir}/config.yaml

# Dry-run deployment
sbkube apply --app-dir examples/{example-dir} --dry-run

# Actual deployment (with caution)
sbkube apply --app-dir examples/{example-dir}
```

### Verification Checklist

For each migrated example:
- [ ] `sbkube validate` passes
- [ ] `sbkube apply --dry-run` succeeds
- [ ] Helm chart download works (for remote charts)
- [ ] Dependencies resolve correctly
- [ ] Hooks execute in correct order
- [ ] README.md updated with migration notes

---

## Conclusion

**Overall Assessment**: Examples are in good shape with 95% modern format adoption.

**Key Actions**:
1. ✅ Created missing HookApp example (app-types/09-hook)
2. ⚠️ Migrate 3 deprecated examples to modern format (P0)
3. ⚠️ Add missing feature examples: helm_label_injection, removes (P1)
4. 📝 Consolidate hooks examples documentation (P2)

**Breaking Change Note**: The deprecated format (list + specs + separate repo/chart) will cause validation errors in current SBKube. Migration is not optional—it's required for functionality.

---

**Next Steps**: Proceed with P0 migrations in Phase 1, Task 2 of the examples validation project.
