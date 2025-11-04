---
type: Internal Planning
audience: Developer
topics: [planning, roadmap, hooks]
llm_priority: low
exclude_from_context: true
last_updated: 2025-01-04
---

# Hooks 시스템 개선 (Phase 1-4)

> **최종 업데이트**: 2025-10-31 (Phase 3 완료) **현재 구현 상태**: Phase 1, 2, 3 완료 (v0.9.0+)

## 개요

SBKube의 hooks 시스템을 "shell 명령어 실행기"에서 "sbkube의 1급 기능"으로 개선하는 4단계 계획입니다.

______________________________________________________________________

## 📋 Phase 별 개요

| Phase | 기능 | 복잡도 | 효과 | 상태 | 버전 | |-------|------|-------|------|------|------| | Phase 1 | Manifests 지원 | 낮음 | 중간 | ✅
완료 | v0.7.0 | | Phase 2 | Type System | 중간 | 높음 | ✅ 완료 | v0.8.0 | | Phase 3 | Validation & Dependency | 높음 | 매우 높음 | ✅
완료 | v0.9.0 | | Phase 4 | Hook as App | 매우 높음 | 낮음 | 📝 계획 | v1.0.0? |

______________________________________________________________________

## ❌ 기존 Hooks의 문제점

### 1. Shell 명령어 직접 실행

```yaml
apps:
  cert-manager:
    type: helm
    chart: jetstack/cert-manager
    hooks:
      post_deploy:
        - kubectl apply -f manifests/issuer1.yaml
        - kubectl apply -f manifests/issuer2.yaml
```

**문제**:

- kubectl 직접 호출 → sbkube가 상태 추적 불가
- 검증 및 롤백 불가
- 실패 시 디버깅 어려움
- YAML 파일 관리 여전히 필요

### 2. Manifests 미지원

hooks는 명령어 문자열 리스트만 받음:

```python
post_deploy: list[str]  # Shell 명령어만
```

YAML 파일 경로 리스트를 직접 받을 수 없음.

### 3. 검증 부재

- pre/post 검증 없음
- 실패 시 상태 불명확
- `on_deploy_failure`가 있지만 복구 로직 없음

______________________________________________________________________

## ✅ Phase 1: Manifests 지원 (v0.7.0)

### 목표

Shell 명령어 대신 **YAML manifests를 직접 받아 YamlApp처럼 처리**

### 구현 내용

#### 1. AppHooks 모델 확장

**파일**: `sbkube/models/config_model.py`

```python
class AppHooks(ConfigBaseModel):
    # 기존 (Shell 명령어)
    pre_deploy: list[str] = Field(default_factory=list)
    post_deploy: list[str] = Field(default_factory=list)

    # 신규 (Manifests) - Phase 1
    pre_deploy_manifests: list[str] = Field(
        default_factory=list,
        description="deploy 실행 전 배포할 YAML manifests"
    )
    post_deploy_manifests: list[str] = Field(
        default_factory=list,
        description="deploy 실행 후 배포할 YAML manifests"
    )
```

#### 2. HookExecutor 확장

**파일**: `sbkube/utils/hook_executor.py`

```python
class HookExecutor:
    def __init__(
        self,
        base_dir: Path,
        kubeconfig: str | None = None,
        context: str | None = None,
        namespace: str | None = None,
        # ...
    ):
        # kubectl 실행을 위한 클러스터 설정 저장
        self.kubeconfig = kubeconfig
        self.context = context
        self.namespace = namespace

    def execute_app_hook_with_manifests(
        self,
        app_name: str,
        app_hooks: dict | None,
        hook_type: HookType,
        context: dict | None = None,
    ) -> bool:
        """Shell 명령어 + Manifests 모두 실행"""
        # 1. Shell 명령어 hooks 실행 (기존)
        if hook_type in app_hooks:
            self.execute_app_hook(...)

        # 2. Manifests hooks 실행 (신규)
        manifests_hook_type = f"{hook_type}_manifests"
        if manifests_hook_type in app_hooks:
            self._deploy_manifests(...)

    def _deploy_manifests(
        self,
        app_name: str,
        manifests: list[str],
        namespace: str | None = None,
    ) -> bool:
        """
        Manifests 파일 배포 (kubectl apply).

        YamlApp 배포 로직과 유사하게 처리:
        - 상대 경로는 work_dir 기준
        - kubectl apply -f 실행
        - namespace 자동 적용
        - 상태 추적
        """
```

