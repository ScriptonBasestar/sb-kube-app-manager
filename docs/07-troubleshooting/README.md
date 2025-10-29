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
helm repo add bitnami https://charts.bitnami.com/bitnami
helm repo update

# 차트 존재 확인
helm search repo bitnami/nginx

# sources.yaml 설정 확인
cat sources.yaml
```

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

# 데이터베이스 재생성
sbkube state reset  # (향후 기능)
```

### 상태 정보 불일치

```bash
# 실제 클러스터와 상태 DB 동기화
sbkube state sync  # (향후 기능)

# 수동으로 상태 확인
kubectl get all -A
helm list -A
sbkube state list
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
Error: failed to fetch https://charts.bitnami.com/bitnami/index.yaml
```

**해결 방법:**

```bash
# 네트워크 연결 확인
curl -I https://charts.bitnami.com/bitnami/index.yaml

# 프록시 설정 (필요한 경우)
export HTTP_PROXY=http://proxy.company.com:8080
export HTTPS_PROXY=http://proxy.company.com:8080

# Helm 저장소 재추가
helm repo remove bitnami
helm repo add bitnami https://charts.bitnami.com/bitnami
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
    chart: bitnami/nginx
    # overrides 필드가 없음!
```

**2. overrides 필드 추가**

```yaml
# ✅ 올바른 설정
apps:
  myapp:
    type: helm
    chart: bitnami/nginx
    overrides:
      - templates/configmap.yaml
      - files/config.txt
```

**3. 빌드 재실행**

```bash
sbkube build --app-dir .

# 성공 메시지 확인:
# 🔨 Building Helm app: myapp
#   Copying chart: charts/nginx/nginx → build/myapp
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
  chart: bitnami/nginx  # 원격 차트는 항상 빌드됨
  version: "15.0.0"
```

**방법 3: 빌드 없이 배포** (로컬 차트 + 커스터마이징 없음)

```bash
# build 건너뛰고 바로 template/deploy
sbkube template --app-dir .
sbkube deploy --app-dir .
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

## 📚 관련 문서

- **[일반적인 문제들](common-issues.md)** - 구체적인 해결 사례
- **[FAQ](faq.md)** - 자주 묻는 질문들
- **[디버깅 가이드](debugging.md)** - 심화 디버깅 방법
- **[설정 가이드](../03-configuration/)** - 올바른 설정 방법

______________________________________________________________________

*문제가 해결되지 않으시면 언제든지 [이슈 트래커](https://github.com/ScriptonBasestar/kube-app-manaer/issues)에 문의해 주세요. 가능한 한 빠르게 도움을
드리겠습니다!*
