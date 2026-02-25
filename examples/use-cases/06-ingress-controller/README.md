# Use Case: Ingress Controller (Traefik)

k3s 기본 Traefik을 활용한 고급 Ingress 설정 예제입니다.

## 📋 개요

**카테고리**: Use Cases

**구성 요소**:
- **Traefik** (k3s 기본 설치 활용)
- **미들웨어** (압축, 인증, Rate Limiting)
- **IngressRoute** (Traefik CRD)
- **데모 앱** (3개 서비스)

**학습 목표**:
- k3s Traefik 활용
- 미들웨어 설정
- 다중 도메인 라우팅
- TLS 설정

## 🎯 사용 사례

### 1. 다중 서비스 라우팅
```
example.com/app1 → App1 Service
example.com/app2 → App2 Service
api.example.com → API Service
```

### 2. 미들웨어 체인
```
Request → 압축 → 인증 → Rate Limit → Backend
```

## 🚀 빠른 시작

```bash
# k3s Traefik 확인
kubectl get pods -n kube-system -l app.kubernetes.io/name=traefik

# 예제 배포
sbkube apply -f sbkube.yaml \
  --app-dir examples/use-cases/06-ingress-controller \
  --namespace ingress-demo
```

## 📖 Traefik 설정

### IngressRoute (Traefik CRD)

```yaml
apiVersion: traefik.containo.us/v1alpha1
kind: IngressRoute
metadata:
  name: app1-route
spec:
  entryPoints:
    - web
  routes:
  - match: Host(`example.com`) && PathPrefix(`/app1`)
    kind: Rule
    services:
    - name: app1
      port: 80
    middlewares:
    - name: compress
```

### 미들웨어

**압축**:
```yaml
apiVersion: traefik.containo.us/v1alpha1
kind: Middleware
metadata:
  name: compress
spec:
  compress: {}
```

**Basic Auth**:
```yaml
apiVersion: traefik.containo.us/v1alpha1
kind: Middleware
metadata:
  name: auth
spec:
  basicAuth:
    secret: auth-secret
```

**Rate Limiting**:
```yaml
apiVersion: traefik.containo.us/v1alpha1
kind: Middleware
metadata:
  name: rate-limit
spec:
  rateLimit:
    average: 100
    burst: 50
```

## 🎓 학습 포인트

### 1. k3s Traefik 활용

k3s는 Traefik을 기본 제공:
- 별도 설치 불필요
- IngressRoute CRD 사용
- 자동 Let's Encrypt 지원 가능

### 2. 미들웨어 체이닝

```yaml
middlewares:
- name: compress      # 1. 압축
- name: auth         # 2. 인증
- name: rate-limit   # 3. Rate Limiting
```

### 3. Path 기반 라우팅

```yaml
# /app1 경로
- match: PathPrefix(`/app1`)
  middlewares:
  - name: strip-prefix-app1
  services:
  - name: app1
```

## 💡 실전 패턴

### TLS 설정

```yaml
apiVersion: traefik.containo.us/v1alpha1
kind: IngressRoute
metadata:
  name: secure-route
spec:
  entryPoints:
    - websecure
  routes:
  - match: Host(`secure.example.com`)
    kind: Rule
    services:
    - name: app
      port: 80
  tls:
    secretName: tls-cert
```

### 헤더 조작

```yaml
apiVersion: traefik.containo.us/v1alpha1
kind: Middleware
metadata:
  name: custom-headers
spec:
  headers:
    customRequestHeaders:
      X-Custom-Header: "value"
    customResponseHeaders:
      X-Powered-By: "Traefik"
```

## 🔍 트러블슈팅

### 문제: IngressRoute가 작동하지 않음

**확인**:
```bash
# Traefik Pod 확인
kubectl get pods -n kube-system -l app.kubernetes.io/name=traefik

# Traefik 로그
kubectl logs -n kube-system -l app.kubernetes.io/name=traefik
```

### 문제: 미들웨어 적용 안됨

**해결**: 같은 네임스페이스에 있어야 함
```yaml
# IngressRoute와 Middleware가 동일 네임스페이스
metadata:
  namespace: ingress-demo
```

## 📚 참고 자료

- [Traefik 공식 문서](https://doc.traefik.io/traefik/)
- [k3s Traefik 가이드](https://docs.k3s.io/networking#traefik-ingress-controller)

## 🧹 정리

```bash
kubectl delete namespace ingress-demo
```

---

**Traefik으로 강력한 Ingress를 구현하세요! 🚦**
