# SBKube v0.8.0 Release Notes

> **Release Date**: 2025-11-13
> **Type**: Minor Release with Breaking Changes
> **Status**: Released

---

## 🎯 TL;DR

**v0.8.0 introduces two major improvements**:

1. **Chart Path Collision Prevention** - New versioned chart storage structure
2. **PV/PVC Validation** - Detect missing PVs before deployment

**⚠️ Breaking Change**: Chart directory structure changed - migration required.

---

## 🚨 Breaking Changes

### Chart Path Structure Migration

**What Changed**:
```
Before (v0.7.x):
.sbkube/charts/redis/           # ❌ Collision risk
.sbkube/charts/grafana/         # ❌ No version tracking

After (v0.8.0):
.sbkube/charts/grafana/loki-18.0.0/         # ✅ No collision
.sbkube/charts/my-company/redis-1.0.0/       # ✅ Different repo
.sbkube/charts/grafana/loki-19.0.0/         # ✅ Different version
.sbkube/charts/grafana/grafana-latest/       # ✅ Version tracked
```

**Migration Steps**:
```bash
# 1. Remove old charts
rm -rf .sbkube/charts

# 2. Re-download with new structure
sbkube prepare --force
```

**Why This Change**:
- **Problem 1**: Charts from different repos with same name collided (e.g., `grafana/loki` vs `my-company/redis`)
- **Problem 2**: Different versions of same chart couldn't coexist (e.g., `redis:18.0.0` vs `redis:19.0.0`)
- **Solution**: New path structure includes repo and version: `{repo}/{chart-name}-{version}/`

**Auto-Detection**: v0.8.0 automatically detects legacy paths and provides migration guidance.

---

## ✨ New Features

### 1. Chart Path Collision Prevention

**Files Modified**:
- [sbkube/models/config_model.py](sbkube/models/config_model.py): Added `HelmApp.get_chart_path()`, `get_version_or_default()`
- [sbkube/commands/prepare.py](sbkube/commands/prepare.py): New path structure for OCI + Helm charts
- [sbkube/commands/build.py](sbkube/commands/build.py): Legacy path detection with migration guide
- [sbkube/commands/deploy.py](sbkube/commands/deploy.py): Updated to use new paths
- [sbkube/commands/template.py](sbkube/commands/template.py): Updated to use new paths

**Benefits**:
- ✅ Multiple repos can have charts with same name
- ✅ Multiple versions of same chart can coexist
- ✅ Automatic legacy detection with clear migration path

**Technical Details**: See [CHART_PATH_REFACTORING_v080.md](10-modules/sbkube/CHART_PATH_REFACTORING_v080.md)

---

### 2. PV/PVC Validation for Manual Provisioning

**Problem Solved**:
```bash
# Before v0.8.0: Silent failure
$ sbkube apply
✅ Deployment succeeded
$ kubectl get pvc
NAME              STATUS    VOLUME   CAPACITY
postgresql-data   Pending            # ❌ Stuck, no guidance

# After v0.8.0: Early detection
$ sbkube validate
❌ 스토리지 검증 실패:
  ✗ postgresql: postgresql-hostpath (8Gi)

💡 PV 생성 방법:
  1. 수동 생성: kubectl apply -f pv.yaml
  2. Dynamic Provisioner 설치: local-path-provisioner
  3. 검증 건너뛰기: sbkube validate --skip-storage-check
```

**Features**:
- **Automatic Detection**: Identifies apps using `kubernetes.io/no-provisioner` StorageClass
- **Cluster Validation**: Checks if required PVs exist in cluster
- **Intelligent Matching**: Matches PVs by StorageClass, size, and availability
- **Flexible Modes**: Skip validation, strict mode, or default warning
- **Graceful Degradation**: Skips validation if cluster unavailable

**New CLI Options**:
```bash
# Standard validation (includes storage check)
sbkube validate

# Skip storage validation
sbkube validate --skip-storage-check

# Strict mode (fail on missing PVs)
sbkube validate --strict-storage-check

# Custom kubeconfig
sbkube validate --kubeconfig ~/.kube/production
```

**Files Added**:
- [sbkube/validators/storage_validators.py](sbkube/validators/storage_validators.py): Core validation logic
- [tests/unit/validators/test_storage_validators.py](tests/unit/validators/test_storage_validators.py): Unit tests
- [docs/05-best-practices/storage-management.md](docs/05-best-practices/storage-management.md): Best practices guide
- [docs/07-troubleshooting/storage-issues.md](docs/07-troubleshooting/storage-issues.md): Troubleshooting guide
- [examples/storage-management/manual-pv-hostpath/](examples/storage-management/manual-pv-hostpath/): Working example

**Files Modified**:
- [sbkube/commands/validate.py](sbkube/commands/validate.py): Integrated storage validation

