"""
Enhanced configuration models with validation and inheritance support.

This module provides improved Pydantic models for sbkube configuration
with comprehensive validation, inheritance, and error handling.
"""

from typing import Any, Literal

from pydantic import Field, field_validator, model_validator

from .base_model import ConfigBaseModel, InheritableConfigModel
from .validators import validate_spec_fields

# --- Base spec definitions with enhanced validation ---


class CopyPair(ConfigBaseModel):
    """Source and destination pair for copy operations."""

    src: str
    dest: str

    @field_validator("src", "dest")
    @classmethod
    def validate_paths(cls, v: str) -> str:
        """Validate that paths are not empty and don't contain dangerous patterns."""
        return cls.validate_path_exists(v, must_exist=False)


class FileActionSpec(ConfigBaseModel):
    """Specification for file actions (apply, create, delete)."""

    type: Literal["apply", "create", "delete"]
    path: str
    namespace: str | None = None

    @field_validator("path")
    @classmethod
    def validate_action_path(cls, v: str) -> str:
        """Validate action path - can be local file or URL."""
        if v.startswith(("http://", "https://")):
            return cls.validate_url(v, allowed_schemes=["http", "https"])
        return cls.validate_path_exists(v, must_exist=False)


# --- App spec base classes ---


class AppSpecBase(ConfigBaseModel):
    """Base class for all application specifications."""

    pass


class AppExecSpec(AppSpecBase):
    """Specification for executing commands."""

    commands: list[str] = Field(default_factory=list)

    @field_validator("commands")
    @classmethod
    def validate_commands(cls, v: list[str]) -> list[str]:
        """Validate command list is not empty and contains strings."""
        if not v:
            raise ValueError("commands cannot be empty")
        if not all(isinstance(cmd, str) and cmd.strip() for cmd in v):
            raise ValueError("all commands must be non-empty strings")
        return v


class AppInstallHelmSpec(AppSpecBase):
    """Specification for Helm chart installation."""

    path: str | None = None
    values: list[str] = Field(default_factory=list)
    release_name: str | None = None
    namespace: str | None = None
    create_namespace: bool = False
    wait: bool = False
    timeout: str | None = None
    atomic: bool = False

    @field_validator("path")
    @classmethod
    def validate_helm_path(cls, v: str | None) -> str | None:
        """Validate Helm chart path."""
        if v is not None:
            return cls.validate_path_exists(v, must_exist=False)
        return v

    @field_validator("release_name")
    @classmethod
    def validate_release_name(cls, v: str | None) -> str | None:
        """Validate Helm release name."""
        if v is not None:
            return cls.validate_kubernetes_name(v, "release_name")
        return v

    @field_validator("namespace")
    @classmethod
    def validate_namespace(cls, v: str | None) -> str | None:
        """Validate namespace name."""
        return cls.validate_namespace(v)

    @field_validator("timeout")
    @classmethod
    def validate_timeout(cls, v: str | None) -> str | None:
        """Validate timeout format (e.g., 5m30s)."""
        if v is not None:
            import re

            if not re.match(r"^\d+[hms](\d+[ms])?$", v):
                raise ValueError("timeout must be in format like '5m30s', '1h', '300s'")
        return v


class AppInstallKubectlSpec(AppSpecBase):
    """Specification for kubectl-based installation."""

    paths: list[str] = Field(default_factory=list)
    namespace: str | None = None

    @field_validator("paths")
    @classmethod
    def validate_kubectl_paths(cls, v: list[str]) -> list[str]:
        """Validate kubectl manifest paths."""
        return cls.validate_non_empty_list(v, "paths")


class AppInstallActionSpec(AppSpecBase):
    """Specification for action-based installation."""

    actions: list[FileActionSpec] = Field(default_factory=list)
    uninstall: dict[str, list[FileActionSpec]] | None = None

    @field_validator("actions")
    @classmethod
    def validate_actions(cls, v: list[FileActionSpec]) -> list[FileActionSpec]:
        """Validate action list is not empty."""
        return cls.validate_non_empty_list(v, "actions")


