# 🔧 SBKube 설정 가이드

SBKube의 설정 시스템에 대한 종합적인 가이드입니다.

______________________________________________________________________

## 📋 설정 파일 개요

SBKube는 두 가지 주요 설정 파일을 사용합니다:

| 파일 | 목적 | 위치 | 필수 여부 | |------|------|------|-----------| | **`sources.yaml`** | 외부 소스 정의 | 프로젝트 루트 | 선택적 | |
**`config.yaml`** | 애플리케이션 정의 | `config/` 디렉토리 | 필수 |

______________________________________________________________________

## 🌐 sources.yaml - 외부 소스 설정

외부 Helm 저장소와 Git 저장소를 정의합니다.

### 기본 구조

```yaml
# 클러스터 정보 (선택적)
cluster: production-cluster
kubeconfig: ~/.kube/config

# Helm 저장소 정의
helm_repos:
  bitnami: https://charts.bitnami.com/bitnami
  prometheus: https://prometheus-community.github.io/helm-charts
  nginx: https://kubernetes.github.io/ingress-nginx

# Git 저장소 정의
git_repos:
  my-app-charts:
    url: https://github.com/example/k8s-charts.git
    branch: main
  private-repo:
    url: https://github.com/company/private-charts.git
    branch: develop
    # SSH 키나 토큰 필요한 경우 Git 설정 활용
```

### 사용 예제

```yaml
# sources.yaml 예제
cluster: k3s-dev
kubeconfig: ~/.kube/k3s-config

helm_repos:
  # 공식 저장소들
  stable: https://charts.helm.sh/stable
  bitnami: https://charts.bitnami.com/bitnami
  
  # 커뮤니티 저장소들
  prometheus-community: https://prometheus-community.github.io/helm-charts
  grafana: https://grafana.github.io/helm-charts
  
  # 사내 저장소
  company-charts: https://charts.company.com/

git_repos:
  # 사내 차트 저장소
  internal-charts:
    url: https://github.com/company/k8s-charts.git
    branch: production
    
  # 설정 저장소  
  config-repo:
    url: https://github.com/company/k8s-configs.git
    branch: main
```

______________________________________________________________________

## ⚙️ config.yaml - 애플리케이션 설정

애플리케이션의 배포 정보를 정의합니다.

### 기본 구조

```yaml
# 전역 설정
namespace: default        # 기본 네임스페이스
cluster: my-cluster      # 클러스터 이름 (선택적)

# 종속성 (선택적)
deps: []                 # 다른 config의 종속성

# 애플리케이션 목록
apps:
  - name: app-name       # 앱 이름 (고유)
    type: app-type       # 앱 타입 (10가지 중 선택)
    enabled: true        # 활성화 여부 (기본: true)
    namespace: custom-ns # 앱별 네임스페이스 (선택적)
    release_name: my-app # Helm 릴리스명 (Helm 앱만)
    specs:               # 타입별 상세 설정
      # 타입에 따른 설정 내용
```

### 앱 타입별 설정 예제

#### 1. Helm 차트 배포

```yaml
apps:
  # 1단계: 소스 준비
  - name: nginx-source
    type: pull-helm
    specs:
      repo: bitnami           # sources.yaml의 저장소명
      chart: nginx            # 차트명
      dest: nginx-custom      # 로컬 저장 디렉토리
      chart_version: "15.1.0" # 차트 버전 (선택적)
      
  # 2단계: 배포 실행
  - name: nginx-app
    type: install-helm
    specs:
      path: nginx-custom      # 빌드된 차트 경로
      values:                 # Helm values 파일들
        - nginx-values.yaml
        - production-override.yaml
    release_name: my-nginx
    namespace: web
```

#### 2. YAML 매니페스트 배포

```yaml
apps:
  - name: simple-webapp
    type: install-yaml
    specs:
      actions:
        - type: apply         # apply, create, delete
          path: deployment.yaml
        - type: apply
          path: service.yaml
        - type: apply
          path: ingress.yaml
    namespace: apps
```

#### 3. Git 소스 통합

```yaml
apps:
  # Git에서 소스 가져오기
  - name: fetch-configs
    type: pull-git
    specs:
      repo: config-repo       # sources.yaml의 Git 저장소명
      paths:
        - src: k8s/production # Git 저장소 내 경로
          dest: prod-configs  # 로컬 대상 경로
        - src: manifests/
          dest: app-manifests/
          
  # 가져온 설정으로 배포
  - name: deploy-configs
    type: install-yaml
    specs:
      actions:
        - type: apply
          path: prod-configs/
```

