# Dependency Chain Example

복잡한 의존성 체인을 가진 애플리케이션 배포 예제입니다.

이 예제는 다음을 보여줍니다:
- **9단계 배포 파이프라인**: 검증 → 스토리지 → 데이터베이스 → 초기화 → 백엔드 → 프론트엔드 → Ingress → 검증
- **다양한 앱 타입 혼합**: exec, action, helm, yaml
- **명시적 의존성**: `depends_on`을 사용한 순차/병렬 제어
- **실전 패턴**: 헬스 체크, 리소스 초기화, 단계별 검증

## 📋 배포 순서

```
Phase 1: verify-cluster (exec)
           ↓
Phase 2: setup-storage (action)
           ↓
Phase 3: postgresql (helm) ← ─┐
           ↓                   │ (병렬)
Phase 4: redis (helm) ← ───────┘
           ↓
Phase 5: init-database (exec)
           ↓
Phase 6: backend-api (yaml)
           ↓
Phase 7: frontend (yaml)
           ↓
Phase 8: ingress (yaml)
           ↓
Phase 9: verify-deployment (exec)
```

### 의존성 관계

| Phase | 앱 이름 | 타입 | depends_on | 설명 |
|-------|---------|------|------------|------|
| 1 | verify-cluster | exec | - | 클러스터 검증 |
| 2 | setup-storage | action | verify-cluster | StorageClass, PVC 생성 |
| 3 | postgresql | helm | setup-storage | DB 배포 (스토리지 필요) |
| 4 | redis | helm | verify-cluster | 캐시 배포 (postgresql과 병렬) |
| 5 | init-database | exec | postgresql | DB 스키마 초기화 |
| 6 | backend-api | yaml | postgresql, redis, init-database | API 서버 (DB+캐시 필요) |
| 7 | frontend | yaml | backend-api | 웹 UI (API 필요) |
| 8 | ingress | yaml | frontend | 트래픽 라우팅 |
| 9 | verify-deployment | exec | ingress | 최종 검증 |

## 🎯 주요 패턴

### 패턴 1: 병렬 실행

**postgresql**과 **redis**는 동시에 실행됩니다 (독립적 의존성):

```yaml
postgresql:
  depends_on:
    - setup-storage  # ← 스토리지만 필요

redis:
  depends_on:
    - verify-cluster  # ← 클러스터 검증만 필요
```

**결과**: Phase 3과 Phase 4가 동시에 실행되어 배포 시간 단축

### 패턴 2: 다중 의존성

**backend-api**는 여러 앱에 동시에 의존:

```yaml
backend-api:
  depends_on:
    - postgresql      # DB 필요
    - redis           # 캐시 필요
    - init-database   # 스키마 초기화 필요
```

**결과**: 세 앱이 모두 완료된 후에만 실행

### 패턴 3: 초기화 작업

**init-database**는 DB 준비 후 스키마 생성:

```yaml
init-database:
  type: exec
  depends_on:
    - postgresql
  commands:
    - sleep 10  # DB 시작 대기
    - kubectl wait --for=condition=ready pod -l app.kubernetes.io/name=postgresql
    - echo "-- Initializing schema"
```

### 패턴 4: 검증 단계

**verify-deployment**는 모든 배포 완료 후 검증:

```yaml
verify-deployment:
  type: exec
  depends_on:
    - ingress  # 마지막 컴포넌트
  commands:
    - kubectl get all -n dependency-demo
    - kubectl wait --for=condition=ready pod -l app=backend-api
    - kubectl wait --for=condition=ready pod -l app=frontend
```

## 🚀 실행 방법

### 1. 전체 파이프라인 실행

```bash
# 한 번에 모든 단계 실행 (자동 순서 제어)
sbkube apply --app-dir examples/dependency-chain

# 단계별 실행 (수동 제어)
sbkube prepare --app-dir examples/dependency-chain
sbkube build --app-dir examples/dependency-chain
sbkube deploy --app-dir examples/dependency-chain
```

**실행 순서 (자동)**:
```
verify-cluster
  → setup-storage
    → postgresql + redis (병렬)
      → init-database
        → backend-api
          → frontend
            → ingress
              → verify-deployment
```

### 2. 특정 단계까지만 실행

```bash
# Phase 5까지만 (데이터베이스 준비)
sbkube deploy --app-dir examples/dependency-chain --app init-database

# Phase 6까지 (백엔드 포함)
sbkube deploy --app-dir examples/dependency-chain --app backend-api
```

### 3. 단계별 수동 실행

