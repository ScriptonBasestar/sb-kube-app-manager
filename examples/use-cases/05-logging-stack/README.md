# Use Case: Logging Stack

Loki + Promtail + Grafana를 사용한 완전한 로그 집계 및 시각화 스택 구축 예제입니다.

## 📋 개요

**카테고리**: Use Cases

**구성 요소**:
- **Loki**: 로그 집계 및 저장 (Prometheus for logs)
- **Promtail**: 로그 수집 에이전트 (모든 노드에서 실행)
- **Grafana**: 로그 시각화 및 쿼리

**학습 목표**:
- 중앙집중식 로그 관리 시스템 구축
- Loki + Promtail 연동
- Grafana에서 로그 쿼리 및 시각화
- 복잡한 의존성 체인 관리

## 🎯 사용 사례

### 1. 중앙집중식 로그 관리

- 모든 Pod 로그를 한 곳에서 조회
- LogQL로 강력한 로그 검색
- 장기 로그 보관 (object storage 백엔드)

### 2. 트러블슈팅 및 디버깅

- 여러 서비스 간 로그 상관관계 분석
- 시간 범위별 로그 검색
- 실시간 로그 스트리밍

### 3. 알림 및 모니터링

- 로그 기반 알림 (ERROR 패턴 감지)
- Grafana 대시보드로 로그 메트릭 시각화
- 서비스 헬스 모니터링

## 🚀 빠른 시작

### 1. 전체 스택 배포

```bash
sbkube apply -f sbkube.yaml \
  --app-dir examples/use-cases/05-logging-stack \
  --namespace logging
```

### 2. 배포 확인

```bash
# 모든 Pod 확인
kubectl get pods -n logging

# 예상 출력:
# loki-0                        1/1   Running
# promtail-xxxxx                1/1   Running (각 노드마다)
# grafana-xxxxx                 1/1   Running

# Promtail DaemonSet 확인
kubectl get daemonset -n logging
```

### 3. Grafana 접속

```bash
# Port-forward
kubectl port-forward -n logging svc/grafana 3000:80

# 브라우저에서: http://localhost:3000
# 로그인: admin / admin-password
```

### 4. 로그 쿼리 테스트

1. Grafana → Explore 메뉴
2. 데이터 소스: Loki 선택
3. LogQL 쿼리 입력:
```logql
{namespace="default"}
```
4. "Run Query" 클릭 → 로그 확인

## 📖 설정 파일 설명

### sbkube.yaml

```yaml
namespace: logging

apps:
  # 1단계: Loki (로그 집계)
  loki:
    type: helm
    chart: grafana/loki
    values:
      - values/loki-values.yaml
    enabled: true

  # 2단계: Promtail (로그 수집, Loki 의존)
  promtail:
    type: helm
    chart: grafana/promtail
    values:
      - values/promtail-values.yaml
    depends_on:
      - loki

  # 3단계: Grafana (시각화, Loki 의존)
  grafana:
    type: helm
    chart: grafana/grafana
    values:
      - values/grafana-values.yaml
    depends_on:
      - loki
```

### 의존성 체인

```
Loki (로그 스토리지)
    ↓
  ├─ Promtail (로그 수집기)
  └─ Grafana (시각화)
```

## 🔧 주요 구성 요소

### 1. Loki (Log Aggregation System)

**역할**: 로그 수집 및 저장 (Prometheus와 유사한 아키텍처)

**주요 설정** (`values/loki-values.yaml`):
```yaml
loki:
  auth_enabled: false

  commonConfig:
    replication_factor: 1

  storage:
    type: filesystem  # 간단한 설정 (프로덕션에서는 S3 권장)

persistence:
  enabled: true
  size: 10Gi
  storageClass: "local-path"

resources:
  requests:
    memory: 256Mi
    cpu: 100m
  limits:
    memory: 512Mi
    cpu: 250m
```

**LogQL 쿼리 예시**:
```logql
# 특정 네임스페이스 로그
{namespace="default"}

# 특정 Pod 로그
{pod="nginx-xxxxx"}

# 에러 로그만
{namespace="default"} |= "error"

# JSON 파싱
{namespace="default"} | json | level="error"

# 시간 범위 + 패턴
{namespace="default"} |~ "exception|error" [5m]
```

### 2. Promtail (Log Shipper)

**역할**: 모든 노드에서 로그 수집하여 Loki로 전송