#### 3. deploy 명령어 통합

**파일**: `sbkube/commands/deploy.py`

```python
# HookExecutor 초기화 시 클러스터 설정 전달
hook_executor = HookExecutor(
    base_dir=BASE_DIR,
    work_dir=APP_CONFIG_DIR,
    dry_run=dry_run,
    kubeconfig=kubeconfig,  # 추가
    context=context,        # 추가
    namespace=namespace,    # 추가
)

# 기존 execute_app_hook 대신 execute_app_hook_with_manifests 사용
hook_executor.execute_app_hook_with_manifests(
    app_name=app_name,
    app_hooks=app_hooks,
    hook_type="post_deploy",
    context=hook_context,
)
```

### 사용 예제

#### 기존 방식 (kubectl 직접 호출)

```yaml
apps:
  cert-manager:
    type: helm
    chart: jetstack/cert-manager
    hooks:
      post_deploy:
        - kubectl apply -f manifests/issuers/cluster-issuer-letsencrypt-prd.yaml
        - kubectl apply -f manifests/issuers/cluster-issuer-letsencrypt-stg.yaml
```

#### Phase 1 (Manifests 지원)

```yaml
apps:
  cert-manager:
    type: helm
    chart: jetstack/cert-manager
    hooks:
      post_deploy_manifests:
        - manifests/issuers/cluster-issuer-letsencrypt-prd.yaml
        - manifests/issuers/cluster-issuer-letsencrypt-stg.yaml
```

### 효과

- ✅ kubectl 직접 호출 불필요
- ✅ sbkube가 YamlApp처럼 처리 → 상태 추적
- ✅ 검증 및 롤백 가능
- ✅ namespace 자동 적용
- ✅ 상세 로깅

______________________________________________________________________

## 📋 Phase 2: Type System (v0.8.0 계획)

### 목표

여러 hook 타입을 명시적으로 지원:

- `type: manifests` - YAML 파일 배포
- `type: inline` - 인라인 YAML 콘텐츠
- `type: command` - Shell 명령어 (개선된)

### 예상 사용법

```yaml
apps:
  cert-manager:
    type: helm
    chart: jetstack/cert-manager
    hooks:
      post_deploy:
        # 타입 1: Manifests
        - type: manifests
          name: deploy-issuers
          files:
            - manifests/issuers/cluster-issuer-letsencrypt-prd.yaml
            - manifests/issuers/cluster-issuer-letsencrypt-stg.yaml
          validation:
            kind: ClusterIssuer
            wait_for_ready: true

        # 타입 2: Inline
        - type: inline
          name: create-certificate
          content:
            apiVersion: cert-manager.io/v1
            kind: Certificate
            metadata:
              name: wildcard-cert
            spec:
              secretName: wildcard-cert-tls
              issuerRef:
                name: letsencrypt-prd
                kind: ClusterIssuer

        # 타입 3: Command (개선된)
        - type: command
          name: verify-dns
          command: |
            dig +short letsencrypt.example.com @8.8.8.8
          retry:
            max_attempts: 3
            delay: 5s
          on_failure: warn
```

______________________________________________________________________

## 🔍 Phase 3: Validation & Dependency (✅ v0.9.0 완료)

### 목표 (달성!)

Hooks를 sbkube 워크플로우에 완전히 통합:

- ✅ Task 실행 후 검증 (validation)
- ✅ Task 간 의존성 관리 (dependency)
- ✅ 실패 시 자동 롤백 (rollback)

### 구현된 기능

#### 1. Validation

Task 실행 후 리소스 상태를 자동으로 검증:

```yaml
post_deploy_tasks:
  - type: manifests
    name: deploy-issuers
    files:
      - manifests/issuers/cluster-issuer-letsencrypt-prd.yaml
    validation:
      kind: ClusterIssuer              # 검증할 리소스 Kind
      name: letsencrypt-prd            # 리소스 이름 (optional)
      wait_for_ready: true             # Ready 상태 대기
      timeout: 120                     # 타임아웃 (초)
      conditions:                      # 검증할 Condition (optional)
        - type: Ready
          status: "True"
```

**동작**:

- `wait_for_ready: true` → `kubectl wait --for=condition=Ready` 실행
- 타임아웃 내에 조건 만족 안 되면 **실패** → rollback 실행

#### 2. Dependency

Task 간 실행 순서 보장 및 외부 리소스 대기:

