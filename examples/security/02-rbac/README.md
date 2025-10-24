# Security: RBAC (Role-Based Access Control)

Kubernetes RBAC를 사용하여 세밀한 권한 관리를 구현하는 예제입니다.

## 📋 개요

**카테고리**: Security

**구성 요소**:
- **ServiceAccount**: Pod가 사용할 계정
- **Role**: 네임스페이스 내 권한 정의
- **RoleBinding**: ServiceAccount와 Role 연결
- **ClusterRole**: 클러스터 전체 권한
- **ClusterRoleBinding**: ClusterRole 바인딩

**학습 목표**:
- 최소 권한 원칙 (Principle of Least Privilege)
- 네임스페이스별 권한 격리
- ServiceAccount 기반 권한 관리
- 실전 RBAC 패턴

## 🎯 사용 사례

### 1. 애플리케이션 권한 제한
- Pod가 특정 리소스만 접근
- ConfigMap/Secret 읽기 전용
- 특정 API만 호출 가능

### 2. 개발자/운영자 권한 분리
- 개발자: 배포 및 읽기
- 운영자: 모든 권한
- 감사자: 읽기 전용

### 3. CI/CD 파이프라인 권한
- 배포 전용 ServiceAccount
- 특정 네임스페이스만 접근
- Secret 생성 불가 (보안)

## 🚀 빠른 시작

### 1. 전체 배포

```bash
sbkube apply \
  --app-dir examples/security/02-rbac \
  --namespace rbac-demo
```

### 2. 권한 확인

```bash
# ServiceAccount 확인
kubectl get sa -n rbac-demo

# Role 확인
kubectl get role -n rbac-demo

# RoleBinding 확인
kubectl get rolebinding -n rbac-demo

# Pod가 ServiceAccount 사용 중인지 확인
kubectl get pods -n rbac-demo -o yaml | grep serviceAccountName
```

### 3. 권한 테스트

```bash
# Pod에서 권한 테스트
kubectl exec -n rbac-demo -it <readonly-pod> -- sh

# ConfigMap 조회 (성공)
kubectl get configmaps

# Secret 조회 (실패 - 권한 없음)
kubectl get secrets
# Error: secrets is forbidden
```

## 📖 RBAC 개념

### 1. 4가지 리소스

```
ServiceAccount (누가?)
    +
Role/ClusterRole (무엇을?)
    +
RoleBinding/ClusterRoleBinding (연결)
    =
권한 부여
```

### 2. Role vs ClusterRole

| 비교 | Role | ClusterRole |
|------|------|-------------|
| **범위** | 네임스페이스 내 | 클러스터 전체 |
| **리소스** | Pod, Service 등 | Node, Namespace 등 |
| **사용 사례** | 앱별 권한 | 관리자 권한 |

### 3. 권한 (Verbs)

```yaml
rules:
- apiGroups: [""]
  resources: ["pods"]
  verbs:
    - get       # 조회
    - list      # 목록
    - watch     # 감시
    - create    # 생성
    - update    # 수정
    - patch     # 부분 수정
    - delete    # 삭제
```

## 🔧 주요 예제

### 예제 1: 읽기 전용 ServiceAccount

```yaml
apiVersion: v1
kind: ServiceAccount
metadata:
  name: readonly-sa
---
apiVersion: rbac.authorization.k8s.io/v1
kind: Role
metadata:
  name: readonly-role
rules:
- apiGroups: [""]
  resources: ["pods", "services", "configmaps"]
  verbs: ["get", "list", "watch"]
---
apiVersion: rbac.authorization.k8s.io/v1
kind: RoleBinding
metadata:
  name: readonly-binding
subjects:
- kind: ServiceAccount
  name: readonly-sa
roleRef:
  kind: Role
  name: readonly-role
  apiGroup: rbac.authorization.k8s.io
```

### 예제 2: 배포 전용 ServiceAccount

```yaml
apiVersion: v1
kind: ServiceAccount
metadata:
  name: deployer-sa
---
apiVersion: rbac.authorization.k8s.io/v1
kind: Role
metadata:
  name: deployer-role
rules:
- apiGroups: ["apps"]
  resources: ["deployments", "replicasets"]
  verbs: ["get", "list", "create", "update", "patch"]
- apiGroups: [""]
  resources: ["pods", "pods/log"]
  verbs: ["get", "list"]
---
apiVersion: rbac.authorization.k8s.io/v1
kind: RoleBinding
metadata:
  name: deployer-binding
subjects:
- kind: ServiceAccount
  name: deployer-sa
roleRef:
  kind: Role
  name: deployer-role
  apiGroup: rbac.authorization.k8s.io
```

### 예제 3: Pod에서 ServiceAccount 사용

```yaml
apiVersion: apps/v1
kind: Deployment
metadata:
  name: app-with-rbac
spec:
  template:
    spec:
      serviceAccountName: readonly-sa  # ServiceAccount 지정
      containers:
      - name: app
        image: nginx:alpine
```

