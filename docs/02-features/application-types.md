# 🎯 SBKube 애플리케이션 타입 가이드

SBKube는 다양한 소스와 배포 방식을 지원하는 10가지 애플리케이션 타입을 제공합니다. 각 타입은 특정 용도와 워크플로우에 최적화되어 있습니다.

______________________________________________________________________

## 📦 소스 준비 타입 (5개)

### 1. `pull-helm` - Helm 저장소 차트

**목적**: Helm 저장소에서 차트를 다운로드\
**사용 시점**: `prepare` → `build` → `template` → `deploy`

#### 설정 예제

```yaml
- name: nginx-helm
  type: pull-helm
  specs:
    repo: bitnami           # sources.yaml에 정의된 저장소명
    chart: nginx            # 차트 이름
    dest: nginx-custom      # 다운로드할 디렉토리명 (선택사항)
    chart_version: "15.1.0" # 차트 버전 (선택사항)
    app_version: "1.25.1"   # 앱 버전 (선택사항)
    removes:                # 제거할 파일 패턴 (선택사항)
      - "templates/tests/"
    overrides:              # 덮어쓸 파일 (선택사항)
      - "custom-values.yaml"
```

#### 워크플로우

1. **prepare**: Helm 저장소에서 차트 다운로드 → `charts/<dest>/`
1. **build**: 차트를 빌드 디렉토리로 복사 → `build/<name>/`
1. **template**: Helm 차트 템플릿 렌더링
1. **deploy**: Helm 릴리스 설치

______________________________________________________________________

### 2. `pull-helm-oci` - OCI 레지스트리 차트

**목적**: OCI 호환 레지스트리에서 Helm 차트 다운로드\
**사용 시점**: `prepare` → `build` → `template` → `deploy`

#### 설정 예제

```yaml
- name: argo-cd
  type: pull-helm-oci
  specs:
    repo: ghcr.io/argoproj/argo-helm
    chart: argo-cd
    dest: argocd
    chart_version: "5.46.7"
    registry_url: "ghcr.io"  # OCI 레지스트리 URL
```

#### 워크플로우

1. **prepare**: OCI 레지스트리에서 차트 pull → `charts/<dest>/`
1. **build**: 차트를 빌드 디렉토리로 복사
1. **template**: Helm 차트 템플릿 렌더링
1. **deploy**: Helm 릴리스 설치

______________________________________________________________________

### 3. `pull-git` - Git 저장소 클론

**목적**: Git 저장소에서 특정 경로의 파일들을 가져오기\
**사용 시점**: `prepare` → `build` → 후속 배포

#### 설정 예제

```yaml
- name: custom-charts
  type: pull-git
  specs:
    repo: stacklok-toolhive    # sources.yaml에 정의된 Git 저장소명
    paths:
      - src: deploy/charts/operator     # Git 저장소 내 경로
        dest: toolhive-operator         # 로컬 대상 경로
      - src: deploy/charts/operator-crds
        dest: toolhive-operator-crds
```

#### sources.yaml 예제

```yaml
git_repos:
  stacklok-toolhive: 
    url: https://github.com/stacklok/toolhive.git
    branch: main
```

#### 워크플로우

1. **prepare**: Git 저장소 클론 → `repos/<repo>/`
1. **build**: 지정된 경로 파일들 복사 → `build/<name>/`

______________________________________________________________________

### 4. `pull-http` - HTTP 파일 다운로드

**목적**: HTTP URL에서 파일을 다운로드\
**사용 시점**: `prepare` → `build`

#### 설정 예제

```yaml
- name: external-manifest
  type: pull-http
  specs:
    url: https://raw.githubusercontent.com/example/repo/main/manifest.yaml
    paths:
      - src: manifest.yaml
        dest: custom-manifest.yaml
```

#### 워크플로우

1. **prepare**: HTTP URL에서 파일 다운로드
1. **build**: 파일을 빌드 디렉토리로 복사

______________________________________________________________________

### 5. `copy-app` - 로컬 파일 복사

**목적**: 로컬 파일 및 디렉토리를 빌드 디렉토리로 복사\
**사용 시점**: `build`

#### 설정 예제

```yaml
- name: local-configs
  type: copy-app
  specs:
    paths:
      - src: manifests/           # 로컬 소스 경로
        dest: kubernetes/         # 빌드 디렉토리 내 대상 경로
      - src: config/app.yaml
        dest: app-config.yaml
```

#### 워크플로우

1. **build**: 로컬 파일을 빌드 디렉토리로 복사 → `build/<name>/`

______________________________________________________________________

## 🚀 배포 실행 타입 (5개)

### 6. `install-helm` - Helm 차트 설치

**목적**: Helm 차트를 사용하여 Kubernetes에 설치\
**사용 시점**: `template`, `deploy`, `upgrade`, `delete`

#### 설정 예제

```yaml
- name: nginx-app
  type: install-helm
  specs:
    path: nginx-custom        # 빌드된 차트 경로 (build/ 기준)
    values:                   # Helm 값 파일들
      - nginx-values.yaml
      - production-values.yaml
  release_name: my-nginx      # Helm 릴리스명
  namespace: web
```

#### 워크플로우

1. **template**: `helm template` 실행 → `rendered/<name>/`
1. **deploy**: `helm install` 실행
1. **upgrade**: `helm upgrade` 실행
1. **delete**: `helm uninstall` 실행

