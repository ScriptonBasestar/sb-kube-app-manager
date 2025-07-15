# Configuration Validation and Inheritance System Migration Guide

## Overview

This guide describes how to migrate existing sbkube commands to use the new enhanced configuration validation and inheritance system.

## New Features

1. **Enhanced Validation**
   - Automatic validation on configuration load
   - Comprehensive field validation (Kubernetes naming, versions, URLs, etc.)
   - Clear error messages with field paths
   - Cross-field dependency validation

2. **Configuration Inheritance**
   - Support for parent configurations using `_parent` field
   - Deep merging of configurations
   - Environment-specific overlays

3. **Improved Error Handling**
   - Structured validation errors
   - Better error messages for users
   - Validation error accumulation

## Migration Steps

### 1. Update Import Statements

Replace old imports:
```python
# Old
from sbkube.utils.base_command import BaseCommand
from sbkube.models.config_model import AppInfoScheme, AppGroupScheme
from sbkube.models.sources_model import SourceScheme

# New
from sbkube.utils.base_command_v2 import EnhancedBaseCommand
from sbkube.models.config_model_v2 import AppInfoScheme, AppGroupScheme
from sbkube.models.sources_model_v2 import SourceScheme
```

### 2. Update Command Base Class

Change your command class to inherit from `EnhancedBaseCommand`:

```python
# Old
class PrepareCommand(BaseCommand):
    def __init__(self, base_dir, app_config_dir, sources_file="sources.yaml"):
        super().__init__(base_dir, app_config_dir)
        self.sources_file = sources_file

# New
class PrepareCommand(EnhancedBaseCommand):
    def __init__(self, base_dir, app_config_dir, sources_file="sources.yaml"):
        super().__init__(
            base_dir=base_dir,
            app_config_dir=app_config_dir,
            sources_file=sources_file,
            validate_on_load=True,  # Enable automatic validation
            use_inheritance=True    # Enable configuration inheritance
        )
```

### 3. Update Configuration Loading

The new base class handles configuration loading with validation automatically:

```python
# Old
def execute_pre_hook(self):
    super().execute_pre_hook()
    # Manual sources loading
    sources_path = self.base_dir / self.sources_file
    if sources_path.exists():
        sources_data = load_config_file(sources_path)
        self.sources = SourceScheme(**sources_data)

# New
def needs_sources(self):
    """Override to indicate this command needs sources."""
    return True

def execute_pre_hook(self):
    super().execute_pre_hook()
    # Sources are automatically loaded if needs_sources() returns True
    # self.sources is already populated and validated
```

### 4. Update Spec Creation

Use the new validated spec creation:

```python
# Old
if app_info.type == 'pull-helm':
    spec = AppPullHelmSpec(**app_info.specs)

# New
spec = self.create_app_spec(app_info)
# or directly:
spec = app_info.get_validated_specs()
```

### 5. Handle Validation Errors

The new system provides better error handling:

```python
# Old
try:
    # Process app
except Exception as e:
    logger.error(f"Error: {e}")

# New
try:
    # Process app
except ConfigValidationError as e:
    logger.error(f"Validation error: {e}")
    # Validation errors are automatically formatted
```

### 6. Use Enhanced Models

The new models provide additional validation methods:

```python
# Example: Working with validated specs
app_info = AppInfoScheme(
    name="my-app",
    type="install-helm",
    specs={
        "path": "charts/my-app",
        "release_name": "my-release",
        "timeout": "5m30s"  # Automatically validated
    }
)

# Get validated spec instance
helm_spec = app_info.get_validated_specs()
# helm_spec is now a fully validated AppInstallHelmSpec instance
```

## Configuration File Changes

### 1. Using Inheritance

Create a base configuration:
```yaml
# base.yaml
namespace: default
global_labels:
  team: platform
  environment: base
apps:
  - name: common-app
    type: install-helm
    specs:
      path: charts/common
```

Create an environment-specific configuration:
```yaml
# production.yaml
_parent: base.yaml  # Inherit from base
namespace: production
global_labels:
  environment: prod  # Override specific label
apps:
  - name: prod-app
    type: install-kubectl
    specs:
      paths: ["prod-manifests.yaml"]
```

### 2. Enhanced Validation

The new system validates many more fields:
```yaml
apps:
  - name: my-app  # Validated against Kubernetes naming conventions
    type: install-helm
    namespace: my-namespace  # Validated namespace format
    specs:
      release_name: my-release  # Validated release name
      timeout: 5m30s  # Validated timeout format
      chart_version: 1.2.3  # Validated version format
```

### 3. Sources Configuration Enhancement

```yaml
# Enhanced sources.yaml
cluster: production
kubeconfig: ~/.kube/config  # Path existence is validated

helm_repos:
  bitnami:
    url: https://charts.bitnami.com/bitnami
    username: optional-username
    password: optional-password

git_repos:
  my-repo:
    url: https://github.com/example/repo.git
    branch: main
    ssh_key: /path/to/key  # Or use username/password
```

## Testing

Add tests for your migrated commands:

```python
import pytest
from sbkube.models.config_model_v2 import AppInfoScheme
from sbkube.exceptions import ConfigValidationError

def test_app_validation():
    # Valid app
    app = AppInfoScheme(
        name="valid-app",
        type="install-helm",
        specs={"path": "charts/app"}
    )
    assert app.name == "valid-app"
    
    # Invalid name
    with pytest.raises(ConfigValidationError):
        AppInfoScheme(
            name="Invalid-App",  # Capital letters not allowed
            type="install-helm",
            specs={}
        )
```

## Benefits After Migration

1. **Automatic Validation**: No need to manually validate configurations
2. **Better Error Messages**: Users get clear feedback on configuration errors
3. **Configuration Reuse**: Use inheritance to reduce duplication
4. **Type Safety**: Validated specs provide type-safe access to fields
5. **Future Proof**: Easy to add new validation rules without changing command code

## Gradual Migration

You can migrate gradually by:
1. Using the new models alongside old ones initially
2. Enabling validation only in development/test environments first
3. Migrating one command at a time
4. Running both old and new versions in parallel during transition

## Support

For questions or issues during migration:
1. Check the test files for examples
2. Review the enhanced model documentation
3. Use `validate_on_load=False` initially if needed to debug issues