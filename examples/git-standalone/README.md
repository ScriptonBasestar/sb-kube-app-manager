# Git Standalone - Git 리포지토리 기반 배포

SBKube의 **git 타입**을 사용하여 Git 리포지토리에서 Helm 차트를 배포하는 예제입니다.

## 📋 목차

- [개요](#-개요)
- [git 타입이란?](#-git-타입이란)
- [설정 구조](#-설정-구조)
- [배포 방법](#-배포-방법)
- [Git 인증](#-git-인증)
- [고급 사용법](#-고급-사용법)
- [제한사항](#-제한사항)

---

## 🎯 개요

이 예제는 **Strimzi Kafka Operator**를 Git 리포지토리에서 직접 배포하는 방법을 보여줍니다.

**배포 애플리케이션**:
- **Strimzi Operator**: Kubernetes용 Kafka Operator
- **소스**: GitHub 리포지토리 (`strimzi/strimzi-kafka-operator`)
- **브랜치**: `release-0.44.x`

---

## 🔧 git 타입이란?

**git 타입**은 Git 리포지토리 내의 Helm 차트를 직접 배포하는 애플리케이션 타입입니다.

### 특징

| 특징 | 설명 |
|-----|------|
| **소스** | Git 리포지토리 (GitHub, GitLab, Bitbucket 등) |
| **차트 위치** | 리포지토리 내 특정 경로 (`path`) |
| **버전 관리** | Git 브랜치 또는 태그 |
| **로컬 수정** | 클론 후 자유롭게 수정 가능 |

### vs Helm 타입

| 비교 항목 | git 타입 | helm 타입 |
|---------|----------|----------|
| **소스** | Git 리포지토리 | Helm 리포지토리 |
| **차트 위치** | 리포지토리 내 경로 | 차트 이름 (repo/chart) |
| **버전** | Git 브랜치/태그 | Helm 차트 버전 |
| **로컬 수정** | ✅ 쉬움 (클론 후 수정) | ❌ 어려움 (패키지) |
| **다중 차트** | ⚠️ 제한적 (하나의 path만) | ✅ 자유롭게 |
| **용도** | 개발 중 차트, Git 기반 프로젝트 | 안정적 릴리스 차트 |

---

## 📝 설정 구조

### config.yaml

```yaml
namespace: git-demo

apps:
  strimzi-operator:
    type: git                     # Git 타입
    repo: strimzi                 # sources.yaml의 git_repos 키
    path: install/cluster-operator # 리포지토리 내 Helm 차트 경로
```

**주요 필드**:
- `type`: `git` 고정
- `repo`: `sources.yaml`의 `git_repos`에 정의된 키
- `path`: Git 리포지토리 내 Helm 차트가 있는 경로

### sources.yaml

```yaml
cluster: git-demo-cluster
kubeconfig: ~/.kube/config

git_repos:
  strimzi:
    url: "https://github.com/strimzi/strimzi-kafka-operator.git"
    branch: "release-0.44.x"
```

**주요 필드**:
- `url`: Git 리포지토리 URL (HTTPS 또는 SSH)
- `branch`: 브랜치 또는 태그 이름

---

## 🚀 배포 방법

### 기본 배포

```bash
cd examples/git-standalone

# 통합 배포 (prepare → build → deploy)
sbkube apply
```

**실행 과정**:
```
✅ [prepare] Git 리포지토리 클론
    git clone https://github.com/strimzi/strimzi-kafka-operator.git repos/strimzi
    cd repos/strimzi && git checkout release-0.44.x

✅ [build] Helm 차트 빌드
    cp -r repos/strimzi/install/cluster-operator build/strimzi-operator/

✅ [deploy] Kubernetes 클러스터 배포
    helm upgrade --install strimzi-operator build/strimzi-operator/ -n git-demo
```

### 단계별 배포

```bash
# 1. Git 리포지토리 클론
sbkube prepare

# 결과 확인
ls repos/strimzi/install/cluster-operator/

# 2. Helm 차트 빌드
sbkube build

# 결과 확인
ls build/strimzi-operator/

# 3. 배포
sbkube deploy --namespace git-demo
```

---

## 🔍 배포 확인

### Helm 릴리스 확인

```bash
helm list -n git-demo
```

**예상 출력**:
```
NAME               NAMESPACE  REVISION  STATUS    CHART
strimzi-operator   git-demo   1         deployed  strimzi-cluster-operator-0.44.0
```

### Pod 상태 확인

```bash
kubectl get pods -n git-demo
```

**예상 출력**:
```
NAME                                        READY   STATUS    RESTARTS   AGE
strimzi-cluster-operator-xxxx-yyyy          1/1     Running   0          2m
```

### CRD 확인

Strimzi는 여러 CRD를 설치합니다:

```bash
kubectl get crd | grep strimzi
```

**예상 출력**:
```
kafkas.kafka.strimzi.io              2025-10-24T10:00:00Z
kafkatopics.kafka.strimzi.io         2025-10-24T10:00:00Z
kafkausers.kafka.strimzi.io          2025-10-24T10:00:00Z
kafkaconnects.kafka.strimzi.io       2025-10-24T10:00:00Z
...
```

---

## 🔐 Git 인증

### Public 리포지토리 (인증 불필요)

```yaml
# sources.yaml
git_repos:
  strimzi:
    url: "https://github.com/strimzi/strimzi-kafka-operator.git"
    branch: "release-0.44.x"
```

### Private 리포지토리 (인증 필요)

#### 방법 1: SSH 키 사용

```yaml
# sources.yaml
git_repos:
  my-private-repo:
    url: "git@github.com:myorg/my-private-repo.git"
    branch: "main"
```

**사전 작업**:
```bash
# SSH 키 생성
ssh-keygen -t ed25519 -C "your@email.com"

# GitHub에 공개키 등록
cat ~/.ssh/id_ed25519.pub

# SSH 에이전트에 키 추가
eval "$(ssh-agent -s)"
ssh-add ~/.ssh/id_ed25519
```

#### 방법 2: Personal Access Token (HTTPS)

```yaml
# sources.yaml
git_repos:
  my-private-repo:
    url: "https://<USERNAME>:<TOKEN>@github.com/myorg/my-private-repo.git"
    branch: "main"
```

**⚠️ 주의**: Token을 sources.yaml에 직접 포함하지 말고 환경변수 사용 권장

**환경변수 사용**:
```bash
export GIT_TOKEN="ghp_xxxxxxxxxxxx"
```

```yaml
# sources.yaml (템플릿)
git_repos:
  my-private-repo:
    url: "https://${GIT_TOKEN}@github.com/myorg/my-private-repo.git"
    branch: "main"
```

---

## 🛠️ 고급 사용법

### 1. 특정 태그 사용

```yaml
git_repos:
  strimzi:
    url: "https://github.com/strimzi/strimzi-kafka-operator.git"
    branch: "0.44.0"  # 태그 이름
```

### 2. 특정 커밋 사용

```yaml
git_repos:
  strimzi:
    url: "https://github.com/strimzi/strimzi-kafka-operator.git"
    branch: "abc123def456"  # 커밋 해시
```

### 3. 다중 차트 배포 (수동 방식)

**제한**: SBKube git 타입은 하나의 `path`만 지원

**해결**: 수동 클론 후 Helm 타입 사용

#### Step 1: 수동 클론

```bash
git clone https://github.com/strimzi/strimzi-kafka-operator.git repos/strimzi
cd repos/strimzi
git checkout release-0.44.x
```

#### Step 2: config.yaml 수정

```yaml
namespace: git-demo

apps:
  # Git 타입 대신 Helm 타입으로 로컬 차트 사용
  strimzi-cluster-operator:
    type: helm
    chart: ./repos/strimzi/install/cluster-operator

  strimzi-topic-operator:
    type: helm
    chart: ./repos/strimzi/install/topic-operator
    depends_on:
      - strimzi-cluster-operator

  strimzi-user-operator:
    type: helm
    chart: ./repos/strimzi/install/user-operator
    depends_on:
      - strimzi-cluster-operator
```

#### Step 3: 배포

```bash
sbkube apply
```

### 4. 로컬 수정 후 배포

**시나리오**: Git 리포지토리의 차트를 수정하여 배포

```bash
# 1. 리포지토리 클론
sbkube prepare

# 2. 차트 수정
vi repos/strimzi/install/cluster-operator/values.yaml

# 3. 재빌드 및 배포
sbkube build --force  # 수정사항 반영
sbkube deploy
```

### 5. Submodule 포함 리포지토리

```bash
# prepare 단계에서 자동으로 submodule 초기화
sbkube prepare
# → git clone --recursive 실행
```

---

## ⚠️ 제한사항

### 1. 단일 경로만 지원

**제한**: 하나의 앱 당 하나의 `path`만 지원

```yaml
# ❌ 지원 안 됨
apps:
  strimzi:
    type: git
    repo: strimzi
    paths:  # 복수형 불가
      - install/cluster-operator
      - install/topic-operator
```

**해결**: 별도 앱으로 분리 또는 수동 클론 후 Helm 타입 사용 (위 고급 사용법 참조)

### 2. Git 인증 필요 시 복잡성

**Private 리포지토리**:
- SSH 키 설정 필요
- Personal Access Token 관리 필요
- 환경변수 설정 권장

### 3. 네트워크 대역폭

**초기 클론**:
- 리포지토리 크기에 따라 시간 소요 (수십 MB ~ 수백 MB)
- `--force` 사용 시 재클론으로 대역폭 소모

**권장**:
- CI/CD에서는 Git 캐시 활용
- 대용량 리포지토리는 shallow clone 고려

### 4. 브랜치 업데이트 반영

**문제**: Git 리포지토리가 업데이트되어도 로컬은 오래된 버전

```bash
sbkube prepare
# → "Repository already exists, skipping clone"
```

**해결**:
```bash
sbkube prepare --force
# → 재클론하여 최신 버전 가져오기

# 또는 수동 pull
cd repos/strimzi
git pull origin release-0.44.x
cd ../..
sbkube build --force
sbkube deploy
```

---

## 💡 실전 예제

### 예제 1: Prometheus Operator (Git)

```yaml
# sources.yaml
git_repos:
  prometheus-operator:
    url: "https://github.com/prometheus-operator/prometheus-operator.git"
    branch: "main"

# config.yaml
apps:
  prometheus-operator:
    type: git
    repo: prometheus-operator
    path: charts/kube-prometheus-stack
```

### 예제 2: Istio (Git)

```yaml
# sources.yaml
git_repos:
  istio:
    url: "https://github.com/istio/istio.git"
    branch: "1.20.0"

# config.yaml
apps:
  istio-base:
    type: git
    repo: istio
    path: manifests/charts/base

  istio-discovery:
    type: git
    repo: istio
    path: manifests/charts/istio-control/istio-discovery
    depends_on:
      - istio-base
```

---

## 🔄 업데이트 및 삭제

### 브랜치 변경 후 재배포

```bash
# 1. sources.yaml 수정
# branch: "release-0.44.x" → "release-0.45.x"

# 2. 강제 재클론 및 재배포
sbkube apply --force
```

### 삭제

```bash
# Helm 릴리스 삭제
sbkube delete --namespace git-demo

# Git 리포지토리 정리 (선택적)
rm -rf repos/strimzi
```

---

## 📚 참고 자료

- [SBKube 애플리케이션 타입 가이드](../../docs/02-features/application-types.md)
- [k3scode/ai/ 예제](../k3scode/ai/) - Toolhive Operator (Git 타입)
- [Strimzi 공식 문서](https://strimzi.io/)

---

## 🔗 관련 예제

- [k3scode/ai/](../k3scode/ai/) - Toolhive Operator (Git 타입)
- [basic/local-chart/](../basic/local-chart/) - 로컬 Helm 차트 사용

---

**💡 팁**: Git 타입은 공식 Helm 차트가 없거나 개발 중인 프로젝트에 유용합니다. 로컬에서 차트를 수정할 수 있어 유연성이 높습니다.
