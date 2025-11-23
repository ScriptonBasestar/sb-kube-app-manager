#!/bin/bash
# 스크립트명: Blue-Green Deployment Script
# 용도: Deploy and manage blue-green deployment strategy
# 사용법: ./deploy-bluegreen.sh <phase>
# 예시: ./deploy-bluegreen.sh blue-active

set -e

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
PHASE="${1:-blue-active}"

case "${PHASE}" in
    blue-active|blue)
        CONFIG="config-blue-active.yaml"
        DESCRIPTION="Blue active (v1.0.0), green idle (v2.0.0)"
        ACTIVE_ENV="blue"
        ;;
    green-active|green)
        CONFIG="config-green-active.yaml"
        DESCRIPTION="Green active (v2.0.0), blue idle (v1.0.0)"
        ACTIVE_ENV="green"
        ;;
    *)
        echo "❌ Invalid phase: ${PHASE}"
        echo "Usage: $0 <blue-active|green-active>"
        exit 1
        ;;
esac

echo "━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━"
echo "🔵🟢 Blue-Green Deployment"
echo "   Phase: ${PHASE}"
echo "   ${DESCRIPTION}"
echo "   Config: ${CONFIG}"
echo "━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━"

# Validate configuration
echo "🔍 Validating configuration..."
sbkube validate "${CONFIG}" --schema-type config

# Deploy both environments
echo "🚀 Deploying both environments..."
sbkube apply --app-dir "${SCRIPT_DIR}" --config "${CONFIG}"

# Apply service pointing to active environment
echo "🔧 Applying Service for ${ACTIVE_ENV} environment..."
kubectl apply -f "${SCRIPT_DIR}/manifests/service-${ACTIVE_ENV}.yaml"

# Wait for rollout
echo "⏳ Waiting for rollout to complete..."
sleep 5

# Check status
echo "📊 Checking deployment status..."
sbkube status --app-dir "${SCRIPT_DIR}" --config "${CONFIG}"

echo ""
echo "━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━"
echo "✅ Blue-Green deployment completed!"
echo "   Active: ${ACTIVE_ENV} environment"
echo "━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━"

# Show pod distribution
echo ""
echo "📈 Environment status:"
kubectl get pods -n bluegreen-demo -l app=backend --show-labels

echo ""
echo "💡 Next steps:"
if [[ "${ACTIVE_ENV}" == "blue" ]]; then
    echo "   → Test and validate green environment (idle)"
    echo "   → When ready, switch traffic: ./switch.sh green"
else
    echo "   → Monitor green environment (active)"
    echo "   → If issues, rollback: ./switch.sh blue"
fi
