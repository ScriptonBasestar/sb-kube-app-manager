# Security: Network Policies

Kubernetes NetworkPolicy로 Pod 간 네트워크 트래픽을 제어하는 예제입니다.

## 📋 개요

**카테고리**: Security

**구성 요소**:
- **Frontend Pod**: 외부 접근 허용, Backend만 호출
- **Backend Pod**: Frontend만 접근 허용, DB 호출
- **Database Pod**: Backend만 접근 허용
- **NetworkPolicy**: Pod 간 트래픽 규칙

**학습 목표**:
- Zero Trust 네트워크 모델
- Pod 간 통신 제한
- Ingress/Egress 규칙
- Namespace 격리

## 🎯 보안 원칙

### 기본 거부 (Default Deny)

```yaml
# 모든 트래픽 차단
apiVersion: networking.k8s.io/v1
kind: NetworkPolicy
metadata:
  name: default-deny-all
spec:
  podSelector: {}  # 모든 Pod
  policyTypes:
  - Ingress
  - Egress
```

### 명시적 허용 (Explicit Allow)

필요한 통신만 NetworkPolicy로 명시적 허용

## 🚀 빠른 시작

### 1. 배포

```bash
sbkube apply \
  --app-dir examples/security/03-network-policies \
  --namespace netpol-demo
```

### 2. 테스트

```bash
# Frontend → Backend (성공)
kubectl exec -n netpol-demo -it <frontend-pod> -- wget -O- http://backend

# Frontend → Database (실패 - NetworkPolicy 차단)
kubectl exec -n netpol-demo -it <frontend-pod> -- wget -T 5 -O- http://database
# Timeout

# Backend → Database (성공)
kubectl exec -n netpol-demo -it <backend-pod> -- wget -O- http://database
```

## 📖 주요 패턴

### 패턴 1: 3-Tier 아키텍처

```
Internet
    ↓ (허용)
Frontend (Ingress 허용, Backend만 Egress)
    ↓ (허용)
Backend (Frontend만 Ingress, Database만 Egress)
    ↓ (허용)
Database (Backend만 Ingress)
```

### 패턴 2: Namespace 격리

```yaml
apiVersion: networking.k8s.io/v1
kind: NetworkPolicy
metadata:
  name: allow-same-namespace
spec:
  podSelector: {}
  policyTypes:
  - Ingress
  ingress:
  - from:
    - podSelector: {}  # 같은 네임스페이스만
```

### 패턴 3: 외부 DNS 허용

```yaml
apiVersion: networking.k8s.io/v1
kind: NetworkPolicy
metadata:
  name: allow-dns
spec:
  podSelector: {}
  policyTypes:
  - Egress
  egress:
  - to:
    - namespaceSelector:
        matchLabels:
          name: kube-system
    ports:
    - protocol: UDP
      port: 53
```

## 🎓 학습 포인트

### 1. Ingress vs Egress

- **Ingress**: Pod로 들어오는 트래픽
- **Egress**: Pod에서 나가는 트래픽

### 2. 선택자 (Selectors)

```yaml
# Pod 선택
podSelector:
  matchLabels:
    app: frontend

# Namespace 선택
namespaceSelector:
  matchLabels:
    env: production

# IP 블록
ipBlock:
  cidr: 192.168.1.0/24
  except:
  - 192.168.1.5/32
```

### 3. 우선순위

- NetworkPolicy는 **화이트리스트** (허용 규칙)
- 여러 정책이 있으면 **OR 조건** (하나라도 허용하면 통과)
- 정책 없으면 **모두 허용** (기본 동작)

## 🔍 트러블슈팅

### 문제 1: NetworkPolicy가 작동하지 않음

**원인**: CNI가 NetworkPolicy 지원하지 않음

**해결**:
```bash
# k3s는 기본적으로 지원 (Flannel)
# 확인:
kubectl get networkpolicy -n netpol-demo
```

### 문제 2: DNS 해석 실패

**원인**: Egress 정책에서 DNS 차단됨

**해결**: DNS Egress 추가 (위 패턴 3 참조)

## 💡 실전 패턴

### 프로덕션 권장 설정

```yaml
# 1. 기본 거부
apiVersion: networking.k8s.io/v1
kind: NetworkPolicy
metadata:
  name: default-deny
spec:
  podSelector: {}
  policyTypes:
  - Ingress
  - Egress
---
# 2. DNS 허용
apiVersion: networking.k8s.io/v1
kind: NetworkPolicy
metadata:
  name: allow-dns
spec:
  podSelector: {}
  egress:
  - to:
    - namespaceSelector: {}
      podSelector:
        matchLabels:
          k8s-app: kube-dns
    ports:
    - protocol: UDP
      port: 53
---
# 3. 개별 앱 규칙
apiVersion: networking.k8s.io/v1
kind: NetworkPolicy
metadata:
  name: frontend-policy
spec:
  podSelector:
    matchLabels:
      app: frontend
  ingress:
  - from:
    - podSelector:
        matchLabels:
          app: ingress
  egress:
  - to:
    - podSelector:
        matchLabels:
          app: backend
```

## 📚 참고 자료

- [Kubernetes NetworkPolicy 공식 문서](https://kubernetes.io/docs/concepts/services-networking/network-policies/)
- [NetworkPolicy Recipes](https://github.com/ahmetb/kubernetes-network-policy-recipes)

## 🧹 정리

```bash
kubectl delete namespace netpol-demo
```

---

**Zero Trust 네트워크로 클러스터를 보호하세요! 🔒**
