# Advanced Chart Customization (Future Feature)

> ⚠️ **중요: 이 기능은 아직 구현되지 않았습니다**
>
> 이 디렉토리는 **미래 기능을 위한 설계 문서 및 예제**입니다.
> 고급 패칭 기능 (Strategic Merge Patch, JSON Patch 등)은 계획 단계이며, 현재 SBKube에 구현되어 있지 않습니다.
>
> **현재 사용 가능한 차트 커스터마이징 기능:**
> - `overrides`: 차트 템플릿 파일 **교체** ([override-with-files](../override-with-files/) 참조)
> - `removes`: 차트 템플릿 파일 **삭제** ([override-with-files](../override-with-files/) 참조)
>
> **로드맵:** 고급 패칭 기능은 v0.6.0 이후 릴리스에서 구현 예정입니다.

---

## 🔮 계획된 기능: Advanced Patching

Helm 차트 템플릿 파일을 빌드 시점에 정교하게 패치하는 기능입니다.

### 기획 의도

현재 `overrides` 기능은 파일 **전체를 교체**하는 방식입니다.
고급 패칭 기능은 파일의 **일부분만 수정**할 수 있도록 합니다:

- **Strategic Merge Patch**: 컨테이너, 볼륨, 포트 추가 (Kubernetes 병합 전략)
- **JSON Patch (RFC 6902)**: 정확한 경로로 값 변경 (add/replace/remove/test 등)
- **Merge Patch (RFC 7386)**: 간단한 키-값 병합 (ConfigMap, Secret)
- **Create Patch**: 새로운 리소스 파일 생성 (ServiceMonitor, NetworkPolicy)

### 사용 시나리오

1. **공식 차트 커스터마이징**: values 파일로 불가능한 변경
2. **사이드카 컨테이너 추가**: 로그 수집, 보안 스캐너 등
3. **보안 강화**: SecurityContext, NetworkPolicy 추가
4. **모니터링 통합**: ServiceMonitor, Annotation 추가
5. **스토리지 커스터마이징**: PVC 설정 변경

---

## 📁 디렉토리 구조

```
advanced-overrides/
├── config.yaml               # 앱 설정 (미래 API 예제)
├── sources.yaml              # Helm 리포지토리
├── grafana-values.yaml       # Grafana 기본 values
├── prometheus-values.yaml    # Prometheus 기본 values
├── patches/                  # 패치 파일들 (예제)
│   ├── add-sidecar-container.yaml       # Sidecar 추가 (Strategic)
│   ├── add-service-port.yaml            # 포트 추가 (Strategic)
│   ├── add-custom-config.yaml           # ConfigMap 추가 (Merge)
│   ├── prometheus-security.yaml         # Security Context (Strategic)
│   ├── prometheus-pvc.yaml              # PVC 커스터마이징 (Strategic)
│   ├── prometheus-servicemonitor.yaml   # 새 파일 생성 (Create)
│   └── redis-json-patch.yaml            # 환경 변수 추가 (JSON)
└── README.md                 # 이 문서
```

---

## 🔧 계획된 Patch 타입

### 1. Strategic Merge Patch (권장)

**특징**:
- Kubernetes 리소스 병합 전략 사용
- 리스트 항목 추가/수정 가능
- 가장 직관적

**예시**: Deployment에 사이드카 컨테이너 추가

```yaml
# patches/add-sidecar-container.yaml
spec:
  template:
    spec:
      containers:
      - name: log-forwarder  # ← 기존 컨테이너에 추가
        image: fluent/fluent-bit:2.0
```

**예상 사용법**:
```yaml
# config.yaml (미래 API)
grafana:
  type: helm
  patches:  # 또는 advanced_overrides
    - target: templates/deployment.yaml
      patch: patches/add-sidecar-container.yaml
      strategy: strategic  # strategic | json | merge | create
```

### 2. JSON Patch (정밀 제어)

**특징**:
- RFC 6902 표준
- 정확한 경로로 값 변경 (add/replace/remove/test 등)
- 복잡한 변경에 유용

**예시**: Redis 환경 변수 추가

```yaml
# patches/redis-json-patch.yaml
- op: add
  path: /spec/template/spec/containers/0/env/-
  value:
    name: REDIS_EXTRA_FLAGS
    value: "--maxmemory 256mb"
```

**예상 사용법**:
```yaml
redis:
  type: helm
  patches:
    - target: templates/master/statefulset.yaml
      patch: patches/redis-json-patch.yaml
      strategy: json
```

### 3. Merge Patch (단순 병합)

**특징**:
- RFC 7386 표준
- 간단한 키-값 병합
- ConfigMap, Secret 수정에 적합

**예시**: ConfigMap에 데이터 추가

```yaml
# patches/add-custom-config.yaml
data:
  custom-dashboard.json: |
    { "dashboard": { "title": "Custom" } }
```

### 4. Create Patch (파일 생성)

**특징**:
- 차트에 없는 새로운 템플릿 파일 생성
- ServiceMonitor, NetworkPolicy 등 추가

**예시**: ServiceMonitor 생성

```yaml
# patches/prometheus-servicemonitor.yaml
apiVersion: monitoring.coreos.com/v1
kind: ServiceMonitor
metadata:
  name: {{ include "prometheus.fullname" . }}-monitor
spec:
  selector:
    matchLabels:
      app: prometheus
  endpoints:
  - port: http
    interval: 30s
```

