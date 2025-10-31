#!/bin/bash
# 스크립트명: SBKube History 명령어 시연 스크립트
# 용도: Phase 5 history 명령어의 모든 옵션 시연
# 사용법: ./test-history.sh
# 예시: ./test-history.sh

set -e

echo "========================================="
echo "SBKube History Command Demo (Phase 5)"
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

# Phase 5: Basic History
echo "=== Phase 5: Basic History List ==="
run_command "sbkube history"

echo "=== Phase 5: Limited History ==="
run_command "sbkube history --limit 5"

echo "=== Phase 5: App-Group Filtering ==="
run_command "sbkube history app_010_data_postgresql"

# Phase 5: Deployment Comparison
echo "=== Phase 5: Deployment Diff ==="
echo "Note: Replace dep_123,dep_456 with actual deployment IDs from your history"
echo -e "${YELLOW}$ sbkube history --diff dep_123,dep_456${NC}"
echo "(Run 'sbkube history' first to get actual deployment IDs)"
echo ""

echo "=== Phase 5: Helm Values Diff ==="
echo -e "${YELLOW}$ sbkube history --values-diff dep_123,dep_456${NC}"
echo "(Run 'sbkube history' first to get actual deployment IDs)"
echo ""

# Format options
echo "=== Phase 5: JSON Format ==="
run_command "sbkube history --format json --limit 3"

echo "=== Phase 5: YAML Format ==="
run_command "sbkube history --format yaml --limit 3"

# Detailed view
echo "=== Phase 5: Show Specific Deployment ==="
echo "Note: Replace dep_123 with actual deployment ID"
echo -e "${YELLOW}$ sbkube history --show dep_123${NC}"
echo "(Run 'sbkube history' first to get actual deployment ID)"
echo ""

echo ""
echo -e "${GREEN}✅ History command demo completed!${NC}"
echo ""
echo "💡 To test comparison features:"
echo "   1. Run 'sbkube history' to get deployment IDs"
echo "   2. Run 'sbkube history --diff <id1>,<id2>'"
echo "   3. Run 'sbkube history --values-diff <id1>,<id2>'"
