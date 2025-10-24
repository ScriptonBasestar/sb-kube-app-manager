# 🔗 다중 애플리케이션 배포

> **난이도**: ⭐⭐ 중급
> **소요 시간**: 15-20분
> **사전 요구사항**: [01-getting-started.md](01-getting-started.md) 완료

---

## 📋 학습 목표

- ✅ 여러 애플리케이션을 하나의 프로젝트로 관리
- ✅ 애플리케이션 간 의존성 설정 (`depends_on`)
- ✅ 선택적 배포 (특정 앱만 배포)
- ✅ 배포 순서 제어

---

## 시나리오: 웹 애플리케이션 스택 배포

다음 구성요소를 배포합니다:
1. **PostgreSQL** - 데이터베이스 (먼저 배포)
2. **Redis** - 캐시/세션 스토어 (먼저 배포)
3. **Backend API** - PostgreSQL과 Redis에 의존
4. **Frontend** - Backend API에 의존

---

## Step 1: 프로젝트 구조

```bash
mkdir web-stack
cd web-stack
```

**디렉토리 구조**:
```
web-stack/
├── config.yaml
├── sources.yaml
└── values/
    ├── postgresql.yaml
    ├── redis.yaml
    ├── backend.yaml
    └── frontend.yaml
```

---

## Step 2: 설정 파일 작성

### `config.yaml` (의존성 포함)

```yaml
namespace: web-stack

apps:
  # 1. 데이터베이스 (의존성 없음)
  postgresql:
    type: helm
    chart: bitnami/postgresql
    version: 14.0.0
    enabled: true
    values:
      - values/postgresql.yaml

  # 2. 캐시 (의존성 없음)
  redis:
    type: helm
    chart: bitnami/redis
    version: 19.0.0
    enabled: true
    values:
      - values/redis.yaml

  # 3. Backend API (DB와 Redis 필요)
  backend:
    type: helm
    chart: bitnami/nginx  # 실제로는 custom chart 사용
    version: 15.0.0
    enabled: true
    depends_on:  # 의존성 설정
      - postgresql
      - redis
    values:
      - values/backend.yaml

  # 4. Frontend (Backend 필요)
  frontend:
    type: helm
    chart: bitnami/nginx
    version: 15.0.0
    enabled: true
    depends_on:  # 의존성 설정
      - backend
    values:
      - values/frontend.yaml
```

### `sources.yaml`

```yaml
helm_repos:
  bitnami:
    url: https://charts.bitnami.com/bitnami
```

### `values/postgresql.yaml`

```yaml
auth:
  postgresPassword: "demo-password"
  database: "webapp"
primary:
  resources:
    requests:
      cpu: 250m
      memory: 256Mi
```

### `values/redis.yaml`

```yaml
architecture: standalone
auth:
  enabled: false
master:
  resources:
    requests:
      cpu: 100m
      memory: 128Mi
```

### `values/backend.yaml`

```yaml
replicaCount: 2
resources:
  requests:
    cpu: 200m
    memory: 256Mi
```

### `values/frontend.yaml`

```yaml
replicaCount: 3
resources:
  requests:
    cpu: 100m
    memory: 128Mi
```

---

## Step 3: 전체 스택 배포

### 3.1 검증

```bash
sbkube validate
```

### 3.2 배포 순서 확인

```bash
# 의존성이 자동으로 해결됩니다:
# 1. postgresql, redis (병렬)
# 2. backend (postgresql, redis 완료 후)
# 3. frontend (backend 완료 후)

sbkube apply
```

**예상 출력**:
```
✨ SBKube `apply` 시작 ✨

🔧 Step 1: Prepare
📦 Preparing Helm app: postgresql
📦 Preparing Helm app: redis
📦 Preparing Helm app: backend
📦 Preparing Helm app: frontend

🚀 Step 3: Deploy (의존성 순서)
📦 Deploying: postgresql
✅ Deployed: postgresql
📦 Deploying: redis
✅ Deployed: redis
📦 Deploying: backend (depends on: postgresql, redis)
✅ Deployed: backend
📦 Deploying: frontend (depends on: backend)
✅ Deployed: frontend

✅ Apply completed: 4/4 apps
```

---

## Step 4: 선택적 배포

### 4.1 특정 앱만 배포

```bash
# Backend만 재배포 (업데이트 시)
sbkube apply --app backend

# Frontend와 Backend만 재배포
sbkube apply --app frontend --app backend
```

### 4.2 일부 앱 비활성화

**`config.yaml` 수정**:
```yaml
apps:
  frontend:
    type: helm
    chart: bitnami/nginx
    enabled: false  # 비활성화
    depends_on:
      - backend
```

```bash
# Frontend 제외하고 배포
sbkube apply
```

---

## Step 5: 배포 확인

```bash
# 모든 리소스 확인
kubectl get all -n web-stack

# 배포 상태
sbkube state list

# 예상 출력:
# App Name     Type   Status     Namespace
# postgresql   helm   deployed   web-stack
# redis        helm   deployed   web-stack
# backend      helm   deployed   web-stack
# frontend     helm   deployed   web-stack
```

---

## Step 6: 정리

```bash
# 전체 삭제
sbkube delete

# 특정 앱만 삭제
sbkube delete --app frontend
```

---

## 핵심 포인트

### ✅ Do's

- 의존성을 명확히 정의 (`depends_on`)
- 데이터베이스 같은 stateful 앱은 먼저 배포
- 각 앱의 values 파일을 분리하여 관리

### ❌ Don'ts

- 순환 의존성 생성 (A → B → A)
- 의존성 없이 동시 배포 시도 (수동 순서 제어 필요 시)

---

## 다음 단계

- **[03-production-deployment.md](03-production-deployment.md)** - 프로덕션 배포 전략
- **[04-customization.md](04-customization.md)** - 차트 커스터마이징

---

**작성자**: SBKube Documentation Team
**버전**: v0.4.7
