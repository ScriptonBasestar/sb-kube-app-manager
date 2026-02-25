---
type: API Reference
audience: End User
topics: [app-types, helm, yaml, git, http, action, exec, kustomize, noop, hook]
llm_priority: high
last_updated: 2026-02-25
---

# 📦 SBKube Application Types

> SBKube가 지원하는 9가지 앱 타입과 각 타입의 설정·워크플로우 참조 문서입니다.

## TL;DR

- **Version**: v0.11.0
- **9 Types**: `helm`, `yaml`, `git`, `http`, `action`, `exec`, `kustomize`, `noop`, `hook`
- **Config Format**: `sbkube.yaml` (unified format only)
- **Related**:
  - **Config Schema**: [config-schema.md](../03-configuration/config-schema.md)
  - **Commands**: [commands.md](commands.md)

---

## App Type Summary

| Type | 용도 | prepare | build | deploy |
|------|------|---------|-------|--------|
| `helm` | Helm 차트 배포 | ✅ pull chart | ✅ overrides/removes | ✅ helm upgrade --install |
| `yaml` | YAML 매니페스트 적용 | - | - | ✅ kubectl apply |
| `git` | Git 리포 클론 | ✅ git clone | - | - |
| `http` | HTTP 파일 다운로드 | ✅ download | - | - |
| `action` | kubectl apply/delete | - | - | ✅ action 실행 |
| `exec` | 커맨드 실행 | - | - | ✅ 셸 명령어 |
| `kustomize` | Kustomize 빌드 | - | ✅ kustomize build | ✅ kubectl apply |
| `noop` | 아무것도 안 함 | - | - | - |
| `hook` | HookApp (커스텀 훅) | - | - | ✅ hook 실행 |

---

## helm

Helm 차트를 pull/build/deploy 합니다. 가장 많이 사용되는 타입입니다.

### Chart 형식

| chart 값 | 타입 | 예시 |
|----------|------|------|
| `repo/chart` | 원격 (Remote) | `grafana/grafana` |
| `./path` | 로컬 (상대경로) | `./charts/my-app` |
| `/path` | 로컬 (절대경로) | `/opt/charts/app` |

### 설정

```yaml
apps:
  grafana:
    type: helm

    # ── Chart Source ──
    chart: grafana/grafana          # repo/chart 또는 ./local-path
    version: "10.1.2"               # 원격 차트만 (권장: 항상 고정)

    # ── Values ──
    values:
      - values/grafana.yaml         # -f 플래그로 전달
      - values/grafana-prod.yaml

    # ── Chart Customization (build 단계에서 적용) ──
    overrides:                      # 차트 내부 파일 교체
      - values.yaml                 # overrides/<app>/values.yaml → build/<app>/values.yaml
      - templates/service.yaml
    removes:                        # 차트 내부 파일 삭제
      - README.md
      - templates/tests/

    # ── Deploy Options ──
    release_name: my-grafana        # Helm 릴리스 이름 (기본: 앱 이름)
    namespace: monitoring
    wait: true                      # 준비 완료 대기 (기본: true)
    timeout: "5m"                   # Helm 타임아웃 (기본: 5m)
    atomic: false                   # 실패 시 자동 롤백 (기본: false)

    # ── Label Injection ──
    helm_label_injection: true      # sbkube 라벨 자동 주입 (기본: true)
```

### Workflow

```
prepare → build → template → deploy
   │         │         │         │
   ▼         ▼         ▼         ▼
chart pull  overrides  helm     helm upgrade
to charts/  + removes  template --install
            to build/  to       --wait
                      rendered/
```

### Overrides 디렉토리 구조

```
project/
├── sbkube.yaml
├── overrides/
│   └── grafana/                    # 앱 이름과 동일
│       ├── values.yaml             # 교체할 파일
│       └── templates/
│           └── service.yaml
└── charts/                         # prepare에 의해 생성
    └── grafana/
        └── grafana/
```

**처리 순서**: 차트 복사 → overrides 적용 → removes 적용

### Chart Type Detection

```python
def is_remote_chart(self) -> bool:
    if self.chart.startswith("./") or self.chart.startswith("/"):
        return False  # 로컬
    if "/" in self.chart and not self.chart.startswith("."):
        return True   # repo/chart (원격)
    return False      # 단독 이름은 로컬
```

### OCI 차트

```yaml
settings:
  oci_registries:
    ghcr:
      registry: oci://ghcr.io/myorg/charts

apps:
  my-app:
    type: helm
    chart: ghcr/my-chart
    version: "1.0.0"
```

### Best Practices

- **버전 고정**: 원격 차트는 반드시 `version` 명시
- **incompatible_charts**: 라벨 주입과 호환되지 않는 차트는 `settings.incompatible_charts`에 등록
- **atomic**: 프로덕션에서는 `atomic: true` 권장
- **depends_on**: 앱 간 의존성은 순서만 보장. `wait: false` 사용 시 주의

---

## yaml

YAML 매니페스트를 직접 `kubectl apply`합니다.

```yaml
apps:
  ingress-rules:
    type: yaml
    manifests:
      - manifests/ingress.yaml
      - manifests/networkpolicy.yaml
      - ${repos.my-charts}/deploy/crds.yaml   # Git 리포 변수 참조
    namespace: web
```

**Workflow**: `deploy` 단계에서 `kubectl apply -f` 실행

**사용 사례**:
- CRD 적용
- 단순 ConfigMap/Secret 배포
- Helm 없이 리소스 직접 적용

---

