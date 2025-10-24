# Use Case: Backup & Restore (Velero)

Velero를 활용한 Kubernetes 클러스터 백업 및 복구 자동화 예제입니다.

## 📋 개요

**카테고리**: Use Cases

**구성 요소**:
- **Velero** (백업/복구 도구)
- **MinIO** (S3 호환 스토리지)
- **데모 앱** (백업 대상)
- **Schedule** (자동 백업)

**학습 목표**:
- Velero 백업/복구 워크플로우
- S3 스토리지 연동
- 스케줄 기반 자동 백업
- 네임스페이스/리소스 선택적 복구

## 🎯 사용 사례

### 1. 재해 복구 (Disaster Recovery)
```
Production Cluster → Velero Backup → S3
Disaster 발생 → Velero Restore → New Cluster
```

### 2. 클러스터 마이그레이션
```
Old Cluster → Backup → New Cluster → Restore
```

### 3. 주기적 스냅샷
```
Schedule: Daily 02:00 AM → Full Backup → S3
Retention: 30 days
```

## 🚀 빠른 시작

```bash
# Velero CLI 설치 (로컬 머신)
wget https://github.com/vmware-tanzu/velero/releases/download/v1.12.0/velero-v1.12.0-linux-amd64.tar.gz
tar -xvf velero-v1.12.0-linux-amd64.tar.gz
sudo mv velero-v1.12.0-linux-amd64/velero /usr/local/bin/

# SBKube로 Velero + MinIO + Demo App 배포
sbkube apply \
  --app-dir examples/use-cases/09-backup-restore \
  --namespace velero-demo

# MinIO 접속 정보 (테스트용)
kubectl port-forward -n velero svc/minio 9000:9000 &
# 브라우저: http://localhost:9000
# 액세스 키: minio / minio123
```

## 📖 Velero 사용법

### 1. 백업 생성

**전체 네임스페이스 백업**:
```bash
velero backup create demo-backup \
  --include-namespaces velero-demo

# 상태 확인
velero backup describe demo-backup
velero backup logs demo-backup
```

**리소스 타입별 백업**:
```bash
velero backup create deployments-only \
  --include-resources deployments,services \
  --include-namespaces velero-demo
```

**라벨 기반 백업**:
```bash
velero backup create app-backup \
  --selector app=critical
```

### 2. 백업 복구

**전체 복구**:
```bash
velero restore create --from-backup demo-backup

# 상태 확인
velero restore describe demo-backup-<timestamp>
```

**다른 네임스페이스로 복구**:
```bash
velero restore create --from-backup demo-backup \
  --namespace-mappings velero-demo:restored-demo
```

**선택적 복구**:
```bash
velero restore create --from-backup demo-backup \
  --include-resources deployments,configmaps
```

### 3. 스케줄 백업

**자동화된 백업 스케줄**:
```bash
# 매일 02:00 AM 백업 (30일 보관)
velero schedule create daily-backup \
  --schedule="0 2 * * *" \
  --ttl 720h0m0s

# 스케줄 확인
velero schedule get
```

## 🎓 학습 포인트

### 1. Velero 아키텍처

```
Velero Client (CLI)
       ↓
Velero Server (K8s Deployment)
       ↓
Restic (PV 백업)
       ↓
S3 Compatible Storage (MinIO)
```

### 2. 백업 대상

- **Kubernetes 리소스**: YAML 정의
- **Persistent Volumes**: 실제 데이터 (Restic)
- **Cluster-scoped 리소스**: StorageClass, ClusterRole 등

### 3. 백업 워크플로우

```bash
# 1. 백업 생성
velero backup create my-backup

# 2. 백업 상태 확인
velero backup get

# 3. 백업 삭제 (재해 시뮬레이션)
kubectl delete namespace velero-demo

# 4. 복구
velero restore create --from-backup my-backup

# 5. 복구 확인
kubectl get all -n velero-demo
```

## 💡 실전 패턴

### Persistent Volume 백업 (Restic)

```yaml
# Pod에 볼륨 백업 어노테이션 추가
apiVersion: v1
kind: Pod
metadata:
  annotations:
    backup.velero.io/backup-volumes: data,config
spec:
  volumes:
  - name: data
    persistentVolumeClaim:
      claimName: app-data
```

### Pre/Post Backup Hooks

```yaml
# 백업 전 DB 일관성 확보
apiVersion: v1
kind: Pod
metadata:
  annotations:
    pre.hook.backup.velero.io/command: '["/bin/bash", "-c", "pg_dump > /backup/dump.sql"]'
    post.hook.backup.velero.io/command: '["/bin/bash", "-c", "rm /backup/dump.sql"]'
```

## 🔍 트러블슈팅

### 문제: 백업이 Partially Failed

**원인**: 일부 리소스 백업 실패

**확인**:
```bash
velero backup logs my-backup | grep error
velero backup describe my-backup --details
```

### 문제: 복구 후 Pod가 Pending

**원인**: PV가 복구되지 않음

**해결**:
```bash
# Restic 활성화 확인
velero plugin get

# PV 백업 확인
velero backup describe my-backup --details | grep "Restic Backups"
```

### 문제: MinIO 접속 실패

**확인**:
```bash
# MinIO Pod 상태
kubectl get pods -n velero -l app=minio

# Secret 확인
kubectl get secret -n velero cloud-credentials -o yaml
```

## 📚 참고 자료

- [Velero 공식 문서](https://velero.io/docs/)
- [Disaster Recovery Guide](https://velero.io/docs/main/disaster-case/)

## 🧹 정리

```bash
kubectl delete namespace velero-demo
helm uninstall velero -n velero
kubectl delete namespace velero
```

---

**Velero로 클러스터를 안전하게 보호하세요! 💾**
