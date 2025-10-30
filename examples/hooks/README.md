# SBKube Hooks 예제

이 예제는 SBKube의 hooks 기능을 시연합니다.

## Hooks란?

Hooks는 SBKube 명령어 실행 전후 및 앱 배포 전후에 커스텀 스크립트를 실행할 수 있는 기능입니다.

## Hooks 종류

### 1. 명령어 수준 훅 (Command-level Hooks)

모든 앱 배포에 적용되는 전역 훅:

```yaml
hooks:
  deploy:
    pre:              # 배포 시작 전 실행
      - echo "Starting deployment"
    post:             # 모든 배포 완료 후 실행
      - echo "Deployment completed"
    on_failure:       # 배포 실패 시 실행
      - echo "Deployment failed"
```

### 2. 앱 수준 훅 (App-level Hooks)

개별 앱 배포 전후에 실행되는 훅:

```yaml
apps:
  redis:
    type: helm
    chart: bitnami/redis
    hooks:
      pre_deploy:          # 이 앱 배포 직전
        - echo "Deploying Redis..."
      post_deploy:         # 이 앱 배포 직후
        - kubectl wait --for=condition=ready pod -l app=redis
      on_deploy_failure:   # 이 앱 배포 실패 시
        - echo "Redis deployment failed"
```

## 지원되는 훅 타입

| 훅 타입 | 레벨 | 설명 |
|---------|------|------|
| `pre` | Command | 명령어 실행 전 |
| `post` | Command | 명령어 실행 후 (성공 시) |
| `on_failure` | Command | 명령어 실패 시 |
| `pre_prepare` | App | 앱 준비 전 |
| `post_prepare` | App | 앱 준비 후 |
| `pre_build` | App | 앱 빌드 전 |
| `post_build` | App | 앱 빌드 후 |
| `pre_deploy` | App | 앱 배포 전 |
| `post_deploy` | App | 앱 배포 후 (성공 시) |
| `on_deploy_failure` | App | 앱 배포 실패 시 |

## 이 예제 실행하기

### 1. 준비

```bash
# Redis 차트 다운로드
sbkube prepare --app-dir examples/hooks

# (선택) 빌드 (이 예제에서는 build 단계 없음)
sbkube build --app-dir examples/hooks
```

### 2. 배포

```bash
# 실제 배포
sbkube deploy --app-dir examples/hooks

# dry-run 모드로 테스트
sbkube deploy --app-dir examples/hooks --dry-run
```

### 3. 확인

배포 중 다음과 같은 훅 실행 로그를 볼 수 있습니다:

```
🪝 Executing pre-hook for command 'deploy'...
  ▶ Running: echo "=== Deployment started at $(date) ==="
  ▶ Running: kubectl cluster-info
✅ pre-hook completed successfully

🚀 Deploying Helm app: redis
🪝 Executing pre_deploy hook for app 'redis'...
  ▶ Running: echo "🚀 Preparing to deploy Redis..."
  ▶ Running: kubectl get pods -l app.kubernetes.io/name=redis -n hooks-demo
✅ pre_deploy hook for 'redis' completed successfully

... (Redis 배포) ...

🪝 Executing post_deploy hook for app 'redis'...
  ▶ Running: echo "✅ Redis deployed successfully!"
  ▶ Running: kubectl wait --for=condition=ready pod -l app.kubernetes.io/name=redis
✅ post_deploy hook for 'redis' completed successfully

🪝 Executing post-hook for command 'deploy'...
  ▶ Running: echo "=== Deployment completed at $(date) ==="
✅ post-hook completed successfully
```

## 실전 사용 사례

### 1. 데이터베이스 백업 및 마이그레이션

```yaml
apps:
  postgresql:
    type: helm
    chart: bitnami/postgresql
    hooks:
      pre_deploy:
        - ./scripts/backup-db.sh
        - echo "Database backed up"
      post_deploy:
        - kubectl wait --for=condition=ready pod -l app=postgresql --timeout=300s
        - ./scripts/run-migrations.sh
      on_deploy_failure:
        - ./scripts/restore-backup.sh
```

### 2. 외부 시스템 알림

```yaml
hooks:
  deploy:
    pre:
      - ./scripts/notify-slack.sh "🚀 Deployment started"
    post:
      - ./scripts/notify-slack.sh "✅ Deployment completed"
    on_failure:
      - ./scripts/notify-slack.sh "❌ Deployment failed"
      - ./scripts/notify-pagerduty.sh
```

### 3. 의존성 확인

```yaml
apps:
  backend:
    type: helm
    chart: ./charts/backend
    hooks:
      pre_deploy:
        - echo "Checking Redis connectivity..."
        - kubectl run redis-test --rm -i --restart=Never --image=redis:alpine -- redis-cli -h redis ping
        - echo "Redis is accessible"
```

### 4. 헬스체크 및 스모크 테스트

```yaml
apps:
  api:
    type: helm
    chart: ./charts/api
    hooks:
      post_deploy:
        - echo "Running smoke tests..."
        - sleep 10
        - curl -f http://api.production.svc.cluster.local/health || exit 1
        - ./scripts/smoke-test.sh
```

## 환경변수

훅 실행 시 다음 환경변수가 자동으로 주입됩니다:

| 변수 | 설명 | 예시 |
|------|------|------|
| `SBKUBE_APP_NAME` | 현재 앱 이름 | `redis` |
| `SBKUBE_NAMESPACE` | 배포 네임스페이스 | `production` |
| `SBKUBE_RELEASE_NAME` | Helm 릴리스 이름 | `my-redis` |

훅 스크립트에서 사용 예시:

```bash
#!/bin/bash
echo "Deploying app: $SBKUBE_APP_NAME"
echo "Namespace: $SBKUBE_NAMESPACE"
echo "Release name: $SBKUBE_RELEASE_NAME"
```

## 주의사항

1. **실행 권한**: 스크립트 파일은 실행 권한이 필요합니다 (`chmod +x script.sh`)
2. **상대 경로**: 훅 명령어는 `app-dir` 디렉토리에서 실행됩니다
3. **타임아웃**: 기본 타임아웃은 300초(5분)입니다
4. **실패 처리**: 훅이 실패하면 배포가 중단됩니다 (continue_on_error 미구현)

## 다음 단계

- [Hooks 문서](../../docs/02-features/hooks.md) - 상세한 hooks 가이드
- [고급 예제](../advanced-hooks/) - 복잡한 시나리오 예제
- [Helm Hooks vs SBKube Hooks](../../docs/07-troubleshooting/README.md#helm-hooks-vs-sbkube-hooks) - 차이점 이해
