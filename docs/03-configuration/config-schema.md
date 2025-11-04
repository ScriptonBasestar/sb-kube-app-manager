# 📋 config.yaml 스키마 가이드

SBKube의 메인 설정 파일인 `config.yaml`의 완전한 스키마 문서입니다.

> **주요 기능**:
>
> - Apps는 이름을 key로 사용하는 dict 구조 (list → dict)
> - `specs` 필드 제거 (필드 평탄화)
> - `helm` + `helm` → 단일 `helm` 타입
> - 지원 타입 단순화 (10개 → 7개)

______________________________________________________________________

## 📂 파일 구조 개요

```yaml
# config.yaml 기본 구조
namespace: string              # 전역 기본 네임스페이스 (필수)
deps: [string]                 # 앱 그룹 의존성 (선택, v0.4.10+)

apps:                          # 애플리케이션 딕셔너리 (필수)
  app-name:                    # 앱 이름 (key)
    type: enum                 # 앱 타입 (필수)
    enabled: boolean           # 활성화 여부 (기본: true)
    depends_on: [string]       # 앱 간 의존성 (선택)
    namespace: string          # 앱별 네임스페이스 (선택)
    # ... 타입별 필드
```

**이전 버전과의 차이점**:

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

### deps (list[string], 선택, v0.4.10+)

이 앱 그룹이 의존하는 다른 앱 그룹 목록입니다.

```yaml
namespace: harbor
deps:
  - a000_infra_network    # Ingress 및 Storage
  - a101_data_rdb         # PostgreSQL 데이터베이스
  - a100_data_memory      # Redis 캐시

apps:
  harbor:
    type: helm
    chart: harbor/harbor
```

**동작 방식** (v0.6.0+):

- **파싱**: 설정 파일에서 `deps` 필드를 읽어들임
- **문서화**: 의존성 정보를 config.yaml에 명시적으로 기록
- **디렉토리 검증** (`sbkube doctor`): deps에 명시된 앱 그룹 디렉토리가 실제로 존재하는지 확인
- **배포 상태 검증** (`sbkube apply`): deps에 명시된 앱 그룹이 실제로 배포되었는지 확인하여 미배포 시 배포 중단

**검증 동작**:

```bash
# 1. sbkube doctor: 디렉토리 존재 여부 확인
$ sbkube doctor
✅ Config Validity
   - namespace: harbor ✓
   - apps: 3 apps defined ✓
   - deps: a000_infra_network ✓
   - deps: a101_data_rdb ✗ (directory not found)  # 에러 발생

# 2. sbkube apply: 배포 상태 확인
$ sbkube apply --app-dir a302_devops
🔍 Checking app-group dependencies...
❌ Error: 2 dependencies not deployed:
  - a101_data_rdb (never deployed)
  - a100_data_memory (last status: failed)

💡 Deploy missing dependencies first:
  sbkube apply --app-dir a101_data_rdb
  sbkube apply --app-dir a100_data_memory

Tip: Use --skip-deps-check to override this check
```

**강제 배포**:

```bash
# 의존성 검증을 건너뛰고 강제로 배포 (CI/CD 등)
sbkube apply --app-dir a302_devops --skip-deps-check
```

**향후 기능** (예정):

- 자동 배포 순서 결정 (`--recursive`)
- 의존성 그래프 시각화
- 순환 의존성 감지

**사용 사례**:

```yaml
# 예제 1: 데이터베이스 의존성
# a302_devops/config.yaml
namespace: harbor
deps:
  - a101_data_rdb       # PostgreSQL 필요
  - a100_data_memory    # Redis 필요
apps:
  harbor:
    type: helm
    chart: harbor/harbor

# 예제 2: 전체 인프라 의존성
# a400_airflow/config.yaml
namespace: airflow
deps:
  - a000_infra_network  # NFS storage, Ingress
  - a101_data_rdb       # Airflow metadata DB
  - a100_data_memory    # Celery executor
apps:
  airflow:
    type: helm
    chart: apache-airflow/airflow
```

**주의사항**:

- 앱 그룹 이름(디렉토리 이름)을 사용 (예: `a000_infra_network`)
- 경로가 아닌 이름만 지정 (예: `../a000_infra_network` ❌)
- 현재는 문서화 목적이며 실제 검증은 향후 버전에서 구현 예정

______________________________________________________________________

## 📱 앱 설정 (apps)

현재 버전에서 `apps`는 **딕셔너리**입니다. 앱 이름이 key가 됩니다.

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

앱 타입을 지정합니다. 현재 버전에서는 **7가지 타입**을 지원합니다.

| 타입 | 설명 | 이전 버전 타입 | |------|------|------------------| | `helm` | Helm 차트 (원격/로컬) | helm + helm | | `yaml` | YAML
매니페스트 | yaml | | `git` | Git 리포지토리 | pull-git | | `http` | HTTP 파일 다운로드 | pull-http | | `action` | 커스텀 액션 | action | |
`exec` | 커스텀 명령어 | exec | | `noop` | No Operation | (신규) |

