#!/bin/bash
# PV 자동 생성 스크립트
# 용도: hostPath 기반 PersistentVolume을 동적으로 생성
# 사용법: ./create-pv.sh <app-name> <size> <node-name> [storage-class]
# 예시: ./create-pv.sh postgresql 8Gi node1

set -euo pipefail

# Arguments
APP_NAME="${1:-}"
STORAGE_SIZE="${2:-8Gi}"
NODE_NAME="${3:-}"
STORAGE_CLASS="${4:-${APP_NAME}-hostpath}"
HOST_PATH="${5:-/mnt/data/${APP_NAME}}"

# Validate arguments
if [ -z "$APP_NAME" ]; then
  echo "Error: APP_NAME is required"
  echo "Usage: $0 <app-name> <size> <node-name> [storage-class] [host-path]"
  echo "Example: $0 postgresql 8Gi node1"
  exit 1
fi

if [ -z "$NODE_NAME" ]; then
  echo "Error: NODE_NAME is required"
  echo "Usage: $0 <app-name> <size> <node-name> [storage-class] [host-path]"
  echo ""
  echo "Available nodes:"
  kubectl get nodes -o custom-columns=NAME:.metadata.name --no-headers
  exit 1
fi

# Verify node exists
if ! kubectl get node "$NODE_NAME" &>/dev/null; then
  echo "Error: Node '$NODE_NAME' not found"
  echo ""
  echo "Available nodes:"
  kubectl get nodes
  exit 1
fi

# Create PV
echo "Creating PersistentVolume:"
echo "  Name: ${APP_NAME}-pv"
echo "  Size: ${STORAGE_SIZE}"
echo "  StorageClass: ${STORAGE_CLASS}"
echo "  HostPath: ${HOST_PATH}"
echo "  Node: ${NODE_NAME}"
echo ""

cat <<EOF | kubectl apply -f -
apiVersion: v1
kind: PersistentVolume
metadata:
  name: ${APP_NAME}-pv
  labels:
    type: local
    app: ${APP_NAME}
spec:
  storageClassName: ${STORAGE_CLASS}
  capacity:
    storage: ${STORAGE_SIZE}
  accessModes:
    - ReadWriteOnce
  persistentVolumeReclaimPolicy: Retain
  hostPath:
    path: ${HOST_PATH}
    type: DirectoryOrCreate
  nodeAffinity:
    required:
      nodeSelectorTerms:
      - matchExpressions:
        - key: kubernetes.io/hostname
          operator: In
          values:
            - ${NODE_NAME}
EOF

echo ""
echo "✅ PersistentVolume created successfully!"
echo ""
echo "Verify with:"
echo "  kubectl get pv ${APP_NAME}-pv"
