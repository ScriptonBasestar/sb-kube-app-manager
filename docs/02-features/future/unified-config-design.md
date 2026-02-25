# Unified Configuration Design (sbkube.yaml)

## Overview

단일 파일 포맷 `sbkube.yaml`로 모든 설정을 통합하고, 재귀적 구조를 지원합니다.

## Current Problems

1. **파일 분리로 인한 혼란**: `sources.yaml`, `config.yaml` 역할 구분 어려움
2. **설정 위치 불명확**: 어디서 설정해야 하는지 혼란
3. **깊은 계층 미지원**: 2단계 이상의 중첩 구조 어려움
4. **설정 상속 부재**: 상위 설정을 하위에서 재사용 불가

## Design Goals

1. **단일 포맷**: 모든 레벨에서 동일한 `sbkube.yaml` 사용
2. **재귀적 구조**: 무한 중첩 지원
3. **유연한 조합**: `apps`만, `phases`만, 또는 둘 다 사용 가능
4. **설정 상속**: 상위 설정이 하위로 자동 전파 (오버라이드 가능)

## Schema Design

### Core Structure

```yaml
# sbkube.yaml - 통합 포맷
apiVersion: sbkube/v1  # 버전 명시 (선택)

# ─────────────────────────────────────────────
# Settings (모든 레벨에서 동일한 키 사용)
# ─────────────────────────────────────────────
settings:
  # Cluster configuration
  kubeconfig: ~/.kube/config
  kubeconfig_context: my-cluster

  # Namespace (하위에서 오버라이드 가능)
  namespace: default

  # Label injection
  helm_label_injection: true
  incompatible_charts: []
  force_label_injection: []

  # Deployment options
  dry_run: false
  wait: true
  timeout: "5m"
  atomic: false

  # Execution options
  parallel: false
  max_workers: 4
  on_failure: stop  # stop | continue | rollback

# ─────────────────────────────────────────────
# Apps (현재 레벨에서 직접 배포할 앱들)
# ─────────────────────────────────────────────
apps:
  nginx:
    type: helm
    chart: bitnami/nginx
    version: "15.0.0"
    # settings 오버라이드 (선택)
    settings:
      namespace: web
      timeout: "10m"

  redis:
    type: helm
    chart: bitnami/redis

# ─────────────────────────────────────────────
# Phases (하위 sbkube.yaml 참조)
# ─────────────────────────────────────────────
phases:
  infra:
    description: "Infrastructure components"
    source: ./infra  # 하위 sbkube.yaml 경로
    # settings 오버라이드 (선택)
    settings:
      namespace: infra
    depends_on: []  # Phase 간 의존성

  services:
    description: "Application services"
    source: ./services
    depends_on: [infra]
```

### Settings Inheritance

```
Level 0 (root sbkube.yaml)
├── settings: {namespace: default, timeout: 5m}
│
├── apps:
│   └── nginx: {settings: {timeout: 10m}}  # timeout만 오버라이드
│       → 최종: {namespace: default, timeout: 10m}
│
└── phases:
    └── infra:
        ├── settings: {namespace: infra}  # namespace만 오버라이드
        │   → 최종: {namespace: infra, timeout: 5m}
        │
        └── source: ./infra/sbkube.yaml
            └── apps:
                └── traefik: {}
                    → 최종: {namespace: infra, timeout: 5m}
```

### Merge Rules

| Type | Behavior | Example |
|------|----------|---------|
| `list` | Merge (dedupe) | `[a, b]` + `[b, c]` → `[a, b, c]` |
| `dict` | Deep merge | `{a: 1}` + `{b: 2}` → `{a: 1, b: 2}` |
| `scalar` | Override | `5m` + `10m` → `10m` |

### Execution Order

```
1. Load root sbkube.yaml
2. Resolve settings inheritance
3. Execute apps (if any) at current level
4. Execute phases in dependency order:
   a. Load phase's sbkube.yaml
   b. Merge parent settings
   c. Recursively execute (goto step 3)
```

## Directory Structure Examples

### Simple Project (apps only)

```
project/
└── sbkube.yaml
    apps:
      nginx: ...
      redis: ...
```

### Multi-Stage Project (phases only)

```
project/
├── sbkube.yaml
│   phases:
│     infra: {source: ./infra}
│     apps: {source: ./apps}
│
├── infra/
│   └── sbkube.yaml
│       apps:
│         traefik: ...
│         cert-manager: ...
│
└── apps/
    └── sbkube.yaml
        apps:
          api: ...
          web: ...
```

### Complex Project (mixed + nested)

