# Example: Manual PV with hostPath StorageClass

This example demonstrates how to use SBKube with `kubernetes.io/no-provisioner` StorageClass that requires manual PV creation.

## Scenario

- **Environment**: Single-node k3s cluster for development
- **StorageClass**: `postgresql-hostpath` (no-provisioner)
- **App**: PostgreSQL with 8Gi persistent storage

## Prerequisites

```bash
# 1. Running Kubernetes cluster (k3s, minikube, kind, etc.)
kubectl get nodes

# 2. SBKube installed
sbkube version

# 3. StorageClass created
kubectl apply -f storageclass.yaml
```

## Files

- `storageclass.yaml`: StorageClass definition (no-provisioner)
- `pv-postgresql.yaml`: Manual PV for PostgreSQL
- `config.yaml`: SBKube app configuration
- `sources.yaml`: Helm repository configuration

## Workflow

### Step 1: Create StorageClass

```bash
kubectl apply -f storageclass.yaml
```

### Step 2: Validate (will fail without PV)

```bash
sbkube validate

# Expected output:
# ❌ 1개의 PV가 없습니다:
#   ✗ postgresql: postgresql-hostpath (8Gi)
```

### Step 3: Create PV

**Option A: Use provided manifest**

```bash
# Update node name in pv-postgresql.yaml first!
# Find your node name:
kubectl get nodes

# Edit pv-postgresql.yaml and replace "node1" with your actual node name

# Then apply:
kubectl apply -f pv-postgresql.yaml
```

**Option B: Use helper script**

```bash
# Create PV with custom parameters
./create-pv.sh postgresql 8Gi $(kubectl get nodes -o jsonpath='{.items[0].metadata.name}')
```

### Step 4: Verify PV

```bash
kubectl get pv

# Expected output:
# NAME            CAPACITY   ACCESS MODES   RECLAIM POLICY   STATUS      STORAGECLASS
# postgresql-pv   8Gi        RWO            Retain           Available   postgresql-hostpath
```

### Step 5: Validate again (should pass)

```bash
sbkube validate

# Expected output:
# ✅ 모든 필요한 PV 존재 확인 (1개)
#   ✓ postgresql: postgresql-hostpath (8Gi)
```

### Step 6: Deploy

```bash
sbkube apply
```

### Step 7: Verify deployment

```bash
# Check PVC binding
kubectl get pvc -n database

# Expected output:
# NAME              STATUS   VOLUME          CAPACITY
# postgresql-data   Bound    postgresql-pv   8Gi

# Check Pod status
kubectl get pods -n database

# Expected output:
# NAME             READY   STATUS    RESTARTS   AGE
# postgresql-0     1/1     Running   0          2m
```

## Cleanup

```bash
# Delete app
sbkube delete

# Delete PV (data will be retained due to Retain policy)
kubectl delete pv postgresql-pv

# Delete data directory (optional, will lose data!)
# kubectl exec -it postgresql-0 -n database -- rm -rf /bitnami/postgresql
```

## Troubleshooting

### PVC stays Pending

```bash
# Check PVC events
kubectl describe pvc postgresql-data -n database

# Common issues:
# 1. StorageClass mismatch
# 2. PV size too small
# 3. Wrong node (for hostPath)

# Solution: Verify PV matches PVC requirements
kubectl get pv postgresql-pv -o yaml
kubectl get pvc postgresql-data -n database -o yaml
```

### Pod can't mount volume

```bash
# Check Pod events
kubectl describe pod postgresql-0 -n database

# Common issue: Pod scheduled to wrong node (hostPath is node-specific)

# Solution: Add node affinity to PV (see pv-postgresql.yaml)
```

## Related Documentation

- [Storage Management Best Practices](../../../docs/05-best-practices/storage-management.md)
- [Storage Troubleshooting](../../../docs/07-troubleshooting/storage-issues.md)
