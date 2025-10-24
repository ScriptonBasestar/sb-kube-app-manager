# Use Case: Service Mesh (Linkerd)

Linkerd를 활용한 마이크로서비스 관찰성, 보안, 신뢰성 강화 예제입니다.

## 📋 개요

**카테고리**: Use Cases

**구성 요소**:
- **Linkerd** (경량 Service Mesh)
- **Demo Microservices** (3개 서비스)
- **mTLS** (자동 암호화)
- **메트릭 & 트레이싱**

**학습 목표**:
- Service Mesh 기본 개념
- Linkerd 설치 및 사이드카 주입
- 서비스 간 mTLS 자동 암호화
- Golden Metrics 모니터링

## 🎯 사용 사례

### 1. 마이크로서비스 3-Tier 아키텍처
```
Frontend → Backend → Database
   ↓         ↓          ↓
Linkerd Proxy (자동 주입)
   ↓         ↓          ↓
mTLS 암호화, Metrics, Retry, Timeout
```

### 2. 자동 mTLS
- 서비스 간 통신 자동 암호화
- 인증서 자동 관리 (Linkerd 제공)
- Zero-config 보안

## 🚀 빠른 시작

```bash
# Linkerd CLI 설치 (로컬 머신)
curl -sL https://run.linkerd.io/install | sh
export PATH=$PATH:$HOME/.linkerd2/bin

# Linkerd 설치 확인 (사전 검증)
linkerd check --pre

# SBKube로 Linkerd 및 데모 앱 배포
sbkube apply \
  --app-dir examples/use-cases/08-service-mesh \
  --namespace linkerd-demo

# Linkerd 설치 확인 (사후 검증)
linkerd check

# Dashboard 실행 (브라우저 자동 열림)
linkerd dashboard &
```

## 📖 Linkerd 설정

### 1. Linkerd Control Plane 설치

```yaml
# config.yaml
linkerd-crds:
  type: helm
  chart: linkerd/linkerd-crds

linkerd-control-plane:
  type: helm
  chart: linkerd/linkerd-control-plane
  depends_on:
    - linkerd-crds
```

### 2. Sidecar 자동 주입

**네임스페이스 어노테이션**:
```yaml
apiVersion: v1
kind: Namespace
metadata:
  name: linkerd-demo
  annotations:
    linkerd.io/inject: enabled  # 자동 주입 활성화
```

**Pod 어노테이션** (선택적):
```yaml
apiVersion: apps/v1
kind: Deployment
spec:
  template:
    metadata:
      annotations:
        linkerd.io/inject: enabled
```

### 3. 서비스 간 mTLS

Linkerd는 자동으로 모든 Pod에 Proxy를 주입하고 mTLS를 활성화합니다:

```
Pod A → Linkerd Proxy A → mTLS → Linkerd Proxy B → Pod B
```

**확인 방법**:
```bash
# TLS 상태 확인
linkerd -n linkerd-demo stat deploy

# Tap (실시간 트래픽 모니터링)
linkerd -n linkerd-demo tap deploy/frontend

# Top (트래픽 순위)
linkerd -n linkerd-demo top deploy
```

## 🎓 학습 포인트

### 1. Golden Metrics

Linkerd는 모든 서비스에 대해 자동으로 수집:
- **Success Rate**: 성공률
- **Request Rate**: 초당 요청 수
- **Latency**: P50, P95, P99 지연시간

**확인**:
```bash
linkerd -n linkerd-demo stat deploy
```

### 2. 트래픽 관찰

```bash
# 실시간 요청 관찰
linkerd -n linkerd-demo tap deploy/backend

# 서비스 간 의존성 확인
linkerd -n linkerd-demo routes deploy/frontend
```

### 3. 신뢰성 패턴

**자동 Retry**:
```yaml
apiVersion: policy.linkerd.io/v1beta1
kind: HTTPRoute
metadata:
  name: backend-route
spec:
  parentRefs:
  - name: backend
    kind: Service
  rules:
  - timeouts:
      request: 5s
```

## 💡 실전 패턴

### Traffic Split (Canary Deployment)

```yaml
apiVersion: split.smi-spec.io/v1alpha1
kind: TrafficSplit
metadata:
  name: backend-split
spec:
  service: backend
  backends:
  - service: backend-v1
    weight: 90
  - service: backend-v2
    weight: 10
```

### Circuit Breaking

```yaml
apiVersion: policy.linkerd.io/v1alpha1
kind: Server
metadata:
  name: backend-server
spec:
  podSelector:
    matchLabels:
      app: backend
  port: http
  proxyProtocol: HTTP/1
```

## 🔍 트러블슈팅

### 문제: Sidecar가 주입되지 않음

**확인**:
```bash
# 네임스페이스 어노테이션 확인
kubectl get ns linkerd-demo -o yaml | grep inject

# Pod 재시작
kubectl rollout restart deploy -n linkerd-demo
```

### 문제: mTLS 작동 안함

**확인**:
```bash
# Linkerd Proxy 확인
kubectl get pods -n linkerd-demo -o jsonpath='{.items[*].spec.containers[*].name}'

# TLS 상태 확인
linkerd -n linkerd-demo edges deployment
```

## 📚 참고 자료

- [Linkerd 공식 문서](https://linkerd.io/2/overview/)
- [Getting Started](https://linkerd.io/2/getting-started/)

## 🧹 정리

```bash
kubectl delete namespace linkerd-demo
helm uninstall linkerd-control-plane -n linkerd
helm uninstall linkerd-crds -n linkerd
```

---

**Linkerd로 마이크로서비스를 관찰하고 보호하세요! 🔗**
