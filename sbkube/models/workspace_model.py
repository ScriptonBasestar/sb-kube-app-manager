"""Workspace Configuration Models for Multi-Phase Deployment.

이 모듈은 workspace.yaml의 Pydantic 모델을 정의합니다.
Phase 기반 다단계 배포를 지원합니다.

Schema Version: 1.0
Target SBKube Version: v0.9.0

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
# Workspace Models
# ============================================================================


class WorkspaceMetadata(ConfigBaseModel):
    """Workspace 메타데이터.

    Examples:
        metadata:
          name: production-deployment
          description: "Production infrastructure deployment"
          environment: prod
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

    tags: Annotated[
        list[str],
        Field(
            description="Tags for categorization",
        ),
    ] = []


class GlobalDefaults(ConfigBaseModel):
    """Workspace 전역 기본값.

    모든 Phase에 적용되는 기본 설정입니다.
    Phase-level 설정으로 오버라이드 가능합니다.

    Examples:
        global:
          kubeconfig: ~/.kube/config
          context: production-cluster
          timeout: 600
          on_failure: stop
          helm_repos:
            grafana:
              url: https://grafana.github.io/helm-charts
    """

    kubeconfig: Annotated[
        str | None,
        Field(
            description="Default kubeconfig path for all phases",
        ),
    ] = None

    context: Annotated[
        str | None,
        Field(
            description="Default kubectl context for all phases",
        ),
    ] = None

    helm_repos: Annotated[
        dict[str, dict[str, Any]],
        Field(
            description="Global Helm repository definitions",
        ),
    ] = {}

    oci_registries: Annotated[
        dict[str, dict[str, Any]],
        Field(
            description="Global OCI registry configurations",
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
            le=3600,
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


class PhaseConfig(ConfigBaseModel):
    """Phase 설정.

    단일 Phase의 배포 설정을 정의합니다.

    Examples:
        p1-infra:
          description: "Network and storage infrastructure"
          source: p1-kube/sources.yaml
          app_groups:
            - a000_network
            - a001_storage
          depends_on: []
          timeout: 900
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
            description="Path to sources.yaml (relative to workspace.yaml)",
        ),
    ]

    app_groups: Annotated[
        list[str],
        Field(
            min_length=1,
            description="List of app groups to deploy in this phase",
        ),
    ]

    depends_on: Annotated[
        list[str],
        Field(
            description="Phase dependencies (must complete before this phase)",
        ),
    ] = []

    timeout: Annotated[
        int | None,
        Field(
            ge=1,
            le=3600,
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

    @field_validator("app_groups")
    @classmethod
    def validate_app_groups(cls, v: list[str]) -> list[str]:
        """앱 그룹 이름 검증."""
        if not v:
            raise ValueError("app_groups must not be empty")

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


class WorkspaceConfig(ConfigBaseModel):
    """Workspace 설정.

    Multi-phase deployment 설정의 최상위 모델입니다.

    Examples:
        version: "1.0"
        metadata:
          name: production-deployment
          environment: prod
        global:
          kubeconfig: ~/.kube/config
          context: production-cluster
        phases:
          p1-infra:
            description: "Infrastructure"
            source: p1-kube/sources.yaml
            app_groups: [a000_network]
          p2-data:
            description: "Data layer"
            source: p2-kube/sources.yaml
            app_groups: [a100_postgres]
            depends_on: [p1-infra]
    """

    version: Annotated[
        str,
        Field(
            description="Workspace schema version",
            pattern=r"^\d+\.\d+$",
        ),
    ]

    metadata: Annotated[
        WorkspaceMetadata,
        Field(
            description="Workspace metadata",
        ),
    ]

    global_config: Annotated[
        GlobalDefaults,
        Field(
            alias="global",
            description="Global defaults for all phases",
        ),
    ] = GlobalDefaults()

    phases: Annotated[
        dict[str, PhaseConfig],
        Field(
            min_length=1,
            description="Phase definitions (ordered map)",
        ),
    ]

    @field_validator("version")
    @classmethod
    def validate_version(cls, v: str) -> str:
        """버전 검증."""
        if not v:
            raise ValueError("version is required")

        # 버전 형식: "1.0", "2.3" 등
        parts = v.split(".")
        if len(parts) != 2:
            raise ValueError("version must be in format 'major.minor' (e.g., '1.0')")

        major, minor = parts
        if not major.isdigit() or not minor.isdigit():
            raise ValueError("version must contain only digits")

        return v

    @field_validator("phases")
    @classmethod
    def validate_phases(cls, v: dict[str, PhaseConfig]) -> dict[str, PhaseConfig]:
        """Phase 검증."""
        if not v:
            raise ValueError("phases must not be empty")

        # Phase 이름 검증
        for phase_name in v.keys():
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
