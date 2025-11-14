# Troubleshooting: Storage Issues

> **Version**: v0.8.0 **Last Updated**: 2025-01-11

## TL;DR

Common storage issues and their solutions:

- **PVC Pending**: No matching PV or provisioner → Create PV or install provisioner
- **Validation Fails**: Missing PV detected → Create PV before deployment
- **Wrong Node**: Pod can't mount → Add node affinity to PV
- **Size Mismatch**: PV too small → Recreate PV with larger size

______________________________________________________________________

## Issue 1: PVC Stuck in Pending State

### Symptom

```bash
$ kubectl get pvc
NAME                STATUS    VOLUME   CAPACITY   ACCESS MODES   STORAGECLASS
postgresql-data     Pending                                       postgresql-hostpath
```

Pod cannot start due to unbound PVC:

```bash
$ kubectl get pods
NAME                    READY   STATUS    RESTARTS   AGE
postgresql-0            0/1     Pending   0          5m

$ kubectl describe pod postgresql-0
Events:
  Type     Reason            Age   From               Message
  ----     ------            ----  ----               -------
  Warning  FailedScheduling  3m    default-scheduler  persistentvolumeclaim "postgresql-data" not found
```

### Root Cause

**Cause 1**: StorageClass uses `kubernetes.io/no-provisioner` but no PV exists

```bash
$ kubectl get storageclass postgresql-hostpath -o yaml
apiVersion: storage.k8s.io/v1
kind: StorageClass
metadata:
  name: postgresql-hostpath
provisioner: kubernetes.io/no-provisioner  # ❌ No auto-provisioning
volumeBindingMode: WaitForFirstConsumer
```

**Cause 2**: PV exists but doesn't match PVC requirements

- Different StorageClass
- Insufficient capacity
- Incompatible access modes
- Wrong node (for hostPath/local PVs)

### Solution A: Create Manual PV

**1. Create PV manifest** (`pv-postgresql.yaml`):

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
            - node1  # ✅ Replace with actual node name
```

**2. Get correct node name**:

```bash
# List all nodes
kubectl get nodes

# Get node where PostgreSQL should run
kubectl get nodes -o custom-columns=NAME:.metadata.name
```

**3. Create PV**:

```bash
kubectl apply -f pv-postgresql.yaml
```

**4. Verify PV and PVC binding**:

```bash
# Check PV status
kubectl get pv postgresql-pv

# Expected output:
# NAME            CAPACITY   STATUS      CLAIM                      STORAGECLASS
# postgresql-pv   8Gi        Available   -                          postgresql-hostpath

# Wait for PVC to bind (may take a few seconds)
kubectl get pvc postgresql-data

# Expected output after binding:
# NAME              STATUS   VOLUME          CAPACITY   ACCESS MODES   STORAGECLASS
# postgresql-data   Bound    postgresql-pv   8Gi        RWO            postgresql-hostpath
```

**5. Verify Pod starts**:

```bash
kubectl get pods
# NAME             READY   STATUS    RESTARTS   AGE
# postgresql-0     1/1     Running   0          2m
```

### Solution B: Install Dynamic Provisioner (Recommended)

**1. Install Rancher Local Path Provisioner**:

```bash
kubectl apply -f https://raw.githubusercontent.com/rancher/local-path-provisioner/v0.0.24/deploy/local-path-storage.yaml
```

**2. Verify installation**:

```bash
kubectl get storageclass local-path

# Expected output:
# NAME         PROVISIONER             RECLAIMPOLICY   VOLUMEBINDINGMODE
# local-path   rancher.io/local-path   Delete          WaitForFirstConsumer
```

**3. Update app configuration** (`config.yaml`):

```yaml
namespace: database
apps:
  postgresql:
    type: helm
    chart: prometheus-community/kube-state-metrics
    values:
      persistence:
        enabled: true
        storageClass: local-path  # ✅ Changed from postgresql-hostpath
        size: 8Gi
