# Advanced Feature: Complex Dependencies

복잡한 의존성 체인을 관리하는 예제입니다.

## 사용 시나리오

- 멀티 티어 애플리케이션 배포
- 마이크로서비스 오케스트레이션
- 순차적 배포가 필요한 경우
- 복잡한 배포 워크플로우

## 기본 의존성

```yaml
apps:
  database:
    type: helm
    chart: cloudnative-pg/cloudnative-pg

  backend:
    type: helm
    chart: my/backend
    depends_on:
      - database  # database가 먼저 배포됨
```

## 복잡한 의존성 체인

### 4-Tier 웹 애플리케이션

```
┌─────────────┐
│  Frontend   │
└──────┬──────┘
       │ depends_on
┌──────▼──────┐
│   Backend   │
└──────┬──────┘
       │ depends_on
┌──────▼──────┬──────────┐
│  Database   │  Cache   │
└─────────────┴──────────┘
```

**config.yaml**:
```yaml
apps:
  # Layer 1: 데이터 레이어
  postgresql:
    type: helm
    chart: cloudnative-pg/cloudnative-pg

  redis:
    type: helm
    chart: prometheus-community/prometheus

  # Layer 2: 백엔드 (DB와 Cache에 의존)
  backend-api:
    type: helm
    chart: my/backend
    depends_on:
      - postgresql
      - redis

  # Layer 3: 프론트엔드 (Backend에 의존)
  frontend:
    type: helm
    chart: my/frontend
    depends_on:
      - backend-api
```

**배포 순서**:
1. `postgresql`과 `redis` (병렬)
2. `backend-api` (1 완료 후)
3. `frontend` (2 완료 후)

## 실전 예제: 마이크로서비스

### 복잡한 서비스 메시

```
Infrastructure
├─ Namespace & RBAC
├─ Database (PostgreSQL)
└─ Message Queue (RabbitMQ)
    ↓
Core Services
├─ Auth Service (depends on DB)
├─ User Service (depends on DB)
└─ Order Service (depends on DB, MQ)
    ↓
API Gateway
└─ Gateway (depends on all core services)
    ↓
Frontend
└─ Web UI (depends on Gateway)
```

**config.yaml**:
```yaml
namespace: microservices

apps:
  # === Infrastructure ===
  setup-infra:
    type: action
    actions:
      - type: apply
        path: manifests/namespace.yaml
      - type: apply
        path: manifests/rbac.yaml

  postgresql:
    type: helm
    chart: cloudnative-pg/cloudnative-pg
    depends_on:
      - setup-infra

  rabbitmq:
    type: helm
    chart: prometheus-community/prometheus
    depends_on:
      - setup-infra

  # === Core Services ===
  auth-service:
    type: helm
    chart: my/auth-service
    depends_on:
      - postgresql

  user-service:
    type: helm
    chart: my/user-service
    depends_on:
      - postgresql
      - auth-service  # Auth에 의존

  order-service:
    type: helm
    chart: my/order-service
    depends_on:
      - postgresql
      - rabbitmq
      - user-service  # User에 의존

  # === API Gateway ===
  api-gateway:
    type: helm
    chart: my/api-gateway
    depends_on:
      - auth-service
      - user-service
      - order-service

  # === Frontend ===
  web-ui:
    type: helm
    chart: my/web-ui
    depends_on:
      - api-gateway

  # === Monitoring (독립적) ===
  prometheus:
    type: helm
    chart: prometheus-community/prometheus
    # depends_on 없음 (독립적)

  # === Post-deployment Verification ===
  smoke-test:
    type: exec
    commands:
      - echo "Running smoke tests..."
      - kubectl get pods -n microservices
      - kubectl wait --for=condition=ready pod -l app=api-gateway -n microservices --timeout=300s
      - echo "All services are ready!"
    depends_on:
      - web-ui  # 모든 서비스가 배포된 후 실행
```

## 다중 의존성 (병렬 실행)

```yaml
apps:
  db-master:
    type: helm
    chart: cloudnative-pg/cloudnative-pg

  db-slave-1:
    type: helm
    chart: cloudnative-pg/cloudnative-pg
    depends_on:
      - db-master

  db-slave-2:
    type: helm
    chart: cloudnative-pg/cloudnative-pg
    depends_on:
      - db-master

  # slave-1과 slave-2는 병렬로 배포됨

  load-balancer:
    type: helm
    chart: my/haproxy
    depends_on:
      - db-master
      - db-slave-1
      - db-slave-2
```

**배포 순서**:
1. `db-master`
2. `db-slave-1`과 `db-slave-2` (병렬)
3. `load-balancer` (모든 DB 준비 후)

## 조건부 의존성

```yaml
apps:
  database:
    type: helm
    chart: cloudnative-pg/cloudnative-pg
    enabled: true

  cache:
    type: helm
    chart: prometheus-community/prometheus
    enabled: false  # 비활성화

  backend:
    type: helm
    chart: my/backend
    depends_on:
      - database
      - cache  # cache가 비활성화되어도 database만 대기
```

**동작**:
- `cache`는 `enabled: false`이므로 건너뜀
- `backend`는 `database`만 대기하고 배포됨

## 순환 의존성 (에러)

```yaml
# ❌ 잘못된 설정 (순환 의존성)
apps:
  service-a:
    type: helm
    chart: my/service-a
    depends_on:
      - service-b

  service-b:
    type: helm
    chart: my/service-b
    depends_on:
      - service-a  # 순환!
```

**에러**:
```
Error: Circular dependency detected: service-a -> service-b -> service-a
```

## 배포

```bash
# 의존성 순서대로 자동 배포
sbkube apply --app-dir .

# 특정 앱만 (의존성 무시)
sbkube apply --app-dir . --apps backend-api

# Dry-run으로 순서 확인
sbkube apply --app-dir . --dry-run
```

## 디버깅

### 배포 순서 확인

```bash
# verbose 모드로 실행
sbkube apply --app-dir . --verbose

# 출력 예시:
# Resolving dependency order...
# Deployment order: [postgresql, redis, backend-api, frontend]
```

### 의존성 그래프 시각화 (수동)

```bash
# config.yaml에서 의존성 추출
grep -A 3 "depends_on:" config.yaml
```

## 베스트 프랙티스

### 1. 레이어 구조화

```yaml
apps:
  # Layer 0: Infrastructure
  namespace-setup:
    type: action
    ...

  # Layer 1: Data
  database:
    type: helm
    ...
    depends_on: [namespace-setup]

  # Layer 2: Services
  backend:
    type: helm
    ...
    depends_on: [database]

  # Layer 3: Gateway
  api-gateway:
    type: helm
    ...
    depends_on: [backend]

  # Layer 4: Frontend
  frontend:
    type: helm
    ...
    depends_on: [api-gateway]
```

### 2. 명확한 네이밍

```yaml
apps:
  01-infra-setup:      # 01 prefix로 순서 표시
    ...

  02-database-postgres:
    depends_on: [01-infra-setup]

  03-backend-api:
    depends_on: [02-database-postgres]
```

### 3. 주석 활용

```yaml
apps:
  backend:
    type: helm
    chart: my/backend
    depends_on:
      - postgresql  # DB 연결 필요
      - redis       # 세션 스토어
      - rabbitmq    # 비동기 작업 큐
```

## 정리

```bash
sbkube delete --app-dir .
```

## 관련 예제

- [Advanced Feature: Enabled Flag](../01-enabled-flag/)
- [Use Case: Multi-Tier Web Stack](../../use-cases/02-wiki-stack/)
