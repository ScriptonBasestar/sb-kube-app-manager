# SBKube Use Cases - Real-World Deployment Scenarios

**Production-ready examples for common Kubernetes deployment patterns**

## 📋 Overview

This directory contains 11 comprehensive use cases demonstrating real-world deployment scenarios using SBKube. Each use case is production-ready and includes complete configuration, documentation, and best practices.

## 🎯 Use Cases Quick Reference

| # | Use Case | Complexity | Apps | Description |
|---|----------|------------|------|-------------|
| **01** | [Dev Environment](01-dev-environment/) | ⭐⭐ Medium | 4 | Complete development environment (Redis, PostgreSQL, Mailhog, LocalStack) |
| **02** | [Wiki Stack](02-wiki-stack/) | ⭐⭐ Medium | 3 | MediaWiki with MySQL and Traefik ingress |
| **03** | [Monitoring Stack](03-monitoring-stack/) | ⭐⭐⭐ Advanced | 2 | Prometheus + Grafana monitoring system |
| **04** | [CI/CD Stack](04-cicd-stack/) | ⭐⭐⭐ Advanced | 3 | GitLab Runner + Docker Registry |
| **05** | [Logging Stack](05-logging-stack/) | ⭐⭐⭐ Advanced | 3 | Loki + Promtail + Grafana logging system |
| **06** | [Ingress Controller](06-ingress-controller/) | ⭐⭐ Medium | 4 | Traefik IngressController with demo apps |
| **07** | [Cert Manager](07-cert-manager/) | ⭐⭐⭐ Advanced | 3 | SSL/TLS certificate automation |
| **08** | [Service Mesh](08-service-mesh/) | ⭐⭐⭐⭐ Expert | 5 | Linkerd service mesh with microservices |
| **09** | [Backup/Restore](09-backup-restore/) | ⭐⭐⭐ Advanced | 4 | Velero backup and restore system |
| **10** | [Database Cluster](10-database-cluster/) | ⭐⭐⭐ Advanced | 2 | PostgreSQL HA cluster with CloudNative-PG |
| **11** | [Message Queue](11-message-queue/) | ⭐⭐⭐ Advanced | 3 | RabbitMQ cluster with producer/consumer |

## 🚀 Getting Started

### Prerequisites

- k3s cluster (or any Kubernetes cluster)
- kubectl configured
- helm 3+
- SBKube v0.5.0+ installed

### Quick Start

```bash
# 1. Choose a use case
cd examples/use-cases/01-dev-environment/

# 2. Review configuration
cat config.yaml

# 3. Validate
sbkube validate config.yaml

# 4. Deploy
sbkube apply --app-dir .

# 5. Check status
sbkube status --app-dir .
```

## 📚 Use Cases by Category

### Development & Testing

**[01-dev-environment/](01-dev-environment/)** - Complete Development Environment
- Redis (session store & cache)
- PostgreSQL (main database)
- Mailhog (email testing server)
- LocalStack (AWS services emulator with S3)

**Best For:** Local development, testing, CI/CD environments

---

**[02-wiki-stack/](02-wiki-stack/)** - Wiki System with Ingress
- MySQL database backend
- MediaWiki application
- Traefik ingress configuration

**Best For:** Internal documentation, knowledge management

---

### Observability

**[03-monitoring-stack/](03-monitoring-stack/)** - Prometheus + Grafana Monitoring
- Prometheus (metrics collection & storage)
- Grafana (visualization dashboards)

**Best For:** Application monitoring, metrics visualization, alerting

---

**[05-logging-stack/](05-logging-stack/)** - Centralized Logging
- Loki (log aggregation)
- Promtail (log collection)
- Grafana (log visualization)

**Best For:** Centralized logging, log analysis, debugging

---

### CI/CD & DevOps

**[04-cicd-stack/](04-cicd-stack/)** - GitLab CI/CD Infrastructure
- PersistentVolume setup for registry storage
- Docker Registry (local storage)
- GitLab Runner

**Best For:** Self-hosted CI/CD, container image management

---

**[09-backup-restore/](09-backup-restore/)** - Backup & Disaster Recovery
- NFS backup storage
- Velero (backup/restore tool)
- Demo application (backup target)
- Automated backup schedule

**Best For:** Disaster recovery, data protection, cluster migration

---

### Networking & Security