class AppInstallKustomizeSpec(AppSpecBase):
    """Specification for Kustomize-based installation."""

    kustomize_path: str
    namespace: str | None = None

    @field_validator("kustomize_path")
    @classmethod
    def validate_kustomize_path(cls, v: str) -> str:
        """Validate Kustomize directory path."""
        return cls.validate_path_exists(v, must_exist=False)


class AppRenderSpec(AppSpecBase):
    """Specification for template rendering."""

    templates: list[str] = Field(default_factory=list)
    values: dict[str, Any] | None = None

    @field_validator("templates")
    @classmethod
    def validate_templates(cls, v: list[str]) -> list[str]:
        """Validate template list."""
        return cls.validate_non_empty_list(v, "templates")


class AppCopySpec(AppSpecBase):
    """Specification for copy operations."""

    paths: list[CopyPair] = Field(default_factory=list)

    @field_validator("paths")
    @classmethod
    def validate_copy_paths(cls, v: list[CopyPair]) -> list[CopyPair]:
        """Validate copy paths list."""
        return cls.validate_non_empty_list(v, "paths")


class AppPullHelmSpec(AppSpecBase):
    """Specification for pulling Helm charts."""

    repo: str
    chart: str
    dest: str | None = None
    chart_version: str | None = None
    app_version: str | None = None
    removes: list[str] = Field(default_factory=list)
    overrides: list[str] = Field(default_factory=list)

    @field_validator("repo", "chart")
    @classmethod
    def validate_required_fields(cls, v: str) -> str:
        """Validate required fields are not empty."""
        if not v or not v.strip():
            raise ValueError("field cannot be empty")
        return v.strip()

    @field_validator("chart_version")
    @classmethod
    def validate_chart_version(cls, v: str | None) -> str | None:
        """Validate Helm chart version."""
        return cls.validate_helm_version(v)


class AppPullHelmOciSpec(AppPullHelmSpec):
    """Specification for pulling Helm charts from OCI registries."""

    pass  # Inherits all validators from AppPullHelmSpec


class AppPullGitSpec(AppSpecBase):
    """Specification for pulling from Git repositories."""

    repo: str
    paths: list[CopyPair] = Field(default_factory=list)
    ref: str | None = None  # Git ref (branch, tag, commit)

    @field_validator("repo")
    @classmethod
    def validate_repo(cls, v: str) -> str:
        """Validate repository name."""
        if not v or not v.strip():
            raise ValueError("repo cannot be empty")
        return v.strip()


class AppPullHttpSpec(AppSpecBase):
    """Specification for pulling from HTTP sources."""

    url: str
    dest: str
    headers: dict[str, str] | None = None

    @field_validator("url")
    @classmethod
    def validate_http_url(cls, v: str) -> str:
        """Validate HTTP URL."""
        return cls.validate_url(v, allowed_schemes=["http", "https"])


# --- Main configuration schemas with inheritance support ---


class AppInfoScheme(InheritableConfigModel):
    """
    Application definition with enhanced validation.

    Supports inheritance from parent app definitions and
    comprehensive validation of all fields.
    """

    name: str
    type: Literal[
        "exec",
        "copy-repo",
        "copy-chart",
        "copy-root",
        "copy-app",
        "install-helm",
        "install-kubectl",
        "install-yaml",
        "install-action",
        "install-kustomize",
        "pull-helm",
        "pull-helm-oci",
        "pull-git",
        "pull-http",
        "render",
    ]
    enabled: bool = True
    namespace: str | None = None
    release_name: str | None = None
    specs: dict[str, Any] = Field(default_factory=dict)
    labels: dict[str, str] = Field(default_factory=dict)
    annotations: dict[str, str] = Field(default_factory=dict)

    @field_validator("name")
    @classmethod
    def validate_app_name(cls, v: str) -> str:
        """Validate application name follows Kubernetes naming convention."""
        return cls.validate_kubernetes_name(v, "name")

    @field_validator("namespace")
    @classmethod
    def validate_namespace_field(cls, v: str | None) -> str | None:
        """Validate namespace if provided."""
        if v is not None:
            return cls.validate_kubernetes_name(v, "namespace")
        return v

    @field_validator("release_name")
    @classmethod
    def validate_release_name(cls, v: str | None) -> str | None:
        """Validate release name if provided."""
        if v is not None:
            return cls.validate_kubernetes_name(v, "release_name")
        return v

    @model_validator(mode="after")
    def validate_specs_for_type(self) -> "AppInfoScheme":
        """Validate specs match the application type."""
        if self.enabled:
            # Validate but don't reassign to avoid triggering validate_assignment recursion
            validated_specs = validate_spec_fields(self.type, self.specs)
            # Use object.__setattr__ to bypass Pydantic's validate_assignment
            object.__setattr__(self, 'specs', validated_specs)
        return self

    def get_validated_specs(self) -> AppSpecBase:
        """
        Get validated spec instance for this app type.

        Returns:
            Validated spec model instance

        Raises:
            ConfigValidationError: If specs don't match the app type
        """
        from .config_model import get_spec_model

        spec_class = get_spec_model(self.type)

        if spec_class is None:
            raise ValueError(f"No spec model found for app type: {self.type}")

        return spec_class(**self.specs)


