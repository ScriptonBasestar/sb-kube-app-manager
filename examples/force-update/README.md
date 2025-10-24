# Force Update - --force 옵션 사용

SBKube의 **`--force`** 옵션을 사용하여 충돌 및 캐시 문제를 해결하는 예제입니다.

## 📋 목차

- [개요](#-개요)
- [--force 옵션이란?](#---force-옵션이란)
- [사용 시나리오](#-사용-시나리오)
- [명령어별 --force 동작](#-명령어별---force-동작)
- [실전 예제](#-실전-예제)
- [주의사항](#️-주의사항)

---

## 🎯 개요

`--force` 옵션은 다음과 같은 상황에서 사용합니다:

- 🔄 이미 다운로드된 차트를 **재다운로드**해야 할 때
- 🔄 이미 클론된 Git 리포지토리를 **재클론**해야 할 때
- 🔄 충돌하는 리소스를 **강제로 업데이트**해야 할 때
- 🔄 캐시된 빌드 결과를 **무시**하고 새로 빌드해야 할 때

---

## 🔧 --force 옵션이란?

`--force`는 기존 결과물을 무시하고 작업을 강제로 재실행하는 옵션입니다.

### 지원 명령어

| 명령어 | --force 지원 | 동작 |
|-------|------------|------|
| `prepare` | ✅ | 차트/리포지토리 강제 재다운로드 |
| `build` | ✅ | 빌드 결과 무시하고 재빌드 |
| `template` | ✅ | 렌더링 결과 무시하고 재렌더링 |
| `deploy` | ✅ | Helm upgrade 강제 실행 |
| `apply` | ✅ | 모든 단계에서 --force 적용 |

---

## 🚀 사용 시나리오

### 시나리오 1: 차트 버전 변경 후 재다운로드

**문제**:
```bash
# config.yaml에서 버전 변경
# version: 17.13.2 → version: 18.0.0

sbkube prepare
# → "Chart already exists, skipping download"
```

**해결**:
```bash
sbkube prepare --force
# → charts/ 디렉토리 삭제 후 재다운로드
```

### 시나리오 2: Git 리포지토리 업데이트

**문제**:
```bash
# Git 리포지토리가 업데이트되었지만 로컬은 오래된 버전

sbkube prepare
# → "Repository already exists, skipping clone"
```

**해결**:
```bash
sbkube prepare --force
# → repos/ 디렉토리 삭제 후 재클론
```

### 시나리오 3: Overrides 변경 후 재빌드

**문제**:
```bash
# overrides/ 파일 수정 후

sbkube build
# → "Build directory already exists, using cached version"
```

**해결**:
```bash
sbkube build --force
# → build/ 디렉토리 삭제 후 재빌드
```

### 시나리오 4: 배포 충돌 해결

**문제**:
```bash
sbkube deploy
# → "Error: Helm release exists with different configuration"
```

**해결**:
```bash
sbkube deploy --force
# → Helm upgrade --force 실행
```

### 시나리오 5: 전체 워크플로우 강제 재실행

**문제**:
```bash
# 여러 단계에서 캐시 문제 발생

sbkube apply
# → 일부 단계가 스킵됨
```

**해결**:
```bash
sbkube apply --force
# → prepare, build, deploy 모두 강제 재실행
```

---

## 🔍 명령어별 --force 동작

### 1. prepare --force

**기본 동작** (--force 없음):
```bash
sbkube prepare
```
- 이미 존재하는 `charts/`, `repos/` 디렉토리는 스킵

**--force 동작**:
```bash
sbkube prepare --force
```
- 기존 `charts/<app-name>/` 삭제 후 재다운로드
- 기존 `repos/<repo-name>/` 삭제 후 재클론

**실행 예시**:
```bash
cd examples/force-update

# 첫 번째 실행
sbkube prepare
# → charts/redis/ 다운로드

# 두 번째 실행 (변경 없음)
sbkube prepare
# → "Chart already exists, skipping"

# 강제 재다운로드
sbkube prepare --force
# → charts/redis/ 삭제 후 재다운로드
```

### 2. build --force

**기본 동작** (--force 없음):
```bash
sbkube build
```
- 이미 존재하는 `build/` 디렉토리는 스킵

**--force 동작**:
```bash
sbkube build --force
```
- 기존 `build/<app-name>/` 삭제 후 재빌드

**실행 예시**:
```bash
# Overrides 파일 수정
vi overrides/redis/values.yaml

# 강제 재빌드
sbkube build --force
# → build/redis/ 삭제 후 재빌드 (새 overrides 적용)
```

### 3. template --force

**기본 동작** (--force 없음):
```bash
sbkube template --output-dir /tmp/rendered
```
- 이미 존재하는 렌더링 파일은 스킵

**--force 동작**:
```bash
sbkube template --output-dir /tmp/rendered --force
```
- 기존 렌더링 파일 덮어쓰기

### 4. deploy --force

**기본 동작** (--force 없음):
```bash
sbkube deploy
```
- `helm upgrade --install` 실행

**--force 동작**:
```bash
sbkube deploy --force
```
- `helm upgrade --install --force` 실행
- Pod를 강제로 재생성

**⚠️ 주의**: `--force`는 Pod를 즉시 종료하고 재생성합니다 (다운타임 발생 가능)

### 5. apply --force

**기본 동작** (--force 없음):
```bash
sbkube apply
```
- prepare → build → deploy 순차 실행 (캐시 활용)

**--force 동작**:
```bash
sbkube apply --force
```
- **모든 단계에서 --force 적용**
  - `prepare --force`
  - `build --force`
  - `deploy --force`

---

## 💡 실전 예제

### 예제 1: 차트 버전 업그레이드

```bash
cd examples/force-update

# 1. 초기 배포
sbkube apply

# 2. config.yaml 수정
# version: 17.13.2 → version: 18.0.0

# 3. 강제 재다운로드 및 재배포
sbkube apply --force
```

**결과**:
- Redis 17.13.2 → 18.0.0 업그레이드

### 예제 2: Values 파일 수정 후 재배포

```bash
# 1. values/redis.yaml 수정
# password: "force-demo-password" → password: "new-password"

# 2. 재빌드 및 재배포 (prepare는 스킵 가능)
sbkube build --force
sbkube deploy --force

# 또는 한 번에
sbkube apply --force
```

### 예제 3: 배포 실패 후 재시도

```bash
# 1. 배포 시도
sbkube deploy
# → Error: Helm release stuck in pending-upgrade

# 2. 강제 재배포
sbkube deploy --force
# → 기존 릴리스 상태 무시하고 업그레이드
```

### 예제 4: Git 리포지토리 최신 버전 반영

```bash
# Git 타입 앱이 있는 경우
sbkube prepare --force
# → Git pull 또는 재클론으로 최신 버전 가져오기

sbkube apply
```

---

## ⚠️ 주의사항

### 1. deploy --force는 다운타임 발생 가능

**--force 없음** (기본):
```bash
sbkube deploy
```
- Rolling update: 새 Pod 생성 → 준비 완료 → 기존 Pod 종료
- **다운타임 없음** (무중단 배포)

**--force 사용**:
```bash
sbkube deploy --force
```
- 기존 Pod 즉시 종료 → 새 Pod 생성
- **다운타임 발생** (서비스 중단)

**권장**:
- 개발 환경: --force 사용 가능
- 프로덕션: --force 사용 주의 (긴급 상황에만)

### 2. 데이터 손실 위험

**주의 대상**:
- StatefulSet (데이터베이스 등)
- PersistentVolumeClaim

**--force 시 동작**:
```bash
sbkube deploy --force
# → Pod 재생성 (PVC는 유지되지만 연결 끊김 가능)
```

**안전한 방법**:
```bash
# 1. 데이터 백업
kubectl exec -n force-demo redis-master-0 -- redis-cli SAVE
kubectl cp force-demo/redis-master-0:/data/dump.rdb ./backup.rdb

# 2. 강제 재배포
sbkube deploy --force

# 3. 데이터 복구 (필요 시)
kubectl cp ./backup.rdb force-demo/redis-master-0:/data/dump.rdb
```

### 3. prepare --force는 네트워크 대역폭 소모

```bash
sbkube prepare --force
# → 수십~수백 MB 차트/리포지토리 재다운로드
```

**권장**:
- 필요한 경우에만 사용
- CI/CD에서는 캐시 활용 고려

### 4. 충돌 확인 없이 덮어쓰기

```bash
# ❌ 위험: 변경사항 확인 없이 덮어쓰기
sbkube apply --force

# ✅ 안전: 먼저 dry-run으로 확인
sbkube apply --dry-run
# 변경사항 확인 후
sbkube apply --force
```

---

## 🔍 디버깅 팁

### --force 적용 여부 확인

```bash
# Verbose 모드로 실행
sbkube apply --force --verbose
```

**출력 예시**:
```
[INFO] prepare: Using --force, deleting charts/redis/
[INFO] prepare: Downloading redis:17.13.2...
[INFO] build: Using --force, deleting build/redis/
[INFO] build: Building redis...
[INFO] deploy: Using --force, executing helm upgrade --force
```

### 단계별 --force 적용

```bash
# 1단계: prepare만 --force
sbkube prepare --force

# 2단계: build는 정상 실행
sbkube build

# 3단계: deploy만 --force
sbkube deploy --force
```

---

## 🆚 --force vs 일반 실행 비교

| 시나리오 | 일반 실행 | --force 실행 |
|---------|---------|------------|
| **차트 이미 존재** | 스킵 | 삭제 후 재다운로드 |
| **Git 리포지토리 이미 존재** | 스킵 | 삭제 후 재클론 |
| **빌드 디렉토리 이미 존재** | 스킵 | 삭제 후 재빌드 |
| **Helm 릴리스 이미 존재** | Upgrade | Force upgrade (Pod 재생성) |
| **실행 속도** | 빠름 (캐시 활용) | 느림 (전체 재실행) |
| **다운타임** | 없음 (Rolling update) | 있음 (Pod 즉시 종료) |
| **사용 권장** | 일반적 상황 | 문제 해결 시 |

---

## 📚 참고 자료

- [SBKube 명령어 참조](../../docs/02-features/commands.md)
- [Helm Upgrade --force](https://helm.sh/docs/helm/helm_upgrade/)
- [apply-workflow/](../apply-workflow/) - 통합 워크플로우 예제

---

## 🔗 관련 예제

- [apply-workflow/](../apply-workflow/) - 기본 apply 사용법
- [state-management/](../state-management/) - 롤백 및 상태 관리

---

**💡 팁**: `--force`는 강력하지만 위험할 수 있습니다. 프로덕션에서는 신중하게 사용하고, 항상 백업을 먼저 수행하세요.
