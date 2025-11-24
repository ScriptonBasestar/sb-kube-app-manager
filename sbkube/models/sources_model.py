"""Enhanced sources model with validation and inheritance support.

This module provides improved Pydantic models for sbkube sources configuration
with comprehensive validation and error handling.
"""

import os
from pathlib import Path
from textwrap import dedent
from typing import Any

import yaml
from pydantic import Field, field_validator, model_validator

from .base_model import ConfigBaseModel, InheritableConfigModel


class GitRepoScheme(ConfigBaseModel):
    """Git repository configuration with enhanced validation."""

    url: str
    branch: str = "main"
    username: str | None = None
    password: str | None = None
    ssh_key: str | None = None

    def __repr__(self) -> str:
        return f"{self.url}#{self.branch}"

    @field_validator("url")
    @classmethod
    def validate_git_url(cls, v: str) -> str:
        """Validate Git URL format."""
        allowed_prefixes = ["http://", "https://", "git://", "ssh://", "git@"]
        if not any(v.startswith(prefix) for prefix in allowed_prefixes):
            msg = f"Git URL must start with one of: {', '.join(allowed_prefixes)}"
            raise ValueError(
                msg,
            )
        return v

    @field_validator("branch")
    @classmethod
    def validate_branch(cls, v: str) -> str:
        """Validate branch name is not empty."""
        if not v or not v.strip():
            msg = "branch name cannot be empty"
            raise ValueError(msg)
        return v.strip()

    @model_validator(mode="after")
    def validate_auth_method(self) -> "GitRepoScheme":
        """Validate that only one authentication method is specified."""
        auth_methods = [self.username and self.password, self.ssh_key]
        if sum(bool(method) for method in auth_methods) > 1:
            msg = (
                "Only one authentication method can be specified: "
                "either username/password or ssh_key"
            )
            raise ValueError(
                msg,
            )
        return self


class HelmRepoScheme(ConfigBaseModel):
    """Helm repository configuration with enhanced validation."""

    url: str
    username: str | None = None
    password: str | None = None
    ca_file: str | None = None
    cert_file: str | None = None
    key_file: str | None = None
    insecure_skip_tls_verify: bool = False

    @field_validator("url")
    @classmethod
    def validate_helm_url(cls, v: str) -> str:
        """Validate Helm repository URL."""
        return cls.validate_url(v, allowed_schemes=["http", "https"])

    @model_validator(mode="after")
    def validate_tls_config(self) -> "HelmRepoScheme":
        """Validate TLS configuration consistency."""
        tls_files = [self.ca_file, self.cert_file, self.key_file]
        tls_files_set = sum(1 for f in tls_files if f is not None)

        if tls_files_set > 0 and tls_files_set < 3:
            msg = (
                "When using TLS, all three files must be specified: "
                "ca_file, cert_file, and key_file"
            )
            raise ValueError(
                msg,
            )

        if self.insecure_skip_tls_verify and tls_files_set > 0:
            msg = "Cannot use insecure_skip_tls_verify with TLS certificate files"
            raise ValueError(
                msg,
            )

        return self


class OciRepoScheme(ConfigBaseModel):
    """OCI repository configuration with enhanced validation."""

    registry: str
    username: str | None = None
    password: str | None = None

    @field_validator("registry")
    @classmethod
    def validate_oci_registry(cls, v: str) -> str:
        """Validate OCI registry URL."""
        if not v.startswith("oci://"):
            # Auto-prefix with oci:// if not present
            v = f"oci://{v}"
        return v


