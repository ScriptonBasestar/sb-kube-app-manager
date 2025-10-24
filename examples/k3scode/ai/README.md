# AI - AI/ML 인프라 배포

Toolhive Operator를 SBKube로 배포하는 예제입니다.

## 📋 목차

- [개요](#-개요)
- [Toolhive란?](#-toolhive란)
- [설정 상세](#-설정-상세)
- [배포 방법](#-배포-방법)
- [사용 예제](#-사용-예제)
- [고급 사용법](#-고급-사용법)

---

## 🎯 개요

이 예제는 k3scode 프로젝트의 **AI/ML 인프라 레이어**로, 다음 애플리케이션을 배포합니다:

| 애플리케이션 | 타입 | 소스 | 용도 |
|------------|------|------|------|
| **Toolhive Operator** | git | stacklok-toolhive | AI/ML 도구 자동화 플랫폼 Operator |

**네임스페이스**: `toolhive`

---

## 🤖 Toolhive란?

**Toolhive**는 Stacklok에서 개발한 Kubernetes 기반 AI/ML 도구 자동화 플랫폼입니다.

### 주요 기능

- **Kubernetes Operator**: CRD 기반 선언적 AI/ML 도구 관리
- **도구 자동화**: AI/ML 워크플로우 자동화
- **통합 플랫폼**: 다양한 AI/ML 도구 통합 관리

### 아키텍처

```
Toolhive Operator (이 예제)
  ├─ CRD 정의
  ├─ Operator Controller
  └─ Webhook
```

---

## ⚙️ 설정 상세

### config.yaml

```yaml
namespace: toolhive

apps:
  toolhive-operator:
    type: git                              # Git 리포지토리 타입
    repo: stacklok-toolhive                # sources.yaml의 git_repos 키
    path: deploy/charts/operator           # 리포지토리 내 Helm 차트 경로
```

**중요 포인트**:
- **타입**: `git` (Git 리포지토리에서 Helm 차트 사용)
- **단일 경로**: SBKube git 타입은 하나의 `path`만 지원
- **다중 경로**: 별도 앱으로 분리 또는 수동 복사 필요

### 공통 소스 (../sources.yaml)

```yaml
git_repos:
  stacklok-toolhive:
    url: "https://github.com/stacklok/toolhive.git"
    branch: "main"
```

### 다중 차트 배포 (주석 처리된 예제)

원래 Toolhive는 두 개의 차트를 사용합니다:

```yaml
# 방법 1: Git 타입으로 분리 (현재는 주석 처리)
# toolhive-operator-chart:
#   type: helm
#   chart: ./repos/stacklok-toolhive/deploy/charts/operator
#   values:
#     - toolhive-operator.yaml

# toolhive-operator-crds:
#   type: helm
#   chart: ./repos/stacklok-toolhive/deploy/charts/operator-crds
#   values:
#     - toolhive-operator-crds.yaml
```

**설명**:
- CRD 차트와 Operator 차트를 분리하여 관리
- `./repos/stacklok-toolhive/`: Git 리포지토리가 클론될 로컬 경로
- 수동 복사 후 Helm 타입으로 배포 가능

---

## 🚀 배포 방법

### 전체 배포

```bash
cd examples/k3scode

# 통합 배포
sbkube apply --base-dir . --app-dir ai
```

**실행 과정**:
1. Git 리포지토리 클론 (prepare)
   ```bash
   git clone https://github.com/stacklok/toolhive.git repos/stacklok-toolhive
   ```
2. Helm 차트 의존성 빌드 (build)
   ```bash
   helm dependency build repos/stacklok-toolhive/deploy/charts/operator
   ```
3. 템플릿 렌더링 (template)
4. `toolhive` 네임스페이스에 배포 (deploy)

### 단계별 배포

```bash
# 1. Git 리포지토리 클론
sbkube prepare --base-dir . --app-dir ai

# 확인
ls repos/stacklok-toolhive/

# 2. Helm 차트 빌드
sbkube build --base-dir . --app-dir ai

# 3. 템플릿 렌더링
sbkube template --base-dir . --app-dir ai --output-dir /tmp/toolhive

# 4. 배포
sbkube deploy --base-dir . --app-dir ai --namespace toolhive
```

---

## 🔍 배포 확인

### Helm 릴리스 확인

```bash
helm list -n toolhive
```

**예상 출력**:
```
NAME               NAMESPACE  REVISION  STATUS    CHART                    APP VERSION
toolhive-operator  toolhive   1         deployed  toolhive-operator-1.0.0  1.0.0
```

### Pod 상태 확인

```bash
kubectl get pods -n toolhive
```

**예상 출력**:
```
NAME                                  READY   STATUS    RESTARTS   AGE
toolhive-operator-xxxx-yyyy           1/1     Running   0          2m
```

### CRD 확인

```bash
kubectl get crd | grep toolhive
```

**예상 출력** (예시):
```
toolconfigs.toolhive.io        2025-10-24T10:00:00Z
toolruns.toolhive.io           2025-10-24T10:00:00Z
```

### Service 확인

```bash
kubectl get svc -n toolhive
```

### Deployment 확인

```bash
kubectl get deployment -n toolhive
kubectl describe deployment toolhive-operator -n toolhive
```

---

## 💻 사용 예제

### Custom Resource 생성

Toolhive Operator가 배포되면 CRD를 사용하여 AI/ML 도구를 관리할 수 있습니다.

#### 예제: ToolConfig 생성

```yaml
# toolconfig-example.yaml
apiVersion: toolhive.io/v1alpha1
kind: ToolConfig
metadata:
  name: my-ml-tool
  namespace: toolhive
spec:
  toolType: jupyter
  resources:
    cpu: 2
    memory: 4Gi
  storage:
    size: 10Gi
```

```bash
kubectl apply -f toolconfig-example.yaml
kubectl get toolconfigs -n toolhive
```

#### 예제: ToolRun 실행

```yaml
# toolrun-example.yaml
apiVersion: toolhive.io/v1alpha1
kind: ToolRun
metadata:
  name: training-job-001
  namespace: toolhive
spec:
  toolConfigRef: my-ml-tool
  command: ["python", "train.py"]
  args: ["--epochs=100"]
```

```bash
kubectl apply -f toolrun-example.yaml
kubectl get toolruns -n toolhive
kubectl logs -n toolhive -l toolrun=training-job-001
```

---

## 🛠️ 고급 사용법

### 1. 다중 차트 배포 (수동 방식)

#### Step 1: Git 리포지토리 클론

```bash
# 수동 클론
git clone https://github.com/stacklok/toolhive.git repos/stacklok-toolhive

# 차트 확인
ls repos/stacklok-toolhive/deploy/charts/
# operator/
# operator-crds/
```

#### Step 2: config.yaml 수정

```yaml
namespace: toolhive

apps:
  # CRD 먼저 배포
  toolhive-crds:
    type: helm
    chart: ./repos/stacklok-toolhive/deploy/charts/operator-crds

  # Operator 나중에 배포
  toolhive-operator:
    type: helm
    chart: ./repos/stacklok-toolhive/deploy/charts/operator
    depends_on:
      - toolhive-crds  # CRD 이후 배포
```

#### Step 3: 배포

```bash
sbkube apply --base-dir . --app-dir ai
```

### 2. Values 커스터마이징

#### values/toolhive-operator.yaml 생성

```yaml
# 리소스 제한
resources:
  limits:
    cpu: 1000m
    memory: 1Gi
  requests:
    cpu: 500m
    memory: 512Mi

# Replica 수
replicaCount: 2

# 이미지 설정
image:
  repository: ghcr.io/stacklok/toolhive
  tag: latest
  pullPolicy: IfNotPresent

# Webhook 설정
webhook:
  enabled: true
  port: 9443
```

#### config.yaml 업데이트

```yaml
apps:
  toolhive-operator:
    type: helm
    chart: ./repos/stacklok-toolhive/deploy/charts/operator
    values:
      - toolhive-operator.yaml  # 추가
```

### 3. RBAC 설정

Toolhive Operator는 클러스터 전체에 접근할 수 있으므로 RBAC 확인 필요:

```bash
# ClusterRole 확인
kubectl get clusterrole | grep toolhive

# ClusterRoleBinding 확인
kubectl get clusterrolebinding | grep toolhive

# ServiceAccount 확인
kubectl get sa -n toolhive
```

### 4. Webhook 설정

```bash
# ValidatingWebhookConfiguration 확인
kubectl get validatingwebhookconfiguration | grep toolhive

# MutatingWebhookConfiguration 확인
kubectl get mutatingwebhookconfiguration | grep toolhive
```

---

## ⚠️ 주의사항

### 1. Git 리포지토리 접근

**Public 리포지토리**: 인증 불필요 (현재 설정)
**Private 리포지토리**: SSH 키 또는 Personal Access Token 필요

```yaml
# sources.yaml (Private 리포지토리)
git_repos:
  stacklok-toolhive:
    url: "git@github.com:stacklok/toolhive.git"  # SSH
    branch: "main"
    # 또는
    # url: "https://<token>@github.com/stacklok/toolhive.git"
```

### 2. 단일 경로 제한

**제한**: SBKube git 타입은 하나의 `path`만 지원

**해결**:
- 방법 1: 앱 분리 (CRD와 Operator를 별도 앱으로)
- 방법 2: 수동 클론 후 Helm 타입 사용 (위 고급 사용법 참조)

### 3. 버전 관리

**권장**: 특정 브랜치나 태그 사용

```yaml
git_repos:
  stacklok-toolhive:
    url: "https://github.com/stacklok/toolhive.git"
    branch: "v1.0.0"  # 특정 버전 태그
```

### 4. 네임스페이스 권한

Toolhive Operator는 클러스터 전체에 접근하므로 주의:

```bash
# ClusterRole 권한 확인
kubectl describe clusterrole toolhive-operator
```

---

## 🔄 삭제

```bash
# 전체 삭제
sbkube delete --base-dir . --app-dir ai --namespace toolhive

# 또는 Helm으로 직접 삭제
helm uninstall toolhive-operator -n toolhive

# CRD 삭제 (주의: 모든 CR도 삭제됨)
kubectl delete crd -l app.kubernetes.io/name=toolhive

# 네임스페이스 삭제
kubectl delete namespace toolhive

# Git 리포지토리 삭제 (선택적)
rm -rf repos/stacklok-toolhive
```

---

## 📚 참고 자료

- [k3scode 프로젝트 개요](../README.md)
- [Toolhive GitHub](https://github.com/stacklok/toolhive)
- [SBKube Git 타입 가이드](../../../docs/02-features/application-types.md#git-type)
- [Kubernetes Operator Pattern](https://kubernetes.io/docs/concepts/extend-kubernetes/operator/)

---

## 🔗 관련 예제

- [Memory - 인메모리 스토어](../memory/README.md) - Redis, Memcached
- [RDB - 관계형 데이터베이스](../rdb/README.md) - PostgreSQL, MariaDB
- [DevOps - 개발 도구](../devops/README.md) - Nexus, ProxyND

---

## 🆚 Git vs Helm 타입 비교

| 비교 항목 | git 타입 (이 예제) | helm 타입 |
|---------|------------------|----------|
| **소스** | Git 리포지토리 | Helm 리포지토리 |
| **차트 위치** | 리포지토리 내 경로 | Helm 차트 이름 |
| **버전 관리** | Git 브랜치/태그 | Helm 차트 버전 |
| **로컬 수정** | ✅ 가능 (클론 후) | ❌ 불가능 (패키지) |
| **다중 차트** | ⚠️ 제한적 | ✅ 자유롭게 |
| **용도** | Git 기반 차트, 개발 중 차트 | 공식 릴리스 차트 |

**선택 가이드**:
- **Git 차트 사용**: git 타입 (Toolhive 등)
- **로컬 수정 필요**: git 타입 → 수동 클론 → helm 타입
- **안정적 배포**: helm 타입 (Bitnami 등)

---

**💡 팁**: Git 타입은 개발 중이거나 공식 Helm 차트가 없는 프로젝트에 유용합니다. 로컬에서 차트를 수정하려면 수동 클론 후 Helm 타입으로 전환하세요.
