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

## Deploy Gate (`sbkube-gate.yaml`)

클러스터를 바꾸는 명령(`deploy`, `apply`, `upgrade`, `delete`, `rollback`, `migrate`)은 실행 전에
설정된 외부 명령을 돌리고, 그 종료코드로 진행 여부를 정한다. 설정은 `sbkube.yaml`이 아니라 별도
`sbkube-gate.yaml` 파일의 `deploy_gate` 블록에 둔다 — 게이트 설정만 편집 보호 경로로 묶을 수 있게
하기 위해서다. **`sbkube-gate.yaml`이 하나도 없으면 게이트도 없고 동작은 그대로다.**

```yaml
# <workspace root>/sbkube-gate.yaml  (.sbkube-workspace 옆) — 전역
deploy_gate:
  command: "uv run scripts/full_ci_gate.py gate"
  mode: enforce            # enforce | warn | off — 필수, 기본값 없음
  precedence: asymmetric   # asymmetric(기본) | individual | global — 전역 파일만
  allow_override: false    # 전역 파일만
  timeout: 60              # 전역 파일만, 선택 — 게이트 명령 제한 시간(초)
  agent_grant:             # 전역 파일만, 선택 — 있으면 `sbkube gate grant` 허용
    ttl: 1h                # <n>m | <n>h | <n>d | unlimited (기본 1h)
```

```yaml
# <phase 또는 앱 그룹 디렉토리>/sbkube-gate.yaml — 개별
deploy_gate:
  mode: off
```

| 필드 | 위치 | 설명 |
|------|------|------|
| `command` | 전역만 | 게이트 명령. 셸 없이 `shlex`로 나눠 실행한다. 최종 `mode`가 `off`가 아니면 필수 |
| `mode` | 전역 필수, 개별 선택 | `enforce`: 실패 시 거부 / `warn`: 경고 후 진행 / `off`: 게이트 없음. 개별 파일은 이 값만 둘 수 있다 |
| `precedence` | 전역만 | 전역과 개별 `mode`가 다를 때의 규칙 |
| `allow_override` | 전역만 | `asymmetric`에서 개별 파일의 완화를 허용 |
| `timeout` | 전역만 | 게이트 명령의 제한 시간(초, 0보다 큰 수). 생략하면 제한 없음. 만료 시 `enforce`는 거부(fail closed), `warn`은 경고 후 계속 |
| `agent_grant.ttl` | 전역만 | 있으면 사람이 `sbkube gate grant --pid`로 에이전트 세션에 게이트 통과를 허용할 수 있다. 기간 `<n>m`/`<n>h`/`<n>d` 또는 `unlimited`(세션 프로세스가 끝날 때까지) |

파일 찾기:

- 범위: `.sbkube-workspace`가 있으면 그 워크스페이스 루트, 없으면 대상을 감싼 저장소 루트(`.git`)
  안에서만 위로 찾는다. 범위 밖 상위 디렉토리의 파일은 보지 않는다. 둘 다 없으면 파일시스템 루트까지
  올라간다.
- 전역: 워크스페이스가 있으면 루트의 `sbkube-gate.yaml`, 없으면 범위 안에서 대상 위로 올라가며 찾은
  가장 위의 파일.
- 개별: 대상 디렉토리에서 위로 올라가며 처음 만나는 파일(전역 제외), 그리고 대상 아래의 모든 파일.
  루트에서 `apply`하면 phase마다 둔 개별 파일이 모두 반영된다. 아래로는 전역 파일이 있을 때만
  찾는다. `.`으로 시작하는 디렉토리는 건너뛰고, 심볼릭 링크는 실제 경로가 범위 안일 때만 따라간다.
  바깥 `apply`가 안쪽까지 배포하므로 자체 `.sbkube-workspace`나 `.git`이 있는 하위 디렉토리도
  찾으며, 그 안의 파일도 개별 파일로 취급한다(`command` 등 전역 전용 키가 있으면 거부).
- 대상 위치나 그 위에 전역 파일 없이 개별 파일만 있으면 오류로 거부한다. 전역 파일이 없으면 아래를
  찾지 않으므로, 루트에서 `apply`할 때 phase에만 둔 파일은 감지되지 않고 게이트 없이 실행된다.
  개별 파일은 전역 파일이 있어야 효력이 있다.
- phase `source`가 워크스페이스 밖(`../shared/...`)을 가리켜도 대상의 `sbkube.yaml`에서 `phases`를
  따라가 그 디렉토리와 아래의 게이트 파일을 개별 파일로 반영한다. 그 안의 심볼릭 링크는 해당 phase
  디렉토리 안을 가리킬 때만 따라간다.
- 개별 파일마다 아래 우선순위로 모드를 정하고, 그중 **가장 엄격한 모드**로 전역 `command`를 한 번
  돌린다.
- 대상 디렉토리: `-f`가 있으면 그 파일의 디렉토리, 아니면 `TARGET`, 아니면 현재 디렉토리.
  `rollback`은 상태 DB에 기록된 배포의 앱 디렉토리(없으면 `--base-dir`/`--app-dir`),
  `migrate`는 `TARGET`(없으면 현재 디렉토리)이다.
- 게이트는 저장소 단위 opt-in이다. 게이트 파일이 있는 저장소 밖에서 대상 없이 실행한 `migrate`나
  기록이 없는 `rollback`은 게이트 파일을 찾지 못해 게이트 없이 실행된다.
- 읽을 수 없거나 형식이 틀린 파일은 명령을 거부한다(fail closed). 모르는 키도 오류다.

