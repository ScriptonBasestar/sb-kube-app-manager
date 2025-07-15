# 📋 config.yaml 스키마 상세 가이드

SBKube의 메인 설정 파일인 `config.yaml`의 완전한 스키마 문서입니다.

______________________________________________________________________

## 📂 파일 구조 개요

```yaml
# config.yaml 기본 구조
namespace: string              # 전역 기본 네임스페이스
cluster: string               # 클러스터 식별자 (선택적)
deps: [string]                # 종속성 목록 (선택적)

apps:                         # 애플리케이션 목록 (필수)
  - name: string              # 앱 이름 (필수)
    type: enum                # 앱 타입 (필수)
    enabled: boolean          # 활성화 여부 (기본: true)
    path: string              # 경로 (선택적)
    namespace: string         # 앱별 네임스페이스 (선택적)
    release_name: string      # Helm 릴리스명 (Helm 앱만)
    specs: object             # 타입별 상세 설정 (필수)
```

______________________________________________________________________

## 🌐 전역 설정

### namespace (string, 필수)

모든 앱에 적용되는 기본 네임스페이스입니다.

```yaml
namespace: default
# 또는
namespace: production
```

**규칙:**

- Kubernetes 네임스페이스 명명 규칙 준수
- 소문자와 하이픈만 사용
- 앱별 설정으로 재정의 가능

### cluster (string, 선택적)

클러스터 식별자입니다. 상태 관리 시 사용됩니다.

```yaml
cluster: production-k8s
# 또는
cluster: dev-cluster
```

### deps (array of strings, 선택적)

다른 설정 파일에 대한 종속성을 정의합니다.

```yaml
deps:
  - base-infrastructure
  - shared-services
```

______________________________________________________________________

## 📱 앱 설정 (apps)

### 필수 필드

#### name (string, 필수)

앱의 고유 식별자입니다.

```yaml
apps:
  - name: nginx-app        # ✅ 올바른 예제
  - name: "my-web-app"     # ✅ 하이픈 포함
  - name: ""               # ❌ 빈 문자열 불가
  - name: nginx app        # ❌ 공백 불가
```

#### type (enum, 필수)

앱 타입을 지정합니다. 10가지 타입 중 선택해야 합니다.

```yaml
type: pull-helm          # ✅ 지원되는 타입
type: invalid-type       # ❌ 지원되지 않는 타입
```

**지원되는 타입:**

- `pull-helm` - Helm 저장소에서 차트 다운로드
- `pull-helm-oci` - OCI 레지스트리에서 차트 pull
- `pull-git` - Git 저장소 클론
- `pull-http` - HTTP URL에서 파일 다운로드
- `copy-app` - 로컬 파일 복사
- `install-helm` - Helm 차트 설치
- `install-yaml` - YAML 매니페스트 배포
- `install-action` - 사용자 정의 액션
- `install-kustomize` - Kustomize 배포
- `exec` - 임의 명령어 실행

#### specs (object, 필수)

앱 타입별 상세 설정을 담는 객체입니다.

```yaml
specs:
  # 타입별로 다른 구조를 가짐
```

### 선택적 필드

#### enabled (boolean, 기본값: true)

앱의 활성화 여부를 제어합니다.

```yaml
enabled: true            # 활성화 (기본값)
enabled: false           # 비활성화
```

#### path (string, 선택적)

앱과 관련된 경로를 지정합니다.

```yaml
path: charts/nginx       # 상대 경로
path: /absolute/path     # 절대 경로
```

#### namespace (string, 선택적)

앱별 네임스페이스입니다. 전역 설정을 재정의합니다.

```yaml
namespace: nginx-system  # 이 앱만 다른 네임스페이스
```

#### release_name (string, Helm 앱만)

Helm 릴리스명을 지정합니다.

```yaml
release_name: my-nginx-release
```

______________________________________________________________________

## 🎯 타입별 specs 상세

### 1. pull-helm

Helm 저장소에서 차트를 다운로드합니다.

