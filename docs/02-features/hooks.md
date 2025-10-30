# Hooks

SBKube hooks 기능을 사용하면 명령어 실행 전후 및 앱 배포 전후에 커스텀 스크립트를 실행할 수 있습니다.

## 목차

- [개요](#개요)
- [Hooks 종류](#hooks-종류)
- [설정 방법](#설정-방법)
- [실행 순서](#실행-순서)
- [환경변수](#환경변수)
- [실전 사용 사례](#실전-사용-사례)
- [Helm Hooks와의 차이](#helm-hooks와의-차이)

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

## 고급 기능 (향후 지원 예정)

다음 기능들은 향후 버전에서 지원될 예정입니다:

- 조건부 훅 실행 (`if` 조건)
- 훅 타임아웃 커스터마이징
- continue_on_error 플래그
- 재시도 로직
- 훅 템플릿 (변수 치환)

## 참고 자료

- [예제: Hooks 기본 사용](../../examples/hooks/)
- [예제: 고급 Hooks](../../examples/advanced-hooks/)
- [Helm Hooks 문서](https://helm.sh/docs/topics/charts_hooks/)
