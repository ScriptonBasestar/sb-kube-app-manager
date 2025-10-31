# 🎨 Helm 차트 커스터마이징

> **난이도**: ⭐⭐⭐ 고급 **소요 시간**: 25분 **사전 요구사항**: [01-getting-started.md](01-getting-started.md) 완료

______________________________________________________________________

## 📋 학습 목표

- ✅ Overrides를 사용한 차트 수정
- ✅ Removes를 사용한 리소스 제거
- ✅ 복잡한 YAML 경로 탐색
- ✅ 커스터마이징 검증 및 디버깅

______________________________________________________________________

## 시나리오: 기본 차트를 프로젝트에 맞게 수정

**배경**: Grafana 차트를 프로젝트 요구사항에 맞게 수정해야 합니다.

**요구사항**:

- 리소스 제한 추가
- Prometheus ServiceMonitor 추가
- 불필요한 ConfigMap 제거
- 특정 라벨 수정

______________________________________________________________________

## Step 1: 기본 차트 구조 파악

### 1.1 차트 다운로드

```bash
mkdir customization-tutorial
cd customization-tutorial

# 프로젝트 초기화
sbkube init --name custom-redis --template basic --non-interactive
```

### 1.2 config.yaml 작성

```yaml
# config.yaml
namespace: custom-demo

apps:
  grafana:
    type: helm
    chart: grafana/grafana
    version: 6.50.0
    enabled: true
    values:
      - grafana-values.yaml
```

### 1.3 sources.yaml 작성

```yaml
# sources.yaml

# 클러스터 설정 (필수, v0.4.10+)
kubeconfig: ~/.kube/config
kubeconfig_context: my-k3s-cluster
cluster: custom-demo-cluster  # 선택, 문서화 목적

# Helm 리포지토리
helm_repos:
  grafana:
    url: https://grafana.github.io/helm-charts
```

### 1.4 차트 준비 및 템플릿 확인

```bash
# 차트 다운로드
sbkube prepare

# 템플릿 렌더링
sbkube template --output-dir /tmp/grafana-original

# 생성된 YAML 파일 확인
ls /tmp/grafana-original/grafana/templates/
# deployment.yaml
# service.yaml
# configmap.yaml
# secret.yaml
# ...
```

______________________________________________________________________

## Step 2: Overrides로 리소스 추가

### 2.1 ServiceMonitor 추가

**목표**: Prometheus Operator의 ServiceMonitor 리소스를 추가합니다.

#### `config.yaml` 수정

```yaml
namespace: custom-demo

apps:
  grafana:
    type: helm
    chart: grafana/grafana
    version: 6.50.0
    enabled: true
    values:
      - grafana-values.yaml

    # Overrides 설정
    overrides:
      - path: templates/servicemonitor.yaml
        content: |
          apiVersion: monitoring.coreos.com/v1
          kind: ServiceMonitor
          metadata:
            name: {{ include "common.names.fullname" . }}
            namespace: {{ .Release.Namespace }}
            labels:
              {{- include "common.labels.standard" . | nindent 4 }}
          spec:
            selector:
              matchLabels:
                {{- include "common.labels.matchLabels" . | nindent 8 }}
                app.kubernetes.io/component: master
            endpoints:
              - port: tcp-redis
                interval: 30s
```

#### 빌드 및 검증

```bash
# Overrides 적용
sbkube build

# 템플릿 확인
sbkube template --output-dir /tmp/redis-custom

# ServiceMonitor 파일 확인
cat /tmp/redis-custom/redis/templates/servicemonitor.yaml
```

**예상 결과**:

```yaml
apiVersion: monitoring.coreos.com/v1
kind: ServiceMonitor
metadata:
  name: redis-custom-demo
  namespace: custom-demo
  labels:
    app.kubernetes.io/name: redis
    # ...
```

______________________________________________________________________

## Step 3: Overrides로 기존 리소스 수정

### 3.1 Deployment에 리소스 제한 추가

**문제**: 기본 Deployment에는 `resources` 필드가 없거나 비어있습니다.

#### YAML 경로 찾기

```bash
# 기본 Deployment 구조 확인
cat charts/redis/redis/templates/master/application.yaml | grep -A 20 "kind: Deployment"
```

**예상 구조**:

```yaml
apiVersion: apps/v1
kind: Deployment
metadata:
  name: {{ include "common.names.fullname" . }}-master
spec:
  template:
    spec:
      containers:
        - name: redis
          image: ...
          # resources 필드가 여기 있어야 함
```

#### Overrides 적용