```yaml
- name: nginx-source
  type: pull-helm
  specs:
    repo: bitnami              # 필수: sources.yaml의 저장소명
    chart: nginx               # 필수: 차트명
    dest: nginx-custom         # 선택적: 저장 디렉토리명
    chart_version: "15.1.0"    # 선택적: 차트 버전
    app_version: "1.25.1"      # 선택적: 앱 버전
    removes:                   # 선택적: 제거할 파일/디렉토리
      - "templates/tests/"
      - "NOTES.txt"
    overrides:                 # 선택적: 덮어쓸 파일
      - "custom-values.yaml"
```

**필수 필드:**

- `repo` (string) - sources.yaml에 정의된 저장소명
- `chart` (string) - 차트명

**선택적 필드:**

- `dest` (string) - 로컬 저장 디렉토리명 (기본값: 차트명)
- `chart_version` (string) - 특정 차트 버전
- `app_version` (string) - 특정 앱 버전
- `removes` (array of strings) - 제거할 파일 패턴
- `overrides` (array of strings) - 덮어쓸 파일 목록

### 2. pull-helm-oci

OCI 레지스트리에서 Helm 차트를 pull합니다.

```yaml
- name: argo-source
  type: pull-helm-oci
  specs:
    repo: ghcr.io/argoproj/argo-helm    # 필수: OCI 저장소 URL
    chart: argo-cd                      # 필수: 차트명
    dest: argocd                        # 선택적: 저장 디렉토리
    chart_version: "5.46.7"             # 선택적: 차트 버전
    registry_url: "ghcr.io"             # 선택적: 레지스트리 URL
```

### 3. pull-git

Git 저장소에서 파일을 가져옵니다.

```yaml
- name: config-source
  type: pull-git
  specs:
    repo: my-configs                    # 필수: sources.yaml의 Git 저장소명
    paths:                              # 필수: 복사할 경로 목록
      - src: k8s/production             # Git 저장소 내 소스 경로
        dest: prod-configs              # 로컬 대상 경로
      - src: manifests/
        dest: app-manifests/
```

### 4. pull-http

HTTP URL에서 파일을 다운로드합니다.

```yaml
- name: remote-manifest
  type: pull-http
  specs:
    url: https://raw.githubusercontent.com/example/repo/main/manifest.yaml  # 필수
    paths:                              # 필수: 저장할 경로
      - src: manifest.yaml
        dest: downloaded-manifest.yaml
```

### 5. copy-app

로컬 파일/디렉토리를 복사합니다.

```yaml
- name: local-configs
  type: copy-app
  specs:
    paths:                              # 필수: 복사 경로 목록
      - src: local-manifests/           # 로컬 소스 경로
        dest: app-configs/              # 빌드 디렉토리 내 대상 경로
      - src: config.yaml
        dest: app-config.yaml
```

### 6. install-helm

Helm 차트를 설치합니다.

```yaml
- name: nginx-app
  type: install-helm
  specs:
    path: nginx-custom                  # 필수: 빌드된 차트 경로
    values:                             # 선택적: values 파일 목록
      - nginx-values.yaml
      - production-override.yaml
  release_name: my-nginx                # 선택적: Helm 릴리스명
  namespace: nginx-system               # 선택적: 네임스페이스
```

### 7. install-yaml

YAML 매니페스트를 직접 배포합니다.

```yaml
- name: simple-app
  type: install-yaml
  specs:
    actions:                            # 필수: 액션 목록
      - type: apply                     # apply, create, delete
        path: deployment.yaml           # 매니페스트 파일 경로
      - type: apply
        path: service.yaml
      - type: create
        path: secret.yaml
```

### 8. install-action

사용자 정의 액션을 실행합니다.

```yaml
- name: custom-setup
  type: install-action
  specs:
    actions:                            # 필수: 설치 액션
      - type: apply
        path: setup-script.sh
    uninstall:                          # 선택적: 제거 액션
      script: cleanup-script.sh
```

### 9. install-kustomize

Kustomize를 사용하여 배포합니다.

```yaml
- name: kustomized-app
  type: install-kustomize
  specs:
    kustomize_path: overlays/production # 필수: kustomization.yaml 위치
```

### 10. exec

임의의 명령어를 실행합니다.

```yaml
- name: setup-commands
  type: exec
  specs:
    commands:                           # 필수: 실행할 명령어 목록
      - "kubectl create namespace my-app --dry-run=client -o yaml | kubectl apply -f -"
      - "kubectl label namespace my-app managed-by=sbkube"
      - "echo 'Setup completed'"
```