```bash
# Phase 1: 검증
sbkube deploy --app-dir examples/dependency-chain --app verify-cluster

# Phase 2: 스토리지
sbkube deploy --app-dir examples/dependency-chain --app setup-storage

# Phase 3-4: 데이터베이스 (병렬)
sbkube deploy --app-dir examples/dependency-chain --app postgresql
sbkube deploy --app-dir examples/dependency-chain --app redis

# Phase 5: 초기화
sbkube deploy --app-dir examples/dependency-chain --app init-database

# Phase 6-9: 애플리케이션
sbkube deploy --app-dir examples/dependency-chain --app backend-api
sbkube deploy --app-dir examples/dependency-chain --app frontend
sbkube deploy --app-dir examples/dependency-chain --app ingress
sbkube deploy --app-dir examples/dependency-chain --app verify-deployment
```

## 🔍 검증

### 배포 진행 상황 확인

```bash
# 전체 리소스 확인
kubectl get all -n dependency-demo

# Pod 상태
kubectl get pods -n dependency-demo -o wide

# 각 Phase별 확인
kubectl get pods -n dependency-demo -l tier=backend
kubectl get pods -n dependency-demo -l tier=frontend

# Helm 릴리스 확인
helm list -n dependency-demo
```

### 의존성 순서 확인

```bash
# Pod 생성 시간으로 순서 확인
kubectl get pods -n dependency-demo --sort-by=.metadata.creationTimestamp

# 예상 순서:
# 1. postgresql-0, redis-master-0 (거의 동시)
# 2. backend-api-xxxxx
# 3. frontend-xxxxx
```

### 서비스 연결 확인

```bash
# ConfigMap 확인 (backend-api가 올바른 DB/Redis 주소 참조)
kubectl get configmap backend-config -n dependency-demo -o yaml

# Service 확인
kubectl get svc -n dependency-demo

# Ingress 확인
kubectl get ingress -n dependency-demo
```

### 로그 확인

```bash
# 초기화 로그 (init-database)
kubectl logs -n dependency-demo -l job-name=init-database

# 백엔드 로그
kubectl logs -n dependency-demo -l app=backend-api

# 프론트엔드 로그
kubectl logs -n dependency-demo -l app=frontend
```

## 💡 사용 사례

### Use Case 1: 전통적인 3-Tier 아키텍처

```
Database Tier (Phase 3-5)
  → Backend Tier (Phase 6)
    → Frontend Tier (Phase 7)
      → Ingress (Phase 8)
```

각 티어가 순차적으로 배포되며, 하위 티어가 준비된 후에만 상위 티어 배포.

### Use Case 2: CI/CD 파이프라인 통합

```bash
# CI/CD 스크립트에서 사용
#!/bin/bash
set -e

# 환경 검증
sbkube deploy --app verify-cluster || exit 1

# 인프라 준비
sbkube deploy --app setup-storage || exit 1

# 데이터베이스 배포
sbkube deploy --app postgresql --app redis || exit 1

# 애플리케이션 배포
sbkube deploy --app backend-api --app frontend || exit 1

# 최종 검증
sbkube deploy --app verify-deployment || exit 1
```

### Use Case 3: 단계적 롤백

배포 실패 시 역순으로 정리:

```bash
# Phase 9 → Phase 1 역순
kubectl delete -f manifests/ingress.yaml
kubectl delete -f manifests/frontend/
kubectl delete -f manifests/backend/
helm uninstall postgresql -n dependency-demo
helm uninstall redis -n dependency-demo
kubectl delete -f manifests/storage/
```

### Use Case 4: 선택적 컴포넌트 배포

개발 환경에서는 일부만:

```yaml
# config-dev.yaml (개발 환경)
apps:
  verify-cluster: { ... }
  postgresql: { ... }
  redis: { ... }
  backend-api: { ... }
  # frontend, ingress 제외 (로컬 개발 서버 사용)
```

## 🎯 핵심 기능

### 1. exec 타입 활용

**용도**:
- 배포 전/후 검증
- 리소스 초기화 (DB 스키마, 시드 데이터)
- 헬스 체크 및 상태 확인

**예시**:
```yaml
verify-cluster:
  type: exec
  commands:
    - kubectl version --client
    - kubectl cluster-info
    - kubectl get nodes
```

### 2. action 타입 활용

**용도**:
- CRD, Operator 설치
- 스토리지 클래스, PVC 생성
- 리소스 정리 (delete)

**예시**:
```yaml
setup-storage:
  type: action
  actions:
    - type: apply
      path: manifests/storage/storageclass.yaml
    - type: apply
      path: manifests/storage/pvc.yaml
```

### 3. depends_on 체인

**단순 순서**:
```yaml
frontend:
  depends_on:
    - backend-api
```

**다중 의존성**:
```yaml
backend-api:
  depends_on:
    - postgresql
    - redis
    - init-database
```

**병렬 실행** (공통 부모):
```yaml
postgresql:
  depends_on:
    - setup-storage

redis:
  depends_on:
    - verify-cluster  # ← postgresql과 독립적
```