## git

Git 리포지토리를 클론합니다. 다른 앱의 소스로 활용됩니다.

```yaml
settings:
  git_repos:
    my-charts:
      url: https://github.com/example/helm-charts.git
      branch: main

apps:
  clone-charts:
    type: git
    repo: my-charts
    path: charts/app               # 리포 내 경로 (선택)
```

**Workflow**: `prepare` 단계에서 `git clone` 실행

**사용 사례**:
- 외부 Helm 차트 가져오기
- 공통 매니페스트 리포지토리 동기화
- OLM Operator 번들 클론

---

## http

HTTP(S) URL에서 파일을 다운로드합니다.

```yaml
apps:
  download-crds:
    type: http
    url: https://github.com/cert-manager/cert-manager/releases/download/v1.14.0/cert-manager.crds.yaml
    dest: manifests/cert-manager-crds.yaml
    headers:
      Authorization: "Bearer ${GITHUB_TOKEN}"
```

**Workflow**: `prepare` 단계에서 HTTP GET 실행

**사용 사례**:
- CRD YAML 직접 다운로드
- 외부 매니페스트 가져오기

---

## action

`kubectl apply`/`delete` 액션을 실행합니다.

```yaml
apps:
  manage-resources:
    type: action
    actions:
      - type: apply
        path: manifests/namespace.yaml
      - type: apply
        path: manifests/rbac/
      - type: delete
        path: manifests/old-config.yaml
```

**Action Types**: `apply`, `delete`, `create`, `replace`, `patch`

**사용 사례**:
- 네임스페이스 생성 후 RBAC 적용
- 리소스 생성/삭제 순서 제어

---

## exec

로컬 셸 명령어를 실행합니다.

```yaml
apps:
  health-check:
    type: exec
    commands:
      - kubectl get nodes
      - helm list -A
      - ./scripts/validate-cluster.sh
```

> ⚠️ **보안 경고**: 로컬 머신에서 임의 명령어 실행.
> `SBKUBE_ALLOW_EXEC=false`로 비활성화 가능.

**사용 사례**:
- 클러스터 상태 검증
- 배포 후 헬스체크
- 외부 시스템 연동 스크립트

---

## kustomize

Kustomize 빌드 후 `kubectl apply`합니다.

```yaml
apps:
  my-app:
    type: kustomize
    path: overlays/production
    namespace: app
```

**Workflow**: `build` 단계에서 `kustomize build` → `deploy` 단계에서 `kubectl apply`

---

## noop

아무 동작도 하지 않습니다.

```yaml
apps:
  manual-step:
    type: noop
    notes: |
      수동으로 완료해야 하는 단계:
      1. DNS A 레코드 설정
      2. TLS 인증서 확인
```

**사용 사례**:
- 수동 작업 기록
- 배포 순서 내 placeholder
- depends_on 체인의 분기점

---

## hook

HookApp — 앱처럼 관리되는 Hook입니다. `depends_on` 등 앱 기능을 모두 활용할 수 있습니다.

```yaml
apps:
  cert-manager:
    type: helm
    chart: jetstack/cert-manager

  setup-issuers:
    type: hook
    depends_on: [cert-manager]
    hooks:
      post_deploy_tasks:
        - type: wait
          resource: deployment/cert-manager
          condition: available
          namespace: cert-manager
          timeout: 180
        - type: manifests
          paths:
            - manifests/cluster-issuer.yaml
        - type: validate
          command: kubectl get clusterissuer letsencrypt-prod -o jsonpath='{.status.conditions[0].type}'
          expected: Ready
          retry: 5
          retry_delay: 15
```

**사용 사례**:
- Helm 배포 후 CRD 인스턴스 생성
- 의존성 기반 후처리 (cert-manager → issuer)
- 복잡한 검증 로직

> 상세 Hook 가이드: [hooks-guide.md](hooks-guide.md)

---

## Common Fields

모든 앱 타입이 공유하는 필드:

| Field | Type | Default | Description |
|-------|------|---------|-------------|
| `type` | enum | (필수) | 앱 타입 |
| `enabled` | bool | `true` | 활성화 여부 |
| `depends_on` | list | `[]` | 앱 간 의존성 |
| `namespace` | string | settings 상속 | 앱별 네임스페이스 |
| `notes` | string | null | 설명/메모 |
| `labels` | dict | `{}` | 커스텀 라벨 |
| `annotations` | dict | `{}` | 커스텀 어노테이션 |
| `hooks` | object | null | 앱별 훅 |

---

## Dependency Management

```yaml
apps:
  database:
    type: helm
    chart: bitnami/postgresql

  cache:
    type: helm
    chart: bitnami/redis

  backend:
    type: helm
    chart: ./charts/backend
    depends_on: [database, cache]       # 병렬 의존성 (database, cache 완료 후 실행)

  frontend:
    type: helm
    chart: ./charts/frontend
    depends_on: [backend]
```

**규칙**:
- `depends_on`은 **배포 순서만** 보장
- 순환 의존성은 검증 오류
- `enabled: false`인 앱에 의존 시 경고

---

## Related Documentation

- **Config Schema**: [config-schema.md](../03-configuration/config-schema.md)
- **Hooks Guide**: [hooks-guide.md](hooks-guide.md)
- **Commands**: [commands.md](commands.md)
- **Architecture**: [ARCHITECTURE.md](../../ARCHITECTURE.md)

---

**Document Version**: 3.0
**Last Updated**: 2026-02-25
**SBKube Version**: 0.11.0
