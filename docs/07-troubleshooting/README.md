# 🔍 SBKube 문제 해결 가이드

SBKube 사용 중 발생할 수 있는 일반적인 문제들과 해결 방법을 제공합니다.

______________________________________________________________________

## 🚨 일반적인 문제들

### 1. 설치 및 환경 문제

#### ❌ Python 버전 호환성 오류

```bash
# 오류 메시지
ERROR: Python 3.12 is required, but you have 3.11
```

**해결 방법:**

```bash
# Python 버전 확인
python --version

# Python 3.12 이상 설치
# Ubuntu/Debian
sudo apt update && sudo apt install python3.12

# macOS (Homebrew)
brew install python@3.12

# pyenv 사용
pyenv install 3.12.0
pyenv global 3.12.0
```

#### ❌ 의존성 설치 실패

```bash
# 오류 메시지
ERROR: Could not find a version that satisfies the requirement sbkube
```

**해결 방법:**

```bash
# pip 업그레이드
pip install --upgrade pip setuptools wheel

# 캐시 클리어 후 재설치
pip cache purge
pip install sbkube

# 사용자 디렉토리에 설치
pip install --user sbkube
```

______________________________________________________________________

### 2. CLI 도구 관련 문제

#### ❌ kubectl 명령어를 찾을 수 없음

```bash
# 오류 메시지
❌ 'kubectl' 명령을 찾을 수 없습니다
```

**해결 방법:**

```bash
# kubectl 설치 확인
which kubectl

# kubectl 설치 (Linux)
curl -LO "https://dl.k8s.io/release/$(curl -L -s https://dl.k8s.io/release/stable.txt)/bin/linux/amd64/kubectl"
sudo install -o root -g root -m 0755 kubectl /usr/local/bin/kubectl

# PATH 환경 변수 확인
echo $PATH
export PATH=$PATH:/usr/local/bin
```

#### ❌ Helm 명령어를 찾을 수 없음

```bash
# 오류 메시지
❌ 'helm' 명령을 사용할 수 없습니다
```

**해결 방법:**

```bash
# Helm 설치
curl https://raw.githubusercontent.com/helm/helm/main/scripts/get-helm-3 | bash

# Helm 버전 확인
helm version

# PATH에 추가 (필요시)
export PATH=$PATH:/usr/local/bin
```

______________________________________________________________________

### 3. Kubernetes 연결 문제

#### ❌ kubeconfig 파일을 찾을 수 없음

```bash
# 오류 메시지
Kubeconfig 파일을 로드할 수 없습니다 (경로: ~/.kube/config)
```

**해결 방법:**

```bash
# kubeconfig 파일 존재 확인
ls -la ~/.kube/config

# 환경 변수로 경로 지정
export KUBECONFIG=/path/to/your/kubeconfig

# SBKube에서 직접 지정
sbkube --kubeconfig /path/to/kubeconfig deploy

# 클러스터 연결 테스트
kubectl cluster-info
```

______________________________________________________________________

#### ❌ Context를 찾을 수 없음

```bash
# 오류 메시지
❌ Kubernetes context 'my-context' not found in kubeconfig: ~/.kube/config

Available contexts in this kubeconfig:
  • k3d-cwrapper-local
  • minikube

📝 Please update sources.yaml with a valid context:
  kubeconfig_context: <valid-context-name>
```

**원인**: sources.yaml의 `kubeconfig_context`가 kubeconfig 파일에 존재하지 않음

**해결 방법**:

```bash
# 1. 사용 가능한 contexts 확인
kubectl config get-contexts

# 출력 예시:
# CURRENT   NAME                  CLUSTER               AUTHINFO
# *         k3d-cwrapper-local    k3d-cwrapper-local    admin@k3d-cwrapper-local
#           minikube              minikube              minikube

# 2. sources.yaml 수정
cat > config/sources.yaml <<EOF
cluster: my-cluster
kubeconfig: ~/.kube/config
kubeconfig_context: k3d-cwrapper-local  # ← NAME 컬럼 값 사용
helm_repos: {}
EOF

# 3. 배포 재시도
sbkube deploy --app-dir config --namespace test
```

