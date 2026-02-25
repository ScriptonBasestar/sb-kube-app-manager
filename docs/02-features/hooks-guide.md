______________________________________________________________________

## type: User Guide audience: End User topics: [hooks, automation, lifecycle] llm_priority: medium last_updated: 2025-01-06

# SBKube Hooks Guide

> **주의**: 이 문서는 Hooks 시스템 사용자 가이드입니다. 기술적 구현 상세는 [ARCHITECTURE.md](../../docs/10-modules/sbkube/ARCHITECTURE.md)를 참조하세요.

SBKube hooks enable custom script execution before/after commands and deployments, providing powerful automation
capabilities for your Kubernetes workflows.

> **보안 주의**: Hooks는 **로컬 머신**에서 명령어/스크립트를 실행합니다. 신뢰된 설정만 사용하고, CI/공유 환경에서는 권한 제한을 고려하세요.
> `SBKUBE_ALLOW_EXEC=false` 환경변수로 hook 실행을 비활성화할 수 있습니다.

## TL;DR

- **Purpose**: Execute custom scripts before/after commands and deployments
- **Version**: v0.7.0 (개발 중), v0.6.0 (안정)
- **Levels**: Command-level (global) and App-level (per-app)
- **Key Hooks**: pre\_*, post\_*, on\_\*\_failure
- **Related**:
  - ****상위 문서**: [ARCHITECTURE.md](../../ARCHITECTURE.md) - 아키텍처 (어떻게)
  - **상세 참조**: [Hooks Reference](hooks-reference.md)
  - **제품 개요**: [PRODUCT.md](../../PRODUCT.md) - 제품 정의

## Overview

Hooks operate at two levels:

1. **Command-level**: Global hooks applying to all app deployments
1. **App-level**: App-specific hooks for individual applications

## Hook Types

### Command-Level Hooks

Define in the top-level `hooks:` section of config.yaml:

```yaml
namespace: production

hooks:
  # prepare command hooks
  prepare:
    pre:
      - echo "Preparing apps..."
    post:
      - echo "All apps prepared"
    on_failure:
      - echo "Preparation failed"

  # deploy command hooks
  deploy:
    pre:
      - echo "Starting deployment"
      - kubectl cluster-info
    post:
      - echo "Deployment completed"
      - kubectl get pods -n production
    on_failure:
      - echo "Deployment failed"
      - ./scripts/rollback.sh
```

### App-Level Hooks

Define in each app's `hooks` field:

```yaml
apps:
  database:
    type: helm
    chart: prometheus-community/kube-state-metrics
    hooks:
      # prepare stage hooks
      pre_prepare:
        - echo "Preparing database chart..."
      post_prepare:
        - echo "Database chart ready"

      # build stage hooks
      pre_build:
        - echo "Building database chart..."
      post_build:
        - echo "Database chart built"

      # deploy stage hooks
      pre_deploy:
        - echo "Backing up database..."
        - ./scripts/backup-db.sh
      post_deploy:
        - echo "Waiting for database..."
        - kubectl wait --for=condition=ready pod -l app=postgresql --timeout=300s
        - echo "Running migrations..."
        - ./scripts/migrate.sh
      on_deploy_failure:
        - echo "Database deployment failed!"
        - ./scripts/restore-backup.sh
```

## Configuration Examples

### Basic Global Hooks

```yaml
namespace: production

hooks:
  deploy:
    pre:
      - echo "=== Deployment started ==="
      - date
    post:
      - echo "=== Deployment completed ==="
      - date
```

### App-Specific Hooks

```yaml
apps:
  redis:
    type: helm
    chart: grafana/loki
    hooks:
      pre_deploy:
        - echo "Deploying Redis..."
      post_deploy:
        - kubectl get pods -l app=redis
```

### Hybrid Configuration (Global + App-Specific)

```yaml
namespace: production

# Global hooks (apply to all apps)
hooks:
  deploy:
    pre:
      - echo "Starting batch deployment"

apps:
  redis:
    type: helm
    chart: grafana/loki
    # App-specific hooks (this app only)
    hooks:
      post_deploy:
        - echo "Redis specific post-deploy task"
```

**Execution Order**: Global pre → App pre → Deployment → App post → Global post

## Execution Order

### Deploy Command Execution

```
1. Global pre-deploy hooks
2. For each app:
   2.1. App pre_deploy hooks
   2.2. App deployment
   2.3. App post_deploy hooks (on success) or on_deploy_failure hooks (on failure)
3. Global post-deploy hooks (on success) or on_failure hooks (on failure)
```

