---
type: User Guide & Reference
audience: End User
topics: [hooks, automation, lifecycle, reference]
llm_priority: medium
last_updated: 2026-02-25
---

# 🔗 SBKube Hooks Guide & Reference

> 배포 워크플로우의 각 단계에서 커스텀 스크립트를 실행하는 Hooks 시스템 가이드입니다.

> **보안 주의**: Hooks는 **로컬 머신**에서 명령어/스크립트를 실행합니다.
> `SBKUBE_ALLOW_EXEC=false` 환경변수로 비활성화 가능.

## TL;DR

- **Purpose**: 명령어/배포 전후에 커스텀 스크립트 실행
- **Version**: v0.11.0
- **Levels**: Command-level (전역) / App-level (앱별)
- **Hook Types**: Shell, Manifests, Tasks, HookApp
- **Key Hooks**: `pre_*`, `post_*`, `on_*_failure`
- **Related**:
  - **Config**: [config-schema.md](../03-configuration/config-schema.md)
  - **App Types**: [application-types.md](application-types.md)
  - **Architecture**: [ARCHITECTURE.md](../../ARCHITECTURE.md)

---

## Hook Levels

### 1. Command-Level Hooks (전역)

모든 앱 배포 전후에 실행됩니다.

```yaml
# sbkube.yaml
apiVersion: sbkube/v1

settings:
  namespace: production

hooks:
  prepare:
    pre:
      - echo "Preparing apps..."
    post:
      - echo "All apps prepared"
    on_failure:
      - echo "Preparation failed"
  deploy:
    pre:
      - echo "Deploying..."
    post:
      - echo "Deploy complete"
    on_failure:
      - ./scripts/notify-failure.sh
```

### 2. App-Level Hooks (앱별)

특정 앱의 배포 전후에 실행됩니다.

```yaml
apps:
  grafana:
    type: helm
    chart: grafana/grafana
    hooks:
      pre_prepare:
        - echo "Preparing grafana..."
      post_deploy:
        - kubectl rollout status deployment/grafana -n monitoring
      on_deploy_failure:
        - ./scripts/alert-grafana-failure.sh
```

---

## Hook Naming Convention

### Command-Level

```yaml
hooks:
  <command>:           # prepare, build, template, deploy, apply
    pre: [...]
    post: [...]
    on_failure: [...]
```

### App-Level

```yaml
apps:
  <app-name>:
    hooks:
      pre_<command>: [...]
      post_<command>: [...]
      on_<command>_failure: [...]
```

지원 명령어: `prepare`, `build`, `template`, `deploy`, `apply`

---

## Execution Order

```
1. Command-level pre hooks
2. For each app (dependency order):
   a. App-level pre_<command> hooks
   b. Execute command for app
   c. App-level post_<command> hooks (성공 시)
   c'. App-level on_<command>_failure hooks (실패 시)
3. Command-level post hooks (모든 앱 성공 시)
3'. Command-level on_failure hooks (실패 시)
```

### apply 명령어 실행 순서

`sbkube apply`는 내부적으로 `prepare → build → template → deploy`를 순차 실행합니다:

```
Command-level apply pre hooks
  ├─ prepare (with its own hooks)
  ├─ build (with its own hooks)
  ├─ template (with its own hooks)
  └─ deploy (with its own hooks)
Command-level apply post hooks
```

---

## Hook Types

### Phase 1: Shell Hooks (기본)

가장 기본적인 형태. 문자열 리스트로 정의합니다.

```yaml
hooks:
  deploy:
    pre:
      - echo "Starting deploy"
      - kubectl get nodes
    post:
      - ./scripts/post-deploy-check.sh
```

### Phase 2: Manifest Hooks

Kubernetes 매니페스트를 Hook에서 직접 적용합니다.

```yaml
apps:
  cert-manager:
    type: helm
    chart: jetstack/cert-manager
    hooks:
      post_deploy_manifests:
        - manifests/cluster-issuer.yaml
        - manifests/certificates/
```

### Phase 3: Task Hooks

타입 기반 구조화된 Hook입니다.

```yaml
apps:
  cert-manager:
    type: helm
    chart: jetstack/cert-manager
    hooks:
      post_deploy_tasks:
        - type: shell
          command: kubectl wait --for=condition=ready pod -l app=cert-manager
          timeout: 120

        - type: manifests
          paths:
            - manifests/cluster-issuer.yaml
          namespace: cert-manager

        - type: validate
          command: kubectl get clusterissuer -o jsonpath='{.items[0].status.conditions[0].type}'
          expected: Ready
          retry: 3
          retry_delay: 10
```

### Phase 4: HookApp (type: hook)

앱으로 정의하여 depends_on 등 앱 기능을 활용합니다.

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
        - type: manifests
          paths:
            - manifests/cluster-issuer.yaml
        - type: validate
          command: kubectl get clusterissuer letsencrypt-prod -o jsonpath='{.status.conditions[0].type}'
          expected: Ready
          retry: 5
          retry_delay: 15