**[06-ingress-controller/](06-ingress-controller/)** - Traefik Ingress
- k3s built-in Traefik (noop representation)
- Demo applications
- Traefik middlewares
- IngressRoute configurations

**Best For:** HTTP routing, SSL termination, traffic management

---

**[07-cert-manager/](07-cert-manager/)** - SSL/TLS Certificate Management
- cert-manager installation
- ClusterIssuer configuration
- Demo app with HTTPS ingress

**Best For:** Automated certificate management, Let's Encrypt integration

---

**[08-service-mesh/](08-service-mesh/)** - Linkerd Service Mesh
- Linkerd CRDs
- Linkerd Control Plane
- Linkerd Viz (metrics & dashboard)
- Namespace configuration (sidecar auto-injection)
- Demo microservices (frontend, backend, database)

**Best For:** Microservices communication, mTLS, traffic management, observability

---

### Databases & Stateful Applications

**[10-database-cluster/](10-database-cluster/)** - PostgreSQL High Availability
- PostgreSQL HA cluster (CloudNative-PG)
- Demo client application for testing

**Best For:** Production databases, high availability, data persistence

---

**[11-message-queue/](11-message-queue/)** - RabbitMQ Messaging
- RabbitMQ cluster (cluster operator)
- Producer application
- Consumer application

**Best For:** Asynchronous communication, event-driven architecture, messaging patterns

---

## 🎓 Learning Path

### Beginner (⭐-⭐⭐)

1. **Start with [01-dev-environment/](01-dev-environment/)**
   - Learn basic multi-app deployment
   - Understand YAML type apps
   - Practice with Helm charts

2. **Then [02-wiki-stack/](02-wiki-stack/)**
   - Learn app dependencies (`depends_on`)
   - Understand ingress configuration

3. **Try [06-ingress-controller/](06-ingress-controller/)**
   - Learn Traefik IngressRoute
   - Understand middlewares

### Intermediate (⭐⭐⭐)

4. **Move to [03-monitoring-stack/](03-monitoring-stack/)**
   - Set up Prometheus + Grafana
   - Learn metrics collection

5. **Then [05-logging-stack/](05-logging-stack/)**
   - Implement centralized logging
   - Understand log aggregation

6. **Try [07-cert-manager/](07-cert-manager/)**
   - Automate SSL/TLS certificates
   - Learn cert-manager patterns

### Advanced (⭐⭐⭐⭐)

7. **Deploy [10-database-cluster/](10-database-cluster/)**
   - Implement HA databases
   - Understand stateful apps

8. **Then [09-backup-restore/](09-backup-restore/)**
   - Implement backup strategies
   - Learn disaster recovery

9. **Finally [08-service-mesh/](08-service-mesh/)**
   - Deploy Linkerd service mesh
   - Understand microservices patterns

## 💡 Common Patterns

### Pattern 1: Multi-Tier Application

**Example:** [02-wiki-stack/](02-wiki-stack/)

```yaml
apps:
  database:
    type: yaml
    # Database layer

  application:
    type: yaml
    depends_on:
      - database    # Wait for database

  ingress:
    type: yaml
    depends_on:
      - application # Wait for application
```

### Pattern 2: Infrastructure + Application

**Example:** [07-cert-manager/](07-cert-manager/)

```yaml
apps:
  infrastructure:
    type: helm
    # Install infrastructure (cert-manager)

  configuration:
    type: yaml
    depends_on:
      - infrastructure # Configure after installation

  application:
    type: yaml
    depends_on:
      - configuration  # Deploy app after config
```

### Pattern 3: Namespace-Scoped Deployment

**Example:** [08-service-mesh/](08-service-mesh/)

```yaml
apps:
  control-plane:
    type: helm
    namespace: linkerd       # Control plane namespace

  application:
    type: yaml
    namespace: app-namespace # Application namespace
    depends_on:
      - control-plane
```

## 🔧 Configuration Best Practices

### 1. Use App Dependencies

```yaml
apps:
  database:
    type: helm
    chart: postgresql

  backend:
    type: yaml
    depends_on:
      - database    # ✅ Wait for database
```

### 2. Enable Apps Selectively

```yaml
apps:
  required-app:
    type: helm
    enabled: true   # ✅ Always deploy

  optional-app:
    type: helm
    enabled: false  # ⚠️ Skip deployment
```

### 3. Organize Values Files

```
use-case/
├── config.yaml
├── sources.yaml
└── values/
    ├── app1-values.yaml
    ├── app2-values.yaml
    └── app3-values.yaml
```

