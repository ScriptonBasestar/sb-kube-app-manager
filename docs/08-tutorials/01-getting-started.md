# 🚀 시작하기 - SBKube 첫 번째 배포

> **난이도**: ⭐ 초급 **소요 시간**: 10-15분 **사전 요구사항**: Kubernetes 클러스터 (Kind/Minikube/K3s), Helm v3

---

## 📋 목차

1. [튜토리얼 목표](#%ED%8A%9C%ED%86%A0%EB%A6%AC%EC%96%BC-%EB%AA%A9%ED%91%9C)
1. [환경 준비](#%ED%99%98%EA%B2%BD-%EC%A4%80%EB%B9%84)
1. [Step 1: 프로젝트 초기화](#step-1-%ED%94%84%EB%A1%9C%EC%A0%9D%ED%8A%B8-%EC%B4%88%EA%B8%B0%ED%99%94)
1. [Step 2: 첫 번째 배포](#step-2-%EC%B2%AB-%EB%B2%88%EC%A7%B8-%EB%B0%B0%ED%8F%AC)
1. [Step 3: 배포 확인](#step-3-%EB%B0%B0%ED%8F%AC-%ED%99%95%EC%9D%B8)
1. [Step 4: 업그레이드 및 삭제](#step-4-%EC%97%85%EA%B7%B8%EB%A0%88%EC%9D%B4%EB%93%9C-%EB%B0%8F-%EC%82%AD%EC%A0%9C)
1. [다음 단계](#%EB%8B%A4%EC%9D%8C-%EB%8B%A8%EA%B3%84)

---

## 튜토리얼 목표

이 튜토리얼을 완료하면 다음을 할 수 있습니다:

- ✅ SBKube 프로젝트를 초기화하고 설정 파일 작성
- ✅ Helm 차트를 사용한 첫 번째 애플리케이션 배포
- ✅ 배포 상태 확인 및 히스토리 조회
- ✅ 애플리케이션 업그레이드 및 삭제

---

## 환경 준비

### 1. Kubernetes 클러스터 준비

**Kind 사용 (권장)**:

```bash
# Kind 클러스터 생성
kind create cluster --name sbkube-tutorial

# 클러스터 확인
kubectl cluster-info
kubectl get nodes
```

**또는 Minikube**:

```bash
minikube start --profile sbkube-tutorial
kubectl config use-context sbkube-tutorial
```

### 2. SBKube 설치

```bash
# pip로 설치
pip install sbkube

# 또는 uv로 설치 (권장)
uv tool install sbkube

# 설치 확인
sbkube --version
# 출력: sbkube, version 0.4.7
```

### 3. 필수 도구 확인

```bash
# Helm 확인
helm version
# 출력: version.BuildInfo{Version:"v3.x.x", ...}

# kubectl 확인
kubectl version --client
```

---

## Step 1: 프로젝트 초기화

### 1.1 작업 디렉토리 생성

```bash
mkdir my-first-sbkube-project
cd my-first-sbkube-project
```

### 1.2 SBKube 프로젝트 초기화

```bash
# 대화형 초기화
sbkube init

# 또는 비대화형 초기화
sbkube init --name my-app --template basic --non-interactive
```

**생성된 파일 구조**:

```
my-first-sbkube-project/
├── config.yaml       # 애플리케이션 설정
└── sources.yaml      # Helm 저장소 및 Git 소스 설정
```

### 1.3 설정 파일 작성

**`config.yaml`**:

```yaml
namespace: tutorial-demo

apps:
  redis:
    type: helm
    chart: bitnami/redis
    version: 19.0.0
    enabled: true
    values:
      - redis-values.yaml
```

**`sources.yaml`**:

```yaml
# 클러스터 설정 (필수, v0.4.10+)
kubeconfig: ~/.kube/config
kubeconfig_context: kind-sbkube-tutorial
cluster: sbkube-tutorial  # 선택, 문서화 목적

# Helm 리포지토리
helm_repos:
  bitnami:
    url: https://charts.bitnami.com/bitnami
```

**`redis-values.yaml`** (Redis 설정):

```yaml
architecture: standalone
auth:
  enabled: false
master:
  resources:
    requests:
      cpu: 100m
      memory: 128Mi
    limits:
      cpu: 200m
      memory: 256Mi
```

---

## Step 2: 첫 번째 배포

### 2.1 설정 검증

```bash
# 설정 파일 유효성 검사
sbkube validate

# 예상 출력:
# ✅ Config file validation passed
# ✅ All required fields present
# ✅ No validation errors found
```

### 2.2 통합 배포 (apply)

```bash
# 전체 워크플로우 실행
sbkube apply

# 또는 dry-run으로 미리 확인
sbkube apply --dry-run
```

**실행 과정**:

```
✨ SBKube `apply` 시작 ✨
📄 Loading config: /path/to/config.yaml
📄 Using sources file: /path/to/sources.yaml

🔧 Step 1: Prepare
📦 Preparing Helm app: redis
  Adding Helm repo: bitnami (https://charts.bitnami.com/bitnami)
  Updating Helm repo: bitnami
  Pulling chart: bitnami/redis → charts/redis
✅ Helm app prepared: redis

🔨 Step 2: Build
⏭️  Skipping build (no overrides/removes)

🚀 Step 3: Deploy
📦 Deploying Helm app: redis
  Installing Helm release: redis-tutorial-demo
  Namespace: tutorial-demo
✅ Helm app deployed: redis

✅ Apply completed: 1/1 apps
```

### 2.3 단계별 실행 (선택 사항)

apply 대신 각 단계를 수동으로 실행할 수도 있습니다:

```bash
# Step 1: 소스 준비
sbkube prepare
# 📦 Helm chart pull

# Step 2: 빌드 (overrides 있는 경우만)
sbkube build
# 🔨 차트 커스터마이징

# Step 3: 배포
sbkube deploy
# 🚀 Kubernetes에 배포
```

---

## Step 3: 배포 확인

### 3.1 Kubernetes 리소스 확인

```bash
# Pod 상태 확인
kubectl get pods -n tutorial-demo

# 예상 출력:
# NAME                     READY   STATUS    RESTARTS   AGE
# redis-master-0           1/1     Running   0          2m

# Service 확인
kubectl get svc -n tutorial-demo

# Helm 릴리스 확인
helm list -n tutorial-demo
```

### 3.2 SBKube 상태 확인

```bash
# 배포 상태 조회
sbkube state list

# 예상 출력:
# App Name    Type    Status      Release Name              Namespace
# redis       helm    deployed    redis-tutorial-demo       tutorial-demo

# 배포 히스토리 확인
sbkube state history --namespace tutorial-demo

# 예상 출력:
# Deployment History for namespace: tutorial-demo
#
# ID  App     Version  Status    Deployed At              Duration
# 1   redis   19.0.0   success   2025-10-24 10:30:45      45s
```

### 3.3 Redis 연결 테스트

```bash
# Redis 포트 포워딩
kubectl port-forward -n tutorial-demo svc/redis-master 6379:6379 &

# Redis CLI로 연결 테스트
redis-cli ping
# 출력: PONG

# 포트 포워딩 종료
pkill -f "port-forward.*redis"
```

---

## Step 4: 업그레이드 및 삭제

### 4.1 애플리케이션 업그레이드

**`redis-values.yaml` 수정**:

```yaml
architecture: standalone
auth:
  enabled: false
master:
  resources:
    requests:
      cpu: 150m  # 100m → 150m으로 증가
      memory: 256Mi  # 128Mi → 256Mi로 증가
```

**업그레이드 실행**:

```bash
# 변경사항 적용
sbkube apply

# 또는 upgrade 명령어 사용
sbkube upgrade --namespace tutorial-demo

# Pod 재시작 확인
kubectl get pods -n tutorial-demo -w
```

### 4.2 배포 히스토리 및 롤백

```bash
# 히스토리 확인
sbkube state history --namespace tutorial-demo

# 예상 출력:
# ID  App     Version  Status    Deployed At
# 2   redis   19.0.0   success   2025-10-24 10:35:20  (업그레이드)
# 1   redis   19.0.0   success   2025-10-24 10:30:45  (최초 배포)

# 이전 버전으로 롤백 (필요시)
sbkube rollback --revision 1 --namespace tutorial-demo
```

### 4.3 애플리케이션 삭제

```bash
# Dry-run으로 삭제 확인
sbkube delete --dry-run

# 예상 출력:
# [DRY-RUN] Would delete Helm release: redis-tutorial-demo (namespace: tutorial-demo)

# 실제 삭제
sbkube delete

# 확인
kubectl get all -n tutorial-demo
# 출력: No resources found in tutorial-demo namespace.

# 네임스페이스도 삭제 (선택 사항)
kubectl delete namespace tutorial-demo
```

---

## 다음 단계

축하합니다! 🎉 SBKube를 사용한 첫 번째 배포를 성공적으로 완료했습니다.

### 추천 튜토리얼

1. **[02-multi-app-deployment.md](02-multi-app-deployment.md)** - 여러 앱 동시 배포
1. **[03-production-deployment.md](03-production-deployment.md)** - 프로덕션 배포 Best Practice
1. **[04-customization.md](04-customization.md)** - 차트 커스터마이징 (overrides/removes)

### 추가 학습 자료

- [명령어 참조](../../docs/02-features/commands.md)
- [설정 스키마](../../docs/03-configuration/config-schema.md)
- [예제 모음](../)

### 트러블슈팅

**문제**: Helm 리포지토리 추가 실패 **해결**: `helm repo add bitnami https://charts.bitnami.com/bitnami` 수동 실행

**문제**: Pod가 Running 상태가 되지 않음 **해결**: `kubectl describe pod -n tutorial-demo <pod-name>` 로 이벤트 확인

**문제**: sbkube apply 실패 **해결**: `sbkube doctor` 명령어로 시스템 진단

---

**작성자**: SBKube Documentation Team **버전**: v0.4.10 **최종 업데이트**: 2025-10-30