```yaml
post_deploy_tasks:
  - type: inline
    name: create-certificate
    content:
      apiVersion: cert-manager.io/v1
      kind: Certificate
      # ...
    dependency:
      # Task 간 순서 보장
      depends_on:
        - deploy-issuers
      # 외부 리소스 대기
      wait_for:
        - kind: Pod
          label_selector: "app=cert-manager"
          condition: Ready
          timeout: 180
```

**동작**:

- `depends_on`: 명시된 task가 먼저 완료되어야 실행 가능
- `wait_for`: `kubectl wait` 명령어로 외부 리소스 조건 대기

#### 3. Rollback

Task 실패 시 자동 정리:

```yaml
post_deploy_tasks:
  - type: manifests
    name: deploy-issuers
    files:
      - manifests/issuers/cluster-issuer-letsencrypt-prd.yaml
    rollback:
      enabled: true                    # 롤백 활성화
      on_failure: always               # 실패 시 롤백 실행 (always, manual, never)
      manifests:                       # 롤백 시 적용할 manifests (optional)
        - manifests/cleanup-issuers.yaml
      commands:                        # 롤백 시 실행할 명령어 (optional)
        - kubectl delete clusterissuer letsencrypt-prd --ignore-not-found=true
        - kubectl delete clusterissuer letsencrypt-stg --ignore-not-found=true
```

**동작**:

- Task 실행 실패 또는 Validation 실패 시 자동 롤백
- `on_failure: always` → 자동 롤백
- `on_failure: manual` → 수동 확인 (현재는 스킵)
- `on_failure: never` → 롤백 비활성화

### 실제 사용 예제

`examples/hooks-phase3/config.yaml`:

```yaml
namespace: cert-manager

apps:
  cert-manager:
    type: helm
    chart: jetstack/cert-manager
    hooks:
      post_deploy_tasks:
        # Step 1: ClusterIssuer 배포
        - type: manifests
          name: deploy-cluster-issuers
          files:
            - manifests/issuers/cluster-issuer-letsencrypt-prd.yaml
            - manifests/issuers/cluster-issuer-letsencrypt-stg.yaml
          validation:
            kind: ClusterIssuer
            wait_for_ready: true
            timeout: 120
          rollback:
            enabled: true
            commands:
              - kubectl delete clusterissuer letsencrypt-prd --ignore-not-found=true

        # Step 2: Certificate 생성
        - type: inline
          name: create-wildcard-certificate
          content:
            apiVersion: cert-manager.io/v1
            kind: Certificate
            metadata:
              name: wildcard-cert
            spec:
              secretName: wildcard-cert-tls
              issuerRef:
                name: letsencrypt-stg
                kind: ClusterIssuer
          dependency:
            depends_on:
              - deploy-cluster-issuers
          validation:
            kind: Certificate
            name: wildcard-cert
            wait_for_ready: true
            timeout: 300

        # Step 3: DNS 검증
        - type: command
          name: verify-dns-records
          command: dig +short _acme-challenge.example.com TXT @8.8.8.8
          retry:
            max_attempts: 5
            delay: 10
          on_failure: warn
          dependency:
            depends_on:
              - create-wildcard-certificate
            wait_for:
              - kind: CertificateRequest
                label_selector: "acme.cert-manager.io/order-name"
                condition: Ready
                timeout: 300
```

### 구현 상세

**새로운 모델**:

- `ValidationRule`: 검증 규칙 정의
- `DependencyConfig`: 의존성 설정 (`depends_on`, `wait_for`)
- `RollbackPolicy`: 롤백 정책 (`enabled`, `on_failure`, `manifests`, `commands`)

**HookExecutor 확장**:

- `_validate_task_result()`: Task 실행 후 validation 검증
- `_check_task_dependencies()`: Task 실행 전 dependency 검증
- `_execute_rollback()`: 실패 시 rollback 실행
- `execute_hook_tasks()` 수정: Phase 3 기능 통합

**테스트 커버리지**:

- 모델 테스트: 17개 (test_phase3_models.py)
- Executor 테스트: 19개 (test_phase3_executor.py)
- 전체 hook 테스트: 74개 통과
- hook_executor.py 커버리지: **82%**

______________________________________________________________________

## 🚀 Phase 4: Hook as App (v1.0.0 검토중)

### 목표

Hooks를 독립적인 `HookApp` 타입으로 승격

### 예상 사용법

