# sbkube Registry Architecture Design

## Executive Summary

sbkube에 Helm Chart Repository와 유사한 App Registry 시스템을 도입하여 Kubernetes 애플리케이션 설정의 재사용성, 버전 관리, 표준화를 달성합니다.

---

## 1. Background & Motivation

### 1.1 현재 문제점

**중복 관리**:
- 여러 클러스터에서 동일한 앱 설정을 개별 관리
- Traefik, Redis, ArgoCD 등 공통 앱의 설정이 90% 중복
- 업그레이드 시 모든 클러스터를 수동으로 동기화

**버전 관리 부재**:
- 앱 설정의 버전이 Git commit에만 의존
- 설정 변경 이력 추적 어려움
- 롤백 시 어느 시점으로 돌아가야 할지 불명확

**표준화 어려움**:
- 팀/조직 표준 설정을 공유할 방법 없음
- 보안 정책, 모니터링 규칙 등을 일관되게 적용하기 어려움

### 1.2 목표

1. **재사용성**: 공통 앱 설정을 여러 클러스터에서 공유
2. **버전 관리**: Semantic Versioning으로 설정 버전 관리
3. **표준화**: 조직 표준 설정을 레지스트리로 배포
4. **호환성**: 기존 sbkube 사용자 경험 유지

---

## 2. Registry Architecture

### 2.1 Registry 구조

```
sbkube-registry/
├── index.yaml                    # 전체 앱 목록 (Helm repo index와 유사)
├── apps/
│   ├── traefik/
│   │   ├── 3.2.0/
│   │   │   ├── app-metadata.yaml    # 앱 메타데이터
│   │   │   ├── config.yaml          # sbkube config
│   │   │   ├── values/              # Helm values
│   │   │   ├── manifests/           # YAML manifests
│   │   │   ├── overrides/           # ConfigMap/Secret overrides
│   │   │   └── README.md
│   │   ├── 3.2.1/
│   │   └── index.yaml               # 앱별 버전 인덱스
│   ├── redis/
│   │   ├── 7.0.0/
│   │   └── index.yaml
│   └── argocd/
│       ├── 2.11.0/
│       └── index.yaml
└── README.md
```

### 2.2 메타데이터 스키마

**index.yaml** (Registry Root):
```yaml
apiVersion: sbkube.io/v1
kind: RegistryIndex
metadata:
  name: scripton-base
  url: https://github.com/scripton/sbkube-registry
  generated: 2025-11-11T12:00:00Z

apps:
  traefik:
    description: Traefik Ingress Controller with enterprise features
    maintainers:
      - name: Scripton Team
        email: team@scripton.com
    versions:
      - version: 3.2.1
        created: 2025-11-10T10:00:00Z
        digest: sha256:abc123...
        deprecated: false
      - version: 3.2.0
        created: 2025-11-01T10:00:00Z
        digest: sha256:def456...
        deprecated: false

  redis:
    description: Redis in-memory data store
    versions:
      - version: 7.0.0
        created: 2025-10-15T10:00:00Z
```

**app-metadata.yaml** (앱별):
```yaml
apiVersion: sbkube.io/v1
kind: AppMetadata
metadata:
  name: traefik
  version: 3.2.1
  created: 2025-11-10T10:00:00Z

description: |
  Traefik Ingress Controller with:
  - ACME/Let's Encrypt support
  - Prometheus metrics
  - Enterprise security policies

dependencies:
  - name: cert-manager
    version: ">=1.13.0"
    optional: true

helm:
  repository: https://helm.traefik.io/traefik
  chart: traefik
  version: 30.0.0

maintainers:
  - name: John Doe
    email: john@example.com

keywords:
  - ingress
  - traefik
  - load-balancer

annotations:
  sbkube.io/phase: p1-infra
  sbkube.io/category: networking
```

---

## 3. Registry Types

### 3.1 Local Registry

**사용 사례**: 개발/테스트, 조직 내부 표준

**구조**:
```bash
# 로컬 파일 시스템
~/mywork/iac/sbkube-registry/
```

**설정**:
```yaml
# ~/.sbkube/config.yaml
registries:
  - name: local-base
    type: local
    path: ~/mywork/iac/sbkube-registry
```

**사용**:
```yaml
# config.yaml
apps:
  traefik:
    type: registry
    source: local-base/traefik@3.2.1
    values:
      - values/overrides.yaml
```

