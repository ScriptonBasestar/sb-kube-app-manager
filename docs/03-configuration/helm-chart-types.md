# Helm Chart Types in SBKube

SBKube은 다양한 형태의 Helm 차트를 지원합니다.

---

## 📦 지원하는 Chart 형식

### 1. Remote Chart (원격 차트)

Helm 리포지토리에서 자동으로 pull 후 install합니다.

```yaml
apps:
  grafana:
    type: helm
    chart: grafana/grafana  # "repo/chart" 형식
    version: 6.50.0         # 선택적
    values:
      - grafana.yaml
```

**동작 방식**:

1. `sbkube prepare`: `grafana/grafana` 차트를 `charts/grafana/` 디렉토리에 pull
1. `sbkube deploy`: `charts/grafana/grafana/` 경로의 차트로 install

---

### 2. Local Chart (로컬 차트)

이미 존재하는 로컬 차트를 직접 사용합니다.

```yaml
apps:
  my-app:
    type: helm
    chart: ./charts/my-app  # 상대 경로
    values:
      - values.yaml
```

**동작 방식**:

1. `sbkube prepare`: 로컬 차트이므로 **건너뜀** (prepare 불필요)
1. `sbkube deploy`: `<app-dir>/charts/my-app/` 경로의 차트로 직접 install

**사용 사례**:

- 커스텀 Helm 차트 개발 중
- Git에서 클론한 차트를 수동으로 수정한 경우
- 로컬에서 작성한 차트

---

### 3. Absolute Path Chart (절대 경로 차트)

절대 경로로 차트를 지정합니다.

```yaml
apps:
  system-chart:
    type: helm
    chart: /opt/helm-charts/system-chart
    values:
      - values.yaml
```

**동작 방식**:

1. `sbkube prepare`: 절대 경로이므로 **건너뜀**
1. `sbkube deploy`: `/opt/helm-charts/system-chart/` 경로의 차트로 install

---

## ⚙️ Helm 배포 옵션

Helm 타입은 기본적으로 `helm upgrade --install --wait --timeout 5m` 형태로 실행됩니다.
앱 단위로 다음 필드를 조정해 동작을 세밀하게 제어할 수 있습니다.

- `wait` (기본값 `true`): 리소스가 준비 상태가 될 때까지 대기합니다. `false`로 지정하면 설치 완료 직후 다음 앱으로 넘어갑니다.
- `timeout` (기본값 `"5m"`): `wait: true`일 때 사용할 대기 시간 상한입니다. Helm의 시간 형식을 그대로 사용합니다. (예: `"90s"`, `"10m"`)
- `atomic` (기본값 `false`): 설치/업그레이드가 실패하면 자동 롤백합니다.

```yaml
apps:
  grafana:
    type: helm
    chart: grafana/grafana
    wait: false          # 준비 완료를 기다리지 않고 즉시 다음 앱 수행
    timeout: "2m"        # wait가 켜져 있을 때만 의미
    atomic: true         # 실패 시 롤백 시도
```

> **주의**
> `depends_on`은 배포 순서만 보장합니다. `wait: false`로 설정한 앱이 종속된 리소스가 준비되기 전에 다음 앱으로 넘어갈 수 있으므로, 필요하면 `kubectl rollout status`나 `exec` 앱을 활용해 상태를 직접 검증하세요.

---

## 🎯 실전 예제

### 예제 1: Remote + Local 혼합

```yaml
# config.yaml
namespace: production

apps:
  # Remote chart (자동 pull)
  grafana:
    type: helm
    chart: grafana/grafana
    version: 6.50.0
    values:
      - grafana-values.yaml

  # Local chart (직접 사용)
  backend:
    type: helm
    chart: ./charts/backend
    values:
      - backend-values.yaml
    depends_on:
      - grafana

  # Git에서 가져온 chart
  monitoring:
    type: helm
    chart: ./charts/prometheus-stack
    values:
      - monitoring-values.yaml
```

**디렉토리 구조**:

```
myapp/
├── config.yaml
├── redis-values.yaml
├── backend-values.yaml
├── monitoring-values.yaml
└── charts/
    ├── backend/          # 로컬 커스텀 차트
    │   ├── Chart.yaml
    │   ├── values.yaml
    │   └── templates/
    └── prometheus-stack/ # Git에서 클론한 차트
        ├── Chart.yaml
        └── ...
```

**실행**:

```bash
# prepare: grafana만 pull (backend, monitoring은 건너뜀)
sbkube prepare --app-dir myapp

# deploy: 모두 배포 (의존성 순서: grafana → backend, monitoring)
sbkube deploy --app-dir myapp
```

---

## 🔍 Chart 타입 판단 로직

SBKube는 다음 규칙으로 chart 타입을 자동 판단합니다:

| chart 값 | 타입 | 예시 | |----------|------|------| | `repo/chart` | Remote | `grafana/grafana` | | `./path` | Local (상대) |
`./charts/my-app` | | `/path` | Local (절대) | `/opt/charts/app` | | `chart-name` | Local (상대) | `my-chart`
(=`./my-chart`) |

**구현 코드**:

```python
def is_remote_chart(self) -> bool:
    # 로컬 경로 패턴
    if self.chart.startswith("./") or self.chart.startswith("/"):
        return False
    # repo/chart 형식
    if "/" in self.chart and not self.chart.startswith("."):
        return True
    # chart만 있는 경우는 로컬로 간주
    return False
```

---

## 🚨 주의 사항

### Remote Chart

- **sources.yaml 필수**: Helm repo URL이 정의되어 있어야 함
- **version 권장**: 버전 고정으로 재현성 보장
- **준비 필요**: `sbkube prepare` 또는 `sbkube apply` 실행 필요

### Local Chart

- **경로 정확성**: chart 디렉토리가 실제로 존재해야 함
- **Chart.yaml 필수**: 유효한 Helm 차트 구조여야 함
- **prepare 불필요**: 로컬 차트는 prepare 단계 건너뜀

---

## 💡 Best Practices

### 1. 개발/운영 환경 분리

```yaml
# dev-config.yaml
apps:
  backend:
    type: helm
    chart: ./charts/backend  # 로컬 개발 차트
    values:
      - dev-values.yaml

# prod-config.yaml
apps:
  backend:
    type: helm
    chart: myorg/backend  # 운영 레지스트리 차트
    version: 1.2.3
    values:
      - prod-values.yaml
```

### 2. 버전 고정

```yaml
apps:
  grafana:
    type: helm
    chart: grafana/grafana
    version: 6.50.0  # 반드시 버전 명시!
```

### 3. 의존성 명시

```yaml
apps:
  cloudnative-pg:
    type: helm
    chart: cloudnative-pg/cloudnative-pg

  backend:
    type: helm
    chart: ./charts/backend
    depends_on:
      - cloudnative-pg  # 명시적 의존성
```

---

## 🔗 참고 문서

- [SBKube Configuration Schema](./config-schema-v3.md)
- [Migration Guide](../MIGRATION_V3.md)
- [Helm Official Docs](https://helm.sh/docs/)
