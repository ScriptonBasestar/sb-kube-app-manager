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
