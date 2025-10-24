# Use Case: Cert-Manager (자동 TLS 인증서)

cert-manager로 Let's Encrypt TLS 인증서를 자동으로 발급하고 갱신하는 예제입니다.

## 📋 개요

**구성 요소**:
- cert-manager (인증서 관리자)
- ClusterIssuer (Let's Encrypt)
- Certificate (인증서 리소스)
- Ingress (TLS 설정)

**학습 목표**:
- 자동 TLS 인증서 발급
- Let's Encrypt 연동
- 자동 갱신

## 🚀 빠른 시작

```bash
sbkube apply \
  --app-dir examples/use-cases/07-cert-manager \
  --namespace cert-manager
```

## 📖 주요 구성

### ClusterIssuer (Let's Encrypt)

```yaml
apiVersion: cert-manager.io/v1
kind: ClusterIssuer
metadata:
  name: letsencrypt-prod
spec:
  acme:
    server: https://acme-v02.api.letsencrypt.org/directory
    email: your-email@example.com
    privateKeySecretRef:
      name: letsencrypt-prod
    solvers:
    - http01:
        ingress:
          class: traefik
```

### Certificate

```yaml
apiVersion: cert-manager.io/v1
kind: Certificate
metadata:
  name: example-tls
spec:
  secretName: example-tls
  issuerRef:
    name: letsencrypt-prod
    kind: ClusterIssuer
  dnsNames:
  - example.com
  - www.example.com
```

### Ingress with TLS

```yaml
apiVersion: networking.k8s.io/v1
kind: Ingress
metadata:
  name: app
  annotations:
    cert-manager.io/cluster-issuer: "letsencrypt-prod"
spec:
  tls:
  - hosts:
    - example.com
    secretName: example-tls
  rules:
  - host: example.com
    http:
      paths:
      - path: /
        pathType: Prefix
        backend:
          service:
            name: app
            port:
              number: 80
```

## 🎓 학습 포인트

### 1. ACME Challenge

**HTTP-01**: 웹서버 기반 검증 (일반적)
**DNS-01**: DNS 기반 검증 (Wildcard 인증서)

### 2. 자동 갱신

cert-manager가 인증서 만료 전 자동 갱신

### 3. Staging 환경

테스트 시에는 Let's Encrypt Staging 사용:
```yaml
server: https://acme-staging-v02.api.letsencrypt.org/directory
```

## 💡 실전 패턴

### Wildcard 인증서

```yaml
apiVersion: cert-manager.io/v1
kind: Certificate
metadata:
  name: wildcard-tls
spec:
  secretName: wildcard-tls
  dnsNames:
  - "*.example.com"
  - example.com
  issuerRef:
    name: letsencrypt-prod
    kind: ClusterIssuer
```

## 📚 참고 자료

- [cert-manager 공식 문서](https://cert-manager.io/docs/)

## 🧹 정리

```bash
kubectl delete namespace cert-manager-demo
```

---

**자동 TLS로 안전한 HTTPS를 구현하세요! 🔐**
