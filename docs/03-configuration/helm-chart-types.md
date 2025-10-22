# Helm Chart Types in SBKube v0.3.0

SBKube v0.3.0은 다양한 형태의 Helm 차트를 지원합니다.

---

## 📦 지원하는 Chart 형식

### 1. Remote Chart (원격 차트)

Helm 리포지토리에서 자동으로 pull 후 install합니다.

```yaml
apps:
  redis:
    type: helm
    chart: bitnami/redis  # "repo/chart" 형식
    version: 17.13.2      # 선택적
    values:
      - redis.yaml
```

**동작 방식**:
1. `sbkube prepare`: `bitnami/redis` 차트를 `charts/redis/` 디렉토리에 pull
2. `sbkube deploy`: `charts/redis/redis/` 경로의 차트로 install

**sources.yaml 예시**:
```yaml
helm:
  bitnami: https://charts.bitnami.com/bitnami
```

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
2. `sbkube deploy`: `<app-dir>/charts/my-app/` 경로의 차트로 직접 install

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
2. `sbkube deploy`: `/opt/helm-charts/system-chart/` 경로의 차트로 install

---

## 🔀 워크플로우 비교

### Remote Chart 워크플로우

```bash
# 1. prepare: chart pull
sbkube prepare --app-dir myapp
# → charts/redis/ 디렉토리에 chart 다운로드

# 2. (선택적) chart 커스터마이징
vim charts/redis/redis/values.yaml

# 3. deploy: install
sbkube deploy --app-dir myapp

# 또는 한 번에
sbkube apply --app-dir myapp
```

### Local Chart 워크플로우

```bash
# 1. prepare: 건너뜀 (로컬 차트)
sbkube prepare --app-dir myapp
# → "Local chart detected, skipping prepare"

# 2. deploy: 직접 install
sbkube deploy --app-dir myapp

# 또는 한 번에 (prepare 자동 건너뜀)
sbkube apply --app-dir myapp
```

---

## 🎯 실전 예제

### 예제 1: Remote + Local 혼합

```yaml
# config.yaml
namespace: production

apps:
  # Remote chart (자동 pull)
  redis:
    type: helm
    chart: bitnami/redis
    version: 17.13.2
    values:
      - redis-values.yaml

  # Local chart (직접 사용)
  backend:
    type: helm
    chart: ./charts/backend
    values:
      - backend-values.yaml
    depends_on:
      - redis

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
# prepare: redis만 pull (backend, monitoring은 건너뜀)
sbkube prepare --app-dir myapp

# deploy: 모두 배포 (의존성 순서: redis → backend, monitoring)
sbkube deploy --app-dir myapp
```

---

### 예제 2: Pull 후 커스터마이징

```yaml
# config.yaml
apps:
  redis:
    type: helm
    chart: bitnami/redis
    version: 17.13.2
    values:
      - redis.yaml
```

**워크플로우**:
```bash
# 1. Chart pull
sbkube prepare --app-dir myapp

# 2. Chart 커스터마이징 (예: ConfigMap 추가)
cat << EOF >> charts/redis/redis/templates/custom-configmap.yaml
apiVersion: v1
kind: ConfigMap
metadata:
  name: redis-custom-config
data:
  custom.conf: |
    maxmemory 2gb
    maxmemory-policy allkeys-lru
EOF

# 3. 수정된 차트로 배포
sbkube deploy --app-dir myapp
```

---

### 예제 3: 로컬 차트 개발

```yaml
# config.yaml
apps:
  myapp:
    type: helm
    chart: ./myapp-chart
    values:
      - dev-values.yaml
```

**차트 생성**:
```bash
# Helm 차트 스캐폴딩
cd myapp/
helm create myapp-chart

# 차트 수정
vim myapp-chart/Chart.yaml
vim myapp-chart/templates/deployment.yaml

# 바로 배포 (prepare 불필요)
sbkube deploy --app-dir .
```

---

## 🔍 Chart 타입 판단 로직

SBKube는 다음 규칙으로 chart 타입을 자동 판단합니다:

| chart 값 | 타입 | 예시 |
|----------|------|------|
| `repo/chart` | Remote | `bitnami/redis` |
| `./path` | Local (상대) | `./charts/my-app` |
| `/path` | Local (절대) | `/opt/charts/app` |
| `chart-name` | Local (상대) | `my-chart` (=`./my-chart`) |

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

## ⚙️ 고급 사용법

### 1. Pull과 Deploy 분리 실행

```bash
# 1단계: 모든 remote chart pull
sbkube prepare --app-dir myapp

# 2단계: Chart 검토 및 수정
ls -la charts/

# 3단계: 배포
sbkube deploy --app-dir myapp
```

### 2. 특정 앱만 준비/배포

```bash
# 특정 앱만 prepare
sbkube prepare --app-dir myapp --app redis

# 특정 앱만 deploy
sbkube deploy --app-dir myapp --app backend
```

### 3. Dry-run으로 테스트

```bash
# 배포 전 검증
sbkube deploy --app-dir myapp --dry-run
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
  redis:
    type: helm
    chart: bitnami/redis
    version: 17.13.2  # 반드시 버전 명시!
```

### 3. 의존성 명시

```yaml
apps:
  postgres:
    type: helm
    chart: bitnami/postgresql

  backend:
    type: helm
    chart: ./charts/backend
    depends_on:
      - postgres  # 명시적 의존성
```

---

## 🔗 참고 문서

- [SBKube Configuration Schema](./config-schema-v3.md)
- [Migration Guide](../MIGRATION_V3.md)
- [Helm Official Docs](https://helm.sh/docs/)
