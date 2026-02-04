"""Workspace Configuration Models for Multi-Phase Deployment.

이 모듈은 sbkube.yaml (unified format)의 Pydantic 모델을 정의합니다.
Phase 기반 다단계 배포를 지원합니다.

Schema Version: 1.0
Target SBKube Version: v0.10.0

Related Documentation:
- User Guide: docs/03-configuration/workspace-schema.md
- Design: docs/02-features/future/workspace-design.md
- Roadmap: docs/02-features/future/workspace-roadmap.md
"""

from pathlib import Path
from typing import Annotated, Any, Literal

from pydantic import Field, field_validator, model_validator

from .base_model import ConfigBaseModel


# ============================================================================
# Git Repository Model
# ============================================================================


class GitRepoConfig(ConfigBaseModel):
    """Git repository configuration."""

    url: str
    branch: str = "main"
    tag: str | None = None

# ============================================================================
# Workspace Models
# ============================================================================


class WorkspaceMetadata(ConfigBaseModel):
    """Workspace 메타데이터.

    Examples:
        metadata:
          name: production-deployment
          description: "Production infrastructure deployment"
          environment: prod
          version: "1.0.0"
          tags:
            - production
            - multi-phase

    """

    name: Annotated[
        str,
        Field(
            description="Workspace name (alphanumeric + dash/underscore)",
            pattern=r"^[a-zA-Z0-9][a-zA-Z0-9_-]*$",
        ),
    ]

    description: Annotated[
        str | None,
        Field(
            description="Human-readable description",
        ),
    ] = None

    environment: Annotated[
        str | None,
        Field(
            description="Environment label (dev, staging, prod, etc.)",
        ),
    ] = None

    version: Annotated[
        str | None,
        Field(
            description="Workspace version (e.g., 1.0.0)",
        ),
    ] = None

    tags: Annotated[
        list[str],
        Field(
            description="Tags for categorization",
        ),
    ] = []


class GlobalDefaults(ConfigBaseModel):
    """Workspace 전역 기본값 (settings 섹션).

    모든 Phase에 적용되는 기본 설정입니다.
    Phase-level 설정으로 오버라이드 가능합니다.

    Examples:
        settings:
          kubeconfig: ~/.kube/config
          kubeconfig_context: production-cluster
          timeout: 600
          on_failure: stop
          helm_repos:
            grafana: https://grafana.github.io/helm-charts

    """

    kubeconfig: Annotated[
        str | None,
        Field(
            description="Default kubeconfig path for all phases",
        ),
    ] = None

    kubeconfig_context: Annotated[
        str | None,
        Field(
            description="Default kubectl context for all phases",
        ),
    ] = None

    # Alias for backward compatibility
    context: Annotated[
        str | None,
        Field(
            description="Alias for kubeconfig_context (deprecated)",
        ),
    ] = None

    helm_repos: Annotated[
        dict[str, str],
        Field(
            description="Global Helm repository definitions (name: url)",
        ),
    ] = {}

    oci_registries: Annotated[
        dict[str, str],
        Field(
            description="Global OCI registry configurations (name: url)",
        ),
    ] = {}

    git_repos: Annotated[
        dict[str, GitRepoConfig | dict[str, Any]],
        Field(
            description="Global Git repository definitions",
        ),
    ] = {}

    git_credentials: Annotated[
        dict[str, dict[str, Any]],
        Field(
            description="Global Git repository credentials",
        ),
    ] = {}

    timeout: Annotated[
        int,
        Field(
            default=600,
            ge=1,
            le=7200,
            description="Default timeout for operations (seconds)",
        ),
    ] = 600

    on_failure: Annotated[
        Literal["stop", "continue", "rollback"],
        Field(
            default="stop",
            description="Default behavior on failure",
        ),
    ] = "stop"


class PhaseSettings(ConfigBaseModel):
    """Phase-specific settings (optional override)."""

    timeout: Annotated[
        int | None,
        Field(
            ge=1,
            le=7200,
            description="Phase-specific timeout (overrides global)",
        ),
    ] = None

    on_failure: Annotated[
        Literal["stop", "continue", "rollback"] | None,
        Field(
            description="Phase-specific failure behavior (overrides global)",
        ),
    ] = None