class SourceScheme(InheritableConfigModel):
    """Main sources configuration with mandatory cluster targeting.

    **Design Principle**:
    - Explicit cluster configuration is REQUIRED
    - No implicit defaults (KUBECONFIG env, ~/.kube/config)
    - One sources.yaml = One cluster target

    **For multi-cluster deployments**:
    Use separate sources files:
    - sources-dev.yaml
    - sources-staging.yaml
    - sources-prd.yaml

    Supports:
    - Multiple repository types (Helm, OCI, Git)
    - Kubeconfig validation
    - Repository authentication
    - Configuration inheritance
    - Optional app directory specification (v0.5.0+)
    """

    # Cluster targeting (required for deployment)
    cluster: str | None = None  # Cluster identifier (documentation purpose, optional)
    kubeconfig: str  # Kubeconfig file path (required)
    kubeconfig_context: str  # Kubectl context name (required)

    # App directory control (optional, v0.5.0+)
    app_dirs: list[str] | None = None  # Explicit list of app directories to deploy

    # Cluster-level global values (optional, v0.7.0+)
    cluster_values_file: str | None = None  # Path to cluster-level values YAML file
    global_values: dict[str, Any] | None = (
        None  # Inline global values (merged with cluster_values_file)
    )

    # Manifest cleanup settings (optional, v0.7.0+)
    cleanup_metadata: bool = True  # Auto-remove server-managed metadata fields (default: True)

    # Repository configuration (optional)
    helm_repos: dict[str, HelmRepoScheme] = Field(default_factory=dict)
    oci_registries: dict[str, OciRepoScheme] = Field(default_factory=dict)
    git_repos: dict[str, GitRepoScheme] = Field(default_factory=dict)

    # Global proxy settings
    http_proxy: str | None = None
    https_proxy: str | None = None
    no_proxy: list[str] | None = None

    def __repr__(self) -> str:
        return dedent(
            f"""
            cluster: {self.cluster}
            kubeconfig: {self.kubeconfig}
            helm_repos: {len(self.helm_repos)} repositories
            oci_registries: {len(self.oci_registries)} registries
            git_repos: {len(self.git_repos)} repositories
        """,
        ).strip()

    @field_validator("helm_repos", mode="before")
    @classmethod
    def normalize_helm_repos(cls, v: Any) -> dict[str, Any]:
        """Normalize helm_repos to support string shorthand format.

        Converts: {"grafana": "https://..."} -> {"grafana": {"url": "https://..."}}
        """
        if not isinstance(v, dict):
            return v

        normalized = {}
        for name, value in v.items():
            if isinstance(value, str):
                # String shorthand: convert to dict with url field
                normalized[name] = {"url": value}
            else:
                # Already a dict or HelmRepoScheme instance
                normalized[name] = value
        return normalized

    @field_validator("git_repos", mode="before")
    @classmethod
    def normalize_git_repos(cls, v: Any) -> dict[str, Any]:
        """Normalize git_repos to support string shorthand format.

        Converts: {"my-repo": "https://github.com/..."} -> {"my-repo": {"url": "https://github.com/..."}}
        """
        if not isinstance(v, dict):
            return v

        normalized = {}
        for name, value in v.items():
            if isinstance(value, str):
                # String shorthand: convert to dict with url field
                normalized[name] = {"url": value}
            else:
                # Already a dict or GitRepoScheme instance
                normalized[name] = value
        return normalized

    @field_validator("oci_registries", mode="before")
    @classmethod
    def normalize_oci_registries(cls, v: Any) -> dict[str, Any]:
        """Normalize oci_registries to support string shorthand format.

        Converts: {"ghcr": "ghcr.io"} -> {"ghcr": {"registry": "ghcr.io"}}
        """
        if not isinstance(v, dict):
            return v

        normalized = {}
        for name, value in v.items():
            if isinstance(value, str):
                # String shorthand: convert to dict with registry field
                normalized[name] = {"registry": value}
            else:
                # Already a dict or OciRepoScheme instance
                normalized[name] = value
        return normalized

    @field_validator("cluster")
    @classmethod
    def validate_cluster_name(cls, v: str | None) -> str | None:
        """Validate cluster name is not empty if specified."""
        if v is not None and (not v or not v.strip()):
            msg = "cluster name cannot be empty"
            raise ValueError(msg)
        return v.strip() if v else None

    @field_validator("kubeconfig")
    @classmethod
    def validate_kubeconfig_not_empty(cls, v: str) -> str:
        """Validate kubeconfig is not empty."""
        if not v or not v.strip():
            msg = (
                "kubeconfig is required. "
                "Specify the path to your kubeconfig file in sources.yaml"
            )
            raise ValueError(
                msg,
            )
        return v.strip()

    @field_validator("kubeconfig_context")
    @classmethod
    def validate_context_not_empty(cls, v: str) -> str:
        """Validate context is not empty."""
        if not v or not v.strip():
            msg = (
                "kubeconfig_context is required. "
                "Specify the kubectl context name in sources.yaml"
            )
            raise ValueError(
                msg,
            )
        return v.strip()

    @field_validator("app_dirs")
    @classmethod
    def validate_app_dirs(cls, v: list[str] | None) -> list[str] | None:
        """Validate app_dirs list."""
        if v is None:
            return None

        if not isinstance(v, list):
            msg = "app_dirs must be a list of directory names"
            raise ValueError(msg)

        if len(v) == 0:
            msg = (
                "app_dirs cannot be empty. Remove the field or provide directory names"
            )
            raise ValueError(msg)

        # Validate each directory name
        validated = []
        for dir_name in v:
            if not isinstance(dir_name, str):
                msg = f"app_dirs must contain strings, got: {type(dir_name).__name__}"
                raise ValueError(msg)

            dir_name = dir_name.strip()
            if not dir_name:
                msg = "app_dirs cannot contain empty directory names"
                raise ValueError(msg)

            # Check for invalid characters or paths
            if "/" in dir_name or "\\" in dir_name:
                msg = (
                    f"app_dirs must contain directory names only, not paths: '{dir_name}'. "
                    "Use simple names like 'redis', 'postgres', etc."
                )
                raise ValueError(msg)

            if dir_name.startswith("."):
                msg = f"app_dirs cannot contain hidden directories: '{dir_name}'"
                raise ValueError(msg)

            validated.append(dir_name)

        # Check for duplicates
        if len(validated) != len(set(validated)):
            msg = "app_dirs cannot contain duplicate directory names"
            raise ValueError(msg)

        return validated

    def get_helm_repo(self, name: str) -> HelmRepoScheme | None:
        """Get Helm repository configuration by name."""
        return self.helm_repos.get(name)

    def get_git_repo(self, name: str) -> GitRepoScheme | None:
        """Get Git repository configuration by name."""
        return self.git_repos.get(name)

    def get_oci_registry(self, name: str) -> OciRepoScheme | None:
        """Get OCI registry configuration by name."""
        return self.oci_registries.get(name)

    def get_app_dirs(self, base_dir, config_file_name: str = "config.yaml") -> list:
        """Get list of app directories to process.

        This method supports two modes:
        1. Explicit mode (app_dirs specified): Use the exact list from sources.yaml
        2. Auto-discovery mode (app_dirs not specified): Find all directories with config.yaml

        Args:
            base_dir: Project root directory (Path object)
            config_file_name: Configuration file name to look for (default: "config.yaml")

        Returns:
            list[Path]: List of app directory paths

        Raises:
            ValueError: If explicit app_dirs reference non-existent directories

        Example:
            # sources.yaml with explicit list
            app_dirs: ["redis", "postgres", "nginx"]

            # sources.yaml without app_dirs (auto-discovery)
            # (field not specified)

        """
        from pathlib import Path

        base_path = Path(base_dir).resolve()

        # Mode 1: Explicit list from sources.yaml
        if self.app_dirs is not None:
            app_paths = []
            missing = []

            for dir_name in self.app_dirs:
                dir_path = base_path / dir_name
                config_path = dir_path / config_file_name

                if not dir_path.exists():
                    missing.append(f"Directory not found: {dir_name}")
                elif not dir_path.is_dir():
                    missing.append(f"Not a directory: {dir_name}")
                elif not config_path.exists():
                    missing.append(
                        f"Config file not found: {dir_name}/{config_file_name}"
                    )
                else:
                    app_paths.append(dir_path)

            if missing:
                raise ValueError(
                    "Invalid app_dirs in sources.yaml:\n"
                    + "\n".join(f"  - {msg}" for msg in missing)
                )

            return sorted(app_paths)

        # Mode 2: Auto-discovery (app_dirs not specified)
        from sbkube.utils.common import find_all_app_dirs

        return find_all_app_dirs(base_path, config_file_name)

    def validate_repo_references(self, app_configs: list[dict[str, Any]]) -> list[str]:
        """Validate that all repository references in app configs exist.

        Args:
            app_configs: List of application configurations

        Returns:
            List of validation errors (empty if all valid)

        """
        errors = []

        for app in app_configs:
            app_type = app.get("type", "")
            specs = app.get("specs", {})

            if app_type == "helm":
                repo = specs.get("repo", "")
                if repo and repo not in self.helm_repos:
                    errors.append(
                        f"App '{app.get('name')}' references unknown Helm repo: {repo}",
                    )

        return errors

    @field_validator("cluster_values_file")
    @classmethod
    def validate_cluster_values_file(cls, v: str | None) -> str | None:
        """Validate cluster_values_file path if specified."""
        if v is None:
            return None

        v = v.strip()
        if not v:
            msg = "cluster_values_file cannot be empty string"
            raise ValueError(msg)

        # Expand user home directory
        expanded_path = os.path.expanduser(v)

        # Check if file exists
        if not os.path.exists(expanded_path):
            msg = f"cluster_values_file not found: {v}"
            raise ValueError(msg)

        if not os.path.isfile(expanded_path):
            msg = f"cluster_values_file is not a file: {v}"
            raise ValueError(msg)

        return v

    def get_merged_global_values(
        self, sources_dir: str | Path | None = None
    ) -> dict[str, Any]:
        """Merge cluster-level values with priority.

        Priority (low to high):
        1. cluster_values_file (lowest)
        2. global_values (highest)

        Args:
            sources_dir: Directory containing sources.yaml (for resolving relative paths)

        Returns:
            Merged global values dictionary

        Example:
            >>> sources = SourceScheme(
            ...     kubeconfig="~/.kube/config",
            ...     kubeconfig_context="prod",
            ...     cluster_values_file="cluster-values.yaml",
            ...     global_values={"global": {"environment": "production"}}
            ... )
            >>> values = sources.get_merged_global_values()
            >>> values["global"]["environment"]
            'production'

        """
        from sbkube.utils.dict_merge import deep_merge

        merged = {}

        # 1. Load from cluster_values_file (lowest priority)
        if self.cluster_values_file:
            file_path = self.cluster_values_file

            # Expand user home directory
            file_path = os.path.expanduser(file_path)

            # Handle relative paths
            if not os.path.isabs(file_path) and sources_dir:
                file_path = os.path.join(sources_dir, file_path)

            try:
                with open(file_path, encoding="utf-8") as f:
                    file_values = yaml.safe_load(f)
                    if file_values and isinstance(file_values, dict):
                        merged = deep_merge(merged, file_values)
            except FileNotFoundError as e:
                msg = f"cluster_values_file not found: {self.cluster_values_file}"
                raise ValueError(msg) from e
            except yaml.YAMLError as e:
                msg = f"Invalid YAML in cluster_values_file: {self.cluster_values_file}"
                raise ValueError(msg) from e

        # 2. Merge inline global_values (higher priority)
        if self.global_values:
            merged = deep_merge(merged, self.global_values)

        return merged