**주의사항**:

- `cluster` 필드는 **사람용 레이블**이며, 아무 이름이나 사용 가능
- `kubeconfig_context`는 **kubectl의 실제 context 이름**이며, 정확히 일치해야 함
- context 이름은 대소문자를 구분함

**특정 kubeconfig 파일의 contexts 확인**:

```bash
kubectl config get-contexts --kubeconfig ~/.kube/my-cluster-config
```

**관련 FAQ**:
[cluster vs kubeconfig_context](faq.md#q1-cluster%EC%99%80-kubeconfig_context%EC%9D%98-%EC%B0%A8%EC%9D%B4%EB%8A%94-%EB%AC%B4%EC%97%87%EC%9D%B8%EA%B0%80%EC%9A%94)

______________________________________________________________________

#### ❌ 클러스터 접근 권한 부족

```bash
# 오류 메시지
Error: Forbidden (403): User cannot access resource
```

**해결 방법:**

```bash
# 현재 사용자 확인
kubectl auth whoami

# 권한 확인
kubectl auth can-i create deployments
kubectl auth can-i create services

# RBAC 설정 (클러스터 관리자 권한 필요)
kubectl create clusterrolebinding sbkube-admin \
  --clusterrole=cluster-admin \
  --user=$(kubectl config current-context)
```

______________________________________________________________________

### 4. 설정 파일 문제

#### ❌ YAML 구문 오류

```bash
# 오류 메시지
yaml.scanner.ScannerError: found character '\t' that cannot start any token
```

**해결 방법:**

```bash
# YAML 파일 검증
python -c "import yaml; yaml.safe_load(open('config.yaml'))"

# 온라인 YAML 검증기 사용
# https://yamlchecker.com/

# 들여쓰기 확인 (탭 대신 스페이스 사용)
cat -A config.yaml  # 탭 문자 확인
```

#### ❌ 설정 스키마 검증 실패

```bash
# 오류 메시지
ValidationError: 'invalid-type' is not one of ['exec', 'helm', ...]
```

**해결 방법:**

```bash
# 설정 파일 검증
sbkube validate

# 지원되는 앱 타입 확인
sbkube --help

# 올바른 타입으로 수정
# 지원 타입: helm, git, http, kustomize
#           helm, yaml, action, exec, noop
```

______________________________________________________________________

### 5. 배포 관련 문제

#### ❌ Helm 차트를 찾을 수 없음

```bash
# 오류 메시지
Error: failed to download chart: chart not found
```

**해결 방법:**

```bash
# Helm 저장소 업데이트
helm repo add grafana https://grafana.github.io/helm-charts
helm repo update

# 차트 존재 확인
helm search repo grafana/grafana

# sources.yaml 설정 확인
cat sources.yaml
```

#### ❌ Helm repo가 sources.yaml에 없음

```bash
# 오류 메시지
❌ Helm repo 'browserless' not found in sources.yaml
```

**원인:**

1. **OCI 레지스트리 사용 시**: `helm_repos` 대신 `oci_registries`에 있어야 함
1. **레포지토리 이름 오타**: sources.yaml과 config.yaml의 이름 불일치
1. **Deprecated 저장소 사용**: 더 이상 지원되지 않는 Helm 저장소

**해결 방법:**

**케이스 1: OCI 레지스트리 차트**

```yaml
# sources.yaml
oci_registries:
  browserless:
    registry: oci://tccr.io/truecharts
  gabe565:
    registry: oci://ghcr.io/gabe565/charts

# config.yaml
apps:
  browserless:
    type: helm
    chart: browserless/browserless-chrome
```

**케이스 2: 레포지토리 이름 오타**

```yaml
# ❌ 잘못된 예시
# sources.yaml
helm_repos:
  corecentric: https://codecentric.github.io/helm-charts  # 오타

# config.yaml
apps:
  mailhog:
    chart: codecentric/mailhog  # 철자 다름

# ✅ 올바른 예시
# sources.yaml
helm_repos:
  codecentric: https://codecentric.github.io/helm-charts

# config.yaml
apps:
  mailhog:
    chart: codecentric/mailhog
```

**케이스 3: Deprecated 저장소**

```yaml
# ❌ 잘못된 예시 (Helm Stable은 2020년에 deprecated)
helm_repos:
  kubernetes-charts: https://charts.helm.sh/stable

apps:
  descheduler:
    chart: kubernetes-charts/descheduler

# ✅ 올바른 예시
helm_repos:
  descheduler: https://kubernetes-sigs.github.io/descheduler/

apps:
  descheduler:
    chart: descheduler/descheduler
```

**검증 명령어:**

```bash
# 1. OCI 레지스트리 확인
helm pull oci://tccr.io/truecharts/browserless-chrome --version 1.0.0 --untar

# 2. Helm 저장소 확인
helm repo add codecentric https://codecentric.github.io/helm-charts
helm repo update
helm search repo codecentric/

# 3. sources.yaml 구조 확인
cat sources.yaml | grep -A 5 "oci_registries:"
cat sources.yaml | grep -A 5 "helm_repos:"
```

**참고:**

- OCI 레지스트리는 `helm repo add` 없이 직접 pull 가능
- 2020년 이후 Helm Stable (kubernetes-charts)은 사용 불가
- 차트별 공식 저장소는 [Artifact Hub](https://artifacthub.io/)에서 확인

#### ❌ 네임스페이스가 존재하지 않음

```bash
# 오류 메시지
Error: namespaces "my-namespace" not found
```

**해결 방법:**

```bash
# 네임스페이스 생성
kubectl create namespace my-namespace

# 또는 설정에서 기본 네임스페이스 사용
# config.yaml에서 namespace: default 설정
```

#### ❌ 리소스 충돌

```bash
# 오류 메시지
Error: Operation cannot be fulfilled: the object has been modified
```

**해결 방법:**

```bash
# 기존 리소스 확인
kubectl get all -n your-namespace

# 기존 Helm 릴리스 확인
helm list -A

# 강제 업데이트 (주의!)
helm upgrade --force my-release ./chart

# 또는 기존 리소스 삭제 후 재배포
sbkube delete
sbkube deploy
```

______________________________________________________________________

## 🔧 디버깅 방법

### 1. 상세 로그 활성화

```bash
# 상세 로그로 실행
sbkube --verbose deploy

# 특정 앱만 디버깅
sbkube --verbose build --app problematic-app
sbkube --verbose deploy --app problematic-app
```

### 2. Dry-run으로 테스트

```bash
# 실제 배포 없이 테스트
sbkube deploy --dry-run

# 템플릿 결과 확인
sbkube template --output-dir debug-output
cat debug-output/*/manifests.yaml
```

### 3. 단계별 실행

```bash
# 각 단계별로 분리 실행
sbkube validate       # 설정 검증
sbkube prepare        # 소스 준비
sbkube build          # 앱 빌드
sbkube template       # 템플릿 생성
sbkube deploy         # 배포 실행
```

### 4. 설정 파일 검증

```bash
# 설정 파일 구문 검사
sbkube validate

# 특정 설정 파일 검사
sbkube validate --config-file custom-config.yaml

# JSON 스키마로 검증
python -c "
import json, yaml, jsonschema
with open('schemas/config.schema.json') as f:
    schema = json.load(f)
with open('config/config.yaml') as f:
    config = yaml.safe_load(f)
jsonschema.validate(config, schema)
"
```

______________________________________________________________________

## 📊 상태 관리 문제

### ❌ 배포 상태 데이터베이스 오류

```bash
# 오류 메시지
sqlite3.OperationalError: database is locked
```

**해결 방법:**

```bash
# 상태 데이터베이스 위치 확인
ls -la ~/.sbkube/

# 잠금 파일 제거 (안전한 경우에만)
rm ~/.sbkube/deployment.db-lock

# 데이터베이스 재생성 (향후 기능 예정)
# sbkube reset-db
```

### 상태 정보 불일치

```bash
# 실제 클러스터와 상태 DB 동기화 (향후 기능 예정)
# sbkube sync-state

# 수동으로 상태 확인
kubectl get all -A
helm list -A
sbkube history
```

______________________________________________________________________

## 🌐 네트워크 관련 문제

### ❌ Git 저장소 접근 실패

```bash
# 오류 메시지
fatal: unable to access 'https://github.com/...': SSL certificate problem
```

**해결 방법:**

```bash
# Git SSL 검증 비활성화 (임시)
git config --global http.sslVerify false

# 올바른 Git 자격증명 설정
git config --global user.name "Your Name"
git config --global user.email "your.email@example.com"

# SSH 키 사용 (권장)
ssh-keygen -t rsa -b 4096 -C "your.email@example.com"
# GitHub에 공개키 등록 후 SSH URL 사용
```

### ❌ Helm 저장소 접근 실패

```bash
# 오류 메시지
Error: failed to fetch https://grafana.github.io/helm-charts/index.yaml
```

**해결 방법:**

```bash
# 네트워크 연결 확인
curl -I https://grafana.github.io/helm-charts/index.yaml

# 프록시 설정 (필요한 경우)
export HTTP_PROXY=http://proxy.company.com:8080
export HTTPS_PROXY=http://proxy.company.com:8080

# Helm 저장소 재추가
helm repo remove grafana
helm repo add grafana https://grafana.github.io/helm-charts
helm repo update
```

______________________________________________________________________

## 🚀 성능 관련 문제

### 배포 속도가 느림

```bash
# 병렬 처리 최적화
export SBKUBE_MAX_WORKERS=8

# 불필요한 앱 비활성화
# config.yaml에서 enabled: false 설정

# 캐시 활용
export HELM_CACHE_HOME=/tmp/helm-cache
```

### 메모리 사용량 과다

```bash
# 메모리 사용량 모니터링
top -p $(pgrep -f sbkube)

# 큰 차트 처리 시 메모리 제한
ulimit -v 2097152  # 2GB 제한

# 배치 처리로 분할
sbkube build --app app1
sbkube build --app app2
```

______________________________________________________________________

## 📱 플랫폼별 문제

### Windows 환경

```bash
# PowerShell에서 실행
python -m sbkube.cli deploy

# 경로 구분자 문제
# Windows에서는 '/' 대신 '\' 사용할 수 있지만
# YAML에서는 항상 '/' 사용 권장

# 권한 문제
# PowerShell을 관리자 권한으로 실행
```

### macOS 환경

```bash
# Homebrew 권한 문제
sudo chown -R $(whoami) /usr/local/Homebrew

# PATH 설정 문제
echo 'export PATH="/usr/local/bin:$PATH"' >> ~/.zshrc
source ~/.zshrc
```

______________________________________________________________________

## 📞 추가 지원

### 로그 수집

문제 신고 시 다음 정보를 포함해 주세요:

```bash
# 환경 정보 수집
sbkube version
python --version
kubectl version --client
helm version

# 상세 로그
sbkube --verbose deploy > sbkube.log 2>&1

# 설정 파일 (민감 정보 제거 후)
cat config.yaml
cat sources.yaml
```

### 커뮤니티 지원

- **[이슈 트래커](https://github.com/ScriptonBasestar/kube-app-manaer/issues)** - 버그 신고 및 기능 요청
- **[FAQ](faq.md)** - 자주 묻는 질문들
- **[GitHub Discussions](https://github.com/ScriptonBasestar/kube-app-manaer/discussions)** - 사용법 질문

______________________________________________________________________

## 🔧 빌드 및 Override 문제

### ❌ Override 파일이 적용되지 않음

#### 증상

- `overrides/` 디렉토리에 파일을 넣었지만 빌드 결과에 반영되지 않음
- `build/` 디렉토리에 override 파일이 없음
- 경고 메시지 표시:
  ```
  ⚠️  Override directory found but not configured: myapp
  ```

#### 원인

`config.yaml`에 `overrides` 필드를 명시하지 않음

#### 해결 방법

**1. config.yaml 확인**

```yaml
# ❌ 잘못된 설정 (overrides 필드 없음)
apps:
  myapp:
    type: helm
    chart: ingress-nginx/ingress-nginx
    # overrides 필드가 없음!
```

**2. overrides 필드 추가**

```yaml
# ✅ 올바른 설정
apps:
  myapp:
    type: helm
    chart: ingress-nginx/ingress-nginx
    overrides:
      - templates/configmap.yaml
      - files/config.txt
```

**3. 빌드 재실행**

```bash
sbkube build --app-dir .

# 성공 메시지 확인:
# 🔨 Building Helm app: myapp
#   Copying chart: .sbkube/charts/nginx/nginx → .sbkube/build/myapp
#   Applying 2 overrides...
#     ✓ Override: templates/configmap.yaml
#     ✓ Override: files/config.txt
# ✅ Helm app built: myapp
```

**4. 결과 검증**

```bash
# Override 파일들이 build/ 디렉토리에 복사되었는지 확인
ls -la build/myapp/templates/configmap.yaml
ls -la build/myapp/files/config.txt
```

#### 예방

- **v0.4.8+**: override 디렉토리가 있지만 설정되지 않은 경우 경고 메시지 자동 표시
- **체크리스트**:
  1. `overrides/[앱이름]/` 디렉토리 존재 확인
  1. `config.yaml`의 해당 앱에 `overrides:` 필드 추가
  1. 모든 override 파일을 리스트로 명시

### ❌ build 디렉토리가 비어있음

#### 증상

- `sbkube build` 실행 후 `build/` 디렉토리가 비어있거나 일부 앱만 생성됨
- 메시지: `⏭️ Skipping Helm app (no customization): myapp`

#### 원인

sbkube는 다음 조건일 때 **빌드를 건너뜁니다** (의도된 최적화):

- 로컬 차트 (`chart: ./charts/myapp`)
- `overrides` 없음
- `removes` 없음

이는 불필요한 파일 복사를 방지하기 위한 **정상 동작**입니다.

#### 해결 방법

**방법 1: Override 또는 Remove 추가** (커스터마이징 필요 시)

```yaml
myapp:
  type: helm
  chart: ./charts/myapp
  overrides:
    - templates/configmap.yaml  # 커스터마이징 추가
```

**방법 2: 원격 차트 사용**

```yaml
myapp:
  type: helm
  chart: ingress-nginx/ingress-nginx  # 원격 차트는 항상 빌드됨
  version: "4.0.0"
```

**방법 3: 빌드 없이 배포** (로컬 차트 + 커스터마이징 없음)

```bash
# build 건너뛰고 바로 template/deploy
sbkube template --app-dir .
sbkube deploy --app-dir .
```

**방법 4: 차트 변경**

```yaml
myapp:
  type: helm
  chart: grafana/grafana  # 원격 차트는 항상 빌드됨
  version: "6.50.0"
```

#### 확인

```bash
sbkube build --app-dir . --verbose

# 출력 예시:
# ⏭️ Skipping Helm app (no customization): myapp
# 또는
# 🔨 Building Helm app: myapp
```

### ❌ .Files.Get 파일을 찾을 수 없음

#### 증상

- Helm 템플릿에서 `{{ .Files.Get "files/config.toml" }}` 사용 시 빈 문자열 반환
- ConfigMap이나 Secret의 data가 비어있음
- 로그: `Error: template: ... error calling Get: file not found`

#### 원인

`files/` 디렉토리가 build/ 디렉토리에 복사되지 않음

#### 해결 방법

**1. files 디렉토리를 overrides에 추가**

```yaml
# overrides/myapp/templates/configmap.yaml
apiVersion: v1
kind: ConfigMap
metadata:
  name: my-config
data:
  config.toml: |-
{{ .Files.Get "files/config.toml" | indent 4 }}  # ← files/ 참조
```

```yaml
# config.yaml
apps:
  myapp:
    type: helm
    chart: my-chart
    overrides:
      - templates/configmap.yaml
      - files/config.toml          # ← 필수! files도 명시
```

**2. 디렉토리 구조 확인**

```
overrides/
  myapp/
    ├── templates/
    │   └── configmap.yaml
    └── files/
        └── config.toml       # ← 파일 존재 확인
```

**3. 빌드 후 검증**

```bash
sbkube build --app-dir .

# build 디렉토리 확인
ls -la build/myapp/files/config.toml

# 템플릿 렌더링 테스트
sbkube template --app-dir . --output-dir /tmp/rendered
cat /tmp/rendered/myapp/configmap.yaml
```

#### 참고

- `.Files.Get`의 경로는 **차트 루트 기준** 상대 경로입니다
- `files/` 디렉토리는 자동으로 복사되지 않으므로 명시적으로 override에 포함해야 합니다

### ❌ Override 파일을 찾을 수 없음

#### 증상

- 빌드 중 경고 메시지:
  ```
  ⚠️ Override file not found: overrides/myapp/templates/configmap.yaml
  ```

#### 원인

1. config.yaml에 명시된 파일이 실제로 존재하지 않음
1. 파일 경로가 잘못됨
1. 파일명 오타

#### 해결 방법

**1. 파일 존재 확인**

```bash
# config.yaml에 명시된 경로로 확인
ls -la overrides/myapp/templates/configmap.yaml
```

**2. 경로 확인**

```yaml
# ❌ 잘못된 경로 (절대 경로 또는 ../ 사용)
overrides:
  - /absolute/path/configmap.yaml          # 잘못됨
  - ../other-app/templates/configmap.yaml  # 잘못됨

# ✅ 올바른 경로 (overrides/[앱이름]/ 기준 상대 경로)
overrides:
  - templates/configmap.yaml               # 올바름
  - files/config.txt                       # 올바름
```

**3. 파일 생성 또는 경로 수정**

```bash
# 파일 생성
mkdir -p overrides/myapp/templates
cat > overrides/myapp/templates/configmap.yaml <<'EOF'
apiVersion: v1
kind: ConfigMap
metadata:
  name: my-config
data:
  key: value
EOF

# 또는 config.yaml 경로 수정
```

**4. 재빌드**

```bash
sbkube build --app-dir .
```

### 🔍 빌드 문제 진단 체크리스트

빌드 관련 문제 발생 시 다음 순서로 확인하세요:

**1. 디렉토리 구조 확인**

```bash
ls -la overrides/
ls -la overrides/[앱이름]/
ls -la build/
```

**2. config.yaml 검증**

```bash
cat config.yaml | grep -A 10 "앱이름:"
# overrides 필드가 있는지 확인
```

**3. 빌드 실행 (verbose 모드)**

```bash
sbkube build --app-dir . --verbose
```

**4. 빌드 결과 확인**

```bash
# Override된 파일이 build/에 있는지 확인
ls -la build/[앱이름]/templates/
ls -la build/[앱이름]/files/
```

**5. 템플릿 렌더링 테스트**

```bash
sbkube template --app-dir . --output-dir /tmp/test
cat /tmp/test/[앱이름]/*.yaml
```

### 📚 관련 문서

- [commands.md - Override 사용법](../02-features/commands.md#-override-%EB%94%94%EB%A0%89%ED%86%A0%EB%A6%AC-%EC%82%AC%EC%9A%A9-%EC%8B%9C-%EC%A3%BC%EC%9D%98%EC%82%AC%ED%95%AD)
- [config-schema.md - overrides 필드](../03-configuration/config-schema.md)
- [examples/override-with-files/](../../examples/override-with-files/) - 실전 예제

______________________________________________________________________

## 🪝 Hooks 관련 문제

### ❌ Hook 실행 실패

#### 증상

```
Error: Hook execution failed
Command: ./scripts/backup.sh
Exit code: 127
```

#### 원인

1. 스크립트 파일이 존재하지 않음
1. 실행 권한 없음
1. 환경 변수 미설정
1. Working directory 오류

#### 해결 방법

```bash
# 1. 파일 존재 확인
ls -la ./scripts/backup.sh

# 2. 실행 권한 부여
chmod +x ./scripts/backup.sh

# 3. 환경 변수 확인 (Hook 내에서)
hooks:
  post_deploy:
    - |
      echo "SBKUBE_APP_NAME: $SBKUBE_APP_NAME"
      echo "SBKUBE_NAMESPACE: $SBKUBE_NAMESPACE"
      env | grep SBKUBE

# 4. Working directory 명시
post_deploy_tasks:
  - type: command
    command: ["./backup.sh"]
    working_dir: "./scripts"
```

### ❌ Manifests Hook 실패: 파일을 찾을 수 없음

#### 증상

```
Error: Manifest file not found: manifests/cluster-issuer.yaml
```

#### 해결 방법

```bash
# 상대 경로 확인
ls manifests/cluster-issuer.yaml

# Phase 1 vs Phase 2 경로 차이 확인
# Phase 1: app_dir 기준
pre_deploy_manifests:
  - path: manifests/cluster-issuer.yaml

# Phase 2: working_dir 설정 가능
pre_deploy_tasks:
  - type: manifests
    paths: ["cluster-issuer.yaml"]
    working_dir: "./manifests"
```

### ❌ Task Validation 실패

#### 증상

```
Error: Validation failed for task 'create-certificate'
Resource certificate/my-cert not ready after 300s
```

#### 해결 방법

```yaml
# Timeout 연장
post_deploy_tasks:
  - type: manifests
    name: create-certificate
    paths: ["certificate.yaml"]
    validation:
      type: resource_ready
      resource: certificate/my-cert
      timeout: 600  # 10분으로 연장

# 또는 on_failure를 warn으로 변경
    on_failure: warn
```

### 🔍 Hooks 디버깅

```bash
# Verbose 모드로 실행
sbkube deploy --app-dir config --verbose

# Dry-run으로 Hook 명령어 확인
sbkube deploy --app-dir config --dry-run

# 특정 앱만 배포 (HookApp 포함)
sbkube deploy --app-dir config --app setup-issuers
```

### 📚 Hooks 관련 문서

- **[Hooks 레퍼런스](../02-features/hooks-reference.md)** - 전체 Hook 타입 및 환경 변수
- **[Hooks 상세 가이드](../02-features/hooks.md)** - 실전 예제 및 Best Practices
- **[Hooks 마이그레이션 가이드](../02-features/hooks-migration-guide.md)** - Phase 간 전환 방법
- **[예제: hooks-error-handling/](../../examples/hooks-error-handling/)** - 에러 처리 예제

______________________________________________________________________

## 📚 관련 문서

- **[일반적인 문제들](common-issues.md)** - 구체적인 해결 사례
- **[FAQ](faq.md)** - 자주 묻는 질문들
- **[디버깅 가이드](debugging.md)** - 심화 디버깅 방법
- **[설정 가이드](../03-configuration/)** - 올바른 설정 방법

______________________________________________________________________

*문제가 해결되지 않으시면 언제든지 [이슈 트래커](https://github.com/ScriptonBasestar/kube-app-manaer/issues)에 문의해 주세요. 가능한 한 빠르게 도움을
드리겠습니다!*
