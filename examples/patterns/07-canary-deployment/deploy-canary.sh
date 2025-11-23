#!/bin/bash
# 스크립트명: Canary Deployment Script
# 용도: Progressively deploy canary version with traffic shifting
# 사용법: ./deploy-canary.sh [phase]
# 예시: ./deploy-canary.sh 10

set -e

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
PHASE="${1:-10}"

case "${PHASE}" in
    stable|0)
        CONFIG="config-stable.yaml"
        DESCRIPTION="Stable version only (100% stable traffic)"
        ;;
    10)
        CONFIG="config-canary-10.yaml"
        DESCRIPTION="Canary phase 1 (10% canary, 90% stable)"
        ;;
    50)
        CONFIG="config-canary-50.yaml"
        DESCRIPTION="Canary phase 2 (50% canary, 50% stable)"
        ;;
    promote|100)
        CONFIG="config-promote.yaml"
        DESCRIPTION="Promote canary to stable (100% new version)"
        ;;
    *)
        echo "❌ Invalid phase: ${PHASE}"
        echo "Usage: $0 [stable|10|50|promote]"
        exit 1
        ;;
esac

echo "━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━"
echo "🐤 Deploying Canary - Phase: ${PHASE}"
echo "   ${DESCRIPTION}"
echo "   Config: ${CONFIG}"
echo "━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━"

# Deploy service and monitoring (shared across versions)
echo "🔧 Applying shared resources (Service, ServiceMonitor)..."
kubectl apply -f "${SCRIPT_DIR}/manifests/"

# Validate configuration
echo "🔍 Validating configuration..."
sbkube validate "${CONFIG}" --schema-type config

# Deploy applications
echo "🚀 Deploying applications..."
sbkube apply --app-dir "${SCRIPT_DIR}" --config "${CONFIG}"

# Wait for rollout
echo "⏳ Waiting for rollout to complete..."
sleep 5

# Check status
echo "📊 Checking deployment status..."
sbkube status --app-dir "${SCRIPT_DIR}" --config "${CONFIG}"

echo ""
echo "━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━"
echo "✅ Canary deployment phase ${PHASE} completed!"
echo "━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━"

# Show pod distribution
echo ""
echo "📈 Current pod distribution:"
kubectl get pods -n canary-demo -l app=backend --show-labels

echo ""
echo "💡 Next steps:"
case "${PHASE}" in
    stable|0)
        echo "   → Deploy canary at 10%: ./deploy-canary.sh 10"
        ;;
    10)
        echo "   → Monitor metrics and logs"
        echo "   → If stable, increase to 50%: ./deploy-canary.sh 50"
        echo "   → If issues, rollback: ./deploy-canary.sh stable"
        ;;
    50)
        echo "   → Monitor metrics and logs"
        echo "   → If stable, promote: ./deploy-canary.sh promote"
        echo "   → If issues, rollback: ./deploy-canary.sh 10"
        ;;
    promote|100)
        echo "   → Canary successfully promoted to stable!"
        echo "   → New stable version: 2.0.0"
        ;;
esac
