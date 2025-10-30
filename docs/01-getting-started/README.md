# 🚀 SBKube 시작하기

SBKube을 처음 사용하는 분들을 위한 빠른 시작 가이드입니다.

> **주요 기능**: 간소화된 설정 구조, 통합된 Helm 타입, 차트 커스터마이징 기능 추가
>
> 이전 버전 사용자는 [마이그레이션 가이드](../MIGRATION_V3.md)를 참조하세요.

---

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

---

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

---

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

# 클러스터 설정 (필수, v0.4.10+)
kubeconfig: ~/.kube/config
kubeconfig_context: my-k3s-cluster
cluster: my-cluster  # 선택, 문서화 목적

# Helm 리포지토리
helm_repos:
  grafana: https://grafana.github.io/helm-charts
  nginx: https://kubernetes.github.io/ingress-nginx

# Git 리포지토리 (선택)
git_repos:
  my-app-repo:
    url: https://github.com/example/my-app.git
    branch: main
```

### Step 3: 앱 설정 파일 생성

`config/config.yaml` 파일을 생성하세요 :

```yaml
# config/config.yaml - 애플리케이션 정의
namespace: default

apps:
  # Helm 차트 배포 예제 (간소화됨!)
  nginx-ingress:
    type: helm
    chart: nginx/ingress-nginx
    namespace: ingress-nginx
    release_name: my-nginx

  # YAML 매니페스트 배포 예제
  simple-app:
    type: yaml
    files:
      - manifests/deployment.yaml
      - manifests/service.yaml

  # 또는 커스텀 액션 사용
  custom-setup:
    type: action
    actions:
      - type: apply
        path: manifests/configmap.yaml
      - type: apply
        path: manifests/deployment.yaml
```

**SBKube의 주요 개선사항**:

- `helm` + `helm` → 단일 `helm` 타입
- `yaml` → `yaml` 타입 (간소화)
- `action` → `action` 타입
- Apps는 이름을 key로 사용 (list → dict)
- `specs` 제거 (필드 평탄화)

### Step 4: 워크플로우 실행

**권장 방법** - 통합 실행:

```bash
# 모든 단계 자동 실행 (prepare → build → deploy)
sbkube apply --app-dir config --namespace default
```

**또는 단계별 실행**:

```bash
# 1. 외부 소스 준비 (Helm 차트 다운로드)
sbkube prepare --app-dir config

# 2. 앱 빌드 (차트 커스터마이징 적용)
sbkube build --app-dir config

# 3. 템플릿 렌더링 (YAML 미리보기)
sbkube template --app-dir config --output-dir rendered

# 4. 실제 배포
sbkube deploy --app-dir config --namespace default
```

**빠른 배포** (커스터마이징 없는 경우):

```bash
# build 단계 건너뛰기
sbkube apply --app-dir config --namespace default --skip-build
```

---

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

---

## 🛠️ 주요 사용 패턴

### 패턴 1: 원격 Helm 차트 배포

```yaml
apps:
  grafana:
    type: helm
    chart: grafana/grafana
    version: 6.50.0
    values:
      - grafana.yaml
```

```bash
sbkube apply --app-dir config --namespace data
```

### 패턴 2: 로컬 Helm 차트 배포

```yaml
apps:
  my-app:
    type: helm
    chart: ./charts/my-app
    values:
      - values.yaml
```

### 패턴 3: YAML 매니페스트 배포

```yaml
apps:
  nginx:
    type: yaml
    files:
      - manifests/deployment.yaml
      - manifests/service.yaml
```

### 패턴 4: Git 리포지토리 사용

```yaml
apps:
  source-code:
    type: git
    repo: my-app-repo
    path: charts/app
```

### 패턴 5: 차트 커스터마이징

```yaml
apps:
  cnpg:
    type: helm
    chart: cloudnative-pg/cloudnative-pg
    overrides:
      templates/secret.yaml: custom-secret.yaml
    removes:
      - templates/serviceaccount.yaml
```

---

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

---

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

---

*SBKube를 사용해 주셔서 감사합니다! 문제가 있으시면 [이슈 트래커](https://github.com/ScriptonBasestar/kube-app-manaer/issues)에 신고해 주세요.*