class AppGroupScheme(InheritableConfigModel):
    """
    Application group configuration with enhanced validation.

    Supports:
    - Inheritance from parent configurations
    - Namespace inheritance to apps
    - Dependency resolution
    - Comprehensive validation
    """

    namespace: str
    deps: list[str] = Field(default_factory=list)
    apps: list[AppInfoScheme] = Field(default_factory=list)
    global_labels: dict[str, str] = Field(default_factory=dict)
    global_annotations: dict[str, str] = Field(default_factory=dict)

    @field_validator("namespace")
    @classmethod
    def validate_namespace(cls, v: str) -> str:
        """Validate namespace name."""
        return cls.validate_namespace(v)

    @field_validator("deps")
    @classmethod
    def validate_deps(cls, v: list[str]) -> list[str]:
        """Validate dependency list contains unique values."""
        return cls.validate_unique_list(v, "deps")

    @model_validator(mode="after")
    def apply_namespace_inheritance(self) -> "AppGroupScheme":
        """
        Apply namespace inheritance to apps that don't specify one.
        Also apply global labels and annotations.
        """
        for app in self.apps:
            # Inherit namespace if not specified
            if app.namespace is None:
                app.namespace = self.namespace

            # Merge global labels and annotations
            if self.global_labels:
                app.labels = {**self.global_labels, **app.labels}

            if self.global_annotations:
                app.annotations = {**self.global_annotations, **app.annotations}

        return self

    @model_validator(mode="after")
    def validate_app_names_unique(self) -> "AppGroupScheme":
        """Ensure all app names are unique within the group."""
        app_names = [app.name for app in self.apps if app.enabled]
        if len(app_names) != len(set(app_names)):
            duplicates = [name for name in app_names if app_names.count(name) > 1]
            raise ValueError(f"Duplicate app names found: {', '.join(set(duplicates))}")
        return self

    def get_enabled_apps(self) -> list[AppInfoScheme]:
        """Get list of enabled applications."""
        return [app for app in self.apps if app.enabled]

    def get_apps_by_type(self, app_type: str) -> list[AppInfoScheme]:
        """Get list of applications by type."""
        return [app for app in self.apps if app.type == app_type and app.enabled]


# --- Enhanced spec model mapping ---


def get_spec_model(app_type: str) -> type[AppSpecBase] | None:
    """Get the appropriate spec model class for an app type."""
    spec_model_mapping = {
        "exec": AppExecSpec,
        "install-helm": AppInstallHelmSpec,
        "install-kubectl": AppInstallKubectlSpec,
        "install-yaml": AppInstallActionSpec,
        "install-action": AppInstallActionSpec,
        "install-kustomize": AppInstallKustomizeSpec,
        "render": AppRenderSpec,
        "copy-repo": AppCopySpec,
        "copy-chart": AppCopySpec,
        "copy-root": AppCopySpec,
        "copy-app": AppCopySpec,
        "pull-helm": AppPullHelmSpec,
        "pull-helm-oci": AppPullHelmOciSpec,
        "pull-git": AppPullGitSpec,
        "pull-http": AppPullHttpSpec,
    }
    return spec_model_mapping.get(app_type)