______________________________________________________________________

### 7. `install-yaml` - YAML 매니페스트 배포

**목적**: Helm 없이 직접 YAML 매니페스트를 배포\
**사용 시점**: `template`, `deploy`, `delete`

#### 설정 예제

```yaml
- name: simple-app
  type: install-yaml
  specs:
    actions:
      - type: apply           # apply, create, delete
        path: deployment.yaml # 매니페스트 파일 경로
      - type: apply
        path: service.yaml
```

#### 워크플로우

1. **template**: YAML 파일을 렌더링 디렉토리로 복사
1. **deploy**: `kubectl apply -f` 실행
1. **delete**: `kubectl delete -f` 실행

______________________________________________________________________

### 8. `install-action` - 사용자 정의 액션

**목적**: 사용자 정의 스크립트나 액션 실행\
**사용 시점**: `deploy`, `delete`

#### 설정 예제

```yaml
- name: custom-deployment
  type: install-action
  specs:
    actions:
      - type: apply
        path: custom-script.sh  # 실행할 스크립트
    uninstall:                # 삭제 시 실행할 스크립트
      script: cleanup.sh
```

#### 워크플로우

1. **deploy**: 지정된 액션 스크립트 실행
1. **delete**: uninstall 스크립트 실행 (정의된 경우)

______________________________________________________________________

### 9. `install-kustomize` - Kustomize 배포

**목적**: Kustomize를 사용하여 매니페스트 커스터마이징 후 배포\
**사용 시점**: `deploy`

#### 설정 예제

```yaml
- name: kustomized-app
  type: install-kustomize
  specs:
    kustomize_path: overlays/production  # kustomization.yaml 위치
```

#### 워크플로우

1. **deploy**: `kubectl apply -k <kustomize_path>` 실행

______________________________________________________________________

### 10. `exec` - 임의 명령어 실행

**목적**: 임의의 명령어나 스크립트 실행\
**사용 시점**: `deploy`

#### 설정 예제

```yaml
- name: database-migration
  type: exec
  specs:
    commands:
      - "kubectl create secret generic db-secret --from-literal=password=secret"
      - "kubectl apply -f migration-job.yaml"
      - "kubectl wait --for=condition=complete job/db-migration --timeout=300s"
```

#### 워크플로우

1. **deploy**: 지정된 명령어들을 순차적으로 실행

______________________________________________________________________

## 🔄 타입별 워크플로우 매트릭스

| 타입 | prepare | build | template | deploy | upgrade | delete |
|------|---------|-------|----------|--------|---------|--------| | `pull-helm` | ✅ | ✅ | ✅ | ✅ | ✅ | ✅ | |
`pull-helm-oci` | ✅ | ✅ | ✅ | ✅ | ✅ | ✅ | | `pull-git` | ✅ | ✅ | - | - | - | - | | `pull-http` | ✅ | ✅ | - | - | - | - |
| `copy-app` | - | ✅ | - | - | - | - | | `install-helm` | - | - | ✅ | ✅ | ✅ | ✅ | | `install-yaml` | - | - | ✅ | ✅ | - |
✅ | | `install-action` | - | - | - | ✅ | - | ✅ | | `install-kustomize` | - | - | - | ✅ | - | - | | `exec` | - | - | - |
✅ | - | - |

______________________________________________________________________

## 🎯 실제 사용 패턴

### 패턴 1: Helm 차트 커스터마이징

```yaml
# 1. 소스 준비
- name: nginx-source
  type: pull-helm
  specs:
    repo: bitnami
    chart: nginx

# 2. 배포 실행  
- name: nginx-deploy
  type: install-helm
  specs:
    path: nginx-source
    values: [custom-values.yaml]
```

### 패턴 2: Git 소스 + 직접 배포

```yaml
# 1. Git에서 매니페스트 가져오기
- name: app-manifests
  type: pull-git
  specs:
    repo: my-app-repo
    paths:
      - src: k8s/
        dest: manifests/

# 2. YAML 직접 배포
- name: app-deploy
  type: install-yaml
  specs:
    actions:
      - type: apply
        path: manifests/
```

### 패턴 3: 로컬 파일 + 커스텀 스크립트

```yaml
# 1. 로컬 설정 복사
- name: local-configs
  type: copy-app
  specs:
    paths:
      - src: configs/
        dest: app-configs/

# 2. 커스텀 배포 스크립트
- name: custom-deploy
  type: install-action
  specs:
    actions:
      - type: apply
        path: deploy-script.sh
```

______________________________________________________________________

## 💡 타입 선택 가이드

### 🎯 소스 타입 선택

- **공식 Helm 차트 사용** → `pull-helm`
- **OCI 레지스트리 차트** → `pull-helm-oci`
- **Git 저장소의 특정 파일** → `pull-git`
- **HTTP URL의 파일** → `pull-http`
- **로컬 파일/디렉토리** → `copy-app`

### 🚀 배포 타입 선택

- **Helm 릴리스 관리 필요** → `install-helm`
- **간단한 YAML 배포** → `install-yaml`
- **복잡한 배포 로직** → `install-action`
- **Kustomize 사용** → `install-kustomize`
- **임의 명령어 실행** → `exec`

______________________________________________________________________

*각 타입의 상세한 스펙 정의는 [config-schema.md](../03-configuration/config-schema.md)를 참조하세요.*
