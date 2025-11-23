#!/bin/bash
# 스크립트명: Blue-Green Switch Script
# 용도: Switch traffic between blue and green environments
# 사용법: ./switch.sh <blue|green>
# 예시: ./switch.sh green

set -e

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
TARGET_ENV="${1}"

if [[ "${TARGET_ENV}" != "blue" && "${TARGET_ENV}" != "green" ]]; then
    echo "❌ Invalid environment: ${TARGET_ENV}"
    echo "Usage: $0 <blue|green>"
    exit 1
fi

echo "━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━"
echo "🔄 Switching traffic to ${TARGET_ENV} environment"
echo "━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━"

# Show current state
echo "📊 Current state:"
kubectl get pods -n bluegreen-demo -l app=backend --show-labels

# Apply service for target environment
echo ""
echo "🔧 Updating Service to point to ${TARGET_ENV} environment..."
kubectl apply -f "${SCRIPT_DIR}/manifests/service-${TARGET_ENV}.yaml"

# Wait for service update
echo "⏳ Waiting for service update..."
sleep 3

# Verify switch
echo "✅ Traffic switched to ${TARGET_ENV} environment"
echo ""
echo "📊 Current service endpoints:"
kubectl get endpoints -n bluegreen-demo backend -o yaml | grep -A5 addresses

echo ""
echo "💡 Verification steps:"
echo "   1. Test the application endpoint"
echo "   2. Monitor metrics for ${TARGET_ENV} pods"
echo "   3. Check logs: kubectl logs -n bluegreen-demo -l environment=${TARGET_ENV}"
echo ""
echo "🔙 Rollback if needed:"
if [[ "${TARGET_ENV}" == "green" ]]; then
    echo "   ./switch.sh blue"
else
    echo "   ./switch.sh green"
fi