### 4. Use Modern Format (v0.5.0+)

```yaml
# ✅ Modern format
apps:
  redis:
    type: helm
    chart: bitnami/redis

# ❌ Deprecated format (pre-v0.5.0)
apps:
  - name: redis
    specs:
      repo: bitnami
      chart: redis
```

## 📊 Use Case Selection Guide

### "I need a development environment"
→ [01-dev-environment/](01-dev-environment/)

### "I want to monitor my applications"
→ [03-monitoring-stack/](03-monitoring-stack/)

### "I need centralized logging"
→ [05-logging-stack/](05-logging-stack/)

### "I want to automate SSL certificates"
→ [07-cert-manager/](07-cert-manager/)

### "I need CI/CD infrastructure"
→ [04-cicd-stack/](04-cicd-stack/)

### "I want to implement backup/restore"
→ [09-backup-restore/](09-backup-restore/)

### "I need a high-availability database"
→ [10-database-cluster/](10-database-cluster/)

### "I want to implement a service mesh"
→ [08-service-mesh/](08-service-mesh/)

### "I need message queue infrastructure"
→ [11-message-queue/](11-message-queue/)

## 🐛 Troubleshooting

### Issue: Validation Fails

```bash
# Check configuration syntax
sbkube validate use-case/config.yaml

# Common issues:
# - YAML type apps must use 'manifests:' not 'files:'
# - Helm type apps must use 'chart: repo/chart' format
# - App names must use hyphens, not underscores
```

### Issue: Deployment Fails

```bash
# Check detailed logs
sbkube apply --app-dir use-case/ --dry-run

# Verify dependencies
sbkube status --app-dir use-case/

# Check Kubernetes events
kubectl get events -n <namespace> --sort-by='.lastTimestamp'
```

### Issue: App Dependencies Not Working

```yaml
# ✅ Correct: depends_on field
apps:
  app1:
    type: helm
  app2:
    type: yaml
    depends_on:
      - app1

# ❌ Wrong: deps field (deprecated)
apps:
  app2:
    deps:
      - app1
```

## 📝 Validation

All use cases have been validated with SBKube v0.5.0+:

```bash
# Validate all use cases
for dir in examples/use-cases/*/; do
  sbkube validate "${dir}config.yaml"
done
```

**Result:** ✅ 11/11 use cases validated successfully

## 🔗 Related Resources

- [App Types Documentation](../../docs/02-features/application-types.md) - All supported app types
- [Configuration Schema](../../docs/03-configuration/config-schema.md) - Complete config reference
- [Commands Reference](../../docs/02-features/commands.md) - All SBKube commands
- [Hooks Guide](../hooks/README.md) - Hook system documentation
- [Best Practices](../../docs/05-best-practices/directory-structure.md) - Project structure guidelines

## 📦 Quick Deploy Commands

```bash
# Deploy specific use case
sbkube apply --app-dir examples/use-cases/01-dev-environment/

# Dry run first
sbkube apply --app-dir examples/use-cases/03-monitoring-stack/ --dry-run

# Check status
sbkube status --app-dir examples/use-cases/05-logging-stack/

# Delete deployment
sbkube delete --app-dir examples/use-cases/07-cert-manager/
```

## ⚠️ Important Notes

1. **Modern Format Required:** All use cases use SBKube v0.5.0+ modern format
2. **YAML Type Apps:** Must use `manifests:` field, not `files:`
3. **Helm Type Apps:** Must use `chart: repo/chart` format, not separate `repo:` + `chart:`
4. **App Dependencies:** Use `depends_on:` field, not `deps:`
5. **App Naming:** Use hyphens in app names, not underscores
6. **Namespace:** Each use case defines its own namespace

## 🎯 Summary

| Category | Use Cases | Complexity | Best For |
|----------|-----------|------------|----------|
| **Development** | 01, 02 | ⭐⭐ | Local dev, testing |
| **Observability** | 03, 05 | ⭐⭐⭐ | Monitoring, logging |
| **CI/CD** | 04, 09 | ⭐⭐⭐ | Automation, backup |
| **Networking** | 06, 07 | ⭐⭐-⭐⭐⭐ | Ingress, SSL/TLS |
| **Advanced** | 08, 10, 11 | ⭐⭐⭐⭐ | Service mesh, databases, messaging |

**Total:** 11 production-ready use cases covering common Kubernetes deployment patterns.
