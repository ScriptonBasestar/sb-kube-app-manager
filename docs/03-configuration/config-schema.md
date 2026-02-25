---
type: API Reference
audience: End User
topics: [configuration, schema, sbkube-yaml, unified-config]
llm_priority: high
last_updated: 2026-02-25
---

# 📋 SBKube Configuration Schema (v0.11.0)

> **단일 설정 파일** `sbkube.yaml`로 모든 배포 설정을 관리합니다.

## TL;DR

- **Format**: `sbkube.yaml` (apiVersion: sbkube/v1)
- **Version**: v0.11.0
- **Key Points**:
  - 단일 파일로 클러스터 설정 + 앱 정의 + Phase 오케스트레이션 통합
  - Settings 상속: global → phase → app
  - 9가지 앱 타입: helm, yaml, git, http, action, exec, kustomize, noop, hook
  - Phase 의존성 기반 다단계 배포
  - Pydantic `extra="forbid"` 강타입 검증
- **Related**:
  - **App Types**: [application-types.md](../02-features/application-types.md)
  - **Commands**: [commands.md](../02-features/commands.md)
  - **Migration**: [migration-guide.md](migration-guide.md)

> ⚠️ **Legacy Format Deprecated**: `sources.yaml` + `config.yaml` 분리 형식은 deprecated입니다.
> v0.11.0부터 `sbkube.yaml` 통합 형식을 사용하세요. 마이그레이션은 [migration-guide.md](migration-guide.md) 참조.

---

## 기본 구조

```yaml
# sbkube.yaml
apiVersion: sbkube/v1

metadata:
  name: my-deployment
  environment: production
  description: Production k3s cluster deployment

settings:
  kubeconfig: ~/.kube/config
  kubeconfig_context: production
  namespace: default
  timeout: 600
  on_failure: stop
  rollback_scope: app

  helm_repos:
    grafana: https://grafana.github.io/helm-charts

apps:
  nginx:
    type: helm
    chart: bitnami/nginx
    version: "15.0.0"

phases:
  p1-infra:
    source: p1-infra/sbkube.yaml
  p2-app:
    source: p2-app/sbkube.yaml
    depends_on: [p1-infra]
```

---

## Settings Reference

### UnifiedSettings

| Field | Type | Default | Description |
|-------|------|---------|-------------|
| `kubeconfig` | string | null | kubeconfig 파일 경로 |
| `kubeconfig_context` | string | null | Kubernetes context |
| `namespace` | string | `"default"` | 기본 네임스페이스 |
| `timeout` | int | `600` | 배포 타임아웃 (초, 1-7200) |
| `on_failure` | string | `"stop"` | 실패 정책: `stop`, `continue`, `rollback` |
| `rollback_scope` | string | `"app"` | 롤백 범위: `app`, `phase`, `all` |
| `execution_order` | string | `"apps_first"` | 실행 순서: `apps_first`, `phases_first` |
| `parallel` | bool | `false` | Phase 병렬 실행 |
| `parallel_apps` | bool | `false` | Phase 내 앱 병렬 실행 |
| `max_workers` | int | `4` | 최대 병렬 워커 (1-32) |
| `helm_label_injection` | bool | `true` | Helm 라벨 자동 주입 |
| `incompatible_charts` | list | `[]` | 라벨 주입 제외 차트 |
| `force_label_injection` | list | `[]` | 라벨 주입 강제 차트 |
| `cleanup_metadata` | bool | `true` | 서버 관리 메타데이터 자동 제거 |
| `helm_repos` | dict | `{}` | Helm 저장소 |
| `oci_registries` | dict | `{}` | OCI 레지스트리 |
| `git_repos` | dict | `{}` | Git 저장소 |

### on_failure 옵션

- **stop**: 첫 번째 실패 시 즉시 중단 (기본값)
- **continue**: 나머지 앱/Phase 계속 실행
- **rollback**: `rollback_scope`에 따라 롤백

### rollback_scope 옵션

- **app**: 실패한 앱만 롤백 (기본값)
- **phase**: 실패한 Phase 전체 롤백
- **all**: 전체 배포 롤백

### execution_order 옵션

- **apps_first**: 루트 앱 실행 → Phase 실행 (기본값)
- **phases_first**: Phase 실행 → 루트 앱 실행

---

## Helm Repository Configuration

### Simple Format

```yaml
settings:
  helm_repos:
    grafana: https://grafana.github.io/helm-charts
    prometheus: https://prometheus-community.github.io/helm-charts
```

### Detailed Format (인증 포함)

```yaml
settings:
  helm_repos:
    private-repo:
      url: https://charts.example.com
      username: myuser
      password: mypassword

    tls-repo:
      url: https://secure-charts.example.com
      ca_file: /path/to/ca.crt
      cert_file: /path/to/client.crt
      key_file: /path/to/client.key

    insecure-repo:
      url: https://self-signed.example.com
      insecure_skip_tls_verify: true
```

### OCI Registry

