# 🚀 SBKube 배포 가이드

SBKube 자체의 설치, 배포, 관리에 대한 종합 가이드입니다.

______________________________________________________________________

## 📦 설치 방법

### 1. PyPI를 통한 설치 (권장)

#### 최신 안정 버전

```bash
# 기본 설치
pip install sbkube

# 버전 확인
sbkube version
```

#### 특정 버전 설치

```bash
# 특정 버전 설치
pip install sbkube==0.1.10

# 최신 버전으로 업그레이드
pip install --upgrade sbkube
```

#### 가상 환경에서 설치

```bash
# venv 사용
python -m venv sbkube-env
source sbkube-env/bin/activate  # Linux/Mac
# sbkube-env\Scripts\activate   # Windows
pip install sbkube

# conda 사용
conda create -n sbkube python=3.12
conda activate sbkube
pip install sbkube
```

______________________________________________________________________

### 2. 소스코드에서 설치

#### 개발 버전 설치

```bash
# 저장소 클론
git clone https://github.com/ScriptonBasestar/kube-app-manaer.git
cd sb-kube-app-manager

# uv를 사용한 설치 (권장)
uv venv
source .venv/bin/activate
uv pip install -e .

# 또는 pip 사용
pip install -e .
```

#### 의존성 포함 설치

```bash
# 개발 의존성 포함
uv pip install -e ".[dev]"

# 테스트 의존성 포함  
uv pip install -e ".[test]"
```

______________________________________________________________________

### 3. Docker를 통한 설치

#### Docker 이미지 빌드

```bash
# Dockerfile 생성
cat > Dockerfile << 'EOF'
FROM python:3.12-slim

# 필수 도구 설치
RUN apt-get update && apt-get install -y \
    curl \
    git \
    && rm -rf /var/lib/apt/lists/*

# kubectl 설치
RUN curl -LO "https://dl.k8s.io/release/$(curl -L -s https://dl.k8s.io/release/stable.txt)/bin/linux/amd64/kubectl" \
    && chmod +x kubectl \
    && mv kubectl /usr/local/bin/

# helm 설치
RUN curl https://raw.githubusercontent.com/helm/helm/main/scripts/get-helm-3 | bash

# SBKube 설치
RUN pip install sbkube

WORKDIR /workspace
ENTRYPOINT ["sbkube"]
EOF

# 이미지 빌드
docker build -t sbkube:latest .

# 사용 예제
docker run --rm -v ~/.kube:/root/.kube -v $(pwd):/workspace sbkube:latest version
```

______________________________________________________________________

## 🔧 시스템 요구사항

### 필수 요구사항

- **Python**: 3.12 이상
- **운영체제**: Linux, macOS, Windows
- **메모리**: 최소 512MB RAM
- **디스크**: 최소 100MB 여유 공간

### 의존 도구

SBKube가 제대로 작동하려면 다음 도구들이 필요합니다:

#### kubectl 설치

```bash
# Linux
curl -LO "https://dl.k8s.io/release/$(curl -L -s https://dl.k8s.io/release/stable.txt)/bin/linux/amd64/kubectl"
sudo install -o root -g root -m 0755 kubectl /usr/local/bin/kubectl

# macOS (Homebrew)
brew install kubectl

# Windows (Chocolatey)
choco install kubernetes-cli
```

#### Helm 설치

```bash
# Linux/macOS
curl https://raw.githubusercontent.com/helm/helm/main/scripts/get-helm-3 | bash

# macOS (Homebrew)
brew install helm

# Windows (Chocolatey)
choco install kubernetes-helm
```

______________________________________________________________________

## 🌐 환경 설정

### 1. Kubernetes 클러스터 접근 설정

#### kubeconfig 설정

```bash
# 기본 kubeconfig 위치
~/.kube/config

# 환경 변수로 설정
export KUBECONFIG=/path/to/your/kubeconfig

# 여러 kubeconfig 파일 병합
export KUBECONFIG=~/.kube/config:~/.kube/cluster2-config
```

#### 클러스터 연결 확인

