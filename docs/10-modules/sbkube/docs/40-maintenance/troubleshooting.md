# SBKube 모듈 트러블슈팅 가이드

## 일반적인 문제

### 1. 설정 파일 관련

#### Pydantic ValidationError
**증상**:
```
ValidationError: 2 validation errors for SBKubeConfig
apps.0.specs.repo
  field required (type=value_error.missing)
```

**원인**: config.yaml의 필수 필드 누락 또는 타입 불일치

**해결**:
1. 오류 메시지에서 필드 경로 확인 (`apps.0.specs.repo`)
2. 해당 앱 설정 검토
3. [config-schema.md](../../../../03-configuration/config-schema.md) 참조하여 수정

**예시**:
```yaml
# 잘못된 설정
apps:
  - name: redis
    type: pull-helm
    specs:
      chart: redis  # repo 필드 누락!

# 올바른 설정
apps:
  - name: redis
    type: pull-helm
    specs:
      repo: bitnami
      chart: redis
      version: "18.0.0"
```

#### YAML 파싱 오류
**증상**:
```
yaml.scanner.ScannerError: while scanning for the next token
found character '\t' that cannot start any token
```

**원인**: YAML 파일에 탭 문자 사용 (공백만 허용)

**해결**:
1. 에디터에서 탭을 공백으로 변환
2. YAML linter 사용 (yamllint)

### 2. 외부 도구 관련

#### kubectl not found
**증상**:
```
Error: kubectl not found in PATH
Please install kubectl first
```

**원인**: kubectl 미설치 또는 PATH 등록 안 됨

**해결**:
```bash
# macOS
brew install kubectl

# Linux
curl -LO "https://dl.k8s.io/release/$(curl -L -s https://dl.k8s.io/release/stable.txt)/bin/linux/amd64/kubectl"
chmod +x kubectl
sudo mv kubectl /usr/local/bin/

# 설치 확인
kubectl version --client
```

#### Helm not found
**증상**:
```
Error: helm not found in PATH
```

**해결**:
```bash
# macOS
brew install helm

# Linux
curl https://raw.githubusercontent.com/helm/helm/main/scripts/get-helm-3 | bash

# 설치 확인
helm version
```

#### Git not found
**증상**:
```
Error: git not found in PATH
Required for 'pull-git' app types
```

**해결**:
```bash
# macOS
brew install git

# Linux
sudo apt-get install git  # Debian/Ubuntu
sudo yum install git      # RHEL/CentOS

# 설치 확인
git --version
```

### 3. Kubernetes 클러스터 관련

#### kubeconfig 파일 없음
**증상**:
```
Error: Kubernetes config file not found
Checked: /home/user/.kube/config
```

**원인**: kubeconfig 파일 경로 잘못됨

**해결**:
```bash
# kubeconfig 파일 확인
ls -la ~/.kube/config

# 다른 경로 사용 시
sbkube deploy --kubeconfig /path/to/kubeconfig
```

#### 클러스터 접근 불가
**증상**:
```
Error: Unable to connect to the server: dial tcp: lookup kubernetes.default.svc: no such host
```

**원인**: 클러스터 실행 중이지 않거나 네트워크 문제

**해결**:
```bash
# 클러스터 상태 확인
kubectl cluster-info

# k3s 재시작 (로컬 환경)
sudo systemctl restart k3s

# 컨텍스트 확인
kubectl config get-contexts
kubectl config use-context <context-name>
```

#### 네임스페이스 없음
**증상**:
```
Error: namespace "my-app" not found
```

**해결**:
```bash
# 네임스페이스 생성
kubectl create namespace my-app

# 또는 config.yaml에 추가하여 자동 생성 (향후 지원)
```

#### RBAC 권한 부족
**증상**:
```
Error: User "default" cannot create resource "deployments" in API group "apps"
```

**원인**: 현재 사용자에게 리소스 생성 권한 없음

**해결**:
```bash
# 권한 확인
kubectl auth can-i create deployments --namespace my-app

# ClusterRole/RoleBinding 생성 (관리자 권한 필요)
kubectl create rolebinding my-binding \
  --clusterrole=edit \
  --user=<사용자명> \
  --namespace=my-app
```

### 4. Helm 관련

#### Helm 저장소 추가 실패
**증상**:
```
Error: Failed to add Helm repo 'bitnami'
```

**원인**: 네트워크 문제 또는 잘못된 URL

**해결**:
```bash
# 수동으로 저장소 추가 테스트
helm repo add bitnami https://charts.bitnami.com/bitnami

# sources.yaml 확인
helm_repos:
  - name: bitnami
    url: https://charts.bitnami.com/bitnami  # URL 정확한지 확인
```

#### Helm 차트 다운로드 실패
**증상**:
```
Error: Chart "redis" version "18.0.0" not found in bitnami repo
```

**원인**: 차트 버전 존재하지 않음

**해결**:
```bash
# 사용 가능한 버전 확인
helm search repo bitnami/redis --versions

# config.yaml에서 올바른 버전 지정
specs:
  version: "19.0.0"  # 존재하는 버전으로 수정
```

#### Helm 릴리스 설치 실패
**증상**:
```
Error: INSTALLATION FAILED: rendered manifests contain a resource that already exists
```

**원인**: 동일한 릴리스 이름이 이미 존재