### 3.2 Git Registry

**사용 사례**: 팀 공유, 버전 관리, CI/CD 통합

**구조**:
```bash
# GitHub/GitLab Repository
https://github.com/scripton/sbkube-registry.git
```

**설정**:
```yaml
# ~/.sbkube/config.yaml
registries:
  - name: scripton-base
    type: git
    url: https://github.com/scripton/sbkube-registry.git
    branch: main  # 또는 특정 브랜치
```

**사용**:
```yaml
apps:
  traefik:
    type: registry
    source: scripton-base/traefik@3.2.1
```

**고급 Git 참조**:
```yaml
apps:
  traefik:
    type: registry
    # Branch 지정
    source: scripton-base/traefik@3.2.1?ref=main

  redis:
    # Commit SHA 지정
    source: scripton-base/redis@7.0.0?ref=abc1234

  argocd:
    # Tag 지정
    source: scripton-base/argocd@2.11.0?ref=v2.11.0
```

### 3.3 OCI Registry (Future)

**사용 사례**: 엔터프라이즈, 공개 레지스트리

**구조**:
```bash
# OCI-compatible registry
oci://ghcr.io/scripton/sbkube-apps
```

**설정**:
```yaml
registries:
  - name: ghcr
    type: oci
    url: oci://ghcr.io/scripton/sbkube-apps
    auth:
      username: ${GITHUB_USERNAME}
      password: ${GITHUB_TOKEN}
```

**사용**:
```yaml
apps:
  traefik:
    type: registry
    source: ghcr/traefik:3.2.1
```

---

## 4. CLI Commands

### 4.1 Registry 관리

```bash
# 레지스트리 추가
sbkube registry add scripton-base https://github.com/scripton/sbkube-registry.git
sbkube registry add local-base --type local --path ~/mywork/iac/sbkube-registry

# 레지스트리 목록
sbkube registry list
# 출력:
# NAME            TYPE    URL
# scripton-base   git     https://github.com/scripton/sbkube-registry.git
# local-base      local   ~/mywork/iac/sbkube-registry

# 레지스트리 업데이트 (Git fetch)
sbkube registry update scripton-base
sbkube registry update --all

# 레지스트리 제거
sbkube registry remove scripton-base
```

### 4.2 App 검색 및 정보

```bash
# 앱 검색
sbkube search traefik
# 출력:
# NAME                    VERSION    DESCRIPTION
# scripton-base/traefik   3.2.1      Traefik Ingress Controller with enterprise features
# scripton-base/traefik   3.2.0      Traefik Ingress Controller (deprecated)

# 특정 레지스트리에서만 검색
sbkube search traefik --registry scripton-base

# 앱 상세 정보
sbkube show scripton-base/traefik@3.2.1
# 출력:
# Name: traefik
# Version: 3.2.1
# Registry: scripton-base
# Description: Traefik Ingress Controller with enterprise features
# Dependencies:
#   - cert-manager (>=1.13.0, optional)
# Helm Chart: traefik/traefik:30.0.0
# Maintainers: Scripton Team <team@scripton.com>

# 모든 버전 확인
sbkube show scripton-base/traefik --versions
```

### 4.3 App 배포 (레지스트리 기반)

```bash
# 레지스트리에서 직접 배포
sbkube deploy --app scripton-base/traefik@3.2.1 \
  --namespace kube-system \
  --values custom-values.yaml

# config.yaml 없이 quick deploy
sbkube deploy \
  --app scripton-base/traefik@3.2.1 \
  --app scripton-base/redis@7.0.0 \
  --namespace infra

# 앱 업그레이드
sbkube upgrade traefik --version 3.2.2
sbkube upgrade --all  # 모든 앱 최신 버전으로

# 앱 다운그레이드/롤백
sbkube rollback traefik --version 3.2.0
```

### 4.4 Registry 생성/관리 (Maintainer용)

```bash
# 새 레지스트리 초기화
sbkube registry init ~/mywork/iac/sbkube-registry
# 생성: index.yaml, apps/, README.md

# 앱 추가
sbkube registry app add traefik --version 3.2.0 \
  --helm-chart traefik/traefik:30.0.0 \
  --description "Traefik Ingress Controller"

# 기존 config.yaml에서 import
sbkube registry app import ./p1-infra/app_010_infra_network \
  --name traefik \
  --version 3.2.0 \
  --registry ~/mywork/iac/sbkube-registry

# 인덱스 재생성
sbkube registry reindex ~/mywork/iac/sbkube-registry

# 앱 검증
sbkube registry validate ~/mywork/iac/sbkube-registry/apps/traefik/3.2.0

# 앱 패키징 (OCI 푸시용)
sbkube registry package traefik:3.2.0 --output traefik-3.2.0.tar.gz
```