class PhaseConfig(ConfigBaseModel):
    """Phase 설정.

    단일 Phase의 배포 설정을 정의합니다.
    source는 하위 sbkube.yaml 파일을 가리킵니다 (계층적 구조).

    Examples:
        ph1-infra:
          description: "Network and storage infrastructure"
          source: ph1_infra/sbkube.yaml
          enabled: true
          settings:
            timeout: 1200
            on_failure: stop
          depends_on: []

    """

    description: Annotated[
        str,
        Field(
            description="Phase description",
        ),
    ]

    source: Annotated[
        str,
        Field(
            description="Path to phase sbkube.yaml (relative to workspace root)",
        ),
    ]

    enabled: Annotated[
        bool,
        Field(
            description="Whether this phase is enabled (default: true)",
        ),
    ] = True

    # app_groups is optional - if not provided, will be auto-discovered from source
    app_groups: Annotated[
        list[str],
        Field(
            description="List of app groups to deploy (optional, auto-discovered if not set)",
        ),
    ] = []

    depends_on: Annotated[
        list[str],
        Field(
            description="Phase dependencies (must complete before this phase)",
        ),
    ] = []

    settings: Annotated[
        PhaseSettings | None,
        Field(
            description="Phase-specific settings",
        ),
    ] = None

    # Flat fields for backward compatibility
    timeout: Annotated[
        int | None,
        Field(
            ge=1,
            le=7200,
            description="Phase-specific timeout (overrides global)",
        ),
    ] = None

    on_failure: Annotated[
        Literal["stop", "continue", "rollback"] | None,
        Field(
            description="Phase-specific failure behavior (overrides global)",
        ),
    ] = None

    env: Annotated[
        dict[str, str],
        Field(
            description="Phase-level environment variables",
        ),
    ] = {}

    app_group_deps: Annotated[
        dict[str, list[str]],
        Field(
            description="App group dependencies within this phase. "
            "Format: {app_group: [depends_on_groups]}. "
            "Groups without dependencies can run in parallel.",
        ),
    ] = {}

    @model_validator(mode="after")
    def merge_settings(self) -> "PhaseConfig":
        """Merge nested settings into flat fields."""
        if self.settings:
            if self.settings.timeout and not self.timeout:
                self.timeout = self.settings.timeout
            if self.settings.on_failure and not self.on_failure:
                self.on_failure = self.settings.on_failure
        return self

    @field_validator("app_groups")
    @classmethod
    def validate_app_groups(cls, v: list[str]) -> list[str]:
        """앱 그룹 이름 검증.

        Empty list is allowed - app_groups will be auto-discovered from source.
        """
        # Empty list is OK - will auto-discover from source
        if not v:
            return v

        for group in v:
            if not group:
                raise ValueError("app_group name cannot be empty")
            # 앱 그룹 이름 패턴: alphanumeric + dash/underscore
            if not all(c.isalnum() or c in "_-" for c in group):
                raise ValueError(
                    f"Invalid app_group name '{group}': "
                    "must contain only alphanumeric, dash, underscore"
                )

        return v

    @model_validator(mode="after")
    def validate_app_group_deps(self) -> "PhaseConfig":
        """App group 의존성 검증.

        1. 참조된 app_group이 app_groups에 존재하는지 확인
        2. 순환 의존성 감지
        """
        # Skip validation if app_group_deps is empty or app_groups is empty
        if not self.app_group_deps or not self.app_groups:
            return self

        app_group_set = set(self.app_groups)

        # 존재하지 않는 app_group 참조 확인
        for group, deps in self.app_group_deps.items():
            if group not in app_group_set:
                raise ValueError(
                    f"app_group_deps references non-existent app_group '{group}'"
                )
            for dep in deps:
                if dep not in app_group_set:
                    raise ValueError(
                        f"app_group '{group}' depends on non-existent app_group '{dep}'"
                    )

        # 순환 의존성 감지 (DFS)
        visited = set()
        rec_stack = set()

        def has_cycle(node: str) -> bool:
            visited.add(node)
            rec_stack.add(node)

            for dep in self.app_group_deps.get(node, []):
                if dep not in visited:
                    if has_cycle(dep):
                        return True
                elif dep in rec_stack:
                    return True

            rec_stack.remove(node)
            return False

        for group in self.app_group_deps:
            if group not in visited:
                if has_cycle(group):
                    raise ValueError(
                        f"Circular dependency detected in app_group_deps involving '{group}'"
                    )

        return self

    def get_app_group_order(self) -> list[list[str]]:
        """App group 실행 순서를 레벨별로 반환.

        의존성을 기반으로 병렬 실행 가능한 그룹들을 레벨로 구분합니다.

        Returns:
            레벨별 app_group 리스트. 같은 레벨의 그룹들은 병렬 실행 가능.

        """
        if not self.app_group_deps:
            # 의존성이 없으면 모든 app_groups를 한 레벨로 (모두 병렬 가능)
            return [self.app_groups]

        # In-degree 계산
        in_degree = {group: 0 for group in self.app_groups}
        for group, deps in self.app_group_deps.items():
            in_degree[group] = len(deps)

        levels = []
        remaining = set(self.app_groups)

        while remaining:
            # 현재 레벨: in_degree가 0인 그룹들
            current_level = [
                g for g in self.app_groups
                if g in remaining and in_degree.get(g, 0) == 0
            ]

            if not current_level:
                # 더 이상 처리할 수 없으면 나머지를 순차로
                current_level = [g for g in self.app_groups if g in remaining]
                levels.append(current_level)
                break

            levels.append(current_level)

            # 처리된 그룹 제거 및 in_degree 갱신
            for group in current_level:
                remaining.remove(group)
                # 이 그룹에 의존하는 다른 그룹들의 in_degree 감소
                for other_group, deps in self.app_group_deps.items():
                    if group in deps and other_group in remaining:
                        in_degree[other_group] -= 1

        return levels


