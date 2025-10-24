# Apply Workflow - 통합 배포 워크플로우

SBKube의 **`apply`** 명령어를 사용한 통합 워크플로우 예제입니다.

## 📋 목차

- [개요](#-개요)
- [apply 명령어란?](#-apply-명령어란)
- [설정 구조](#-설정-구조)
- [실행 방법](#-실행-방법)
- [워크플로우 상세](#-워크플로우-상세)
- [의존성 관리](#-의존성-관리)
- [비교: apply vs 단계별 실행](#-비교-apply-vs-단계별-실행)

---

## 🎯 개요

이 예제는 **Redis + Nginx** 스택을 `sbkube apply` 명령어로 한 번에 배포하는 방법을 보여줍니다.

**배포 애플리케이션**:
- **Redis**: 캐싱 레이어 (Bitnami Helm 차트)
- **Nginx**: 웹 서버 (Bitnami Helm 차트)
- **의존성**: Nginx는 Redis 이후 배포 (`depends_on`)

---

## 🔧 apply 명령어란?

`sbkube apply`는 다음 4단계를 **자동으로 순차 실행**합니다:

```
1. prepare  → Helm 리포지토리 추가 및 차트 다운로드
   ↓
2. build    → 차트 커스터마이징 (overrides/removes 적용)
   ↓
3. template → YAML 매니페스트 렌더링 (선택적)
   ↓
4. deploy   → Kubernetes 클러스터에 배포
```

### 단계별 실행 vs apply

| 방식 | 명령어 | 장점 | 단점 |
|-----|--------|------|------|
| **단계별** | `prepare` → `build` → `deploy` | 각 단계 확인 가능 | 번거로움, 실수 가능 |
| **apply** | `apply` | 간편, 빠름, 실수 방지 | 중간 단계 확인 불가 |

---

## 📝 설정 구조

### config.yaml

```yaml
namespace: apply-demo

apps:
  # 1. Redis (먼저 배포)
  redis:
    type: helm
    chart: bitnami/redis
    version: 17.13.2
    values:
      - redis.yaml

  # 2. Nginx (Redis 이후 배포)
  nginx:
    type: helm
    chart: bitnami/nginx
    version: 15.0.0
    values:
      - nginx.yaml
    depends_on:
      - redis  # Redis 배포 완료 후 실행
```

### sources.yaml

```yaml
cluster: apply-demo-cluster
kubeconfig: ~/.kube/config

helm_repos:
  bitnami: https://charts.bitnami.com/bitnami
```

### values/redis.yaml

```yaml
architecture: standalone
auth:
  enabled: true
  password: "demo-password"
master:
  persistence:
    enabled: true
    size: 1Gi
  resources:
    limits:
      cpu: 250m
      memory: 256Mi
```

### values/nginx.yaml

```yaml
replicaCount: 2
service:
  type: ClusterIP
  port: 80
resources:
  limits:
    cpu: 250m
    memory: 256Mi
```

---

## 🚀 실행 방법

### 기본 사용법 (apply)

```bash
cd examples/apply-workflow

# 전체 워크플로우 실행 (prepare → build → deploy)
sbkube apply
```

**실행 과정**:
```
✅ [prepare] Bitnami Helm 리포지토리 추가
✅ [prepare] Redis 차트 다운로드 (17.13.2)
✅ [prepare] Nginx 차트 다운로드 (15.0.0)
✅ [build] Redis 차트 빌드
✅ [build] Nginx 차트 빌드
✅ [deploy] Redis 배포 (apply-demo 네임스페이스)
⏳ [deploy] Redis 준비 대기...
✅ [deploy] Nginx 배포 (Redis 이후)
✅ 완료!
```

### 특정 앱만 배포

```bash
# Redis만 배포
sbkube apply --app redis

# Nginx만 배포 (Redis가 이미 배포되어 있어야 함)
sbkube apply --app nginx
```

### Dry-run 모드

```bash
# 실제 배포 없이 계획 확인
sbkube apply --dry-run
```

**출력 예시**:
```
[DRY-RUN] prepare: bitnami 리포지토리 추가
[DRY-RUN] prepare: redis 차트 다운로드 (17.13.2)
[DRY-RUN] prepare: nginx 차트 다운로드 (15.0.0)
[DRY-RUN] build: redis 차트 빌드
[DRY-RUN] build: nginx 차트 빌드
[DRY-RUN] deploy: redis (apply-demo)
[DRY-RUN] deploy: nginx (apply-demo, depends_on: redis)
```

### 네임스페이스 오버라이드

```bash
# config.yaml의 namespace 무시하고 다른 네임스페이스에 배포
sbkube apply --namespace production
```

---

## 🔍 워크플로우 상세

### 1단계: prepare

**목적**: 외부 소스 준비

**수행 작업**:
- Helm 리포지토리 추가 (`helm repo add bitnami ...`)
- Helm 리포지토리 업데이트 (`helm repo update`)
- Helm 차트 다운로드 (`helm pull bitnami/redis --version 17.13.2`)

**결과**:
```
charts/
├── redis/
│   └── redis/  # bitnami/redis:17.13.2
└── nginx/
    └── nginx/  # bitnami/nginx:15.0.0
```

### 2단계: build

**목적**: 차트 커스터마이징

**수행 작업**:
- `charts/` → `build/` 복사
- `overrides/` 적용 (이 예제에서는 없음)
- `removes` 파일 제거 (이 예제에서는 없음)

**결과**:
```
build/
├── redis/  # 커스터마이즈된 Redis 차트
└── nginx/  # 커스터마이즈된 Nginx 차트
```

### 3단계: template (apply는 생략)

**목적**: YAML 매니페스트 렌더링

**수행 작업** (apply는 이 단계를 건너뜀):
- `helm template` 실행
- `rendered/` 디렉토리에 YAML 저장

**참고**: `sbkube template`로 별도 실행 가능

### 4단계: deploy

**목적**: Kubernetes 클러스터 배포

**수행 작업**:
1. Redis 배포: `helm upgrade --install redis build/redis/ -n apply-demo`
2. Redis 준비 대기
3. Nginx 배포: `helm upgrade --install nginx build/nginx/ -n apply-demo`

**결과**:
```
NAME    NAMESPACE   REVISION  STATUS    CHART
redis   apply-demo  1         deployed  redis-17.13.2
nginx   apply-demo  1         deployed  nginx-15.0.0
```

---

## 🔗 의존성 관리

### depends_on 동작

```yaml
apps:
  redis:
    type: helm
    chart: bitnami/redis
    # depends_on 없음 → 먼저 배포

  nginx:
    type: helm
    chart: bitnami/nginx
    depends_on:
      - redis  # Redis 완료 후 실행
```

**실행 순서**:
```
1. Redis 배포 시작
2. Redis Pod가 Ready 상태가 될 때까지 대기
3. Nginx 배포 시작
```

### 다중 의존성

```yaml
apps:
  database:
    type: helm
    chart: bitnami/postgresql

  cache:
    type: helm
    chart: bitnami/redis

  backend:
    type: helm
    chart: myapp/backend
    depends_on:
      - database  # PostgreSQL 먼저
      - cache     # Redis 먼저
```

**실행 순서**:
```
1. database, cache 병렬 배포
2. 둘 다 Ready 대기
3. backend 배포
```

---

## 🔍 배포 확인

### Helm 릴리스 확인

```bash
helm list -n apply-demo
```

**예상 출력**:
```
NAME   NAMESPACE   REVISION  STATUS    CHART          APP VERSION
redis  apply-demo  1         deployed  redis-17.13.2  7.2.0
nginx  apply-demo  1         deployed  nginx-15.0.0   1.25.0
```

### Pod 상태 확인

```bash
kubectl get pods -n apply-demo
```

**예상 출력**:
```
NAME                     READY   STATUS    RESTARTS   AGE
redis-master-0           1/1     Running   0          2m
nginx-xxxx-yyyy          1/1     Running   0          1m
nginx-xxxx-zzzz          1/1     Running   0          1m
```

### Service 확인

```bash
kubectl get svc -n apply-demo
```

**예상 출력**:
```
NAME            TYPE        CLUSTER-IP      PORT(S)
redis-master    ClusterIP   10.43.100.1     6379/TCP
nginx           ClusterIP   10.43.100.2     80/TCP
```

---

## 🆚 비교: apply vs 단계별 실행

### 방법 1: apply (권장)

```bash
sbkube apply
```

**장점**:
- ✅ 간단: 한 줄로 전체 배포
- ✅ 빠름: 자동 최적화
- ✅ 안전: 의존성 순서 자동 처리
- ✅ 에러 처리: 단계별 롤백 지원

**단점**:
- ❌ 중간 확인 불가: 각 단계 결과를 확인하기 어려움

### 방법 2: 단계별 실행

```bash
sbkube prepare
sbkube build
sbkube deploy
```

**장점**:
- ✅ 세밀한 제어: 각 단계마다 결과 확인
- ✅ 디버깅 용이: 문제 발생 단계 파악 쉬움
- ✅ 선택적 실행: 필요한 단계만 실행 가능

**단점**:
- ❌ 번거로움: 3번 명령어 입력
- ❌ 실수 가능: 순서를 잘못 입력할 수 있음

### 방법 3: template까지 포함

```bash
sbkube prepare
sbkube build
sbkube template --output-dir /tmp/rendered
# 렌더링 결과 확인 후
sbkube deploy
```

**용도**:
- 배포 전 최종 YAML 매니페스트 검토
- GitOps 워크플로우 (렌더링된 YAML을 Git에 커밋)

---

## 💡 실전 시나리오

### 시나리오 1: 개발 환경 빠른 배포

```bash
# 개발 환경은 속도 중시 → apply 사용
sbkube apply --namespace dev
```

### 시나리오 2: 프로덕션 신중한 배포

```bash
# 프로덕션은 검증 중시 → 단계별 실행
sbkube prepare
sbkube build
sbkube template --output-dir /tmp/rendered

# 렌더링 결과 검토
cat /tmp/rendered/*.yaml

# 문제 없으면 배포
sbkube deploy --namespace production
```

### 시나리오 3: CI/CD 파이프라인

```yaml
# .gitlab-ci.yml
deploy:
  script:
    - sbkube apply --namespace $CI_ENVIRONMENT_NAME --dry-run  # 검증
    - sbkube apply --namespace $CI_ENVIRONMENT_NAME             # 배포
```

---

## 🔄 업데이트 및 삭제

### 업데이트

```bash
# values 파일 수정 후
sbkube apply  # 자동으로 helm upgrade 실행
```

### 삭제

```bash
# 전체 삭제
sbkube delete --namespace apply-demo

# 특정 앱만 삭제
sbkube delete --namespace apply-demo --app nginx
```

---

## ⚠️ 주의사항

### 1. depends_on 순환 참조 금지

```yaml
# ❌ 잘못된 설정
apps:
  app-a:
    depends_on: [app-b]
  app-b:
    depends_on: [app-a]  # 순환 참조!
```

**결과**: 배포 실패 (무한 대기)

### 2. apply는 template를 건너뜀

`sbkube apply`는 template 단계를 실행하지 않습니다.

**렌더링 결과가 필요하면**:
```bash
sbkube template --output-dir /tmp/rendered
sbkube apply  # template 결과는 사용하지 않음
```

### 3. 네임스페이스 충돌

```bash
# ❌ 이미 존재하는 네임스페이스에 다른 설정으로 배포 시도
sbkube apply --namespace existing-namespace  # 충돌 가능
```

**해결**: `--force` 옵션 또는 기존 릴리스 삭제 후 재배포

---

## 📚 참고 자료

- [SBKube 명령어 참조](../../docs/02-features/commands.md)
- [의존성 관리 가이드](../../docs/02-features/dependency-management.md)
- [Helm Upgrade 참조](https://helm.sh/docs/helm/helm_upgrade/)

---

## 🔗 관련 예제

- [force-update/](../force-update/) - `--force` 옵션 사용 예제
- [state-management/](../state-management/) - 상태 관리 (history, rollback)
- [complete-workflow/](../complete-workflow/) - 전체 워크플로우 상세 예제

---

**💡 팁**: 개발 환경에서는 `apply`로 빠르게 배포하고, 프로덕션에서는 단계별 실행으로 신중하게 배포하세요.