---

## 5. Configuration Integration

### 5.1 기존 방식 (Backward Compatible)

```yaml
# config.yaml (기존 방식 계속 사용 가능)
namespace: infra

apps:
  traefik:
    type: helm
    chart: traefik/traefik
    values:
      - values/traefik.yaml
    namespace: kube-system
```

### 5.2 레지스트리 참조 방식

```yaml
# config.yaml (새로운 방식)
namespace: infra

apps:
  traefik:
    type: registry
    source: scripton-base/traefik@3.2.1
    values:
      # 레지스트리 base values 위에 override
      - values/custom-overrides.yaml
    namespace: kube-system

  redis:
    type: registry
    source: scripton-base/redis@7.0.0
    # values 없으면 레지스트리 기본값 사용
```

### 5.3 혼합 사용

```yaml
apps:
  # 레지스트리 앱
  traefik:
    type: registry
    source: scripton-base/traefik@3.2.1

  # 기존 방식 (로컬 설정)
  custom-app:
    type: helm
    chart: my-org/custom-app
    values:
      - values/custom-app.yaml

  # 로컬 YAML 매니페스트
  local-service:
    type: yaml
    manifests:
      - manifests/service.yaml
```

### 5.4 Values Override 우선순위

```yaml
# 최종 values는 아래 순서로 merge
# 1. Registry base values (lowest priority)
# 2. Registry app-specific values
# 3. User-provided values files (highest priority)

apps:
  traefik:
    type: registry
    source: scripton-base/traefik@3.2.1
    values:
      - values/global-overrides.yaml    # 2순위
      - values/cluster-overrides.yaml   # 1순위 (최우선)
```

---

## 6. Implementation Phases

### Phase 1: Local Registry (Week 1-2) ✅ 즉시 시작 가능

**목표**: 로컬 파일 시스템 기반 레지스트리

**구현**:
1. Registry 디렉토리 구조 정의
2. `app-metadata.yaml` 스키마 구현
3. 로컬 레지스트리 읽기/쓰기 기능
4. 기존 `config.yaml`에서 `type: registry` 지원

**CLI 명령어**:
- `sbkube registry init`
- `sbkube registry add --type local`
- `sbkube search` (로컬 레지스트리 검색)
- `sbkube show`

**검증**:
```bash
# Traefik을 레지스트리로 추출
sbkube registry app import \
  ./p1-infra/app_010_infra_network \
  --name traefik \
  --version 3.2.0

# 다른 클러스터에서 사용
cd ../polypia/ph1_foundation/app_000_infra_network
# config.yaml 수정
apps:
  traefik:
    type: registry
    source: local-base/traefik@3.2.0

sbkube deploy --app-dir .
```

### Phase 2: Git Registry (Week 3-4)

**목표**: Git 저장소 기반 레지스트리

**구현**:
1. Git clone/pull 자동화
2. `~/.sbkube/registry-cache/` 캐시 디렉토리
3. Git ref 지원 (branch/tag/commit)
4. Registry 자동 업데이트

**CLI 명령어**:
- `sbkube registry add <url>`
- `sbkube registry update`
- Git URL 파싱 (`source: github.com/org/repo//path@version`)

**검증**:
```bash
# GitHub 레지스트리 추가
sbkube registry add scripton-base \
  https://github.com/scripton/sbkube-registry.git

# 자동 clone → ~/.sbkube/registry-cache/scripton-base/
# 앱 검색 및 배포
sbkube search traefik --registry scripton-base
sbkube deploy --app scripton-base/traefik@3.2.1
```

### Phase 3: Versioning & Index (Week 5-6)

**목표**: Semantic Versioning, 버전 관리, 인덱스

**구현**:
1. `index.yaml` 자동 생성
2. Semantic Version 파싱 및 정렬
3. 버전 범위 지원 (`>=3.2.0`, `~3.2.0`)
4. Deprecation 경고