class WorkspaceConfig(ConfigBaseModel):
    """Workspace 설정 (sbkube.yaml unified format).

    Multi-phase deployment 설정의 최상위 모델입니다.

    Examples:
        apiVersion: sbkube/v1
        metadata:
          name: production-deployment
          environment: prod
          version: "1.0.0"
        settings:
          kubeconfig: ~/.kube/config
          kubeconfig_context: production-cluster
          helm_repos:
            grafana: https://grafana.github.io/helm-charts
        phases:
          ph1-infra:
            description: "Infrastructure"
            source: ph1_infra/sbkube.yaml
            depends_on: []
          ph2-data:
            description: "Data layer"
            source: ph2_data/sbkube.yaml
            depends_on: [ph1-infra]

    """

    api_version: Annotated[
        str,
        Field(
            alias="apiVersion",
            description="API version (sbkube/v1)",
        ),
    ] = "sbkube/v1"

    # Legacy version field (optional, prefer metadata.version)
    version: Annotated[
        str | None,
        Field(
            description="Schema version (legacy, use metadata.version instead)",
        ),
    ] = None

    metadata: Annotated[
        WorkspaceMetadata,
        Field(
            description="Workspace metadata",
        ),
    ]

    # Support both "settings" and "global" (legacy)
    settings: Annotated[
        GlobalDefaults,
        Field(
            description="Global settings for all phases",
        ),
    ] = GlobalDefaults()

    global_config: Annotated[
        GlobalDefaults | None,
        Field(
            alias="global",
            description="Global defaults (legacy, use 'settings' instead)",
        ),
    ] = None

    phases: Annotated[
        dict[str, PhaseConfig],
        Field(
            min_length=1,
            description="Phase definitions (ordered map)",
        ),
    ]

    @model_validator(mode="after")
    def merge_global_to_settings(self) -> "WorkspaceConfig":
        """Merge legacy 'global' into 'settings'."""
        if self.global_config and not self.settings.kubeconfig:
            # Copy global_config values to settings if not already set
            if self.global_config.kubeconfig:
                self.settings.kubeconfig = self.global_config.kubeconfig
            if self.global_config.kubeconfig_context:
                self.settings.kubeconfig_context = self.global_config.kubeconfig_context
            if self.global_config.context:
                self.settings.kubeconfig_context = self.global_config.context
            if self.global_config.helm_repos:
                self.settings.helm_repos = self.global_config.helm_repos
            if self.global_config.timeout != 600:
                self.settings.timeout = self.global_config.timeout
            if self.global_config.on_failure != "stop":
                self.settings.on_failure = self.global_config.on_failure
        return self

    @field_validator("phases")
    @classmethod
    def validate_phases(cls, v: dict[str, PhaseConfig]) -> dict[str, PhaseConfig]:
        """Phase 검증."""
        if not v:
            raise ValueError("phases must not be empty")

        # Phase 이름 검증
        for phase_name in v:
            if not phase_name:
                raise ValueError("phase name cannot be empty")
            # Phase 이름 패턴: alphanumeric + dash/underscore
            if not all(c.isalnum() or c in "_-" for c in phase_name):
                raise ValueError(
                    f"Invalid phase name '{phase_name}': "
                    "must contain only alphanumeric, dash, underscore"
                )

        return v

    @model_validator(mode="after")
    def validate_phase_dependencies(self) -> "WorkspaceConfig":
        """Phase 의존성 검증.

        1. 순환 의존성 감지
        2. 존재하지 않는 Phase 참조 감지
        """
        phase_names = set(self.phases.keys())

        # 존재하지 않는 Phase 참조 확인
        for phase_name, phase_config in self.phases.items():
            for dep in phase_config.depends_on:
                if dep not in phase_names:
                    raise ValueError(
                        f"Phase '{phase_name}' depends on non-existent phase '{dep}'"
                    )

        # 순환 의존성 감지 (Kahn's algorithm 준비)
        visited = set()
        rec_stack = set()

        def has_cycle(node: str) -> bool:
            """DFS로 순환 의존성 감지."""
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

        for phase_name in phase_names:
            if phase_name not in visited:
                if has_cycle(phase_name):
                    raise ValueError(
                        f"Circular dependency detected involving phase '{phase_name}'"
                    )

        return self

    def get_phase_order(self) -> list[str]:
        """Phase 실행 순서 반환.

        Kahn's algorithm을 사용하여 위상 정렬합니다.

        Returns:
            Phase 이름 리스트 (실행 순서대로)

        Raises:
            ValueError: 순환 의존성이 있는 경우

        """
        # In-degree 계산: 각 노드가 몇 개의 의존성을 가지는지
        in_degree = dict.fromkeys(self.phases.keys(), 0)
        for phase_name, phase_config in self.phases.items():
            for dep in phase_config.depends_on:
                in_degree[phase_name] = in_degree.get(phase_name, 0) + 1

        # In-degree가 0인 노드부터 시작 (의존성이 없는 Phase)
        queue = [phase for phase, degree in in_degree.items() if degree == 0]
        result = []

        while queue:
            # YAML 순서 유지를 위해 정렬하지 않음
            node = queue.pop(0)
            result.append(node)

            # 이 노드에 의존하는 다른 노드들의 in-degree 감소
            for phase_name, phase_config in self.phases.items():
                if node in phase_config.depends_on:
                    in_degree[phase_name] -= 1
                    if in_degree[phase_name] == 0:
                        queue.append(phase_name)

        # 모든 노드가 처리되었는지 확인
        if len(result) != len(self.phases):
            raise ValueError("Circular dependency detected in phases")

        return result

    def get_phase_config(self, phase_name: str) -> PhaseConfig:
        """Phase 설정 조회.

        Args:
            phase_name: Phase 이름

        Returns:
            PhaseConfig

        Raises:
            KeyError: Phase가 존재하지 않는 경우

        """
        if phase_name not in self.phases:
            raise KeyError(f"Phase '{phase_name}' not found")

        return self.phases[phase_name]

    def resolve_source_path(
        self, phase_name: str, workspace_dir: Path
    ) -> Path:
        """Phase의 sources.yaml 절대 경로 반환.

        Args:
            phase_name: Phase 이름
            workspace_dir: workspace.yaml이 있는 디렉토리

        Returns:
            sources.yaml의 절대 경로

        Raises:
            KeyError: Phase가 존재하지 않는 경우

        """
        phase_config = self.get_phase_config(phase_name)
        source_path = workspace_dir / phase_config.source

        return source_path.resolve()