### 선택적 필드

#### enabled (boolean, 기본값: true)

앱의 활성화 여부를 제어합니다.

```yaml
apps:
  grafana:
    type: helm
    chart: grafana/grafana
    enabled: true              # 활성화 (기본값)

  old-app:
    type: helm
    chart: ingress-nginx/ingress-nginx
    enabled: false             # 비활성화 (건너뜀)
```

#### depends_on (array of strings, 선택)

이 앱이 의존하는 다른 앱들의 이름 목록입니다.

```yaml
apps:
  database:
    type: helm
    chart: cloudnative-pg/cloudnative-pg

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
  grafana:
    type: helm
    chart: grafana/grafana
    namespace: monitoring     # 이 앱만 monitoring 네임스페이스에 배포
```

**Namespace 상속 규칙 (v0.6.1+)**:

모든 앱 타입 (helm, yaml, action, kustomize)에서 동일하게 동작합니다:

1. **명시적 앱 네임스페이스 우선**: `app.namespace`가 설정되어 있으면 이를 사용
2. **전역 네임스페이스 폴백**: `app.namespace`가 `None`이면 `config.namespace` 사용
3. **kubectl 기본값**: 둘 다 없으면 `default` 네임스페이스 (kubectl 기본 동작)

**예제**:

```yaml
# config.yaml
namespace: production  # 전역 네임스페이스

apps:
  # 1. 전역 네임스페이스 사용 (production)
  app1:
    type: yaml
    manifests:
      - manifests/app1.yaml
    # namespace 필드 없음 → production 사용

  # 2. 앱별 네임스페이스 오버라이드
  app2:
    type: yaml
    manifests:
      - manifests/app2.yaml
    namespace: staging  # production 대신 staging 사용

  # 3. Helm 앱도 동일한 규칙 적용
  app3:
    type: helm
    chart: my/chart
    # namespace 필드 없음 → production 사용
```

**이전 버전과의 차이 (v0.6.0 이하)**:

- **v0.6.0 이하**: YAML/Action/Kustomize 타입은 전역 네임스페이스를 자동 상속하지 않음 (버그)
- **v0.6.1+**: 모든 앱 타입이 동일하게 전역 네임스페이스를 상속 (수정됨)

**권장 사항**:
- 대부분의 경우 전역 `namespace`만 설정하고 앱별 `namespace`는 생략
- 특정 앱만 다른 네임스페이스가 필요한 경우에만 앱별 오버라이드 사용

#### labels (dict, 선택)

앱에 적용할 커스텀 라벨입니다.

```yaml
apps:
  grafana:
    type: helm
    chart: grafana/grafana
    labels:
      environment: production
      team: platform
```

#### annotations (dict, 선택)

앱에 적용할 커스텀 어노테이션입니다.

```yaml
apps:
  grafana:
    type: helm
    chart: grafana/grafana
    annotations:
      description: "Production Grafana"
      owner: "platform-team"
```

______________________________________________________________________

## 🎯 타입별 설정

### 1. helm - Helm 차트

Helm 차트를 준비하고 배포합니다 (원격 또는 로컬).

#### 필수 필드

```yaml
apps:
  grafana:
    type: helm
    chart: grafana/grafana     # 필수: 차트 경로
```

#### 모든 필드

```yaml
apps:
  grafana:
    type: helm
    chart: grafana/grafana     # 필수: <repo>/<chart> 또는 ./path
    version: 6.50.0            # 선택: 차트 버전 (원격만)
    values:                    # 선택: values 파일 목록
      - grafana-values.yaml
      - grafana-production.yaml
    overrides:                 # 선택: 파일 교체
      templates/secret.yaml: custom-secret.yaml
    removes:                   # 선택: 파일 삭제
      - templates/serviceaccount.yaml
      - templates/tests/
    namespace: monitoring      # 선택: 네임스페이스
    context: prod-cluster      # 선택: Kubernetes context (v0.6.1+)
    release_name: my-grafana   # 선택: 릴리스 이름 (기본: 앱 이름)
```

**chart 필드 형식**:

- 원격: `<repo>/<chart>` (예: `grafana/grafana`)
- 로컬 (상대): `./charts/app`
- 로컬 (절대): `/absolute/path/to/chart`
- 이름만: `chart-name` (로컬 차트로 간주)

**overrides** (선택, 리스트):

차트 파일을 교체하거나 새로 추가할 파일 목록 (v0.4.9+에서 Glob 패턴 지원)

```yaml
overrides:
  - templates/deployment.yaml       # 기존 파일 교체
  - templates/*.yaml                # Glob: 모든 YAML 템플릿
  - templates/**/*.yaml             # Glob: 재귀적 (서브디렉토리 포함)
  - files/config.toml               # files 디렉토리 파일 추가
```

