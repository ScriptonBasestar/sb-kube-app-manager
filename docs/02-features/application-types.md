# 🎯 SBKube 애플리케이션 타입 가이드

SBKube은 다양한 소스와 배포 방식을 지원하는 **7가지 애플리케이션 타입**을 제공합니다.

> **주요 기능**:
>
> - `helm` + `helm` → 단일 `helm` 타입으로 통합
> - `yaml` → `yaml` 타입으로 간소화
> - `action` → `action` 타입으로 간소화
> - `git`, `http`, `helm-oci` 제거 (단순화)
> - `http`, `exec` 타입 추가

---

## 📦 지원 애플리케이션 타입

### 1. `helm` - Helm 차트 (원격/로컬)

**목적**: Helm 차트를 준비하고 배포 (원격 차트 또는 로컬 차트) **워크플로우**: `prepare` → `build` → `template` → `deploy`

#### 원격 Helm 차트 (Remote)

```yaml
apps:
  grafana:
    type: helm
    chart: grafana/grafana         # <repo>/<chart> 형식
    version: 6.50.0                # 차트 버전 (선택사항)
    values:
      - grafana-values.yaml
    namespace: monitoring
    release_name: my-grafana
```

#### 로컬 Helm 차트 (Local)

```yaml
apps:
  my-app:
    type: helm
    chart: ./charts/my-app         # 상대 경로
    values:
      - values.yaml
```

또는

```yaml
apps:
  local-chart:
    type: helm
    chart: /absolute/path/to/chart  # 절대 경로
```

#### 차트 커스터마이징

```yaml
apps:
  cloudnative-pg:
    type: helm
    chart: cloudnative-pg/cloudnative-pg
    overrides:
      templates/secret.yaml: custom-secret.yaml
      templates/configmap.yaml: custom-configmap.yaml
    removes:
      - templates/serviceaccount.yaml
      - templates/tests/
```

**주요 필드**:

- `chart` (필수): 차트 경로
  - 원격: `<repo>/<chart>` (예: `grafana/grafana`)
  - 로컬: `./path` 또는 `/absolute/path`
  - 이름만: `chart-name` (로컬 차트로 간주)
- `version` (선택): 차트 버전 (원격 차트만 해당)
- `values` (선택): Helm values 파일 목록
- `overrides` (선택): 차트 파일 교체 (dict)
- `removes` (선택): 차트 파일 삭제 (list)
- `namespace` (선택): 배포 네임스페이스
- `release_name` (선택): Helm 릴리스 이름 (기본값: 앱 이름)

**워크플로우**:

1. **prepare**: 원격 차트는 다운로드, 로컬 차트는 검증
1. **build**: 차트 커스터마이징 적용 (overrides, removes)
1. **template**: Helm 차트 템플릿 렌더링
1. **deploy**: Helm 릴리스 설치/업그레이드

---

### 2. `yaml` - YAML 매니페스트

**목적**: Kubernetes YAML 매니페스트 직접 배포 **워크플로우**: `build` → `template` → `deploy`

#### 기본 설정 예제

```yaml
apps:
  nginx:
    type: yaml
    manifests:
      - manifests/deployment.yaml
      - manifests/service.yaml
      - manifests/ingress.yaml
    namespace: web
```

#### Git 리포지토리 파일 참조 (v0.6.0+)

Git 타입 앱으로 클론된 리포지토리 내부의 YAML 파일을 참조할 수 있습니다.

```yaml
apps:
  # 1. Git 리포지토리 클론
  olm:
    type: git
    repo: olm
    branch: master

  # 2. Git 리포지토리 내부 YAML 참조
  olm-operator:
    type: yaml
    manifests:
      - ${repos.olm}/deploy/upstream/quickstart/crds.yaml
      - ${repos.olm}/deploy/upstream/quickstart/olm.yaml
    depends_on:
      - olm
```

**변수 치환 규칙**:

- `${repos.app-name}`: git 타입 앱 이름을 참조
- 자동 확장: `.sbkube/repos/app-name`으로 변환
- 참조 검증: 앱 존재 여부 및 타입 검증

**주요 필드**:

- `manifests` (필수): YAML 파일 경로 목록 (변수 사용 가능)
- `namespace` (선택): 배포 네임스페이스

**워크플로우**:

1. **prepare**: 건너뜀 (YAML 파일이 이미 준비됨)
1. **build**: 파일 유효성 검증
1. **template**: 파일 읽기 및 렌더링
1. **deploy**: `kubectl apply` 실행 (변수 확장)

---

### 3. `git` - Git 리포지토리

