"""
Custom validators for configuration schema validation.

This module provides reusable validators for Pydantic models
to ensure configuration data integrity and consistency.
"""

import re
from pathlib import Path
from typing import Any

# Kubernetes naming convention regex
KUBE_NAME_PATTERN = re.compile(r"^[a-z0-9]([-a-z0-9]*[a-z0-9])?$")
KUBE_NAMESPACE_PATTERN = re.compile(r"^[a-z0-9]([-a-z0-9]*[a-z0-9])?$")

# Version patterns
SEMVER_PATTERN = re.compile(r"^v?\d+\.\d+\.\d+(-[\w\d\.\-]+)?(\+[\w\d\.\-]+)?$")
HELM_VERSION_PATTERN = re.compile(r"^\d+\.\d+\.\d+(-[\w\d\.\-]+)?$")


class ValidatorMixin:
    """Mixin class providing common validation methods."""

    @classmethod
    def validate_kubernetes_name(cls, v: str, field_name: str = "name") -> str:
        """Validate Kubernetes resource naming convention."""
        if not v:
            raise ValueError(f"{field_name} cannot be empty")
        if len(v) > 253:
            raise ValueError(f"{field_name} must be less than 253 characters")
        if not KUBE_NAME_PATTERN.match(v):
            raise ValueError(
                f"{field_name} '{v}' must consist of lowercase alphanumeric "
                "characters or '-', and must start and end with an alphanumeric character",
            )
        return v

    @classmethod
    def validate_namespace(cls, v: str | None) -> str | None:
        """Validate Kubernetes namespace naming convention."""
        if v is None:
            return v
        if len(v) > 63:
            raise ValueError("namespace must be less than 63 characters")
        if not KUBE_NAMESPACE_PATTERN.match(v):
            raise ValueError(
                f"namespace '{v}' must consist of lowercase alphanumeric "
                "characters or '-', and must start and end with an alphanumeric character",
            )
        return v

    @classmethod
    def validate_path_exists(cls, v: str, must_exist: bool = False) -> str:
        """Validate file/directory path."""
        if not v:
            raise ValueError("path cannot be empty")

        path = Path(v)
        if must_exist and not path.exists():
            raise ValueError(f"path '{v}' does not exist")

        # Check for path traversal attempts
        try:
            path.resolve()
        except (RuntimeError, ValueError):
            raise ValueError(
                f"invalid path '{v}' - contains invalid characters or traversal attempts",
            )

        return v

    @classmethod
    def validate_url(cls, v: str, allowed_schemes: list[str] = None) -> str:
        """Validate URL format and scheme."""
        if not v:
            raise ValueError("URL cannot be empty")

        if allowed_schemes:
            if not any(v.startswith(f"{scheme}://") for scheme in allowed_schemes):
                raise ValueError(
                    f"URL must start with one of: {', '.join(f'{s}://' for s in allowed_schemes)}",
                )

        return v

    @classmethod
    def validate_helm_version(cls, v: str | None) -> str | None:
        """Validate Helm chart version format."""
        if v is None:
            return v

        if not HELM_VERSION_PATTERN.match(v):
            raise ValueError(
                f"Invalid Helm version format '{v}'. "
                "Expected format: MAJOR.MINOR.PATCH[-PRERELEASE]",
            )
        return v

    @classmethod
    def validate_semver(cls, v: str | None) -> str | None:
        """Validate semantic version format."""
        if v is None:
            return v

        if not SEMVER_PATTERN.match(v):
            raise ValueError(
                f"Invalid semantic version format '{v}'. "
                "Expected format: [v]MAJOR.MINOR.PATCH[-PRERELEASE][+BUILD]",
            )
        return v

    @classmethod
    def validate_non_empty_list(
        cls,
        v: list[Any],
        field_name: str = "list",
    ) -> list[Any]:
        """Validate that a list is not empty."""
        if not v:
            raise ValueError(f"{field_name} cannot be empty")
        return v

    @classmethod
    def validate_unique_list(cls, v: list[Any], field_name: str = "list") -> list[Any]:
        """Validate that all items in a list are unique."""
        if len(v) != len(set(v)):
            raise ValueError(f"{field_name} must contain unique values")
        return v


def validate_spec_fields(app_type: str, specs: dict[str, Any]) -> dict[str, Any]:
    """
    Validate that required fields are present in specs based on app type.

    This function checks for required fields specific to each application type.
    """
    required_fields = {
        "helm": ["repo", "chart"],  # Unified Helm type (pull + install)
        "yaml": ["actions"],  # YAML manifests deployment
        "action": ["actions"],  # Custom actions
        "http": ["url"],  # HTTP download
        "exec": ["commands"],  # Command execution
    }

    if app_type not in required_fields:
        raise ValueError(f"Unknown app type: {app_type}")

    missing_fields = []
    for field in required_fields.get(app_type, []):
        if field not in specs or specs[field] is None:
            missing_fields.append(field)

    if missing_fields:
        raise ValueError(
            f"Missing required fields for app type '{app_type}': {', '.join(missing_fields)}",
        )

    return specs


def validate_cross_field_dependencies(data: dict[str, Any]) -> dict[str, Any]:
    """
    Validate cross-field dependencies in configuration.

    For example:
    - If release_name is specified, namespace should also be specified
    - If pulling from OCI, chart_version might be required
    """
    # Add cross-field validation logic here as needed
    return data
