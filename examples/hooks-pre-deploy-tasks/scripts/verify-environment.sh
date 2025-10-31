#!/bin/bash
# 스크립트명: verify-environment.sh
# 용도: 배포 전 환경 검증
# 사용법: bash verify-environment.sh

echo "🔍 Verifying deployment environment..."

# kubectl 확인
if ! command -v kubectl &> /dev/null; then
    echo "❌ kubectl not found"
    exit 1
fi
echo "✅ kubectl available"

# 클러스터 접근 확인
if ! kubectl cluster-info &> /dev/null; then
    echo "❌ Cannot access Kubernetes cluster"
    exit 1
fi
echo "✅ Cluster accessible"

# StorageClass 확인 (optional)
if kubectl get storageclass &> /dev/null; then
    echo "✅ StorageClass available"
fi

echo "✅ Environment verification complete"
