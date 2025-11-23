# App Type: hook (HookApp)

**HookApp**은 독립적인 앱 타입으로 배포 workflow의 일부로 관리됩니다.

이 예제는 HookApp의 핵심 기능들을 시연합니다:
- 3가지 task type: `manifests`, `inline`, `command`
- Task별 validation 및 rollback
- 앱 레벨 lifecycle 관리
- 다른 앱과의 의존성 설정 (depends_on)

## 📋 config.yaml 주요 기능

### 1. HookApp 기본 구조

```yaml
apps:
  setup-resources:
    type: hook  # HookApp type (v0.8.0+)

    # 메타데이터 (선택사항)
    labels:
      app: hook-example
      component: setup
    annotations:
      description: "Setup application resources"

    # Tasks: 순차적으로 실행
    tasks:
      - type: manifests
        name: deploy-configmap
        files:
          - manifests/configmap.yaml
```

### 2. Task Type: manifests

파일 기반 Kubernetes 매니페스트 배포:

```yaml
tasks:
  - type: manifests
    name: deploy-configmap
    files:
      - manifests/configmap.yaml  # 매니페스트 파일 경로
    validation:
      kind: ConfigMap
      name: app-config
      namespace: default
      wait_for_ready: true
      timeout: 60
    rollback:
      enabled: true
      on_failure: always
      commands:
        - kubectl delete configmap app-config -n default --ignore-not-found=true
```

**사용 사례**:
- 외부 YAML 파일로 관리되는 리소스
- 복잡한 매니페스트 (여러 리소스 포함)
- Git으로 버전 관리되는 설정

### 3. Task Type: inline

config.yaml에 직접 YAML 포함:

```yaml
tasks:
  - type: inline
    name: create-secret
    content:
      apiVersion: v1
      kind: Secret
      metadata:
        name: app-credentials
        namespace: default
      type: Opaque
      stringData:
        username: "admin"
        password: "changeme"
    validation:
      kind: Secret
      name: app-credentials
      namespace: default
    rollback:
      enabled: true
      commands:
        - kubectl delete secret app-credentials -n default --ignore-not-found=true
```

**사용 사례**:
- 간단한 리소스 (ConfigMap, Secret 등)
- 동적으로 생성되는 설정
- 파일 분리가 불필요한 경우

### 4. Task Type: command

커스텀 명령어 실행:

```yaml
tasks:
  - type: command
    name: verify-resources
    command: |
      echo "Verifying resources..."
      kubectl get configmap app-config -n default
      kubectl get secret app-credentials -n default
    retry:
      max_attempts: 3
      delay: 5
    on_failure: warn  # 실패 시 경고만 (배포 계속)
```

**사용 사례**:
- 배포 후 검증 스크립트
- 데이터베이스 마이그레이션
- 외부 API 호출
- 커스텀 초기화 로직

### 5. Validation (Task 레벨)

각 task의 성공 여부 검증:

```yaml
tasks:
  - type: manifests
    name: deploy-configmap
    files:
      - manifests/configmap.yaml
    validation:
      kind: ConfigMap              # 검증할 리소스 kind
      name: app-config             # 리소스 이름
      namespace: default           # 네임스페이스
      wait_for_ready: true         # Ready 상태 대기
      timeout: 60                  # 타임아웃 (초)
      conditions:                  # 추가 조건 (선택사항)
        - type: Ready
          status: "True"
```

### 6. Rollback (Task 레벨)

Task 실패 시 자동 rollback:

```yaml
tasks:
  - type: inline
    name: create-secret
    content: { ... }
    rollback:
      enabled: true
      on_failure: always           # always | never | on_error
      commands:
        - kubectl delete secret app-credentials -n default --ignore-not-found=true
```

### 7. 앱 레벨 Rollback

모든 task 실패 시 전체 rollback:

```yaml
apps:
  setup-resources:
    type: hook
    tasks: [ ... ]

    # 앱 레벨 rollback (모든 task 실패 시)
    rollback:
      enabled: true
      on_failure: always
      commands:
        - kubectl delete configmap app-config -n default --ignore-not-found=true
        - kubectl delete secret app-credentials -n default --ignore-not-found=true
```

### 8. depends_on (다른 앱과의 의존성)

```yaml
apps:
  # Step 1: Database 배포 (Helm)
  postgres:
    type: helm
    chart: bitnami/postgresql
    version: 12.1.2

  # Step 2: Database 초기화 (HookApp)
  init-database:
    type: hook
    depends_on:
      - postgres  # postgres가 먼저 배포되어야 함
    tasks:
      - type: command
        name: create-schema
        command: |
          psql -c "CREATE SCHEMA IF NOT EXISTS app_schema;"
```

## 📁 File Structure

