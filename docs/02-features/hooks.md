# Hooks

SBKube hooks 기능을 사용하면 명령어 실행 전후 및 앱 배포 전후에 커스텀 스크립트를 실행할 수 있습니다.

## 목차

- [개요](#개요)
- [Hooks 종류](#hooks-종류)
- [설정 방법](#설정-방법)
- [실행 순서](#실행-순서)
- [환경변수](#환경변수)
- [실전 사용 사례](#실전-사용-사례)
- [Phase 4: HookApp (Hook as First-Class App)](#phase-4-hookapp-hook-as-first-class-app)
- [Helm Hooks와의 차이](#helm-hooks와의-차이)
- [고급 기능 및 참고 자료](#고급-기능-및-참고-자료)

## 개요

Hooks는 두 가지 레벨에서 실행할 수 있습니다:

1. **명령어 수준 (Command-level)**: 전역 훅으로, 모든 앱 배포에 적용
2. **앱 수준 (App-level)**: 개별 앱에 특화된 훅

## Hooks 종류

### 명령어 수준 훅

config.yaml의 최상위 레벨에 정의:

```yaml
namespace: production

hooks:
  # prepare 명령어 훅
  prepare:
    pre:
      - echo "Preparing apps..."
    post:
      - echo "All apps prepared"
    on_failure:
      - echo "Preparation failed"

  # deploy 명령어 훅
  deploy:
    pre:
      - echo "Starting deployment"
      - kubectl cluster-info
    post:
      - echo "Deployment completed"
      - kubectl get pods -n production
    on_failure:
      - echo "Deployment failed"
      - ./scripts/rollback.sh
```

### 앱 수준 훅

각 앱의 hooks 필드에 정의:

```yaml
apps:
  database:
    type: helm
    chart: bitnami/postgresql
    hooks:
      # prepare 단계 훅
      pre_prepare:
        - echo "Preparing database chart..."
      post_prepare:
        - echo "Database chart ready"

      # build 단계 훅
      pre_build:
        - echo "Building database chart..."
      post_build:
        - echo "Database chart built"

      # deploy 단계 훅
      pre_deploy:
        - echo "Backing up database..."
        - ./scripts/backup-db.sh
      post_deploy:
        - echo "Waiting for database..."
        - kubectl wait --for=condition=ready pod -l app=postgresql --timeout=300s
        - echo "Running migrations..."
        - ./scripts/migrate.sh
      on_deploy_failure:
        - echo "Database deployment failed!"
        - ./scripts/restore-backup.sh
```

## 설정 방법

### 1. 전역 훅 설정

`config.yaml`에서:

```yaml
namespace: production

hooks:
  deploy:
    pre:
      - echo "=== Deployment started ==="
      - date
    post:
      - echo "=== Deployment completed ==="
      - date
```

### 2. 앱별 훅 설정

각 앱에 `hooks` 필드 추가:

```yaml
apps:
  redis:
    type: helm
    chart: bitnami/redis
    hooks:
      pre_deploy:
        - echo "Deploying Redis..."
      post_deploy:
        - kubectl get pods -l app=redis
```

### 3. 하이브리드 (전역 + 앱별)

두 가지를 함께 사용할 수 있습니다:

```yaml
namespace: production

# 전역 훅 (모든 앱에 적용)
hooks:
  deploy:
    pre:
      - echo "Starting batch deployment"

apps:
  redis:
    type: helm
    chart: bitnami/redis
    # 앱별 훅 (이 앱에만 적용)
    hooks:
      post_deploy:
        - echo "Redis specific post-deploy task"
```

**실행 순서**: 전역 pre → 앱 pre → 배포 → 앱 post → 전역 post

## 실행 순서

### deploy 명령어 실행 시

```
1. 전역 pre-deploy 훅 실행
2. 앱 A:
   2.1. 앱 A pre_deploy 훅 실행
   2.2. 앱 A 배포
   2.3. 앱 A post_deploy 훅 실행 (성공 시) 또는 on_deploy_failure 훅 (실패 시)
3. 앱 B:
   3.1. 앱 B pre_deploy 훅 실행
   3.2. 앱 B 배포
   3.3. 앱 B post_deploy 훅 실행 (성공 시) 또는 on_deploy_failure 훅 (실패 시)
4. 전역 post-deploy 훅 실행 (모두 성공 시) 또는 on_failure 훅 (하나라도 실패 시)
```

### prepare 명령어 실행 시

```
1. 전역 pre-prepare 훅 실행
2. 각 앱:
   2.1. 앱 pre_prepare 훅 실행
   2.2. 앱 준비 (차트 다운로드 등)
   2.3. 앱 post_prepare 훅 실행
3. 전역 post-prepare 훅 실행
```

## 환경변수

훅 실행 시 다음 환경변수가 자동으로 주입됩니다:

### 앱별 훅 환경변수

| 변수 | 설명 | 예시 |
|------|------|------|
| `SBKUBE_APP_NAME` | 현재 앱 이름 | `redis` |
| `SBKUBE_NAMESPACE` | 배포 네임스페이스 | `production` |
| `SBKUBE_RELEASE_NAME` | Helm 릴리스 이름 | `my-redis` |

### 사용 예시

```yaml
apps:
  backend:
    type: helm
    chart: ./charts/backend
    hooks:
      post_deploy:
        - echo "Deployed $SBKUBE_APP_NAME to $SBKUBE_NAMESPACE"
        - kubectl get pods -l release=$SBKUBE_RELEASE_NAME
```

또는 쉘 스크립트에서:

```bash
#!/bin/bash
# scripts/notify.sh

echo "=== Deployment Info ==="
echo "App: $SBKUBE_APP_NAME"
echo "Namespace: $SBKUBE_NAMESPACE"
echo "Release: $SBKUBE_RELEASE_NAME"
```

## 작업 디렉토리

훅 스크립트는 **`--app-dir`로 지정된 디렉토리**에서 실행됩니다.

### 디렉토리 구조 예시

```
/project/                    # 프로젝트 루트 (BASE_DIR)
├── sources.yaml             # 소스 설정
├── redis_dir/               # --app-dir 옵션으로 지정
│   ├── config.yaml          # 앱 설정 파일
│   ├── values.yaml
│   └── scripts/
│       ├── pre-deploy.sh    # 훅 스크립트
│       └── backup.sh
```

### 명령어 실행

```bash
cd /project
sbkube deploy --app-dir redis_dir
```

### 훅 실행 위치

```yaml
# redis_dir/config.yaml
hooks:
  deploy:
    pre:
      - ./scripts/pre-deploy.sh  # ← redis_dir 기준 상대 경로
```

**실제 실행**:
```bash
cd /project/redis_dir          # work_dir로 이동
./scripts/pre-deploy.sh        # 실행
# = /project/redis_dir/scripts/pre-deploy.sh
```

### 핵심 원칙

1. **훅은 APP_CONFIG_DIR에서 실행**: `--app-dir`로 지정한 디렉토리가 작업 디렉토리
2. **상대 경로 사용 가능**: `./scripts/backup.sh` 같은 상대 경로를 자연스럽게 사용
3. **절대 경로도 가능**: `/usr/local/bin/my-script.sh` 같은 절대 경로도 지원

### 실전 팁

```yaml
# redis_dir/config.yaml
namespace: production

hooks:
  deploy:
    pre:
      # ✅ 권장: 상대 경로 (APP_CONFIG_DIR 기준)
      - ./scripts/backup.sh
      - ./scripts/check-status.sh

      # ✅ 가능: 절대 경로
      - /usr/local/bin/notify-slack.sh

      # ✅ 가능: 시스템 명령어
      - echo "Starting deployment..."
      - kubectl cluster-info
```

## 실전 사용 사례

### 1. 데이터베이스 백업 및 마이그레이션

```yaml
apps:
  postgresql:
    type: helm
    chart: bitnami/postgresql
    version: 13.0.0
    hooks:
      pre_deploy:
        - echo "Creating database backup..."
        - kubectl exec postgresql-0 -n production -- pg_dump -U postgres mydb > /backups/db-$(date +%Y%m%d-%H%M%S).sql
        - echo "Backup completed"

      post_deploy:
        - echo "Waiting for database to be ready..."
        - kubectl wait --for=condition=ready pod -l app.kubernetes.io/name=postgresql -n production --timeout=300s
        - echo "Running database migrations..."
        - kubectl exec postgresql-0 -n production -- psql -U postgres -d mydb -f /migrations/latest.sql
        - echo "Migrations completed"

      on_deploy_failure:
        - echo "Database deployment failed, restoring backup..."
        - kubectl exec postgresql-0 -n production -- psql -U postgres -d mydb -f /backups/db-latest.sql
        - echo "Backup restored"
```

### 2. 서비스 헬스체크 및 알림

```yaml
hooks:
  deploy:
    pre:
      - ./scripts/notify-slack.sh "🚀 Deployment started for $SBKUBE_NAMESPACE"

    post:
      - ./scripts/notify-slack.sh "✅ Deployment completed for $SBKUBE_NAMESPACE"
      - ./scripts/send-metrics.sh

    on_failure:
      - ./scripts/notify-slack.sh "❌ Deployment failed for $SBKUBE_NAMESPACE"
      - ./scripts/notify-pagerduty.sh "critical"

apps:
  backend:
    type: helm
    chart: ./charts/backend
    hooks:
      post_deploy:
        - echo "Running health check..."
        - sleep 10
        - curl -f http://backend.production.svc.cluster.local/health || exit 1
        - echo "Health check passed"
        - ./scripts/smoke-test.sh
```

### 3. 의존성 대기 및 검증

```yaml
apps:
  redis:
    type: helm
    chart: bitnami/redis
    hooks:
      post_deploy:
        - kubectl wait --for=condition=ready pod -l app.kubernetes.io/name=redis --timeout=300s
        - echo "Redis is ready"

  backend:
    type: helm
    chart: ./charts/backend
    depends_on:
      - redis
    hooks:
      pre_deploy:
        - echo "Checking Redis connectivity..."
        - kubectl run redis-test --rm -i --restart=Never --image=redis:alpine -- redis-cli -h redis ping
        - echo "Redis is accessible"

      post_deploy:
        - echo "Running integration tests..."
        - ./scripts/integration-test.sh
```

### 4. GitOps 및 외부 시스템 통합

```yaml
hooks:
  deploy:
    pre:
      # Argo CD 동기화 일시 중지
      - argocd app set myapp --sync-policy none

      # Git 태그 생성
      - git tag -a "deploy-$(date +%Y%m%d-%H%M%S)" -m "Deployment to staging"
      - git push origin --tags

    post:
      # Argo CD 동기화 재개
      - argocd app set myapp --sync-policy automated

      # 배포 정보 외부 시스템에 기록
      - |
        curl -X POST https://deploy-tracker.example.com/api/deployments \
          -H "Content-Type: application/json" \
          -d "{\"environment\": \"staging\", \"timestamp\": \"$(date -u +%Y-%m-%dT%H:%M:%SZ)\"}"
```

### 5. 보안 스캔 및 검증

```yaml
apps:
  frontend:
    type: helm
    chart: ./charts/frontend
    hooks:
      post_deploy:
        # Lighthouse CI 성능 테스트
        - lhci autorun --collect.url=https://staging.example.com

        # 보안 헤더 검증
        - ./scripts/check-security-headers.sh https://staging.example.com

        # 접근성 테스트
        - pa11y https://staging.example.com
```

## Phase 4: HookApp (Hook as First-Class App)

> **도입 버전**: v0.8.0
> **상태**: ✅ 안정

### 개요

Phase 4에서는 Hook 자체를 하나의 독립된 앱(`type: hook`)으로 정의할 수 있습니다. 이를 통해 Hook을 재사용 가능하고 독립적으로 관리할 수 있습니다.

### 기존 방식의 한계

기존에는 Hook이 특정 앱에 종속되어 있었습니다:

```yaml
apps:
  - name: cert-manager
    type: helm
    hooks:
      post_deploy_tasks:
        # 이 Hook은 cert-manager에만 사용 가능
        - type: manifests
          paths: ["cluster-issuer.yaml"]
```

**문제점**:
- Hook을 다른 환경이나 프로젝트에서 재사용하기 어려움
- 복잡한 초기화 로직을 독립적으로 관리하기 어려움
- `enabled: false`로 쉽게 비활성화할 수 없음

### HookApp 방식

```yaml
apps:
  # 1. cert-manager 설치 (Helm 앱)
  - name: cert-manager
    type: helm
    specs:
      repo: jetstack
      chart: cert-manager
      version: v1.13.0

  # 2. ClusterIssuer 설정 (독립된 HookApp)
  - name: setup-cluster-issuers
    type: hook  # Phase 4: Hook이 First-class App
    enabled: true

    hooks:
      post_deploy_tasks:
        # ClusterIssuer 배포
        - type: manifests
          name: deploy-issuers
          paths:
            - manifests/letsencrypt-staging.yaml
            - manifests/letsencrypt-prod.yaml

        # 배포 검증
        - type: command
          name: verify-issuers
          command:
            - bash
            - -c
            - |
              kubectl wait --for=condition=ready \
                clusterissuer/letsencrypt-prod --timeout=60s
          dependency:
            wait_for_tasks: ["deploy-issuers"]
```

### HookApp의 특징

| 특징 | 설명 | 장점 |
|------|------|------|
| **First-class App** | `type: hook`으로 독립된 앱 | 다른 앱과 동일하게 관리 |
| **Lifecycle 간소화** | `prepare`, `build`, `template` 건너뜀 | `deploy`에서만 실행 |
| **재사용 가능** | 다른 프로젝트에서도 사용 가능 | 중복 제거 |
| **Enabled 플래그** | `enabled: false`로 비활성화 | 쉬운 On/Off |
| **Dependency 지원** | 앱 간 의존성 관리 | 실행 순서 제어 |
| **개별 배포 가능** | `sbkube deploy --app setup-issuers` | 독립적 관리 |

### 실행 순서

```
┌─────────────────────────────────────────────────────────┐
│  sbkube deploy                                           │
└─────────────────────────────────────────────────────────┘
                       │
                       ▼
┌─────────────────────────────────────────────────────────┐
│  1. cert-manager (type: helm)                            │
│     - prepare: Helm chart pull                           │
│     - build: Chart build                                 │
│     - template: Render templates                         │
│     - deploy: Install Helm release                       │
└─────────────────────────────────────────────────────────┘
                       │
                       ▼
┌─────────────────────────────────────────────────────────┐
│  2. setup-cluster-issuers (type: hook)                   │
│     - prepare: ⏭️  SKIP                                  │
│     - build: ⏭️  SKIP                                    │
│     - template: ⏭️  SKIP                                 │
│     - deploy: ✅ Execute post_deploy_tasks               │
│       └─ Task 1: Deploy manifests                        │
│       └─ Task 2: Verify (after Task 1)                   │
└─────────────────────────────────────────────────────────┘
```

### 실전 사용 사례

#### 1. cert-manager 초기화

```yaml
apps:
  - name: cert-manager
    type: helm
    specs:
      repo: jetstack
      chart: cert-manager

  - name: setup-issuers
    type: hook
    hooks:
      post_deploy_tasks:
        - type: manifests
          paths:
            - manifests/letsencrypt-staging.yaml
            - manifests/letsencrypt-prod.yaml
```

#### 2. Database Schema 초기화

```yaml
apps:
  - name: postgres
    type: helm
    specs:
      repo: bitnami
      chart: postgresql

  - name: init-database-schema
    type: hook
    hooks:
      post_deploy_tasks:
        # Schema 생성
        - type: command
          name: create-schema
          command:
            - kubectl
            - exec
            - deployment/postgres
            - --
            - psql
            - -c
            - "CREATE SCHEMA IF NOT EXISTS myapp;"

        # Migration 실행
        - type: command
          name: run-migrations
          command: ["./scripts/migrate.sh"]
          dependency:
            wait_for_tasks: ["create-schema"]
```

#### 3. 여러 HookApp 체인

```yaml
apps:
  # 1. Keycloak 설치
  - name: keycloak
    type: helm
    specs:
      repo: bitnami
      chart: keycloak

  # 2. Realm 생성 (HookApp)
  - name: create-realm
    type: hook
    hooks:
      post_deploy_tasks:
        - type: inline
          yaml: |
            apiVersion: v1
            kind: ConfigMap
            metadata:
              name: keycloak-realm
            data:
              realm.json: |
                {"realm": "myrealm", "enabled": true}

  # 3. Client 생성 (HookApp, Realm 이후)
  - name: create-clients
    type: hook
    hooks:
      post_deploy_tasks:
        - type: command
          command: ["./scripts/create-keycloak-clients.sh"]

  # 4. 실제 애플리케이션
  - name: my-app
    type: helm
    specs:
      chart: ./charts/myapp
```

**실행 순서**: keycloak → create-realm → create-clients → my-app

### HookApp vs 일반 Hook

| 항목 | 일반 Hook (앱에 종속) | HookApp (`type: hook`) |
|------|---------------------|----------------------|
| **정의 위치** | 기존 앱의 `hooks:` 섹션 | 독립된 앱 정의 |
| **재사용성** | ❌ 낮음 (앱과 결합) | ✅ 높음 (독립적) |
| **Lifecycle** | 앱과 동일 (prepare/build/template/deploy) | 간소화 (deploy만) |
| **Enabled 플래그** | ❌ 없음 | ✅ 있음 |
| **개별 배포** | ❌ 불가 | ✅ 가능 |
| **사용 시나리오** | 특정 앱에만 필요한 작업 | 재사용 가능한 초기화 작업 |

### 언제 HookApp을 사용할까?

**HookApp 사용 권장**:
- ✅ 여러 프로젝트/환경에서 재사용
- ✅ 복잡한 초기화 로직 (여러 task 포함)
- ✅ 독립적으로 On/Off 전환 필요
- ✅ 다른 앱과 명확한 의존성 관계

**일반 Hook 사용 권장**:
- ✅ 특정 앱에만 종속된 작업
- ✅ 간단한 Shell 명령어
- ✅ 한 번만 사용

### 추가 리소스

- **[Hooks 레퍼런스](./hooks-reference.md)**: 전체 Hook 타입 및 환경 변수
- **[Hooks 마이그레이션 가이드](./hooks-migration-guide.md)**: Phase 3 → Phase 4 전환 방법
- **[예제: HookApp 기본](../../examples/hooks-hookapp-simple/)**: 간단한 HookApp 예제
- **[예제: HookApp 고급](../../examples/hooks-phase4/)**: 복잡한 체인 예제

## Helm Hooks와의 차이

SBKube hooks와 Helm hooks는 다른 개념입니다:

| 특성 | SBKube Hooks | Helm Hooks |
|------|--------------|------------|
| **정의** | SBKube 명령어 실행 시점 | Helm 릴리스 라이프사이클 |
| **실행 주체** | SBKube CLI | Helm/Kubernetes |
| **실행 위치** | 로컬 머신 | Kubernetes 클러스터 |
| **목적** | 배포 자동화, 검증 | 클러스터 내 작업 |
| **사용 예시** | 백업, 알림, 외부 시스템 통합 | DB 마이그레이션, 초기화 작업 |

### SBKube Hooks 사용 시기

- 로컬에서 실행해야 하는 작업 (백업, 알림)
- 외부 시스템 통합 (GitOps, CI/CD)
- 배포 전후 검증
- 다중 앱 조정

### Helm Hooks 사용 시기

- 클러스터 내에서 실행되어야 하는 작업
- DB 초기화 및 마이그레이션
- 시크릿 생성 및 관리
- Pre/Post 설치 검증 Job

### 함께 사용하기

두 가지를 함께 사용할 수 있습니다:

```yaml
# config.yaml (SBKube hooks)
apps:
  backend:
    type: helm
    chart: ./charts/backend
    hooks:
      pre_deploy:
        - echo "SBKube: Backing up database (local)"
        - ./scripts/backup-db.sh

# charts/backend/templates/pre-install-hook.yaml (Helm hooks)
apiVersion: batch/v1
kind: Job
metadata:
  name: db-migration
  annotations:
    "helm.sh/hook": pre-install  # Helm hook
spec:
  template:
    spec:
      containers:
      - name: migrate
        image: backend:latest
        command: ["./migrate", "up"]
```

**실행 순서**:
1. SBKube `pre_deploy` 훅 (로컬)
2. Helm `pre-install` 훅 (클러스터)
3. 실제 배포
4. Helm `post-install` 훅 (클러스터)
5. SBKube `post_deploy` 훅 (로컬)

## 고급 기능 및 참고 자료

### 현재 지원되는 고급 기능

- ✅ **Phase 1: Manifests Hooks** - YAML 파일 자동 배포
- ✅ **Phase 2: Task 시스템** - manifests/inline/command 타입
- ✅ **Phase 3: Validation, Dependency, Rollback** - 실행 결과 검증 및 자동 롤백
- ✅ **Phase 4: HookApp** - Hook을 First-class App으로 관리
- ✅ **Retry 로직** - Command Task에서 자동 재시도 지원
- ✅ **에러 처리 모드** - fail/warn/ignore/manual

### 향후 지원 예정 기능

다음 기능들은 향후 버전에서 지원될 예정입니다:

- 조건부 훅 실행 (`if` 조건, 환경별 분기)
- 훅 템플릿 (변수 치환, Jinja2/Go template)
- 병렬 Task 실행 (현재는 dependency 기반 순차 실행)
- Hook 실행 결과 캐싱

### 참고 문서

#### SBKube Hooks 문서

- **[Hooks 레퍼런스](./hooks-reference.md)** - 모든 Hook 타입, 네이밍 컨벤션, 환경 변수 완전 가이드
- **[Hooks 마이그레이션 가이드](./hooks-migration-guide.md)** - Phase 간 전환 및 업그레이드 방법
- **[Application Types](./application-types.md)** - HookApp 타입 상세 설명

#### 예제 코드

**기본 예제**:
- [examples/hooks/](../../examples/hooks/) - 기본 Hook 사용법
- [examples/hooks-basic-all/](../../examples/hooks-basic-all/) - 모든 Hook 타입 종합 예제

**Phase별 예제**:
- [examples/hooks-manifests/](../../examples/hooks-manifests/) - Phase 1: Manifests
- [examples/hooks-phase3/](../../examples/hooks-phase3/) - Phase 3: Validation/Dependency/Rollback
- [examples/hooks-phase4/](../../examples/hooks-phase4/) - Phase 4: HookApp (복잡한 체인)

**시나리오별 예제**:
- [examples/hooks-pre-deploy-tasks/](../../examples/hooks-pre-deploy-tasks/) - 배포 전 검증
- [examples/hooks-command-level/](../../examples/hooks-command-level/) - 전역 알림 및 로깅
- [examples/hooks-error-handling/](../../examples/hooks-error-handling/) - 에러 처리 및 롤백
- [examples/hooks-mixed-phases/](../../examples/hooks-mixed-phases/) - 여러 Phase 혼합 사용
- [examples/hooks-hookapp-simple/](../../examples/hooks-hookapp-simple/) - HookApp 입문

#### 외부 참고 자료

- [Helm Hooks 문서](https://helm.sh/docs/topics/charts_hooks/) - Helm Hook과의 차이점 이해
