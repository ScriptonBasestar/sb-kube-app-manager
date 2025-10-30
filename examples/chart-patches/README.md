# Chart Patches Example

> ⚠️ **중요: 이 기능은 아직 구현되지 않았습니다**
>
> `chart_patches` 기능은 계획 단계이며, 현재 SBKube에 구현되어 있지 않습니다.
> 이 디렉토리는 미래 기능을 위한 설계 문서 및 예제입니다.
>
> **현재 사용 가능한 차트 커스터마이징 기능:**
> - `overrides`: 차트 템플릿 파일 **교체** ([override-with-files](../override-with-files/) 참조)
> - `removes`: 차트 템플릿 파일 **삭제** ([override-with-files](../override-with-files/) 참조)
>
> **로드맵:** `chart_patches` 기능은 v0.4.0 이후 릴리스에서 구현 예정입니다.

---

## 🔮 계획된 기능: chart_patches

Helm 차트 템플릿 파일을 빌드 시점에 패치하는 방법을 시연합니다.

이 예제는 다음을 보여줍니다:
- **Strategic Merge Patch**: 컨테이너, 볼륨, 포트 추가
- **JSON Patch**: 정확한 경로로 값 변경
- **Merge Patch**: ConfigMap 데이터 추가
- **Create Patch**: 새로운 리소스 파일 생성

## 🎯 chart_patches란?

`chart_patches`는 Helm 차트의 템플릿 파일을 빌드 단계에서 수정할 수 있는 **계획된** 기능입니다 (v0.4.0+ 목표).

### 사용 시나리오

1. **공식 차트 커스터마이징**: values 파일로 불가능한 변경
2. **사이드카 컨테이너 추가**: 로그 수집, 보안 스캐너 등
3. **보안 강화**: SecurityContext, NetworkPolicy 추가
4. **모니터링 통합**: ServiceMonitor, Annotation 추가
5. **스토리지 커스터마이징**: PVC 설정 변경

## 📁 디렉토리 구조

```
chart-patches/
├── config.yaml               # 앱 설정 + chart_patches 정의
├── sources.yaml              # Helm 리포지토리
├── grafana-values.yaml       # Grafana 기본 values
├── prometheus-values.yaml    # Prometheus 기본 values
├── patches/                  # 패치 파일들
│   ├── add-sidecar-container.yaml       # Sidecar 추가 (Strategic)
│   ├── add-service-port.yaml            # 포트 추가 (Strategic)
│   ├── add-custom-config.yaml           # ConfigMap 추가 (Merge)
│   ├── prometheus-security.yaml         # Security Context (Strategic)
│   ├── prometheus-pvc.yaml              # PVC 커스터마이징 (Strategic)
│   ├── prometheus-servicemonitor.yaml   # 새 파일 생성 (Create)
│   └── redis-json-patch.yaml            # 환경 변수 추가 (JSON)
└── README.md                 # 이 문서
```

## 🔧 Patch 타입

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

**사용**:
```yaml
chart_patches:
  - target: templates/deployment.yaml
    patch: patches/add-sidecar-container.yaml
    type: strategic
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

**사용**:
```yaml
chart_patches:
  - target: templates/master/statefulset.yaml
    patch: patches/redis-json-patch.yaml
    type: json
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

**사용**:
```yaml
chart_patches:
  - target: templates/configmap.yaml
    patch: patches/add-custom-config.yaml
    type: merge
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
  # ...
```

**사용**:
```yaml
chart_patches:
  - target: templates/servicemonitor.yaml  # 새 파일
    patch: patches/prometheus-servicemonitor.yaml
    type: create
```

## 🚀 실행 방법

### 1. 전체 워크플로우

```bash
# 1단계: Helm 차트 다운로드
sbkube prepare --app-dir examples/chart-patches

# 차트가 charts/ 디렉토리에 다운로드됨
ls charts/grafana/
ls charts/prometheus/
ls charts/redis/

# 2단계: 빌드 (패치 적용)
sbkube build --app-dir examples/chart-patches

# 패치가 적용된 차트가 빌드됨
# 변경사항 확인:
cat charts/grafana/templates/deployment.yaml | grep log-forwarder

# 3단계: 템플릿 생성 (검증)
sbkube template --app-dir examples/chart-patches --output-dir rendered

# 렌더링된 매니페스트 확인
ls rendered/
cat rendered/grafana-deployment.yaml | grep log-forwarder

# 4단계: 배포
sbkube deploy --app-dir examples/chart-patches

# 또는 한 번에
sbkube apply --app-dir examples/chart-patches
```