**해결**:
```bash
# 기존 릴리스 확인
helm list --namespace my-app

# 기존 릴리스 삭제 (주의!)
helm uninstall my-redis --namespace my-app

# 또는 다른 릴리스 이름 사용
release_name: my-redis-v2
```

### 5. Git 관련

#### Git 리포지토리 클론 실패
**증상**:
```
Error: Failed to clone repository 'https://github.com/example/repo.git'
```

**원인**: 네트워크 문제, 권한 부족, 잘못된 URL

**해결**:
```bash
# 수동으로 클론 테스트
git clone https://github.com/example/repo.git

# Private 리포지토리는 인증 필요
git clone https://<TOKEN>@github.com/example/repo.git

# SSH 사용
git clone git@github.com:example/repo.git
```

#### Git ref(브랜치/태그) 없음
**증상**:
```
Error: Reference 'v1.2.3' not found in repository
```

**해결**:
```bash
# 리포지토리 확인
git ls-remote https://github.com/example/repo.git

# sources.yaml에서 올바른 ref 지정
git_repos:
  - name: my-repo
    url: https://github.com/example/repo.git
    ref: main  # 또는 존재하는 브랜치/태그
```

### 6. 배포 상태 관련

#### 상태 DB 손상
**증상**:
```
Error: database disk image is malformed
```

**원인**: SQLite 데이터베이스 파일 손상

**해결**:
```bash
# 백업 후 DB 파일 삭제 (주의: 히스토리 손실!)
mv ~/.sbkube/state.db ~/.sbkube/state.db.bak

# SBKube 재실행하면 새 DB 생성됨
sbkube state list
```

#### 롤백 실패
**증상**:
```
Error: Deployment ID not found: 12345
```

**원인**: 잘못된 배포 ID

**해결**:
```bash
# 히스토리에서 올바른 ID 확인
sbkube state history --namespace my-app

# 올바른 ID로 롤백
sbkube state rollback --deployment-id <정확한-ID>
```

## 디버깅 팁

### 1. Verbose 모드 사용
```bash
sbkube deploy --verbose

# 출력 예시:
# [DEBUG] Loading config from /path/to/config.yaml
# [DEBUG] Validating app: redis (type: pull-helm)
# [DEBUG] Executing helm install my-redis charts/redis
```

### 2. Dry-run 모드로 사전 검증
```bash
sbkube deploy --dry-run

# 실제 배포 없이 시뮬레이션
# 오류를 사전에 발견 가능
```

### 3. 설정 검증
```bash
sbkube validate --app-dir config

# config.yaml, sources.yaml 검증
# Pydantic 오류 사전 확인
```

### 4. 로그 파일 확인
```bash
# SBKube 로그 (향후 구현)
tail -f ~/.sbkube/logs/sbkube.log
```

### 5. Kubernetes 리소스 직접 확인
```bash
# Pod 상태
kubectl get pods -n my-app

# Deployment 상태
kubectl get deployments -n my-app

# 이벤트 확인
kubectl get events -n my-app --sort-by='.lastTimestamp'

# Pod 로그
kubectl logs <pod-name> -n my-app
```

## 성능 문제

### 1. 느린 Helm 차트 다운로드
**원인**: 네트워크 속도 또는 차트 크기

**해결**:
- 로컬 캐시 활용 (`charts/` 디렉토리 보존)
- 미러 저장소 사용 (sources.yaml에서 URL 변경)
- 병렬 다운로드 (향후 구현)

### 2. 템플릿 렌더링 느림
**원인**: 대규모 Helm 차트 또는 많은 values 파일

**해결**:
- values 파일 최소화
- 불필요한 리소스 제거
- 차트 업스트림에 성능 개선 요청

## 알려진 제한사항

### 1. 동시 배포 미지원
**현재**: 동시에 여러 sbkube 프로세스 실행 시 상태 충돌 가능

**해결** (향후): 분산 잠금 구현 예정 (v0.4.x)

### 2. 대규모 앱 수 처리
**현재**: 100+ 앱 처리 시 성능 저하 가능

**해결** (향후): 병렬 처리 구현 예정 (v0.3.x)

### 3. 멀티 클러스터 미지원
**현재**: 단일 클러스터만 대상

**해결** (향후): 멀티 클러스터 지원 예정 (v0.4.x)

## 문제 보고

### GitHub Issues
문제 발생 시 다음 정보와 함께 이슈 등록:
- SBKube 버전 (`sbkube version`)
- OS 및 Python 버전
- 오류 메시지 전문
- 재현 가능한 최소 config.yaml

### 이슈 템플릿
```markdown
**SBKube 버전**: v0.2.1
**OS**: Ubuntu 22.04
**Python**: 3.12.1
**Helm**: v3.13.0
**kubectl**: v1.28.0

**문제**:
[문제 설명]

**재현 방법**:
1. [단계 1]
2. [단계 2]

**오류 메시지**:
```
[오류 전문]
```

**config.yaml**:
```yaml
[최소한의 설정 파일]
```
```

---

**문서 버전**: 1.0
**마지막 업데이트**: 2025-10-20
**관련 문서**:
- [../../MODULE.md](../../MODULE.md) - 모듈 정의
- [../../ARCHITECTURE.md](../../ARCHITECTURE.md) - 아키텍처
- [../../../07-troubleshooting/README.md](../../../07-troubleshooting/README.md) - 사용자용 트러블슈팅
