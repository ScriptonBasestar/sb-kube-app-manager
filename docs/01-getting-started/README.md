# 🚀 SBKube 시작하기

SBKube를 처음 사용하는 분들을 위한 빠른 시작 가이드입니다.

______________________________________________________________________

## 📦 설치

### 요구사항

- **Python 3.12** 이상
- **kubectl** - Kubernetes 클러스터 접근용
- **helm** - Helm 차트 관리용

### PyPI를 통한 설치

```bash
# 최신 안정 버전 설치
pip install sbkube

# 설치 확인
sbkube version
```

### 개발 환경 설치 (소스코드)

```bash
# 저장소 클론
git clone https://github.com/ScriptonBasestar/kube-app-manaer.git
cd sb-kube-app-manager

# uv를 사용한 설치 (권장)
uv venv
source .venv/bin/activate
uv pip install -e .
```

______________________________________________________________________

## ⚙️ 기본 설정

### 1. Kubernetes 클러스터 연결 확인

```bash
# kubeconfig 정보 확인
sbkube

# 특정 컨텍스트 사용
sbkube --context my-cluster --namespace my-namespace
```

### 2. 필수 도구 확인

SBKube는 다음 도구들이 설치되어 있는지 자동으로 확인합니다:

- `kubectl` - Kubernetes 클러스터 관리
- `helm` - Helm 차트 관리

______________________________________________________________________

## 🎯 첫 번째 배포

### Step 1: 프로젝트 디렉토리 생성

```bash
mkdir my-sbkube-project
cd my-sbkube-project
```

### Step 2: 소스 설정 파일 생성

`sources.yaml` 파일을 생성하세요:

```yaml
# sources.yaml - 외부 소스 정의
cluster: my-cluster
kubeconfig: ~/.kube/config

helm_repos:
  bitnami: https://charts.bitnami.com/bitnami
  nginx: https://kubernetes.github.io/ingress-nginx

git_repos:
  my-app-repo:
    url: https://github.com/example/my-app.git
    branch: main
```

### Step 3: 앱 설정 파일 생성

`config/config.yaml` 파일을 생성하세요:

```yaml
# config/config.yaml - 애플리케이션 정의
namespace: default

apps:
  # Helm 차트 배포 예제
  - name: nginx-ingress
    type: pull-helm
    specs:
      repo: nginx
      chart: ingress-nginx
      dest: nginx-ingress
  
  - name: nginx-deploy
    type: install-helm
    specs:
      path: nginx-ingress
      values: []
    release_name: my-nginx
    namespace: ingress-nginx

  # YAML 매니페스트 배포 예제  
  - name: simple-app
    type: install-yaml
    specs:
      actions:
        - type: apply
          path: manifests/deployment.yaml
        - type: apply  
          path: manifests/service.yaml
```

### Step 4: 기본 워크플로우 실행

```bash
# 1. 외부 소스 준비 (Helm 차트 다운로드)
sbkube prepare

# 2. 앱 빌드 (배포 가능한 형태로 준비)
sbkube build

# 3. 템플릿 렌더링 (YAML 미리보기)
sbkube template --output-dir rendered

# 4. 실제 배포
sbkube deploy
```

______________________________________________________________________

## 🔍 배포 확인

### 배포 상태 확인

```bash
# Helm 릴리스 확인
helm list -A

# Kubernetes 리소스 확인
kubectl get pods,svc -n ingress-nginx
kubectl get pods,svc -n default

# SBKube 배포 상태 확인 (신규 기능)
sbkube state list
```

### 로그 및 디버깅

```bash
# 상세 로그와 함께 실행
sbkube --verbose deploy

# Dry-run으로 미리 확인
sbkube deploy --dry-run
```

______________________________________________________________________

## 🛠️ 주요 사용 패턴

### 패턴 1: Helm 차트 배포

```bash
# 1. sources.yaml에 Helm 저장소 추가
# 2. config.yaml에 pull-helm + install-helm 앱 정의
# 3. prepare → build → deploy 실행
```

### 패턴 2: 직접 YAML 배포

```bash
# 1. YAML 매니페스트 파일 준비
# 2. config.yaml에 install-yaml 앱 정의
# 3. build → deploy 실행 (prepare 불필요)
```

### 패턴 3: Git 소스 통합

```bash
# 1. sources.yaml에 Git 저장소 추가
# 2. config.yaml에 pull-git 앱 정의
# 3. prepare → build → deploy 실행
```

______________________________________________________________________

## 📚 다음 단계

### 더 자세한 학습

- **[명령어 가이드](../02-features/commands.md)** - 각 명령어의 상세 옵션
- **[앱 타입 가이드](../02-features/application-types.md)** - 지원하는 10가지 앱 타입
- **[설정 가이드](../03-configuration/)** - 설정 파일 작성법

### 실제 예제 확인

- **[기본 예제](../06-examples/)** - 다양한 배포 시나리오
- **[examples/ 디렉토리](../../examples/)** - 실행 가능한 예제들

### 문제 해결

- **[문제 해결 가이드](../07-troubleshooting/)** - 일반적인 문제들
- **[FAQ](../07-troubleshooting/faq.md)** - 자주 묻는 질문

______________________________________________________________________

## 💡 팁과 모범 사례

### 🎯 효율적인 개발 워크플로우

```bash
# 특정 앱만 처리하여 빠른 개발
sbkube build --app my-app
sbkube deploy --app my-app

# 설정 검증 먼저 실행
sbkube validate

# Dry-run으로 안전하게 확인
sbkube deploy --dry-run
```

### 🔧 설정 관리 팁

- **환경별 설정**: 개발/스테이징/프로덕션 환경별로 별도 config 디렉토리 사용
- **값 파일 분리**: Helm values 파일을 환경별로 분리 관리
- **네임스페이스 관리**: 앱별로 적절한 네임스페이스 설정

### 🚨 주의사항

- **백업**: 중요한 클러스터에 배포하기 전 항상 백업 확인
- **권한**: 적절한 RBAC 권한 설정 확인
- **리소스**: 클러스터 리소스 여유분 확인

______________________________________________________________________

*SBKube를 사용해 주셔서 감사합니다! 문제가 있으시면 [이슈 트래커](https://github.com/ScriptonBasestar/kube-app-manaer/issues)에 신고해 주세요.*