______________________________________________________________________

## 🎯 고급 설정 패턴

### 환경별 설정 관리

```bash
# 디렉토리 구조
my-project/
├── sources.yaml                    # 공통 소스
├── environments/
│   ├── development/
│   │   └── config.yaml            # 개발 환경
│   ├── staging/  
│   │   └── config.yaml            # 스테이징 환경
│   └── production/
│       └── config.yaml            # 프로덕션 환경
└── values/                        # 공통 values 파일들
    ├── common-values.yaml
    ├── dev-values.yaml
    └── prod-values.yaml

# 환경별 실행
sbkube --app-dir environments/development deploy
sbkube --app-dir environments/production deploy
```

### 조건부 앱 활성화

```yaml
apps:
  # 개발 환경에서만 활성화
  - name: debug-tools
    type: install-helm
    enabled: false            # 기본적으로 비활성화
    specs:
      path: debug-chart
      
  # 프로덕션에서만 활성화  
  - name: monitoring
    type: install-helm
    enabled: true
    specs:
      path: prometheus-stack
```

### 복잡한 워크플로우

```yaml
apps:
  # 1. 인프라 준비
  - name: namespace-setup
    type: exec
    specs:
      commands:
        - "kubectl create namespace app-system --dry-run=client -o yaml | kubectl apply -f -"
        - "kubectl label namespace app-system managed-by=sbkube"
        
  # 2. 기본 리소스
  - name: base-resources
    type: install-yaml
    specs:
      actions:
        - type: apply
          path: rbac/
        - type: apply
          path: secrets/
          
  # 3. 애플리케이션
  - name: main-app
    type: install-helm
    specs:
      path: main-chart
      values: [app-values.yaml]
    depends_on: [namespace-setup, base-resources]  # 의존성 (향후 지원 예정)
```

______________________________________________________________________

## 🔍 설정 검증

### 자동 검증

```bash
# 설정 파일 유효성 검사
sbkube validate

# 특정 설정 파일 검사
sbkube validate --config-file staging-config.yaml
```

### Pydantic 스키마 기반 검증

SBKube는 강력한 타입 검증을 제공합니다:

- **필수 필드 검사**: 누락된 필수 필드 감지
- **타입 검증**: 잘못된 데이터 타입 감지
- **값 범위 검사**: 허용되지 않는 값 감지
- **구조 검증**: 잘못된 설정 구조 감지

### 일반적인 검증 오류

```yaml
# ❌ 잘못된 예제
apps:
  - name: ""              # 빈 이름
    type: "invalid-type"  # 지원되지 않는 타입
    specs: "not-object"   # 객체가 아닌 값

# ✅ 올바른 예제  
apps:
  - name: "valid-app"
    type: "install-helm"
    specs:
      path: "chart-path"
      values: []
```

______________________________________________________________________

## 🌐 환경 변수 및 전역 옵션

### 환경 변수 지원

```bash
# Kubernetes 설정
export KUBECONFIG=/path/to/kubeconfig
export KUBE_NAMESPACE=my-namespace

# SBKube 실행
sbkube deploy  # 환경 변수 자동 적용
```

### 명령행 옵션 우선순위

```
명령행 옵션 > 환경 변수 > 설정 파일 > 기본값
```

예시:

```bash
# 우선순위 적용 예제
export KUBE_NAMESPACE=env-namespace

sbkube --namespace cli-namespace deploy --app-dir config
# 실제 사용: cli-namespace (명령행 옵션이 최우선)
```

______________________________________________________________________

## 📚 관련 문서

- **[JSON 스키마 상세](config-schema.md)** - config.yaml 완전 스키마
- **[소스 스키마 상세](sources-schema.md)** - sources.yaml 완전 스키마
- **[설정 마이그레이션](migration.md)** - 버전 간 설정 업그레이드
- **[실제 예제](examples.md)** - 다양한 설정 예제 모음

______________________________________________________________________

*설정에 대한 추가 질문이 있으시면 [문제 해결 가이드](../07-troubleshooting/)를 참조하거나
[이슈 트래커](https://github.com/ScriptonBasestar/kube-app-manaer/issues)에 문의해 주세요.*
