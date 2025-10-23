#!/bin/bash
# Phase F1-F2: 문서 버전 및 Legacy 타입 업데이트

set -e

cd "$(dirname "$0")/../.."

echo "=== Phase F1: 버전 정보 업데이트 ==="

# v0.2.x → 이전 버전
sed -i 's/v0\.2\.x 사용자는/이전 버전 사용자는/g' docs/01-getting-started/README.md
sed -i 's/v0\.2\.x에서 마이그레이션/이전 버전에서 마이그레이션/g' docs/02-features/application-types.md
sed -i 's/Before (v0\.2\.x)/Before/g' docs/02-features/application-types.md
sed -i 's/v0\.2\.x와의 차이점/이전 버전과의 차이점/g' docs/03-configuration/config-schema.md
sed -i 's/v0\.2\.x 동등 타입/이전 버전 타입/g' docs/03-configuration/config-schema.md

# vision-roadmap.md 업데이트
sed -i 's/(v0\.2\.x - v0\.3\.x)/(v0.3.x - v0.4.x)/g' docs/00-product/vision-roadmap.md
sed -i 's/v0\.2\.x (현재 버전)/v0.3.x (현재 버전)/g' docs/00-product/vision-roadmap.md
sed -i 's/v0\.2\.x 안정화/v0.3.0 안정화/g' docs/00-product/vision-roadmap.md

echo "=== Phase F2: Legacy 타입 제거 ==="

# helm-oci 제거
sed -i '/^- \*\*`helm-oci`\*\* - OCI 차트 준비$/d' docs/02-features/commands.md
sed -i '/^- \*\*`helm-oci`\*\* - OCI 레지스트리에서 Helm 차트 pull$/d' docs/02-features/README.md

# Legacy 타입 목록 업데이트 (helm, yaml, action, exec, git, http, kustomize, noop)
sed -i "s/'exec', 'helm', 'install-action', 'install-kustomize', 'yaml',/'exec', 'helm', 'action', 'yaml',/g" docs/02-features/architecture.md
sed -i "s/'helm', 'helm-oci', 'pull-git', 'pull-http', 'copy-app'/'helm', 'git', 'http', 'kustomize', 'noop'/g" docs/02-features/architecture.md

# install-action → action
sed -i 's/install-action/action/g' docs/03-configuration/config-schema.md

# troubleshooting 타입 목록 업데이트
sed -i 's/# 지원 타입: helm, helm-oci, pull-git, pull-http, copy-app/# 지원 타입: helm, git, http, kustomize/g' docs/07-troubleshooting/README.md
sed -i 's/#           helm, yaml, install-action, install-kustomize, exec/#           helm, yaml, action, exec, noop/g' docs/07-troubleshooting/README.md

# INDEX.md 타입 업데이트
sed -i 's/- \*\*helm\*\* \/ \*\*helm-oci\*\* \/ \*\*pull-git\*\* - 소스 준비/- **helm** \/ **git** \/ **http** - 소스 준비/g' docs/INDEX.md
sed -i 's/- \*\*copy-app\*\* - 로컬 파일 복사//g' docs/INDEX.md
sed -i 's/- \*\*helm\*\* \/ \*\*yaml\*\* \/ \*\*install-action\*\* - 배포 방법/- **helm** \/ **yaml** \/ **action** \/ **exec** - 배포 방법/g' docs/INDEX.md

# ARCHITECTURE.md 업데이트
sed -i "s/elif app.type == 'helm-oci':/# Legacy type removed/g" docs/10-modules/sbkube/ARCHITECTURE.md
sed -i "s/'helm', 'pull-git', 'copy-app',/'helm', 'git', 'http', 'kustomize',/g" docs/10-modules/sbkube/ARCHITECTURE.md

# backlog.md 업데이트
sed -i 's/helm-oci/helm/g' docs/99-internal/backlog.md

echo "완료!"