**Limitations (v0.8.0)**:
- Cannot parse `HelmApp.values` (list of file paths, not inline dict)
- Future enhancement (v0.9.0): Load values files or support inline values in config

**Documentation**:
- [Storage Management Best Practices](05-best-practices/storage-management.md)
- [Storage Troubleshooting Guide](07-troubleshooting/storage-issues.md)
- [Example: Manual PV with hostPath](../examples/storage-management/manual-pv-hostpath/)

---

## 🐛 Bug Fixes

No bug fixes in this release (feature-focused release).

---

## 📚 Documentation Updates

### New Documentation

1. **[storage-management.md](05-best-practices/storage-management.md)**
   - Manual PV creation guide
   - Dynamic provisioner recommendations
   - Common storage patterns
   - Troubleshooting checklist

2. **[storage-issues.md](07-troubleshooting/storage-issues.md)**
   - 5 common storage issues with solutions
   - Quick diagnosis checklist
   - Step-by-step troubleshooting

3. **[CHART_PATH_REFACTORING_v080.md](10-modules/sbkube/CHART_PATH_REFACTORING_v080.md)**
   - Technical details of path structure change
   - Migration guide
   - Implementation details

### Updated Documentation

1. **[directory-structure.md](05-best-practices/directory-structure.md)**
   - Added v0.8.0 migration guide
   - Documented new chart path structure

2. **[CHANGELOG.md](../CHANGELOG.md)**
   - Comprehensive v0.8.0 change documentation

---

## 🧪 Testing

**New Tests**:
- 5 unit tests for storage validation (all passing)
- Mocked kubectl integration tests
- Size comparison logic validation

**Test Coverage**:
- Storage validators: 40% coverage (focused on critical paths)
- All existing tests continue to pass

---

## 🔄 Migration Guide

### For Existing Users

**Step 1: Backup** (optional, recommended)
```bash
cp -r .sbkube/charts .sbkube/charts.backup
```

**Step 2: Remove Old Charts**
```bash
rm -rf .sbkube/charts
```

**Step 3: Re-download with New Structure**
```bash
sbkube prepare --force
```

**Step 4: Verify**
```bash
ls -R .sbkube/charts/
# Expected: charts/{repo}/{chart-name}-{version}/
```

**Step 5: Deploy**
```bash
sbkube apply
```

### Rollback (If Needed)

If you need to rollback to v0.7.2:
```bash
# 1. Downgrade SBKube
uv add sbkube==0.7.2

# 2. Remove new charts
rm -rf .sbkube/charts

# 3. Re-download with old structure
sbkube prepare
```

---

## 🚀 Upgrade Instructions

### From v0.7.x

```bash
# 1. Upgrade SBKube
uv add sbkube==0.8.0

# 2. Follow migration guide above
rm -rf .sbkube/charts
sbkube prepare --force

# 3. Validate (includes new storage check)
sbkube validate

# 4. Deploy
sbkube apply
```

### From v0.6.x or Earlier

Upgrade to v0.7.2 first, then follow instructions above.

---

## 🔮 What's Next (v0.9.0)

Planned features for next release:

1. **Hook Context Variables**
   - Jinja2 template rendering in hooks
   - Built-in variables: `app.name`, `app.namespace`, `app.values.*`
   - Environment variable lookup

2. **Infra Command** (Optional)
   - `sbkube infra analyze`: Analyze PV requirements
   - `sbkube infra provision`: Auto-create PVs
   - `sbkube infra cleanup`: Remove unused PVs

3. **Enhanced Storage Validation**
   - Load and parse values files
   - Support inline values in config
   - Multi-app PV dependency detection

---

## 📊 Statistics

**Lines of Code**:
- Added: ~2,000 lines (storage validation + docs)
- Modified: ~100 lines (chart path changes)

**Commits**:
- 3 commits in v0.8.0 development cycle

**Documentation**:
- 3 new documents (~300KB)
- 2 updated documents

**Tests**:
- 5 new unit tests
- All existing tests passing

---

## 🙏 Acknowledgments

**Contributors**:
- Claude Sonnet 4.5 (AI pair programming)
- archmagece (project lead)

**Special Thanks**:
- Users who reported chart collision issues
- Community feedback on storage troubleshooting

---

## 📞 Support

**Found an Issue?**
- Report bugs: [GitHub Issues](https://github.com/archmagece/sb-kube-app-manager/issues)

**Need Help?**
- Read docs: [Documentation](../docs/)
- See examples: [Examples](../examples/)
- Check troubleshooting: [Troubleshooting Guide](07-troubleshooting/)

---

## 📝 Changelog

See [CHANGELOG.md](../CHANGELOG.md) for complete version history.

---

**Released**: 2025-11-13
**Version**: 0.8.0
**Previous**: 0.7.2