```yaml
# config.yaml
apps:
  redis:
    # ...
    overrides:
      # 기존 ServiceMonitor 유지
      - path: templates/servicemonitor.yaml
        content: |
          # (이전 내용 동일)

      # Deployment 수정
      - path: templates/master/application.yaml
        content: |
          apiVersion: apps/v1
          kind: Deployment
          metadata:
            name: {{ include "common.names.fullname" . }}-master
            namespace: {{ .Release.Namespace }}
            labels:
              {{- include "common.labels.standard" . | nindent 4 }}
              app.kubernetes.io/component: master
          spec:
            replicas: {{ .Values.master.replicaCount }}
            selector:
              matchLabels:
                {{- include "common.labels.matchLabels" . | nindent 8 }}
                app.kubernetes.io/component: master
            template:
              metadata:
                labels:
                  {{- include "common.labels.standard" . | nindent 10 }}
                  app.kubernetes.io/component: master
              spec:
                containers:
                  - name: redis
                    image: {{ .Values.image.registry }}/{{ .Values.image.repository }}:{{ .Values.image.tag }}
                    imagePullPolicy: {{ .Values.image.pullPolicy }}
                    ports:
                      - name: tcp-redis
                        containerPort: 6379
                    # ⭐ 리소스 제한 추가
                    resources:
                      requests:
                        cpu: 100m
                        memory: 128Mi
                      limits:
                        cpu: 200m
                        memory: 256Mi
```

#### 검증

```bash
sbkube build
sbkube template --output-dir /tmp/redis-custom

# Deployment의 resources 필드 확인
cat /tmp/redis-custom/redis/templates/master/application.yaml | grep -A 10 "resources:"
```

______________________________________________________________________

## Step 4: Removes로 불필요한 리소스 제거

### 4.1 ConfigMap 제거

**시나리오**: 기본 차트의 `configuration.yaml` ConfigMap은 사용하지 않습니다.

#### `config.yaml` 수정

```yaml
apps:
  redis:
    # ...
    overrides:
      # (기존 내용 유지)

    # Removes 설정
    removes:
      - templates/master/configmap.yaml
      - templates/replica/configmap.yaml
```

#### 검증

```bash
sbkube build
sbkube template --output-dir /tmp/redis-custom

# ConfigMap 파일이 없는지 확인
ls /tmp/redis-custom/redis/templates/master/
# configmap.yaml이 없어야 함
```

______________________________________________________________________

## Step 5: 복잡한 수정 - 라벨 오버라이드

### 5.1 모든 리소스의 라벨 통일

**목표**: 모든 리소스에 `environment: production` 라벨을 추가합니다.

#### Overrides 전략

**방법 1**: 각 리소스 파일을 개별 오버라이드 (권장하지 않음 - 너무 많음)

**방법 2**: `_helpers.tpl`을 오버라이드하여 공통 라벨 수정

```yaml
# config.yaml
apps:
  redis:
    # ...
    overrides:
      # 기존 overrides 유지

      # _helpers.tpl 수정
      - path: templates/_helpers.tpl
        content: |
          {{/* Common labels */}}
          {{- define "common.labels.standard" -}}
          app.kubernetes.io/name: {{ include "common.names.name" . }}
          helm.sh/chart: {{ include "common.names.chart" . }}
          app.kubernetes.io/instance: {{ .Release.Name }}
          app.kubernetes.io/managed-by: {{ .Release.Service }}
          environment: production
          {{- end -}}

          {{/* Match labels */}}
          {{- define "common.labels.matchLabels" -}}
          app.kubernetes.io/name: {{ include "common.names.name" . }}
          app.kubernetes.io/instance: {{ .Release.Name }}
          {{- end -}}
```

#### 검증

```bash
sbkube build
sbkube template --output-dir /tmp/redis-custom

# 모든 리소스에 environment: production 라벨이 있는지 확인
grep -r "environment: production" /tmp/redis-custom/redis/templates/
```

______________________________________________________________________

## Step 6: 실전 배포 및 검증

### 6.1 최종 설정 확인

```yaml
# config.yaml (전체)
namespace: custom-demo

apps:
  grafana:
    type: helm
    chart: grafana/grafana
    version: 6.50.0
    enabled: true
    values:
      - grafana-values.yaml

    overrides:
      # ServiceMonitor 추가
      - path: templates/servicemonitor.yaml
        content: |
          apiVersion: monitoring.coreos.com/v1
          kind: ServiceMonitor
          metadata:
            name: {{ include "common.names.fullname" . }}
            namespace: {{ .Release.Namespace }}
            labels:
              {{- include "common.labels.standard" . | nindent 4 }}
          spec:
            selector:
              matchLabels:
                {{- include "common.labels.matchLabels" . | nindent 8 }}
            endpoints:
              - port: tcp-redis
                interval: 30s

      # Deployment 수정 (리소스 제한)
      - path: templates/master/application.yaml
        content: |
          # (이전 섹션 내용)

    removes:
      - templates/master/configmap.yaml
      - templates/replica/configmap.yaml
```

### 6.2 배포

```bash
# Dry-run으로 최종 확인
sbkube apply --dry-run

# 실제 배포
sbkube apply
```

### 6.3 Kubernetes 리소스 검증

```bash
# ServiceMonitor 확인
kubectl get servicemonitor -n custom-demo
# NAME                AGE
# redis-custom-demo   10s

# Deployment의 리소스 제한 확인
kubectl get deployment redis-custom-demo-master -n custom-demo -o yaml | grep -A 10 "resources:"

# ConfigMap이 없는지 확인
kubectl get configmap -n custom-demo
# 기본 ConfigMap만 있고, redis-configuration은 없어야 함

# 라벨 확인
kubectl get all -n custom-demo --show-labels | grep "environment=production"
```

