"""Helm command builder utilities for SBKube.

This module provides a fluent builder interface for constructing Helm commands
with proper option handling, reducing code duplication across commands.

Phase 4 refactoring: Centralize helm command construction patterns.
"""

import tempfile
from dataclasses import dataclass, field
from enum import Enum
from pathlib import Path
from typing import TYPE_CHECKING

if TYPE_CHECKING:
    from sbkube.models.config_model import HelmApp


class HelmCommand(Enum):
    """Supported Helm commands."""

    TEMPLATE = "template"
    UPGRADE = "upgrade"
    INSTALL = "install"
    PULL = "pull"
    REPO_ADD = "repo add"
    REPO_UPDATE = "repo update"


@dataclass
class HelmCommandResult:
    """Result of Helm command building.

    Attributes:
        command: List of command arguments
        temp_files: List of temporary files that need cleanup
        description: Human-readable description of the command

    """

    command: list[str]
    temp_files: list[Path] = field(default_factory=list)
    description: str = ""

    def cleanup(self) -> None:
        """Remove temporary files created during command building."""
        import os

        for temp_file in self.temp_files:
            if temp_file.exists():
                os.unlink(temp_file)


class HelmCommandBuilder:
    """Fluent builder for Helm commands.

    Example:
        ```python
        result = (
            HelmCommandBuilder(HelmCommand.TEMPLATE)
            .with_release_name("nginx")
            .with_chart_path("/path/to/chart")
            .with_namespace("default")
            .with_values_file("/path/to/values.yaml")
            .with_set("key", "value")
            .build()
        )
        # result.command = ["helm", "template", "nginx", "/path/to/chart", ...]
        ```

    """

    def __init__(self, command: HelmCommand) -> None:
        """Initialize builder with Helm command type.

        Args:
            command: Type of Helm command to build

        """
        self._command = command
        self._release_name: str | None = None
        self._chart_path: Path | None = None
        self._chart_ref: str | None = None  # For pull command
        self._namespace: str | None = None
        self._create_namespace: bool = False
        self._install_flag: bool = False
        self._wait: bool = False
        self._atomic: bool = False
        self._timeout: str | None = None
        self._values_files: list[Path] = []
        self._set_values: dict[str, str] = {}
        self._set_string_values: dict[str, str] = {}
        self._extra_args: list[str] = []
        self._temp_files: list[Path] = []

        # For cluster global values
        self._cluster_values_dict: dict | None = None

        # For repo add
        self._repo_name: str | None = None
        self._repo_url: str | None = None

        # For pull
        self._destination: Path | None = None
        self._version: str | None = None
        self._untar: bool = False

    def with_release_name(self, name: str) -> "HelmCommandBuilder":
        """Set the release name."""
        self._release_name = name
        return self

    def with_chart_path(self, path: Path | str) -> "HelmCommandBuilder":
        """Set the chart path (for template/upgrade/install)."""
        self._chart_path = Path(path) if isinstance(path, str) else path
        return self

    def with_chart_ref(self, ref: str) -> "HelmCommandBuilder":
        """Set the chart reference (for pull, e.g., 'repo/chart' or OCI URL)."""
        self._chart_ref = ref
        return self

    def with_namespace(self, namespace: str | None) -> "HelmCommandBuilder":
        """Set the target namespace."""
        if namespace:
            self._namespace = namespace
        return self

    def with_create_namespace(self, create: bool = True) -> "HelmCommandBuilder":
        """Enable --create-namespace flag."""
        self._create_namespace = create
        return self

    def with_install_flag(self, install: bool = True) -> "HelmCommandBuilder":
        """Enable --install flag (for upgrade command)."""
        self._install_flag = install
        return self

    def with_wait(self, wait: bool = True) -> "HelmCommandBuilder":
        """Enable --wait flag."""
        self._wait = wait
        return self

    def with_atomic(self, atomic: bool = True) -> "HelmCommandBuilder":
        """Enable --atomic flag."""
        self._atomic = atomic
        return self

    def with_timeout(self, timeout: str | None) -> "HelmCommandBuilder":
        """Set --timeout value (e.g., '5m0s')."""
        if timeout:
            self._timeout = timeout
        return self

    def with_values_file(self, path: Path | str) -> "HelmCommandBuilder":
        """Add a values file."""
        file_path = Path(path) if isinstance(path, str) else path
        self._values_files.append(file_path)
        return self

    def with_values_files(self, paths: list[Path | str]) -> "HelmCommandBuilder":
        """Add multiple values files."""
        for path in paths:
            self.with_values_file(path)
        return self

    def with_set(self, key: str, value: str) -> "HelmCommandBuilder":
        """Add a --set key=value pair."""
        self._set_values[key] = value
        return self

    def with_set_values(self, values: dict[str, str]) -> "HelmCommandBuilder":
        """Add multiple --set key=value pairs."""
        self._set_values.update(values)
        return self

    def with_set_string(self, key: str, value: str) -> "HelmCommandBuilder":
        """Add a --set-string key=value pair."""
        self._set_string_values[key] = value
        return self

    def with_cluster_global_values(
        self, values: dict | None
    ) -> "HelmCommandBuilder":
        """Set cluster global values (will create temp file)."""
        self._cluster_values_dict = values
        return self

    def with_repo(self, name: str, url: str) -> "HelmCommandBuilder":
        """Set repo name and URL (for repo add)."""
        self._repo_name = name
        self._repo_url = url
        return self

    def with_destination(self, path: Path | str) -> "HelmCommandBuilder":
        """Set destination directory (for pull)."""
        self._destination = Path(path) if isinstance(path, str) else path
        return self

    def with_version(self, version: str | None) -> "HelmCommandBuilder":
        """Set chart version (for pull)."""
        if version:
            self._version = version
        return self

    def with_untar(self, untar: bool = True) -> "HelmCommandBuilder":
        """Enable --untar flag (for pull)."""
        self._untar = untar
        return self

    def with_extra_args(self, *args: str) -> "HelmCommandBuilder":
        """Add extra command-line arguments."""
        self._extra_args.extend(args)
        return self

    def from_helm_app(
        self,
        app: "HelmApp",
        app_config_dir: Path,
        include_cluster_values: bool = True,
        cluster_global_values: dict | None = None,
    ) -> "HelmCommandBuilder":
        """Configure builder from HelmApp configuration.

        Args:
            app: HelmApp configuration object
            app_config_dir: Directory containing values files
            include_cluster_values: Whether to include cluster global values
            cluster_global_values: Cluster-level values dictionary

        Returns:
            Self for chaining

        """
        # Release name
        if app.release_name:
            self.with_release_name(app.release_name)

        # Namespace
        if app.namespace:
            self.with_namespace(app.namespace)

        # Deployment options
        if app.create_namespace:
            self.with_create_namespace()
        if app.wait:
            self.with_wait()
        if app.atomic:
            self.with_atomic()
        if app.timeout:
            self.with_timeout(app.timeout)

        # Cluster global values (lowest priority - added first)
        if include_cluster_values and cluster_global_values:
            self.with_cluster_global_values(cluster_global_values)

        # Values files
        if app.values:
            for values_file in app.values:
                values_path = app_config_dir / values_file
                if values_path.exists():
                    self.with_values_file(values_path)

        # Set values
        if app.set_values:
            self.with_set_values(app.set_values)

        return self

    def build(self) -> HelmCommandResult:
        """Build the Helm command.

        Returns:
            HelmCommandResult with command list and temp files

        Raises:
            ValueError: If required parameters are missing

        """
        cmd: list[str] = ["helm"]
        temp_files: list[Path] = []

        if self._command == HelmCommand.TEMPLATE:
            cmd.append("template")
            if not self._release_name:
                raise ValueError("Release name is required for helm template")
            if not self._chart_path:
                raise ValueError("Chart path is required for helm template")
            cmd.extend([self._release_name, str(self._chart_path)])

        elif self._command == HelmCommand.UPGRADE:
            cmd.append("upgrade")
            if not self._release_name:
                raise ValueError("Release name is required for helm upgrade")
            if not self._chart_path:
                raise ValueError("Chart path is required for helm upgrade")
            cmd.extend([self._release_name, str(self._chart_path)])
            if self._install_flag:
                cmd.append("--install")

        elif self._command == HelmCommand.INSTALL:
            cmd.append("install")
            if not self._release_name:
                raise ValueError("Release name is required for helm install")
            if not self._chart_path:
                raise ValueError("Chart path is required for helm install")
            cmd.extend([self._release_name, str(self._chart_path)])

        elif self._command == HelmCommand.PULL:
            cmd.append("pull")
            if not self._chart_ref:
                raise ValueError("Chart reference is required for helm pull")
            cmd.append(self._chart_ref)
            if self._destination:
                cmd.extend(["--destination", str(self._destination)])
            if self._version:
                cmd.extend(["--version", self._version])
            if self._untar:
                cmd.append("--untar")

        elif self._command == HelmCommand.REPO_ADD:
            cmd.extend(["repo", "add"])
            if not self._repo_name or not self._repo_url:
                raise ValueError("Repo name and URL are required for helm repo add")
            cmd.extend([self._repo_name, self._repo_url])

        elif self._command == HelmCommand.REPO_UPDATE:
            cmd.extend(["repo", "update"])

        # Common options
        if self._namespace and self._command not in (
            HelmCommand.PULL,
            HelmCommand.REPO_ADD,
            HelmCommand.REPO_UPDATE,
        ):
            cmd.extend(["--namespace", self._namespace])

        if self._create_namespace:
            cmd.append("--create-namespace")

        if self._wait:
            cmd.append("--wait")

        if self._atomic:
            cmd.append("--atomic")

        if self._timeout:
            cmd.extend(["--timeout", self._timeout])

        # Cluster global values (write to temp file)
        if self._cluster_values_dict:
            import yaml

            temp_file = tempfile.NamedTemporaryFile(
                mode="w", suffix=".yaml", delete=False, encoding="utf-8"
            )
            yaml.dump(
                self._cluster_values_dict, temp_file, default_flow_style=False
            )
            temp_file.close()
            temp_path = Path(temp_file.name)
            temp_files.append(temp_path)
            cmd.extend(["--values", str(temp_path)])

        # Values files
        for values_file in self._values_files:
            cmd.extend(["--values", str(values_file)])

        # Set values
        for key, value in self._set_values.items():
            cmd.extend(["--set", f"{key}={value}"])

        # Set string values
        for key, value in self._set_string_values.items():
            cmd.extend(["--set-string", f"{key}={value}"])

        # Extra args
        cmd.extend(self._extra_args)

        description = self._build_description()

        return HelmCommandResult(
            command=cmd,
            temp_files=temp_files,
            description=description,
        )

    def _build_description(self) -> str:
        """Build human-readable command description."""
        parts = [f"helm {self._command.value}"]
        if self._release_name:
            parts.append(f"release={self._release_name}")
        if self._namespace:
            parts.append(f"ns={self._namespace}")
        return " ".join(parts)


