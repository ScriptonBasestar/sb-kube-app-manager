# Overrides - Helm 차트 커스터마이징

SBKube의 **overrides**와 **removes** 기능을 사용하여 Helm 차트를 커스터마이징하는 예제입니다.

## 📋 목차

- [개요](#-개요)
- [디렉토리 구조](#-디렉토리-구조)
- [핵심 개념](#-핵심-개념)
- [설정 상세](#-설정-상세)
- [워크플로우](#-워크플로우)
- [실전 예제](#-실전-예제)
- [고급 사용법](#-고급-사용법)

---

## 🎯 개요

이 디렉토리는 Helm 차트를 커스터마이징하는 두 가지 방법을 보여줍니다:

| 하위 디렉토리 | 설명 | 난이도 |
|------------|------|--------|
| **[overrides/](overrides/)** | 기본 overrides/removes 예제 | ⭐⭐ |
| **[advanced-example/](advanced-example/)** | 고급 커스터마이징 (상세 문서 포함) | ⭐⭐⭐ |

---

## 📁 디렉토리 구조

### 기본 예제 (overrides/)

```
overrides/
├── config.yaml              # SBKube 설정
└── redis/                   # 오버라이드 파일
    ├── values.yaml          # 커스텀 values.yaml
    └── templates/
        └── service.yaml     # 커스텀 service.yaml
```

### 고급 예제 (advanced-example/)

```
advanced-example/
├── config.yaml              # SBKube 설정 (상세 옵션 포함)
├── redis.yaml               # Helm values
├── sources.yaml             # Helm 리포지토리 설정
├── overrides/
│   └── redis/
│       ├── values.yaml
│       └── templates/
│           └── service.yaml
└── README.md                # 상세 워크플로우 설명
```

---

## 🔑 핵심 개념

### Overrides

**목적**: Helm 차트의 특정 파일을 커스텀 버전으로 **교체**

**사용 시나리오**:
- `values.yaml`: 기본값 변경
- `templates/service.yaml`: Service 타입 변경 (LoadBalancer → ClusterIP)
- `templates/deployment.yaml`: 환경변수 추가, 리소스 제한 변경
- `templates/configmap.yaml`: ConfigMap 내용 수정

**작동 방식**:
1. `prepare` 단계: 원본 차트 다운로드 (`charts/<app-name>/<chart-name>/`)
2. `build` 단계: 오버라이드 적용
   - 원본 차트 → `build/<app-name>/` 복사
   - `overrides/<app-name>/` 파일로 교체

### Removes

**목적**: 불필요한 파일/디렉토리 **제거**

**사용 시나리오**:
- `README.md`: 문서 파일 제거 (배포에 불필요)
- `templates/ingress.yaml`: Ingress 리소스 제거
- `templates/tests/`: 테스트 파일 디렉토리 제거
- `files/aaa.conf`: 불필요한 설정 파일 제거

**작동 방식**:
- `build` 단계에서 `removes` 목록의 파일/디렉토리 삭제

---

## ⚙️ 설정 상세

### config.yaml (기본 예제)

```yaml
namespace: demo

apps:
  redis:
    type: helm
    chart: bitnami/redis
    version: 17.13.2
    values:
      - redis.yaml

    # Overrides: overrides/redis/ 디렉토리의 파일로 차트 파일 교체
    overrides:
      - values.yaml             # values.yaml 교체
      - templates/service.yaml  # service.yaml 교체

    # Removes: 빌드 시 불필요한 파일/디렉토리 제거
    removes:
      - README.md
      - templates/ingress.yaml

    # 추가 옵션
    labels:
      app.kubernetes.io/managed-by: sbkube
      environment: demo
    annotations:
      sbkube.io/version: "0.3.0"

    create_namespace: true
    wait: true
    timeout: 10m
    atomic: true
```

### 주요 필드

| 필드 | 타입 | 설명 |
|-----|------|------|
| `overrides` | list[string] | 교체할 파일 목록 (차트 루트 기준 상대 경로) |
| `removes` | list[string] | 제거할 파일/디렉토리 목록 (차트 루트 기준 상대 경로) |
| `labels` | dict | 추가할 레이블 |
| `annotations` | dict | 추가할 어노테이션 |
| `create_namespace` | bool | 네임스페이스 자동 생성 여부 |
| `wait` | bool | 배포 완료 대기 여부 |
| `timeout` | string | 대기 시간 제한 |
| `atomic` | bool | 실패 시 자동 롤백 여부 |

---

## 🔄 워크플로우

### 전체 프로세스

```
1. prepare  → charts/redis/redis/ (원본 차트 다운로드)
   ↓
2. build    → build/redis/ (오버라이드 적용, 파일 제거)
   ↓
3. template → rendered/redis.yaml (YAML 렌더링, 선택적)
   ↓
4. deploy   → Kubernetes 클러스터 배포
```

### Prepare 단계

```bash
sbkube prepare --app-dir examples/overrides/overrides
```

**결과**:
```
charts/
└── redis/
    └── redis/               # bitnami/redis 차트
        ├── Chart.yaml
        ├── values.yaml      # 원본 values
        ├── templates/
        │   ├── deployment.yaml
        │   ├── service.yaml # 원본 service
        │   ├── ingress.yaml # 나중에 제거될 파일
        │   └── ...
        └── README.md        # 나중에 제거될 파일
```

### Build 단계

```bash
sbkube build --app-dir examples/overrides/overrides
```

**처리 과정**:
1. `charts/redis/redis/` → `build/redis/` 복사
2. `overrides/redis/values.yaml` → `build/redis/values.yaml` 교체
3. `overrides/redis/templates/service.yaml` → `build/redis/templates/service.yaml` 교체
4. `build/redis/README.md` 삭제
5. `build/redis/templates/ingress.yaml` 삭제

**결과**:
```
build/
└── redis/
    ├── Chart.yaml
    ├── values.yaml          # ✅ 오버라이드됨
    └── templates/
        ├── deployment.yaml
        ├── service.yaml     # ✅ 오버라이드됨
        └── ...              # ✅ ingress.yaml 제거됨
                            # ✅ README.md 제거됨
```

### Template 단계 (선택적)

```bash
sbkube template --app-dir examples/overrides/overrides --output-dir /tmp/rendered
```

**결과**:
```
/tmp/rendered/
└── redis.yaml               # 렌더링된 최종 매니페스트
```

### Deploy 단계

```bash
sbkube deploy --app-dir examples/overrides/overrides --namespace demo
```

**처리 과정**:
- `build/redis/` 디렉토리의 차트를 사용하여 Helm install/upgrade 실행
- Labels 및 Annotations 적용
- 커스터마이즈된 차트가 배포됨

### 통합 실행 (권장)

```bash
cd examples/overrides

# 기본 예제
sbkube apply --app-dir overrides

# 고급 예제
sbkube apply --app-dir advanced-example
```

---

## 💡 실전 예제

### 예제 1: Service 타입 변경

**배경**: bitnami/redis는 기본적으로 LoadBalancer를 사용하지만 ClusterIP로 변경하고 싶음

**overrides/redis/templates/service.yaml**:
```yaml
apiVersion: v1
kind: Service
metadata:
  name: redis-master
spec:
  type: ClusterIP              # LoadBalancer → ClusterIP
  ports:
    - name: tcp-redis
      port: 6379
      targetPort: redis
  selector:
    app.kubernetes.io/name: redis
    app.kubernetes.io/component: master
```

**config.yaml**:
```yaml
apps:
  redis:
    overrides:
      - templates/service.yaml  # 커스텀 service.yaml 사용
```

### 예제 2: Values 기본값 변경

**배경**: 비밀번호, 리소스 제한, 영속성 설정을 커스터마이징

**overrides/redis/values.yaml**:
```yaml
auth:
  password: "my-custom-password"

master:
  resources:
    limits:
      cpu: 500m
      memory: 512Mi
    requests:
      cpu: 250m
      memory: 256Mi

  persistence:
    enabled: true
    size: 2Gi
```

**config.yaml**:
```yaml
apps:
  redis:
    overrides:
      - values.yaml  # 커스텀 values.yaml 사용
```

### 예제 3: ConfigMap 추가

**배경**: Redis 설정을 ConfigMap으로 추가

**overrides/redis/templates/configmap.yaml** (신규 파일):
```yaml
apiVersion: v1
kind: ConfigMap
metadata:
  name: redis-custom-config
data:
  redis.conf: |
    maxmemory 256mb
    maxmemory-policy allkeys-lru
    save ""
```

**config.yaml**:
```yaml
apps:
  redis:
    overrides:
      - templates/configmap.yaml  # 새 ConfigMap 추가
```

### 예제 4: 불필요한 리소스 제거

**배경**: Ingress, Tests, 문서 파일을 제거하여 깔끔한 배포

**config.yaml**:
```yaml
apps:
  redis:
    removes:
      - README.md
      - templates/ingress.yaml
      - templates/tests/
      - files/sample-config.conf
```

---

## 🛠️ 고급 사용법

### 1. 다중 파일 오버라이드

```yaml
apps:
  redis:
    overrides:
      - values.yaml
      - templates/service.yaml
      - templates/deployment.yaml
      - templates/configmap.yaml
```

**디렉토리 구조**:
```
overrides/redis/
├── values.yaml
└── templates/
    ├── service.yaml
    ├── deployment.yaml
    └── configmap.yaml
```

### 2. 환경별 오버라이드

```yaml
# config-dev.yaml
apps:
  redis:
    overrides:
      - values-dev.yaml
      - templates/service.yaml

# config-prod.yaml
apps:
  redis:
    overrides:
      - values-prod.yaml
      - templates/service.yaml
```

**디렉토리 구조**:
```
overrides/redis/
├── values-dev.yaml
├── values-prod.yaml
└── templates/
    └── service.yaml
```

### 3. 부분 템플릿 오버라이드

**배경**: StatefulSet의 일부분만 수정하고 싶음

**overrides/redis/templates/primary/statefulset.yaml**:
```yaml
# bitnami/redis의 원본 StatefulSet을 복사 후 일부 수정
apiVersion: apps/v1
kind: StatefulSet
metadata:
  name: {{ include "redis.fullname" . }}-master
spec:
  # ... (대부분 원본 유지)
  template:
    spec:
      # ✅ 여기만 수정: hostPath 볼륨 사용
      volumes:
      - name: data
        hostPath:
          path: /data/redis
          type: DirectoryOrCreate
```

### 4. Helm 훅 추가

**overrides/redis/templates/pre-install-job.yaml**:
```yaml
apiVersion: batch/v1
kind: Job
metadata:
  name: redis-pre-install
  annotations:
    "helm.sh/hook": pre-install
    "helm.sh/hook-weight": "-5"
spec:
  template:
    spec:
      containers:
      - name: pre-install
        image: busybox
        command: ["sh", "-c", "echo 'Pre-install setup'"]
      restartPolicy: Never
```

---

## ⚠️ 주의사항

### 1. Overrides 디렉토리 구조

**올바른 구조**:
```
overrides/<app-name>/
```

**예시**:
```
overrides/redis/values.yaml
overrides/redis/templates/service.yaml
```

**잘못된 예시**:
```
❌ overrides/values.yaml  # 앱 이름 누락
❌ redis/values.yaml       # overrides 디렉토리 누락
```

### 2. Removes 패턴

**상대 경로 사용** (차트 루트 기준):
```yaml
removes:
  - README.md                  # ✅ 차트 루트의 README.md
  - templates/ingress.yaml     # ✅ templates/ 디렉토리의 ingress.yaml
  - tests/                     # ✅ tests/ 디렉토리 전체
```

**절대 경로 사용 금지**:
```yaml
removes:
  - /README.md                 # ❌ 절대 경로
  - ../other-chart/file.yaml   # ❌ 상위 디렉토리
```

### 3. 빌드 순서

**필수**: prepare → build 순서로 실행

```bash
# ❌ 잘못된 순서 (build 먼저)
sbkube build --app-dir .      # 실패: charts/ 디렉토리 없음

# ✅ 올바른 순서
sbkube prepare --app-dir .    # charts/ 다운로드
sbkube build --app-dir .      # overrides 적용

# ✅ 또는 통합 실행
sbkube apply --app-dir .      # 모든 단계 자동 실행
```

### 4. 템플릿 문법 유지

**중요**: 오버라이드 파일에서도 Helm 템플릿 문법 유지 필요

```yaml
# ❌ 잘못된 오버라이드 (하드코딩)
metadata:
  name: redis-master

# ✅ 올바른 오버라이드 (템플릿 사용)
metadata:
  name: {{ include "redis.fullname" . }}-master
```

---

## 🆚 v0.2.x vs v0.3.0 비교

### v0.2.x (이전 버전)

```yaml
apps:
  - name: redis-pull
    type: helm
    specs:
      repo: bitnami
      chart: redis
      dest: redis

  - name: redis
    type: helm
    specs:
      path: redis
      overrides:
        - values.yaml
      removes:
        - README.md
```

**문제점**:
- Pull과 Install이 분리됨
- `specs` 네스팅으로 설정 복잡
- 앱 이름이 `name` 필드에 중복

### v0.3.0 (현재 버전)

```yaml
apps:
  redis:
    type: helm
    chart: bitnami/redis
    overrides:
      - values.yaml
    removes:
      - README.md
```

**개선 사항**:
- Pull과 Install이 하나의 `helm` 타입으로 통합
- 앱 이름이 딕셔너리 키로 이동
- `specs` 제거로 설정 평탄화
- 간결하고 직관적

---

## 🔍 디버깅 팁

### Build 결과 확인

```bash
# Build 실행
sbkube build --app-dir examples/overrides/overrides

# 결과 확인
ls -la build/redis/
cat build/redis/values.yaml
cat build/redis/templates/service.yaml
```

### Template 렌더링 확인

```bash
# Template 실행
sbkube template --app-dir examples/overrides/overrides --output-dir /tmp/rendered

# 렌더링 결과 확인
cat /tmp/rendered/redis.yaml
```

### Helm 차트 검증

```bash
# Helm으로 직접 검증
helm lint build/redis/

# Dry-run 테스트
helm install redis build/redis/ --dry-run --debug
```

---

## 📚 참고 자료

- [SBKube 애플리케이션 타입 가이드](../../docs/02-features/application-types.md)
- [SBKube 명령어 참조](../../docs/02-features/commands.md)
- [Helm 차트 개발 가이드](https://helm.sh/docs/chart_template_guide/)
- [advanced-example/README.md](advanced-example/README.md) - 상세 워크플로우

---

## 🔗 관련 예제

- [k3scode/devops/](../k3scode/devops/) - 로컬 차트 사용 예제 (proxynd-custom)
- [k3scode/rdb/](../k3scode/rdb/) - overrides 주석 예제 (PostgreSQL, MariaDB)

---

**💡 팁**: Overrides는 강력하지만 유지보수가 어렵습니다. 가능하면 `values.yaml`로 커스터마이징하고, 불가피한 경우에만 템플릿 오버라이드를 사용하세요.