**CLI 명령어**:
- `sbkube registry reindex`
- `sbkube show --versions`
- `sbkube upgrade --check`

**검증**:
```yaml
# app-metadata.yaml에서 버전 제약
dependencies:
  - name: cert-manager
    version: ">=1.13.0"

# CLI에서 버전 범위 검색
sbkube search traefik --version "~3.2.0"
```

### Phase 4: OCI Registry (Week 7-8+)

**목표**: OCI-compatible registry 지원

**구현**:
1. OCI artifacts push/pull (ORAS 사용)
2. GitHub Container Registry (ghcr.io) 통합
3. 인증 처리 (Docker credentials)
4. Registry mirror 지원

**CLI 명령어**:
- `sbkube registry add --type oci`
- `sbkube registry push`
- `sbkube registry pull`

**검증**:
```bash
# OCI 레지스트리에 푸시
sbkube registry push traefik:3.2.1 \
  --registry oci://ghcr.io/scripton/sbkube-apps

# 다른 사용자가 pull
sbkube registry add ghcr \
  --type oci \
  --url oci://ghcr.io/scripton/sbkube-apps

sbkube deploy --app ghcr/traefik:3.2.1
```

---

## 7. Migration Guide

### 7.1 기존 사용자 마이그레이션

**Step 1: 레지스트리 생성**
```bash
cd ~/mywork/iac
mkdir sbkube-registry
cd sbkube-registry
sbkube registry init .
```

**Step 2: 공통 앱 추출**
```bash
# Traefik 설정을 레지스트리로 export
cd ~/mywork/iac/scripton/p3-kube/p1-infra/app_010_infra_network
sbkube registry app export . \
  --name traefik \
  --version 3.2.0 \
  --output ~/mywork/iac/sbkube-registry
```

**Step 3: 클러스터별 차이점을 overrides로 변환**
```bash
# Scripton 클러스터
cd ~/mywork/iac/scripton/p3-kube/p1-infra/app_010_infra_network

# 기존 values/traefik.yaml을 분석
sbkube registry diff \
  --registry-app local-base/traefik@3.2.0 \
  --local-values values/traefik.yaml \
  --output values/overrides.yaml

# config.yaml 수정
apps:
  traefik:
    type: registry
    source: local-base/traefik@3.2.0
    values:
      - values/overrides.yaml  # 차이점만 포함
```

**Step 4: 다른 클러스터에서 재사용**
```bash
# Polypia 클러스터도 동일 과정 반복
cd ~/mywork/iac/polypia/ph3_kube_app_cluster/ph1_foundation/app_000_infra_network
# ... 동일한 registry app 참조
```

### 7.2 점진적 마이그레이션 전략

**우선순위**:
1. ✅ **High Priority**: 중복도 >90%, 여러 클러스터에서 사용
   - Traefik, Redis, Prometheus, Cert-Manager
2. ⚠️ **Medium Priority**: 중복도 50-90%
   - ArgoCD, PostgreSQL, Grafana
3. ⏸️ **Low Priority**: 클러스터 특화 설정
   - 각 클러스터의 unique 앱들

**권장 순서**:
```bash
# Week 1: Traefik, Redis 2개 앱만
# Week 2: Prometheus, Cert-Manager 추가
# Week 3: 나머지 공통 앱들
# Week 4: 클러스터별 검증 및 튜닝
```

---

## 8. Best Practices

### 8.1 레지스트리 구조

**DO**:
- ✅ Semantic Versioning 사용
- ✅ README.md에 상세 문서 포함
- ✅ 변경 사항은 CHANGELOG.md에 기록
- ✅ 각 버전은 immutable (변경 금지)
- ✅ 하위 호환성 유지 (major version 변경 제외)

**DON'T**:
- ❌ 배포된 버전 수정 (새 버전 생성)
- ❌ secrets/credentials를 레지스트리에 포함
- ❌ 환경별 설정을 base에 포함

### 8.2 버전 관리

```yaml
# 권장: Semantic Versioning
traefik:
  3.2.1  # Patch: 버그 수정, 하위 호환
  3.2.0  # Minor: 새 기능 추가, 하위 호환
  3.0.0  # Major: Breaking changes

# app-metadata.yaml에 deprecation 명시
deprecated: true
deprecationMessage: "Use version 3.2.1 or higher"
```

### 8.3 Values Override 패턴