## 🎓 학습 포인트

### 1. 최소 권한 원칙

**❌ 나쁜 예**:
```yaml
# 모든 권한 부여
rules:
- apiGroups: ["*"]
  resources: ["*"]
  verbs: ["*"]
```

**✅ 좋은 예**:
```yaml
# 필요한 권한만
rules:
- apiGroups: [""]
  resources: ["configmaps"]
  verbs: ["get", "list"]
```

### 2. 기본 ServiceAccount

```yaml
# 명시하지 않으면 "default" ServiceAccount 사용
# default는 최소 권한만 가짐 (보안 권장)
spec:
  serviceAccountName: default
```

### 3. ClusterRole 재사용

```yaml
# ClusterRole을 여러 네임스페이스에서 재사용
apiVersion: rbac.authorization.k8s.io/v1
kind: ClusterRole
metadata:
  name: pod-reader
rules:
- apiGroups: [""]
  resources: ["pods"]
  verbs: ["get", "list"]
---
# 네임스페이스 A에서 바인딩
apiVersion: rbac.authorization.k8s.io/v1
kind: RoleBinding
metadata:
  name: read-pods
  namespace: team-a
subjects:
- kind: ServiceAccount
  name: app-sa
  namespace: team-a
roleRef:
  kind: ClusterRole  # ClusterRole 참조
  name: pod-reader
  apiGroup: rbac.authorization.k8s.io
```

## 🧪 테스트 시나리오

### 시나리오 1: 권한 확인

```bash
# ServiceAccount로 권한 테스트
kubectl auth can-i get pods \
  --as=system:serviceaccount:rbac-demo:readonly-sa \
  -n rbac-demo
# yes

kubectl auth can-i delete pods \
  --as=system:serviceaccount:rbac-demo:readonly-sa \
  -n rbac-demo
# no
```

### 시나리오 2: Pod에서 kubectl 사용

```bash
# Pod 내부에 kubectl 설치된 경우
kubectl exec -it <pod-name> -- sh

# 권한 내 작업 (성공)
kubectl get configmaps

# 권한 외 작업 (실패)
kubectl delete configmap test
# Error: forbidden
```

## 🔍 트러블슈팅

### 문제 1: "Forbidden" 에러

**원인**: 권한 부족

**해결**:
```bash
# 필요한 권한 확인
kubectl auth can-i <verb> <resource> \
  --as=system:serviceaccount:<namespace>:<sa-name>

# Role 수정하여 권한 추가
```

### 문제 2: RoleBinding이 작동하지 않음

**원인**: 네임스페이스 불일치

**해결**:
```yaml
# ServiceAccount, Role, RoleBinding이 모두 같은 네임스페이스에 있어야 함
metadata:
  namespace: rbac-demo  # 일치 필수
```

## 💡 실전 패턴

### 패턴 1: CI/CD 파이프라인

```yaml
# GitLab Runner용 ServiceAccount
apiVersion: v1
kind: ServiceAccount
metadata:
  name: gitlab-deploy
---
apiVersion: rbac.authorization.k8s.io/v1
kind: Role
metadata:
  name: gitlab-deploy-role
rules:
- apiGroups: ["apps"]
  resources: ["deployments"]
  verbs: ["get", "list", "create", "update", "patch"]
- apiGroups: [""]
  resources: ["services", "configmaps"]
  verbs: ["get", "list", "create", "update"]
```

### 패턴 2: 감사 전용

```yaml
# 읽기 전용 감사자
apiVersion: rbac.authorization.k8s.io/v1
kind: ClusterRole
metadata:
  name: audit-reader
rules:
- apiGroups: ["*"]
  resources: ["*"]
  verbs: ["get", "list", "watch"]
```

### 패턴 3: 네임스페이스 격리

```yaml
# 팀별 네임스페이스 권한
apiVersion: rbac.authorization.k8s.io/v1
kind: RoleBinding
metadata:
  name: team-a-admin
  namespace: team-a
subjects:
- kind: Group
  name: team-a-developers
roleRef:
  kind: ClusterRole
  name: admin  # 기본 제공 ClusterRole
  apiGroup: rbac.authorization.k8s.io
```

## 📚 추가 학습 자료

- [Kubernetes RBAC 공식 문서](https://kubernetes.io/docs/reference/access-authn-authz/rbac/)
- [RBAC 베스트 프랙티스](https://kubernetes.io/docs/concepts/security/rbac-good-practices/)

## 🎯 다음 단계

1. **Network Policies**: 네트워크 수준 보안
2. **Pod Security**: Pod 보안 컨텍스트
3. **OPA (Open Policy Agent)**: 정책 기반 보안

## 🧹 정리

```bash
kubectl delete namespace rbac-demo
```

---

**최소 권한 원칙으로 안전한 클러스터를 운영하세요! 🔒**
