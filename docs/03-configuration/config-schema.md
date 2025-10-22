# 📋 config.yaml 스키마 가이드 (v0.3.0)

SBKube v0.3.0의 메인 설정 파일인 `config.yaml`의 완전한 스키마 문서입니다.

> **v0.3.0 주요 변경사항**:
> - Apps는 이름을 key로 사용하는 dict 구조 (list → dict)
> - `specs` 필드 제거 (필드 평탄화)
> - `pull-helm` + `install-helm` → 단일 `helm` 타입
> - 지원 타입 단순화 (10개 → 7개)

______________________________________________________________________

## 📂 파일 구조 개요

```yaml
# config.yaml 기본 구조 (v0.3.0)
namespace: string              # 전역 기본 네임스페이스 (필수)

apps:                          # 애플리케이션 딕셔너리 (필수)
  app-name:                    # 앱 이름 (key)
    type: enum                 # 앱 타입 (필수)
    enabled: boolean           # 활성화 여부 (기본: true)
    depends_on: [string]       # 의존성 목록 (선택)
    namespace: string          # 앱별 네임스페이스 (선택)
    # ... 타입별 필드
```

**v0.2.x와의 차이점**:
- `apps`가 list가 아닌 dict
- `name` 필드 제거 (key가 이름)
- `specs` 필드 제거 (평탄화)

______________________________________________________________________

## 🌐 전역 설정

### namespace (string, 필수)

모든 앱에 적용되는 기본 네임스페이스입니다.

```yaml
namespace: default
```

또는

```yaml
namespace: production
```

**규칙**:
- Kubernetes 네임스페이스 명명 규칙 준수
- 소문자와 하이픈만 사용 (`[a-z0-9-]+`)
- 앱별 `namespace` 필드로 재정의 가능

______________________________________________________________________

## 📱 앱 설정 (apps)

v0.3.0에서 `apps`는 **딕셔너리**입니다. 앱 이름이 key가 됩니다.

### 기본 구조

```yaml
apps:
  app-name:                    # 앱 이름 (key)
    type: helm                 # 타입 (필수)
    enabled: true              # 활성화 여부 (선택, 기본: true)
    depends_on: []             # 의존성 (선택)
```

### 필수 필드

#### type (enum, 필수)

앱 타입을 지정합니다. v0.3.0에서는 **7가지 타입**을 지원합니다.

| 타입 | 설명 | v0.2.x 동등 타입 |
|------|------|------------------|
| `helm` | Helm 차트 (원격/로컬) | pull-helm + install-helm |
| `yaml` | YAML 매니페스트 | install-yaml |
| `git` | Git 리포지토리 | pull-git |
| `http` | HTTP 파일 다운로드 | pull-http |
| `action` | 커스텀 액션 | install-action |
| `exec` | 커스텀 명령어 | exec |
| `noop` | No Operation | (신규) |

### 선택적 필드

#### enabled (boolean, 기본값: true)

앱의 활성화 여부를 제어합니다.

```yaml
apps:
  redis:
    type: helm
    chart: bitnami/redis
    enabled: true              # 활성화 (기본값)

  old-app:
    type: helm
    chart: bitnami/nginx
    enabled: false             # 비활성화 (건너뜀)
```

#### depends_on (array of strings, 선택)

이 앱이 의존하는 다른 앱들의 이름 목록입니다.

```yaml
apps:
  database:
    type: helm
    chart: bitnami/postgresql

  backend:
    type: helm
    chart: ./charts/backend
    depends_on:
      - database              # database 완료 후 실행
```

**의존성 규칙**:
- 순환 의존성은 자동으로 감지되어 오류 발생
- 의존성 순서대로 배포 실행
- 의존성이 실패하면 의존하는 앱도 건너뜀

#### namespace (string, 선택)

앱별 네임스페이스입니다. 전역 `namespace`를 재정의합니다.

```yaml
namespace: default            # 전역 네임스페이스

apps:
  redis:
    type: helm
    chart: bitnami/redis
    namespace: data           # 이 앱만 data 네임스페이스에 배포
```

#### labels (dict, 선택)

앱에 적용할 커스텀 라벨입니다.

```yaml
apps:
  redis:
    type: helm
    chart: bitnami/redis
    labels:
      environment: production
      team: platform
```

#### annotations (dict, 선택)

앱에 적용할 커스텀 어노테이션입니다.

