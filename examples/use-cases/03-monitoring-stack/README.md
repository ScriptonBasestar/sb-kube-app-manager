# Use Case 03: Monitoring Stack (Prometheus + Grafana)

k3s 클러스터에 Prometheus와 Grafana를 이용한 완전한 모니터링 스택을 구축합니다.

## 시나리오

k3s 클러스터와 배포된 애플리케이션을 모니터링하기 위한 스택:

1. **Prometheus** - 메트릭 수집 및 저장
2. **Grafana** - 메트릭 시각화 대시보드
3. **Node Exporter** - 노드 메트릭 수집
4. **kube-state-metrics** - Kubernetes 메트릭 수집
5. **AlertManager** - 알림 관리 (선택사항)

## 아키텍처

```
┌──────────────────────────────────────────────────┐
│              Monitoring Stack                    │
├──────────────────────────────────────────────────┤
│                                                  │
│  ┌──────────┐         ┌────────────┐            │
│  │ Grafana  │────────▶│ Prometheus │            │
│  │  :3000   │         │   :9090    │            │
│  └──────────┘         └─────┬──────┘            │
│                             │                    │
│                ┌────────────┼────────────┐       │
│                │            │            │       │
│         ┌──────▼──┐   ┌─────▼────┐  ┌───▼───┐   │
│         │  Node   │   │  kube-   │  │ Alert │   │
│         │ Export  │   │  state   │  │Manager│   │
│         └─────────┘   └──────────┘  └───────┘   │
│                                                  │
└──────────────────────────────────────────────────┘
```

## 배포

```bash
# 전체 스택 배포
sbkube apply --app-dir .

# Prometheus만 먼저 배포
sbkube apply --app-dir . --apps prometheus

# Grafana 배포 (Prometheus 의존)
sbkube apply --app-dir . --apps grafana
```

## 접근

### Grafana 웹 UI
```bash
# 포트포워딩
kubectl port-forward -n monitoring svc/grafana 3000:80

# 브라우저에서 http://localhost:3000 접속
# Username: admin
# Password: admin-password
```

### Prometheus 웹 UI
```bash
# 포트포워딩
kubectl port-forward -n monitoring svc/prometheus-server 9090:80

# 브라우저에서 http://localhost:9090 접속
```

### AlertManager 웹 UI
```bash
# 포트포워딩
kubectl port-forward -n monitoring svc/prometheus-alertmanager 9093:80

# 브라우저에서 http://localhost:9093 접속
```

## Grafana 대시보드 설정

### 1. Prometheus 데이터 소스 추가

Grafana에 로그인 후:

1. Configuration > Data Sources
2. Add data source > Prometheus
3. URL: `http://prometheus-server.monitoring.svc.cluster.local`
4. Save & Test

### 2. 대시보드 Import

인기 있는 대시보드 ID:
- **315** - Kubernetes cluster monitoring
- **6417** - Kubernetes Cluster (Prometheus)
- **3662** - Prometheus 2.0 Stats
- **1860** - Node Exporter Full

Import 방법:
1. Dashboards > Import
2. 대시보드 ID 입력
3. Prometheus 데이터 소스 선택
4. Import

## 모니터링 쿼리 예제

### Prometheus Query

```promql
# CPU 사용률
sum(rate(container_cpu_usage_seconds_total[5m])) by (pod)

# 메모리 사용량
sum(container_memory_usage_bytes) by (pod)

# Pod 상태
kube_pod_status_phase{namespace="default"}

# 노드 CPU 사용률
100 - (avg by (instance) (irate(node_cpu_seconds_total{mode="idle"}[5m])) * 100)
```

## 알림 설정 (AlertManager)

### Slack 연동 예제

`alertmanager-config.yaml` 수정:
```yaml
receivers:
  - name: 'slack'
    slack_configs:
      - api_url: 'YOUR_SLACK_WEBHOOK_URL'
        channel: '#alerts'
        title: 'Kubernetes Alert'
        text: '{{ range .Alerts }}{{ .Annotations.description }}{{ end }}'
```