### Prepare Command Execution

```
1. Global pre-prepare hooks
2. For each app:
   2.1. App pre_prepare hooks
   2.2. App preparation (chart download, etc.)
   2.3. App post_prepare hooks
3. Global post-prepare hooks
```

## Environment Variables

Hooks automatically receive these environment variables:

| Variable | Description | Example | |----------|-------------|---------| | `SBKUBE_APP_NAME` | Current app name |
`redis` | | `SBKUBE_NAMESPACE` | Deployment namespace | `production` | | `SBKUBE_RELEASE_NAME` | Helm release name |
`my-redis` |

### Usage Example

```yaml
apps:
  backend:
    type: helm
    chart: ./charts/backend
    hooks:
      post_deploy:
        - echo "Deployed $SBKUBE_APP_NAME to $SBKUBE_NAMESPACE"
        - kubectl get pods -l release=$SBKUBE_RELEASE_NAME
```

## Working Directory

Hook scripts execute in the **directory specified by `--app-dir`**.

### Directory Structure Example

```
/project/                    # Project root (BASE_DIR)
├── sources.yaml             # Source configuration
├── redis_dir/               # Specified via --app-dir
│   ├── config.yaml          # App configuration
│   ├── values.yaml
│   └── scripts/
│       ├── pre-deploy.sh    # Hook scripts
│       └── backup.sh
```

### Command Execution

```bash
cd /project
sbkube deploy --app-dir redis_dir
```

Hook scripts run from the `redis_dir` directory, enabling natural relative path usage:

```yaml
# redis_dir/config.yaml
hooks:
  deploy:
    pre:
      - ./scripts/pre-deploy.sh  # ← Relative path from redis_dir
```

## Migration Guide

### Basic Shell → Phase 1 Manifests

**Before**: Manual kubectl commands

```yaml
hooks:
  post_deploy:
    - |
      kubectl apply -f manifests/cluster-issuer.yaml
      kubectl wait --for=condition=ready clusterissuer/letsencrypt-prod --timeout=60s
```

**After**: Automatic YAML deployment

```yaml
hooks:
  post_deploy_manifests:
    - path: manifests/cluster-issuer.yaml
```

### Phase 1 → Phase 2 Tasks

**Before**: Separate manifests and commands

```yaml
hooks:
  post_deploy_manifests:
    - path: manifests/realm-config.yaml

  post_deploy:
    - |
      kubectl wait --for=condition=ready pod -l app=keycloak --timeout=300s
      curl http://keycloak:8080/realms/myrealm
```

**After**: Structured task types

```yaml
hooks:
  post_deploy_tasks:
    - type: manifests
      name: deploy-realm-config
      paths:
        - manifests/realm-config.yaml

    - type: command
      name: wait-keycloak-ready
      command:
        - kubectl
        - wait
        - --for=condition=ready
        - pod
        - -l
        - app=keycloak
        - --timeout=300s

    - type: command
      name: verify-realm
      command: ["curl", "http://keycloak:8080/realms/myrealm"]
```

### Phase 2 → Phase 3 (Validation)

**Before**: No automatic validation

```yaml
post_deploy_tasks:
  - type: manifests
    name: create-issuer
    paths:
      - manifests/letsencrypt-prod.yaml
```

**After**: Validation and rollback

```yaml
post_deploy_tasks:
  - type: manifests
    name: create-issuer
    paths:
      - manifests/letsencrypt-prod.yaml

    validation:
      type: resource_ready
      resource: clusterissuer/letsencrypt-prod
      timeout: 120

    rollback:
      action: delete_resource
      resource: clusterissuer/letsencrypt-prod
```

### Phase 3 → Phase 4 (HookApp)

**Before**: App-coupled hooks

```yaml
apps:
  - name: cert-manager
    type: helm
    hooks:
      post_deploy_tasks:
        - type: manifests
          paths:
            - manifests/letsencrypt-staging.yaml
            - manifests/letsencrypt-prod.yaml
```

**After**: Independent HookApp

