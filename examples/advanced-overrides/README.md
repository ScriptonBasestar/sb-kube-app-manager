# Advanced Chart Customization

Helm 차트를 고급 방식으로 커스터마이징하는 예제입니다.

## 📋 개요

이 예제는 SBKube의 `overrides`와 `removes` 기능을 사용하여 Helm 차트를 정교하게 커스터마이징하는 방법을 보여줍니다.

### 주요 기능

- **overrides**: 차트 템플릿 파일 **전체 교체**
- **removes**: 차트 템플릿 파일/디렉토리 **삭제** (Glob 패턴 지원)
- **values**: Helm values 파일을 통한 기본 커스터마이징
- **set_values**: 명령줄 스타일 값 오버라이드

---

## 📁 디렉토리 구조

```
advanced-overrides/
├── config.yaml               # 앱 설정
├── sources.yaml              # Helm 리포지토리
├── grafana-values.yaml       # Grafana 기본 values
├── prometheus-values.yaml    # Prometheus 기본 values
├── overrides/                # 커스텀 템플릿 파일들
│   └── grafana/
│       └── templates/
│           ├── deployment.yaml    # 사이드카가 포함된 Deployment
│           └── service.yaml       # 추가 포트가 포함된 Service
└── README.md                 # 이 문서
```

---

## 🔧 사용 시나리오

### 시나리오 1: 사이드카 컨테이너 추가 (Grafana)

**목적**: Grafana Deployment에 로그 수집 사이드카 추가

**방법**: `overrides`를 사용하여 `templates/deployment.yaml` 파일 전체 교체

```yaml
# config.yaml
grafana:
  overrides:
    - templates/deployment.yaml  # 사이드카가 포함된 커스텀 Deployment
```

**커스텀 파일 위치**: `overrides/grafana/templates/deployment.yaml`

### 시나리오 2: 불필요한 리소스 제거 (Prometheus)

**목적**: Prometheus에서 사용하지 않는 컴포넌트 제거

**방법**: `removes`를 사용하여 디렉토리 단위 삭제

```yaml
# config.yaml
prometheus:
  removes:
    - templates/pushgateway/         # Pushgateway 미사용
    - templates/kube-state-metrics/  # 별도 설치
    - templates/node-exporter/       # 별도 설치
```

### 시나리오 3: Glob 패턴 활용 (Redis)

**목적**: Standalone 모드에서 Replica 관련 파일 제거

**방법**: `removes`에서 Glob 패턴 사용

```yaml
# config.yaml
redis:
  removes:
    - templates/replicas/**/*        # replicas 디렉토리 전체 제거
    - templates/*-pdb.yaml          # PodDisruptionBudget 제거
```

---

## 🚀 실행 방법

### 전체 워크플로우

```bash
# 1단계: Helm 차트 다운로드
sbkube prepare --app-dir examples/advanced-overrides

# 2단계: 빌드 (overrides/removes 적용)
sbkube build --app-dir examples/advanced-overrides

# 커스터마이징 확인:
cat build/grafana/templates/deployment.yaml | grep log-forwarder
ls build/prometheus/templates/  # pushgateway/ 디렉토리가 없음

# 3단계: 템플릿 생성 (검증)
sbkube template --app-dir examples/advanced-overrides --output-dir rendered

# 4단계: 배포
sbkube deploy --app-dir examples/advanced-overrides --namespace advanced-demo

# 또는 한 번에
sbkube apply --app-dir examples/advanced-overrides --namespace advanced-demo
```

### 개별 앱 테스트

```bash
# Grafana만 배포
sbkube apply --app-dir examples/advanced-overrides --namespace advanced-demo --app grafana

# Prometheus만 배포
sbkube apply --app-dir examples/advanced-overrides --namespace advanced-demo --app prometheus
```

---

## 📋 실전 패턴

### 패턴 1: 파일 전체 교체 (overrides)

**사용 시기**:
- values 파일로 불가능한 변경 (컨테이너 추가, 포트 추가 등)
- 템플릿 로직 자체를 변경해야 할 때

**예시**:
```yaml
grafana:
  overrides:
    - templates/deployment.yaml
    - templates/service.yaml
```

**주의사항**:
- 원본 차트 버전 업데이트 시 overrides 파일도 함께 업데이트 필요
- 파일 경로는 차트 루트 기준 상대 경로