```

**4. Redeploy**:

```bash
# Delete old PVC (if exists)
kubectl delete pvc postgresql-data

# Redeploy
sbkube apply
```

### Solution C: Skip Validation (Temporary)

If you know the PV will be created by external process:

```bash
sbkube validate --skip-storage-check
sbkube apply
```

______________________________________________________________________

## Issue 2: SBKube Validation Fails with Missing PV

### Symptom

```bash
$ sbkube validate

✅ Config 검증 통과
✅ Sources 검증 통과
✅ 의존성 검증 통과
❌ 스토리지 검증 실패:
  ✗ postgresql: postgresql-hostpath (8Gi)

💡 PV 생성 방법:
  1. 수동 생성: kubectl apply -f pv.yaml
  2. Dynamic Provisioner 설치: local-path-provisioner, nfs-provisioner
  3. 검증 건너뛰기: sbkube validate --skip-storage-check
```

### Root Cause

App requires PV with `kubernetes.io/no-provisioner` StorageClass, but PV doesn't exist in cluster.

### Solution A: Create PV Before Deployment

```bash
# 1. Create PV
kubectl apply -f pv-postgresql.yaml

# 2. Validate again
sbkube validate
# Output: ✅ 모든 필요한 PV 존재 확인 (1개)

# 3. Deploy
sbkube apply
```

### Solution B: Use Dynamic Provisioner

See [Solution B in Issue 1](#solution-b-install-dynamic-provisioner-recommended)

### Solution C: Strict Mode (Fail on Missing PV)

```bash
# Validation will fail and abort if PV missing
sbkube validate --strict-storage-check
```

______________________________________________________________________

## Issue 3: PV Exists but Pod Still Pending

### Symptom

```bash
$ kubectl get pv
NAME            CAPACITY   STATUS      CLAIM   STORAGECLASS
postgresql-pv   8Gi        Available   -       postgresql-hostpath

$ kubectl get pvc
NAME              STATUS    VOLUME   CAPACITY
postgresql-data   Pending

$ kubectl describe pvc postgresql-data
Events:
  Type     Reason         Age   From                         Message
  ----     ------         ----  ----                         -------
  Warning  VolumeMismatch  2m    persistentvolume-controller  Cannot bind to requested volume "postgresql-pv": no persistent volumes available
```

### Root Cause

**Cause 1**: StorageClass mismatch

```bash
# PV uses different StorageClass than PVC
$ kubectl get pv postgresql-pv -o jsonpath='{.spec.storageClassName}'
postgresql-hostpath

$ kubectl get pvc postgresql-data -o jsonpath='{.spec.storageClassName}'
postgresql-local  # ❌ Different!
```

**Cause 2**: Size mismatch (PV too small)

```bash
# PV: 8Gi
# PVC requests: 10Gi
# ❌ PV must be >= PVC size
```

**Cause 3**: Access mode incompatibility

```bash
# PV: ReadWriteOnce
# PVC: ReadWriteMany
# ❌ PV must support PVC's access mode
```

**Cause 4**: Node affinity mismatch (hostPath PVs)

```bash
# PV node affinity: node1
# Pod scheduled to: node2
# ❌ hostPath PV can only be used on specific node
```

### Solution

**1. Check StorageClass match**:

```bash
# PV StorageClass
kubectl get pv postgresql-pv -o jsonpath='{.spec.storageClassName}'

# PVC StorageClass
kubectl get pvc postgresql-data -o jsonpath='{.spec.storageClassName}'

# If different, recreate PV with correct StorageClass
```

**2. Check size**:

```bash
# PV size
kubectl get pv postgresql-pv -o jsonpath='{.spec.capacity.storage}'

# PVC size
kubectl get pvc postgresql-data -o jsonpath='{.spec.resources.requests.storage}'

# If PV < PVC, recreate PV with larger size
```

**3. Check access modes**:

```bash
# PV access modes
kubectl get pv postgresql-pv -o jsonpath='{.spec.accessModes}'

