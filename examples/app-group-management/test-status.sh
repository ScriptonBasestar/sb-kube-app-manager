#!/bin/bash
# 스크립트명: SBKube Status 명령어 시연 스크립트
# 용도: Phase 1-7 status 명령어의 모든 옵션 시연
# 사용법: ./test-status.sh
# 예시: ./test-status.sh

set -e

echo "========================================="
echo "SBKube Status Command Demo (Phase 1-7)"
echo "========================================="
echo ""

# 색상 정의
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
NC='\033[0m' # No Color

run_command() {
    echo -e "${YELLOW}$ $1${NC}"
    eval "$1"
    echo ""
}

# Phase 1-2: 기본 명령어
echo "=== Phase 1-2: Basic Status Command ==="
run_command "sbkube status"

# Phase 4: App-Group 그룹핑
echo "=== Phase 4: App-Group Grouping ==="
run_command "sbkube status --by-group"

echo "=== Phase 4: Specific App-Group ==="
run_command "sbkube status app_010_data_postgresql"

echo "=== Phase 4: Managed Apps Only ==="
run_command "sbkube status --managed"

echo "=== Phase 4: Unhealthy Resources Only ==="
run_command "sbkube status --unhealthy"

# Phase 6: Dependency Tree
echo "=== Phase 6: Dependency Tree ==="
run_command "sbkube status --deps"

echo "=== Phase 6: Dependency Tree for Specific Group ==="
run_command "sbkube status app_020_app_backend --deps"

# Phase 7: Health Check
echo "=== Phase 7: Health Check Details ==="
run_command "sbkube status --health-check"

# 옵션 조합
echo "=== Combined Options ==="
run_command "sbkube status --by-group --health-check"

run_command "sbkube status --managed --unhealthy --health-check"

echo ""
echo -e "${GREEN}✅ Status command demo completed!${NC}"
