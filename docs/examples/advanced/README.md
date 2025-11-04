# Advanced Configuration Examples

This directory contains advanced SBKube configuration examples.

## Files

### helm-customization.yaml
Advanced Helm chart customization using overrides system.

**Features**:
- Custom file injection
- Template file removal
- Chart modification

**Use case**: Customizing third-party Helm charts without forking

### app-group-deps.yaml
App-group dependency management (v0.6.0+).

**Features**:
- Cross-directory dependencies
- Deployment order validation
- Multi-group orchestration

**Use case**: Large-scale multi-group deployments

## See Also

- [Common Examples](../common/) - Basic configurations
- [Project Examples](../../../examples/) - Full project examples
- [Chart Customization Guide](../../03-configuration/chart-customization.md)
