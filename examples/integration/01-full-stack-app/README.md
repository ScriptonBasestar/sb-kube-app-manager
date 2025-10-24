# Integration: Full-Stack Application

완전한 웹 애플리케이션 스택 (Frontend + Backend + Database + Cache + Ingress) 예제입니다.

## 📋 개요

**카테고리**: Integration

**구성 요소**:
- **Frontend**: React SPA (Nginx)
- **Backend**: REST API (Node.js/Python)
- **Database**: PostgreSQL
- **Cache**: Redis
- **Ingress**: Traefik

**학습 목표**:
- 전체 스택 배포 오케스트레이션
- 서비스 간 의존성 관리
- 환경 변수 기반 설정
- End-to-End 통합

## 🎯 아키텍처

```
User → Traefik Ingress
         ↓
    Frontend (Nginx)
         ↓
    Backend API (Node.js)
         ↓
    ┌────┴────┐
    ↓         ↓
PostgreSQL  Redis
```

## 🚀 빠른 시작

```bash
# 전체 스택 배포
sbkube apply \
  --app-dir examples/integration/01-full-stack-app \
  --namespace fullstack

# 배포 확인
kubectl get pods -n fullstack
kubectl get ingress -n fullstack

# 접속 테스트 (로컬)
curl http://fullstack.local/api/health
```

## 📖 상세 설명

### 1. 배포 순서 (depends_on)

```yaml
1. PostgreSQL + Redis (데이터 레이어)
2. Backend (API 레이어)
3. Frontend (UI 레이어)
4. Ingress (라우팅 레이어)
```

### 2. 환경 변수 전달

**Backend → Database**:
```yaml
env:
- name: DATABASE_URL
  value: "postgresql://user:pass@postgres:5432/db"
- name: REDIS_URL
  value: "redis://redis:6379"
```

### 3. Health Check

모든 서비스는 /health 엔드포인트 제공:
- Backend: `GET /api/health`
- Frontend: `GET /health`

## 💡 실전 패턴

### ConfigMap 기반 설정
```yaml
apiVersion: v1
kind: ConfigMap
metadata:
  name: app-config
data:
  API_URL: "http://backend:3000"
  LOG_LEVEL: "info"
```

### Secret 기반 인증
```yaml
apiVersion: v1
kind: Secret
metadata:
  name: db-credentials
stringData:
  username: appuser
  password: secretpassword
```

## 🧹 정리

```bash
kubectl delete namespace fullstack
```

---

**전체 스택 애플리케이션 배포 마스터! 🚀**
