# SBKube 디렉토리 구조 베스트 프랙티스

> **작성일**: 2025-10-31
> **대상**: 프로덕션 환경에서 SBKube 프로젝트를 구조화하는 모범 사례

---

## 📋 목차

1. [개요](#개요)
2. [기본 원칙](#기본-원칙)
3. [디렉토리 구조](#디렉토리-구조)
4. [각 디렉토리 상세 설명](#각-디렉토리-상세-설명)
5. [프로젝트 규모별 구조](#프로젝트-규모별-구조)
6. [파일 네이밍 규칙](#파일-네이밍-규칙)
7. [예제 및 비교](#예제-및-비교)

---

## 개요

### 문제점

`examples/` 디렉토리에서는 학습 및 테스트 목적으로 모든 파일(config.yaml, sources.yaml, values, manifests 등)이 한 디렉토리에 혼재되어 있습니다.

```
examples/basic/  ❌ 학습용 (비권장: 프로덕션)
├── config.yaml
├── sources.yaml
├── values-app1.yaml
├── values-app2.yaml
└── manifest.yaml
```

**프로덕션 환경에서는 명확한 구조 분리가 필요합니다**:
- 설정 파일과 데이터 파일 분리
- 앱 그룹별 독립성 확보
- 유지보수 및 협업 용이성
- Git 관리 및 버전 관리 최적화

---

## 기본 원칙

### 1. 관심사의 분리 (Separation of Concerns)

| 항목 | 위치 | 설명 |
|------|------|------|
| **전역 설정** | 프로젝트 루트 | sources.yaml, .gitignore 등 |
| **앱 그룹 설정** | `app_*/` | 각 앱 그룹별 config.yaml |
| **앱별 데이터** | `app_*/values/`, `app_*/static-manifests/` | Helm values, YAML manifests |
| **빌드 산출물** | `.sbkube/` | 자동 생성 파일 (Git 제외) |

### 2. 명확한 네이밍

- **앱 그룹 디렉토리**: `app_{순서}_{카테고리}_{설명}`
  - 예: `app_000_infra_network`, `app_100_data_memory`
- **파일명**: 앱 이름과 일치
  - 예: `traefik.yaml`, `nfs-syno-main.yaml`

### 3. Git 친화적 구조

```gitignore
# .gitignore (프로젝트 루트)

# SBKube 작업 디렉토리 (필수 제외)
.sbkube/          # 자동 생성: charts, repos, build, rendered

# 앱 그룹별 산출물 (선택적 제외)
# rendered/       # 템플릿 렌더링 결과 (팀 정책에 따라 포함/제외)
# app_*/build/    # 빌드 중간 산출물 (거의 사용 안 함)

# 백업 및 임시 파일
backups/
output/
*.tmp
*.bak
```

**Git 관리 전략**:
- **필수 제외**: `.sbkube/` (자동 생성 파일)
- **선택적 제외**: `rendered/` (팀 정책에 따라 결정)
  - 제외: 빠른 merge, 작은 repo 크기
  - 포함: 배포 이력 추적, manifest 변경 리뷰
- **포함 권장**: `values/`, `static-manifests/`, `config.yaml`

---

## 디렉토리 구조

### 최상위 구조 (프로젝트 루트)

```
project-root/
├── sources.yaml                    # 전역 소스 설정 (Helm repos, Git repos, OCI registries)
├── .gitignore                      # Git 제외 파일
├── README.md                       # 프로젝트 개요
├── .sbkube/                        # SBKube 작업 디렉토리 (Git 제외)
│   ├── charts/                     # Helm 차트 다운로드 (prepare)
│   ├── repos/                      # Git 리포지토리 클론 (prepare)
│   ├── build/                      # 빌드 산출물 (build)
│   └── rendered/                   # 템플릿 렌더링 결과 (template)
├── app_000_infra_network/          # 앱 그룹 1: 네트워크 인프라
│   ├── config.yaml                 # 앱 그룹 설정
│   ├── values/                     # Helm values 파일
│   ├── static-manifests/           # Static YAML manifests
│   ├── overrides/                  # 차트 파일 오버라이드
│   ├── hooks/                      # 배포 전후 실행 스크립트 (선택)
│   ├── tests/                      # 테스트 스크립트 (선택)
│   └── README.md                   # 앱 그룹 설명
├── app_100_data_memory/            # 앱 그룹 2: 인메모리 데이터베이스
│   ├── config.yaml
│   ├── values/
│   └── ...
└── app_200_orchestration/          # 앱 그룹 3: 오케스트레이션
    ├── config.yaml
    ├── values/
    └── ...
```

### 앱 그룹 디렉토리 구조 (`app_*`)

```
app_XXX_category_name/
├── config.yaml                     # 필수: 앱 그룹 설정 파일
├── values/                         # 권장: Helm values 파일 모음
│   ├── redis.yaml                  # 앱별 values 파일
│   ├── memcached.yaml
│   └── valkey.yaml
├── manifests/                      # 선택: 템플릿 처리가 필요한 manifests (helm/yaml 타입)
│   ├── deployment.yaml             # Go 템플릿 변수 포함 가능
│   └── service.yaml
├── static-manifests/               # 선택: 템플릿 처리 없이 바로 배포할 manifests (yaml 타입)
│   ├── k3s/
│   │   └── storage-class.yaml
│   └── nfs-storage/
│       └── pv.yaml
├── overrides/                      # 선택: Helm 차트 파일 오버라이드
│   └── templates/
│       └── custom-configmap.yaml
├── hooks/                          # 선택: 배포 전후 실행 스크립트
│   ├── pre-deploy.sh
│   └── post-deploy.sh
├── tests/                          # 선택: 테스트 스크립트
│   └── smoke-test.sh
├── rendered/                       # 선택: 템플릿 렌더링 결과 (Git 제외 가능)
│   ├── redis.yaml
│   └── memcached.yaml
└── README.md                       # 권장: 앱 그룹 설명
```

---

## 각 디렉토리 상세 설명

### 1. 프로젝트 루트

#### `sources.yaml` (필수)

전역 소스 설정 파일로, 모든 앱 그룹이 공유합니다.

```yaml
cluster: production-cluster
kubeconfig: ~/.kube/config
kubeconfig_context: production

# Helm 레지스트리
helm_repos:
  grafana: https://grafana.github.io/helm-charts
  prometheus-community: https://prometheus-community.github.io/helm-charts
  traefik: https://helm.traefik.io/traefik

# Git 리포지토리
git_repos:
  pulp-operator:
    url: https://github.com/pulp/pulp-operator.git
    branch: main

# OCI 레지스트리
oci_registries:
  browserless: oci://tccr.io/truecharts
```

**위치 결정 규칙**:
1. `sources.yaml`이 있는 디렉토리가 `.sbkube/` 작업 디렉토리의 기준점
2. 단일 클러스터: 프로젝트 루트에 위치
3. 멀티 클러스터: 각 클러스터별 디렉토리에 `sources.yaml` 배치

**app_dirs 기능** (v0.2.0+):

`sources.yaml`에서 앱 그룹 디렉토리를 명시적으로 지정할 수 있습니다:

```yaml
cluster: production-cluster
kubeconfig: ~/.kube/config

# 앱 그룹 디렉토리 명시 (선택)
app_dirs:
  - app_000_infra_network
  - app_100_data_memory
  - app_200_orchestration

helm_repos:
  grafana: https://grafana.github.io/helm-charts
  # ...
```

**동작 방식**:
- `app_dirs` 지정 시: 해당 디렉토리만 처리
- `app_dirs` 미지정 시: config.yaml이 있는 모든 하위 디렉토리 자동 탐색

#### `.sbkube/` (자동 생성, Git 제외)

SBKube가 자동으로 생성하는 작업 디렉토리입니다. `sources.yaml`이 있는 디렉토리를 기준으로 생성됩니다.

```
.sbkube/
├── charts/              # prepare 단계: Helm 차트 다운로드
│   ├── redis/           # 앱별 격리 디렉토리
│   │   └── redis/       # ← Helm 차트 실제 내용 (Chart.yaml, templates/ 등)
│   └── memcached/
│       └── memcached/   # ← Helm 차트 실제 내용
├── repos/               # prepare 단계: Git 리포지토리 클론
│   └── pulp-operator/
│       └── .git/
├── build/               # build 단계: 빌드 산출물 (overrides 적용 후)
│   └── traefik/
└── rendered/            # template 단계: 렌더링된 manifests (통합)
    ├── redis.yaml
    └── memcached.yaml
```

> **💡 이중 디렉토리 구조 설명**:
>
> Helm의 `helm pull --untar --untardir` 동작 특성상 `charts/{chart_name}/{chart_name}/` 구조가 생성됩니다.
> - **외부 디렉토리** (`charts/redis/`): 앱별 격리 및 버전 관리용
> - **내부 디렉토리** (`charts/redis/redis/`): Helm 차트의 실제 내용
>
> **왜 이렇게 되는가?**
> ```bash
> # Helm 명령어 (SBKube 내부 동작)
> helm pull bitnami/redis --untar --untardir .sbkube/charts/redis
>
> # 결과:
> # .sbkube/charts/redis/redis/  ← 차트 이름이 한 번 더 들어감
> #                      └─ 차트 이름 (Helm이 자동 생성)
> ```
>
> 이는 SBKube의 설계가 아닌 **Helm CLI의 표준 동작**입니다.
> 동일한 차트의 다른 버전을 관리하거나, 차트 이름이 다른 경우를 대비한 Helm의 설계입니다.
>
> **개선 가능성**:
> - SBKube v0.3+ 에서 `charts/{chart_name}/` 구조로 단순화하는 옵션 검토 중
> - 현재는 Helm 표준을 따르는 것이 호환성 측면에서 안전함

**주의사항**:
- `.gitignore`에 반드시 추가: `.sbkube/`
- 사용자가 직접 편집하지 않음
- `--force` 옵션으로 재생성 가능
- `sources.yaml` 위치가 작업 디렉토리 기준점

---

### 2. 앱 그룹 디렉토리 (`app_*`)

#### `config.yaml` (필수)

각 앱 그룹의 설정 파일:

```yaml
namespace: data-memory

apps:
  redis:
    type: helm
    enabled: true
    chart: bitnami/redis
    version: "18.0.0"
    values:
      - values/redis.yaml

  memcached:
    type: helm
    enabled: true
    chart: bitnami/memcached
    values:
      - values/memcached.yaml

  custom-app:
    type: yaml
    enabled: true
    manifests:
      - static-manifests/custom-app.yaml
```

#### `values/` (권장)

Helm values 파일을 앱별로 분리:

```
values/
├── redis.yaml           # Redis values
├── memcached.yaml       # Memcached values
└── valkey.yaml          # Valkey values
```

**네이밍 규칙**:
- 파일명 = 앱 이름 + `.yaml`
- 예: `config.yaml`의 `redis` 앱 → `values/redis.yaml`

**장점**:
- 파일 탐색 용이
- Git diff 명확
- 앱별 책임 분리

#### `manifests/` (선택)

템플릿 처리가 필요한 Kubernetes 매니페스트 파일:

```
manifests/
├── deployment.yaml      # Go 템플릿 변수 포함
├── service.yaml
├── configmap.yaml
└── ingress.yaml
```

**특징**:
- **Go 템플릿 변수 사용 가능**: `{{ .Values.image }}`, `{{ .Release.Name }}`
- **Helm 차트 템플릿**: Helm 차트의 `templates/` 디렉토리와 동일한 형식
- **sbkube template으로 렌더링**: `.sbkube/rendered/`에 최종 YAML 생성
- **환경별 커스터마이징**: values 파일로 동적 값 주입

**사용 예시**:

`manifests/deployment.yaml`:
```yaml
apiVersion: apps/v1
kind: Deployment
metadata:
  name: {{ .Values.name }}
spec:
  replicas: {{ .Values.replicaCount }}
  template:
    spec:
      containers:
      - name: app
        image: {{ .Values.image.repository }}:{{ .Values.image.tag }}
        env:
        - name: DATABASE_URL
          value: {{ .Values.database.url }}
```

`values/myapp.yaml`:
```yaml
name: myapp
replicaCount: 3
image:
  repository: myregistry/myapp
  tag: "1.0.0"
database:
  url: "postgresql://db:5432"
```

`config.yaml`:
```yaml
apps:
  myapp:
    type: yaml
    enabled: true
    manifests:
      - manifests/deployment.yaml
      - manifests/service.yaml
    values:
      - values/myapp.yaml
```

**렌더링 과정**:
```bash
# 템플릿 렌더링
sbkube template --app-dir app_myapp --output-dir app_myapp/rendered

# 결과: app_myapp/rendered/myapp.yaml
# 모든 템플릿 변수가 values로 치환됨
```

#### `static-manifests/` (선택)

Static YAML manifests (yaml 타입 앱용):

```
static-manifests/
├── k3s/
│   ├── storage-class.yaml
│   └── volume-snapshot-class.yaml
├── nfs-storage/
│   ├── pv-main.yaml
│   └── pv-tmp.yaml
└── custom/
    └── namespace.yaml
```

**사용 예**:
```yaml
# config.yaml
apps:
  k3s-storage-class:
    type: yaml
    enabled: true
    manifests:
      - static-manifests/k3s/storage-class.yaml
      - static-manifests/k3s/volume-snapshot-class.yaml
```

#### `manifests/` vs `static-manifests/` 비교

두 디렉토리의 핵심 차이점:

| 항목 | `manifests/` | `static-manifests/` |
|------|-------------|---------------------|
| **템플릿 처리** | ✅ 필요 (Go 템플릿) | ❌ 불필요 (완성된 YAML) |
| **변수 사용** | `{{ .Values.* }}` | 불가능 |
| **렌더링** | `sbkube template` 실행 | 그대로 사용 |
| **환경별 다른 값** | values 파일로 가능 | 파일 자체를 환경별로 분리 |
| **용도** | 동적 설정, 환경별 차이 | 고정 설정, 모든 환경 동일 |
| **예시** | Deployment, StatefulSet | StorageClass, ConfigMap |

**언제 어느 것을 사용하나?**

**`manifests/` 사용 (동적 매니페스트)**:
- 환경별로 다른 값이 필요한 경우
  - 예: 개발(1 replica) vs 프로덕션(3 replicas)
- 이미지 태그, 리소스 제한이 자주 변경되는 경우
- Helm values로 커스터마이징하고 싶은 경우
- 복잡한 Deployment, StatefulSet, DaemonSet

**`static-manifests/` 사용 (정적 매니페스트)**:
- 모든 환경에서 동일한 값을 사용하는 경우
  - 예: StorageClass, VolumeSnapshotClass
- 간단한 ConfigMap, Secret (하드코딩된 값)
- Namespace, ServiceAccount 등 기본 리소스
- 변경이 거의 없는 설정

**실전 예시**:

```yaml
# config.yaml
apps:
  # 동적: 환경별 다른 설정
  myapp:
    type: yaml
    manifests:
      - manifests/deployment.yaml    # 템플릿 변수 사용
      - manifests/service.yaml
    values:
      - values/myapp-prod.yaml       # 프로덕션 값

  # 정적: 모든 환경 동일
  k3s-storage:
    type: yaml
    manifests:
      - static-manifests/k3s/storage-class.yaml  # 고정 값
```

#### `overrides/` (선택)

Helm 차트 파일을 직접 오버라이드:

```
overrides/
├── templates/
│   ├── custom-configmap.yaml
│   └── custom-service.yaml
└── Chart.yaml
```

**사용 예**:
```yaml
# config.yaml
apps:
  traefik:
    type: helm
    chart: traefik/traefik
    values:
      - values/traefik.yaml
    overrides:
      - templates/configmap-providers.yaml
      - static-manifests/traefik.toml
```

**주의사항**:
- 차트 업데이트 시 충돌 가능성
- 가능한 `values.yaml`로 해결 권장
- 정말 필요한 경우에만 사용

#### `hooks/` (선택)

배포 전후 실행 스크립트:

```
hooks/
├── pre-deploy.sh       # 배포 전 실행
├── post-deploy.sh      # 배포 후 실행
└── traefik/            # 앱별 훅 (선택)
    └── wait-for-pods.sh
```

**사용 예**:
```yaml
# config.yaml
hooks:
  deploy:
    pre:
      - command: bash hooks/pre-deploy.sh
    post:
      - command: bash hooks/post-deploy.sh
```

#### `tests/` (선택)

테스트 스크립트 및 자동화:

```
tests/
├── smoke-test.sh       # 배포 후 기본 검증
├── integration-test.sh # 통합 테스트
└── traefiktest/        # 앱별 테스트
    └── test-ingress.yaml
```

#### `rendered/` (선택, Git 제외 권장)

앱 그룹별 템플릿 렌더링 결과 (디버깅 및 검증용):

```
rendered/
├── redis.yaml
├── memcached.yaml
└── valkey.yaml
```

**용도**:
- `sbkube template --output-dir app_XXX/rendered` 명령어 결과
- 배포 전 manifest 검증 및 리뷰
- CI/CD 파이프라인에서 diff 확인
- Git에 포함 여부는 팀 정책에 따름

**Git 관리 정책**:
- **제외 권장**: `.gitignore`에 `app_*/rendered/` 추가
- **포함 가능**: 배포 이력 추적이 필요한 경우
- 실제 프로덕션 예시에서는 Git에 포함되어 있음 (polypia 클러스터)

---

## 프로젝트 규모별 구조

### 소규모 프로젝트 (단일 클러스터, 10개 이하 앱)

```
my-k8s-project/
├── sources.yaml
├── .gitignore
├── app_infra/
│   ├── config.yaml
│   └── values/
└── app_data/
    ├── config.yaml
    └── values/
```

**특징**:
- 단순한 2-3개 앱 그룹
- 앱 그룹명 간소화 (순서 번호 생략 가능)
- 최소한의 디렉토리 구조

### 중규모 프로젝트 (단일 클러스터, 10-50개 앱)

```
my-k8s-project/
├── sources.yaml
├── .gitignore
├── app_000_infra_network/
│   ├── config.yaml
│   ├── values/
│   └── static-manifests/
├── app_100_data_memory/
│   ├── config.yaml
│   └── values/
├── app_200_orchestration/
│   ├── config.yaml
│   ├── values/
│   └── overrides/
└── app_300_monitoring/
    ├── config.yaml
    ├── values/
    └── hooks/
```

**특징**:
- 순서 번호 부여 (배포 의존성 관리)
- 카테고리별 그룹화
- 추가 디렉토리 활용 (overrides, hooks)

### 대규모 프로젝트 (멀티 클러스터, 50개 이상 앱)

```
kubernetes-infra/
├── clusters/
│   ├── production/
│   │   ├── sources.yaml
│   │   ├── app_000_infra/
│   │   ├── app_100_data/
│   │   └── ...
│   ├── staging/
│   │   ├── sources.yaml
│   │   ├── app_000_infra/
│   │   └── ...
│   └── development/
│       ├── sources.yaml
│       └── ...
├── shared/
│   ├── values-common/     # 공통 values 템플릿
│   └── manifests-common/  # 공통 manifests
└── docs/
    └── architecture.md
```

**특징**:
- 환경별 디렉토리 분리
- 공통 리소스 재사용
- 상세한 문서화

---

## 파일 네이밍 규칙

### 앱 그룹 디렉토리명

**패턴**: `app_{순서}_{카테고리}_{설명}`

- **순서** (3자리): 배포 순서 (000, 010, 020, ...)
- **카테고리**: 앱 그룹의 역할
  - `infra`: 인프라 (네트워크, 스토리지)
  - `data`: 데이터베이스
  - `orchestration`: 워크플로우 오케스트레이션
  - `monitoring`: 모니터링
  - `devops`: DevOps 도구
  - `app`: 애플리케이션
- **설명**: 간결한 설명 (snake_case)

**예시**:
```
app_000_infra_network         # 순서 000, 인프라, 네트워크
app_010_infra_cert_manager    # 순서 010, 인프라, 인증서 관리
app_100_data_memory           # 순서 100, 데이터, 인메모리 DB
app_200_orchestration_argo    # 순서 200, 오케스트레이션, Argo
app_300_monitoring            # 순서 300, 모니터링
```

### Values 파일명

**패턴**: `{앱이름}.yaml`

- `config.yaml`의 앱 이름과 정확히 일치
- 하이픈(`-`) 사용 (Kubernetes 네이밍 규칙)

**예시**:
```
values/
├── redis.yaml
├── redis-cluster.yaml
├── nfs-syno-main.yaml
└── postgresql-ha.yaml
```

### Manifest 파일명

**패턴**: `{리소스종류}-{이름}.yaml` 또는 `{앱이름}.yaml`

**예시**:
```
static-manifests/
├── storage-class.yaml
├── pv-main.yaml
├── namespace-data.yaml
└── k3s/
    └── volume-snapshot-class.yaml
```

---

## 예제 및 비교

### ❌ 비권장: Examples 스타일 (학습용)

```
examples/basic/
├── config.yaml          # 모든 설정이 한 곳에
├── sources.yaml
├── values-redis.yaml    # values 파일이 루트에 혼재
├── values-memcached.yaml
├── manifest.yaml        # manifests도 루트에
└── override.yaml
```

**문제점**:
- 파일 탐색 어려움
- 앱 추가 시 루트 디렉토리 복잡도 증가
- Git diff 혼란
- 협업 시 충돌 가능성

### ✅ 권장: 프로덕션 스타일 (실제 예시: polypia 클러스터)

```
ph3_kube_app_cluster/
├── sources.yaml                     # 전역 설정
├── .gitignore                       # .sbkube/ 제외
├── README.md
├── app_000_infra_network/           # 인프라: 네트워크 (Traefik, HAProxy, CoreDNS)
│   ├── config.yaml
│   ├── values/
│   │   ├── traefik.yaml
│   │   ├── haproxy.yaml
│   │   ├── coredns.yaml
│   │   ├── nfs-syno-main.yaml       # 스토리지 설정
│   │   └── nfs-syno-tmp.yaml
│   ├── static-manifests/
│   │   ├── k3s/
│   │   │   └── storage-class.yaml   # Kubernetes 기본 리소스
│   │   ├── nfs-storage/
│   │   │   └── pv.yaml
│   │   └── traefik2*.toml           # Traefik 설정 파일들
│   ├── overrides/                   # Helm 차트 오버라이드
│   │   └── templates/
│   │       └── configmap-providers.yaml
│   ├── rendered/                    # Git 포함 (배포 이력 추적)
│   │   ├── traefik.yaml
│   │   └── haproxy.yaml
│   ├── hooks/                       # 배포 훅 스크립트
│   │   └── traefik/
│   ├── tests/                       # 배포 후 테스트
│   │   └── traefiktest/
│   └── ROUTING.md                   # 앱 그룹 문서
├── app_010_infra_cert_manager/      # 인프라: 인증서 관리
│   ├── config.yaml
│   └── values/
├── app_100_data_memory/             # 데이터: 인메모리 DB (Redis, Memcached)
│   ├── config.yaml
│   ├── values/
│   │   ├── redis.yaml
│   │   ├── memcached.yaml
│   │   └── valkey.yaml
│   └── rendered/
├── app_220_orchestration_airflow/   # 오케스트레이션: Apache Airflow
│   ├── config.yaml
│   ├── values/
│   ├── static-manifests/
│   ├── overrides/
│   └── README.md
└── .sbkube/                         # 자동 생성 (Git 제외)
    ├── charts/                      # Helm 차트 다운로드
    ├── repos/                       # Git 리포지토리 클론
    ├── build/                       # 빌드 산출물
    └── rendered/                    # 통합 렌더링 결과
```

**장점**:
- **명확한 구조**: 앱 그룹별 독립된 디렉토리
- **파일 탐색 용이**: 앱 이름으로 values 파일 바로 찾기
- **앱 그룹별 독립성**: 각 그룹이 자체 config.yaml 보유
- **Git 친화적**: 설정 파일과 산출물 분리
- **확장 용이**: 새 앱 그룹 추가 간편
- **협업 최적화**: 그룹별 담당자 분리 가능
- **배포 순서 제어**: 디렉토리 순서로 의존성 표현

---

## 마이그레이션 가이드

### Examples에서 프로덕션 구조로 전환

**Before (Examples)**:
```
examples/basic/
├── config.yaml
├── sources.yaml
├── values-app1.yaml
└── values-app2.yaml
```

**After (프로덕션)**:
```
project-root/
├── sources.yaml
├── app_infra/
│   ├── config.yaml
│   └── values/
│       └── app1.yaml
└── app_data/
    ├── config.yaml
    └── values/
        └── app2.yaml
```

**마이그레이션 단계**:

1. **전역 설정 분리**
   ```bash
   cp examples/basic/sources.yaml project-root/sources.yaml
   ```

2. **앱 그룹 생성**
   ```bash
   mkdir -p project-root/app_infra/values
   mkdir -p project-root/app_data/values
   ```

3. **앱별 파일 이동**
   ```bash
   mv examples/basic/values-app1.yaml project-root/app_infra/values/app1.yaml
   mv examples/basic/values-app2.yaml project-root/app_data/values/app2.yaml
   ```

4. **config.yaml 분할**
   - 각 앱 그룹별로 `config.yaml` 생성
   - 앱 정의를 적절히 분배

5. **검증**
   ```bash
   sbkube validate --base-dir project-root --app-dir app_infra
   sbkube validate --base-dir project-root --app-dir app_data
   ```

---

## 체크리스트

### 새 프로젝트 시작 시

- [ ] 프로젝트 루트에 `sources.yaml` 생성
- [ ] `.gitignore`에 `.sbkube/` 추가
- [ ] 앱 그룹 디렉토리 생성 (네이밍 규칙 준수)
- [ ] 각 앱 그룹에 `config.yaml` 작성
- [ ] `values/` 디렉토리 생성 및 파일 분리
- [ ] 필요시 `static-manifests/`, `overrides/` 디렉토리 생성
- [ ] 각 앱 그룹에 `README.md` 작성 (권장)

### 기존 프로젝트 리팩토링 시

- [ ] 현재 구조 분석 및 문제점 파악
- [ ] 앱 그룹 분류 계획 수립
- [ ] 마이그레이션 스크립트 작성 (선택)
- [ ] 단계별 마이그레이션 (한 번에 하나씩)
- [ ] 각 단계마다 검증 (`sbkube validate`)
- [ ] 배포 테스트 (`sbkube deploy --dry-run`)

---

## 기술적 배경: 이중 디렉토리 구조

### 문제: charts/{name}/{name}/ 동어반복

사용자들이 종종 혼란스러워하는 부분:

```
.sbkube/charts/redis/redis/  ← 왜 redis가 두 번?
```

### 원인: Helm CLI의 표준 동작

**Helm의 `--untardir` 동작**:
```bash
# 명령어
helm pull bitnami/redis --untar --untardir /path/to/target

# 결과
/path/to/target/
└── redis/        ← Helm이 차트 이름으로 자동 생성
    ├── Chart.yaml
    ├── values.yaml
    └── templates/
```

Helm은 항상 `--untardir` 경로 **아래**에 차트 이름으로 디렉토리를 생성합니다.

### SBKube의 현재 구현

```python
# sbkube/commands/prepare.py:294-332
dest_dir = charts_dir / chart_name  # .sbkube/charts/redis
cmd = ["helm", "pull", f"{repo_name}/{chart_name}",
       "--untar", "--untardir", str(dest_dir)]
# 결과: .sbkube/charts/redis/redis/
```

SBKube는 앱별 격리를 위해 `charts/{chart_name}/`을 만들고,
Helm은 그 안에 또 `{chart_name}/`을 만듭니다.

### 개선 방안

#### 방안 1: 직접 charts/ 아래 압축 해제 (간단)

```python
# 변경 후
dest_dir = charts_dir  # .sbkube/charts
cmd = ["helm", "pull", f"{repo_name}/{chart_name}",
       "--untar", "--untardir", str(dest_dir)]
# 결과: .sbkube/charts/redis/
```

**장점**: 구조 단순화
**단점**: 동일 차트의 여러 버전 관리 불가, 차트 이름 충돌 가능

#### 방안 2: 심볼릭 링크 (호환성 유지)

```python
# charts/redis/ → charts/redis/redis/ 심볼릭 링크
# 기존 코드 호환성 유지하면서 사용자 편의성 개선
```

**장점**: 기존 코드 영향 없음
**단점**: Windows 호환성 문제

#### 방안 3: 설정 옵션 제공 (권장)

```yaml
# sources.yaml
helm_options:
  flatten_chart_dirs: true  # charts/{name}/ 구조 사용
```

**장점**: 사용자 선택 가능, 기존 프로젝트 영향 없음
**단점**: 구현 복잡도 증가

### 결론

현재 버전(v0.2.x)에서는 **Helm 표준을 그대로 따르는 것이 안전**합니다:
- Helm 생태계와 호환성 유지
- 예상치 못한 부작용 방지
- 명확한 디렉토리 격리

향후 버전(v0.3+)에서 설정 옵션으로 개선을 검토 중입니다.

---

## 추가 권장사항

### 1. 대규모 프로젝트 모듈화 전략

**문제**: 앱 그룹이 너무 많아지면 (40개+) 루트 디렉토리가 복잡해짐

**해결책**: 카테고리별 서브 디렉토리 사용

```
ph3_kube_app_cluster/
├── sources.yaml
├── infra/                           # 인프라 관련 앱 그룹
│   ├── app_000_network/
│   ├── app_010_cert_manager/
│   └── app_020_olm/
├── data/                            # 데이터 관련 앱 그룹
│   ├── app_100_memory/
│   ├── app_111_rdb_cnpg/
│   └── app_120_nosql/
├── platform/                        # 플랫폼 관련 앱 그룹
│   ├── app_200_orchestration/
│   └── app_300_monitoring/
└── .sbkube/
```

**sources.yaml 설정**:
```yaml
app_dirs:
  - infra/app_000_network
  - infra/app_010_cert_manager
  - data/app_100_memory
  # ...
```

### 2. 환경별 설정 분리 (멀티 클러스터)

**구조**:
```
kubernetes-infra/
├── clusters/
│   ├── production/
│   │   ├── sources.yaml             # 환경별 sources
│   │   ├── app_000_infra/
│   │   └── ...
│   ├── staging/
│   │   ├── sources.yaml
│   │   ├── app_000_infra/
│   │   └── ...
│   └── development/
│       ├── sources.yaml
│       └── ...
└── shared/
    ├── values-common/               # 공통 values 템플릿
    │   ├── redis-base.yaml
    │   └── postgres-base.yaml
    └── manifests-common/
```

**사용법**:
```bash
# Production 배포
cd clusters/production
sbkube apply --app-dir app_000_infra

# Staging 배포
cd clusters/staging
sbkube apply --app-dir app_000_infra
```

### 3. CI/CD 통합 패턴

**GitLab CI 예시**:
```yaml
# .gitlab-ci.yml
stages:
  - validate
  - template
  - deploy

validate:
  stage: validate
  script:
    - sbkube validate --app-dir app_000_infra

template:
  stage: template
  script:
    - sbkube template --app-dir app_000_infra --output-dir rendered/
  artifacts:
    paths:
      - app_000_infra/rendered/

deploy:
  stage: deploy
  script:
    - sbkube deploy --app-dir app_000_infra --dry-run
  when: manual
```

---

## 참고 자료

### SBKube 문서
- [SBKube 설정 가이드](../03-configuration/config-schema.md)
- [앱 타입 가이드](../02-features/application-types.md)
- [멀티 앱 그룹 관리](../02-features/multi-app-groups.md)
- [명령어 레퍼런스](../02-features/commands.md)

### 관련 개념
- [Kubernetes 네이밍 규칙](https://kubernetes.io/docs/concepts/overview/working-with-objects/names/)
- [Helm 차트 구조](https://helm.sh/docs/topics/charts/)
- [Git 모범 사례](https://git-scm.com/book/en/v2/Git-Branching-Branching-Workflows)

---

## 변경 이력

### v1.1 (2025-10-31)
- **이중 디렉토리 구조 상세 설명 추가**: `charts/{name}/{name}/` 동어반복 원인 설명
- **기술적 배경 섹션 신설**: Helm CLI의 표준 동작 설명
- **3가지 개선 방안 제시**: 직접 해제, 심볼릭 링크, 설정 옵션
- 향후 버전(v0.3+) 개선 계획 명시

### v1.0 (2025-10-31)
- 초기 문서 작성
- Polypia 클러스터 실제 구조 반영
- `.sbkube/` 디렉토리 상세 설명 추가
- `app_dirs` 기능 설명 추가
- Git 관리 전략 명확화
- CI/CD 통합 패턴 추가
- 대규모 프로젝트 모듈화 전략 추가

---

**문서 버전**: 1.1
**마지막 업데이트**: 2025-10-31
**작성자**: SBKube Documentation Team
**검토 대상**: 프로덕션 환경 구조화, Helm 디렉토리 구조 이슈
