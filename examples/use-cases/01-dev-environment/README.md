# Use Case 01: Development Environment Setup

k3s 클러스터에 개발 환경을 구축하는 실전 예제입니다.

## 시나리오

로컬 k3s 클러스터에 다음 서비스들을 배포하여 완전한 개발 환경을 구성합니다:

1. **Redis** - 세션 스토어 및 캐시
2. **PostgreSQL** - 메인 데이터베이스
3. **Mailhog** - 이메일 테스트 서버
4. **MinIO** - S3 호환 객체 스토리지

## 아키텍처

```
┌─────────────────────────────────────────┐
│         Development Environment         │
├─────────────────────────────────────────┤
│                                         │
│  ┌─────────┐  ┌────────────┐           │
│  │  Redis  │  │ PostgreSQL │           │
│  │  :6379  │  │   :5432    │           │
│  └─────────┘  └────────────┘           │
│                                         │
│  ┌─────────┐  ┌────────────┐           │
│  │ Mailhog │  │   MinIO    │           │
│  │  :8025  │  │   :9000    │           │
│  └─────────┘  └────────────┘           │
│                                         │
└─────────────────────────────────────────┘
```

## 배포

```bash
# 전체 환경 배포
sbkube apply --app-dir .

# 특정 서비스만 배포
sbkube apply --app-dir . --apps redis,postgresql
```

## 서비스 접근

### Redis
```bash
# Redis CLI 접근
kubectl port-forward svc/redis-master -n dev-env 6379:6379
redis-cli -h localhost -a dev-password
```

### PostgreSQL
```bash
# PostgreSQL 접근
kubectl port-forward svc/postgresql -n dev-env 5432:5432
psql -h localhost -U postgres -d dev_db
# Password: postgres-password
```

### Mailhog (Web UI)
```bash
# 웹 UI 접근
kubectl port-forward svc/mailhog -n dev-env 8025:8025
# 브라우저에서 http://localhost:8025 열기
```

### MinIO (S3 호환 스토리지)
```bash
# MinIO 콘솔 접근
kubectl port-forward svc/minio -n dev-env 9000:9000 9001:9001
# 브라우저에서 http://localhost:9001 열기
# Username: minioadmin
# Password: minioadmin
```

## 애플리케이션 연동 예제

### Python 애플리케이션에서 사용

```python
import redis
import psycopg2
from minio import Minio

# Redis 연결
r = redis.Redis(host='redis-master.dev-env.svc.cluster.local', port=6379, password='dev-password')
r.set('key', 'value')

# PostgreSQL 연결
conn = psycopg2.connect(
    host='postgresql.dev-env.svc.cluster.local',
    database='dev_db',
    user='postgres',
    password='postgres-password'
)

# MinIO 연결
minio_client = Minio(
    'minio.dev-env.svc.cluster.local:9000',
    access_key='minioadmin',
    secret_key='minioadmin',
    secure=False
)
```

### Node.js 애플리케이션에서 사용

```javascript
const redis = require('redis');
const { Client } = require('pg');
const Minio = require('minio');

// Redis
const redisClient = redis.createClient({
  host: 'redis-master.dev-env.svc.cluster.local',
  port: 6379,
  password: 'dev-password'
});

// PostgreSQL
const pgClient = new Client({
  host: 'postgresql.dev-env.svc.cluster.local',
  port: 5432,
  database: 'dev_db',
  user: 'postgres',
  password: 'postgres-password'
});

// MinIO
const minioClient = new Minio.Client({
  endPoint: 'minio.dev-env.svc.cluster.local',
  port: 9000,
  useSSL: false,
  accessKey: 'minioadmin',
  secretKey: 'minioadmin'
});
```

## 정리

```bash
# 전체 환경 삭제
sbkube delete --app-dir .

# 또는
kubectl delete namespace dev-env
```

## 운영 환경 전환

이 예제는 개발 환경용으로 persistence가 비활성화되어 있습니다.
운영 환경에서는 다음 사항을 변경하세요:

1. **Persistence 활성화**
```yaml
persistence:
  enabled: true
  size: 10Gi
  storageClass: "local-path"
```

2. **리소스 제한 강화**
```yaml
resources:
  limits:
    memory: 2Gi
    cpu: 1000m
```

3. **보안 강화**
- 강력한 비밀번호 사용
- Kubernetes Secret으로 민감 정보 관리
- NetworkPolicy 적용

## ⚠️ 보안 경고 (Security Warning)

**이 개발 환경 예제는 데모 목적으로 하드코딩된 인증 정보를 사용합니다.**

**프로덕션 환경에서는 절대 사용하지 마세요!**

### 예제에 포함된 하드코딩된 인증 정보

**Redis** (`manifests/redis.yaml`):
- 비밀번호 없음 (기본 설정)

**PostgreSQL** (`manifests/postgresql.yaml`):
- Database: `devdb`
- User: `devuser`
- Password: `devpassword`

**LocalStack** (`manifests/localstack.yaml`):
- AWS 에뮬레이터 (인증 불필요)

**Mailhog** (Helm chart):
- 인증 불필요 (테스트 도구)

### 프로덕션 환경 권장 사항

1. **Kubernetes Secrets 사용**:
   ```bash
   # PostgreSQL 인증 정보를 Secret으로 생성
   kubectl create secret generic postgresql-credentials \
     --namespace dev-env \
     --from-literal=username=produser \
     --from-literal=password=$(openssl rand -base64 32) \
     --from-literal=database=proddb

   # Redis 비밀번호 Secret 생성
   kubectl create secret generic redis-credentials \
     --namespace dev-env \
     --from-literal=password=$(openssl rand -base64 32)
   ```

2. **External Secrets Operator 사용**:
   - AWS Secrets Manager 연동
   - GCP Secret Manager 연동
   - Azure Key Vault 연동
   - HashiCorp Vault 연동

3. **환경별 분리 및 보안 설정**:
   - 개발/스테이징/프로덕션 별도 네임스페이스
   - NetworkPolicy로 트래픽 제한
   - RBAC로 접근 권한 관리
   - 정기적인 비밀번호 로테이션

4. **감사 및 모니터링**:
   - 접근 로그 기록
   - 이상 행위 탐지
   - 보안 스캔 정기 실행

자세한 내용은 다음 문서를 참조하세요:
- [Kubernetes Secrets 문서](https://kubernetes.io/docs/concepts/configuration/secret/)
- [External Secrets Operator](https://external-secrets.io/)
- [Network Policies](https://kubernetes.io/docs/concepts/services-networking/network-policies/)

## 관련 예제

- [Use Case 02: Production Web Stack](../02-web-stack/)
- [Use Case 03: Monitoring Stack](../03-monitoring/)
