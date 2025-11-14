# Migration Guide: v0.7.x → v0.8.0

> **Quick Start**: 5-minute migration guide for existing SBKube users

---

## 🎯 Quick Migration (TL;DR)

```bash
# Step 1: Upgrade
uv add sbkube==0.8.0

# Step 2: Migrate charts
rm -rf .sbkube/charts
sbkube prepare --force

# Step 3: Validate (new!)
sbkube validate

# Step 4: Deploy
sbkube apply

# Done! ✅
```

---

## ⚠️ Breaking Changes

### Chart Directory Structure Changed

**Before (v0.7.x)**:
```
.sbkube/charts/redis/
.sbkube/charts/grafana/
```

**After (v0.8.0)**:
```
.sbkube/charts/grafana/loki-18.0.0/
.sbkube/charts/grafana/grafana-latest/
```

**Why**: Prevents chart name collisions between different repos and versions.

---

## 📋 Step-by-Step Migration

### Step 1: Backup (Optional but Recommended)

```bash
# Backup current charts
cp -r .sbkube/charts .sbkube/charts.backup

# Backup current config
cp config.yaml config.yaml.backup
```

### Step 2: Upgrade SBKube

```bash
# If using uv (recommended)
uv add sbkube==0.8.0

# If using pip
pip install sbkube==0.8.0

# Verify version
sbkube version
# Expected: 0.8.0
```

### Step 3: Remove Old Charts

```bash
# Remove old chart structure
rm -rf .sbkube/charts

# Verify removal
ls -la .sbkube/
# charts/ should not exist
```

### Step 4: Re-download Charts

```bash
# Download charts with new structure
sbkube prepare --force

# Verify new structure
ls -R .sbkube/charts/
# Expected: charts/{repo}/{chart-name}-{version}/
```

### Step 5: Validate (NEW in v0.8.0)

```bash
# Run validation (includes new storage check)
sbkube validate

# If you see PV warnings:
# Option A: Create missing PVs (see Step 6)
# Option B: Skip storage check: sbkube validate --skip-storage-check
# Option C: Install dynamic provisioner (recommended)
```

### Step 6: Handle PV Requirements (If Needed)

If validation shows missing PVs:

```bash
# Check what's missing
sbkube validate

# Example output:
# ❌ 스토리지 검증 실패:
#   ✗ postgresql: postgresql-hostpath (8Gi)

# Option A: Create PV manually
kubectl apply -f - <<EOF
apiVersion: v1
kind: PersistentVolume
metadata:
  name: postgresql-pv
spec:
  storageClassName: postgresql-hostpath
  capacity:
    storage: 8Gi
  accessModes:
    - ReadWriteOnce
  persistentVolumeReclaimPolicy: Retain
  hostPath:
    path: /mnt/data/postgresql
    type: DirectoryOrCreate
  nodeAffinity:
    required:
      nodeSelectorTerms:
      - matchExpressions:
        - key: kubernetes.io/hostname
          operator: In
          values:
            - $(kubectl get nodes -o jsonpath='{.items[0].metadata.name}')
EOF

# Option B: Install local-path-provisioner (recommended)
kubectl apply -f https://raw.githubusercontent.com/rancher/local-path-provisioner/v0.0.24/deploy/local-path-storage.yaml

# Update config.yaml to use local-path StorageClass
```

### Step 7: Deploy

```bash
# Deploy with new structure
sbkube apply

# Verify deployment
kubectl get pods
kubectl get pvc
```

---

## 🔍 Troubleshooting

### Issue 1: Legacy Path Warning

**Symptom**:
```
❌ Chart found at legacy path (v0.7.1): .sbkube/charts/redis
```

**Solution**:
```bash
rm -rf .sbkube/charts
sbkube prepare --force
```

### Issue 2: PVC Stuck in Pending

**Symptom**:
```bash
$ kubectl get pvc
NAME              STATUS    VOLUME   CAPACITY
postgresql-data   Pending
```

**Solution**: See [Storage Troubleshooting Guide](07-troubleshooting/storage-issues.md)

**Quick Fix**:
```bash
# Check what's needed
sbkube validate

# Create PV or install provisioner (see Step 6)
```

### Issue 3: Chart Not Found After Migration

**Symptom**:
```
Chart not found: .sbkube/charts/redis
```

**Solution**:
```bash
# Re-download charts
sbkube prepare --force

# Verify
ls -R .sbkube/charts/
```

---

## 🎓 What Changed in v0.8.0

### 1. Chart Path Structure

**Old**: `charts/{chart-name}/`
**New**: `charts/{repo}/{chart-name}-{version}/`

**Benefits**:
- ✅ Different repos can have same chart name
- ✅ Different versions can coexist
- ✅ Better organization

### 2. PV/PVC Validation (NEW)

**Feature**: Automatic PV requirement detection

**Commands**:
```bash
# Standard validation
sbkube validate

# Skip storage check
sbkube validate --skip-storage-check

# Strict mode (fail on missing PVs)
sbkube validate --strict-storage-check
```

**Documentation**:
- [Storage Management](05-best-practices/storage-management.md)
- [Storage Issues](07-troubleshooting/storage-issues.md)

---

## 📚 Additional Resources

### Documentation

- [Release Notes v0.8.0](RELEASE_v0.8.0.md)
- [Storage Management Best Practices](05-best-practices/storage-management.md)
- [Storage Troubleshooting Guide](07-troubleshooting/storage-issues.md)
- [Chart Path Refactoring Details](10-modules/sbkube/CHART_PATH_REFACTORING_v080.md)

### Examples

- [Manual PV with hostPath](../examples/storage-management/manual-pv-hostpath/)

### Support

- [GitHub Issues](https://github.com/archmagece/sb-kube-app-manager/issues)
- [Documentation Index](INDEX.md)

---

## ⏮️ Rollback (Emergency)

If you encounter critical issues:

```bash
# 1. Downgrade SBKube
uv add sbkube==0.7.2

# 2. Restore old charts (if backed up)
rm -rf .sbkube/charts
mv .sbkube/charts.backup .sbkube/charts

# 3. Restore old config (if needed)
mv config.yaml.backup config.yaml

# 4. Deploy with old version
sbkube apply

# 5. Report issue
# GitHub: https://github.com/archmagece/sb-kube-app-manager/issues
```

---

## ✅ Migration Checklist

Use this checklist to track your migration:

- [ ] Backup charts and config (optional)
- [ ] Upgrade to v0.8.0
- [ ] Remove old charts directory
- [ ] Re-download charts with `prepare --force`
- [ ] Run `sbkube validate` (new command)
- [ ] Create PVs or install provisioner (if needed)
- [ ] Deploy with `sbkube apply`
- [ ] Verify all pods running
- [ ] Verify all PVCs bound
- [ ] Test application functionality
- [ ] Remove backup (after successful migration)

---

## 🎉 Success!

After successful migration, you'll have:

- ✅ New chart structure preventing collisions
- ✅ PV validation preventing PVC Pending issues
- ✅ Better organized `.sbkube/` directory
- ✅ All features from v0.8.0

**Questions?** Check [Release Notes](RELEASE_v0.8.0.md) or [Documentation](INDEX.md)

---

**Last Updated**: 2025-01-11
**Applies To**: v0.7.x → v0.8.0
**Estimated Time**: 5-15 minutes
