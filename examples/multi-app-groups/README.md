# Multi-App Groups Example

여러 앱 그룹을 관리하고 배포하는 방법을 시연합니다.

이 예제는 다음을 보여줍니다:
- **자동 탐색**: 모든 `sbkube.yaml`이 있는 디렉토리 자동 발견
- **선택적 배포**: `app_dirs`로 특정 그룹만 배포
- **다중 앱 타입**: Helm과 YAML 매니페스트 혼합 사용
- **계층적 구조**: 티어별(frontend, backend, database) 그룹화

## 📁 디렉토리 구조

```
multi-app-groups/
├── sbkube.yaml               # 자동 탐색 (모든 그룹)
├── sources-selective.yaml     # 선택적 배포 (일부 그룹만)
├── frontend/
│   └── sbkube.yaml           # Nginx 프론트엔드
├── backend/
│   ├── sbkube.yaml           # API 서버 (YAML 매니페스트)
│   ├── deployment.yaml
│   └── service.yaml
└── database/
    └── sbkube.yaml           # PostgreSQL + Redis
```

## 🎯 배포 시나리오

### 시나리오 1: 모든 앱 그룹 배포 (자동 탐색)

**sbkube.yaml** 사용 - `app_dirs` 미지정 시 자동으로 `frontend/`, `backend/`, `database/` 모두 발견

```bash
# 모든 그룹 자동 탐색 및 배포
sbkube apply --app-dir examples/multi-app-groups

# 또는 명시적으로
sbkube apply --app-dir examples/multi-app-groups --source sbkube.yaml
```

**배포되는 앱**:
- `frontend/` → nginx-frontend (Helm)
- `backend/` → api-server (YAML)
- `database/` → postgres-database, redis-cache (Helm)

### 시나리오 2: 선택적 그룹 배포 (app_dirs)

**sources-selective.yaml** 사용 - `app_dirs`로 frontend와 database만 지정

```bash
# 특정 그룹만 배포
sbkube apply --app-dir examples/multi-app-groups --source sources-selective.yaml
```

**배포되는 앱**:
- `frontend/` → nginx-frontend (Helm)
- `database/` → postgres-database, redis-cache (Helm)
- ❌ `backend/` → **배포되지 않음** (app_dirs에 없음)

### 시나리오 3: 단일 그룹만 배포

```bash
# frontend 그룹만 배포
sbkube apply --app-dir examples/multi-app-groups --app-config-dir frontend

# backend 그룹만 배포
sbkube apply --app-dir examples/multi-app-groups --app-config-dir backend

# database 그룹만 배포
sbkube apply --app-dir examples/multi-app-groups --app-config-dir database
```

## 🚀 실행 방법

### 1. 전체 워크플로우 (모든 그룹)

```bash
# 준비 (Helm 차트 다운로드)
sbkube prepare --app-dir examples/multi-app-groups

# 빌드 (차트 커스터마이징)
sbkube build --app-dir examples/multi-app-groups

# 템플릿 생성 (dry-run)
sbkube template --app-dir examples/multi-app-groups --output-dir rendered

# 배포
sbkube deploy --app-dir examples/multi-app-groups

# 또는 한 번에
sbkube apply --app-dir examples/multi-app-groups
```

### 2. 선택적 배포 (frontend + database만)

```bash
sbkube apply --app-dir examples/multi-app-groups --source sources-selective.yaml
```

### 3. 단계별 배포 (티어별 순차 배포)

```bash
# Step 1: 데이터베이스 티어 먼저
sbkube apply --app-dir examples/multi-app-groups --app-config-dir database

# Step 2: 백엔드 티어
sbkube apply --app-dir examples/multi-app-groups --app-config-dir backend

# Step 3: 프론트엔드 티어 마지막
sbkube apply --app-dir examples/multi-app-groups --app-config-dir frontend
```

## 🔍 검증

### 배포 확인

```bash
# 네임스페이스 확인
kubectl get all -n multi-app-demo

# Helm 릴리스 확인
helm list -n multi-app-demo

# Pod 상태
kubectl get pods -n multi-app-demo

# Service 확인
kubectl get svc -n multi-app-demo
```

**예상 출력**:
```
NAME                                         READY   STATUS    RESTARTS   AGE
pod/nginx-frontend-xxxxx                     1/1     Running   0          2m
pod/api-server-xxxxx                         1/1     Running   0          2m
pod/postgres-database-0                      1/1     Running   0          2m
pod/redis-cache-master-0                     1/1     Running   0          2m
```

### 앱 그룹별 확인

```bash
# Frontend 그룹
kubectl get deploy,svc -n multi-app-demo -l tier=frontend
# 또는 Helm으로
helm get values nginx-frontend -n multi-app-demo

# Backend 그룹
kubectl get deploy,svc -n multi-app-demo -l tier=backend

# Database 그룹
kubectl get pods,svc -n multi-app-demo | grep -E 'postgres|redis'
```

### 자동 탐색 동작 확인

```bash
# sbkube가 발견한 앱 그룹 확인 (prepare 단계에서 로그 확인)
sbkube prepare --app-dir examples/multi-app-groups

# 출력 예시:
# Found app groups: frontend, backend, database
# Processing: frontend/sbkube.yaml
# Processing: backend/sbkube.yaml
# Processing: database/sbkube.yaml
```

## 💡 사용 사례

### Use Case 1: 마이크로서비스 아키텍처

