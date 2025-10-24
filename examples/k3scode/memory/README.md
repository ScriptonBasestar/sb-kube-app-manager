# Memory - 인메모리 데이터 스토어 배포

Redis와 Memcached 인메모리 데이터 스토어를 SBKube로 배포하는 예제입니다.

## 📋 목차

- [개요](#-개요)
- [배포 애플리케이션](#-배포-애플리케이션)
- [설정 상세](#-설정-상세)
- [배포 방법](#-배포-방법)
- [사용 예제](#-사용-예제)
- [운영 가이드](#-운영-가이드)

---

## 🎯 개요

이 예제는 k3scode 프로젝트의 **메모리 스토어 레이어**로, 다음 애플리케이션을 배포합니다:

| 애플리케이션 | 타입 | 차트 | 용도 |
|------------|------|------|------|
| **Redis** | helm | bitnami/redis | 키-값 스토어, 캐싱, 세션 관리 |
| **Memcached** | helm | bitnami/memcached | 분산 메모리 캐싱 |

**네임스페이스**: `data`

---

## 📦 배포 애플리케이션

### 1. Redis

**설정 파일**: [values/redis.yaml](values/redis.yaml)

#### 주요 설정

```yaml
architecture: standalone      # 단일 인스턴스 모드

image:
  repository: bitnami/redis
  tag: 7.2-debian-12         # Redis 7.2

auth:
  password: 'passw0rd'       # ⚠️ 프로덕션에서는 변경 필수!

metrics:
  enabled: true              # Prometheus 메트릭 활성화

master:
  persistence:
    enabled: true            # 데이터 영속성 활성화
    size: 1Gi               # 볼륨 크기
```

#### 특징

- **단일 인스턴스**: 간단한 개발/테스트 환경
- **영속성**: PVC를 통한 데이터 보존
- **메트릭**: Prometheus 모니터링 지원
- **인증**: 비밀번호 기반 접근 제어

### 2. Memcached

**설정 파일**: [values/memcached.yaml](values/memcached.yaml)

#### 주요 설정

```yaml
architecture: standalone      # 단일 인스턴스 모드

auth:
  enabled: false             # 인증 비활성화 (기본)
  username: "user01"
  password: "passw0rd"

metrics:
  enabled: true              # Prometheus 메트릭 활성화

persistence:
  enabled: true              # 영속성 활성화
  size: 1Gi
```

#### 특징

- **인증 옵션**: 필요 시 SASL 인증 활성화 가능
- **영속성**: 재시작 시 데이터 보존 (선택적)
- **메트릭**: Prometheus 모니터링 지원

---

## ⚙️ 설정 상세

### config.yaml

```yaml
namespace: data

apps:
  redis:
    type: helm
    chart: bitnami/redis
    values:
      - redis.yaml

  memcached:
    type: helm
    chart: bitnami/memcached
    values:
      - memcached.yaml
```

### 공통 소스 (../sources.yaml)

```yaml
helm_repos:
  bitnami: https://charts.bitnami.com/bitnami
```

---

## 🚀 배포 방법

### 전체 배포 (Redis + Memcached)

```bash
cd examples/k3scode

# 통합 배포
sbkube apply --base-dir . --app-dir memory
```

**실행 과정**:
1. Bitnami Helm 리포지토리 추가 (prepare)
2. Redis 및 Memcached 차트 다운로드 (build)
3. values.yaml로 템플릿 렌더링 (template)
4. `data` 네임스페이스에 배포 (deploy)

### 개별 배포

#### Redis만 배포

```yaml
# config.yaml에서 memcached 비활성화
apps:
  redis:
    type: helm
    chart: bitnami/redis
    values:
      - redis.yaml

  memcached:
    enabled: false
```

```bash
sbkube apply --base-dir . --app-dir memory
```

#### Memcached만 배포

```yaml
# config.yaml에서 redis 비활성화
apps:
  redis:
    enabled: false

  memcached:
    type: helm
    chart: bitnami/memcached
    values:
      - memcached.yaml
```

---

## 🔍 배포 확인

### Helm 릴리스 확인

```bash
helm list -n data
```

**예상 출력**:
```
NAME        NAMESPACE  REVISION  STATUS    CHART              APP VERSION
redis       data       1         deployed  redis-17.13.2      7.2.0
memcached   data       1         deployed  memcached-7.0.5    1.6.22
```

### Pod 상태 확인

```bash
kubectl get pods -n data
```

**예상 출력**:
```
NAME                         READY   STATUS    RESTARTS   AGE
redis-master-0               1/1     Running   0          2m
memcached-0                  1/1     Running   0          2m
```

### Service 확인

```bash
kubectl get svc -n data
```

**예상 출력**:
```
NAME                TYPE        CLUSTER-IP      PORT(S)
redis-master        ClusterIP   10.43.100.1     6379/TCP
redis-headless      ClusterIP   None            6379/TCP
memcached           ClusterIP   10.43.100.2     11211/TCP
```

### PVC 확인

```bash
kubectl get pvc -n data
```

**예상 출력**:
```
NAME                      STATUS   VOLUME    CAPACITY   ACCESS MODES
redis-data-redis-master-0 Bound    pvc-xxx   1Gi        RWO
data-memcached-0          Bound    pvc-yyy   1Gi        RWO
```

---

## 💻 사용 예제

### Redis 접속

#### 클러스터 내부에서

```bash
# Redis CLI 실행
kubectl exec -it -n data redis-master-0 -- redis-cli

# 인증
auth passw0rd

# 테스트
SET mykey "Hello Redis"
GET mykey
```

#### 애플리케이션에서

**Python 예제**:
```python
import redis

r = redis.Redis(
    host='redis-master.data.svc.cluster.local',
    port=6379,
    password='passw0rd',
    decode_responses=True
)

r.set('user:1000', 'John Doe')
print(r.get('user:1000'))
```

**Node.js 예제**:
```javascript
const redis = require('redis');

const client = redis.createClient({
  host: 'redis-master.data.svc.cluster.local',
  port: 6379,
  password: 'passw0rd'
});

client.set('session:abc123', JSON.stringify({ user: 'admin' }));
client.get('session:abc123', (err, value) => {
  console.log(JSON.parse(value));
});
```

### Memcached 접속

#### 클러스터 내부에서

```bash
# Telnet으로 접속
kubectl exec -it -n data memcached-0 -- sh
telnet localhost 11211

# 테스트
set mykey 0 0 5
hello
get mykey
```

#### 애플리케이션에서

**Python 예제**:
```python
import pymemcache

client = pymemcache.Client(
    ('memcached.data.svc.cluster.local', 11211)
)

client.set('page:home', 'Cached HTML content')
print(client.get('page:home'))
```

**Node.js 예제**:
```javascript
const Memcached = require('memcached');

const memcached = new Memcached('memcached.data.svc.cluster.local:11211');

memcached.set('user:1000', { name: 'John' }, 3600, (err) => {
  memcached.get('user:1000', (err, data) => {
    console.log(data);
  });
});
```

---

## 🛠️ 운영 가이드

### 비밀번호 변경

#### Redis 비밀번호 변경

**1. values/redis.yaml 수정**:
```yaml
auth:
  password: 'new-secure-password'
```

**2. 재배포**:
```bash
sbkube apply --base-dir . --app-dir memory
```

#### Memcached 인증 활성화

**values/memcached.yaml 수정**:
```yaml
auth:
  enabled: true
  username: "memcache_user"
  password: "secure-password"
```

### 스케일링

#### Redis Replication 활성화

**values/redis.yaml 수정**:
```yaml
architecture: replication  # standalone → replication

master:
  count: 1

replica:
  replicaCount: 2         # 복제본 2개
```

#### Memcached 확장

**values/memcached.yaml 수정**:
```yaml
replicaCount: 3          # 3개 인스턴스
```

### 모니터링

#### Prometheus 메트릭 수집

```yaml
# values/redis.yaml
metrics:
  enabled: true
  serviceMonitor:
    enabled: true         # ServiceMonitor 생성 (Prometheus Operator)
```

#### Grafana 대시보드

- **Redis**: [Dashboard 11835](https://grafana.com/grafana/dashboards/11835)
- **Memcached**: [Dashboard 37](https://grafana.com/grafana/dashboards/37)

### 백업 및 복구

#### Redis 데이터 백업

```bash
# RDB 파일 백업
kubectl exec -n data redis-master-0 -- redis-cli -a passw0rd SAVE
kubectl cp data/redis-master-0:/data/dump.rdb ./backup-redis-$(date +%Y%m%d).rdb
```

#### Redis 데이터 복구

```bash
# RDB 파일 복사
kubectl cp ./backup-redis-20251024.rdb data/redis-master-0:/data/dump.rdb

# Redis 재시작
kubectl delete pod -n data redis-master-0
```

### 리소스 제한 설정

```yaml
# values/redis.yaml
master:
  resources:
    limits:
      cpu: 500m
      memory: 512Mi
    requests:
      cpu: 250m
      memory: 256Mi

# values/memcached.yaml
resources:
  limits:
    cpu: 250m
    memory: 256Mi
  requests:
    cpu: 100m
    memory: 128Mi
```

---

## ⚠️ 주의사항

### 1. 비밀번호 보안

**⚠️ 중요**: 기본 비밀번호(`passw0rd`)는 프로덕션에서 **절대 사용 금지**!

**권장 방법**:
```bash
# 강력한 비밀번호 생성
openssl rand -base64 32

# Kubernetes Secret 사용
kubectl create secret generic redis-password \
  --from-literal=password=$(openssl rand -base64 32) \
  -n data
```

**values/redis.yaml**:
```yaml
auth:
  existingSecret: redis-password
  existingSecretPasswordKey: password
```

### 2. 영속성 주의사항

- **Memcached**: 본래 휘발성 캐시이므로 영속성은 선택적
- **Redis**: 중요 데이터는 AOF(Append-Only File)도 활성화 권장

```yaml
# values/redis.yaml
master:
  persistence:
    enabled: true
  appendonly: yes           # AOF 활성화
```

### 3. 네트워크 정책

**클러스터 내부 접근만 허용**:
```yaml
# networkpolicy.yaml (별도 생성)
apiVersion: networking.k8s.io/v1
kind: NetworkPolicy
metadata:
  name: redis-policy
  namespace: data
spec:
  podSelector:
    matchLabels:
      app.kubernetes.io/name: redis
  ingress:
  - from:
    - namespaceSelector:
        matchLabels:
          app-tier: backend  # backend 네임스페이스만 허용
    ports:
    - port: 6379
```

---

## 🔄 삭제

```bash
# 전체 삭제
sbkube delete --base-dir . --app-dir memory --namespace data

# 또는 Helm으로 직접 삭제
helm uninstall redis -n data
helm uninstall memcached -n data
```

**⚠️ 주의**: PVC는 자동 삭제되지 않으므로 수동 삭제 필요
```bash
kubectl delete pvc -n data --all
```

---

## 📚 참고 자료

- [k3scode 프로젝트 개요](../README.md)
- [Redis Bitnami 차트](https://github.com/bitnami/charts/tree/main/bitnami/redis)
- [Memcached Bitnami 차트](https://github.com/bitnami/charts/tree/main/bitnami/memcached)
- [Redis 공식 문서](https://redis.io/docs/)
- [Memcached 위키](https://github.com/memcached/memcached/wiki)

---

## 🔗 관련 예제

- [RDB - 관계형 데이터베이스](../rdb/README.md) - PostgreSQL, MariaDB
- [DevOps - 개발 도구](../devops/README.md) - Nexus, ProxyND
- [AI - AI/ML 인프라](../ai/README.md) - Toolhive Operator

---

**💡 팁**: 캐싱 레이어는 애플리케이션 성능에 직접적인 영향을 줍니다. 적절한 리소스 할당과 모니터링이 중요합니다.
