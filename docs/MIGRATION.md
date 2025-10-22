# SBKube Migration Guide

> **Breaking Changes**: v0.2.x → v0.3.0

## 🎯 변경 목적

사용자가 더 쉽고 직관적으로 SBKube를 사용할 수 있도록 설정 구조를 전면 개편했습니다.

### 핵심 개선 사항

1. **앱 단위 그룹화**: 관련 작업들을 앱 단위로 통합
2. **설정 간소화**: 불필요한 중복 제거
3. **의존성 명시**: `depends_on`으로 앱 간 순서 자동 관리
4. **타입 통합**: pull + install → 하나의 타입으로

---

## 📋 주요 변경 사항

### 1. Apps 구조 변경: List → Dict

#### Before (v0.2.x)

```yaml
apps:
  - name: redis-pull
    type: pull-helm
    specs:
      repo: bitnami
      chart: redis
      dest: redis
  - name: redis
    type: install-helm
    specs:
      values:
        - redis.yaml
```

#### After (v0.3.0)

```yaml
apps:
  redis:
    type: helm
    chart: bitnami/redis
    values:
      - redis.yaml
```

**변경 내용**:
- `apps`가 배열(list)에서 딕셔너리(dict)로 변경
- 앱 이름이 `name` 필드에서 딕셔너리 키로 이동
- pull과 install이 하나의 `helm` 타입으로 통합

---

### 2. Helm 타입 통합

#### Before (v0.2.x)

```yaml
apps:
  - name: redis-pull
    type: pull-helm
    specs:
      repo: bitnami
      chart: redis
      chart_version: 17.13.2
      dest: redis

  - name: redis
    type: install-helm
    specs:
      path: redis
      values:
        - redis.yaml
```

#### After (v0.3.0)

```yaml
apps:
  redis:
    type: helm
    chart: bitnami/redis
    version: 17.13.2
    values:
      - redis.yaml
```

**변경 내용**:
- `pull-helm` + `install-helm` → `helm` (자동으로 pull + install 수행)
- `repo`와 `chart`를 `chart: repo/chart` 형식으로 통합
- `chart_version` → `version`
- `dest`, `path` 필드 제거 (자동 관리)

---

### 3. Specs 평탄화

#### Before (v0.2.x)

```yaml
apps:
  - name: custom
    type: install-yaml
    specs:
      paths:
        - deployment.yaml
        - service.yaml
```

#### After (v0.3.0)

```yaml
apps:
  custom:
    type: yaml
    files:
      - deployment.yaml
      - service.yaml
```

**변경 내용**:
- `specs` 필드 제거
- 모든 설정이 앱 레벨로 평탄화
- `install-yaml` → `yaml`
- `paths` → `files`

---

### 4. 의존성 명시

#### Before (v0.2.x)

```yaml
deps: []  # 전역 deps만 존재

apps:
  - name: redis
    type: install-helm
    specs: ...

  - name: backend
    type: install-helm
    specs: ...
    # 순서는 배열 순서에 의존
```

#### After (v0.3.0)

```yaml
apps:
  redis:
    type: helm
    chart: bitnami/redis

  backend:
    type: helm
    chart: my/backend
    depends_on:
      - redis  # 명시적 의존성
```

**변경 내용**:
- `depends_on` 필드로 앱 간 의존성 명시
- 자동 위상 정렬로 올바른 순서 보장
- 순환 의존성 자동 검출

---

### 5. 타입 이름 변경

| v0.2.x | v0.3.0 | 비고 |
|--------|--------|------|
| `pull-helm` + `install-helm` | `helm` | 통합 |
| `install-yaml` | `yaml` | 간소화 |
| `install-kubectl` | `yaml` | 통합 |
| `install-action` | `action` | 간소화 |
| `install-kustomize` | `kustomize` | 간소화 |
| `pull-git` | `git` | 간소화 |
| `exec` | `exec` | 동일 |
| `copy-*` | - | 제거 (불필요) |
| `render` | - | 제거 (template 명령어 사용) |

---

## 🔄 자동 마이그레이션

### 명령어 사용

```bash
# 1. 미리보기
sbkube migrate config.yaml

# 2. 새 파일로 저장
sbkube migrate config.yaml -o config-v3.yaml

# 3. 기존 파일 덮어쓰기 (백업 필수!)
cp config.yaml config.backup.yaml
sbkube migrate config.yaml -o config.yaml --force
```

### 마이그레이션 도구가 처리하는 것

- ✅ `apps` list → dict 변환
- ✅ `pull-helm` + `install-helm` → `helm` 통합
- ✅ `specs` 평탄화
- ✅ 타입 이름 변경
- ✅ 필드 이름 변경 (`paths` → `files` 등)

### 수동 확인 필요 사항

- ⚠️ `depends_on` 의존성 추가 (원래는 순서로만 관리)
- ⚠️ `copy-*` 타입은 제거됨 (대체 방법 검토 필요)
- ⚠️ `render` 타입은 제거됨 (`template` 명령어 사용)

---

## 📝 실전 예제

### 예제 1: 단순 Helm 차트 배포

#### Before (v0.2.x)

```yaml
namespace: production

deps: []

apps:
  - name: redis-pull
    type: pull-helm
    specs:
      repo: bitnami
      chart: redis
      dest: redis

  - name: redis
    type: install-helm
    specs:
      values:
        - redis.yaml
```

#### After (v0.3.0)

```yaml
namespace: production

apps:
  redis:
    type: helm
    chart: bitnami/redis
    values:
      - redis.yaml
```

---

### 예제 2: 의존성이 있는 멀티 앱

#### Before (v0.2.x)

