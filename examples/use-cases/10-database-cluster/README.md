# Use Case: Database Cluster (PostgreSQL HA)

PostgreSQL 고가용성 클러스터 구성 예제입니다 (CloudNativePG).

## 📋 개요

**카테고리**: Use Cases

**구성 요소**:
- **PostgreSQL HA** (Primary-Standby Replication)
- **Pgpool-II** (Connection Pooling & Load Balancing)
- **Streaming Replication** (자동 복제)
- **Automatic Failover** (장애 자동 복구)

**학습 목표**:
- PostgreSQL 고가용성 아키텍처
- 읽기/쓰기 분산
- 장애 복구 자동화
- 연결 풀링

## 🎯 사용 사례

### 1. 고가용성 (High Availability)
```
Primary DB (Write)
   ↓ Replication
Standby DB 1 (Read)
Standby DB 2 (Read)

Primary 장애 → Standby 자동 승격
```

### 2. 읽기 확장 (Read Scaling)
```
App → Pgpool → Primary (Write)
              → Standby 1 (Read)
              → Standby 2 (Read)
```

## 🚀 빠른 시작

```bash
# PostgreSQL HA 클러스터 배포
sbkube apply \
  --app-dir examples/use-cases/10-database-cluster \
  --namespace db-cluster

# 배포 확인
kubectl get pods -n db-cluster
kubectl get pvc -n db-cluster

# 클러스터 상태 확인
kubectl exec -it postgresql-ha-postgresql-0 -n db-cluster -- repmgr cluster show

# Pgpool 접속 (연결 풀링)
kubectl port-forward -n db-cluster svc/postgresql-ha-pgpool 5432:5432 &
psql -h localhost -U postgres -d postgres
```

## 📖 PostgreSQL HA 설정

### 1. 아키텍처

```
┌─────────────────────────────────────┐
│        Pgpool-II Service            │
│    (Load Balancer & Connection Pool)│
└───────────┬─────────────────────────┘
            │
    ┌───────┼───────┐
    ↓       ↓       ↓
┌─────┐ ┌─────┐ ┌─────┐
│ Pri │→│Stby1│→│Stby2│
│mary │ │     │ │     │
└─────┘ └─────┘ └─────┘
  PVC     PVC     PVC
```

### 2. Replication 설정

**Streaming Replication** (자동):
- Primary → Standby 실시간 복제
- WAL (Write-Ahead Logging) 전송
- Hot Standby (읽기 가능)

**확인 명령어**:
```bash
# Replication 상태 확인
kubectl exec -it postgresql-ha-postgresql-0 -n db-cluster -- \
  psql -U postgres -c "SELECT * FROM pg_stat_replication;"

# Standby 상태 확인
kubectl exec -it postgresql-ha-postgresql-1 -n db-cluster -- \
  psql -U postgres -c "SELECT pg_is_in_recovery();"
```

### 3. Failover 테스트

**수동 Failover**:
```bash
# Primary Pod 삭제 (장애 시뮬레이션)
kubectl delete pod postgresql-ha-postgresql-0 -n db-cluster

# Standby가 자동으로 Primary로 승격
kubectl logs postgresql-ha-postgresql-1 -n db-cluster

# 클러스터 상태 확인
kubectl exec -it postgresql-ha-postgresql-1 -n db-cluster -- \
  repmgr cluster show
```

## 🎓 학습 포인트

### 1. Pgpool-II 기능

**Connection Pooling**:
- 연결 재사용 → DB 부하 감소
- 최대 연결 수 제한

**Load Balancing**:
- 읽기 쿼리 → Standby로 분산
- 쓰기 쿼리 → Primary로 전송

**Health Check**:
- DB 노드 자동 감지
- 장애 노드 자동 제외

### 2. 데이터 일관성

**동기 복제 vs 비동기 복제**:
```yaml
# 동기 복제 (Synchronous) - 느리지만 안전
postgresql:
  synchronousCommit: "on"
  numSynchronousReplicas: 1

# 비동기 복제 (Asynchronous) - 빠르지만 데이터 손실 가능
postgresql:
  synchronousCommit: "off"
```

### 3. 백업 전략

**자동 백업 (pgBackRest)**:
```bash
# 풀 백업
kubectl exec -it postgresql-ha-postgresql-0 -n db-cluster -- \
  pg_basebackup -D /tmp/backup -Ft -z -P

# PITR (Point-In-Time Recovery) 설정
# config.yaml에 archive_mode: on
```

## 💡 실전 패턴

### 애플리케이션 연결 설정

**Write (Primary)**:
```yaml
env:
- name: DB_HOST
  value: "postgresql-ha-pgpool.db-cluster.svc.cluster.local"
- name: DB_PORT
  value: "5432"
- name: DB_USER
  value: "postgres"
```

**Read (Standby)**:
```yaml
env:
- name: DB_READ_HOST
  value: "postgresql-ha-postgresql-read.db-cluster.svc.cluster.local"
```

### 모니터링

```bash
# 연결 수 확인
kubectl exec -it postgresql-ha-postgresql-0 -n db-cluster -- \
  psql -U postgres -c "SELECT count(*) FROM pg_stat_activity;"

# 복제 지연 확인
kubectl exec -it postgresql-ha-postgresql-0 -n db-cluster -- \
  psql -U postgres -c "SELECT * FROM pg_stat_replication;"
```

## 🔍 트러블슈팅

### 문제: Standby가 복제되지 않음

**확인**:
```bash
# Replication Slot 확인
kubectl exec -it postgresql-ha-postgresql-0 -n db-cluster -- \
  psql -U postgres -c "SELECT * FROM pg_replication_slots;"

# WAL 송신 상태 확인
kubectl exec -it postgresql-ha-postgresql-0 -n db-cluster -- \
  psql -U postgres -c "SELECT * FROM pg_stat_wal_receiver;"
```

### 문제: Pgpool 연결 실패

**확인**:
```bash
# Pgpool 로그
kubectl logs -n db-cluster deployment/postgresql-ha-pgpool

# Backend 노드 상태
kubectl exec -it postgresql-ha-pgpool-<pod> -n db-cluster -- \
  pcp_node_info -h localhost -U postgres
```

## 📚 참고 자료

- [CloudNativePG Documentation](https://cloudnative-pg.io/)
- [PostgreSQL Replication](https://www.postgresql.org/docs/current/high-availability.html)

## 🧹 정리

```bash
kubectl delete namespace db-cluster
```

---

**PostgreSQL HA로 안정적인 데이터베이스를 구축하세요! 🐘**