```yaml
apps:
  redis:
    type: helm
    chart: bitnami/redis
    annotations:
      description: "Production Redis"
      owner: "platform-team"
```

______________________________________________________________________

## 🎯 타입별 설정

### 1. helm - Helm 차트

Helm 차트를 준비하고 배포합니다 (원격 또는 로컬).

#### 필수 필드

```yaml
apps:
  redis:
    type: helm
    chart: bitnami/redis       # 필수: 차트 경로
```

#### 모든 필드

```yaml
apps:
  redis:
    type: helm
    chart: bitnami/redis       # 필수: <repo>/<chart> 또는 ./path
    version: 17.13.2           # 선택: 차트 버전 (원격만)
    values:                    # 선택: values 파일 목록
      - redis-values.yaml
      - redis-production.yaml
    overrides:                 # 선택: 파일 교체
      templates/secret.yaml: custom-secret.yaml
    removes:                   # 선택: 파일 삭제
      - templates/serviceaccount.yaml
      - templates/tests/
    namespace: data            # 선택: 네임스페이스
    release_name: my-redis     # 선택: 릴리스 이름 (기본: 앱 이름)
```

**chart 필드 형식**:
- 원격: `<repo>/<chart>` (예: `bitnami/redis`)
- 로컬 (상대): `./charts/app`
- 로컬 (절대): `/absolute/path/to/chart`
- 이름만: `chart-name` (로컬 차트로 간주)

**overrides**:
- Key: 차트 내 파일 경로
- Value: 교체할 로컬 파일 경로
- `build` 단계에서 적용

**removes**:
- 차트에서 제거할 파일/디렉토리 목록
- 와일드카드 지원 (예: `templates/tests/`)
- `build` 단계에서 적용

______________________________________________________________________

### 2. yaml - YAML 매니페스트

Kubernetes YAML 매니페스트를 직접 배포합니다.

#### 필수 필드

```yaml
apps:
  nginx:
    type: yaml
    files:                     # 필수: YAML 파일 목록
      - manifests/deployment.yaml
      - manifests/service.yaml
```

#### 모든 필드

```yaml
apps:
  nginx:
    type: yaml
    files:                     # 필수: YAML 파일 목록 (비어있으면 안됨)
      - manifests/deployment.yaml
      - manifests/service.yaml
      - manifests/ingress.yaml
    namespace: web             # 선택: 네임스페이스
```

______________________________________________________________________

### 3. git - Git 리포지토리

Git 리포지토리를 클론하여 차트/매니페스트를 가져옵니다.

#### 필수 필드

```yaml
apps:
  source:
    type: git
    repo: my-app               # 필수: sources.yaml의 Git 저장소 이름
```

#### 모든 필드

```yaml
apps:
  source:
    type: git
    repo: my-app               # 필수: sources.yaml의 저장소 이름
    path: charts/app           # 선택: 리포지토리 내 경로
```

**sources.yaml 예제**:
```yaml
git_repos:
  my-app:
    url: https://github.com/example/myapp.git
    branch: main
```

**사용 패턴**:
```yaml
apps:
  # 1. Git 클론
  source:
    type: git
    repo: my-app
    path: charts/myapp

  # 2. 클론된 차트 사용
  app:
    type: helm
    chart: ./repos/my-app/charts/myapp
    depends_on:
      - source
```

______________________________________________________________________

### 4. http - HTTP 파일 다운로드

HTTP(S) URL에서 파일을 다운로드합니다.

#### 필수 필드

```yaml
apps:
  download:
    type: http
    url: https://example.com/manifest.yaml  # 필수: 다운로드 URL
    dest: manifest.yaml                     # 필수: 저장 경로
```

#### 모든 필드

```yaml
apps:
  download:
    type: http
    url: https://example.com/manifest.yaml  # 필수: URL
    dest: manifest.yaml                     # 필수: 저장 경로
    headers:                                # 선택: HTTP 헤더
      Authorization: "Bearer token"
      User-Agent: "SBKube/0.3.0"
```

**사용 패턴**:
```yaml
apps:
  # 1. 파일 다운로드
  download:
    type: http
    url: https://example.com/crd.yaml
    dest: crd.yaml

  # 2. 다운로드된 파일 적용
  apply:
    type: yaml
    files:
      - crd.yaml
    depends_on:
      - download
```

______________________________________________________________________

### 5. action - 커스텀 액션

복잡한 배포 시나리오를 위한 커스텀 액션 시퀀스입니다.