```bash
# SBKube로 클러스터 정보 확인
sbkube

# kubectl로 직접 확인
kubectl cluster-info
kubectl get nodes
```

### 2. 권한 설정

#### 필요한 RBAC 권한

SBKube가 작동하려면 다음 권한이 필요합니다:

```yaml
# sbkube-rbac.yaml
apiVersion: v1
kind: ServiceAccount
metadata:
  name: sbkube
  namespace: default
---
apiVersion: rbac.authorization.k8s.io/v1
kind: ClusterRole
metadata:
  name: sbkube-operator
rules:
- apiGroups: [""]
  resources: ["*"]
  verbs: ["*"]
- apiGroups: ["apps"]
  resources: ["*"]
  verbs: ["*"]
- apiGroups: ["extensions"]
  resources: ["*"]
  verbs: ["*"]
---
apiVersion: rbac.authorization.k8s.io/v1
kind: ClusterRoleBinding
metadata:
  name: sbkube-operator
roleRef:
  apiGroup: rbac.authorization.k8s.io
  kind: ClusterRole
  name: sbkube-operator
subjects:
- kind: ServiceAccount
  name: sbkube
  namespace: default
```

#### 적용

```bash
kubectl apply -f sbkube-rbac.yaml
```

______________________________________________________________________

## 🏢 프로덕션 배포

### 1. CI/CD 파이프라인 통합

#### GitHub Actions 예제

```yaml
# .github/workflows/deploy.yml
name: Deploy with SBKube

on:
  push:
    branches: [main]
  pull_request:
    branches: [main]

jobs:
  deploy:
    runs-on: ubuntu-latest
    steps:
    - uses: actions/checkout@v3
    
    - name: Setup Python
      uses: actions/setup-python@v4
      with:
        python-version: '3.12'
        
    - name: Install SBKube
      run: pip install sbkube
      
    - name: Setup kubectl
      uses: azure/setup-kubectl@v3
      
    - name: Setup Helm
      uses: azure/setup-helm@v3
      
    - name: Configure kubeconfig
      run: |
        mkdir -p ~/.kube
        echo "${{ secrets.KUBECONFIG }}" | base64 -d > ~/.kube/config
        
    - name: Validate configuration
      run: sbkube validate
      
    - name: Deploy to staging
      if: github.event_name == 'pull_request'
      run: |
        sbkube --namespace staging deploy --dry-run
        sbkube --namespace staging deploy
        
    - name: Deploy to production
      if: github.ref == 'refs/heads/main'
      run: |
        sbkube --namespace production deploy
```

#### GitLab CI 예제

```yaml
# .gitlab-ci.yml
stages:
  - validate
  - deploy-staging
  - deploy-production

variables:
  SBKUBE_VERSION: "0.4.5"

before_script:
  - pip install sbkube==$SBKUBE_VERSION
  - mkdir -p ~/.kube
  - echo "$KUBECONFIG_CONTENT" | base64 -d > ~/.kube/config

validate:
  stage: validate
  script:
    - sbkube validate
  only:
    - merge_requests
    - main

deploy-staging:
  stage: deploy-staging
  script:
    - sbkube --namespace staging deploy
  only:
    - merge_requests
  environment:
    name: staging

deploy-production:
  stage: deploy-production
  script:
    - sbkube --namespace production deploy
  only:
    - main
  environment:
    name: production
  when: manual
```

### 2. 모니터링 및 로깅

#### 배포 상태 모니터링

```bash
# 배포 상태 확인
sbkube state list

# 특정 클러스터 모니터링
sbkube state list --cluster production

# 상세 로그로 배포
sbkube --verbose deploy
```

#### 로그 수집 설정

```yaml
# logging-config.yaml
apiVersion: v1
kind: ConfigMap
metadata:
  name: sbkube-logging
data:
  config.yaml: |
    logging:
      level: INFO
      format: json
      output: /var/log/sbkube/deployment.log
```

______________________________________________________________________

## 🔄 업그레이드 및 마이그레이션

### SBKube 버전 업그레이드

