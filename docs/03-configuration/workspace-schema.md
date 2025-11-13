______________________________________________________________________

## type: API Reference
audience: End User
topics: [workspace, configuration, schema, yaml, multi-phase, orchestration]
llm_priority: high
last_updated: 2025-01-13

# 📋 workspace.yaml Schema Guide

> **Status**: DESIGN RESOLVED - Implementation pending (v0.9.0)

> **주의**: 이 문서는 [workspace-design.md](../02-features/future/workspace-design.md)의 사용자 가이드 버전입니다. 설계 결정 및 기술적 상세는 design 문서를 참조하세요.

## TL;DR

- **Purpose**: Multi-phase deployment orchestration schema reference
- **Version**: v1.0 (설계 완료, 구현 대기)
- **Key Points**:
  - Orchestrates multiple phases (p1-infra, p2-data, p3-app)
  - Each phase references independent `sources.yaml`
  - Sequential execution with dependency management
  - Support for single-cluster deployment (v1.0)
  - Multi-cluster support planned (v1.1+)
- **Quick Reference**: See "📂 File Structure Overview" for basic structure
- **Related**:
  - **설계 문서**: [workspace-design.md](../02-features/future/workspace-design.md) - Design decisions
  - **구현 계획**: [workspace-roadmap.md](../02-features/future/workspace-roadmap.md) - Implementation plan
  - **Sources 설정**: [sources-schema.md](sources-schema.md) - `sources.yaml` schema
  - **Config 설정**: [config-schema.md](config-schema.md) - `config.yaml` schema
  - **상위 문서**: [SPEC.md](../../SPEC.md) - Technical specification

Multi-phase deployment를 위한 `workspace.yaml` 설정 파일의 완전한 스키마 문서입니다.

> **Use Case**:
>
> - p1-kube, p2-kube, p3-kube처럼 단계별로 나뉜 프로젝트 구조 지원
> - Infrastructure → Data → Application 순차 배포
> - Phase 간 명시적 의존성 관리

______________________________________________________________________

## 🚀 Quick Start

**5분 안에 workspace 시작하기**:

### 1. 프로젝트 구조 준비

```bash
# 프로젝트 디렉토리 구조
mkdir -p p1-kube/a000_network p2-kube/a100_postgres
```

### 2. workspace.yaml 생성

```yaml
# workspace.yaml
version: "1.0"

metadata:
  name: my-first-workspace

phases:
  p1-infra:
    description: "Infrastructure"
    source: p1-kube/sources.yaml
    app_groups:
      - a000_network
    depends_on: []

  p2-data:
    description: "Database"
    source: p2-kube/sources.yaml
    app_groups:
      - a100_postgres
    depends_on:
      - p1-infra
```

### 3. 각 Phase의 sources.yaml 생성

```bash
# p1-kube/sources.yaml
cat > p1-kube/sources.yaml <<EOF
kubeconfig: ~/.kube/config
kubeconfig_context: production-cluster
helm_repos:
  cilium:
    url: https://helm.cilium.io/
EOF

# p2-kube/sources.yaml
cat > p2-kube/sources.yaml <<EOF
kubeconfig: ~/.kube/config
kubeconfig_context: production-cluster
helm_repos:
  bitnami:
    url: https://charts.bitnami.com/bitnami
EOF
```

### 4. 검증 및 배포 (v0.9.0+)

```bash
# 설정 검증
sbkube workspace validate -f workspace.yaml

# 전체 배포
sbkube workspace deploy -f workspace.yaml

# 또는 특정 phase만
sbkube workspace deploy -f workspace.yaml --phase p1-infra
```

**다음 단계**: 아래 Complete Example 참조하여 더 복잡한 구조 구축

______________________________________________________________________

## 📂 File Structure Overview

