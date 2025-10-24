# App Type: Exec

커스텀 명령어를 실행하는 예제입니다.

## 사용 시나리오

- 배포 전후 스크립트 실행
- 데이터베이스 마이그레이션
- 헬스 체크
- 환경 검증
- 정리 작업

## 예제 1: 배포 전 검증

### config.yaml
```yaml
namespace: exec-demo

apps:
  # 1. 사전 체크
  pre-deployment-check:
    type: exec
    commands:
      - echo "=== Pre-deployment Health Check ==="
      - kubectl version --client
      - kubectl cluster-info
      - kubectl get nodes
      - echo "✅ Cluster is ready"

  # 2. 애플리케이션 배포
  my-app:
    type: helm
    chart: bitnami/nginx
    depends_on:
      - pre-deployment-check

  # 3. 배포 후 검증
  post-deployment-verify:
    type: exec
    commands:
      - echo "=== Post-deployment Verification ==="
      - kubectl get pods -n exec-demo
      - kubectl get svc -n exec-demo
      - echo "✅ Deployment completed"
    depends_on:
      - my-app
```

## 예제 2: 데이터베이스 마이그레이션

### config.yaml
```yaml
namespace: exec-demo

apps:
  # 1. PostgreSQL 배포
  postgresql:
    type: helm
    chart: bitnami/postgresql

  # 2. DB 마이그레이션 실행
  db-migration:
    type: exec
    commands:
      - echo "Waiting for PostgreSQL to be ready..."
      - kubectl wait --for=condition=ready pod -l app.kubernetes.io/name=postgresql -n exec-demo --timeout=300s
      - echo "Running database migrations..."
      - kubectl exec -n exec-demo postgresql-0 -- psql -U postgres -c "CREATE DATABASE IF NOT EXISTS myapp;"
      - echo "✅ Migration completed"
    depends_on:
      - postgresql
```

## 실행

```bash
# 전체 워크플로우 실행
sbkube apply --app-dir .

# 특정 앱만 실행
sbkube apply --app-dir . --apps pre-deployment-check
```

## 주의사항

### 1. 멱등성
exec 명령어는 멱등성이 보장되지 않습니다. 여러 번 실행해도 안전한 명령어를 사용하세요.

**좋은 예**:
```yaml
commands:
  - kubectl get pods  # 읽기 전용
  - echo "Hello"      # 출력만
```

**나쁜 예**:
```yaml
commands:
  - kubectl create namespace test  # 두 번 실행하면 에러
  - rm -rf /data/*                 # 위험!
```

### 2. 에러 처리
명령어가 실패하면 전체 워크플로우가 중단됩니다.

### 3. 환경 변수
kubectl의 kubeconfig와 현재 context를 사용합니다.

## 고급 예제

### 조건부 명령어 실행

```yaml
apps:
  conditional-cleanup:
    type: exec
    enabled: false  # 필요시 활성화
    commands:
      - kubectl delete pods --field-selector=status.phase=Succeeded -n exec-demo
      - kubectl delete pods --field-selector=status.phase=Failed -n exec-demo
```

### 멀티라인 스크립트

```yaml
apps:
  complex-script:
    type: exec
    commands:
      - |
        echo "Starting complex operation..."
        for pod in $(kubectl get pods -n exec-demo -o name); do
          echo "Checking $pod"
          kubectl describe -n exec-demo $pod | grep -i error || true
        done
        echo "Check completed"
```

## 정리

```bash
sbkube delete --app-dir .
```

## 보안 고려사항

⚠️ **주의**: exec 타입은 임의의 명령어를 실행할 수 있습니다.

- 신뢰할 수 있는 명령어만 사용
- 민감한 정보를 명령어에 직접 포함하지 말 것
- 프로덕션 환경에서는 신중히 사용

## 관련 예제

- [App Type: Action](../04-action/) - kubectl apply/delete 액션
- [Use Case: Dev Environment](../../use-cases/01-dev-environment/)