```yaml
# ❌ 안티패턴: 전체 values 복사
# values/overrides.yaml (1000줄)
deployment:
  replicas: 3
  # ... 나머지 설정 전부 복사

# ✅ 권장: 차이점만 override
# values/overrides.yaml (50줄)
deployment:
  replicas: 3  # 클러스터별 차이만

service:
  type: LoadBalancer
  loadBalancerIP: 192.168.1.100  # 클러스터별 IP
```

### 8.4 보안

**Secrets 관리**:
```yaml
# ❌ 레지스트리에 secret 포함 금지
apps:
  redis:
    values:
      auth:
        password: "hardcoded-password"  # 절대 금지!

# ✅ 환경 변수 또는 외부 secret 참조
apps:
  redis:
    values:
      auth:
        existingSecret: redis-auth  # Kubernetes Secret 참조
```

**레지스트리 접근 제어**:
```yaml
# Private Git registry
registries:
  - name: company-private
    type: git
    url: https://github.com/company/sbkube-private.git
    auth:
      type: token
      token: ${GITHUB_TOKEN}  # 환경 변수 사용
```

---

## 9. Example Use Cases

### 9.1 Multi-Cluster 표준화

**목표**: 3개 클러스터에서 동일한 Traefik 설정 사용

```bash
# Registry 생성
sbkube registry init ~/company/sbkube-standard

# Traefik 표준 설정 추가
sbkube registry app add traefik --version 1.0.0 \
  --helm-chart traefik/traefik:30.0.0

# 3개 클러스터 모두 동일하게 참조
# prod-cluster-1/config.yaml
apps:
  traefik:
    type: registry
    source: company-std/traefik@1.0.0

# prod-cluster-2/config.yaml
apps:
  traefik:
    type: registry
    source: company-std/traefik@1.0.0

# staging-cluster/config.yaml
apps:
  traefik:
    type: registry
    source: company-std/traefik@1.0.0
```

### 9.2 보안 정책 배포

**목표**: 보안 팀이 승인한 설정을 모든 클러스터에 강제 적용

```yaml
# security-registry/apps/traefik/1.0.0/values.yaml
# 보안 팀 승인 설정
deployment:
  podSecurityPolicy:
    enabled: true

ports:
  web:
    forwardedHeaders:
      trustedIPs: ["10.0.0.0/8"]  # 내부 네트워크만

logs:
  access:
    enabled: true
    format: json  # SIEM 통합 필수

# 개발 팀은 override 불가 (정책 준수)
# 단, 성능 튜닝은 가능
apps:
  traefik:
    type: registry
    source: security/traefik@1.0.0
    values:
      - overrides/performance-tuning.yaml  # 성능만 조정
```

### 9.3 버전 업그레이드

**목표**: 새 Traefik 버전을 단계적으로 롤아웃

```bash
# Phase 1: 레지스트리에 새 버전 추가
sbkube registry app add traefik --version 3.3.0 \
  --helm-chart traefik/traefik:31.0.0

# Phase 2: Staging 클러스터에서 테스트
cd staging-cluster
# config.yaml 수정
apps:
  traefik:
    source: company-std/traefik@3.3.0  # 버전만 변경

sbkube deploy --app-dir .

# Phase 3: 검증 후 Production 클러스터 업그레이드
cd prod-cluster-1
# config.yaml 수정 → 3.3.0
sbkube deploy --app-dir .

# 문제 발생 시 즉시 롤백
sbkube rollback traefik --version 3.2.1
```

---

## 10. Technical Specifications

### 10.1 파일 포맷

**index.yaml** (JSON Schema):
```json
{
  "$schema": "http://json-schema.org/draft-07/schema#",
  "type": "object",
  "required": ["apiVersion", "kind", "metadata", "apps"],
  "properties": {
    "apiVersion": { "const": "sbkube.io/v1" },
    "kind": { "const": "RegistryIndex" },
    "metadata": {
      "type": "object",
      "required": ["name", "url", "generated"],
      "properties": {
        "name": { "type": "string" },
        "url": { "type": "string", "format": "uri" },
        "generated": { "type": "string", "format": "date-time" }
      }
    },
    "apps": {
      "type": "object",
      "patternProperties": {
        "^[a-z0-9-]+$": {
          "type": "object",
          "required": ["description", "versions"],
          "properties": {
            "description": { "type": "string" },
            "versions": {
              "type": "array",
              "items": {
                "type": "object",
                "required": ["version", "created", "digest"],
                "properties": {
                  "version": { "type": "string", "pattern": "^\\d+\\.\\d+\\.\\d+$" },
                  "created": { "type": "string", "format": "date-time" },
                  "digest": { "type": "string", "pattern": "^sha256:[a-f0-9]{64}$" },
                  "deprecated": { "type": "boolean", "default": false }
                }
              }
            }
          }
        }
      }
    }
  }
}
```

