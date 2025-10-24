# State Management - 배포 상태 관리

SBKube의 **state**, **history**, **rollback** 명령어를 사용한 배포 상태 관리 예제입니다.

## 📋 목차

- [개요](#-개요)
- [상태 관리 명령어](#-상태-관리-명령어)
- [사용 시나리오](#-사용-시나리오)
- [실전 워크플로우](#-실전-워크플로우)
- [상태 데이터베이스](#-상태-데이터베이스)
- [고급 사용법](#-고급-사용법)

---

## 🎯 개요

SBKube는 배포 히스토리를 **SQLite 데이터베이스**에 저장하여 다음 기능을 제공합니다:

- 📊 **state list**: 모든 배포 상태 조회
- 📜 **state history**: 특정 앱/네임스페이스의 배포 히스토리
- ↩️ **rollback**: 이전 버전으로 롤백
- 🔍 **state show**: 특정 배포 상세 정보

---

## 🔧 상태 관리 명령어

### 1. state list

**용도**: 모든 배포 상태 조회

```bash
sbkube state list
```

**출력 예시**:
```
NAMESPACE    APP     REVISION  STATUS    DEPLOYED AT          CHART
state-demo   redis   1         deployed  2025-10-24 10:00:00  redis-17.13.2
state-demo   redis   2         deployed  2025-10-24 11:00:00  redis-17.13.2
state-demo   redis   3         deployed  2025-10-24 12:00:00  redis-18.0.0
```

**옵션**:
```bash
# 특정 네임스페이스만
sbkube state list --namespace state-demo

# 특정 앱만
sbkube state list --app redis

# JSON 형식 출력
sbkube state list --format json
```

### 2. state history

**용도**: 특정 앱/네임스페이스의 배포 히스토리 조회

```bash
sbkube state history --namespace state-demo --app redis
```

**출력 예시**:
```
REVISION  DEPLOYED AT          STATUS    CHART          DESCRIPTION
1         2025-10-24 10:00:00  deployed  redis-17.13.2  Initial deployment
2         2025-10-24 11:00:00  deployed  redis-17.13.2  Updated values
3         2025-10-24 12:00:00  deployed  redis-18.0.0   Upgraded to 18.0.0
```

**옵션**:
```bash
# 최근 5개만
sbkube state history --namespace state-demo --app redis --limit 5

# 특정 날짜 이후
sbkube state history --namespace state-demo --app redis --since "2025-10-24"
```

### 3. rollback

**용도**: 이전 버전으로 롤백

```bash
sbkube rollback --namespace state-demo --app redis --revision 2
```

**실행 과정**:
```
1. Revision 2의 설정 가져오기
2. Helm rollback 실행
3. 새로운 Revision 4 생성 (Revision 2의 내용)
```

**옵션**:
```bash
# Dry-run 모드
sbkube rollback --namespace state-demo --app redis --revision 2 --dry-run

# 강제 롤백 (Pod 재생성)
sbkube rollback --namespace state-demo --app redis --revision 2 --force
```

### 4. state show

**용도**: 특정 배포의 상세 정보

```bash
sbkube state show --namespace state-demo --app redis --revision 3
```

**출력 예시**:
```yaml
namespace: state-demo
app: redis
revision: 3
status: deployed
chart: redis-18.0.0
deployed_at: 2025-10-24 12:00:00
values:
  architecture: standalone
  auth:
    password: state-demo-v3
  master:
    persistence:
      size: 2Gi
```

---

## 🚀 사용 시나리오

### 시나리오 1: 배포 후 상태 확인

```bash
cd examples/state-management

# 1. 배포
sbkube apply

# 2. 상태 확인
sbkube state list
```

**출력**:
```
NAMESPACE    APP     REVISION  STATUS    DEPLOYED AT
state-demo   redis   1         deployed  2025-10-24 10:00:00
```

### 시나리오 2: 값 변경 후 재배포

```bash
# 1. values/redis.yaml 수정
# password: "state-demo-v1" → "state-demo-v2"

# 2. 재배포
sbkube apply

# 3. 히스토리 확인
sbkube state history --namespace state-demo --app redis
```

**출력**:
```
REVISION  DEPLOYED AT          DESCRIPTION
1         2025-10-24 10:00:00  Initial deployment (v1)
2         2025-10-24 11:00:00  Updated password (v2)
```

### 시나리오 3: 차트 버전 업그레이드

```bash
# 1. config.yaml 수정
# version: 17.13.2 → version: 18.0.0

# 2. 재배포
sbkube apply --force  # 차트 재다운로드 필요

# 3. 히스토리 확인
sbkube state history --namespace state-demo --app redis
```

**출력**:
```
REVISION  DEPLOYED AT          CHART          DESCRIPTION
1         2025-10-24 10:00:00  redis-17.13.2  Initial deployment
2         2025-10-24 11:00:00  redis-17.13.2  Updated values
3         2025-10-24 12:00:00  redis-18.0.0   Upgraded chart
```

### 시나리오 4: 문제 발생 시 롤백

```bash
# 3번 배포 후 문제 발생!

# 1. 이전 버전으로 롤백 (Revision 2)
sbkube rollback --namespace state-demo --app redis --revision 2

# 2. 롤백 확인
sbkube state history --namespace state-demo --app redis
```

**출력**:
```
REVISION  DEPLOYED AT          CHART          DESCRIPTION
1         2025-10-24 10:00:00  redis-17.13.2  Initial deployment
2         2025-10-24 11:00:00  redis-17.13.2  Updated values
3         2025-10-24 12:00:00  redis-18.0.0   Upgraded chart (FAILED)
4         2025-10-24 12:05:00  redis-17.13.2  Rollback to revision 2
```

---

## 💡 실전 워크플로우

### 워크플로우 1: Blue-Green 배포 패턴

```bash
# 1. 현재 버전 확인 (Blue)
sbkube state list --namespace production --app myapp

# 2. 새 버전 배포 (Green)
# config.yaml 수정 후
sbkube apply --namespace production

# 3. 테스트
curl http://myapp.production.svc.cluster.local/health

# 4. 문제 있으면 즉시 롤백
sbkube rollback --namespace production --app myapp --revision $(previous_revision)

# 5. 문제 없으면 유지
echo "Green deployment successful"
```

### 워크플로우 2: Canary 배포 패턴

```bash
# 1. 기존 버전 확인
sbkube state show --namespace production --app backend --revision current

# 2. Canary 배포 (일부만)
# config.yaml에서 replicaCount: 10 → 2 (20%)
sbkube apply --namespace production-canary

# 3. 모니터링
# 문제 발견 시 즉시 삭제
sbkube delete --namespace production-canary

# 4. 문제 없으면 전체 배포
# config.yaml에서 replicaCount: 2 → 10
sbkube apply --namespace production

# 5. 이전 버전 제거
sbkube rollback --namespace production --app backend --revision $(old_revision)
```

### 워크플로우 3: 정기 백업 및 복구

```bash
# 정기 백업 (cron job)
# /usr/local/bin/sbkube-backup.sh
#!/bin/bash
DATE=$(date +%Y%m%d)

# 상태 데이터베이스 백업
cp ~/.sbkube/state.db /backup/sbkube-state-$DATE.db

# 히스토리 export
sbkube state list --format json > /backup/sbkube-history-$DATE.json
```

**복구**:
```bash
# 1. 데이터베이스 복원
cp /backup/sbkube-state-20251024.db ~/.sbkube/state.db

# 2. 특정 리비전으로 롤백
sbkube rollback --namespace production --app myapp --revision 10
```

---

## 🗄️ 상태 데이터베이스

### 데이터베이스 위치

```bash
# 기본 위치
~/.sbkube/state.db
```

### 스키마 구조 (예상)

```sql
-- deployments 테이블
CREATE TABLE deployments (
  id INTEGER PRIMARY KEY AUTOINCREMENT,
  namespace TEXT NOT NULL,
  app TEXT NOT NULL,
  revision INTEGER NOT NULL,
  chart TEXT,
  status TEXT,
  deployed_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
  config TEXT,  -- JSON 형식의 설정
  UNIQUE(namespace, app, revision)
);

-- deployment_history 테이블
CREATE TABLE deployment_history (
  id INTEGER PRIMARY KEY AUTOINCREMENT,
  deployment_id INTEGER,
  action TEXT,  -- deploy, upgrade, rollback, delete
  timestamp TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
  user TEXT,
  description TEXT,
  FOREIGN KEY(deployment_id) REFERENCES deployments(id)
);
```

### 직접 조회 (SQLite CLI)

```bash
# 데이터베이스 열기
sqlite3 ~/.sbkube/state.db

# 모든 배포 조회
SELECT * FROM deployments;

# 특정 네임스페이스의 히스토리
SELECT * FROM deployments WHERE namespace = 'state-demo' ORDER BY deployed_at DESC;

# 롤백 히스토리 조회
SELECT * FROM deployment_history WHERE action = 'rollback';
```

---

## 🛠️ 고급 사용법

### 1. 다중 네임스페이스 관리

```bash
# 모든 네임스페이스의 상태
sbkube state list

# 네임스페이스별 필터링
sbkube state list --namespace production
sbkube state list --namespace staging
sbkube state list --namespace development
```

### 2. 배포 비교

```bash
# Revision 2와 3 비교
sbkube state show --namespace state-demo --app redis --revision 2 > rev2.yaml
sbkube state show --namespace state-demo --app redis --revision 3 > rev3.yaml
diff rev2.yaml rev3.yaml
```

### 3. 자동 롤백 스크립트

```bash
#!/bin/bash
# auto-rollback.sh

NAMESPACE=$1
APP=$2
HEALTH_CHECK_URL=$3

# 배포 전 리비전 저장
PREVIOUS_REVISION=$(sbkube state history --namespace $NAMESPACE --app $APP --limit 1 | tail -1 | awk '{print $1}')

# 배포
sbkube apply --namespace $NAMESPACE

# 헬스 체크 (5분 대기)
sleep 300
if ! curl -f $HEALTH_CHECK_URL; then
  echo "Health check failed, rolling back..."
  sbkube rollback --namespace $NAMESPACE --app $APP --revision $PREVIOUS_REVISION
fi
```

**사용**:
```bash
./auto-rollback.sh state-demo redis http://redis.state-demo.svc.cluster.local/health
```

### 4. 히스토리 정리

```bash
# 오래된 리비전 삭제 (수동)
# 데이터베이스에서 직접 삭제
sqlite3 ~/.sbkube/state.db "DELETE FROM deployments WHERE deployed_at < '2025-01-01';"

# 또는 SBKube 명령어 (v0.5.0+)
# sbkube state prune --older-than 30d
```

---

## ⚠️ 주의사항

### 1. 롤백 vs Helm 롤백

**SBKube rollback**:
```bash
sbkube rollback --namespace state-demo --app redis --revision 2
```
- SBKube 상태 데이터베이스 기반
- config.yaml과 values 파일 정보 사용

**Helm rollback**:
```bash
helm rollback redis 2 -n state-demo
```
- Helm 자체 히스토리 기반
- Helm 릴리스 정보만 사용

**권장**: SBKube rollback 사용 (일관성 유지)

### 2. 데이터베이스 백업 필수

**백업 위치**:
```bash
cp ~/.sbkube/state.db ~/backup/state.db.$(date +%Y%m%d)
```

**자동 백업 (cron)**:
```cron
# 매일 새벽 3시 백업
0 3 * * * cp ~/.sbkube/state.db ~/backup/state.db.$(date +%Y%m%d)
```

### 3. 롤백 시 데이터 손실 위험

**StatefulSet (데이터베이스 등)**:
```bash
# ❌ 위험: 데이터 손실 가능
sbkube rollback --namespace state-demo --app postgres --revision 1

# ✅ 안전: 데이터 백업 먼저
kubectl exec -n state-demo postgres-0 -- pg_dump > backup.sql
sbkube rollback --namespace state-demo --app postgres --revision 1
```

### 4. 동시 배포 시 충돌

**문제**: 여러 사용자가 동시에 배포하면 상태 불일치 가능

**해결**: 배포 잠금 메커니즘 사용 (v0.5.0+)
```bash
# 배포 잠금
sbkube deploy --namespace production --lock

# 잠금 확인
sbkube state locks
```

---

## 📊 상태 모니터링

### Prometheus Exporter (계획)

```bash
# SBKube 상태를 Prometheus 메트릭으로 노출 (v0.6.0+)
sbkube state export-metrics --port 9090
```

**메트릭 예시**:
```
sbkube_deployments_total{namespace="state-demo",app="redis"} 3
sbkube_deployment_status{namespace="state-demo",app="redis",status="deployed"} 1
sbkube_last_deployment_time{namespace="state-demo",app="redis"} 1729756800
```

---

## 📚 참고 자료

- [SBKube 명령어 참조](../../docs/02-features/commands.md)
- [Helm Rollback 참조](https://helm.sh/docs/helm/helm_rollback/)
- [SQLite 공식 문서](https://www.sqlite.org/docs.html)

---

## 🔗 관련 예제

- [apply-workflow/](../apply-workflow/) - 통합 워크플로우
- [force-update/](../force-update/) - --force 옵션 사용

---

**💡 팁**: 프로덕션 환경에서는 배포 전에 항상 히스토리를 확인하고, 롤백 계획을 미리 세우세요. 상태 데이터베이스는 정기적으로 백업하세요.