### 2. 패치 적용 확인

```bash
# 빌드 후 차트 파일 확인
cat charts/grafana/templates/deployment.yaml

# 예상 결과: log-forwarder 사이드카가 추가되어 있음
# spec:
#   template:
#     spec:
#       containers:
#       - name: grafana       # 원본
#       - name: log-forwarder # ← 패치로 추가됨
```

### 3. 패치 전/후 비교

```bash
# 패치 전: prepare만 실행
sbkube prepare --app-dir examples/chart-patches
cp -r charts charts-before

# 패치 후: build 실행
sbkube build --app-dir examples/chart-patches
cp -r charts charts-after

# 차이 확인
diff -r charts-before/grafana/templates/ charts-after/grafana/templates/
```

## 📋 실전 패턴

### 패턴 1: 사이드카 컨테이너 추가

**목적**: 모든 Pod에 로그 수집 사이드카 추가

**패치 파일** (Strategic Merge):
```yaml
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

**config.yaml**:
```yaml
grafana:
  chart_patches:
    - target: templates/deployment.yaml
      patch: patches/add-sidecar-container.yaml
      type: strategic
```

### 패턴 2: 보안 강화

**목적**: SecurityContext 추가

**패치 파일** (Strategic Merge):
```yaml
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

**패치 파일** (Create):
```yaml
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

**패치 파일** (JSON Patch):
```yaml
- op: add
  path: /spec/template/spec/containers/0/env/-
  value:
    name: CUSTOM_FLAG
    value: "enabled"
```

## 🔍 검증

### 패치 적용 확인

```bash
# 1. 빌드 후 파일 존재 확인
ls charts/grafana/templates/deployment.yaml

# 2. 파일 내용 확인
cat charts/grafana/templates/deployment.yaml | grep -A 5 "log-forwarder"

# 3. 템플릿 렌더링 확인
sbkube template --app-dir . --output-dir rendered
cat rendered/grafana-deployment.yaml | grep "log-forwarder"
```

### 배포 후 확인

```bash
# Pod에 사이드카 컨테이너 존재 확인
kubectl get pods -n chart-patches-demo
kubectl describe pod -n chart-patches-demo <grafana-pod-name> | grep -A 10 "Containers:"

# 예상 결과:
# Containers:
#   grafana:
#     ...
#   log-forwarder:
#     ...
```

### 패치 오류 디버깅

```bash
# sbkube 빌드 로그 확인
sbkube build --app-dir . --verbose

# 패치 파일 문법 확인
yamllint patches/add-sidecar-container.yaml

# 패치 전후 비교
diff charts-before/grafana/templates/deployment.yaml \
     charts-after/grafana/templates/deployment.yaml
```

## 💡 사용 사례

### Use Case 1: 엔터프라이즈 보안 정책

모든 Pod에 보안 설정 강제:

```yaml
chart_patches:
  - target: templates/deployment.yaml
    patch: patches/enterprise-security.yaml
    type: strategic
```

**enterprise-security.yaml**:
```yaml
spec:
  template:
    spec:
      securityContext:
        runAsNonRoot: true
        seccompProfile:
          type: RuntimeDefault
      containers:
      - name: "*"  # 모든 컨테이너에 적용
        securityContext:
          allowPrivilegeEscalation: false
          capabilities:
            drop: [ALL]
```

### Use Case 2: 멀티 테넌시

각 테넌트별 레이블/주석 추가:

```yaml
chart_patches:
  - target: templates/deployment.yaml
    patch: patches/tenant-labels.yaml
    type: merge
```

**tenant-labels.yaml**:
```yaml
metadata:
  labels:
    tenant: customer-a
    cost-center: "1234"
  annotations:
    contact: "admin@customer-a.com"
```

### Use Case 3: Service Mesh 통합

Istio 사이드카 주입 제어:

```yaml
chart_patches:
  - target: templates/deployment.yaml
    patch: patches/istio-sidecar.yaml
    type: merge
```

**istio-sidecar.yaml**:
```yaml
metadata:
  annotations:
    sidecar.istio.io/inject: "true"
    traffic.sidecar.istio.io/includeOutboundIPRanges: "*"
```

### Use Case 4: 커스텀 리소스 추가

차트에 없는 NetworkPolicy 추가:

```yaml
chart_patches:
  - target: templates/networkpolicy.yaml
    patch: patches/network-policy.yaml
    type: create