```yaml
apps:
  # 1. cert-manager (Helm app)
  - name: cert-manager
    type: helm
    specs:
      repo: jetstack
      chart: cert-manager

  # 2. ClusterIssuer setup (Independent HookApp)
  - name: setup-cluster-issuers
    type: hook  # Phase 4: Hook as First-class App
    enabled: true

    hooks:
      post_deploy_tasks:
        - type: manifests
          name: deploy-issuers
          paths:
            - manifests/letsencrypt-staging.yaml
            - manifests/letsencrypt-prod.yaml

        - type: command
          name: verify-issuers
          command:
            - kubectl
            - wait
            - --for=condition=ready
            - clusterissuer/letsencrypt-prod
            - --timeout=60s
          dependency:
            wait_for_tasks: ["deploy-issuers"]
```

## Best Practices

### 1. Database Backup and Migration

```yaml
apps:
  postgresql:
    type: helm
    chart: prometheus-community/kube-state-metrics
    version: 13.0.0
    hooks:
      pre_deploy:
        - echo "Creating database backup..."
        - kubectl exec postgresql-0 -n production -- pg_dump -U postgres mydb > /backups/db-$(date +%Y%m%d-%H%M%S).sql
        - echo "Backup completed"

      post_deploy:
        - echo "Waiting for database to be ready..."
        - kubectl wait --for=condition=ready pod -l app.kubernetes.io/name=postgresql -n production --timeout=300s
        - echo "Running database migrations..."
        - kubectl exec postgresql-0 -n production -- psql -U postgres -d mydb -f /migrations/latest.sql
        - echo "Migrations completed"

      on_deploy_failure:
        - echo "Database deployment failed, restoring backup..."
        - kubectl exec postgresql-0 -n production -- psql -U postgres -d mydb -f /backups/db-latest.sql
        - echo "Backup restored"
```

### 2. Service Health Checks and Notifications

```yaml
hooks:
  deploy:
    pre:
      - ./scripts/notify-slack.sh "🚀 Deployment started for $SBKUBE_NAMESPACE"

    post:
      - ./scripts/notify-slack.sh "✅ Deployment completed for $SBKUBE_NAMESPACE"
      - ./scripts/send-metrics.sh

    on_failure:
      - ./scripts/notify-slack.sh "❌ Deployment failed for $SBKUBE_NAMESPACE"
      - ./scripts/notify-pagerduty.sh "critical"

apps:
  backend:
    type: helm
    chart: ./charts/backend
    hooks:
      post_deploy:
        - echo "Running health check..."
        - sleep 10
        - curl -f http://backend.production.svc.cluster.local/health || exit 1
        - echo "Health check passed"
        - ./scripts/smoke-test.sh
```

### 3. Dependency Management

```yaml
apps:
  redis:
    type: helm
    chart: grafana/loki
    hooks:
      post_deploy:
        - kubectl wait --for=condition=ready pod -l app.kubernetes.io/name=redis --timeout=300s
        - echo "Redis is ready"

  backend:
    type: helm
    chart: ./charts/backend
    depends_on:
      - redis
    hooks:
      pre_deploy:
        - echo "Checking Redis connectivity..."
        - kubectl run redis-test --rm -i --restart=Never --image=redis:alpine -- redis-cli -h redis ping
        - echo "Redis is accessible"

      post_deploy:
        - echo "Running integration tests..."
        - ./scripts/integration-test.sh
```

### 4. GitOps and External System Integration

```yaml
hooks:
  deploy:
    pre:
      # Pause Argo CD sync
      - argocd app set myapp --sync-policy none

      # Create Git tag
      - git tag -a "deploy-$(date +%Y%m%d-%H%M%S)" -m "Deployment to staging"
      - git push origin --tags

    post:
      # Resume Argo CD sync
      - argocd app set myapp --sync-policy automated

      # Record deployment info
      - |
        curl -X POST https://deploy-tracker.example.com/api/deployments \
          -H "Content-Type: application/json" \
          -d "{\"environment\": \"staging\", \"timestamp\": \"$(date -u +%Y-%m-%dT%H:%M:%SZ)\"}"
```

## Troubleshooting

### Common Issues

1. **Hook scripts not found**

   - Verify the working directory matches `--app-dir`
   - Use relative paths from the app directory
   - Check script permissions (must be executable)

1. **Environment variables missing**

   - Verify using: `env | grep SBKUBE`
   - Check SBKube version supports the expected variables

1. **Hooks not executing**

   - Enable verbose mode: `sbkube deploy --verbose`
   - Check hook naming conventions (snake_case for app-level)
   - Verify YAML indentation

### Debugging Tips