**디렉토리 구조**:

```
app-dir/
├── config.yaml
└── overrides/
    └── grafana/            # 앱 이름과 일치해야 함
        ├── templates/deployment.yaml      # 교체할 파일
        └── files/config.toml              # 추가할 파일
```

**동작**: `sbkube build` 시 차트를 `build/grafana/`로 복사 후, 명시된 파일을 `overrides/grafana/`에서 복사하여 덮어쓰기 또는 추가

**주의사항**:

- `overrides/` 디렉토리가 있어도 config.yaml에 명시 필수
- Glob 와일드카드: `*` (다중 문자), `?` (단일 문자), `**` (재귀)

**관련 문서**:

- [commands.md - Override 사용법](../02-features/commands.md#-override-%EB%94%94%EB%A0%89%ED%86%A0%EB%A6%AC-%EC%82%AC%EC%9A%A9-%EC%8B%9C-%EC%A3%BC%EC%9D%98%EC%82%AC%ED%95%AD)
- [troubleshooting.md - Override 문제 해결](../07-troubleshooting/README.md)

**removes**:

- 차트에서 제거할 파일/디렉토리 목록
- 와일드카드 지원 (예: `templates/tests/`)
- `build` 단계에서 적용

**context** (선택, v0.6.1+):

앱을 배포할 Kubernetes 컨텍스트를 지정합니다.

```yaml
apps:
  prod-app:
    type: helm
    chart: myapp/app
    context: prod-cluster      # 이 앱은 prod-cluster에 배포
    namespace: production

  staging-app:
    type: helm
    chart: myapp/app
    context: staging-cluster   # 이 앱은 staging-cluster에 배포
    namespace: staging
```

**Context 우선순위**:
1. **app.context** (최우선): config.yaml의 앱별 context 필드
2. **sources.yaml context**: 프로젝트 기본 context (kubeconfig_context)
3. **현재 context**: kubectl의 현재 활성 context

**사용 사례**:
- 멀티 클러스터 관리: 하나의 config.yaml로 여러 클러스터에 배포
- 개발/스테이징/프로덕션 분리: 앱별로 다른 클러스터 지정
- 마이그레이션: 일부 앱만 새 클러스터로 이동

**주의사항**:
- context는 ~/.kube/config 또는 KUBECONFIG 환경변수의 kubeconfig 파일에 정의되어 있어야 합니다
- app.context 지정 시 sources.yaml의 kubeconfig는 사용되지 않습니다 (시스템 기본 kubeconfig 사용)

______________________________________________________________________

### 2. yaml - YAML 매니페스트

Kubernetes YAML 매니페스트를 직접 배포합니다.

#### 필수 필드

```yaml
apps:
  nginx:
    type: yaml
    manifests:                 # 필수: YAML 파일 목록
      - manifests/deployment.yaml
      - manifests/service.yaml
```

#### 모든 필드

```yaml
apps:
  nginx:
    type: yaml
    manifests:                 # 필수: YAML 파일 목록 (비어있으면 안됨)
      - manifests/deployment.yaml
      - manifests/service.yaml
      - manifests/ingress.yaml
    namespace: web             # 선택: 네임스페이스
    context: prod-cluster      # 선택: Kubernetes context (v0.6.1+)
```

#### 변수 치환 (v0.6.0+)

Git 리포지토리 내부의 파일을 참조할 때 `${repos.app-name}` 변수를 사용할 수 있습니다.

```yaml
apps:
  # 1. Git 리포지토리 클론
  olm:
    type: git
    repo: olm
    branch: master
    enabled: true

  # 2. Git 리포지토리 내부 YAML 파일 참조
  olm-operator:
    type: yaml
    manifests:
      - ${repos.olm}/deploy/upstream/quickstart/crds.yaml
      - ${repos.olm}/deploy/upstream/quickstart/olm.yaml
    namespace: ""
    depends_on:
      - olm
```

**변수 치환 규칙**:

- `${repos.app-name}` 형식: `app-name`은 git 타입 앱의 이름
- 자동 확장: `.sbkube/repos/app-name`으로 변환
- 검증: 참조된 앱이 존재하고 git 타입인지 검증
- 하위 호환성: 기존 상대경로 방식도 계속 지원

**장점**:

- **유지보수성**: 명시적이고 깨지지 않는 경로
- **가독성**: 의도가 명확 (어떤 리포지토리의 파일인지)
- **안전성**: 설정 로드 시 변수 구문 검증

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
      User-Agent: "SBKube/0.4.10"
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
  grafana:
    type: helm
    chart: grafana/grafana
    version: 6.50.0
    values:
      - grafana-values.yaml

  backend:
    type: helm
    chart: ./charts/backend
    depends_on:
      - grafana
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
    chart: cloudnative-pg/cloudnative-pg
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