**목적**: Git 리포지토리에서 차트/매니페스트 가져오기 **워크플로우**: `prepare` → 후속 타입으로 처리

#### 설정 예제

```yaml
apps:
  custom-app-source:
    type: git
    repo: example-app              # sources.yaml에 정의된 Git 저장소명
    path: charts/myapp             # 리포지토리 내 경로

  custom-app:
    type: helm
    chart: ./repos/example-app/charts/myapp
    depends_on:
      - custom-app-source          # Git 클론 완료 후 실행
```

#### sources.yaml 예제

```yaml
git_repos:
  example-app:
    url: https://github.com/example/myapp.git
    branch: main
```

**주요 필드**:

- `repo` (필수): sources.yaml에 정의된 Git 저장소 이름
- `path` (선택): 리포지토리 내 특정 경로

**워크플로우**:

1. **prepare**: Git 저장소 클론 → `repos/<repo>/`
1. 후속 `helm` 또는 `yaml` 타입 앱이 `./repos/<repo>/<path>` 참조

---

### 4. `http` - HTTP 파일 다운로드

**목적**: HTTP(S) URL에서 파일 다운로드 **워크플로우**: `prepare` → 후속 타입으로 처리

#### 설정 예제

```yaml
apps:
  manifest-download:
    type: http
    url: https://example.com/manifest.yaml
    dest: downloaded-manifest.yaml
    headers:
      Authorization: "Bearer token"
      User-Agent: "SBKube/0.4.10"

  manifest-apply:
    type: yaml
    files:
      - downloaded-manifest.yaml
    depends_on:
      - manifest-download
```

**주요 필드**:

- `url` (필수): 다운로드 URL
- `dest` (필수): 저장할 파일 경로
- `headers` (선택): HTTP 헤더 (dict)

**워크플로우**:

1. **prepare**: `curl`을 사용해 파일 다운로드
1. 후속 `yaml` 타입 앱이 다운로드된 파일 사용

---

### 5. `action` - 커스텀 액션

**목적**: 복잡한 배포 시나리오를 위한 커스텀 액션 시퀀스 **워크플로우**: `deploy` 단계에서 실행

#### 설정 예제

```yaml
apps:
  monitoring-setup:
    type: action
    actions:
      - type: apply
        path: manifests/namespace.yaml
      - type: apply
        path: manifests/crd.yaml
      - type: apply
        path: manifests/deployment.yaml
      - type: delete
        path: manifests/old-resource.yaml
```

**주요 필드**:

- `actions` (필수): 액션 목록
  - `type` (필수): `apply` 또는 `delete`
  - `path` (필수): YAML 파일 경로

**워크플로우**:

1. **prepare**: 건너뜀
1. **build**: 액션 유효성 검증
1. **deploy**: 순서대로 `kubectl apply/delete` 실행

---

### 6. `exec` - 커스텀 명령어 실행

**목적**: 임의의 명령어 실행 (초기화, 정리 등) **워크플로우**: `deploy` 단계에서 실행

#### 설정 예제

```yaml
apps:
  pre-deployment-check:
    type: exec
    commands:
      - echo "Checking cluster health..."
      - kubectl get nodes
      - helm list -A

  post-deployment-cleanup:
    type: exec
    commands:
      - kubectl delete pods --field-selector=status.phase=Succeeded
      - echo "Cleanup completed!"
    depends_on:
      - pre-deployment-check
```

**주요 필드**:

- `commands` (필수): 실행할 명령어 목록 (list of strings)

**워크플로우**:

1. **prepare**: 건너뜀
1. **build**: 명령어 유효성 검증
1. **deploy**: 순서대로 명령어 실행

---

### 7. `noop` - No Operation (더미)

**목적**: 실제 동작 없이 의존성 관리용 **워크플로우**: 모든 단계에서 건너뜀

#### 설정 예제

```yaml
apps:
  base-setup:
    type: noop
    description: "Base setup completed by manual process"

  app1:
    type: helm
    chart: my/app1
    depends_on:
      - base-setup
```

**주요 필드**:

- `description` (선택): 설명

**워크플로우**:

- 모든 단계에서 건너뜀, 의존성 그래프에만 참여

---

## 🔄 타입 간 의존성

현재 버전에서는 `depends_on` 필드로 앱 간 의존성을 명시할 수 있습니다.

### 예제 1: Git + Helm

```yaml
apps:
  source:
    type: git
    repo: my-app

  app:
    type: helm
    chart: ./repos/my-app/chart
    depends_on:
      - source
```

