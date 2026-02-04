"""Unified Configuration Model for SBKube v0.10.0+.

This module provides the unified configuration schema (sbkube.yaml) that consolidates
workspace, sources, and config settings into a single hierarchical structure.

Schema Version: 1.0
Target SBKube Version: v0.10.0

Key Features:
- Single file configuration (sbkube.yaml)
- Settings inheritance (global -> phase -> app)
- Backward compatible with legacy files
- Recursive phase structure support

Related Documentation:
- Design: docs/design/unified-config-design.md
- Migration: docs/03-configuration/migration-guide.md
"""

from pathlib import Path
from typing import Annotated, Any, Literal

from pydantic import Field, field_validator, model_validator

from .base_model import ConfigBaseModel
from .config_model import AppConfig
from .sources_model import GitRepoScheme, HelmRepoScheme, OciRepoScheme


# ============================================================================
# Unified Settings
# ============================================================================


class UnifiedSettings(ConfigBaseModel):
    """Unified settings that can be defined at any level.

    Settings are inherited from parent to child with override capability.
    Inheritance order: global -> phase -> app

    Examples:
        settings:
          # Cluster targeting
          kubeconfig: ~/.kube/config
          kubeconfig_context: prod-cluster
          namespace: production

          # Label injection
          helm_label_injection: true
          incompatible_charts:
            - traefik/traefik
          force_label_injection: []

          # Execution control
          execution_order: apps_first
          parallel: false
          parallel_apps: false
          max_workers: 4

          # Failure handling
          on_failure: stop
          rollback_scope: app

          # Timeouts
          timeout: 600

    """

    # ---- Cluster Settings ----
    kubeconfig: Annotated[
        str | None,
        Field(
            description="Path to kubeconfig file",
        ),
    ] = None

    kubeconfig_context: Annotated[
        str | None,
        Field(
            description="Kubectl context name",
        ),
    ] = None

    namespace: Annotated[
        str,
        Field(
            description="Default Kubernetes namespace",
        ),
    ] = "default"

    cluster: Annotated[
        str | None,
        Field(
            description="Cluster identifier (for documentation)",
        ),
    ] = None

    # ---- Repository Configuration ----
    helm_repos: Annotated[
        dict[str, HelmRepoScheme | str],
        Field(
            description="Helm repository definitions",
        ),
    ] = {}

    oci_registries: Annotated[
        dict[str, OciRepoScheme | str],
        Field(
            description="OCI registry configurations",
        ),
    ] = {}

    git_repos: Annotated[
        dict[str, GitRepoScheme | str],
        Field(
            description="Git repository configurations",
        ),
    ] = {}

    # ---- Label Injection Settings ----
    helm_label_injection: Annotated[
        bool,
        Field(
            description="Enable automatic label injection for Helm charts",
        ),
    ] = True

    incompatible_charts: Annotated[
        list[str],
        Field(
            description="Charts that don't support commonLabels/commonAnnotations",
        ),
    ] = []

    force_label_injection: Annotated[
        list[str],
        Field(
            description="Charts to force enable label injection",
        ),
    ] = []

    # ---- Execution Settings ----
    execution_order: Annotated[
        Literal["apps_first", "phases_first"],
        Field(
            description="Execution order when both apps and phases are defined",
        ),
    ] = "apps_first"

    parallel: Annotated[
        bool,
        Field(
            description="Execute independent phases in parallel",
        ),
    ] = False

    parallel_apps: Annotated[
        bool,
        Field(
            description="Execute app groups in parallel within phases",
        ),
    ] = False

    max_workers: Annotated[
        int,
        Field(
            ge=1,
            le=32,
            description="Maximum parallel workers",
        ),
    ] = 4

    # ---- Failure Handling ----
    on_failure: Annotated[
        Literal["stop", "continue", "rollback"],
        Field(
            description="Behavior when deployment fails",
        ),
    ] = "stop"

    rollback_scope: Annotated[
        Literal["app", "phase", "all"],
        Field(
            description="Scope of rollback on failure",
        ),
    ] = "app"

    # ---- Timeouts ----
    timeout: Annotated[
        int,
        Field(
            ge=1,
            le=3600,
            description="Default timeout for operations (seconds)",
        ),
    ] = 600

    # ---- Proxy Settings ----
    http_proxy: Annotated[
        str | None,
        Field(
            description="HTTP proxy URL",
        ),
    ] = None

    https_proxy: Annotated[
        str | None,
        Field(
            description="HTTPS proxy URL",
        ),
    ] = None

    no_proxy: Annotated[
        list[str] | None,
        Field(
            description="Hosts to exclude from proxy",
        ),
    ] = None

    # ---- Cleanup Settings ----
    cleanup_metadata: Annotated[
        bool,
        Field(
            description="Auto-remove server-managed metadata fields",
        ),
    ] = True

    # ---- Global Values ----
    cluster_values_file: Annotated[
        str | None,
        Field(
            description="Path to cluster-level values YAML file",
        ),
    ] = None

    global_values: Annotated[
        dict[str, Any] | None,
        Field(
            description="Inline global values for all apps",
        ),
    ] = None

    @field_validator("helm_repos", mode="before")
    @classmethod
    def normalize_helm_repos(cls, v: Any) -> dict[str, Any]:
        """Normalize helm_repos to support string shorthand format."""
        if not isinstance(v, dict):
            return v
        normalized = {}
        for name, value in v.items():
            if isinstance(value, str):
                normalized[name] = {"url": value}
            else:
                normalized[name] = value
        return normalized

    @field_validator("oci_registries", mode="before")
    @classmethod
    def normalize_oci_registries(cls, v: Any) -> dict[str, Any]:
        """Normalize oci_registries to support string shorthand format."""
        if not isinstance(v, dict):
            return v
        normalized = {}
        for name, value in v.items():
            if isinstance(value, str):
                normalized[name] = {"registry": value}
            else:
                normalized[name] = value
        return normalized

    @field_validator("git_repos", mode="before")
    @classmethod
    def normalize_git_repos(cls, v: Any) -> dict[str, Any]:
        """Normalize git_repos to support string shorthand format."""
        if not isinstance(v, dict):
            return v
        normalized = {}
        for name, value in v.items():
            if isinstance(value, str):
                normalized[name] = {"url": value}
            else:
                normalized[name] = value
        return normalized