### 10.2 Digest 계산

```python
import hashlib
import yaml

def calculate_app_digest(app_dir: Path) -> str:
    """
    앱 디렉토리의 모든 파일을 기반으로 SHA256 digest 계산
    """
    hasher = hashlib.sha256()

    # 특정 순서로 파일 읽기 (재현 가능한 digest)
    files = sorted(app_dir.rglob("*.yaml")) + sorted(app_dir.rglob("*.yml"))

    for file in files:
        hasher.update(file.read_bytes())

    return f"sha256:{hasher.hexdigest()}"
```

### 10.3 캐시 전략

```python
# ~/.sbkube/config.yaml
cache:
  enabled: true
  directory: ~/.sbkube/registry-cache
  ttl: 3600  # seconds (1 hour)

registries:
  - name: scripton-base
    type: git
    url: https://github.com/scripton/sbkube-registry.git
    cache:
      enabled: true
      update_strategy: on_access  # on_access | manual | auto
```

**캐시 업데이트 전략**:
- `on_access`: 앱 접근 시 TTL 체크 후 자동 업데이트
- `manual`: 수동으로 `sbkube registry update` 실행 시에만
- `auto`: 백그라운드에서 주기적으로 업데이트 (cron-like)

---

## 11. Comparison with Alternatives

### 11.1 vs Helm Chart Repository

| Feature | Helm Repository | sbkube Registry |
|---------|----------------|-----------------|
| **대상** | Helm charts만 | Helm + YAML + Exec 통합 |
| **설정 관리** | values.yaml만 | values + manifests + overrides |
| **Phase 개념** | ❌ 없음 | ✅ Phase별 dependency 관리 |
| **Multi-app** | 개별 차트 | 앱 그룹 관리 (config.yaml) |
| **OCI 지원** | ✅ 공식 지원 | 🔄 Phase 4 계획 |

### 11.2 vs Flux CD / ArgoCD

| Feature | Flux/ArgoCD | sbkube Registry |
|---------|-------------|-----------------|
| **GitOps** | ✅ 전문 도구 | ⚠️ Git registry로 간접 지원 |
| **CD 자동화** | ✅ 자동 sync | ❌ 수동 deploy |
| **버전 관리** | Git commit | Semantic Version |
| **로컬 개발** | ⚠️ 복잡 | ✅ 간단 |
| **학습 곡선** | 높음 | 낮음 (Helm 경험자) |

**보완 관계**: sbkube Registry + ArgoCD 조합 권장
- Registry: 앱 설정 버전 관리
- ArgoCD: GitOps 자동 배포

### 11.3 vs Kustomize Base

| Feature | Kustomize | sbkube Registry |
|---------|-----------|-----------------|
| **구조** | base + overlay | registry + overrides |
| **버전 관리** | Git 경로 참조 | Semantic Version |
| **Helm 통합** | ⚠️ 제한적 | ✅ 네이티브 지원 |
| **인덱스/검색** | ❌ 없음 | ✅ Registry index |
| **복잡도** | 중간 | 낮음 |

---

## 12. Future Enhancements

### 12.1 AI-powered Recommendations (AI 기반 추천)

```bash
# AI가 설정 최적화 제안
sbkube registry optimize traefik
# 출력:
# ✅ Recommendation 1: Enable HTTP/3 (performance +15%)
# ✅ Recommendation 2: Increase replicas to 3 (high availability)
# ⚠️ Warning: forwardedHeaders.insecure=true (security risk)
```

### 12.2 Drift Detection (설정 변경 감지)

```bash
# 실제 클러스터와 레지스트리 설정 비교
sbkube registry drift-detect
# 출력:
# ⚠️ Drift detected in 'traefik':
#   - Expected: deployment.replicas=3
#   - Actual: deployment.replicas=1
#   - Action: Run 'sbkube deploy' to reconcile
```