def build_helm_template_command(
    app: "HelmApp",
    app_name: str,
    chart_path: Path,
    app_config_dir: Path,
    cluster_global_values: dict | None = None,
) -> HelmCommandResult:
    """Build helm template command from HelmApp configuration.

    Convenience function for the common helm template use case.

    Args:
        app: HelmApp configuration
        app_name: Name of the application
        chart_path: Path to the chart directory
        app_config_dir: Directory containing values files
        cluster_global_values: Cluster-level values dictionary

    Returns:
        HelmCommandResult ready for execution

    """
    release_name = app.release_name or app_name

    return (
        HelmCommandBuilder(HelmCommand.TEMPLATE)
        .with_release_name(release_name)
        .with_chart_path(chart_path)
        .from_helm_app(
            app,
            app_config_dir,
            cluster_global_values=cluster_global_values,
        )
        .build()
    )


def build_helm_upgrade_command(
    app: "HelmApp",
    app_name: str,
    chart_path: Path,
    app_config_dir: Path,
    cluster_global_values: dict | None = None,
    install: bool = True,
) -> HelmCommandResult:
    """Build helm upgrade command from HelmApp configuration.

    Convenience function for the common helm upgrade --install use case.

    Args:
        app: HelmApp configuration
        app_name: Name of the application
        chart_path: Path to the chart directory
        app_config_dir: Directory containing values files
        cluster_global_values: Cluster-level values dictionary
        install: Whether to include --install flag

    Returns:
        HelmCommandResult ready for execution

    """
    release_name = app.release_name or app_name

    return (
        HelmCommandBuilder(HelmCommand.UPGRADE)
        .with_release_name(release_name)
        .with_chart_path(chart_path)
        .with_install_flag(install)
        .from_helm_app(
            app,
            app_config_dir,
            cluster_global_values=cluster_global_values,
        )
        .build()
    )