**주요 설정** (`values/promtail-values.yaml`):
```yaml
config:
  clients:
    - url: http://loki:3100/loki/api/v1/push

# DaemonSet으로 모든 노드에 배포
daemonset:
  enabled: true

# 모든 Pod 로그 수집
serviceMonitor:
  enabled: false  # Prometheus 없으므로 비활성화

resources:
  requests:
    memory: 128Mi
    cpu: 50m
  limits:
    memory: 256Mi
    cpu: 100m
```

**수집 프로세스**:
```
각 노드의 /var/log/pods/*
    ↓
Promtail (DaemonSet)
    ↓
Loki (HTTP API)
    ↓
Grafana (LogQL 쿼리)
```

### 3. Grafana (Visualization)

**역할**: 로그 시각화 및 대시보드

**주요 설정** (`values/grafana-values.yaml`):
```yaml
adminUser: admin
adminPassword: admin-password  # 프로덕션에서는 변경 필수

datasources:
  datasbkube.yaml:
    apiVersion: 1
    datasources:
      - name: Loki
        type: loki
        url: http://loki:3100
        access: proxy
        isDefault: true
        editable: true

dashboardProviders:
  dashboardproviders.yaml:
    apiVersion: 1
    providers:
      - name: 'default'
        folder: 'Logs'
        type: file
        disableDeletion: false
        editable: true
        options:
          path: /var/lib/grafana/dashboards/default

persistence:
  enabled: true
  size: 5Gi
  storageClass: "local-path"

resources:
  requests:
    memory: 256Mi
    cpu: 100m
  limits:
    memory: 512Mi
    cpu: 250m
```

**기본 대시보드**:
- Logs Dashboard (LogQL 쿼리)
- Pod Logs (네임스페이스별)
- Error Logs (에러 로그만)

## 🎓 학습 포인트

### 1. Loki vs Elasticsearch

| 비교 | Loki | Elasticsearch |
|------|------|---------------|
| **인덱싱** | 메타데이터만 | 전체 로그 |
| **저장공간** | 적음 (압축) | 많음 |
| **쿼리 속도** | 빠름 (레이블 기반) | 매우 빠름 (전문 검색) |
| **비용** | 저렴 | 비쌈 |
| **사용 사례** | 간단한 로그 집계 | 복잡한 로그 분석 |

Loki는 **"Prometheus for logs"** 컨셉:
- 레이블 기반 쿼리
- 효율적인 저장공간
- Kubernetes 환경에 최적화

### 2. Promtail 라벨링

```yaml
# Promtail이 자동으로 추가하는 레이블
{
  namespace="default",
  pod="nginx-xxxxx",
  container="nginx",
  job="default/nginx"
}
```

**커스텀 라벨 추가**:
```yaml
# promtail-values.yaml
config:
  snippets:
    extraRelabelConfigs:
      - source_labels: [__meta_kubernetes_pod_label_app]
        target_label: app
      - source_labels: [__meta_kubernetes_pod_label_version]
        target_label: version
```

### 3. 로그 보관 정책

```yaml
# loki-values.yaml
loki:
  limits_config:
    retention_period: 744h  # 31일 보관

  table_manager:
    retention_deletes_enabled: true
    retention_period: 744h
```

### 4. 스케일링 전략

**Loki 스케일링**:
- 작은 환경: Single Binary (이 예제)
- 중간 환경: Simple Scalable (read/write 분리)
- 대규모 환경: Microservices (완전 분산)

**Promtail 스케일링**:
- DaemonSet으로 자동 스케일 (노드 수에 비례)

## 🧪 테스트 시나리오

### 시나리오 1: 로그 수집 확인

```bash
# 테스트 Pod 배포
kubectl run test-logger --image=alpine --command -- sh -c "while true; do echo 'Test log message'; sleep 5; done"

# Grafana Explore에서 쿼리:
{pod="test-logger"}

# 로그 확인 (5초마다 메시지)
```

### 시나리오 2: 에러 로그 필터링

```bash
# 에러를 발생시키는 Pod
kubectl run error-pod --image=alpine --command -- sh -c "while true; do echo 'ERROR: Something went wrong'; sleep 10; done"

# Grafana에서 쿼리:
{namespace="default"} |= "ERROR"

# 에러 로그만 표시
```

### 시나리오 3: 여러 네임스페이스 로그

```bash
# 다른 네임스페이스에 Pod 생성
kubectl create namespace test-ns
kubectl run app1 -n test-ns --image=nginx

# Grafana에서 쿼리:
{namespace=~"default|test-ns"}

# 두 네임스페이스 로그 모두 표시
```

### 시나리오 4: JSON 로그 파싱