```yaml
hooks:
  post_deploy:
    # Print environment for debugging
    - |
      echo "SBKUBE_APP_NAME: $SBKUBE_APP_NAME"
      echo "SBKUBE_NAMESPACE: $SBKUBE_NAMESPACE"
      env | grep SBKUBE

    # Check working directory
    - pwd

    # Verify resource existence
    - kubectl get namespace $SBKUBE_NAMESPACE || kubectl create namespace $SBKUBE_NAMESPACE
```

## Phase 4: HookApp (Hook as First-Class App)

> **Version**: v0.8.0+ **Status**: ✅ Stable

### Overview

Phase 4 allows hooks to be defined as independent apps (`type: hook`), making them reusable and independently
manageable.

### HookApp Features

| Feature | Description | Benefit | |---------|-------------|---------| | **First-class App** | `type: hook` for
independent apps | Managed like other apps | | **Simplified Lifecycle** | Skip `prepare`, `build`, `template` | Execute
only during `deploy` | | **Reusable** | Use across projects | Eliminate duplication | | **Enabled Flag** |
`enabled: false` to disable | Easy on/off | | **Dependency Support** | Inter-app dependencies | Control execution order
| | **Individual Deployment** | `sbkube deploy --app setup-issuers` | Independent management |

### When to Use HookApp

**Use HookApp when:**

- ✅ Reusing across multiple projects/environments
- ✅ Complex initialization logic (multiple tasks)
- ✅ Need to independently enable/disable
- ✅ Clear dependency relationships with other apps

**Use regular hooks when:**

- ✅ App-specific operations only
- ✅ Simple shell commands
- ✅ One-time use

### Example: cert-manager Initialization

```yaml
apps:
  - name: cert-manager
    type: helm
    specs:
      repo: jetstack
      chart: cert-manager

  - name: setup-issuers
    type: hook
    hooks:
      post_deploy_tasks:
        - type: manifests
          paths:
            - manifests/letsencrypt-staging.yaml
            - manifests/letsencrypt-prod.yaml
```

## Helm Hooks vs SBKube Hooks

SBKube hooks and Helm hooks are different concepts:

| Aspect | SBKube Hooks | Helm Hooks | |--------|--------------|------------| | **Definition** | SBKube command
execution points | Helm release lifecycle | | **Execution** | SBKube CLI | Helm/Kubernetes | | **Location** | Local
machine | Kubernetes cluster | | **Purpose** | Deployment automation, validation | In-cluster operations | |
**Examples** | Backup, notifications, external integration | DB migration, initialization |

Both can be used together:

```yaml
# config.yaml (SBKube hooks)
apps:
  backend:
    type: helm
    chart: ./charts/backend
    hooks:
      pre_deploy:
        - echo "SBKube: Backing up database (local)"
        - ./scripts/backup-db.sh

# charts/backend/templates/pre-install-hook.yaml (Helm hooks)
apiVersion: batch/v1
kind: Job
metadata:
  name: db-migration
  annotations:
    "helm.sh/hook": pre-install  # Helm hook
spec:
  template:
    spec:
      containers:
      - name: migrate
        image: backend:latest
        command: ["./migrate", "up"]
```

______________________________________________________________________

## Related Documentation

- ****상위 문서**: [ARCHITECTURE.md](../../ARCHITECTURE.md) - 아키텍처 (어떻게)
- **제품 개요**: [PRODUCT.md](../../PRODUCT.md) - 제품 정의 (무엇을, 왜)
- **상세 참조**: [Hooks Reference](./hooks-reference.md) - 훅 타입, 환경 변수 상세
- **앱 타입**: [Application Types](./application-types.md) - HookApp 타입 상세
- **예제**: [../../examples/hooks\*/](../../examples/) - 다양한 hooks 예제

### Examples Directory

- `examples/hooks/` - Basic hook usage
- `examples/hooks-basic-all/` - All hook types
- `examples/hooks-manifests/` - Phase 1: Manifests
- `examples/hooks-phase3/` - Phase 3: Validation/Dependency/Rollback
- `examples/hooks-phase4/` - Phase 4: HookApp (complex chains)
- `examples/hooks-pre-deploy-tasks/` - Pre-deployment validation
- `examples/hooks-command-level/` - Global notifications
- `examples/hooks-error-handling/` - Error handling and rollback
- `examples/hooks-hookapp-simple/` - HookApp introduction

______________________________________________________________________

**문서 버전**: 1.1 **마지막 업데이트**: 2025-01-06 **담당자**: archmagece@users.noreply.github.com