---

## 🚀 예상 워크플로우

```bash
# 1단계: Helm 차트 다운로드
sbkube prepare --app-dir examples/advanced-overrides

# 2단계: 빌드 (고급 패치 적용)
sbkube build --app-dir examples/advanced-overrides

# 패치가 적용된 차트 확인:
cat build/grafana/templates/deployment.yaml | grep log-forwarder

# 3단계: 템플릿 생성 (검증)
sbkube template --app-dir examples/advanced-overrides --output-dir rendered

# 4단계: 배포
sbkube deploy --app-dir examples/advanced-overrides

# 또는 한 번에
sbkube apply --app-dir examples/advanced-overrides
```

---

## 📋 실전 패턴 (미래 사용 예)

### 패턴 1: 사이드카 컨테이너 추가

**목적**: 모든 Pod에 로그 수집 사이드카 추가

```yaml
# patches/log-sidecar.yaml (Strategic Merge)
spec:
  template:
    spec:
      containers:
      - name: log-forwarder
        image: fluent/fluent-bit:2.0
        volumeMounts:
          - name: varlog
            mountPath: /var/log
      volumes:
      - name: varlog
        emptyDir: {}
```

### 패턴 2: 보안 강화

**목적**: SecurityContext 추가

```yaml
# patches/security.yaml (Strategic Merge)
spec:
  template:
    spec:
      securityContext:
        runAsNonRoot: true
        runAsUser: 65534
        fsGroup: 65534
      containers:
      - name: prometheus-server
        securityContext:
          allowPrivilegeEscalation: false
          capabilities:
            drop: [ALL]
```

### 패턴 3: 모니터링 통합

**목적**: Prometheus ServiceMonitor 추가

```yaml
# patches/servicemonitor.yaml (Create)
apiVersion: monitoring.coreos.com/v1
kind: ServiceMonitor
metadata:
  name: {{ include "prometheus.fullname" . }}
spec:
  selector:
    matchLabels:
      app: prometheus
  endpoints:
  - port: http
    interval: 30s
```

### 패턴 4: 환경 변수 추가

**목적**: 특정 설정 추가 (values로 불가능한 경우)

```yaml
# patches/env.yaml (JSON Patch)
- op: add
  path: /spec/template/spec/containers/0/env/-
  value:
    name: CUSTOM_FLAG
    value: "enabled"
```

---

## 🎯 현재 vs 미래

| 기능 | 현재 (v0.5.x) | 미래 (v0.6.0+) |
|------|---------------|----------------|
| **파일 전체 교체** | ✅ `overrides` | ✅ `overrides` (유지) |
| **파일 삭제** | ✅ `removes` | ✅ `removes` (유지) |
| **부분 패칭 (Strategic)** | ❌ | ✅ `patches` (신규) |
| **JSON Patch** | ❌ | ✅ `patches` (신규) |
| **Merge Patch** | ❌ | ✅ `patches` (신규) |
| **파일 생성 (Create)** | ⚠️ overrides로 가능 | ✅ `patches` (개선) |

---

## 💡 설계 고려사항

### API 설계

**옵션 1**: 새 필드 `patches` 추가

```yaml
grafana:
  overrides:  # 기존 - 전체 교체
    - templates/deployment.yaml
  removes:    # 기존 - 삭제
    - templates/tests/
  patches:    # 신규 - 부분 수정
    - target: templates/deployment.yaml
      patch: patches/add-sidecar.yaml
      strategy: strategic
```

**옵션 2**: `overrides`를 확장

```yaml
grafana:
  overrides:
    - path: templates/deployment.yaml  # 전체 교체
    - target: templates/service.yaml   # 부분 패치
      patch: patches/add-port.yaml
      strategy: strategic
  removes:
    - templates/tests/
```

### 처리 순서

```
prepare (차트 다운로드)
  → build:
      1. overrides (전체 교체)
      2. patches (부분 수정)
      3. removes (삭제)
  → template (렌더링)
  → deploy (배포)
```

---

## 📚 관련 문서

- **현재 사용 가능**: [override-with-files](../override-with-files/) - `overrides`와 `removes` 예제
- **기본 가이드**: [app-types/01-helm](../app-types/01-helm/) - Helm 앱 타입
- **고급 기능**: [advanced-features/](../advanced-features/) - Helm 고급 설정

---

## 🔑 핵심 정리

1. **이 디렉토리는 설계 문서입니다**
   - 현재 구현되지 않은 미래 기능
   - API 설계 및 사용 패턴 기획

2. **현재 대안**
   - 전체 파일 교체: `overrides` 사용
   - 불필요한 파일 제거: `removes` 사용
   - 예제: [override-with-files](../override-with-files/)

3. **구현 로드맵**
   - v0.6.0: Strategic Merge Patch
   - v0.7.0: JSON Patch, Merge Patch
   - v0.8.0: Create Patch 최적화

4. **기여 환영**
   - 이 기능에 대한 피드백은 GitHub Issues에 환영합니다
   - 설계 개선 제안이 있다면 PR을 보내주세요

---

**작성일**: 2025-10-31
**상태**: 설계 단계 (구현 예정)
**버전**: SBKube v0.5.0+