```yaml
settings:
  oci_registries:
    ghcr:
      url: ghcr.io/myorg
      username: ${GITHUB_USER}
      password: ${GITHUB_TOKEN}

    harbor:
      registry: harbor.example.com
      username: admin
      password: Harbor12345
```

**Auto-prefixing**: `ghcr.io` → `oci://ghcr.io`

### Git Repository

```yaml
settings:
  git_repos:
    my-charts:
      url: https://github.com/example/helm-charts.git
      branch: main

    ssh-repo:
      url: git@github.com:example/charts.git
      branch: main
      ssh_key: ~/.ssh/id_rsa
```

---

## App Configuration

### 공통 필드

모든 앱 타입이 공유하는 필드:

```yaml
apps:
  app-name:                    # 앱 이름 (key)
    type: enum                 # 앱 타입 (필수)
    enabled: boolean           # 활성화 여부 (기본: true)
    depends_on: [string]       # 앱 간 의존성 (선택)
    namespace: string          # 앱별 네임스페이스 (선택)
    notes: string              # 설명/메모 (선택)
    labels: dict               # 커스텀 라벨 (선택)
    annotations: dict          # 커스텀 어노테이션 (선택)
```

**Namespace 상속 규칙:**

1. **앱별 namespace** (최우선): `app.namespace`
2. **전역 namespace** (폴백): `settings.namespace`
3. **kubectl 기본값**: `default`

### 앱 타입별 설정

> 상세 앱 타입 가이드: [application-types.md](../02-features/application-types.md)

#### helm — Helm 차트

```yaml
apps:
  grafana:
    type: helm
    chart: grafana/grafana          # repo/chart (원격) 또는 ./path (로컬)
    version: "10.1.2"               # 차트 버전 (원격만)
    values:                         # values 파일 목록
      - values/grafana.yaml
    overrides:                      # 차트 파일 교체 (Glob 지원)
      - templates/secret.yaml
      - templates/*.yaml
    removes:                        # 차트 파일 삭제
      - templates/tests/
    release_name: my-grafana        # Helm 릴리스 이름 (기본: 앱 이름)
    wait: true                      # 준비 완료 대기 (기본: true)
    timeout: "5m"                   # 대기 타임아웃 (기본: 5m)
    atomic: false                   # 실패 시 자동 롤백 (기본: false)
    helm_label_injection: true      # 라벨 자동 주입 (기본: true)
```

**chart 필드 형식:**

| 형식 | 타입 | 예시 |
|------|------|------|
| `repo/chart` | 원격 | `grafana/grafana` |
| `./path` | 로컬 (상대) | `./charts/my-app` |
| `/path` | 로컬 (절대) | `/opt/charts/app` |

**Overrides 시스템** (build 단계에서 적용):

```
overrides/<app-name>/templates/secret.yaml  →  build/<app-name>/templates/secret.yaml
```

- `overrides/` 디렉토리의 파일이 차트 파일을 교체
- Glob 패턴 지원: `*`, `?`, `**`
- config에 명시된 파일만 적용 (자동 탐색 없음)

**OCI 레지스트리 차트**: `settings.oci_registries`에 등록 후 `registry-name/chart-name` 형식 사용

```yaml
settings:
  oci_registries:
    ghcr:
      registry: oci://ghcr.io/myorg/charts
apps:
  my-app:
    type: helm
    chart: ghcr/my-chart       # OCI 레지스트리 참조
    version: "1.0.0"
```

#### yaml — YAML 매니페스트

```yaml
apps:
  nginx:
    type: yaml
    manifests:
      - manifests/deployment.yaml
      - manifests/service.yaml
      - ${repos.olm}/deploy/crds.yaml    # Git 리포 변수 참조
```

#### git — Git 리포지토리

```yaml
apps:
  source:
    type: git
    repo: my-app               # settings.git_repos의 저장소 이름
    path: charts/app           # 리포지토리 내 경로 (선택)
```

#### http — HTTP 파일 다운로드

```yaml
apps:
  download:
    type: http
    url: https://example.com/manifest.yaml
    dest: manifest.yaml
    headers:
      Authorization: "Bearer token"
```

#### action — 커스텀 액션

```yaml
apps:
  setup:
    type: action
    actions:
      - type: apply
        path: manifests/crd.yaml
      - type: delete
        path: manifests/old.yaml
```

#### exec — 커스텀 명령어

```yaml
apps:
  check:
    type: exec
    commands:
      - kubectl get nodes
      - helm list -A
```

> ⚠️ **보안 주의**: `exec` 타입은 로컬 머신에서 임의 명령어를 실행합니다.
> `SBKUBE_ALLOW_EXEC=false`로 비활성화 가능.

#### noop — No Operation

```yaml
apps:
  manual-step:
    type: noop
    notes: "수동 설정 완료 표시용"
```

#### hook — HookApp (v0.8.0+)

```yaml
apps:
  setup-issuers:
    type: hook
    hooks:
      post_deploy_tasks:
        - type: manifests
          paths:
            - manifests/cluster-issuer.yaml
```

---

## Phase Reference

