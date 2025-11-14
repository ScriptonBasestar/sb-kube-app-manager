# Documentation as Code Example

This example demonstrates how to use the `notes` field to maintain operational documentation directly in your configuration files.

## What is Documentation as Code?

Instead of maintaining separate documentation that often becomes outdated, embed critical information directly in your `config.yaml` where it stays synchronized with your actual deployments.

## Features Demonstrated

### 1. Design Decision Recording

```yaml
victoria-metrics:
  notes: |
    Why chosen:
    - 20x faster than Prometheus

    Alternatives considered:
    - Prometheus: Too slow for our requirements
```

Record **why** you chose a specific solution and what alternatives were evaluated.

### 2. Deployment Order Documentation

```yaml
thanos:
  enabled: false
  notes: |
    ⚠️  DEPLOYMENT ORDER: Deploy AFTER Prometheus is stable
```

Document critical deployment sequences and dependencies.

### 3. Operational Information

```yaml
external-postgres:
  type: noop
  notes: |
    Contacts:
    - DBA team: dba@company.com
    - On-call: oncall-db@pagerduty.com

    DR procedure: docs/disaster-recovery/postgres-rds.md
```

Keep contact information, backup schedules, and DR procedures with your config.

### 4. Migration Planning

```yaml
thanos:
  notes: |
    Migration plan:
    1. Set up S3 bucket with lifecycle policies
    2. Enable Thanos sidecar in Prometheus
    3. Deploy Thanos Query + Store Gateway
```

Document future migration steps and estimated timelines.

## Usage

### View All Apps with Notes

```bash
sbkube status --app-dir examples/documentation-as-code --show-notes
```

### Validate Configuration

```bash
sbkube validate --app-dir examples/documentation-as-code
```

## Benefits

1. **No Documentation Drift**: Information stays with code
2. **Onboarding**: New team members understand "why" not just "what"
3. **Decision History**: Track design decisions over time
4. **Operational Context**: Critical info is always accessible
5. **Version Control**: Documentation changes tracked in git

## Best Practices

### ✅ Good Notes

- **Why**: Explain design decisions
- **What**: Document important constraints
- **When**: Note deployment order and timing
- **Who**: Include contact information

### ❌ Avoid

- Duplicating information from Helm chart docs
- Implementation details (those belong in chart values)
- Temporary notes (use comments for those)

## Real-World Use Cases

### Team Handoff

When you leave a project, your successor reads `config.yaml` and immediately understands:
- Why VictoriaMetrics was chosen over Prometheus
- Why TimescaleDB was rejected
- Who to contact for database issues

### Incident Response

During an outage, engineers can quickly find:
- DR procedures
- On-call contacts
- Configuration details
- Known limitations

### Compliance & Audit

Document compliance requirements directly in config:

```yaml
vault:
  notes: |
    Secrets management (SOC 2 requirement)
    Audit logs: /var/log/vault/audit.log
    Key rotation: Quarterly (automated)
    Compliance: PCI-DSS Level 1
```

## Related Examples

- [hooks](../hooks/) - Using hooks with apps
- [dependency-chain](../dependency-chain/) - App dependencies
- [app-group-management](../app-group-management/) - Managing app groups