```yaml
# workspace.yaml 기본 구조
version: "1.0"                    # 스키마 버전 (필수)

metadata:                         # 워크스페이스 메타데이터 (필수)
  name: string                    # 워크스페이스 이름 (필수)
  description: string             # 설명 (선택)
  environment: string             # 환경 라벨 (선택)
  tags: [string]                  # 태그 (선택)

global:                           # 전역 기본값 (선택)
  kubeconfig: string              # 기본 kubeconfig 경로
  context: string                 # 기본 kubectl context
  helm_repos: {...}               # 전역 Helm 리포지토리
  timeout: number                 # 기본 타임아웃 (초)
  on_failure: enum                # 실패 시 동작 (stop/continue/rollback)

phases:                           # Phase 정의 (필수)
  phase-name:                     # Phase 이름 (key)
    description: string           # Phase 설명 (필수)
    source: string                # sources.yaml 경로 (필수)
    app_groups: [string]          # 배포할 앱 그룹 목록 (필수)
    depends_on: [string]          # 의존하는 Phase 목록 (선택)
    timeout: number               # Phase별 타임아웃 (선택)
    on_failure: enum              # Phase별 실패 동작 (선택)
    env: {string: string}         # Phase별 환경변수 (선택)
```

**핵심 개념**:

- **Workspace**: 여러 Phase를 포함하는 최상위 배포 단위
- **Phase**: 독립적인 배포 단계 (예: infra, data, app)
- **sources.yaml**: 각 Phase가 참조하는 클러스터 및 리포지토리 설정
- **app_groups**: Phase 내에서 배포할 앱 그룹 목록

______________________________________________________________________

## 🌐 Global Configuration (Optional)

전체 Phase에 적용되는 기본값 설정입니다. 각 Phase의 `sources.yaml`에서 override 가능합니다.

### version (string, 필수)

Workspace 스키마 버전입니다.

```yaml
version: "1.0"
```

**규칙**:
- Semantic versioning 형식
- 현재 버전: `"1.0"` (v0.9.0 목표)
- 문자열로 표기 (따옴표 필수)

### metadata (object, 필수)

Workspace 메타데이터입니다.

```yaml
metadata:
  name: production-deployment
  description: "Production infrastructure and application deployment"
  environment: prod
  tags:
    - production
    - multi-phase
```

**필드**:
- `name` (string, 필수): Workspace 식별자 (alphanumeric + dash/underscore)
- `description` (string, 선택): 사람이 읽을 수 있는 설명
- `environment` (string, 선택): 환경 라벨 (dev, staging, prod 등)
- `tags` (list[string], 선택): 분류를 위한 태그 목록

### global.kubeconfig (string, 선택)

모든 Phase에 적용될 기본 kubeconfig 파일 경로입니다.

```yaml
global:
  kubeconfig: ~/.kube/config
```

**우선순위**:
1. Phase의 `sources.yaml`에 정의된 kubeconfig (최우선)
2. Workspace의 `global.kubeconfig`
3. 환경변수 `$KUBECONFIG`
4. 기본값: `~/.kube/config`

### global.context (string, 선택)

모든 Phase에 적용될 기본 kubectl context입니다.

```yaml
global:
  context: production-cluster
```

**권장사항**: Phase별로 다른 context를 사용하는 경우, 각 Phase의 `sources.yaml`에서 명시적으로 설정하는 것이 명확합니다.

### global.helm_repos (map[string, object], 선택)

전역 Helm 리포지토리 정의입니다.

```yaml
global:
  helm_repos:
    bitnami:
      url: https://charts.bitnami.com/bitnami
    prometheus-community:
      url: https://prometheus-community.github.io/helm-charts
```

**우선순위 규칙**:
1. App-level (config.yaml의 `chart: repo/name`) - 최우선
2. Phase-level (sources.yaml의 `helm_repos`)
3. Workspace-level (global.helm_repos) - 최하위

### global.timeout (number, 선택)

기본 작업 타임아웃 (초 단위)입니다.

```yaml
global:
  timeout: 600  # 10분
```

**규칙**:
- 초 단위 (seconds)
- Phase별 override 가능
- 기본값: 600초 (10분)

### global.on_failure (enum, 선택)

Phase 실패 시 동작을 정의합니다.

```yaml
global:
  on_failure: stop  # stop, continue, rollback
```

**옵션**:
- `stop`: 실패 즉시 중단 (기본값)
- `continue`: 실패해도 다음 Phase 계속 진행
- `rollback`: 실패 시 자동 롤백 (v1.1+)

______________________________________________________________________

## 📦 Phase Configuration (Required)

각 Phase는 독립적인 배포 단계를 나타냅니다.

### Phase 기본 구조