우선순위(강화 = `off` → `warn` → `enforce`). 어느 규칙이든 전역과 개별이 어긋나면 두 파일 경로와
값, 적용 결과를 경고로 찍고 실행한다.

| `precedence` | 개별이 강화 | 개별이 완화 |
|--------------|-------------|-------------|
| `asymmetric` (기본) | 개별 | `allow_override: true`일 때만 개별, 아니면 전역 |
| `individual` | 개별 | 개별 |
| `global` | 개별 | 전역 |

게이트 명령 호출:

- 인자 하나로 작업 이름을 받는다: `deploy`, `apply`, `upgrade`, `delete`, `rollback`, `migrate`,
  `apply --prune-disabled`이면 `prune`.
- 환경변수 `SBKUBE_GATE_OPERATION`(작업 이름), `SBKUBE_GATE_TARGET`(대상 디렉토리)이 추가된다.
- 작업 디렉토리는 전역 파일의 디렉토리다.
- `--dry-run`과 `rollback --list`는 클러스터를 바꾸지 않으므로 게이트를 돌리지 않는다.
- `apply`가 내부에서 `deploy`를 부르거나 workspace phase를 스레드로 돌려도 게이트는 바깥 명령에서
  한 번만 돈다. 단, `WorkspaceDeployCommand`를 import하지 못해 `sbkube apply` 하위 프로세스로
  넘어가는 대체 경로에서는 하위 프로세스가 게이트를 다시 돈다.

사람의 건너뛰기는 `--skip-deploy-gate=<사유>` 한 가지다
([commands.md](../02-features/commands.md#deploy-gate-건너뛰기)). 환경변수로 끄는 방법은 없다.

에이전트 세션 허용은 `agent_grant`가 있을 때 사람이 터미널에서 `sbkube gate grant --pid <PID>`로
준다([commands.md](../02-features/commands.md#gate-grant--에이전트-세션-허용)). 게이트는 허용된 프로세스(PID와
시작 시각)가 현재 명령의 조상이고 기간이 남았을 때 게이트 명령 없이 통과하며, 남은 기간을 경고로 찍는다.
프로세스 목록(`ps`)을 읽지 못하면 허용 없이 게이트 명령을 돌린다.

YAML 1.1 파서는 따옴표 없는 `off`를 불리언으로 읽지만 `mode`에서는 `off`로 받아들인다.

---

## Access (에이전트 접근 경계)

에이전트는 사람과 같은 OS 사용자로 sbkube를 실행하므로, 우회할 수 없는 경계는 Kubernetes RBAC뿐이다.
에이전트에게는 읽기 전용 ServiceAccount의 kubeconfig를 주고, 배포는 사람이 발급한 짧은 수명 토큰으로 한다.
`settings.access`는 그 설정이다. 1단계에서는 스키마와 읽기 전용 명령
(`sbkube access verify`·`audit`, [commands.md](../02-features/commands.md#access-verify--읽기-전용-자격증명-확인))만 있다.

```yaml
settings:
  kubeconfig: ~/.kube/polypia-cluster          # 관리자 자격증명
  kubeconfig_context: polypia-cluster
  access:
    auto_profile: true
    namespace: agent-access
    token_dir: ~/.kube/agent-access
    readonly:
      service_account: agent-readonly
      kubeconfig: ~/.kube/polypia-cluster-agent
      extra_rules:                             # RBAC PolicyRule 형식
        - apiGroups: ["cert-manager.io"]
          resources: ["certificates"]
          verbs: ["get", "list"]
    deployer:
      service_account: sbkube-deployer
      kubeconfig: ~/.kube/polypia-cluster-deploy
      token_ttl: 1h
```

| Field | Type | Default | Description |
|-------|------|---------|-------------|
| `access.auto_profile` | bool | `true` | 명령별 kubeconfig 자동 선택. 1단계에서는 스키마만 있고 동작하지 않음 |
| `access.namespace` | string | `"agent-access"` | ServiceAccount를 두는 네임스페이스 |
| `access.token_dir` | string | `"~/.kube/agent-access"` | 토큰 파일 디렉토리 |
| `access.readonly.service_account` | string | `"agent-readonly"` | 에이전트용 ServiceAccount |
| `access.readonly.kubeconfig` | string | null | 에이전트 kubeconfig 경로 |
| `access.readonly.extra_rules` | list | `[]` | 추가 읽기 규칙: `apiGroups`, `resources`, `verbs`(필수, 1개 이상), `resourceNames`, `nonResourceURLs`. `resources`와 `nonResourceURLs` 중 정확히 하나만 지정하고, 빈 문자열 항목은 거부 |
| `access.deployer.service_account` | string | `"sbkube-deployer"` | 배포용 ServiceAccount |
| `access.deployer.kubeconfig` | string | null | 배포 kubeconfig 경로 |
| `access.deployer.token_ttl` | string | `"1h"` | 발급 토큰 수명. `30m`, `1h`, `1h30m` 같은 Go 형식. 단위는 `h`·`m`·`s` 순서로 한 번씩만(`1h1h` 거부), 최소 `10m`(TokenRequest `expirationSeconds` ≥ 600) |

- 모든 모델은 `extra="forbid"`라 알 수 없는 필드는 거부된다.
- `access`는 전역(루트) `settings`에서만 읽는다. 상속 대상 설정에 포함되지 않으므로 phase·앱 수준에 적어도
  검증만 통과할 뿐 어떤 명령도 읽지 않는다.
- `access`가 없으면 동작은 이전과 같다.

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
