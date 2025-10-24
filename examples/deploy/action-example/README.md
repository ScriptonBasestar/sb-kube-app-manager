# Action Type Example - kubectl 액션 실행

SBKube의 **action 타입**을 사용하여 kubectl 명령어(apply/create/delete)를 순차적으로 실행하는 예제입니다.

## 📋 목차

- [개요](#-개요)
- [action 타입이란?](#-action-타입이란)
- [사용 시나리오](#-사용-시나리오)
- [설정 구조](#-설정-구조)
- [실행 방법](#-실행-방법)
- [고급 사용법](#-고급-사용법)

---

## 🎯 개요

이 예제는 다음을 시연합니다:

1. **CRD 배포**: Custom Resource Definition 생성
2. **Operator 배포**: CRD를 관리하는 Operator 배포
3. **순차 실행**: CRD → Operator 순서로 자동 배포
4. **kubectl 액션**: apply/create/delete 명령어 활용

---

## 🔧 action 타입이란?

**action 타입**은 kubectl 명령어를 순차적으로 실행하는 애플리케이션 타입입니다.

### 지원 액션

| 액션 타입 | kubectl 명령어 | 설명 | 기존 리소스 처리 |
|---------|---------------|------|---------------|
| **apply** | `kubectl apply` | 리소스 생성/업데이트 | 업데이트 (멱등성) |
| **create** | `kubectl create` | 리소스 생성 (엄격) | 오류 발생 |
| **delete** | `kubectl delete` | 리소스 삭제 | 삭제 |

### Helm과의 차이점

| 비교 항목 | Helm 타입 | action 타입 |
|---------|----------|-----------|
| **패키징** | 차트 기반 | 원시 YAML 매니페스트 |
| **템플릿팅** | Jinja2/Go template | 없음 (정적 YAML) |
| **릴리스 관리** | Helm 릴리스 추적 | kubectl 리소스만 생성 |
| **롤백** | `helm rollback` | 수동 처리 필요 |
| **용도** | 복잡한 앱 배포 | CRD, Operator, 간단한 리소스 |

---

## 🚀 사용 시나리오

### 시나리오 1: CRD + Operator 배포

**배경**: Kubernetes Operator를 배포할 때 CRD를 먼저 생성해야 합니다.

**문제**: Helm은 CRD를 별도로 관리하기 어렵고, 순서 보장이 불확실합니다.

**해결**: action 타입으로 순차 실행

```yaml
apps:
  custom-operator:
    type: action
    actions:
      - type: apply
        path: manifests/custom-crd.yaml      # 1. CRD 먼저
      - type: apply
        path: manifests/custom-operator.yaml  # 2. Operator 나중에
```

### 시나리오 2: 엄격한 리소스 생성 (create)

**배경**: 이미 존재하는 리소스를 덮어쓰면 안 되는 경우

**해결**: `create` 액션 사용

```yaml
apps:
  strict-resource:
    type: action
    actions:
      - type: create                    # 이미 존재하면 실패
        path: manifests/resource.yaml
```

**결과**: 리소스가 이미 존재하면 배포 실패 (안전성 보장)

### 시나리오 3: 리소스 정리 (delete)

**배경**: 배포 과정에서 오래된 리소스를 먼저 삭제해야 하는 경우

**해결**: `delete` 액션 사용

```yaml
apps:
  cleanup-job:
    type: action
    actions:
      - type: delete
        path: manifests/old-job.yaml    # 오래된 Job 삭제
      - type: apply
        path: manifests/new-job.yaml    # 새 Job 생성
```

**⚠️ 주의**: 앱 전체 삭제는 `sbkube delete` 명령어를 사용하세요.

---

## 📝 설정 구조

### config.yaml

```yaml
namespace: example-action

apps:
  custom-operator:
    type: action                         # 애플리케이션 타입
    actions:                             # 액션 목록 (순차 실행)
      - type: apply                      # kubectl apply
        path: manifests/custom-crd.yaml  # 매니페스트 파일 경로
      - type: apply
        path: manifests/custom-operator.yaml
```

### manifests/custom-crd.yaml

CustomResourceDefinition 정의:

```yaml
apiVersion: apiextensions.k8s.io/v1
kind: CustomResourceDefinition
metadata:
  name: myresources.example.com
spec:
  group: example.com
  versions:
  - name: v1
    served: true
    storage: true
    schema:
      openAPIV3Schema:
        type: object
        properties:
          spec:
            type: object
            properties:
              replicas:
                type: integer
                minimum: 1
  scope: Namespaced
  names:
    plural: myresources
    singular: myresource
    kind: MyResource
```

### manifests/custom-operator.yaml

Operator Deployment + RBAC:

```yaml
apiVersion: apps/v1
kind: Deployment
metadata:
  name: custom-operator
spec:
  replicas: 1
  template:
    spec:
      containers:
      - name: operator
        image: busybox:latest
        command: ["sleep", "3600"]
---
apiVersion: v1
kind: ServiceAccount
metadata:
  name: custom-operator
---
apiVersion: rbac.authorization.k8s.io/v1
kind: ClusterRole
metadata:
  name: custom-operator
rules:
- apiGroups: ["example.com"]
  resources: ["myresources"]
  verbs: ["get", "list", "watch", "create", "update", "patch", "delete"]
---
apiVersion: rbac.authorization.k8s.io/v1
kind: ClusterRoleBinding
metadata:
  name: custom-operator
roleRef:
  apiGroup: rbac.authorization.k8s.io
  kind: ClusterRole
  name: custom-operator
subjects:
- kind: ServiceAccount
  name: custom-operator
  namespace: example-action
```

---

## ⚡ 실행 방법

### 1. 통합 배포 (권장)

```bash
cd examples/deploy/action-example

# 전체 워크플로우 실행 (prepare → build → template → deploy)
sbkube apply --app-dir . --namespace example-action
```

**실행 결과**:
```
✅ CRD 생성: myresources.example.com
✅ Operator 배포: custom-operator (Deployment, ServiceAccount, RBAC)
```

### 2. 단계별 배포

```bash
# 1. 준비 (action 타입은 이 단계에서 아무 작업 안 함)
sbkube prepare --app-dir .

# 2. 빌드 (action 타입은 이 단계에서 아무 작업 안 함)
sbkube build --app-dir .

# 3. 템플릿 (매니페스트 복사)
sbkube template --app-dir . --output-dir /tmp/action-example

# 4. 배포 (kubectl 액션 실행)
sbkube deploy --app-dir . --namespace example-action
```

### 3. Dry-run 모드

```bash
# 실제 배포 없이 실행 계획 확인
sbkube deploy --app-dir . --namespace example-action --dry-run
```

---

## 🔍 배포 확인

### CRD 확인

```bash
# CRD 생성 확인
kubectl get crd myresources.example.com

# CRD 상세 정보
kubectl describe crd myresources.example.com
```

**예상 출력**:
```
NAME                        CREATED AT
myresources.example.com     2025-10-24T10:00:00Z
```

### Operator 확인

```bash
# Deployment 확인
kubectl get deployment -n example-action

# Pod 상태 확인
kubectl get pods -n example-action

# ServiceAccount 및 RBAC 확인
kubectl get sa,clusterrole,clusterrolebinding -n example-action
```

**예상 출력**:
```
NAME                               READY   UP-TO-DATE   AVAILABLE   AGE
deployment.apps/custom-operator    1/1     1            1           1m

NAME                                   READY   STATUS    RESTARTS   AGE
pod/custom-operator-xxxx-yyyy          1/1     Running   0          1m
```

### Custom Resource 생성 테스트

```bash
# 샘플 CR 생성
cat <<EOF | kubectl apply -f -
apiVersion: example.com/v1
kind: MyResource
metadata:
  name: test-resource
  namespace: example-action
spec:
  replicas: 3
EOF

# CR 확인
kubectl get myresources -n example-action
```

---

## 🛠️ 고급 사용법

### 1. 여러 매니페스트 파일 처리

```yaml
apps:
  multi-manifest:
    type: action
    actions:
      - type: apply
        path: manifests/namespace.yaml
      - type: apply
        path: manifests/configmap.yaml
      - type: apply
        path: manifests/deployment.yaml
      - type: apply
        path: manifests/service.yaml
```

### 2. 조건부 활성화/비활성화

```yaml
apps:
  optional-resource:
    type: action
    enabled: false                      # 배포 비활성화
    actions:
      - type: apply
        path: manifests/optional.yaml
```

### 3. create vs apply 선택

**apply 사용 시** (권장):
```yaml
actions:
  - type: apply
    path: manifests/resource.yaml
```
- **장점**: 멱등성 보장, 업데이트 가능
- **단점**: 실수로 덮어쓸 수 있음

**create 사용 시**:
```yaml
actions:
  - type: create
    path: manifests/resource.yaml
```
- **장점**: 안전성 (이미 존재하면 실패)
- **단점**: 업데이트 불가능

### 4. 네임스페이스별 배포

```yaml
namespace: production              # 기본 네임스페이스

apps:
  prod-operator:
    type: action
    actions:
      - type: apply
        path: manifests/prod-crd.yaml
      - type: apply
        path: manifests/prod-operator.yaml
```

```bash
# production 네임스페이스에 배포
sbkube deploy --app-dir . --namespace production

# staging 네임스페이스에 배포 (오버라이드)
sbkube deploy --app-dir . --namespace staging
```

---

## ⚠️ 주의사항 및 제한사항

### 1. 순서 보장

- **보장됨**: 동일 앱 내 액션들은 순차 실행
- **보장 안 됨**: 다른 앱 간의 순서
  ```yaml
  apps:
    app-a:
      type: action
      actions: [...]    # app-a의 액션들은 순차 실행
    app-b:
      type: action
      actions: [...]    # app-b는 app-a와 독립적으로 실행
  ```

**해결**: 의존성이 있는 리소스는 하나의 앱으로 통합

### 2. 롤백 제한

- **Helm 타입**: `helm rollback` 지원
- **action 타입**: 수동 롤백 필요

**수동 롤백 방법**:
```bash
# 1. 이전 매니페스트로 되돌리기
git checkout <previous-commit> manifests/

# 2. 재배포
sbkube apply --app-dir .

# 또는 수동 삭제
kubectl delete -f manifests/custom-operator.yaml
kubectl delete -f manifests/custom-crd.yaml
```

### 3. 템플릿팅 미지원

- **Helm**: values.yaml + Go 템플릿
- **action**: 정적 YAML만 지원

**대안**: Jinja2로 사전 렌더링 또는 Kustomize 사용

### 4. 리소스 삭제 주의

```yaml
# ❌ 잘못된 사용
apps:
  cleanup:
    type: action
    actions:
      - type: delete
        path: manifests/all-resources.yaml  # 위험!
```

**올바른 방법**:
```bash
# 앱 전체 삭제는 sbkube delete 사용
sbkube delete --app-dir . --namespace example-action
```

---

## 🔄 삭제 (Uninstall)

### 방법 1: sbkube delete (권장)

```bash
sbkube delete --app-dir . --namespace example-action
```

**실행 내용**:
- Deployment, ServiceAccount, RBAC 삭제
- CRD는 수동 삭제 필요 (다른 리소스에 영향 줄 수 있음)

### 방법 2: kubectl delete

```bash
# Operator 삭제
kubectl delete -f manifests/custom-operator.yaml

# CRD 삭제 (주의: 모든 CR도 함께 삭제됨)
kubectl delete -f manifests/custom-crd.yaml

# 또는 네임스페이스 전체 삭제
kubectl delete namespace example-action
```

---

## 📚 참고 자료

- [SBKube 애플리케이션 타입 가이드](../../../docs/02-features/application-types.md)
- [kubectl 명령어 참조](https://kubernetes.io/docs/reference/kubectl/)
- [CRD 가이드](https://kubernetes.io/docs/tasks/extend-kubernetes/custom-resources/custom-resource-definitions/)
- [Operator Pattern](https://kubernetes.io/docs/concepts/extend-kubernetes/operator/)

---

## 🆚 다른 타입과 비교

| 기능 | action | helm | yaml | exec |
|-----|--------|------|------|------|
| **kubectl 명령어** | ✅ apply/create/delete | ❌ | ❌ | ❌ |
| **Helm 릴리스 관리** | ❌ | ✅ | ❌ | ❌ |
| **템플릿팅** | ❌ | ✅ | ❌ | ❌ |
| **순차 실행** | ✅ | ❌ | ❌ | ✅ |
| **커스텀 스크립트** | ❌ | ❌ | ❌ | ✅ |
| **CRD 배포** | ✅ 최적 | ⚠️ 제한적 | ✅ 가능 | ✅ 가능 |

**선택 가이드**:
- **CRD + Operator**: action 타입 (순서 보장)
- **복잡한 앱**: helm 타입 (템플릿팅 + 릴리스 관리)
- **간단한 매니페스트**: yaml 타입 (단일 파일)
- **커스텀 로직**: exec 타입 (스크립트 실행)

---

**💡 팁**: action 타입은 CRD 및 Operator 배포에 최적화되어 있습니다. 복잡한 애플리케이션은 Helm 타입을 사용하세요.