### 이메일 연동 예제

```yaml
receivers:
  - name: 'email'
    email_configs:
      - to: 'ops-team@example.com'
        from: 'alertmanager@k3s.local'
        smarthost: 'smtp.gmail.com:587'
        auth_username: 'your-email@gmail.com'
        auth_password: 'your-app-password'
```

## 커스텀 알림 규칙

`custom-rules.yaml` 생성:
```yaml
groups:
  - name: custom-rules
    rules:
      - alert: HighPodMemory
        expr: sum(container_memory_usage_bytes) by (pod) / 1024 / 1024 > 500
        for: 5m
        labels:
          severity: warning
        annotations:
          description: "Pod {{ $labels.pod }} is using {{ $value }}MB of memory"

      - alert: PodCrashLooping
        expr: rate(kube_pod_container_status_restarts_total[15m]) > 0
        for: 5m
        labels:
          severity: critical
        annotations:
          description: "Pod {{ $labels.pod }} is crash looping"
```

## 메트릭 보존 기간 조정

프로덕션 환경에서는 `prometheus-values.yaml` 수정:
```yaml
server:
  retention: "30d"  # 30일간 메트릭 보관
  persistentVolume:
    size: 50Gi
```

## 고급 설정

### ServiceMonitor 추가 (애플리케이션 모니터링)

```yaml
apiVersion: monitoring.coreos.com/v1
kind: ServiceMonitor
metadata:
  name: my-app-monitor
  namespace: monitoring
spec:
  selector:
    matchLabels:
      app: my-app
  endpoints:
  - port: metrics
    interval: 30s
```

### Prometheus Federation (멀티 클러스터)

```yaml
scrape_configs:
  - job_name: 'federate'
    scrape_interval: 15s
    honor_labels: true
    metrics_path: '/federate'
    params:
      'match[]':
        - '{job="kubernetes-pods"}'
    static_configs:
      - targets:
        - 'prometheus-1.example.com:9090'
        - 'prometheus-2.example.com:9090'
```

## 리소스 최적화

### 메모리 제한 조정
```yaml
# 대규모 클러스터용
server:
  resources:
    limits:
      memory: 4Gi
      cpu: 2000m
    requests:
      memory: 2Gi
      cpu: 1000m
```

### 스크랩 간격 조정
```yaml
# 메트릭 수집 빈도 줄이기 (리소스 절약)
server:
  global:
    scrape_interval: 1m
    scrape_timeout: 30s
```

## 트러블슈팅

### Prometheus가 타겟을 발견 못함
```bash
# RBAC 권한 확인
kubectl get clusterrolebinding prometheus

# ServiceMonitor 확인
kubectl get servicemonitor -n monitoring
```

### Grafana에서 데이터가 안보임
```bash
# Prometheus 연결 테스트
kubectl exec -n monitoring grafana-xxx -- curl http://prometheus-server.monitoring.svc.cluster.local

# Prometheus 로그 확인
kubectl logs -n monitoring prometheus-server-xxx
```

### 디스크 공간 부족
```bash
# PV 사이즈 확인
kubectl get pvc -n monitoring

# 메트릭 보존 기간 줄이기
# prometheus-values.yaml에서 retention 설정
```

## 정리

```bash
# 전체 삭제
sbkube delete --app-dir .

# PV도 삭제
kubectl delete pvc -n monitoring --all
```

## 프로덕션 체크리스트

- [ ] Persistence 활성화 (Prometheus, Grafana)
- [ ] 적절한 retention 기간 설정
- [ ] AlertManager 알림 설정 (Slack, Email)
- [ ] 중요 메트릭에 대한 알림 규칙 정의
- [ ] Grafana 대시보드 구성
- [ ] RBAC 권한 최소화
- [ ] 리소스 제한 적절히 조정
- [ ] 백업 정책 수립

## 관련 예제

- [Use Case 01: Development Environment](../01-dev-environment/)
- [Use Case 02: Wiki Stack](../02-wiki-stack/)