# PVC access modes
kubectl get pvc postgresql-data -o jsonpath='{.spec.accessModes}'

# If incompatible, recreate PV with correct access modes
```

**4. Check node affinity (hostPath only)**:

```bash
# Where is the PV located?
kubectl get pv postgresql-pv -o yaml | grep -A10 nodeAffinity

# Where is the Pod trying to run?
kubectl get pod postgresql-0 -o jsonpath='{.spec.nodeName}'

# If different nodes and PV uses hostPath, add correct node affinity
```

______________________________________________________________________

## Issue 4: Data Loss After PV Deletion

### Symptom

PV deleted and all data lost.

### Root Cause

Default reclaim policy is `Delete` for dynamic provisioners.

### Solution: Use Retain Policy

**For Manual PVs**:

```yaml
apiVersion: v1
kind: PersistentVolume
metadata:
  name: postgresql-pv
spec:
  persistentVolumeReclaimPolicy: Retain  # ✅ Keep data after PVC deletion
  storageClassName: postgresql-hostpath
  # ...
```

**For Dynamic Provisioners**:

```yaml
# In StorageClass
apiVersion: storage.k8s.io/v1
kind: StorageClass
metadata:
  name: local-path-retain
provisioner: rancher.io/local-path
reclaimPolicy: Retain  # ✅ Keep data after PVC deletion
volumeBindingMode: WaitForFirstConsumer
```

______________________________________________________________________

## Issue 5: Multiple PVCs, Some Pending

### Symptom

```bash
$ kubectl get pvc
NAME                STATUS    VOLUME          CAPACITY
postgresql-data     Bound     postgresql-pv   8Gi
redis-data          Pending
mysql-data          Pending
```

### Solution: Create All Required PVs

**Check what's missing**:

```bash
sbkube validate

# Output shows all missing PVs:
# ❌ 2개의 PV가 없습니다:
#   ✗ redis: redis-hostpath (2Gi)
#   ✗ mysql: mysql-hostpath (10Gi)
```

**Create all PVs at once**:

```bash
kubectl apply -f - <<EOF
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
  persistentVolumeReclaimPolicy: Retain
  hostPath:
    path: /mnt/data/redis
    type: DirectoryOrCreate
---
apiVersion: v1
kind: PersistentVolume
metadata:
  name: mysql-pv
spec:
  storageClassName: mysql-hostpath
  capacity:
    storage: 10Gi
  accessModes:
    - ReadWriteOnce
  persistentVolumeReclaimPolicy: Retain
  hostPath:
    path: /mnt/data/mysql
    type: DirectoryOrCreate
EOF
```

______________________________________________________________________

## Quick Diagnosis Checklist

When facing storage issues, check in this order:

1. **PVC Status**:

   ```bash
   kubectl get pvc
   kubectl describe pvc <pvc-name>
   ```

1. **PV Availability**:

   ```bash
   kubectl get pv
   ```

1. **StorageClass**:

   ```bash
   kubectl get storageclass
   kubectl get storageclass <class-name> -o yaml
   ```

1. **Validation**:

   ```bash
   sbkube validate
   ```

1. **Pod Events**:

   ```bash
   kubectl describe pod <pod-name>
   ```

1. **Node Affinity** (hostPath only):

   ```bash
   kubectl get pv <pv-name> -o yaml | grep -A10 nodeAffinity
   kubectl get pod <pod-name> -o jsonpath='{.spec.nodeName}'
   ```

______________________________________________________________________

## Related Documentation

- [Storage Management Best Practices](../05-best-practices/storage-management.md)
- [Examples: Storage Management](../../examples/storage-management/)
- [Config Schema: Persistence](../03-configuration/config-schema.md)

______________________________________________________________________

## Change History

### v1.0 (2025-01-11)

- Initial troubleshooting guide for v0.8.0 PV validation
- Added 5 common storage issues with solutions
- Added quick diagnosis checklist