```bash
# JSON 로그를 출력하는 Pod
kubectl run json-logger --image=alpine --command -- sh -c 'while true; do echo "{\"level\":\"info\",\"msg\":\"Hello\"}"; sleep 5; done'

# Grafana에서 쿼리:
{pod="json-logger"} | json | level="info"

# JSON 필드로 필터링
```

## 🔍 트러블슈팅

### 문제 1: "Loki에서 로그가 보이지 않음"

**원인**: Promtail이 Loki에 연결하지 못함

**확인**:
```bash
# Promtail 로그 확인
kubectl logs -n logging -l app.kubernetes.io/name=promtail

# Loki URL 확인
kubectl exec -n logging -it <promtail-pod> -- cat /etc/promtail/config.yml | grep url
```

**해결**:
```yaml
# promtail-values.yaml
config:
  clients:
    - url: http://loki:3100/loki/api/v1/push  # 올바른 URL
```

### 문제 2: "Promtail Pod가 시작하지 않음"

**원인**: /var/log 마운트 권한 부족

**확인**:
```bash
kubectl describe pod -n logging <promtail-pod>
```

**해결**:
```yaml
# promtail-values.yaml
securityContext:
  privileged: true  # 또는
  runAsUser: 0
```

### 문제 3: "Grafana에서 Loki 데이터 소스 연결 실패"

**원인**: Loki 서비스 이름 불일치

**해결**:
```yaml
# grafana-values.yaml
datasources:
  datasbkube.yaml:
    datasources:
      - name: Loki
        url: http://loki:3100  # 정확한 서비스 이름
```

**테스트**:
```bash
# Grafana Pod에서 Loki 접근 확인
kubectl exec -n logging <grafana-pod> -- curl http://loki:3100/ready
```

### 문제 4: "로그가 너무 많아서 느려짐"

**원인**: 로그 볼륨 과다

**해결**:
```yaml
# loki-values.yaml
loki:
  limits_config:
    # 쿼리 제한
    max_query_series: 1000
    max_query_lookback: 720h

    # 로그 라인 제한
    max_entries_limit_per_query: 5000
```

## 💡 실전 패턴

### 패턴 1: S3 백엔드 사용 (프로덕션)

```yaml
# loki-values.yaml
loki:
  storage:
    type: s3
    s3:
      endpoint: minio:9000
      bucketname: loki-logs
      access_key_id: admin
      secret_access_key: password
      s3ForcePathStyle: true
      insecure: true
```

### 패턴 2: 멀티테넌트 설정

```yaml
# loki-values.yaml
loki:
  auth_enabled: true

  # 테넌트별 로그 분리
  limits_config:
    per_tenant_override_config: /etc/loki/overrides.yaml

# promtail-values.yaml
config:
  clients:
    - url: http://loki:3100/loki/api/v1/push
      tenant_id: team-a  # 테넌트 ID
```

### 패턴 3: 알림 설정

```yaml
# grafana-values.yaml
# Grafana Alert 설정
dashboards:
  logs-alert.json: |
    {
      "alert": {
        "name": "High Error Rate",
        "condition": "count({namespace=\"prod\"} |= \"ERROR\") > 100"
      }
    }
```

### 패턴 4: 로그 파이프라인

```yaml
# promtail-values.yaml
config:
  snippets:
    pipelineStages:
      - json:
          expressions:
            level: level
            message: msg
      - labels:
          level:
      - match:
          selector: '{level="error"}'
          action: keep
```

## 📚 추가 학습 자료

### 공식 문서
- [Loki Documentation](https://grafana.com/docs/loki/latest/)
- [LogQL Query Language](https://grafana.com/docs/loki/latest/logql/)
- [Promtail Configuration](https://grafana.com/docs/loki/latest/clients/promtail/)

### SBKube 관련
- [Dependency Management](../../docs/02-features/commands.md#의존성-관리)
- [Monitoring Stack](../03-monitoring-stack/) - Prometheus + Grafana

### 관련 예제
- [Monitoring Stack](../03-monitoring-stack/) - 메트릭 모니터링
- [Complex Dependencies](../../advanced-features/02-complex-dependencies/)

## 🎯 다음 단계

1. **모니터링 통합**:
   - [Monitoring Stack](../03-monitoring-stack/)과 결합
   - Metrics + Logs 통합 대시보드

2. **알림 설정**:
   - Grafana Alert 설정
   - Slack, PagerDuty 통합

3. **고급 쿼리**:
   - LogQL 함수 활용
   - Metrics from Logs

## 🧹 정리

```bash
# 전체 스택 삭제
kubectl delete namespace logging

# 또는 개별 삭제
helm uninstall loki promtail grafana -n logging
```

---

**모든 로그를 한 곳에서 관리하세요! 📊**
