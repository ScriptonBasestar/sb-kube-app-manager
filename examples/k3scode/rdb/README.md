# RDB - 관계형 데이터베이스 배포

PostgreSQL과 MariaDB 관계형 데이터베이스를 SBKube로 배포하는 예제입니다.

## 📋 목차

- [개요](#-개요)
- [배포 애플리케이션](#-배포-애플리케이션)
- [설정 상세](#-설정-상세)
- [배포 방법](#-배포-방법)
- [사용 예제](#-사용-예제)
- [운영 가이드](#-운영-가이드)

---

## 🎯 개요

이 예제는 k3scode 프로젝트의 **관계형 데이터베이스 레이어**로, 다음 애플리케이션을 배포합니다:

| 애플리케이션 | 타입 | 차트 | 용도 |
|------------|------|------|------|
| **PostgreSQL** | helm | bitnami/postgresql | 고급 관계형 DB, ACID 트랜잭션 |
| **MariaDB** | helm | bitnami/mariadb | MySQL 호환 DB, 웹 애플리케이션 |

**네임스페이스**: `data`

---

## 📦 배포 애플리케이션

### 1. PostgreSQL

**차트**: `bitnami/postgresql`

#### 주요 기능

- **ACID 트랜잭션**: 완벽한 데이터 일관성
- **고급 기능**: JSON, Full-text search, GIS 지원
- **확장성**: 복제, 샤딩, 파티셔닝
- **표준 SQL**: SQL 표준 완벽 지원

#### 기본 설정 (예상)

```yaml
# values/postgresql.yaml (파일이 없으므로 기본값 사용)
auth:
  postgresPassword: changeme    # ⚠️ 변경 필수
  username: app_user
  password: app_password
  database: app_db

primary:
  persistence:
    enabled: true
    size: 8Gi

metrics:
  enabled: true
```

### 2. MariaDB

**차트**: `bitnami/mariadb`

#### 주요 기능

- **MySQL 호환**: MySQL 프로토콜 완전 호환
- **웹 애플리케이션**: WordPress, Drupal 등에 최적
- **빠른 성능**: 쿼리 최적화 및 캐싱
- **레플리케이션**: Master-Slave 복제 지원

#### 기본 설정 (예상)

```yaml
# values/mariadb.yaml (파일이 없으므로 기본값 사용)
auth:
  rootPassword: changeme        # ⚠️ 변경 필수
  username: app_user
  password: app_password
  database: app_db

primary:
  persistence:
    enabled: true
    size: 8Gi

metrics:
  enabled: true
```

---

## ⚙️ 설정 상세

### config.yaml

```yaml
namespace: data

apps:
  postgresql:
    type: helm
    chart: bitnami/postgresql
    values:
      - postgresql.yaml
    # overrides:
    #   - templates/pg-host-vol.yaml
    #   - templates/primary/statefulset.yaml
    # removes:
    #   - files/aaa.conf

  mariadb:
    type: helm
    chart: bitnami/mariadb
    values:
      - mariadb.yaml
    # overrides:
    #   - templates/mariadb-vol.yaml
    #   - templates/primary/statefulset.yaml
```

### 고급 기능

#### overrides (템플릿 오버라이드)

SBKube의 `overrides` 기능을 사용하면 Helm 차트의 템플릿을 직접 수정할 수 있습니다:

```yaml
apps:
  postgresql:
    overrides:
      - templates/pg-host-vol.yaml        # hostPath 볼륨 사용
      - templates/primary/statefulset.yaml # StatefulSet 커스터마이징
```

**예: hostPath 볼륨 사용**
```yaml
# templates/pg-host-vol.yaml
apiVersion: v1
kind: PersistentVolume
metadata:
  name: postgresql-data
spec:
  capacity:
    storage: 10Gi
  accessModes:
    - ReadWriteOnce
  hostPath:
    path: /data/postgresql
```

#### removes (파일 제거)

불필요한 설정 파일을 제거할 수 있습니다:

```yaml
apps:
  postgresql:
    removes:
      - files/aaa.conf  # 불필요한 설정 제거
```

### 공통 소스 (../sources.yaml)

```yaml
helm_repos:
  bitnami: https://charts.bitnami.com/bitnami
```

---

## 🚀 배포 방법

### 전체 배포 (PostgreSQL + MariaDB)

```bash
cd examples/k3scode

# 통합 배포
sbkube apply --base-dir . --app-dir rdb
```

**실행 과정**:
1. Bitnami Helm 리포지토리 추가 (prepare)
2. PostgreSQL 및 MariaDB 차트 다운로드 (build)
3. values.yaml로 템플릿 렌더링 (template)
4. `data` 네임스페이스에 배포 (deploy)

### 개별 배포

#### PostgreSQL만 배포

```yaml
# config.yaml에서 mariadb 비활성화
apps:
  postgresql:
    type: helm
    chart: bitnami/postgresql
    values:
      - postgresql.yaml

  mariadb:
    enabled: false
```

```bash
sbkube apply --base-dir . --app-dir rdb
```

#### MariaDB만 배포

```yaml
# config.yaml에서 postgresql 비활성화
apps:
  postgresql:
    enabled: false

  mariadb:
    type: helm
    chart: bitnami/mariadb
    values:
      - mariadb.yaml
```

---

## 🔍 배포 확인

### Helm 릴리스 확인

```bash
helm list -n data
```

**예상 출력**:
```
NAME        NAMESPACE  REVISION  STATUS    CHART                 APP VERSION
postgresql  data       1         deployed  postgresql-12.0.0     15.5.0
mariadb     data       1         deployed  mariadb-14.0.0        11.1.3
```

### Pod 상태 확인

```bash
kubectl get pods -n data
```

**예상 출력**:
```
NAME                READY   STATUS    RESTARTS   AGE
postgresql-0        1/1     Running   0          2m
mariadb-0           1/1     Running   0          2m
```

### Service 확인

```bash
kubectl get svc -n data
```

**예상 출력**:
```
NAME                 TYPE        CLUSTER-IP      PORT(S)
postgresql           ClusterIP   10.43.200.1     5432/TCP
postgresql-headless  ClusterIP   None            5432/TCP
mariadb              ClusterIP   10.43.200.2     3306/TCP
mariadb-headless     ClusterIP   None            3306/TCP
```

### PVC 확인

```bash
kubectl get pvc -n data
```

**예상 출력**:
```
NAME                   STATUS   VOLUME    CAPACITY   ACCESS MODES
data-postgresql-0      Bound    pvc-xxx   8Gi        RWO
data-mariadb-0         Bound    pvc-yyy   8Gi        RWO
```

---

## 💻 사용 예제

### PostgreSQL 접속

#### psql 클라이언트 사용

```bash
# Pod에서 직접 접속
kubectl exec -it -n data postgresql-0 -- psql -U postgres

# 비밀번호 입력 후
\l                # 데이터베이스 목록
\c app_db         # app_db로 전환
\dt               # 테이블 목록
```

#### 애플리케이션에서 연결

**Python (psycopg2)**:
```python
import psycopg2

conn = psycopg2.connect(
    host="postgresql.data.svc.cluster.local",
    port=5432,
    database="app_db",
    user="app_user",
    password="app_password"
)

cursor = conn.cursor()
cursor.execute("SELECT version();")
print(cursor.fetchone())
conn.close()
```

**Node.js (pg)**:
```javascript
const { Client } = require('pg');

const client = new Client({
  host: 'postgresql.data.svc.cluster.local',
  port: 5432,
  database: 'app_db',
  user: 'app_user',
  password: 'app_password'
});

client.connect();
client.query('SELECT NOW()', (err, res) => {
  console.log(res.rows[0]);
  client.end();
});
```

**Connection String**:
```
postgresql://app_user:app_password@postgresql.data.svc.cluster.local:5432/app_db
```

### MariaDB 접속

#### mysql 클라이언트 사용

```bash
# Pod에서 직접 접속
kubectl exec -it -n data mariadb-0 -- mysql -u root -p

# 비밀번호 입력 후
SHOW DATABASES;
USE app_db;
SHOW TABLES;
```

#### 애플리케이션에서 연결

**Python (pymysql)**:
```python
import pymysql

conn = pymysql.connect(
    host='mariadb.data.svc.cluster.local',
    port=3306,
    user='app_user',
    password='app_password',
    database='app_db'
)

cursor = conn.cursor()
cursor.execute("SELECT VERSION();")
print(cursor.fetchone())
conn.close()
```

**Node.js (mysql2)**:
```javascript
const mysql = require('mysql2');

const connection = mysql.createConnection({
  host: 'mariadb.data.svc.cluster.local',
  port: 3306,
  user: 'app_user',
  password: 'app_password',
  database: 'app_db'
});

connection.query('SELECT NOW()', (err, results) => {
  console.log(results[0]);
  connection.end();
});
```

**Connection String**:
```
mysql://app_user:app_password@mariadb.data.svc.cluster.local:3306/app_db
```

---

## 🛠️ 운영 가이드

### Values 파일 생성

현재 config.yaml은 values 파일을 참조하지만 파일이 없습니다. 다음과 같이 생성하세요:

#### values/postgresql.yaml

```yaml
auth:
  postgresPassword: changeme
  username: app_user
  password: app_password
  database: app_db

primary:
  persistence:
    enabled: true
    size: 8Gi

  resources:
    limits:
      cpu: 1000m
      memory: 1Gi
    requests:
      cpu: 500m
      memory: 512Mi

metrics:
  enabled: true
  serviceMonitor:
    enabled: true
```

#### values/mariadb.yaml

```yaml
auth:
  rootPassword: changeme
  username: app_user
  password: app_password
  database: app_db

primary:
  persistence:
    enabled: true
    size: 8Gi

  resources:
    limits:
      cpu: 1000m
      memory: 1Gi
    requests:
      cpu: 500m
      memory: 512Mi

metrics:
  enabled: true
  serviceMonitor:
    enabled: true
```

### 비밀번호 관리

#### Kubernetes Secret 사용 (권장)

```bash
# PostgreSQL 비밀번호 Secret 생성
kubectl create secret generic postgresql-password \
  --from-literal=postgres-password=$(openssl rand -base64 32) \
  --from-literal=password=$(openssl rand -base64 32) \
  -n data

# MariaDB 비밀번호 Secret 생성
kubectl create secret generic mariadb-password \
  --from-literal=mariadb-root-password=$(openssl rand -base64 32) \
  --from-literal=mariadb-password=$(openssl rand -base64 32) \
  -n data
```

**values/postgresql.yaml**:
```yaml
auth:
  existingSecret: postgresql-password
  secretKeys:
    adminPasswordKey: postgres-password
    userPasswordKey: password
```

**values/mariadb.yaml**:
```yaml
auth:
  existingSecret: mariadb-password
```

### 레플리케이션 설정

#### PostgreSQL Replication

```yaml
# values/postgresql.yaml
architecture: replication

readReplicas:
  replicaCount: 2
  persistence:
    enabled: true
    size: 8Gi
```

#### MariaDB Replication

```yaml
# values/mariadb.yaml
architecture: replication

secondary:
  replicaCount: 2
  persistence:
    enabled: true
    size: 8Gi
```

### 백업 및 복구

#### PostgreSQL 백업

```bash
# 데이터베이스 덤프
kubectl exec -n data postgresql-0 -- pg_dump -U postgres app_db > backup-postgres-$(date +%Y%m%d).sql

# 전체 클러스터 백업
kubectl exec -n data postgresql-0 -- pg_dumpall -U postgres > backup-postgres-all-$(date +%Y%m%d).sql
```

#### PostgreSQL 복구

```bash
# 백업 복사
kubectl cp backup-postgres-20251024.sql data/postgresql-0:/tmp/

# 복구
kubectl exec -n data postgresql-0 -- psql -U postgres app_db < /tmp/backup-postgres-20251024.sql
```

#### MariaDB 백업

```bash
# 데이터베이스 덤프
kubectl exec -n data mariadb-0 -- mysqldump -u root -p app_db > backup-mariadb-$(date +%Y%m%d).sql

# 전체 백업
kubectl exec -n data mariadb-0 -- mysqldump -u root -p --all-databases > backup-mariadb-all-$(date +%Y%m%d).sql
```

#### MariaDB 복구

```bash
# 백업 복사
kubectl cp backup-mariadb-20251024.sql data/mariadb-0:/tmp/

# 복구
kubectl exec -n data mariadb-0 -- mysql -u root -p app_db < /tmp/backup-mariadb-20251024.sql
```

### 모니터링

#### Prometheus 메트릭

```yaml
# PostgreSQL
metrics:
  enabled: true
  serviceMonitor:
    enabled: true

# MariaDB
metrics:
  enabled: true
  serviceMonitor:
    enabled: true
```

#### Grafana 대시보드

- **PostgreSQL**: [Dashboard 9628](https://grafana.com/grafana/dashboards/9628)
- **MariaDB**: [Dashboard 13106](https://grafana.com/grafana/dashboards/13106)

### 성능 튜닝

#### PostgreSQL

```yaml
# values/postgresql.yaml
primary:
  extendedConfiguration: |
    max_connections = 200
    shared_buffers = 256MB
    effective_cache_size = 1GB
    work_mem = 16MB
```

#### MariaDB

```yaml
# values/mariadb.yaml
primary:
  configuration: |
    [mysqld]
    max_connections=200
    innodb_buffer_pool_size=512M
    query_cache_size=32M
```

---

## ⚠️ 주의사항

### 1. 비밀번호 보안

**⚠️ 절대 금지**: 기본 비밀번호 사용
**권장**: Kubernetes Secret + 강력한 비밀번호

### 2. 데이터 영속성

**중요**: PVC 삭제 시 데이터 손실!

```bash
# ❌ 위험: PVC도 함께 삭제
kubectl delete pvc -n data --all

# ✅ 안전: PVC 보존
helm uninstall postgresql -n data  # PVC는 남음
```

### 3. 리소스 제한

**권장**: CPU/메모리 제한 설정

```yaml
resources:
  limits:
    cpu: 1000m
    memory: 2Gi
  requests:
    cpu: 500m
    memory: 1Gi
```

### 4. 네트워크 보안

**권장**: NetworkPolicy로 접근 제한

```yaml
# networkpolicy.yaml
apiVersion: networking.k8s.io/v1
kind: NetworkPolicy
metadata:
  name: db-policy
  namespace: data
spec:
  podSelector:
    matchLabels:
      app.kubernetes.io/name: postgresql
  ingress:
  - from:
    - namespaceSelector:
        matchLabels:
          app-tier: backend
    ports:
    - port: 5432
```

---

## 🔄 삭제

```bash
# 전체 삭제
sbkube delete --base-dir . --app-dir rdb --namespace data

# 또는 Helm으로 직접 삭제
helm uninstall postgresql -n data
helm uninstall mariadb -n data

# PVC 삭제 (주의: 데이터 손실!)
kubectl delete pvc -n data data-postgresql-0 data-mariadb-0
```

---

## 📚 참고 자료

- [k3scode 프로젝트 개요](../README.md)
- [PostgreSQL Bitnami 차트](https://github.com/bitnami/charts/tree/main/bitnami/postgresql)
- [MariaDB Bitnami 차트](https://github.com/bitnami/charts/tree/main/bitnami/mariadb)
- [PostgreSQL 공식 문서](https://www.postgresql.org/docs/)
- [MariaDB 공식 문서](https://mariadb.com/kb/en/)

---

## 🔗 관련 예제

- [Memory - 인메모리 스토어](../memory/README.md) - Redis, Memcached
- [DevOps - 개발 도구](../devops/README.md) - Nexus, ProxyND
- [AI - AI/ML 인프라](../ai/README.md) - Toolhive Operator

---

**💡 팁**: 관계형 데이터베이스는 애플리케이션의 핵심입니다. 백업, 모니터링, 보안에 특별히 신경 쓰세요.