티어별로 앱을 그룹화하여 관리:
- `frontend/` - 웹 UI 서비스들
- `backend/` - API 게이트웨이, 비즈니스 로직 서비스들
- `database/` - 데이터 저장소들 (PostgreSQL, Redis, MongoDB 등)

### Use Case 2: 환경별 배포

개발/스테이징/프로덕션 환경별로 다른 그룹 배포:
```bash
# 개발 환경: 모든 서비스
sbkube apply -f sbkube.yaml --source sources-dev.yaml

# 프로덕션: frontend + database만 (backend는 다른 클러스터)
sbkube apply -f sbkube.yaml --source sources-prd.yaml
```

### Use Case 3: 점진적 롤아웃

단계적으로 서비스 배포:
```bash
# Phase 1: 인프라 (database)
sbkube apply -f sbkube.yaml --app-config-dir database

# Phase 2: 백엔드 서비스
sbkube apply -f sbkube.yaml --app-config-dir backend

# Phase 3: 프론트엔드 (사용자 트래픽 받음)
sbkube apply -f sbkube.yaml --app-config-dir frontend
```

## 🎯 핵심 기능

### 1. 자동 탐색 (Auto-Discovery)

**sbkube.yaml** - `app_dirs` 없음:
```yaml
kubeconfig: ~/.kube/config
kubeconfig_context: default
# app_dirs를 지정하지 않으면 자동 탐색
```

SBKube가 자동으로 `frontend/`, `backend/`, `database/`를 발견합니다.

### 2. 선택적 배포 (Selective Deployment)

**sources-selective.yaml** - `app_dirs` 명시:
```yaml
app_dirs:
  - frontend
  - database
  # backend 제외
```

명시된 그룹만 배포됩니다.

### 3. 다중 앱 타입 혼합

같은 네임스페이스에서 여러 앱 타입 사용:
- **Helm 차트**: `frontend/sbkube.yaml`, `database/sbkube.yaml`
- **YAML 매니페스트**: `backend/sbkube.yaml`

### 4. 계층적 구조

```
multi-app-groups/
├── sbkube.yaml        # 공통 설정 (kubeconfig, helm_repos)
├── group1/
│   └── sbkube.yaml     # 그룹별 앱 설정
├── group2/
│   └── sbkube.yaml
└── group3/
    └── sbkube.yaml
```

## 📋 우선순위 규칙

배포 순서 제어:

1. **app_dirs 순서**: `app_dirs` 리스트 순서대로 배포
   ```yaml
   app_dirs:
     - database   # 1번째
     - backend    # 2번째
     - frontend   # 3번째
   ```

2. **자동 탐색 순서**: 알파벳 순서
   ```
   backend → database → frontend
   ```

3. **그룹 내 앱 순서**: `sbkube.yaml`의 apps 키 순서

## 🐛 Troubleshooting

### 문제 1: 특정 그룹만 배포되지 않음

**증상**: frontend와 database는 배포되지만 backend는 무시됨

**원인**: `app_dirs`에 backend가 없음

**해결**:
```yaml
# sources-selective.yaml 확인
app_dirs:
  - frontend
  - backend   # ← 추가
  - database
```

### 문제 2: 자동 탐색이 모든 디렉토리를 찾지 못함

**증상**: `sbkube prepare`가 일부 그룹만 발견

**원인**: `sbkube.yaml` 파일이 없거나 잘못된 위치

**해결**:
```bash
# 각 그룹 디렉토리에 sbkube.yaml 존재 확인
ls frontend/sbkube.yaml
ls backend/sbkube.yaml
ls database/sbkube.yaml

# 파일명 대소문자 확인 (sbkube.yaml, not Config.yaml)
```

### 문제 3: app_dirs 검증 오류

**증상**: `ValidationError: app_dirs cannot be empty`

**해결**:
```yaml
# 잘못된 예
app_dirs: []  # ❌ 빈 리스트

# 올바른 예
app_dirs:     # ✅ 최소 1개 이상
  - frontend
```

또는 자동 탐색을 사용하려면 `app_dirs` 자체를 제거:
```yaml
# app_dirs: []  # ← 이 줄 전체 삭제
```

### 문제 4: 네임스페이스 충돌

**증상**: 다른 그룹의 리소스가 충돌

**원인**: 모든 그룹이 같은 네임스페이스 사용

**해결**:
```yaml
# frontend/sbkube.yaml
namespace: multi-app-demo-frontend

# backend/sbkube.yaml
namespace: multi-app-demo-backend

# database/sbkube.yaml
namespace: multi-app-demo-database
```

## 📚 관련 예제

- [app-dirs-explicit](../app-dirs-explicit/) - `app_dirs` 기본 사용법
- [app-types/01-helm](../app-types/01-helm/) - Helm 차트 고급 기능
- [app-types/02-yaml](../app-types/02-yaml/) - YAML 매니페스트 배포
- [advanced-features/04-multi-namespace](../advanced-features/04-multi-namespace/) - 멀티 네임스페이스

## 🔑 핵심 정리

1. **자동 탐색 vs 명시적 지정**
   - 자동: `app_dirs` 없음 → 모든 `sbkube.yaml` 발견
   - 명시: `app_dirs: [...]` → 지정된 그룹만

2. **유연한 배포 제어**
   - 전체 배포: `sbkube apply -f sbkube.yaml`
   - 그룹 선택: `--source sources-selective.yaml`
   - 단일 그룹: `--app-config-dir <group>`

3. **실용적인 구조**
   - 티어별 분리: frontend/backend/database
   - 앱 타입 혼합: Helm + YAML
   - 공통 설정: sbkube.yaml에서 관리
