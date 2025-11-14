# Storage Management Best Practices

> **Version**: v0.8.0 **Last Updated**: 2025-01-11 **Audience**: DevOps Engineers, Cluster Administrators

## TL;DR

- **Problem**: `kubernetes.io/no-provisioner` StorageClass requires manual PV creation
- **Solution**: Use `sbkube validate` to check PV requirements before deployment
- **Best Practice**: Use dynamic provisioners (local-path, NFS) for production

______________________________________________________________________

## 📋 Table of Contents

1. [Understanding StorageClass Types](#understanding-storageclass-types)
1. [PV Validation Workflow](#pv-validation-workflow)
1. [Manual PV Creation](#manual-pv-creation)
1. [Dynamic Provisioners (Recommended)](#dynamic-provisioners-recommended)
1. [Common Patterns](#common-patterns)
1. [Troubleshooting](#troubleshooting)

______________________________________________________________________

## Understanding StorageClass Types

### Dynamic Provisioning (Recommended)

Kubernetes automatically creates PVs when PVCs are created.

**Examples**:

- `rancher.io/local-path` (Rancher Local Path Provisioner)
- `nfs-client` (NFS Subdir External Provisioner)
- `kubernetes.io/aws-ebs` (AWS EBS)
- `kubernetes.io/gce-pd` (Google Persistent Disk)

**Benefits**:

- ✅ Fully automatic - no manual PV creation
- ✅ Production-ready
- ✅ Supports dynamic resizing

### Manual Provisioning (No-Provisioner)

Requires manual PV creation before deploying apps.

**Examples**:

- `kubernetes.io/no-provisioner` with hostPath
- `kubernetes.io/no-provisioner` with local volumes

**Use Cases**:

- Development/testing environments
- Single-node clusters (k3s, minikube)
- Specific hardware requirements (SSD, NVMe)

**Challenges**:

- ❌ Manual PV creation required
- ❌ PVC stays Pending without PV
- ❌ No automatic cleanup

______________________________________________________________________

## PV Validation Workflow

### Step 1: Check PV Requirements

```bash
# Validate all apps (including storage check)
sbkube validate

# Output example:
# ✅ Config 검증 통과
# ✅ Sources 검증 통과
# ✅ 의존성 검증 통과
# ❌ 스토리지 검증 실패:
#   ✗ postgresql: postgresql-hostpath (8Gi)
#
# 💡 PV 생성 방법:
#   1. 수동 생성: kubectl apply -f pv.yaml
#   2. Dynamic Provisioner 설치: local-path-provisioner, nfs-provisioner
#   3. 검증 건너뛰기: sbkube validate --skip-storage-check
```

### Step 2: Create Required PVs

See [Manual PV Creation](#manual-pv-creation) section.

### Step 3: Deploy Apps

```bash
sbkube apply
```

______________________________________________________________________

## Manual PV Creation

### Example: hostPath PV for PostgreSQL

**PV Manifest** (`pv-postgresql.yaml`):

```yaml
apiVersion: v1
kind: PersistentVolume
metadata:
  name: postgresql-pv
  labels:
    type: local
    app: postgresql
spec:
  storageClassName: postgresql-hostpath
  capacity:
    storage: 8Gi
  accessModes:
    - ReadWriteOnce
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
            - node1  # Change to your node name
```

**Create PV**:

```bash
# Create PV
kubectl apply -f pv-postgresql.yaml

# Verify PV
kubectl get pv postgresql-pv

# Expected output:
# NAME            CAPACITY   ACCESS MODES   RECLAIM POLICY   STATUS      STORAGECLASS
# postgresql-pv   8Gi        RWO            Retain           Available   postgresql-hostpath
```

**App Configuration** (`config.yaml`):

```yaml
namespace: database
apps:
  postgresql:
    type: helm
    chart: prometheus-community/kube-state-metrics
    version: 13.0.0
    values:
      persistence:
        enabled: true
        storageClass: postgresql-hostpath
        size: 8Gi
```

### Example: Multiple PVs

```bash
# Create PVs for multiple apps
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
  hostPath:
    path: /mnt/data/postgresql
    type: DirectoryOrCreate
---
apiVersion: v1
kind: PersistentVolume
metadata:
  name: redis-pv
spec:
  storageClassName: redis-hostpath
  capacity:
    storage: 2Gi
  accessModes:
    - ReadWriteOnce
  hostPath:
    path: /mnt/data/redis
    type: DirectoryOrCreate
EOF
```

______________________________________________________________________

## Dynamic Provisioners (Recommended)

### Option 1: Rancher Local Path Provisioner

**Installation**:

```bash
kubectl apply -f https://raw.githubusercontent.com/rancher/local-path-provisioner/v0.0.24/deploy/local-path-storage.yaml
```

**Set as Default**:

```bash
kubectl patch storageclass local-path -p '{"metadata": {"annotations":{"storageclass.kubernetes.io/is-default-class":"true"}}}'
```

**App Configuration**:

```yaml
namespace: database
apps:
  postgresql:
    type: helm
    chart: prometheus-community/kube-state-metrics
    version: 13.0.0
    values:
      persistence:
        enabled: true
        storageClass: local-path  # ✅ No manual PV needed
        size: 8Gi
```

### Option 2: NFS Subdir External Provisioner

**Installation (Helm)**:

```bash
helm repo add nfs-subdir-external-provisioner \
  https://kubernetes-sigs.github.io/nfs-subdir-external-provisioner/

helm install nfs-subdir-external-provisioner \
  nfs-subdir-external-provisioner/nfs-subdir-external-provisioner \
  --set nfs.server=nfs-server.example.com \
  --set nfs.path=/exported/path
```

**App Configuration**:

```yaml
namespace: database
apps:
  postgresql:
    type: helm
    chart: prometheus-community/kube-state-metrics
    version: 13.0.0
    values:
      persistence:
        enabled: true
        storageClass: nfs-client  # ✅ No manual PV needed
        size: 8Gi
```

______________________________________________________________________

## Common Patterns

### Pattern 1: Development with hostPath

**Use Case**: Single-node k3s cluster for development

**Solution**: Manual PV creation with validation skip

```bash
# Create PVs manually
kubectl apply -f pvs/

# Skip storage validation (PVs already created)
sbkube validate --skip-storage-check

# Deploy
sbkube apply
```

### Pattern 2: Production with Dynamic Provisioner

**Use Case**: Multi-node production cluster

**Solution**: Install dynamic provisioner

```bash
# Install local-path-provisioner
kubectl apply -f https://raw.githubusercontent.com/rancher/local-path-provisioner/v0.0.24/deploy/local-path-storage.yaml

# Validate (should pass)
sbkube validate

# Deploy
sbkube apply
```

### Pattern 3: Mixed Storage Classes

**Use Case**: Some apps with dynamic provisioning, others with manual PVs

**Configuration**:

```yaml
namespace: database
apps:
  postgresql:
    type: helm
    chart: prometheus-community/kube-state-metrics
    values:
      persistence:
        storageClass: local-path  # ✅ Dynamic

  redis:
    type: helm
    chart: grafana/loki
    values:
      master:
        persistence:
          storageClass: redis-hostpath  # ⚠️ Manual PV required
```

**Workflow**:

```bash
# 1. Create manual PVs
kubectl apply -f pv-redis.yaml

# 2. Validate
sbkube validate
# Output: ✅ All PVs exist

# 3. Deploy
sbkube apply
```

______________________________________________________________________

## Troubleshooting

### Issue 1: PVC Stuck in Pending

**Symptom**:

```bash
$ kubectl get pvc
NAME                STATUS    VOLUME   CAPACITY
postgresql-data     Pending
```

**Diagnosis**:

```bash
# Check PVC events
kubectl describe pvc postgresql-data

# Look for:
# Events:
#   Type     Reason              Message
#   ----     ------              -------
#   Warning  ProvisioningFailed  no volume plugin matched
```

**Solution**:

See [docs/07-troubleshooting/storage-issues.md](../07-troubleshooting/storage-issues.md)

### Issue 2: Validation Detects Missing PV

**Symptom**:

```bash
$ sbkube validate
❌ 1개의 PV가 없습니다:
  ✗ postgresql: postgresql-hostpath (8Gi)
```

**Solution A**: Create PV manually

```bash
kubectl apply -f pv-postgresql.yaml
sbkube validate  # Should pass now
```

**Solution B**: Use dynamic provisioner

```bash
# Install local-path-provisioner
kubectl apply -f https://raw.githubusercontent.com/rancher/local-path-provisioner/v0.0.24/deploy/local-path-storage.yaml

# Update config.yaml to use local-path
# Then validate again
```

**Solution C**: Skip validation (if PV will be created later)

```bash
sbkube validate --skip-storage-check
```

### Issue 3: Wrong Node Selected

**Symptom**: PV created but Pod can't mount (wrong node)

**Solution**: Add node affinity to PV

```yaml
apiVersion: v1
kind: PersistentVolume
metadata:
  name: postgresql-pv
spec:
  # ...
  nodeAffinity:
    required:
      nodeSelectorTerms:
      - matchExpressions:
        - key: kubernetes.io/hostname
          operator: In
          values:
            - correct-node-name  # ✅ Specify correct node
```

______________________________________________________________________

## Best Practices Summary

1. **Production**: Always use dynamic provisioners
1. **Development**: Manual PVs acceptable, but document clearly
1. **Validation**: Run `sbkube validate` before every deployment
1. **Node Affinity**: Always specify for hostPath PVs
1. **Reclaim Policy**: Use `Retain` for manual PVs (avoid data loss)
1. **Size Planning**: PV size must be ≥ PVC size
1. **Access Modes**: Match PV and PVC access modes

______________________________________________________________________

## Related Documentation

- [Troubleshooting: Storage Issues](../07-troubleshooting/storage-issues.md)
- [Examples: Storage Management](../../examples/storage-management/)
- [Config Schema: Persistence](../03-configuration/config-schema.md)

______________________________________________________________________

## Change History

### v1.0 (2025-01-11)

- Initial documentation for v0.8.0 PV validation feature
- Added manual PV creation guide
- Added dynamic provisioner recommendations
- Added common patterns and troubleshooting