#### 필수 필드

```yaml
apps:
  setup:
    type: action
    actions:                   # 필수: 액션 목록
      - type: apply
        path: manifests/crd.yaml
```

#### 모든 필드

```yaml
apps:
  setup:
    type: action
    actions:                   # 필수: 액션 목록 (비어있으면 안됨)
      - type: apply            # apply 또는 delete
        path: manifests/namespace.yaml
      - type: apply
        path: manifests/crd.yaml
      - type: apply
        path: manifests/deployment.yaml
      - type: delete           # 선택: 기존 리소스 삭제
        path: manifests/old-resource.yaml
```

**액션 타입**:
- `apply`: `kubectl apply -f <path>` 실행
- `delete`: `kubectl delete -f <path>` 실행

______________________________________________________________________

### 6. exec - 커스텀 명령어 실행

임의의 명령어를 실행합니다 (초기화, 정리 등).

#### 필수 필드

```yaml
apps:
  check:
    type: exec
    commands:                  # 필수: 명령어 목록
      - echo "Checking..."
      - kubectl get nodes
```

#### 모든 필드

```yaml
apps:
  pre-check:
    type: exec
    commands:                  # 필수: 명령어 목록 (비어있으면 안됨)
      - echo "Starting pre-deployment checks..."
      - kubectl get nodes
      - helm list -A
      - echo "Pre-deployment checks completed!"
```

______________________________________________________________________

### 7. noop - No Operation

실제 동작 없이 의존성 관리에만 사용됩니다.

#### 필드

```yaml
apps:
  base-setup:
    type: noop
    description: "Base setup completed manually"  # 선택: 설명
```

______________________________________________________________________

## 📝 완전한 예제

### 기본 예제

```yaml
namespace: production

apps:
  redis:
    type: helm
    chart: bitnami/redis
    version: 17.13.2
    values:
      - redis-values.yaml

  backend:
    type: helm
    chart: ./charts/backend
    depends_on:
      - redis
```

### 고급 예제

```yaml
namespace: production

apps:
  # Git 리포지토리 클론
  app-source:
    type: git
    repo: my-app
    path: charts/myapp

  # HTTP 다운로드
  crd-download:
    type: http
    url: https://example.com/crd.yaml
    dest: crd.yaml

  # CRD 적용
  crd-setup:
    type: yaml
    files:
      - crd.yaml
    depends_on:
      - crd-download

  # 데이터베이스 배포 (차트 커스터마이징)
  database:
    type: helm
    chart: bitnami/postgresql
    namespace: data
    overrides:
      templates/secret.yaml: custom-secret.yaml
    removes:
      - templates/serviceaccount.yaml
    depends_on:
      - crd-setup

  # 백엔드 배포 (Git 소스 사용)
  backend:
    type: helm
    chart: ./repos/my-app/charts/myapp
    values:
      - backend-values.yaml
    labels:
      environment: production
      team: backend
    depends_on:
      - app-source
      - database

  # 배포 후 정리
  cleanup:
    type: exec
    commands:
      - kubectl delete pods --field-selector=status.phase=Succeeded -n production
    depends_on:
      - backend
```

______________________________________________________________________

## 🔄 v0.2.x에서 마이그레이션

### Before (v0.2.x)

```yaml
namespace: production

apps:
  - name: redis-pull
    type: pull-helm
    specs:
      repo: bitnami
      chart: redis
      dest: redis
      chart_version: 17.13.2

  - name: redis
    type: install-helm
    specs:
      path: redis
      values:
        - redis-values.yaml
```

### After (v0.3.0)

```yaml
namespace: production

apps:
  redis:
    type: helm
    chart: bitnami/redis
    version: 17.13.2
    values:
      - redis-values.yaml
```

**자동 마이그레이션**:
```bash
sbkube migrate old-config.yaml -o config.yaml
```

______________________________________________________________________

## ⚠️ 주의사항

### 필수 검증

SBKube는 Pydantic을 사용하여 설정을 검증합니다:

- **타입 검증**: 필드 타입 불일치 시 오류
- **필수 필드**: 누락 시 오류
- **순환 의존성**: 자동 감지 및 오류
- **앱 이름 중복**: 중복 시 오류

### 검증 명령어

```bash
# 설정 파일 검증
sbkube validate --app-dir config
```

______________________________________________________________________

*더 많은 예제는 [examples/](../../examples/) 디렉토리를 참조하세요.*