```yaml
phases:
  p1-infra:
    description: "Network and storage infrastructure"
    source: p1-kube/sources.yaml
    app_groups:
      - a000_network
      - a001_storage
    depends_on: []
```

### phase-name (key, 필수)

Phase의 고유 식별자입니다.

**규칙**:
- Workspace 내에서 고유해야 함
- Alphanumeric + dash/underscore 사용 권장
- 네이밍 컨벤션: `p[숫자]-[역할]` (예: p1-infra, p2-data, p3-app)

### description (string, 필수)

Phase의 사람이 읽을 수 있는 설명입니다.

```yaml
description: "Database and caching layer"
```

### source (string, 필수)

이 Phase가 사용할 `sources.yaml` 파일의 경로입니다.

```yaml
source: p2-kube/sources.yaml
```

**규칙**:
- `workspace.yaml`을 기준으로 한 상대 경로
- 파일이 존재해야 함 (validation 시 확인)
- 각 Phase는 독립적인 `sources.yaml` 사용 가능

**예시**:
```
project/
├── workspace.yaml
├── p1-kube/
│   ├── sources.yaml          # Phase p1-infra가 참조
│   └── config.yaml
├── p2-kube/
│   ├── sources.yaml          # Phase p2-data가 참조
│   └── config.yaml
```

### app_groups (list[string], 필수)

이 Phase에서 배포할 앱 그룹 목록입니다.

```yaml
app_groups:
  - a100_postgres
  - a101_redis
```

**규칙**:
- `source`에 정의된 `sources.yaml`과 같은 디렉토리에 있는 앱 그룹 디렉토리명
- 순서대로 배포됨
- 앱 그룹 디렉토리가 실제로 존재해야 함 (validation 시 확인)

**예시**:
```
p2-kube/
├── sources.yaml
├── a100_postgres/
│   └── config.yaml
└── a101_redis/
    └── config.yaml
```

### depends_on (list[string], 선택)

이 Phase가 의존하는 다른 Phase 목록입니다.

```yaml
depends_on:
  - p1-infra
```

**규칙**:
- Phase 이름(key) 참조
- 의존하는 Phase가 먼저 완료되어야 이 Phase 시작
- 순환 의존성 금지 (validation 시 DFS로 검출)
- 비어있으면 (또는 생략하면) 의존성 없음

**Validation**:
- 존재하지 않는 Phase 참조 시 오류
- 순환 의존성 발견 시 오류

### timeout (number, 선택)

이 Phase의 타임아웃 (초 단위)입니다.

```yaml
timeout: 900  # 15분
```

**규칙**:
- `global.timeout` override
- 이 Phase의 모든 app group 배포 시간 합산

### on_failure (enum, 선택)

이 Phase 실패 시 동작입니다.

```yaml
on_failure: stop  # stop, continue, rollback
```

**규칙**: `global.on_failure`와 동일한 옵션

### env (map[string, string], 선택)

Phase별 환경변수입니다.

```yaml
env:
  DB_NAMESPACE: databases
  POSTGRES_VERSION: "15"
```

**사용**:
- Hooks 스크립트에서 참조 가능
- 앱 배포 시 환경변수로 전달

### parallel (boolean, 선택) 🔮 v1.1+

Phase 내 앱 그룹의 병렬 배포를 활성화합니다.

```yaml
parallel: true
```

**규칙**:
- `true`: 앱 그룹 간 의존성이 없으면 병렬로 배포
- `false` (기본값): 순차 배포
- **v1.0 제한**: v1.0에서는 항상 순차 배포 (이 옵션 무시됨)
- **v1.1+ 계획**: 병렬 배포 지원

**예시** (v1.1+):
```yaml
p2-data:
  parallel: true
  app_groups:
    - a100_postgres  # 병렬 시작
    - a101_redis     # 병렬 시작
```

### wait_for_ready (boolean, 선택) 🔮 v1.1+

의존하는 Phase가 완전히 준비 상태가 될 때까지 대기합니다.

```yaml
wait_for_ready: true
```

**규칙**:
- `true`: Phase 배포 완료 + readiness check 통과까지 대기
- `false` (기본값): Phase 배포 완료만 확인
- **v1.0 제한**: v1.0에서는 배포 완료만 확인
- **v1.1+ 계획**: Readiness check 지원