```yaml
apps:
  cert-manager:
    type: helm
    chart: jetstack/cert-manager

  cert-manager-issuers:
    type: hook  # 새로운 앱 타입
    depends_on:
      - cert-manager
    manifests:
      - manifests/issuers/cluster-issuer-letsencrypt-prd.yaml
      - manifests/issuers/cluster-issuer-letsencrypt-stg.yaml
    validation:
      kind: ClusterIssuer
      wait_for_ready: true
```

### 효과

- ✅ hooks를 별도 앱으로 관리
- ✅ 재사용 가능한 hook 라이브러리
- ✅ 독립적인 lifecycle

______________________________________________________________________

## 📚 참고 자료

### 관련 파일

**모델**:

- `sbkube/models/config_model.py`:
  - Phase 2: `ManifestsHookTask`, `InlineHookTask`, `CommandHookTask`
  - Phase 3: `ValidationRule`, `DependencyConfig`, `RollbackPolicy`
  - `AppHooks`: `pre_deploy_tasks`, `post_deploy_tasks`

**실행**:

- `sbkube/utils/hook_executor.py`:
  - Phase 2: `execute_hook_tasks()`, `_execute_single_task()`
  - Phase 3: `_validate_task_result()`, `_check_task_dependencies()`, `_execute_rollback()`

**통합**:

- `sbkube/commands/deploy.py`: Hook 실행 통합

**테스트**:

- `tests/unit/test_hook_executor.py`: Phase 1, 2 executor 테스트
- `tests/unit/test_hook_task_models.py`: Phase 2 모델 테스트
- `tests/unit/test_phase3_models.py`: Phase 3 모델 테스트
- `tests/unit/test_phase3_executor.py`: Phase 3 executor 테스트

**예제**:

- `examples/hooks-manifests/`: Phase 1 (manifests 지원)
- `examples/hooks-phase3/`: Phase 3 (validation, dependency, rollback)

### 예제 실행

**Phase 1 예제**:

```bash
cd examples/hooks-manifests
sbkube apply --app-dir . --namespace cert-manager
```

**Phase 3 예제**:

```bash
cd examples/hooks-phase3
sbkube apply --app-dir . --namespace cert-manager
```

### 테스트 실행

```bash
# 전체 hook 테스트 (Phase 1, 2, 3)
uv run pytest tests/unit/test_hook_executor.py \
             tests/unit/test_hook_task_models.py \
             tests/unit/test_phase3_models.py \
             tests/unit/test_phase3_executor.py -v

# Phase 3 모델 테스트만
uv run pytest tests/unit/test_phase3_models.py -v

# Phase 3 executor 테스트만
uv run pytest tests/unit/test_phase3_executor.py -v
```

______________________________________________________________________

## 🎯 요약

| Phase | 핵심 개선사항 | 사용자 이점 | 상태 | |-------|------------|-----------|------| | **Phase 1** | Manifests 지원 | kubectl 직접 호출
불필요 | ✅ 완료 (v0.7.0) | | **Phase 2** | Type System | 타입별 전용 처리, 강타입 검증 | ✅ 완료 (v0.8.0) | | **Phase 3** | Validation &
Dependency | 자동 검증, 의존성 관리, 롤백 | ✅ 완료 (v0.9.0) | | **Phase 4** | Hook as App | 재사용, 독립 관리 | 📝 계획 (v1.0.0?) |

### 현재 상태 (2025-10-31)

**✅ Phase 1, 2, 3 완료!**

sbkube hooks는 이제 단순한 shell 명령어 실행기가 아니라, **강력한 Kubernetes 리소스 관리 시스템**입니다:

1. **Type System** (Phase 2): `manifests`, `inline`, `command` 타입별 전용 처리
1. **Validation** (Phase 3): 배포 후 리소스 상태 자동 검증
1. **Dependency** (Phase 3): Task 간 의존성 관리 및 외부 리소스 대기
1. **Rollback** (Phase 3): 실패 시 자동 정리 및 복구

**사용 가능한 필드**:

- `pre_deploy_tasks` / `post_deploy_tasks`: Phase 2, 3 기능 모두 포함
- `pre_deploy_manifests` / `post_deploy_manifests`: Phase 1 (호환성 유지)
- `pre_deploy` / `post_deploy`: 기존 shell 명령어 (호환성 유지)

**예제**:

- Phase 1: `examples/hooks-manifests/`
- Phase 3: `examples/hooks-phase3/`

**테스트 커버리지**:

- 74개 테스트 통과
- hook_executor.py: 82% 커버리지