```

---

## Task Types Reference

| Task Type | 설명 | 주요 필드 |
|-----------|------|-----------|
| `shell` | 셸 명령어 실행 | `command`, `timeout` |
| `manifests` | K8s 매니페스트 적용 | `paths`, `namespace` |
| `validate` | 상태 검증 | `command`, `expected`, `retry`, `retry_delay` |
| `wait` | 리소스 대기 | `resource`, `condition`, `timeout` |
| `http` | HTTP 요청 | `url`, `method`, `expected_status` |

### validate Task

```yaml
- type: validate
  command: kubectl get pods -l app=redis -o jsonpath='{.items[0].status.phase}'
  expected: Running
  retry: 5              # 재시도 횟수 (기본: 1)
  retry_delay: 10       # 재시도 간격 초 (기본: 5)
  timeout: 120          # 전체 타임아웃 초
```

### wait Task

```yaml
- type: wait
  resource: deployment/redis
  condition: available
  namespace: cache
  timeout: 300
```

### http Task

```yaml
- type: http
  url: http://localhost:8080/healthz
  method: GET
  expected_status: 200
  retry: 3
  retry_delay: 5
```

---

## Environment Variables

Hook 실행 시 자동 설정되는 환경 변수:

### 전역 변수

| 변수 | 설명 | 예시 |
|------|------|------|
| `SBKUBE_VERSION` | SBKube 버전 | `0.11.0` |
| `SBKUBE_COMMAND` | 실행 중 명령어 | `deploy` |
| `SBKUBE_HOOK_PHASE` | Hook 단계 | `pre`, `post`, `on_failure` |
| `SBKUBE_NAMESPACE` | 전역 네임스페이스 | `production` |
| `SBKUBE_KUBECONFIG` | kubeconfig 경로 | `~/.kube/config` |
| `SBKUBE_CONTEXT` | kubectl 컨텍스트 | `k3s-prod` |
| `SBKUBE_DRY_RUN` | Dry-run 모드 여부 | `true`, `false` |

### 앱별 변수 (App-Level Hook 전용)

| 변수 | 설명 | 예시 |
|------|------|------|
| `SBKUBE_APP_NAME` | 앱 이름 | `grafana` |
| `SBKUBE_APP_TYPE` | 앱 타입 | `helm` |
| `SBKUBE_APP_NAMESPACE` | 앱 네임스페이스 | `monitoring` |
| `SBKUBE_APP_STATUS` | 실행 결과 | `success`, `failed` |
| `SBKUBE_HELM_CHART` | Helm 차트 | `grafana/grafana` |
| `SBKUBE_HELM_VERSION` | 차트 버전 | `10.1.2` |

---

## Error Handling

### on_failure 전략

```yaml
apps:
  grafana:
    type: helm
    chart: grafana/grafana
    hooks:
      on_deploy_failure:
        - echo "Grafana deploy failed: $SBKUBE_APP_NAME"
        - ./scripts/notify-slack.sh "$SBKUBE_APP_NAME deployment failed"
        - kubectl describe pod -l app=grafana -n monitoring
```

### Hook 실패 동작

| Hook 위치 | 실패 시 동작 |
|-----------|-------------|
| `pre_*` | 해당 앱/명령어 실행 **중단** |
| `post_*` | 경고 로그, 나머지 프로세스 **계속** |
| `on_*_failure` | 경고 로그만 (cascade 방지) |

### validate + retry 패턴

```yaml
apps:
  redis:
    type: helm
    chart: bitnami/redis
    hooks:
      post_deploy_tasks:
        - type: validate
          command: redis-cli -h redis.cache ping
          expected: PONG
          retry: 10
          retry_delay: 5
          timeout: 120
```

---

## Best Practices

### 1. 멱등성 보장

```yaml
# ✅ 좋은 예: 멱등한 hook
hooks:
  post_deploy:
    - kubectl apply -f manifests/config.yaml    # 멱등
    - kubectl create ns monitoring --dry-run=client -o yaml | kubectl apply -f -

# ❌ 나쁜 예: 비멱등 hook
hooks:
  post_deploy:
    - kubectl create ns monitoring              # 이미 존재하면 실패
```

### 2. 타임아웃 설정

```yaml
hooks:
  post_deploy_tasks:
    - type: shell
      command: ./scripts/long-running.sh
      timeout: 300  # 5분 제한
```

### 3. 에러 알림

```yaml
hooks:
  deploy:
    on_failure:
      - |
        curl -X POST https://hooks.slack.com/services/xxx \
          -H 'Content-type: application/json' \
          -d '{"text": "Deploy failed: '$SBKUBE_COMMAND' for '$SBKUBE_APP_NAME'"}'
```

### 4. HookApp으로 복잡한 후처리

```yaml
apps:
  cert-manager:
    type: helm
    chart: jetstack/cert-manager

  # HookApp: depends_on으로 순서 보장
  cert-manager-setup:
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
          command: kubectl get clusterissuer -o jsonpath='{.items[0].status.conditions[0].type}'
          expected: Ready
          retry: 5
          retry_delay: 15
```

---

## Related Documentation

- **Config Schema**: [config-schema.md](../03-configuration/config-schema.md)
- **Application Types**: [application-types.md](application-types.md)
- **Commands**: [commands.md](commands.md)
- **Architecture**: [ARCHITECTURE.md](../../ARCHITECTURE.md)

---

**Document Version**: 3.0
**Last Updated**: 2026-02-25
**SBKube Version**: 0.11.0