### 예제 2: HTTP + YAML

```yaml
apps:
  download:
    type: http
    url: https://example.com/crd.yaml
    dest: crd.yaml

  apply:
    type: yaml
    files:
      - crd.yaml
    depends_on:
      - download
```

### 예제 3: Exec + Helm

```yaml
apps:
  check:
    type: exec
    commands:
      - kubectl get nodes

  deploy:
    type: helm
    chart: my/app
    depends_on:
      - check
```

---

## 📋 타입 선택 가이드

| 타입 | 사용 시점 | 예제 | |------|----------|------| | `helm` | Helm 차트 배포 (원격/로컬) | grafana/grafana, ./charts/app | | `yaml` |
직접 YAML 매니페스트 | deployment.yaml, service.yaml | | `git` | Git에서 차트 가져오기 | GitHub 리포지토리 | | `http` | URL에서 파일 다운로드 | CRD,
매니페스트 | | `action` | 복잡한 배포 시퀀스 | CRD → 앱 → 설정 | | `exec` | 초기화/정리 작업 | 클러스터 체크, 정리 | | `noop` | 의존성 관리 | 수동 설정 완료 표시 |

---

## 🚀 이전 버전에서 마이그레이션

### Before

```yaml
apps:
  - name: grafana-pull
    type: helm
    specs:
      repo: grafana
      chart: grafana
      dest: grafana

  - name: grafana
    type: helm
    specs:
      path: grafana
      values:
        - grafana.yaml
```

### After

```yaml
apps:
  grafana:
    type: helm
    chart: grafana/grafana
    values:
      - grafana.yaml
```

**자동 마이그레이션**:

```bash
```

---

### 6. `hook` - HookApp (Hook as First-Class App)

**목적**: Hook을 독립된 앱으로 관리하여 재사용 가능한 초기화 작업 수행

**워크플로우**: `deploy`만 실행 (`prepare`, `build`, `template` 건너뜀)

**도입 버전**: v0.8.0 (Phase 4)

#### 기본 사용법

```yaml
apps:
  # 1. 기본 앱 배포
  - name: cert-manager
    type: helm
    specs:
      repo: jetstack
      chart: cert-manager

  # 2. HookApp으로 초기화 작업
  - name: setup-cluster-issuers
    type: hook  # Hook을 First-class App으로
    enabled: true

    hooks:
      post_deploy_tasks:
        - type: manifests
          paths:
            - manifests/letsencrypt-staging.yaml
            - manifests/letsencrypt-prod.yaml
```

#### 특징

| 특징 | 설명 |
|------|------|
| **독립된 앱** | 다른 앱과 동일하게 관리 |
| **Lifecycle 간소화** | `prepare`, `build`, `template` 건너뜀, `deploy`만 실행 |
| **재사용 가능** | 다른 프로젝트/환경에서도 사용 가능 |
| **Enabled 플래그** | `enabled: false`로 쉽게 비활성화 |
| **Dependency 지원** | 앱 간 의존성 관리 |

#### 실행 순서

```
1. cert-manager (type: helm)
   └─ prepare/build/template/deploy 모두 실행

2. setup-cluster-issuers (type: hook)
   └─ deploy만 실행 (post_deploy_tasks)
```

#### 사용 시나리오

1. **초기화 작업**: ClusterIssuer, IngressClass 등 설정 리소스
2. **데이터베이스 스키마**: Schema 생성, Seed 데이터
3. **검증**: Health check, Smoke test
4. **복잡한 체인**: 여러 HookApp을 순차 실행

#### HookApp vs 일반 Hook

| 항목 | 일반 Hook (앱에 종속) | HookApp |
|------|---------------------|---------|
| 정의 | 기존 앱의 `hooks:` 섹션 | 독립된 `type: hook` 앱 |
| 재사용성 | ❌ 낮음 | ✅ 높음 |
| Enabled 플래그 | ❌ 없음 | ✅ 있음 |
| 개별 배포 | ❌ 불가 | ✅ 가능 |

#### 참고 문서

- **[Hooks 레퍼런스](./hooks-reference.md)** - HookApp 상세 설명
- **[Hooks 마이그레이션 가이드](./hooks-migration-guide.md)** - Phase 3 → Phase 4 전환
- **[예제: hooks-hookapp-simple/](../../examples/hooks-hookapp-simple/)** - HookApp 입문
- **[예제: hooks-phase4/](../../examples/hooks-phase4/)** - 복잡한 HookApp 체인

---

*더 많은 예제는 [examples/](../../examples/) 디렉토리를 참조하세요.*