```

## 🎯 우선순위 규칙

Helm 차트 커스터마이징 순서:

1. **차트 기본값** (Chart.yaml의 values)
2. **values 파일** (config.yaml의 values:)
3. **set_values** (config.yaml의 set_values:)
4. **chart_patches** ← 최종 단계 (빌드 시 적용)

**예시**:
```yaml
grafana:
  values:
    - grafana-values.yaml      # replicaCount: 1

  set_values:
    - replicaCount=3           # ← 3으로 오버라이드

  chart_patches:
    - target: templates/deployment.yaml
      patch: patches/add-sidecar.yaml
      type: strategic          # ← 최종 템플릿 수정
```

## 🐛 Troubleshooting

### 문제 1: 패치 적용 실패

**증상**: `Error: failed to apply patch to templates/deployment.yaml`

**원인**: 패치 파일 경로 또는 YAML 문법 오류

**해결**:
```bash
# 1. 패치 파일 존재 확인
ls patches/add-sidecar-container.yaml

# 2. YAML 문법 확인
yamllint patches/add-sidecar-container.yaml

# 3. target 경로 확인 (차트 다운로드 후)
ls charts/grafana/templates/deployment.yaml
```

### 문제 2: Strategic Merge가 예상대로 작동 안 함

**증상**: 컨테이너가 추가되지 않고 대체됨

**원인**: Strategic Merge의 병합 규칙 오해

**해결**:
```yaml
# 잘못된 예 (전체 대체)
spec:
  template:
    spec:
      containers:  # ← 이 배열 전체가 대체됨
      - name: new-container

# 올바른 예 (항목 추가)
spec:
  template:
    spec:
      containers:
      - name: new-container  # ← 기존 컨테이너에 추가됨
        # name을 기준으로 병합
```

### 문제 3: JSON Patch 경로 오류

**증상**: `Error: path not found: /spec/template/spec/containers/0/env`

**원인**: 배열 인덱스 또는 경로 오류

**해결**:
```bash
# 1. 원본 파일 구조 확인
cat charts/redis/templates/master/statefulset.yaml | yq e '.spec.template.spec.containers'

# 2. 정확한 경로 파악
# containers 배열의 첫 번째 항목 = /containers/0
# env가 없으면 먼저 생성:
- op: add
  path: /spec/template/spec/containers/0/env
  value: []

- op: add
  path: /spec/template/spec/containers/0/env/-
  value:
    name: NEW_VAR
    value: "value"
```

### 문제 4: 패치 후 Helm 템플릿 문법 깨짐

**증상**: `Error: template: deployment.yaml: ... unexpected "{{"`

**원인**: 패치 파일에 Helm 템플릿 구문이 잘못됨

**해결**:
```yaml
# 잘못된 예
metadata:
  name: my-app-{{ .Release.Name }  # ← 닫는 괄호 누락

# 올바른 예
metadata:
  name: my-app-{{ .Release.Name }}
```

### 문제 5: Create Patch로 생성한 파일이 렌더링 안 됨

**증상**: `templates/servicemonitor.yaml` 생성했지만 `helm template` 결과에 없음

**원인**: Helm이 `.yaml` 또는 `.tpl` 확장자만 인식

**해결**:
```yaml
# target 파일명 확인
chart_patches:
  - target: templates/servicemonitor.yaml  # ✅ .yaml
    # NOT: servicemonitor.yml
    # NOT: servicemonitor.txt
```

## 📚 관련 예제

- [override-with-files](../override-with-files/) - overrides, removes 기능
- [advanced-features/03-helm-customization](../advanced-features/03-helm-customization/) - Helm 고급 기능
- [app-types/01-helm](../app-types/01-helm/) - Helm 기본

## 🔑 핵심 정리

1. **chart_patches 타입**
   - **Strategic Merge**: 리소스 병합 (권장)
   - **JSON Patch**: 정밀 제어
   - **Merge Patch**: 간단한 병합
   - **Create**: 새 파일 생성

2. **적용 순서**
   ```
   prepare (차트 다운로드)
     → build (패치 적용) ← chart_patches 실행
       → template (렌더링)
         → deploy (배포)
   ```

3. **사용 시나리오**
   - values로 불가능한 변경
   - 사이드카 컨테이너 추가
   - 보안 설정 강화
   - 모니터링 통합

4. **주의사항**
   - 패치 파일 경로 정확히 지정
   - YAML 문법 엄격히 준수
   - Helm 템플릿 구문 유효성 확인
   - build 단계에서 패치 적용 확인

5. **디버깅 팁**
   - `sbkube build --verbose`로 로그 확인
   - 패치 전후 diff로 비교
   - `sbkube template`로 최종 결과 검증