**차이점**:
```yaml
# wait_for_ready: false (기본)
- p1-infra 배포 완료 → p2-data 즉시 시작

# wait_for_ready: true (v1.1+)
- p1-infra 배포 완료 → Pod readiness 확인 → p2-data 시작
```

### rollback (object, 선택) 🔮 v1.1+

Phase별 롤백 전략을 정의합니다.

```yaml
rollback:
  enabled: true
  auto: false  # Manual approval required
```

**필드**:
- `enabled` (boolean): 롤백 기능 활성화 여부
- `auto` (boolean): 실패 시 자동 롤백 여부
  - `true`: 자동 롤백
  - `false`: 수동 승인 필요

**v1.0 vs v1.1+**:
- **v1.0**: `on_failure: stop/continue` 만 지원
- **v1.1+**: `rollback` 블록으로 세밀한 제어

**on_failure와의 관계**:
```yaml
# Option 1: 즉시 중단
on_failure: stop

# Option 2: 계속 진행
on_failure: continue

# Option 3: 롤백 (v1.1+)
on_failure: stop
rollback:
  enabled: true
  auto: true  # 자동 롤백
```

______________________________________________________________________

## 🔗 Phase Dependency Resolution

Phase 간 의존성은 Kahn's algorithm으로 해결됩니다.

### 예시 1: 순차 배포

```yaml
phases:
  p1-infra:
    depends_on: []

  p2-data:
    depends_on:
      - p1-infra

  p3-app:
    depends_on:
      - p2-data
```

**실행 순서**: p1-infra → p2-data → p3-app

### 예시 2: 병렬 가능

```yaml
phases:
  p1-infra:
    depends_on: []

  p2-database:
    depends_on:
      - p1-infra

  p2-cache:
    depends_on:
      - p1-infra

  p3-app:
    depends_on:
      - p2-database
      - p2-cache
```

**실행 순서**:
1. p1-infra
2. p2-database, p2-cache (병렬 가능, v1.0에서는 순차)
3. p3-app

### 예시 3: 순환 의존성 (오류)

```yaml
phases:
  p1-infra:
    depends_on:
      - p2-data    # ❌ 순환 참조

  p2-data:
    depends_on:
      - p1-infra   # ❌ 순환 참조
```

**결과**: Validation 오류 (DFS로 검출)

______________________________________________________________________

## 🎯 Complete Example

### 프로덕션 3-Phase 배포

```yaml
# workspace.yaml
version: "1.0"

metadata:
  name: production-deployment
  description: "Full production stack deployment"
  environment: prod
  tags:
    - production
    - multi-phase

global:
  kubeconfig: ~/.kube/config
  context: production-cluster
  helm_repos:
    bitnami:
      url: https://charts.bitnami.com/bitnami
  timeout: 600
  on_failure: stop

phases:
  p1-infra:
    description: "Network and storage infrastructure"
    source: p1-kube/sources.yaml
    app_groups:
      - a000_network
      - a001_storage
    depends_on: []
    timeout: 900
    env:
      INFRA_NAMESPACE: infrastructure
      STORAGE_CLASS: standard

  p2-data:
    description: "Database and caching layer"
    source: p2-kube/sources.yaml
    app_groups:
      - a100_postgres
      - a101_redis
    depends_on:
      - p1-infra
    env:
      DB_NAMESPACE: databases
      POSTGRES_VERSION: "15"

  p3-app:
    description: "Application services"
    source: p3-kube/sources.yaml
    app_groups:
      - a200_backend
      - a201_frontend
    depends_on:
      - p2-data
    on_failure: rollback
```

### 디렉토리 구조

```
project/
├── workspace.yaml
├── p1-kube/
│   ├── sources.yaml
│   ├── a000_network/
│   │   └── config.yaml
│   └── a001_storage/
│       └── config.yaml
├── p2-kube/
│   ├── sources.yaml
│   ├── a100_postgres/
│   │   └── config.yaml
│   └── a101_redis/
│       └── config.yaml
└── p3-kube/
    ├── sources.yaml
    ├── a200_backend/
    │   └── config.yaml
    └── a201_frontend/
        └── config.yaml
```

______________________________________________________________________

## 💡 Best Practices

### Phase 분할 전략

**권장 Phase 구조**:

1. **p1-infra** (Infrastructure): 기반 인프라
   - Network (CNI: Cilium, Calico)
   - Storage (NFS, Ceph)
   - Ingress Controller
   - Cert Manager

2. **p2-data** (Data Layer): 데이터 계층
   - Database (PostgreSQL, MySQL)
   - Cache (Redis, Memcached)
   - Message Queue (RabbitMQ, Kafka)

3. **p3-app** (Application): 애플리케이션
   - Backend Services
   - Frontend Services
   - APIs

4. **p4-monitoring** (Optional): 관측성
   - Prometheus
   - Grafana
   - Loki
   - Alert Manager

### 네이밍 규칙

**Phase 네이밍**:
```yaml
# 권장: p[숫자]-[역할]
p1-infra        # ✅ 명확한 순서와 역할
p2-data         # ✅
p3-app          # ✅

# 비권장
infrastructure  # ❌ 순서 불명확
phase1          # ❌ 역할 불명확
```

**App Group 네이밍**:
```yaml
# 권장: a[숫자]_[역할]
a000_network    # ✅ 순서와 역할 명확
a001_storage    # ✅
a100_postgres   # ✅

# 비권장
network         # ❌ 순서 불명확
```

### Timeout 설정 가이드

**Phase별 권장 timeout** (초 단위):

```yaml
phases:
  p1-infra:
    timeout: 900     # 15분 - 네트워크 초기화 시간 필요

  p2-data:
    timeout: 1200    # 20분 - 데이터베이스 초기화 시간

  p3-app:
    timeout: 600     # 10분 - 일반 앱 배포

  p4-monitoring:
    timeout: 600     # 10분
```

**경험 법칙**:
- 기본: 600초 (10분)
- Network/Storage: 900-1200초 (15-20분)
- Database: 1200-1800초 (20-30분)
- 단순 App: 300-600초 (5-10분)

### 의존성 관리 원칙

**1. 명시적 의존성**:
```yaml
# ✅ 명확한 의존성 표현
phases:
  p2-data:
    depends_on:
      - p1-infra  # Infrastructure 먼저 필요함을 명시
```

**2. 최소 의존성**:
```yaml
# ✅ 꼭 필요한 의존성만
phases:
  p3-app:
    depends_on:
      - p2-data     # DB 의존성만 명시
    # p1-infra는 p2-data에 의해 간접적으로 보장됨
```

**3. 과도한 의존성 피하기**:
```yaml
# ❌ 불필요한 의존성
phases:
  p4-monitoring:
    depends_on:
      - p1-infra
      - p2-data
      - p3-app     # 모든 것에 의존 - 과도함

# ✅ 필요한 의존성만
phases:
  p4-monitoring:
    depends_on:
      - p3-app     # p3-app만 있으면 충분 (간접 의존)
```

### 환경별 관리

**개발/스테이징/프로덕션 분리**:

```bash
# 환경별 workspace 파일 사용
workspace-dev.yaml
workspace-staging.yaml
workspace-prod.yaml
```

**또는 metadata로 구분**:
```yaml
# workspace-prod.yaml
metadata:
  name: production-deployment
  environment: prod

global:
  kubeconfig: ~/.kube/prod-config
  context: production-cluster
```

### 테스트 전략

**점진적 테스트**:

1. **단일 Phase 테스트**:
   ```bash
   sbkube workspace deploy -f workspace.yaml --phase p1-infra
   ```

2. **의존성 체인 테스트**:
   ```bash
   # p1 → p2 순서 확인
   sbkube workspace deploy -f workspace.yaml --phase p2-data
   ```

3. **전체 테스트**:
   ```bash
   sbkube workspace deploy -f workspace.yaml
   ```

**Dry-run 활용**:
```bash
# 실제 배포 전 검증
sbkube workspace validate -f workspace.yaml
sbkube workspace deploy -f workspace.yaml --dry-run
```

### 문제 해결 팁

**Phase 실패 시**:
```bash
# 1. 현재 상태 확인
sbkube workspace status -f workspace.yaml

# 2. 실패한 phase만 재배포
sbkube workspace deploy -f workspace.yaml --phase p2-data

# 3. 전체 재배포 (필요시)
sbkube workspace deploy -f workspace.yaml --force
```

