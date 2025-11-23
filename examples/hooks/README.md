# SBKube Hooks Examples - Navigation Guide

This directory contains a comprehensive collection of hooks examples demonstrating SBKube's hook system evolution and capabilities.

## 📚 Hooks Examples Overview

SBKube's hooks system has evolved through multiple phases, each adding more sophisticated capabilities. This guide helps you navigate the examples and understand the progression.

### Quick Navigation

| Example Directory | Phase | Complexity | Description |
|-------------------|-------|------------|-------------|
| **[hooks/](#basic-hooks)** | Phase 1 | ⭐ Basic | Simple shell command hooks |
| **[hooks-manifests/](#manifest-hooks)** | Phase 1 | ⭐ Basic | YAML manifest deployment hooks |
| **[hooks-pre-deploy-tasks/](#pre-deploy-tasks)** | Phase 2 | ⭐⭐ Medium | Pre-deployment task system |
| **[hooks-phase3/](#phase-3-structured-tasks)** | Phase 3 | ⭐⭐⭐ Advanced | Structured task types (manifests, inline, command) |
| **[hooks-phase4/](#phase-4-hookapp)** | Phase 4 | ⭐⭐⭐⭐ Expert | HookApp - First-class app type |
| **[hooks-basic-all/](#comprehensive-demo)** | All | ⭐⭐⭐ Advanced | All hook types in one example |

---

## 🎯 Learning Path

### Beginner → Advanced

**1. Start Here** → [hooks/](#basic-hooks)
- Learn basic shell command hooks
- Understand command-level vs app-level hooks
- Simple, easy-to-understand examples

**2. Next** → [hooks-manifests/](#manifest-hooks)
- Deploy YAML manifests as hooks
- Understand pre_deploy_manifests

**3. Then** → [hooks-pre-deploy-tasks/](#pre-deploy-tasks)
- Structured task system
- Multiple task types
- Task dependencies

**4. Advanced** → [hooks-phase3/](#phase-3-structured-tasks)
- Inline YAML tasks
- Task validation
- Retry mechanisms

**5. Expert** → [hooks-phase4/](#phase-4-hookapp)
- HookApp as independent app type
- Task rollback policies
- Complex workflows (cert-manager example)

**6. Reference** → [hooks-basic-all/](#comprehensive-demo)
- See all hook types side-by-side
- Understand hook execution order
- Best practices demonstration

---

## 📖 Detailed Example Descriptions

### Basic Hooks

**Directory**: `examples/hooks/`
**Phase**: 1
**Level**: Beginner

**What You'll Learn:**
- Command-level hooks (`pre`, `post`, `on_failure`)
- App-level hooks (`pre_deploy`, `post_deploy`)
- Environment variables (`$SBKUBE_APP_NAME`, `$SBKUBE_NAMESPACE`)
- Basic error handling

**Use Cases:**
- Logging deployment start/end
- Simple health checks
- Notification scripts

**Key Example:**
```yaml
hooks:
  deploy:
    pre:
      - echo "=== Deployment started at $(date) ==="
    post:
      - echo "=== Deployment completed ==="

apps:
  redis:
    hooks:
      pre_deploy:
        - echo "Deploying Redis..."
      post_deploy:
        - kubectl wait --for=condition=ready pod -l app=redis
```

---

### Manifest Hooks

**Directory**: `examples/hooks-manifests/`
**Phase**: 1
**Level**: Beginner

**What You'll Learn:**
- Deploying YAML manifests as hooks
- `pre_deploy_manifests` and `post_deploy_manifests`
- Relationship between hooks and Kubernetes resources

**Use Cases:**
- Creating ConfigMaps before app deployment
- Setting up Secrets
- Deploying prerequisites

**Key Example:**
```yaml
apps:
  redis:
    hooks:
      pre_deploy_manifests:
        - manifests/configmap.yaml
```

---

### Pre-Deploy Tasks

**Directory**: `examples/hooks-pre-deploy-tasks/`
**Phase**: 2
**Level**: Medium

**What You'll Learn:**
- Task-based hook system
- Task types: `manifests`, `command`
- Task naming for better tracking
- Sequential task execution

**Use Cases:**
- Complex pre-deployment setup
- Multi-step verification
- Environment preparation

**Key Example:**
```yaml
apps:
  postgres:
    hooks:
      pre_deploy_tasks:
        - type: command
          name: ensure-namespace
          command: |
            kubectl get namespace $SBKUBE_NAMESPACE || \
            kubectl create namespace $SBKUBE_NAMESPACE

        - type: manifests
          name: create-secret
          files:
            - manifests/secret.yaml
```

---

### Phase 3: Structured Tasks

**Directory**: `examples/hooks-phase3/`
**Phase**: 3
**Level**: Advanced

**What You'll Learn:**
- Three task types: `manifests`, `inline`, `command`
- Inline YAML content (no separate file needed)
- Task validation and retry
- Advanced error handling

**Use Cases:**
- Dynamic resource creation
- Inline secret/configmap deployment
- Complex validation workflows

**Key Example:**
```yaml
hooks:
  post_deploy_tasks:
    - type: inline
      name: create-certificate
      content:
        apiVersion: cert-manager.io/v1
        kind: Certificate
        metadata:
          name: wildcard-cert
        spec:
          secretName: wildcard-cert-tls
      validation:
        kind: Certificate
        name: wildcard-cert
```

---

### Phase 4: HookApp

**Directory**: `examples/hooks-phase4/`
**Phase**: 4 (Latest)
**Level**: Expert

**What You'll Learn:**
- **HookApp as independent app type** (`type: hook`)
- App-level lifecycle management
- Rollback policies
- Complex dependency chains
- Real-world scenario (cert-manager setup)

**Use Cases:**
- Infrastructure setup (cert-manager, operators)
- Database initialization
- Multi-step deployment workflows
- Post-deployment configuration

**Key Example:**
```yaml
apps:
  setup-cert-manager:
    type: hook  # HookApp!
    depends_on:
      - cert-manager

    tasks:
      - type: manifests
        name: deploy-issuers
        files:
          - manifests/issuers/cluster-issuer-letsencrypt-prd.yaml
        validation:
          kind: ClusterIssuer
          wait_for_ready: true
        rollback:
          enabled: true
          manifests:
            - manifests/cleanup-issuers.yaml
```

**Advanced Features:**
- No prepare/build/template phases (deploy-only)
- Task-level validation and rollback
- App-level rollback fallback
- depends_on for app ordering

---

### Comprehensive Demo

**Directory**: `examples/hooks-basic-all/`
**Phase**: All Phases
**Level**: Advanced (Reference)

**What You'll Learn:**
- All hook types in one config
- Hook execution order
- Phase 1 (shell), Phase 1 (manifests), Phase 2 (tasks) side-by-side
- Best practices for organizing hooks

**Use Cases:**
- Understanding hook system progression
- Reference implementation
- Testing hook behavior

**Key Example:**
Shows progression from simple to complex:
1. Shell commands (Phase 1)
2. Manifest deployment (Phase 1)
3. Structured tasks (Phase 2)

All in one config for easy comparison.

---

## 🔧 Hooks System Evolution

### Phase 1: Shell Commands & Manifests

**Features:**
- Simple shell command execution
- YAML manifest deployment
- Command-level and app-level hooks

**Limitations:**
- No structured task system
- Limited error handling
- No validation/retry

**Examples:** `hooks/`, `hooks-manifests/`

### Phase 2: Structured Tasks

**Features:**
- Task naming for tracking
- Two task types: `manifests`, `command`
- Sequential execution
- Better organization

**Limitations:**
- No inline YAML
- Limited validation
- No rollback

**Examples:** `hooks-pre-deploy-tasks/`

### Phase 3: Enhanced Tasks

**Features:**
- Third task type: `inline`
- Inline YAML content
- Task validation
- Retry mechanisms

**Limitations:**
- Still part of app lifecycle
- No independent task apps

**Examples:** `hooks-phase3/`

### Phase 4: HookApp (v0.8.0+)

**Features:**
- **Independent app type** (`type: hook`)
- Skip prepare/build/template phases
- Task-level rollback
- App-level lifecycle
- Full validation support

**Current State:** Latest implementation

**Examples:** `hooks-phase4/`, `app-types/09-hook/`

---

## 🚀 Quick Start by Use Case

### "I want to run a script before deployment"
→ Start with **[hooks/](#basic-hooks)**
```yaml
apps:
  my-app:
    hooks:
      pre_deploy:
        - ./scripts/pre-deploy.sh
```

### "I need to create ConfigMaps before my app"
→ Try **[hooks-manifests/](#manifest-hooks)**
```yaml
apps:
  my-app:
    hooks:
      pre_deploy_manifests:
        - manifests/configmap.yaml
```

### "I have complex multi-step setup"
→ Use **[hooks-phase3/](#phase-3-structured-tasks)**
```yaml
hooks:
  post_deploy_tasks:
    - type: manifests
      name: step1
      files: [...]
    - type: inline
      name: step2
      content: {...}
    - type: command
      name: step3
      command: |
        ...
```

### "I need cert-manager or operator setup"
→ Use **[HookApp (Phase 4)](#phase-4-hookapp)**
```yaml
apps:
  setup-infrastructure:
    type: hook
    tasks:
      - type: manifests
        name: deploy-crd
        files: [...]
        validation:
          kind: CustomResourceDefinition
```

---

## 📊 Feature Comparison

| Feature | Phase 1 | Phase 2 | Phase 3 | Phase 4 (HookApp) |
|---------|---------|---------|---------|-------------------|
| **Shell Commands** | ✅ | ✅ | ✅ | ✅ |
| **Manifest Files** | ✅ | ✅ | ✅ | ✅ |
| **Inline YAML** | ❌ | ❌ | ✅ | ✅ |
| **Task Naming** | ❌ | ✅ | ✅ | ✅ |
| **Validation** | ❌ | ❌ | ✅ | ✅ |
| **Retry** | ❌ | ❌ | ✅ | ✅ |
| **Rollback** | ❌ | ❌ | ❌ | ✅ |
| **Independent App** | ❌ | ❌ | ❌ | ✅ |
| **depends_on** | ❌ | ❌ | ❌ | ✅ |

---

## 🔗 Related Documentation

- [Hooks Guide](../../docs/02-features/hooks-guide.md) - Complete hooks documentation
- [HookApp Type](../../docs/02-features/application-types.md#hook) - HookApp specification
- [Application Types](../../docs/02-features/application-types.md) - All app types
- [Commands Reference](../../docs/02-features/commands.md) - SBKube commands

---

## 💡 Best Practices

### 1. Choose the Right Phase

- **Simple scripts** → Phase 1 (hooks/)
- **Manifest deployment** → Phase 1 (hooks-manifests/)
- **Multi-step setup** → Phase 3 (hooks-phase3/)
- **Infrastructure setup** → Phase 4 (HookApp)

### 2. Error Handling

- Always check exit codes in shell commands
- Use validation for critical resources
- Implement rollback for destructive operations

### 3. Task Organization

- Name tasks descriptively
- Keep tasks focused (single responsibility)
- Use dependencies (`depends_on`) for ordering

### 4. Performance

- Avoid long-running tasks in hooks
- Use background jobs for async operations
- Set appropriate timeouts

### 5. Security

- Don't hardcode secrets in hook commands
- Use Kubernetes Secrets/ConfigMaps
- Validate external inputs

---

## ⚠️ Important Notes

1. **HookApp (Phase 4)** is only available in **SBKube v0.8.0+**
2. **Older phases** are still supported for backward compatibility
3. **Migration path**: Phase 1 → Phase 3 → Phase 4 (HookApp)
4. **Namespace inheritance**: HookApp uses global namespace (cannot override)
5. **Execution order**: Hooks run sequentially in definition order

---

## 📝 Summary

| If you need... | Use this example | Phase |
|----------------|------------------|-------|
| Simple scripts | `hooks/` | 1 |
| Manifest deployment | `hooks-manifests/` | 1 |
| Structured tasks | `hooks-phase3/` | 3 |
| Infrastructure setup | `hooks-phase4/` | 4 |
| Independent hook app | `app-types/09-hook/` | 4 |
| Reference/All features | `hooks-basic-all/` | All |

**Recommendation**: Start with **Phase 1** for learning, move to **Phase 4 (HookApp)** for production infrastructure setup.
