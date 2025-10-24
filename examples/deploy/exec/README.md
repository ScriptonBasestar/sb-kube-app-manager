# Exec Type Example - 커스텀 명령어 실행

SBKube의 **exec 타입**을 사용하여 배포 과정에서 커스텀 쉘 명령어를 실행하는 예제입니다.

## 📋 목차

- [개요](#-개요)
- [exec 타입이란?](#-exec-타입이란)
- [사용 시나리오](#-사용-시나리오)
- [설정 구조](#-설정-구조)
- [실행 방법](#-실행-방법)
- [고급 사용법](#-고급-사용법)
- [주의사항](#️-주의사항)

---

## 🎯 개요

이 예제는 다음을 시연합니다:

1. **Pre-deployment 검증**: 배포 전 클러스터 상태 확인
2. **Post-deployment 정리**: 배포 후 완료된 Pod 정리
3. **순차 실행**: 명령어 순서 보장
4. **의존성 관리**: 앱 간 실행 순서 제어

---

## 🔧 exec 타입이란?

**exec 타입**은 배포 과정에서 쉘 명령어를 순차적으로 실행하는 애플리케이션 타입입니다.

### 특징

| 특징 | 설명 |
|-----|------|
| **실행 위치** | SBKube를 실행하는 머신 (로컬/CI 서버) |
| **실행 순서** | commands 리스트 순서대로 순차 실행 |
| **오류 처리** | 하나라도 실패하면 전체 배포 중단 |
| **환경변수** | SBKube 실행 환경의 환경변수 사용 |

### 다른 타입과 비교

| 비교 항목 | exec | action | helm |
|---------|------|--------|------|
| **실행 대상** | 쉘 명령어 | kubectl 명령어 | Helm 차트 |
| **실행 위치** | 로컬 머신 | Kubernetes 클러스터 | Kubernetes 클러스터 |
| **용도** | 검증, 마이그레이션, 훅 | CRD, Operator | 애플리케이션 배포 |
| **kubectl 사용** | 수동 (commands에 포함) | 자동 (actions 처리) | 자동 (Helm 처리) |

---

## 🚀 사용 시나리오

### 시나리오 1: Pre-deployment 검증

**배경**: 배포 전 클러스터 상태를 확인하고 싶습니다.

**해결**:
```yaml
apps:
  pre-deployment-check:
    type: exec
    commands:
      - echo "Checking cluster connectivity..."
      - kubectl get nodes
      - kubectl get namespaces
      - echo "Cluster is ready!"
```

**실행 결과**:
- 클러스터 연결 확인
- 노드 상태 출력
- 네임스페이스 목록 출력
- 하나라도 실패하면 배포 중단

### 시나리오 2: Post-deployment 정리

**배경**: 배포 후 완료된 Job/Pod를 자동으로 정리하고 싶습니다.

**해결**:
```yaml
apps:
  post-deployment-cleanup:
    type: exec
    commands:
      - echo "Cleaning up completed pods..."
      - kubectl delete pods --field-selector=status.phase=Succeeded -n example-exec
      - kubectl delete pods --field-selector=status.phase=Failed -n example-exec
      - echo "Cleanup done!"
```

**실행 결과**:
- Succeeded 상태 Pod 삭제
- Failed 상태 Pod 삭제

### 시나리오 3: 데이터베이스 마이그레이션

**배경**: 애플리케이션 배포 전에 데이터베이스 스키마를 업데이트해야 합니다.

**해결**:
```yaml
apps:
  db-migration:
    type: exec
    commands:
      - echo "Running database migrations..."
      - kubectl exec -n database deploy/postgres -- psql -U admin -d app -f /migrations/001_init.sql
      - kubectl exec -n database deploy/postgres -- psql -U admin -d app -f /migrations/002_add_users.sql
      - echo "Migrations completed!"
```

**실행 결과**:
- PostgreSQL Pod 내부에서 SQL 마이그레이션 실행
- 여러 마이그레이션 파일 순차 실행

### 시나리오 4: 외부 시스템 통합

**배경**: 배포 시 외부 API에 알림을 보내거나 상태를 업데이트해야 합니다.

**해결**:
```yaml
apps:
  notify-deployment:
    type: exec
    commands:
      - echo "Notifying deployment to Slack..."
      - curl -X POST https://hooks.slack.com/services/XXX -d '{"text":"Deployment started"}'
      - echo "Notification sent!"
```

**실행 결과**:
- Slack 웹훅으로 배포 시작 알림 전송

### 시나리오 5: 설정 파일 생성/검증

**배경**: 배포 전에 동적으로 ConfigMap이나 Secret을 생성해야 합니다.

**해결**:
```yaml
apps:
  generate-config:
    type: exec
    commands:
      - echo "Generating ConfigMap..."
      - kubectl create configmap app-config --from-literal=env=production -n example-exec --dry-run=client -o yaml | kubectl apply -f -
      - kubectl get configmap app-config -n example-exec
      - echo "ConfigMap created!"
```

---

## 📝 설정 구조

### config.yaml

```yaml
namespace: example-exec

apps:
  # Pre-deployment 검증
  pre-deployment-check:
    type: exec
    commands:
      - echo "Starting pre-deployment checks..."
      - kubectl get nodes
      - echo "Pre-deployment checks completed!"

  # Post-deployment 정리
  post-deployment-cleanup:
    type: exec
    commands:
      - echo "Running post-deployment cleanup..."
      - kubectl delete pods --field-selector=status.phase=Succeeded -n example-exec
      - echo "Cleanup completed!"
    depends_on:
      - pre-deployment-check    # pre-deployment-check 이후 실행
```

### 주요 필드

| 필드 | 타입 | 필수 | 설명 |
|-----|------|-----|------|
| `type` | string | ✅ | `exec` 고정 |
| `commands` | list[string] | ✅ | 실행할 쉘 명령어 목록 |
| `depends_on` | list[string] | ❌ | 의존하는 앱 목록 (먼저 실행) |
| `enabled` | boolean | ❌ | 활성화 여부 (기본: true) |

---

## ⚡ 실행 방법

### 1. 통합 배포 (권장)

```bash
cd examples/deploy/exec

# 전체 워크플로우 실행
sbkube apply --app-dir . --namespace example-exec
```

**실행 순서**:
1. `pre-deployment-check` 실행 (의존성 없음)
2. `post-deployment-cleanup` 실행 (depends_on: pre-deployment-check)

### 2. 단계별 배포

```bash
# 1. 준비 (exec 타입은 이 단계에서 아무 작업 안 함)
sbkube prepare --app-dir .

# 2. 빌드 (exec 타입은 이 단계에서 아무 작업 안 함)
sbkube build --app-dir .

# 3. 템플릿 (exec 타입은 이 단계에서 아무 작업 안 함)
sbkube template --app-dir . --output-dir /tmp/exec

# 4. 배포 (commands 실행)
sbkube deploy --app-dir . --namespace example-exec
```

### 3. Dry-run 모드

```bash
# 실제 실행 없이 계획 확인
sbkube deploy --app-dir . --namespace example-exec --dry-run
```

**⚠️ 주의**: Dry-run 모드에서도 명령어는 실행되지 않습니다 (현재 구현 기준).

---

## 🔍 실행 결과 확인

### 로그 출력

SBKube 실행 시 명령어 출력을 실시간으로 확인할 수 있습니다:

```
✅ pre-deployment-check 실행 시작
Starting pre-deployment checks...
NAME           STATUS   ROLES                  AGE   VERSION
k3s-master     Ready    control-plane,master   10d   v1.28.0
k3s-worker-1   Ready    <none>                 10d   v1.28.0
Pre-deployment checks completed!
✅ pre-deployment-check 완료

✅ post-deployment-cleanup 실행 시작
Running post-deployment cleanup...
pod "job-12345" deleted
Cleanup completed!
✅ post-deployment-cleanup 완료
```

### 실패 처리

명령어가 실패하면 배포가 즉시 중단됩니다:

```
✅ pre-deployment-check 실행 시작
Starting pre-deployment checks...
Error from server (Forbidden): nodes is forbidden
❌ pre-deployment-check 실패
Error: Command failed: kubectl get nodes
```

---

## 🛠️ 고급 사용법

### 1. 환경변수 사용

```yaml
apps:
  env-example:
    type: exec
    commands:
      - echo "Deployment environment: $DEPLOY_ENV"
      - echo "App version: $APP_VERSION"
      - kubectl set env deployment/myapp ENV=$DEPLOY_ENV -n example-exec
```

**실행**:
```bash
export DEPLOY_ENV=production
export APP_VERSION=1.2.3
sbkube deploy --app-dir . --namespace example-exec
```

### 2. 멀티라인 명령어

```yaml
apps:
  multiline-example:
    type: exec
    commands:
      - |
        echo "Starting complex task..."
        for i in {1..5}; do
          echo "Step $i"
        done
        echo "Complex task completed!"
```

### 3. 스크립트 파일 실행

```yaml
apps:
  script-example:
    type: exec
    commands:
      - chmod +x scripts/deploy-hook.sh
      - ./scripts/deploy-hook.sh production example-exec
```

**scripts/deploy-hook.sh**:
```bash
#!/bin/bash
ENV=$1
NAMESPACE=$2

echo "Running deployment hook for $ENV in $NAMESPACE"
kubectl get pods -n $NAMESPACE
# 더 많은 로직...
```

### 4. 조건부 실행

```yaml
apps:
  conditional-example:
    type: exec
    commands:
      - test -f /tmp/skip-migration || echo "Running migration..."
      - test -f /tmp/skip-migration || kubectl exec -n database deploy/postgres -- psql -f /migrations/latest.sql
```

### 5. 의존성 체인

```yaml
apps:
  step-1:
    type: exec
    commands:
      - echo "Step 1: Prepare database"
      - kubectl create namespace database

  step-2:
    type: exec
    commands:
      - echo "Step 2: Deploy database"
      - kubectl apply -f manifests/postgres.yaml -n database
    depends_on:
      - step-1

  step-3:
    type: exec
    commands:
      - echo "Step 3: Run migrations"
      - kubectl exec -n database deploy/postgres -- psql -f /migrations/init.sql
    depends_on:
      - step-2
```

**실행 순서**: step-1 → step-2 → step-3 (순차 보장)

---

## ⚠️ 주의사항

### 1. 실행 위치

**중요**: 명령어는 **SBKube를 실행하는 머신**에서 실행됩니다.

```yaml
# ❌ 잘못된 이해
commands:
  - ls /app/data  # Kubernetes Pod 내부 파일이 아님!

# ✅ 올바른 이해
commands:
  - ls /home/user/data  # 로컬 머신 파일
  - kubectl exec deploy/myapp -- ls /app/data  # Pod 내부 파일 (올바름)
```

### 2. kubectl 컨텍스트

**중요**: kubectl 명령어는 현재 kubeconfig 컨텍스트를 사용합니다.

**확인**:
```bash
# 현재 컨텍스트 확인
kubectl config current-context

# 컨텍스트 변경
kubectl config use-context my-cluster
```

**설정**:
```yaml
apps:
  explicit-context:
    type: exec
    commands:
      - kubectl --context=production-cluster get nodes
      - kubectl --kubeconfig=/path/to/config get pods
```

### 3. 오류 처리

**중요**: 하나의 명령어라도 실패하면 전체 배포가 중단됩니다.

```yaml
# ❌ 실패 시 중단됨
commands:
  - kubectl delete pod non-existent  # 실패!
  - echo "This will not run"

# ✅ 실패해도 계속 진행 (|| true)
commands:
  - kubectl delete pod non-existent || true
  - echo "This will run"
```

### 4. 보안 주의사항

**중요**: 민감한 정보를 명령어에 직접 포함하지 마세요.

```yaml
# ❌ 위험: 비밀번호 노출
commands:
  - kubectl create secret generic db-password --from-literal=password=SuperSecret123

# ✅ 안전: 환경변수 사용
commands:
  - kubectl create secret generic db-password --from-literal=password=$DB_PASSWORD
```

**실행**:
```bash
export DB_PASSWORD=$(cat /secure/db-password.txt)
sbkube deploy --app-dir .
```

### 5. 멱등성 고려

**중요**: exec 명령어는 반복 실행 시 같은 결과를 보장하지 않습니다.

```yaml
# ❌ 멱등하지 않음 (두 번째 실행 시 실패)
commands:
  - kubectl create namespace my-namespace

# ✅ 멱등함 (이미 존재해도 성공)
commands:
  - kubectl create namespace my-namespace --dry-run=client -o yaml | kubectl apply -f -
```

### 6. 타임아웃 및 긴 작업

**주의**: 오래 걸리는 명령어는 타임아웃될 수 있습니다.

```yaml
# ⚠️ 잠재적 타임아웃
commands:
  - kubectl wait --for=condition=ready pod/myapp --timeout=600s

# ✅ 백그라운드 작업 + 확인
commands:
  - kubectl apply -f manifests/long-job.yaml &
  - sleep 5
  - kubectl get jobs
```

---

## 🔄 삭제 (Cleanup)

### 자동 정리

exec 타입은 리소스를 생성하지 않으므로 자동 삭제 대상이 없습니다.

### 수동 정리

명령어가 생성한 리소스는 수동으로 삭제해야 합니다:

```bash
# 생성한 ConfigMap 삭제
kubectl delete configmap app-config -n example-exec

# 실행한 Job 삭제
kubectl delete job db-migration -n example-exec

# 네임스페이스 삭제
kubectl delete namespace example-exec
```

---

## 📚 참고 자료

- [SBKube 애플리케이션 타입 가이드](../../../docs/02-features/application-types.md)
- [SBKube 명령어 참조](../../../docs/02-features/commands.md)
- [kubectl 명령어 참조](https://kubernetes.io/docs/reference/kubectl/)
- [Bash 스크립팅 가이드](https://www.gnu.org/software/bash/manual/bash.html)

---

## 🆚 다른 타입과 비교

| 기능 | exec | action | helm | yaml |
|-----|------|--------|------|------|
| **쉘 명령어 실행** | ✅ | ❌ | ❌ | ❌ |
| **kubectl 자동 실행** | ❌ | ✅ | ❌ | ❌ |
| **Helm 차트 배포** | ❌ | ❌ | ✅ | ❌ |
| **YAML 매니페스트** | ❌ | ✅ | ❌ | ✅ |
| **사전/사후 훅** | ✅ 최적 | ⚠️ | ⚠️ | ❌ |
| **데이터베이스 마이그레이션** | ✅ 최적 | ⚠️ | ❌ | ❌ |
| **외부 API 호출** | ✅ 최적 | ❌ | ❌ | ❌ |

**선택 가이드**:
- **검증/훅/마이그레이션**: exec 타입
- **CRD/Operator 배포**: action 타입
- **애플리케이션 배포**: helm 또는 yaml 타입

---

## 💡 실전 예제

### 예제 1: 완전한 배포 파이프라인

```yaml
namespace: production

apps:
  # 1. Pre-deployment 검증
  pre-check:
    type: exec
    commands:
      - echo "=== Pre-deployment Checks ==="
      - kubectl get nodes
      - kubectl get namespaces | grep production || kubectl create namespace production
      - echo "Checks passed!"

  # 2. 데이터베이스 백업
  db-backup:
    type: exec
    commands:
      - echo "=== Database Backup ==="
      - kubectl exec -n production deploy/postgres -- pg_dump -U admin mydb > /tmp/backup-$(date +%Y%m%d).sql
      - echo "Backup completed!"
    depends_on:
      - pre-check

  # 3. 데이터베이스 마이그레이션
  db-migration:
    type: exec
    commands:
      - echo "=== Running Migrations ==="
      - kubectl exec -n production deploy/postgres -- psql -U admin -d mydb -f /migrations/latest.sql
      - echo "Migrations completed!"
    depends_on:
      - db-backup

  # 4. 애플리케이션 배포 (Helm)
  app-deploy:
    type: helm
    chart: myapp/backend
    values:
      - values.yaml
    depends_on:
      - db-migration

  # 5. Post-deployment 테스트
  post-test:
    type: exec
    commands:
      - echo "=== Post-deployment Tests ==="
      - sleep 10
      - kubectl wait --for=condition=ready pod -l app=backend -n production --timeout=300s
      - curl -f http://backend.production.svc.cluster.local/health
      - echo "Tests passed!"
    depends_on:
      - app-deploy

  # 6. Slack 알림
  notify:
    type: exec
    commands:
      - echo "=== Sending Notifications ==="
      - curl -X POST $SLACK_WEBHOOK -d '{"text":"Deployment to production completed!"}'
    depends_on:
      - post-test
```

**실행 순서**: pre-check → db-backup → db-migration → app-deploy → post-test → notify

---

**💡 팁**: exec 타입은 배포 과정의 유연성을 극대화합니다. Pre/Post 훅, 검증, 마이그레이션 등 다양한 시나리오에 활용하세요.
