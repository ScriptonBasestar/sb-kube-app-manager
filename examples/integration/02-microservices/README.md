# Integration: Microservices Architecture

5개 마이크로서비스 + API Gateway + Service Mesh 통합 예제입니다.

## 📋 개요

**구성 요소**:
- **API Gateway** (Traefik IngressRoute)
- **5 Microservices** (Users, Orders, Products, Payments, Notifications)
- **Service Mesh** (Linkerd, 선택적)
- **Service Discovery** (Kubernetes DNS)

## 🎯 아키텍처

```
API Gateway (Traefik)
       ↓
   ┌───┼───┬───┬───┐
   ↓   ↓   ↓   ↓   ↓
Users Orders Products Payments Notifications
```

## 🚀 빠른 시작

```bash
sbkube apply -f sbkube.yaml \
  --app-dir examples/integration/02-microservices \
  --namespace microservices
```

---

**마이크로서비스 아키텍처 구현 완료! 🔗**
