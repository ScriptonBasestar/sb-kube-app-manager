#!/bin/bash
# Phase F4: 최종 검증

set -e
cd "$(dirname "$0")/../.."

echo "=== Phase F4: 문서 현행화 최종 검증 ==="
echo ""

# 1. 버전 정보 검증
echo "1. 버전 정보 검증 (0.3.0):"
if grep -r "0\.2\.1" docs/ 2>/dev/null | grep -v ".sh:" | grep -v "CHANGELOG"; then
    echo "  ❌ 0.2.1 버전 참조 발견!"
else
    echo "  ✅ 0.2.1 참조 없음"
fi

if grep -r "v0\.2\." docs/ 2>/dev/null | grep -v ".sh:" | grep -v "CHANGELOG\|MIGRATION" | head -5; then
    echo "  ⚠️  v0.2.x 참조 일부 남아있음 (마이그레이션 문서 제외)"
else
    echo "  ✅ v0.2.x 참조 정리됨"
fi
echo ""

# 2. Legacy 타입 검증
echo "2. Legacy 타입 검증:"
LEGACY_TYPES="helm-oci|copy-app|pull-helm|pull-git|pull-http|install-action|install-yaml|install-kustomize"

if grep -rE "type: ($LEGACY_TYPES)" docs/ 2>/dev/null | grep -v ".sh:" | grep -v "CHANGELOG"; then
    echo "  ❌ Legacy 타입 발견!"
else
    echo "  ✅ Legacy 타입 없음"
fi
echo ""

# 3. specs 필드 검증
echo "3. specs 필드 검증:"
if grep -r "^    specs:" docs/ 2>/dev/null | grep -v ".sh:" | grep -v "CHANGELOG\|README\.md\|examples" | head -5; then
    echo "  ⚠️  specs 필드 일부 남아있음 (예제 파일 재작성 필요)"
else
    echo "  ✅ 주요 문서에서 specs 필드 제거됨"
fi
echo ""

# 4. 현행 타입 확인
echo "4. 현행 타입 (8개):"
echo "  helm, yaml, action, exec, git, http, kustomize, noop"
echo ""

# 5. 문서 파일 개수
echo "5. 문서 통계:"
echo "  - 총 문서 파일: $(find docs/ -name "*.md" | wc -l)개"
echo "  - Phase E-F 수정 파일: 약 25개"
echo ""

echo "=== 검증 완료 ==="
echo ""
echo "📝 추가 작업 필요:"
echo "  - docs/03-configuration/README.md (v0.2.x 형식, 재작성 필요)"
echo "  - docs/06-examples/README.md (v0.2.x 형식, 재작성 필요)"
echo "  - 위 파일들은 examples/ 디렉토리 README.md로 대체 가능"