```
app-types/09-hook/
├── config.yaml              # HookApp 설정
├── sources.yaml             # 클러스터 설정
├── manifests/               # manifests task용 YAML 파일
│   └── configmap.yaml
└── README.md
```

## 🚀 사용 방법

### 1. 배포

```bash
# 전체 배포
sbkube apply --app-dir examples/app-types/09-hook

# Dry-run (실제 배포 안 함)
sbkube apply --app-dir examples/app-types/09-hook --dry-run
```

### 2. 검증

```bash
# 설정 검증
sbkube validate examples/app-types/09-hook/config.yaml

# 배포 상태 확인
sbkube status --app-dir examples/app-types/09-hook

# 리소스 직접 확인
kubectl get configmap app-config -n default
kubectl get secret app-credentials -n default
```

### 3. 삭제

```bash
# HookApp 삭제
sbkube delete --app-dir examples/app-types/09-hook

# 또는 직접 삭제
kubectl delete configmap app-config -n default
kubectl delete secret app-credentials -n default
```

## 📊 실행 결과

```
=== SBKube Apply ===
Namespace: default
Apps: setup-resources

[1/4] prepare: Skipped (HookApp)
[2/4] build: Skipped (HookApp)
[3/4] template: Skipped (HookApp)
[4/4] deploy:
  ✓ setup-resources (hook)
    ✓ Task: deploy-configmap (manifests)
      - Deployed: ConfigMap/app-config
      - Validation: PASSED
    ✓ Task: create-secret (inline)
      - Created: Secret/app-credentials
      - Validation: PASSED
    ✓ Task: verify-resources (command)
      - Output:
        === Verifying deployed resources ===

        ConfigMap:
        data:
          app.properties: |
            environment=development
            log_level=debug

        Secret:
        app-credentials (exists)

        === Verification complete ===

✓ Deployment completed successfully
```

## 🔗 관련 문서

- [HookApp 상세 가이드](../../docs/02-features/hooks-guide.md)
- [Application Types](../../docs/02-features/application-types.md)
- [Hooks Phase 4 예제](../../hooks-phase4/README.md) - 복잡한 HookApp 시나리오

## 💡 Best Practices

### 1. Task 실행 순서

Tasks는 정의된 순서대로 순차 실행됩니다:
- 의존성이 있는 task는 순서를 고려
- 검증 task는 마지막에 배치

### 2. Validation 사용

- 중요한 리소스는 반드시 validation 설정
- timeout을 충분히 설정 (복잡한 리소스는 300초 이상)

### 3. Rollback 전략

- Task별 rollback: 해당 task만 정리
- 앱 레벨 rollback: 모든 task의 리소스 정리
- on_failure:
  - `always`: 실패 시 항상 rollback
  - `on_error`: 에러 시에만 rollback
  - `never`: rollback 안 함

### 4. on_failure 옵션

- `fail`: 실패 시 배포 중단 (기본값)
- `warn`: 경고만 출력하고 계속 진행
- `ignore`: 완전히 무시

### 5. depends_on 활용

- Helm 앱 배포 후 HookApp으로 초기화
- 여러 HookApp을 체인으로 연결
- 복잡한 배포 순서 관리

## ⚠️ 주의사항

1. **HookApp은 v0.8.0+ 기능**: 이전 버전에서는 동작하지 않음
2. **준비 단계 없음**: prepare/build/template 단계를 건너뜀
3. **순서 중요**: Tasks는 정의된 순서대로만 실행
4. **Namespace 상속**: 앱 레벨 namespace 설정 불가 (전역 namespace 사용)
5. **Rollback 한계**: 외부 시스템 변경(API 호출 등)은 자동 rollback 불가

## 🎯 Use Cases

### 1. Helm 앱 배포 후 초기화

```yaml
apps:
  postgres:
    type: helm
    chart: bitnami/postgresql

  init-db:
    type: hook
    depends_on: [postgres]
    tasks:
      - type: command
        name: create-schema
        command: psql -c "CREATE SCHEMA app;"
```

### 2. 복잡한 Secret/ConfigMap 관리

```yaml
apps:
  config-setup:
    type: hook
    tasks:
      - type: inline
        name: create-app-config
        content: { ... }  # 복잡한 ConfigMap
      - type: command
        name: encrypt-secrets
        command: ./scripts/encrypt-and-store.sh
```

### 3. 배포 전/후 검증

```yaml
apps:
  pre-checks:
    type: hook
    tasks:
      - type: command
        name: verify-cluster
        command: ./scripts/verify-cluster-ready.sh

  my-app:
    type: helm
    depends_on: [pre-checks]
    chart: my-app/chart

  post-checks:
    type: hook
    depends_on: [my-app]
    tasks:
      - type: command
        name: smoke-test
        command: ./scripts/smoke-test.sh
```