### 12.3 Multi-Registry Search (여러 레지스트리 검색)

```bash
# 여러 레지스트리에서 동시 검색
sbkube search traefik --all-registries
# 출력:
# REGISTRY           NAME     VERSION    STARS
# scripton-base      traefik  3.2.1      ⭐⭐⭐⭐⭐
# helm-official      traefik  30.0.0     ⭐⭐⭐⭐
# company-private    traefik  1.0.0      -
```

### 12.4 Compliance Validation (규정 준수 검증)

```yaml
# registry/apps/traefik/policies.yaml
policies:
  - name: security-baseline
    rules:
      - field: ports.web.forwardedHeaders.insecure
        value: false
        severity: error

  - name: observability
    rules:
      - field: logs.access.enabled
        value: true
        severity: warning

# 배포 전 자동 검증
sbkube validate --policies security-baseline,observability
```

---

## 13. Open Questions & Decisions Needed

### 13.1 스키마 버전 관리

**질문**: `apiVersion: sbkube.io/v1`를 어떻게 진화시킬 것인가?

**옵션**:
1. **Kubernetes 스타일**: `v1` → `v1beta1` → `v2`
2. **Helm 스타일**: `index.yaml`에 `apiVersion` 필드만 변경
3. **유연한 스키마**: 하위 호환성 유지하며 필드 추가

**권장**: 옵션 3 (하위 호환성 최우선)

### 13.2 Registry 네이밍

**질문**: Registry와 app을 어떻게 참조할 것인가?

**옵션**:
1. `registry/app@version` (Helm 스타일)
2. `registry:app:version` (Maven 스타일)
3. `oci://registry/app:version` (OCI 스타일)

**권장**: 옵션 1 (Helm 사용자 친화적)

### 13.3 Private Registry 인증

**질문**: Private Git/OCI registry 인증을 어떻게 처리?

**옵션**:
1. `~/.sbkube/credentials.yaml` 파일
2. 환경 변수 (`SBKUBE_REGISTRY_TOKEN`)
3. Docker credentials 재사용 (`~/.docker/config.json`)

**권장**: 옵션 2 + 옵션 3 조합

---

## 14. Conclusion

sbkube Registry는 Kubernetes 애플리케이션 관리에 **재사용성**, **버전 관리**, **표준화**를 도입하는 핵심 기능입니다.

### 14.1 Key Benefits

1. **DRY (Don't Repeat Yourself)**: 공통 설정을 한 번만 정의
2. **Semantic Versioning**: 명확한 버전 관리와 롤백
3. **Collaboration**: 팀/조직 간 설정 공유
4. **Compatibility**: 기존 sbkube 사용자 경험 유지

### 14.2 Success Metrics

- ✅ 설정 중복도 90% → 10% 감소
- ✅ 업그레이드 시간 N개 클러스터 → 1번 작업으로 단축
- ✅ 표준 준수율 100% (레지스트리 강제)
- ✅ 학습 곡선 최소화 (Helm 경험자는 즉시 사용 가능)

### 14.3 Next Steps

1. **Prototype**: Phase 1 (로컬 레지스트리) 2주 내 구현
2. **Feedback**: 2개 클러스터에서 실전 테스트
3. **Iterate**: 피드백 반영 후 Git/OCI 레지스트리 추가
4. **Stabilize**: v1.0.0 릴리스 및 문서화

---

## Appendix A: Glossary

- **Registry**: sbkube 앱 설정을 저장하는 저장소 (Local/Git/OCI)
- **App**: Kubernetes 애플리케이션 단위 (Helm/YAML/Exec)
- **Source**: 레지스트리 앱 참조 (예: `registry/app@version`)
- **Base Values**: 레지스트리에 저장된 기본 설정
- **Overrides**: 클러스터별 커스터마이징 설정
- **Digest**: 앱 설정의 SHA256 해시 (무결성 검증)

## Appendix B: References

- [Helm Chart Repository Guide](https://helm.sh/docs/topics/chart_repository/)
- [OCI Artifacts Specification](https://github.com/opencontainers/artifacts)
- [Semantic Versioning 2.0.0](https://semver.org/)
- [Kubernetes API Versioning](https://kubernetes.io/docs/reference/using-api/#api-versioning)

---

**Document Version**: 1.0.0
**Last Updated**: 2025-11-11
**Author**: Claude (Anthropic)
**Status**: Draft for Review