```
project/
├── sbkube.yaml
│   settings:
│     namespace: production
│   apps:
│     monitoring: ...  # 루트 레벨 앱
│   phases:
│     infra: {source: ./infra}
│     services: {source: ./services}
│
├── infra/
│   └── sbkube.yaml
│       settings:
│         namespace: infra
│       apps:
│         traefik: ...
│
└── services/
    └── sbkube.yaml
        apps:
          api: ...
        phases:
          databases: {source: ./databases}
          └── databases/
              └── sbkube.yaml
                  apps:
                    postgres: ...
                    redis: ...
```

## Migration Plan

### Phase 1: Schema Definition (v0.10.0)
- [ ] Define new Pydantic models for unified schema
- [ ] Support `sbkube.yaml` file detection
- [ ] Implement settings inheritance logic

### Phase 2: Backward Compatibility (v0.10.x)
- [ ] Fallback to legacy files: `sbkube.yaml` > `sources.yaml` > `config.yaml`
- [ ] Auto-migration tool: `sbkube migrate`
- [ ] Deprecation warnings for legacy files

### Phase 3: Full Implementation (v0.11.0)
- [ ] Recursive execution engine
- [ ] Parallel phase execution
- [ ] State tracking for nested structures

### Phase 4: Legacy Removal (v1.0.0)
- [ ] Remove legacy file support
- [ ] Update all documentation
- [ ] Update all examples

## CLI Changes

```bash
# 자동 감지 (sbkube.yaml 찾기)
sbkube apply

# 명시적 파일 지정
sbkube apply -f ./custom/sbkube.yaml

# 특정 phase만 실행
sbkube apply --phase infra

# 특정 app만 실행
sbkube apply --app nginx

# 마이그레이션
sbkube migrate  # legacy config + sources.yaml → sbkube.yaml
```

## Settings Reference

| Key | Type | Default | Description |
|-----|------|---------|-------------|
| **Cluster** |
| `kubeconfig` | string | - | Kubeconfig file path |
| `kubeconfig_context` | string | - | Kubectl context name |
| `namespace` | string | `default` | Default namespace |
| **Label Injection** |
| `helm_label_injection` | bool | `true` | Enable label injection |
| `incompatible_charts` | list | `[]` | Charts to disable injection |
| `force_label_injection` | list | `[]` | Override incompatible list |
| **Deployment** |
| `dry_run` | bool | `false` | Dry-run mode |
| `wait` | bool | `true` | Wait for resources ready |
| `timeout` | string | `5m` | Deployment timeout |
| `atomic` | bool | `false` | Atomic deployment |
| **Execution** |
| `execution_order` | string | `apps_first` | `apps_first` or `phases_first` |
| `parallel` | bool | `false` | Parallel phase execution |
| `parallel_apps` | bool | `false` | Parallel app execution within phase |
| `max_workers` | int | `4` | Max parallel workers |
| **Failure Handling** |
| `on_failure` | string | `stop` | `stop`, `continue`, or `rollback` |
| `rollback_scope` | string | `app` | `app`, `phase`, or `all` |

## Design Decisions

### 1. apps + phases 실행 순서
**결정**: 설정 가능 (`execution_order`), 기본값 `apps_first`

```yaml
settings:
  execution_order: apps_first  # apps_first | phases_first
```

- `apps_first` (기본): 현재 레벨 apps 실행 → phases 실행
- `phases_first`: phases 먼저 실행 → 현재 레벨 apps 실행

### 2. Phase 내 app 병렬 실행
**결정**: `parallel_apps` 옵션 지원, 기본값 `false`

```yaml
settings:
  parallel_apps: true   # Phase 내 apps 병렬 실행
  max_workers: 4        # 최대 병렬 워커 수
```

### 3. Cross-phase 의존성
**결정**: Phase 간 의존성만 지원 (단순)

```yaml
phases:
  infra:
    source: ./infra
  services:
    source: ./services
    depends_on: [infra]  # Phase 간 의존성만
```

복잡한 의존성이 필요한 경우 → 순차적 phase로 분리:
```yaml
phases:
  step1:
    source: ./step1
  step2:
    source: ./step2
    depends_on: [step1]
  step3:
    source: ./step3
    depends_on: [step2]
```

### 4. 롤백 범위
**결정**: 선택 가능 (`rollback_scope`), 기본값 `app`

```yaml
settings:
  rollback_scope: app  # app | phase | all
  on_failure: rollback  # stop | continue | rollback
```

- `app` (기본): 실패한 app만 롤백
- `phase`: 실패한 phase 전체 롤백
- `all`: 전체 배포 롤백

## References

- Current multi-phase design: unified `sbkube.yaml` phases model
- Current sources schema: [sources_model.py](../../../sbkube/models/sources_model.py)
- Current config schema: [config_model.py](../../../sbkube/models/config_model.py)