# ============================================================================
# Phase Reference
# ============================================================================


class PhaseReference(ConfigBaseModel):
    """Reference to a phase configuration.

    Phases can be:
    1. Inline: Apps defined directly in the phase
    2. External: Reference to another sbkube.yaml file

    Examples:
        # External reference
        phases:
          p1-infra:
            source: p1-kube/sbkube.yaml
            depends_on: []

        # Inline definition
        phases:
          p1-infra:
            description: "Infrastructure"
            apps:
              nginx:
                type: helm
                chart: bitnami/nginx

    """

    description: Annotated[
        str | None,
        Field(
            description="Phase description",
        ),
    ] = None

    source: Annotated[
        str | None,
        Field(
            description="Path to external sbkube.yaml (relative to parent)",
        ),
    ] = None

    depends_on: Annotated[
        list[str],
        Field(
            description="Phase dependencies",
        ),
    ] = []

    # Settings override for this phase
    settings: Annotated[
        UnifiedSettings | None,
        Field(
            description="Phase-specific settings (overrides global)",
        ),
    ] = None

    # Inline apps (alternative to source)
    apps: Annotated[
        dict[str, AppConfig],
        Field(
            description="Inline app definitions",
        ),
    ] = {}

    # App group dependencies for parallel execution
    app_group_deps: Annotated[
        dict[str, list[str]],
        Field(
            description="Dependencies between app groups within this phase",
        ),
    ] = {}

    @model_validator(mode="after")
    def validate_source_or_apps(self) -> "PhaseReference":
        """Validate that either source or apps is defined (not both)."""
        has_source = self.source is not None
        has_apps = len(self.apps) > 0

        if has_source and has_apps:
            msg = "Phase cannot have both 'source' and 'apps' defined"
            raise ValueError(msg)

        if not has_source and not has_apps:
            msg = "Phase must have either 'source' or 'apps' defined"
            raise ValueError(msg)

        return self