Phase로 다단계 배포를 오케스트레이션합니다.

### 외부 참조

```yaml
phases:
  p1-infra:
    description: Infrastructure components
    source: p1-infra/sbkube.yaml
    depends_on: []
```

### 인라인 정의

```yaml
phases:
  p1-infra:
    description: Infrastructure components
    apps:
      traefik:
        type: helm
        chart: traefik/traefik
        version: "25.0.0"
```

### Phase 옵션

| Field | Type | Required | Description |
|-------|------|----------|-------------|
| `description` | string | No | Phase 설명 |
| `source` | string | No* | 외부 sbkube.yaml 경로 |
| `apps` | dict | No* | 인라인 앱 정의 |
| `depends_on` | list | No | Phase 의존성 |
| `settings` | object | No | Phase 설정 오버라이드 |

\* `source` 또는 `apps` 중 하나 필수.

---

## Settings Inheritance

Settings는 부모 → 자식으로 상속됩니다:

- **Scalars**: 자식이 부모를 오버라이드
- **Lists**: 병합 후 중복 제거
- **Dicts**: Deep merge

```yaml
# Root sbkube.yaml
settings:
  timeout: 600
  namespace: default
  helm_repos:
    bitnami: https://charts.bitnami.com/bitnami

phases:
  p1-infra:
    source: p1-infra/sbkube.yaml
    settings:
      timeout: 300              # timeout만 오버라이드
```

```yaml
# p1-infra/sbkube.yaml
settings:
  namespace: kube-system        # namespace 오버라이드
  helm_repos:
    traefik: https://helm.traefik.io/traefik  # 부모 repos에 추가

apps:
  traefik:
    type: helm
    chart: traefik/traefik
    # 최종 설정: timeout=300, namespace=kube-system
    # helm_repos: {bitnami: ..., traefik: ...}
```

---

## Recursive Execution

```
sbkube.yaml (root)
├── apps (root-level)
└── phases
    ├── p1-infra/sbkube.yaml
    │   ├── apps
    │   └── phases (nested)
    └── p2-app/sbkube.yaml
        └── apps
```

**실행 흐름:**

1. 부모 settings와 현재 settings 머지
2. `execution_order`에 따라:
   - `apps_first`: 루트 앱 실행 → Phase 실행
   - `phases_first`: Phase 실행 → 루트 앱 실행
3. 각 Phase (의존성 순서):
   - 참조 config 로드 (source)
   - 상속된 settings로 재귀 실행

---

## Manifest Metadata Cleanup

`cleanup_metadata: true` (기본값) 시 template 단계에서 자동 제거되는 필드:

- `metadata.managedFields`
- `metadata.creationTimestamp`
- `metadata.resourceVersion`
- `metadata.uid`
- `metadata.generation`
- `metadata.selfLink`
- `status` (전체)

이 필드들은 Kubernetes API 서버가 관리하며, 사용자 매니페스트에 포함 시 배포 실패를 유발합니다.

---

## Complete Example

```yaml
apiVersion: sbkube/v1

metadata:
  name: production-cluster
  environment: production
  version: "1.0.0"

settings:
  kubeconfig: ~/.kube/config
  kubeconfig_context: production-k3s
  namespace: default
  timeout: 600
  on_failure: rollback
  rollback_scope: phase
  execution_order: phases_first
  parallel: true
  max_workers: 4

  helm_repos:
    bitnami:
      url: https://charts.bitnami.com/bitnami
    traefik:
      url: https://helm.traefik.io/traefik

  incompatible_charts:
    - traefik/traefik
    - jetstack/cert-manager

apps:
  monitoring-crd:
    type: helm
    chart: prometheus-community/kube-prometheus-stack-crds

phases:
  p1-infra:
    description: Core infrastructure
    source: phases/p1-infra/sbkube.yaml

  p2-networking:
    description: Networking
    source: phases/p2-networking/sbkube.yaml
    depends_on: [p1-infra]

  p3-apps:
    description: Applications
    source: phases/p3-apps/sbkube.yaml
    depends_on: [p1-infra, p2-networking]

  p4-monitoring:
    description: Monitoring (inline)
    apps:
      prometheus:
        type: helm
        chart: prometheus-community/kube-prometheus-stack
        namespace: monitoring
    depends_on: [p1-infra]
```

---

## Validation

```bash
# 설정 검증
sbkube validate

# Dry-run 검증
sbkube apply -f sbkube.yaml --dry-run

# 환경 진단
sbkube doctor
```

---

## Related Documentation

- **앱 타입 상세**: [application-types.md](../02-features/application-types.md)
- **명령어 참조**: [commands.md](../02-features/commands.md)
- **마이그레이션**: [migration-guide.md](migration-guide.md)
- **Hooks**: [hooks-guide.md](../02-features/hooks-guide.md)
- **아키텍처**: [ARCHITECTURE.md](../../ARCHITECTURE.md)

---

**Document Version**: 3.0
**Last Updated**: 2026-02-25
**SBKube Version**: 0.11.0