```yaml
namespace: production

deps: []

apps:
  - name: postgres-pull
    type: pull-helm
    specs:
      repo: bitnami
      chart: postgresql
      dest: postgres

  - name: postgres
    type: install-helm
    specs:
      values:
        - postgres.yaml

  - name: redis-pull
    type: pull-helm
    specs:
      repo: bitnami
      chart: redis
      dest: redis

  - name: redis
    type: install-helm
    specs:
      values:
        - redis.yaml

  - name: backend
    type: install-helm
    specs:
      path: backend-chart
      values:
        - backend.yaml
    # 순서상 postgres, redis 다음에 배포
```

#### After (v0.3.0)

```yaml
namespace: production

apps:
  postgres:
    type: helm
    chart: bitnami/postgresql
    values:
      - postgres.yaml

  redis:
    type: helm
    chart: bitnami/redis
    values:
      - redis.yaml

  backend:
    type: helm
    chart: my/backend
    values:
      - backend.yaml
    depends_on:
      - postgres
      - redis
```

**개선 사항**:
- 앱 개수가 6개 → 3개로 감소
- 의존성이 명시적으로 표현됨
- 설정이 훨씬 간결하고 읽기 쉬움

---

### 예제 3: YAML 매니페스트 직접 배포

#### Before (v0.2.x)

```yaml
apps:
  - name: custom-app
    type: install-yaml
    specs:
      paths:
        - deployment.yaml
        - service.yaml
        - configmap.yaml
```

#### After (v0.3.0)

```yaml
apps:
  custom-app:
    type: yaml
    files:
      - deployment.yaml
      - service.yaml
      - configmap.yaml
```

---

### 예제 4: 커스텀 명령어 실행

#### Before (v0.2.x)

```yaml
apps:
  - name: post-install
    type: exec
    specs:
      commands:
        - echo "Deployment completed"
        - kubectl get pods
```

#### After (v0.3.0)

```yaml
apps:
  post-install:
    type: exec
    commands:
      - echo "Deployment completed"
      - kubectl get pods
```

---

## 🚀 명령어 사용법 변경

### Prepare

#### Before (v0.2.x)

```bash
sbkube prepare --app-dir memory
# redis-pull과 redis를 따로 처리
```

#### After (v0.3.0)

```bash
sbkube prepare --app-dir memory
# redis 앱 하나만 처리 (자동으로 pull)
```

---

### Deploy

#### Before (v0.2.x)

```bash
sbkube deploy --app-dir memory --namespace data
# redis만 배포 (redis-pull은 prepare에서 처리)
```

#### After (v0.3.0)

```bash
sbkube deploy --app-dir memory
# redis 앱 배포 (네임스페이스는 config에서)
```

---

### Apply (통합 명령어)

#### v0.3.0 신규 기능

```bash
# 전체 워크플로우 한 번에
sbkube apply --app-dir memory

# 의존성 순서 자동 해결
# 1. prepare 단계
# 2. deploy 단계 (depends_on 순서대로)

# 특정 앱만 (의존성 포함)
sbkube apply --app-dir memory --app backend
# → postgres, redis, backend 순서로 배포
```

---

## ⚠️ 주의 사항

### 1. Breaking Changes

v0.3.0은 **완전히 새로운 설정 구조**입니다. v0.2.x 설정 파일은 그대로 사용할 수 없습니다.

**반드시** 마이그레이션 도구를 사용하거나 수동으로 변환하세요.

### 2. 백업

```bash
# 마이그레이션 전에 반드시 백업!
cp config.yaml config.backup.yaml
cp sources.yaml sources.backup.yaml
```

### 3. 테스트

```bash
# 먼저 dry-run으로 테스트
sbkube apply --app-dir memory --dry-run

# 정상 동작 확인 후 실제 배포
sbkube apply --app-dir memory
```

### 4. 제거된 기능

- `copy-*` 타입: 더 이상 지원하지 않음
- `render` 타입: `template` 명령어 사용
- `deps` (전역): 앱별 `depends_on` 사용

---

## 🔍 트러블슈팅

### 문제: "chart must be in 'repo/chart' format"

```yaml
# ❌ 잘못된 형식
apps:
  redis:
    type: helm
    chart: redis  # repo 없음

# ✅ 올바른 형식
apps:
  redis:
    type: helm
    chart: bitnami/redis
```

### 문제: "Circular dependency detected"

```yaml
# ❌ 순환 의존성
apps:
  app1:
    type: helm
    chart: my/app1
    depends_on:
      - app2

  app2:
    type: helm
    chart: my/app2
    depends_on:
      - app1  # 순환!

# ✅ 올바른 의존성
apps:
  app1:
    type: helm
    chart: my/app1

  app2:
    type: helm
    chart: my/app2
    depends_on:
      - app1  # app1 → app2 (단방향)
```

### 문제: "App depends on non-existent app"

```yaml
# ❌ 존재하지 않는 앱 참조
apps:
  backend:
    type: helm
    chart: my/backend
    depends_on:
      - redis  # 정의되지 않음

# ✅ 올바른 참조
apps:
  redis:
    type: helm
    chart: bitnami/redis

  backend:
    type: helm
    chart: my/backend
    depends_on:
      - redis  # 정의됨
```

---

## 📚 추가 리소스

- [v0.3.0 설정 스키마 문서](03-configuration/config-schema-v3.md)
- [v0.3.0 예제](../examples/v3/)
- [GitHub Releases](https://github.com/your-org/sbkube/releases)

---

## 💬 피드백

마이그레이션 중 문제가 발생하거나 제안 사항이 있으면 [GitHub Issues](https://github.com/your-org/sbkube/issues)로 알려주세요.
