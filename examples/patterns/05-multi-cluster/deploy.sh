#!/bin/bash
# 스크립트명: Multi-Cluster Deployment Script
# 용도: Deploy the same application stack to multiple Kubernetes clusters
# 사용법: ./deploy.sh [cluster-a|cluster-b|all]
# 예시: ./deploy.sh all

set -e

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
CLUSTER="${1:-all}"

deploy_to_cluster() {
    local cluster_name=$1
    local config_file="config-${cluster_name}.yaml"
    local sources_file="sources-${cluster_name}.yaml"

    echo "━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━"
    echo "📦 Deploying to ${cluster_name}"
    echo "━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━"

    # Validate configuration
    echo "🔍 Validating configuration..."
    sbkube validate "${config_file}"

    # Deploy
    echo "🚀 Deploying applications..."
    sbkube apply \
        --app-dir "${SCRIPT_DIR}" \
        --config "${config_file}" \
        --sources "${sources_file}"

    # Check status
    echo "📊 Checking deployment status..."
    sbkube status \
        --app-dir "${SCRIPT_DIR}" \
        --config "${config_file}"

    echo "✅ Deployment to ${cluster_name} completed"
    echo ""
}

case "${CLUSTER}" in
    cluster-a)
        deploy_to_cluster "cluster-a"
        ;;
    cluster-b)
        deploy_to_cluster "cluster-b"
        ;;
    all)
        deploy_to_cluster "cluster-a"
        deploy_to_cluster "cluster-b"
        ;;
    *)
        echo "Usage: $0 [cluster-a|cluster-b|all]"
        exit 1
        ;;
esac

echo "━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━"
echo "🎉 Multi-cluster deployment completed successfully!"
echo "━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━"
