# Basic Configuration Examples

This directory contains minimal configuration examples for quick reference and learning.

## Files

### minimal-config.yaml
The simplest possible SBKube configuration. Use this as a starting point for new projects.

**Use case**: Learning SBKube basics, quick prototypes

### multi-app.yaml
Multi-application deployment with dependencies (database + backend).

**Use case**: Production deployments, understanding app dependencies

## Usage

These are simplified config snippets for documentation reference. For complete, runnable examples, see:

```bash
# Complete workflow example
cd examples/complete-workflow
sbkube apply --app-dir .

# Advanced features
cd examples/advanced-features/03-helm-customization
sbkube apply --app-dir .

# App group management
cd examples/app-group-management
sbkube apply --app-dir .
```

## See Also

- [Complete Workflow](../complete-workflow/) - Full runnable example
- [Advanced Features](../advanced-features/) - Feature-specific examples
- [App Group Management](../app-group-management/) - Multi-group orchestration