______________________________________________________________________

## Step 7: 디버깅 팁

### 7.1 Overrides 적용 확인

```bash
# 빌드 후 차트 디렉토리 확인
ls -la charts-built/redis/templates/

# Overrides된 파일의 내용 확인
cat charts-built/redis/templates/servicemonitor.yaml

# 차이 비교
diff charts/redis/redis/templates/master/application.yaml \
     charts-built/redis/templates/master/application.yaml
```

### 7.2 Helm Template 디버깅

```bash
# Helm 직접 사용하여 템플릿 렌더링
helm template test-release charts-built/redis \
  --namespace custom-demo \
  --values redis-values.yaml \
  --debug
```

### 7.3 YAML 문법 오류 확인

```bash
# YAML 파일 검증
yamllint charts-built/redis/templates/servicemonitor.yaml

# 또는 Python으로
python3 -c "import yaml; yaml.safe_load(open('charts-built/redis/templates/servicemonitor.yaml'))"
```

______________________________________________________________________

## Step 8: 고급 커스터마이징 패턴

### 8.1 조건부 Overrides

**시나리오**: 개발 환경에서만 Debug Sidecar 추가

```yaml
# config.yaml
apps:
  redis:
    # ...
    overrides:
      - path: templates/master/application.yaml
        content: |
          # (기본 Deployment 내용)
          spec:
            template:
              spec:
                containers:
                  - name: redis
                    # (기본 컨테이너)
                  {{- if eq .Values.environment "dev" }}
                  - name: debug-sidecar
                    image: busybox:latest
                    command: ["/bin/sh", "-c", "tail -f /dev/null"]
                  {{- end }}
```

```yaml
# redis-values.yaml
environment: dev
```

### 8.2 Patch 스타일 Overrides

**시나리오**: 일부 필드만 수정하고 나머지는 유지

**방법**: Strategic Merge Patch 활용 (Kubernetes 네이티브)

```yaml
# config.yaml
apps:
  redis:
    # ...
    overrides:
      - path: templates/master/application.yaml
        merge_strategy: strategic  # (예정된 기능)
        content: |
          apiVersion: apps/v1
          kind: Deployment
          metadata:
            name: {{ include "common.names.fullname" . }}-master
          spec:
            template:
              spec:
                containers:
                  - name: redis
                    resources:
                      requests:
                        cpu: 100m
                        memory: 128Mi
```

______________________________________________________________________

## 체크리스트

### Overrides 작성 시 ✅

- [ ] 기본 차트의 템플릿 구조를 먼저 확인
- [ ] Helm 템플릿 문법 ({{ }}, {{- }}) 올바르게 사용
- [ ] YAML 들여쓰기 정확히 유지
- [ ] `sbkube build` 후 `charts-built/` 디렉토리 확인
- [ ] `sbkube template`로 최종 렌더링 검증

### Removes 사용 시 ✅

- [ ] 제거할 파일의 정확한 경로 확인
- [ ] 의존성 있는 리소스는 함께 제거
- [ ] `sbkube template` 출력에서 누락 확인

### 배포 전 ✅

- [ ] `sbkube apply --dry-run` 실행
- [ ] Helm 템플릿 오류 확인
- [ ] YAML 문법 검증
- [ ] 리소스 제한 및 보안 설정 확인

______________________________________________________________________

## 트러블슈팅

### 문제: Overrides 적용 안 됨

**원인**: 빌드 단계를 건너뜀

**해결**:

```bash
# build 단계를 명시적으로 실행
sbkube build

# 또는 apply로 전체 실행
sbkube apply
```

### 문제: Helm 템플릿 오류

**원인**: Helm 템플릿 문법 오류, 함수 호출 실패

**해결**:

```bash
# Helm 직접 템플릿 렌더링으로 디버깅
helm template test charts-built/redis --debug

# 오류 메시지에서 라인 번호 확인
# templates/servicemonitor.yaml:5:10: executing "templates/servicemonitor.yaml" at <include "common.labels.standard" .>: error calling include: template: redis/templates/_helpers.tpl:12:14: executing "common.labels.standard" at <.Values.commonLabels>: nil pointer evaluating interface {}.commonLabels
```

### 문제: Removes 후 배포 실패

**원인**: 제거한 리소스가 다른 리소스에 참조됨

**해결**:

```bash
# 제거하려는 리소스가 참조되는지 확인
grep -r "configmap.yaml" charts/redis/redis/templates/
```

______________________________________________________________________

## 다음 단계

- **[05-troubleshooting.md](05-troubleshooting.md)** - 문제 해결 가이드
- **Helm Chart 개발 가이드** - 자체 차트 작성

______________________________________________________________________

**작성자**: SBKube Documentation Team **버전**: v0.5.0 **최종 업데이트**: 2025-10-31