______________________________________________________________________

## 🔍 검증 규칙

### 이름 규칙

```yaml
# ✅ 올바른 앱 이름
name: nginx-app
name: web-frontend
name: database-01

# ❌ 잘못된 앱 이름
name: ""                # 빈 문자열
name: "nginx app"       # 공백 포함
name: "NGINX-APP"       # 대문자 (권장하지 않음)
```

### 타입 검증

```yaml
# ✅ 지원되는 타입
type: pull-helm
type: install-yaml
type: exec

# ❌ 지원되지 않는 타입
type: pull-docker       # 존재하지 않는 타입
type: install-kubectl   # 올바른 타입: install-yaml
```

### 필수 필드 검증

```yaml
# ❌ 필수 필드 누락
apps:
  - name: my-app
    # type 누락 - 오류 발생
    
  - name: another-app
    type: install-helm
    # specs 누락 - 오류 발생
```

### 타입별 specs 검증

```yaml
# ❌ pull-helm의 잘못된 specs
- name: nginx
  type: pull-helm
  specs:
    # repo 필드 누락 - 오류
    chart: nginx

# ❌ install-yaml의 잘못된 specs  
- name: app
  type: install-yaml
  specs:
    # actions 필드 누락 - 오류
    files: ["app.yaml"]
```

______________________________________________________________________

## 📝 완전한 예제

### 기본 예제

```yaml
# config.yaml - 기본 구성
namespace: default

apps:
  # Helm 차트 준비 및 배포
  - name: nginx-source
    type: pull-helm
    specs:
      repo: bitnami
      chart: nginx
      dest: nginx-chart
      
  - name: nginx-app
    type: install-helm
    specs:
      path: nginx-chart
      values: [nginx-values.yaml]
    release_name: my-nginx
    namespace: web

  # YAML 직접 배포
  - name: simple-service
    type: install-yaml
    specs:
      actions:
        - type: apply
          path: manifests/
```

### 고급 예제

```yaml
# config.yaml - 고급 구성
namespace: production
cluster: prod-k8s
deps: [infrastructure, monitoring]

apps:
  # 다중 소스 준비
  - name: external-charts
    type: pull-git
    specs:
      repo: company-charts
      paths:
        - src: charts/backend
          dest: backend-chart
        - src: charts/frontend
          dest: frontend-chart
          
  - name: external-configs
    type: pull-http
    specs:
      url: https://config-server.company.com/k8s/prod.yaml
      paths:
        - src: prod.yaml
          dest: production-config.yaml

  # 로컬 파일 준비
  - name: local-secrets
    type: copy-app
    enabled: false              # 기본적으로 비활성화
    specs:
      paths:
        - src: secrets/
          dest: app-secrets/

  # 복잡한 배포 워크플로우
  - name: setup-namespace
    type: exec
    specs:
      commands:
        - "kubectl create namespace app-system --dry-run=client -o yaml | kubectl apply -f -"
        - "kubectl label namespace app-system env=production"

  - name: backend-app
    type: install-helm
    specs:
      path: backend-chart
      values:
        - common-values.yaml
        - backend-prod-values.yaml
    release_name: backend-service
    namespace: app-system

  - name: frontend-app
    type: install-kustomize
    specs:
      kustomize_path: overlays/production
    namespace: app-system

  # 설치 후 액션
  - name: post-install
    type: install-action
    specs:
      actions:
        - type: apply
          path: post-install.sh
```

______________________________________________________________________

## 🔗 관련 문서

- **[sources.yaml 스키마](sources-schema.md)** - 외부 소스 설정 스키마
- **[앱 타입 가이드](../02-features/application-types.md)** - 각 타입의 상세 사용법
- **[설정 예제](examples.md)** - 다양한 실제 사용 예제
- **[마이그레이션 가이드](migration.md)** - 버전 간 설정 업그레이드

______________________________________________________________________

*설정 스키마에 대한 추가 질문이 있으시면 [문제 해결 가이드](../07-troubleshooting/)를 참조하거나
[이슈 트래커](https://github.com/ScriptonBasestar/kube-app-manaer/issues)에 문의해 주세요.*