### 4. 대기 및 검증 패턴

```yaml
init-database:
  type: exec
  commands:
    # 1. 대기
    - sleep 10

    # 2. 조건부 대기
    - kubectl wait --for=condition=ready pod -l app=postgresql --timeout=120s

    # 3. 작업 수행
    - echo "CREATE TABLE ..." > /tmp/schema.sql

    # 4. 완료 확인
    - echo "✅ Initialization completed"
```

## 📊 배포 시간 분석

### 순차 실행 시 (의존성 무시)

```
verify-cluster:     10초
setup-storage:      15초
postgresql:         60초
redis:              30초
init-database:      20초
backend-api:        30초
frontend:           25초
ingress:            10초
verify-deployment:  15초
───────────────────────
총 시간:           215초 (3분 35초)
```

### 병렬 실행 시 (최적화)

```
verify-cluster:                        10초
  → setup-storage:                     15초
    → postgresql + redis (병렬):       60초 (max)
      → init-database:                 20초
        → backend-api:                 30초
          → frontend:                  25초
            → ingress:                 10초
              → verify-deployment:     15초
───────────────────────────────────────────
총 시간:                              185초 (3분 5초)

절감 시간: 30초 (redis 병렬 실행)
```

## 🐛 Troubleshooting

### 문제 1: 의존성 순서 위반

**증상**: backend-api가 postgresql보다 먼저 시작됨

**원인**: `depends_on`이 누락되었거나 잘못됨

**해결**:
```yaml
backend-api:
  depends_on:
    - postgresql  # ← 추가
    - redis
```

### 문제 2: 무한 대기

**증상**: `kubectl wait` 명령어가 타임아웃

**원인**: Pod가 Ready 상태가 되지 않음 (이미지 pull 실패, 설정 오류 등)

**해결**:
```bash
# Pod 상태 확인
kubectl describe pod -n dependency-demo -l app=postgresql

# 이벤트 확인
kubectl get events -n dependency-demo --sort-by='.lastTimestamp'

# 로그 확인
kubectl logs -n dependency-demo <pod-name>
```

### 문제 3: StorageClass 없음

**증상**: PVC가 Pending 상태

**원인**: 클러스터에 StorageClass가 없음

**해결**:
```bash
# 기존 StorageClass 확인
kubectl get storageclass

# k3s의 기본 provisioner 사용
# manifests/storage/storageclass.yaml 수정:
provisioner: rancher.io/local-path  # k3s 기본 프로비저너
```

### 문제 4: 의존성 순환

**증상**: `Circular dependency detected` 오류

**원인**: A → B → C → A 같은 순환 참조

**해결**:
```yaml
# 잘못된 예 (순환)
app-a:
  depends_on: [app-b]
app-b:
  depends_on: [app-c]
app-c:
  depends_on: [app-a]  # ← 순환!

# 올바른 예 (비순환)
app-a:
  depends_on: []
app-b:
  depends_on: [app-a]
app-c:
  depends_on: [app-b]
```

### 문제 5: exec 명령어 실패

**증상**: exec 타입 앱이 실패하고 파이프라인 중단

**원인**: kubectl 명령어 오류, 권한 부족

**해결**:
```bash
# 로그 확인 (sbkube 출력)
sbkube deploy --app verify-cluster

# kubectl 접근 확인
kubectl config current-context
kubectl auth can-i create pods --namespace=dependency-demo

# 수동 테스트
kubectl version --client
kubectl cluster-info
```

## 📚 관련 예제

- [app-types/04-action](../app-types/04-action/) - action 타입 기본
- [app-types/05-exec](../app-types/05-exec/) - exec 타입 기본
- [advanced-features/02-complex-dependencies](../advanced-features/02-complex-dependencies/) - 복잡한 의존성
- [multi-app-groups](../multi-app-groups/) - 멀티 그룹 배포

## 🔑 핵심 정리

1. **의존성 체인 설계**
   - 최소 의존성 원칙: 꼭 필요한 것만
   - 병렬 가능성 최대화: 독립적 앱은 동시 실행
   - 명확한 순서: 데이터베이스 → 백엔드 → 프론트엔드

2. **타입별 역할**
   - `exec`: 검증, 초기화, 상태 확인
   - `action`: CRD, 스토리지, 정리 작업
   - `helm`: 복잡한 애플리케이션 (DB, 캐시)
   - `yaml`: 커스텀 애플리케이션 (API, 웹)

3. **실전 패턴**
   - 시작 전 검증 (`verify-cluster`)
   - 완료 후 검증 (`verify-deployment`)
   - 대기 로직 (`kubectl wait`)
   - 선택적 컴포넌트 (`enabled: false`)

4. **배포 최적화**
   - 병렬 실행으로 시간 단축
   - 단계별 롤백 지점 확보
   - CI/CD 통합 용이
