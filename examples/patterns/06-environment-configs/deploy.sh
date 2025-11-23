#!/bin/bash
# 스크립트명: Environment-Based Deployment Script
# 용도: Deploy application to specific environment (dev, staging, production)
# 사용법: ./deploy.sh <environment>
# 예시: ./deploy.sh dev

set -e

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
ENV="${1:-dev}"

# Validate environment parameter
case "${ENV}" in
    dev|development)
        CONFIG_FILE="config-dev.yaml"
        ;;
    staging|stg)
        CONFIG_FILE="config-staging.yaml"
        ;;
    prod|production)
        CONFIG_FILE="config-production.yaml"
        ;;
    *)
        echo "❌ Invalid environment: ${ENV}"
        echo "Usage: $0 <dev|staging|production>"
        exit 1
        ;;
esac

echo "━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━"
echo "📦 Deploying to ${ENV} environment"
echo "   Config: ${CONFIG_FILE}"
echo "━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━"

# Validate configuration
echo "🔍 Validating configuration..."
sbkube validate "${CONFIG_FILE}" --schema-type config

# Deploy
echo "🚀 Deploying applications..."
sbkube apply --app-dir "${SCRIPT_DIR}" --config "${CONFIG_FILE}"

# Check status
echo "📊 Checking deployment status..."
sbkube status --app-dir "${SCRIPT_DIR}" --config "${CONFIG_FILE}"

echo "━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━"
echo "✅ Deployment to ${ENV} completed successfully!"
echo "━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━"