# ============================================================================
# Unified Config (Main Model)
# ============================================================================


class UnifiedConfig(ConfigBaseModel):
    """Unified configuration model for sbkube.yaml.

    This is the single-file configuration format that consolidates:
    - Cluster settings (from sources.yaml)
    - App definitions (from config.yaml)
    - Phase orchestration (from workspace.yaml)

    Examples:
        apiVersion: sbkube/v1

        metadata:
          name: my-deployment
          environment: prod

        settings:
          kubeconfig: ~/.kube/config
          kubeconfig_context: prod-cluster
          namespace: production

        apps:
          nginx:
            type: helm
            chart: bitnami/nginx
            version: 15.0.0

        phases:
          p1-infra:
            source: p1-kube/sbkube.yaml
          p2-app:
            depends_on: [p1-infra]
            apps:
              backend:
                type: helm
                chart: my-org/backend

    """

    apiVersion: Annotated[
        str,
        Field(
            description="API version (sbkube/v1)",
            pattern=r"^sbkube/v\d+$",
        ),
    ] = "sbkube/v1"

    metadata: Annotated[
        dict[str, Any],
        Field(
            description="Configuration metadata",
        ),
    ] = {}

    settings: Annotated[
        UnifiedSettings,
        Field(
            description="Global settings",
        ),
    ] = UnifiedSettings()

    apps: Annotated[
        dict[str, AppConfig],
        Field(
            description="App definitions (executed directly)",
        ),
    ] = {}

    phases: Annotated[
        dict[str, PhaseReference],
        Field(
            description="Phase definitions (for multi-phase deployment)",
        ),
    ] = {}

    # App group dependencies (same level as deps in SBKubeConfig)
    deps: Annotated[
        list[str],
        Field(
            description="App group dependencies",
        ),
    ] = []

    @field_validator("metadata", mode="before")
    @classmethod
    def ensure_metadata_name(cls, v: dict[str, Any] | None) -> dict[str, Any]:
        """Ensure metadata has at least a name field."""
        if v is None:
            return {"name": "unnamed"}
        if "name" not in v:
            v["name"] = "unnamed"
        return v

    @model_validator(mode="after")
    def validate_phase_dependencies(self) -> "UnifiedConfig":
        """Validate phase dependencies exist and detect cycles."""
        if not self.phases:
            return self

        phase_names = set(self.phases.keys())

        # Check all dependencies exist
        for phase_name, phase in self.phases.items():
            for dep in phase.depends_on:
                if dep not in phase_names:
                    msg = f"Phase '{phase_name}' depends on non-existent phase '{dep}'"
                    raise ValueError(msg)

        # Detect circular dependencies
        visited = set()
        rec_stack = set()

        def has_cycle(node: str) -> bool:
            visited.add(node)
            rec_stack.add(node)

            for dep in self.phases[node].depends_on:
                if dep not in visited:
                    if has_cycle(dep):
                        return True
                elif dep in rec_stack:
                    return True

            rec_stack.remove(node)
            return False

        for phase_name in self.phases:
            if phase_name not in visited and has_cycle(phase_name):
                msg = f"Circular dependency detected involving phase '{phase_name}'"
                raise ValueError(msg)

        return self

    @model_validator(mode="after")
    def validate_apps_namespace(self) -> "UnifiedConfig":
        """Apply namespace inheritance to apps."""
        default_namespace = self.settings.namespace

        for app in self.apps.values():
            if hasattr(app, "namespace") and app.namespace is None:
                app.namespace = default_namespace

        return self

    def get_phase_order(self) -> list[str]:
        """Get phase execution order using topological sort.

        Returns:
            List of phase names in execution order.

        """
        if not self.phases:
            return []

        in_degree = {name: 0 for name in self.phases}
        graph = {name: [] for name in self.phases}

        for name, phase in self.phases.items():
            for dep in phase.depends_on:
                graph[dep].append(name)
                in_degree[name] += 1

        # Kahn's algorithm
        queue = [name for name, degree in in_degree.items() if degree == 0]
        result = []

        while queue:
            queue.sort()  # Consistent ordering
            node = queue.pop(0)
            result.append(node)

            for neighbor in graph[node]:
                in_degree[neighbor] -= 1
                if in_degree[neighbor] == 0:
                    queue.append(neighbor)

        return result

    def get_enabled_apps(self) -> dict[str, AppConfig]:
        """Get enabled apps from the config."""
        return {name: app for name, app in self.apps.items() if app.enabled}

    def resolve_source_path(self, phase_name: str, base_dir: Path) -> Path | None:
        """Resolve the source path for a phase.

        Args:
            phase_name: Name of the phase
            base_dir: Base directory for resolution

        Returns:
            Resolved path or None if phase has inline apps

        """
        phase = self.phases.get(phase_name)
        if not phase or not phase.source:
            return None

        return (base_dir / phase.source).resolve()

    @classmethod
    def from_legacy_files(
        cls,
        sources_path: Path | None = None,
        config_path: Path | None = None,
        workspace_path: Path | None = None,
    ) -> "UnifiedConfig":
        """Create UnifiedConfig from legacy configuration files.

        This method supports backward compatibility by converting legacy
        files (sources.yaml, config.yaml, workspace.yaml) to the unified format.

        Args:
            sources_path: Path to sources.yaml
            config_path: Path to config.yaml
            workspace_path: Path to workspace.yaml

        Returns:
            UnifiedConfig instance

        """
        from sbkube.models.config_model import SBKubeConfig
        from sbkube.models.sources_model import SourceScheme
        from sbkube.models.workspace_model import WorkspaceConfig

        settings_data: dict[str, Any] = {}
        apps_data: dict[str, AppConfig] = {}
        phases_data: dict[str, PhaseReference] = {}
        metadata_data: dict[str, Any] = {"name": "converted"}

        # Load sources.yaml
        if sources_path and sources_path.exists():
            sources = SourceScheme.from_yaml(sources_path)
            settings_data.update({
                "kubeconfig": sources.kubeconfig,
                "kubeconfig_context": sources.kubeconfig_context,
                "cluster": sources.cluster,
                "helm_repos": {
                    k: v.model_dump() for k, v in sources.helm_repos.items()
                },
                "oci_registries": {
                    k: v.model_dump() for k, v in sources.oci_registries.items()
                },
                "git_repos": {
                    k: v.model_dump() for k, v in sources.git_repos.items()
                },
                "incompatible_charts": sources.incompatible_charts,
                "force_label_injection": sources.force_label_injection,
                "cluster_values_file": sources.cluster_values_file,
                "global_values": sources.global_values,
                "cleanup_metadata": sources.cleanup_metadata,
                "http_proxy": sources.http_proxy,
                "https_proxy": sources.https_proxy,
                "no_proxy": sources.no_proxy,
            })

        # Load config.yaml
        if config_path and config_path.exists():
            config = SBKubeConfig.from_yaml(config_path)
            settings_data["namespace"] = config.namespace
            apps_data = config.apps

        # Load workspace.yaml
        if workspace_path and workspace_path.exists():
            workspace = WorkspaceConfig.from_yaml(workspace_path)
            metadata_data = {
                "name": workspace.metadata.name,
                "description": workspace.metadata.description,
                "environment": workspace.metadata.environment,
                "tags": workspace.metadata.tags,
            }

            # Convert global config
            global_cfg = workspace.global_config
            settings_data.update({
                "kubeconfig": global_cfg.kubeconfig or settings_data.get("kubeconfig"),
                "kubeconfig_context": (
                    global_cfg.context or settings_data.get("kubeconfig_context")
                ),
                "timeout": global_cfg.timeout,
                "on_failure": global_cfg.on_failure,
            })

            # Convert phases
            for phase_name, phase_cfg in workspace.phases.items():
                phases_data[phase_name] = PhaseReference(
                    description=phase_cfg.description,
                    source=phase_cfg.source,
                    depends_on=phase_cfg.depends_on,
                    app_group_deps=phase_cfg.app_group_deps,
                )

        return cls(
            metadata=metadata_data,
            settings=UnifiedSettings(**settings_data),
            apps=apps_data,
            phases=phases_data,
        )