### 패턴 2: 디렉토리 삭제 (removes)

**사용 시기**:
- 불필요한 컴포넌트 제거 (테스트, 예제 등)
- 리소스 절약

**예시**:
```yaml
prometheus:
  removes:
    - templates/pushgateway/
    - templates/tests/
```

### 패턴 3: Glob 패턴 활용 (removes)

**사용 시기**:
- 패턴 기반 대량 파일 제거
- 특정 타입의 리소스만 선택적 제거

**예시**:
```yaml
redis:
  removes:
    - templates/replicas/**/*    # 하위 모든 파일
    - templates/*-pdb.yaml       # PDB만 제거
    - templates/**/*-test-*.yaml # 모든 테스트 파일
```

**지원 패턴**:
- `*`: 단일 레벨 와일드카드
- `**`: 재귀 디렉토리 매칭
- `?`: 단일 문자 매칭

### 패턴 4: 보안 강화

**목적**: SecurityContext, NetworkPolicy 추가

**방법**:
1. 원본 Deployment에 SecurityContext 추가
2. `overrides/`에 커스텀 Deployment 파일 작성
3. `overrides`로 파일 교체

**예시** (`overrides/prometheus/templates/server/deploy.yaml`):
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

---

## 🎯 현재 기능 vs 제한사항

### ✅ 현재 사용 가능

| 기능 | 설명 | 예제 |
|------|------|------|
| **파일 전체 교체** | `overrides` | `templates/deployment.yaml` |
| **파일 삭제** | `removes` | `templates/tests/` |
| **Glob 패턴 삭제** | `removes` | `templates/**/*-test.yaml` |
| **Values 오버라이드** | `values` | `grafana-values.yaml` |
| **CLI 스타일 값 설정** | `set_values` | `service.type=LoadBalancer` |

### ⚠️ 제한사항

| 기능 | 현재 상태 | 대안 |
|------|----------|------|
| **부분 패칭** | ❌ 미지원 | `overrides`로 파일 전체 교체 |
| **Strategic Merge** | ❌ 미지원 | `overrides`로 파일 전체 교체 |
| **JSON Patch** | ❌ 미지원 | `overrides`로 파일 전체 교체 |
| **파일 생성** | ⚠️ `overrides`로 가능 | 커스텀 파일을 `overrides/`에 작성 |

**미래 계획**: 부분 패칭 기능은 v0.6.0 이후 릴리스에서 검토 예정

---

## 💡 모범 사례

### 1. 버전 관리

```bash
# overrides 파일도 Git에 커밋
git add overrides/
git commit -m "Add custom Grafana deployment with sidecar"
```

### 2. 차트 업데이트 시 주의

```bash
# 차트 버전 업데이트 전 diff 확인
helm pull grafana/grafana --version 10.1.2 --untar
helm pull grafana/grafana --version 10.2.0 --untar

diff grafana-10.1.2/templates/deployment.yaml \
     grafana-10.2.0/templates/deployment.yaml
```

### 3. 검증

```bash
# template 단계에서 미리 확인
sbkube template --app-dir examples/advanced-overrides --output-dir rendered

# 렌더링된 매니페스트 검증
kubectl apply --dry-run=client -f rendered/grafana/
```

### 4. 문서화

```yaml
# config.yaml에 주석으로 이유 명시
grafana:
  overrides:
    - templates/deployment.yaml  # fluent-bit 사이드카 추가 (로그 수집)
  removes:
    - templates/tests/           # 테스트 리소스 불필요
```

---

## 📚 관련 예제

- [override-with-files](../override-with-files/) - `overrides`와 `removes` 기본 예제
- [app-types/01-helm](../app-types/01-helm/) - Helm 앱 타입 기본
- [advanced-features/](../advanced-features/) - Helm 고급 설정

---

## 🔑 핵심 정리

1. **overrides**: 파일 전체를 교체하여 정교한 커스터마이징
2. **removes**: 불필요한 파일/디렉토리 제거 (Glob 패턴 지원)
3. **values**: Helm 표준 방식의 기본 커스터마이징
4. **조합**: overrides + removes + values를 함께 사용하여 복잡한 요구사항 해결

---

**작성일**: 2025-10-31
**버전**: SBKube v0.5.0+
**상태**: 실제 동작 예제