**디버깅**:
```bash
# Verbose 모드로 상세 로그 확인
sbkube workspace deploy -f workspace.yaml --verbose

# 특정 app group만 테스트
cd p2-kube && sbkube apply -c sources.yaml -g a100_postgres
```

______________________________________________________________________

## 🔧 CLI Commands (v0.9.0 목표)

### Workspace 배포

```bash
# 전체 workspace 배포
sbkube workspace deploy -f workspace.yaml

# 특정 phase만 배포
sbkube workspace deploy -f workspace.yaml --phase p2-data

# Dry-run (검증만)
sbkube workspace deploy -f workspace.yaml --dry-run
```

### Workspace 검증

```bash
# 설정 검증
sbkube workspace validate -f workspace.yaml

# 검증 내용:
# - Phase 정의 유효성
# - sources.yaml 파일 존재 확인
# - app_groups 디렉토리 존재 확인
# - 순환 의존성 검출
# - Cluster 접근 가능성 (optional)
```

### Workspace 상태 조회

```bash
# 전체 상태
sbkube workspace status -f workspace.yaml

# 특정 phase 상태
sbkube workspace status -f workspace.yaml --phase p1-infra
```

### Workspace 롤백 (v1.1+)

```bash
# 특정 phase 롤백
sbkube workspace rollback -f workspace.yaml --phase p3-app
```

______________________________________________________________________

## 🚨 Validation Rules

Workspace 배포 전 다음 사항이 자동으로 검증됩니다:

### 파일 존재성 검증

- ✅ 모든 Phase의 `source` 파일이 존재하는가?
- ✅ 모든 `app_groups` 디렉토리가 존재하는가?

### 의존성 검증

- ✅ `depends_on`에 명시된 Phase가 실제로 존재하는가?
- ✅ 순환 의존성이 없는가? (DFS)

### 네이밍 검증

- ✅ Phase 이름이 고유한가?
- ✅ Phase 이름이 유효한 식별자인가?

### 클러스터 접근성 검증 (Optional)

- ⚠️ 각 Phase의 `sources.yaml`에 정의된 클러스터 접근 가능한가?

______________________________________________________________________

## 🔄 Migration from Current SBKube Workflow

### Before (Single Phase)

```bash
cd p1-kube/
sbkube apply -c sources.yaml
```

### After (Workspace)

```bash
# Option 1: 전체 배포
sbkube workspace deploy -f workspace.yaml

# Option 2: Phase별 배포 (기존과 유사)
sbkube workspace deploy -f workspace.yaml --phase p1-infra
```

### Backward Compatibility

- ✅ 기존 워크플로우는 그대로 작동
- ✅ `workspace.yaml`은 선택사항 (multi-phase 필요 시에만)
- ✅ `sources.yaml`, `config.yaml` 포맷 변경 없음
- ✅ 기존 명령어 (`sbkube apply`) 그대로 사용 가능

______________________________________________________________________

## 📚 Related Documentation

- **설계 문서**: [workspace-design.md](../02-features/future/workspace-design.md)
- **구현 계획**: [workspace-roadmap.md](../02-features/future/workspace-roadmap.md)
- **Sources 스키마**: [sources-schema.md](sources-schema.md)
- **Config 스키마**: [config-schema.md](config-schema.md)
- **SPEC.md**: [../../SPEC.md](../../SPEC.md)
- **PRODUCT.md**: [../../PRODUCT.md](../../PRODUCT.md)

______________________________________________________________________

## 🎯 Future Enhancements (v1.1+)

### Multi-Cluster Support

```yaml
phases:
  p1-infra-us:
    source: us-cluster/sources.yaml    # US cluster
    app_groups: [...]

  p1-infra-eu:
    source: eu-cluster/sources.yaml    # EU cluster
    app_groups: [...]
```

### Parallel Phase Execution

```yaml
phases:
  p2-database:
    parallel: true  # Enable parallel deployment within phase
    app_groups:
      - postgres
      - mysql
```

### Conditional Phase Execution

```yaml
phases:
  p3-canary:
    condition: "{{ .Values.canary_enabled }}"
    app_groups: [...]
```

______________________________________________________________________

**Document Version**: 1.0
**Status**: DESIGN RESOLVED (Implementation pending)
**Target Version**: v0.9.0
