"""
Enhanced sources model with validation and inheritance support.

This module provides improved Pydantic models for sbkube sources configuration
with comprehensive validation and error handling.
"""

import os
from pathlib import Path
from textwrap import dedent
from typing import Any

from pydantic import field_validator, model_validator

from .base_model import ConfigBaseModel, InheritableConfigModel


class GitRepoScheme(ConfigBaseModel):
    """Git repository configuration with enhanced validation."""

    url: str
    branch: str = "main"
    username: str | None = None
    password: str | None = None
    ssh_key: str | None = None

    def __repr__(self):
        return f"{self.url}#{self.branch}"

    @field_validator("url")
    @classmethod
    def validate_git_url(cls, v: str) -> str:
        """Validate Git URL format."""
        allowed_prefixes = ["http://", "https://", "git://", "ssh://", "git@"]
        if not any(v.startswith(prefix) for prefix in allowed_prefixes):
            raise ValueError(
                f"Git URL must start with one of: {', '.join(allowed_prefixes)}",
            )
        return v

    @field_validator("branch")
    @classmethod
    def validate_branch(cls, v: str) -> str:
        """Validate branch name is not empty."""
        if not v or not v.strip():
            raise ValueError("branch name cannot be empty")
        return v.strip()

    @model_validator(mode="after")
    def validate_auth_method(self) -> "GitRepoScheme":
        """Validate that only one authentication method is specified."""
        auth_methods = [self.username and self.password, self.ssh_key]
        if sum(bool(method) for method in auth_methods) > 1:
            raise ValueError(
                "Only one authentication method can be specified: "
                "either username/password or ssh_key",
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
            raise ValueError(
                "When using TLS, all three files must be specified: "
                "ca_file, cert_file, and key_file",
            )

        if self.insecure_skip_tls_verify and tls_files_set > 0:
            raise ValueError(
                "Cannot use insecure_skip_tls_verify with TLS certificate files",
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
    """
    Main sources configuration with enhanced validation and inheritance.

    Supports:
    - Multiple repository types (Helm, OCI, Git)
    - Kubeconfig validation
    - Repository authentication
    - Configuration inheritance
    """

    cluster: str
    kubeconfig: str | None = None
    kubeconfig_context: str | None = None
    helm_repos: dict[str, HelmRepoScheme] = {}
    oci_repos: dict[str, dict[str, str]] = {}  # Legacy format
    oci_registries: dict[str, OciRepoScheme] = {}  # New format
    git_repos: dict[str, GitRepoScheme] = {}

    # Global proxy settings
    http_proxy: str | None = None
    https_proxy: str | None = None
    no_proxy: list[str] | None = None

    def __repr__(self):
        return dedent(
            f"""
            cluster: {self.cluster}
            kubeconfig: {self.kubeconfig}
            helm_repos: {len(self.helm_repos)} repositories
            oci_registries: {len(self.oci_registries)} registries
            git_repos: {len(self.git_repos)} repositories
        """,
        ).strip()

    @field_validator("cluster")
    @classmethod
    def validate_cluster_name(cls, v: str) -> str:
        """Validate cluster name is not empty."""
        if not v or not v.strip():
            raise ValueError("cluster name cannot be empty")
        return v.strip()

    @field_validator("kubeconfig")
    @classmethod
    def validate_kubeconfig_path(cls, v: str | None) -> str | None:
        """Validate kubeconfig path exists if specified."""
        if v is None:
            return v

        # Expand user home directory
        v = os.path.expanduser(v)

        # Check if file exists
        if not Path(v).exists():
            raise ValueError(f"kubeconfig file not found: {v}")

        return v

    @field_validator("helm_repos")
    @classmethod
    def validate_helm_repos_legacy(cls, v: dict[str, str]) -> dict[str, HelmRepoScheme]:
        """Convert legacy helm_repos format to new format."""
        if not v:
            return {}

        # Check if already in new format
        if all(isinstance(repo, HelmRepoScheme) for repo in v.values()):
            return v

        # Convert from legacy format
        converted = {}
        for name, url in v.items():
            if isinstance(url, str):
                converted[name] = HelmRepoScheme(url=url)
            elif isinstance(url, dict):
                converted[name] = HelmRepoScheme(**url)
            else:
                converted[name] = url

        return converted

    @field_validator("oci_repos")
    @classmethod
    def validate_oci_repos_legacy(
        cls,
        v: dict[str, dict[str, str]],
    ) -> dict[str, dict[str, str]]:
        """Validate legacy OCI repos format."""
        for repo_group, charts in v.items():
            for chart_name, oci_url in charts.items():
                if not oci_url.startswith("oci://"):
                    raise ValueError(
                        f"Invalid OCI URL for {repo_group}/{chart_name}: "
                        f"{oci_url} (must start with 'oci://')",
                    )
        return v

    @model_validator(mode="after")
    def migrate_oci_repos(self) -> "SourceScheme":
        """Migrate legacy oci_repos to new oci_registries format."""
        if self.oci_repos and not self.oci_registries:
            # Migrate from legacy format
            registries = {}
            for provider, charts in self.oci_repos.items():
                # Extract registry URL from first chart
                if charts:
                    first_url = next(iter(charts.values()))
                    # Extract registry from oci://registry/path
                    registry = first_url.split("/")[2]
                    registries[provider] = OciRepoScheme(registry=f"oci://{registry}")

            self.oci_registries = registries

        return self

    def get_helm_repo(self, name: str) -> HelmRepoScheme | None:
        """Get Helm repository configuration by name."""
        return self.helm_repos.get(name)

    def get_git_repo(self, name: str) -> GitRepoScheme | None:
        """Get Git repository configuration by name."""
        return self.git_repos.get(name)

    def get_oci_registry(self, name: str) -> OciRepoScheme | None:
        """Get OCI registry configuration by name."""
        return self.oci_registries.get(name)

    def get_oci_chart_url(self, provider: str, chart: str) -> str | None:
        """Get OCI chart URL from legacy format."""
        if provider in self.oci_repos:
            return self.oci_repos[provider].get(chart)
        return None

    def validate_repo_references(self, app_configs: list[dict[str, Any]]) -> list[str]:
        """
        Validate that all repository references in app configs exist.

        Args:
            app_configs: List of application configurations

        Returns:
            List of validation errors (empty if all valid)
        """
        errors = []

        for app in app_configs:
            app_type = app.get("type", "")
            specs = app.get("specs", {})

            if app_type in ["pull-helm", "pull-helm-oci"]:
                repo = specs.get("repo", "")

                if app_type == "pull-helm" and repo not in self.helm_repos:
                    errors.append(
                        f"App '{app.get('name')}' references unknown Helm repo: {repo}",
                    )

                if app_type == "pull-helm-oci":
                    # Check both new and legacy formats
                    if repo not in self.oci_registries and repo not in self.oci_repos:
                        errors.append(
                            f"App '{app.get('name')}' references unknown OCI registry: {repo}",
                        )

            elif app_type == "pull-git":
                repo = specs.get("repo", "")
                if repo not in self.git_repos:
                    errors.append(
                        f"App '{app.get('name')}' references unknown Git repo: {repo}",
                    )

        return errors