```bash
# 현재 버전 확인
sbkube version

# 최신 버전으로 업그레이드
pip install --upgrade sbkube

# 특정 버전으로 업그레이드
pip install sbkube==0.2.0
```

### 설정 파일 마이그레이션

```bash
# 설정 호환성 확인
sbkube validate

# 마이그레이션 가이드 확인
# docs/03-configuration/migration.md 참조
```

______________________________________________________________________

## 🐳 컨테이너 환경

### Kubernetes Job으로 실행

```yaml
# sbkube-job.yaml
apiVersion: batch/v1
kind: Job
metadata:
  name: sbkube-deploy
spec:
  template:
    spec:
      containers:
      - name: sbkube
        image: python:3.12-slim
        command: ["/bin/bash"]
        args:
          - -c
          - |
            pip install sbkube kubectl helm
            sbkube deploy
        volumeMounts:
        - name: kubeconfig
          mountPath: /root/.kube
        - name: config
          mountPath: /workspace
      volumes:
      - name: kubeconfig
        secret:
          secretName: kubeconfig
      - name: config
        configMap:
          name: sbkube-config
      restartPolicy: Never
```

### Helm Chart로 패키징

```yaml
# helm-chart/templates/deployment.yaml
apiVersion: apps/v1
kind: Deployment
metadata:
  name: sbkube-operator
spec:
  replicas: 1
  selector:
    matchLabels:
      app: sbkube-operator
  template:
    metadata:
      labels:
        app: sbkube-operator
    spec:
      containers:
      - name: sbkube
        image: sbkube:{{ .Values.image.tag }}
        command: ["sbkube"]
        args: ["state", "watch"]  # 상태 모니터링 모드
```

______________________________________________________________________

## 🚨 보안 고려사항

### 1. 권한 최소화

```yaml
# 제한된 권한 예제
apiVersion: rbac.authorization.k8s.io/v1
kind: Role
metadata:
  name: sbkube-limited
  namespace: apps
rules:
- apiGroups: ["apps"]
  resources: ["deployments", "services"]
  verbs: ["get", "list", "create", "update", "patch"]
```

### 2. 비밀 정보 관리

```bash
# kubeconfig를 Secret으로 관리
kubectl create secret generic kubeconfig \
  --from-file=config=/path/to/kubeconfig \
  --namespace=sbkube-system

# 환경 변수로 전달
export KUBECONFIG=/dev/stdin
kubectl get secret kubeconfig -o jsonpath='{.data.config}' | base64 -d | sbkube deploy
```

______________________________________________________________________

## 📊 성능 최적화

### 1. 병렬 처리

```bash
# 여러 앱 동시 처리
sbkube build  # 자동으로 병렬 처리

# 리소스 제한 설정
export SBKUBE_MAX_WORKERS=4
```

### 2. 캐싱 활용

```bash
# Helm 차트 캐시 활용
export HELM_CACHE_HOME=/path/to/cache

# Git 저장소 캐시
export SBKUBE_CACHE_DIR=/path/to/sbkube-cache
```

______________________________________________________________________

## 🔍 문제 해결

### 일반적인 설치 문제

```bash
# 의존성 문제 해결
pip install --upgrade pip setuptools wheel
pip install sbkube

# 권한 문제 해결
pip install --user sbkube

# Python 버전 확인
python --version  # 3.12 이상 필요
```

### 런타임 문제 해결

```bash
# 상세 로그 확인
sbkube --verbose deploy

# 설정 검증
sbkube validate

# 클러스터 연결 확인
sbkube  # kubeconfig 정보 표시
```

______________________________________________________________________

## 📚 관련 문서

- **[시작하기 가이드](../01-getting-started/)** - 기본 설치 및 사용법
- **[설정 가이드](../03-configuration/)** - 설정 파일 작성법
- **[문제 해결](../07-troubleshooting/)** - 일반적인 문제 해결
- **[개발자 가이드](../04-development/)** - 개발 환경 구성

______________________________________________________________________

*배포 관련 추가 질문이 있으시면 [이슈 트래커](https://github.com/ScriptonBasestar/kube-app-manaer/issues)에 문의해 주세요.*
