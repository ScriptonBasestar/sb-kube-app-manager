#!/bin/bash
# Phase F3: specs 필드 제거 (핵심 파일만)

set -e
cd "$(dirname "$0")/../.."

echo "=== Phase F3: specs 필드 및 v0.2.x 예제 정리 ==="

# 1. docs/00-product/product-spec.md - 섹션 2.1의 legacy 예제 삭제
echo "Updating product-spec.md..."
# Legacy Helm 예제 섹션 삭제 (라인 148-171)
sed -i '148,171d' docs/00-product/product-spec.md

# 2. docs/10-modules/sbkube/docs/40-maintenance/troubleshooting.md - specs 예제 삭제
echo "Updating troubleshooting.md..."
sed -i '/^    specs:$/,/^      dest:/d' docs/10-modules/sbkube/docs/40-maintenance/troubleshooting.md

# 3. docs/02-features/architecture.md - specs 필드 언급 삭제
echo "Updating architecture.md..."
sed -i '/specs: Dict\[str, Any\]/d' docs/02-features/architecture.md

# 4. docs/10-modules/sbkube/MODULE.md - specs 스키마 삭제
echo "Updating MODULE.md..."
sed -i '/^    specs: dict$/d' docs/10-modules/sbkube/MODULE.md

# 5. docs/10-modules/sbkube/ARCHITECTURE.md - specs 참조 정리
echo "Updating ARCHITECTURE.md..."
sed -i 's/└─ specs: Union\[AppSpecBase, dict\]/# Flattened structure (no specs wrapper)/g' docs/10-modules/sbkube/ARCHITECTURE.md
sed -i 's/└─► specs: AppSpecBase/# Direct fields at app level/g' docs/10-modules/sbkube/ARCHITECTURE.md

echo "Phase F3 완료!"
echo ""
echo "참고: docs/03-configuration/README.md와 docs/06-examples/README.md는"
echo "      v0.2.x 형식이므로 별도 재작성 또는 삭제가 필요합니다."
