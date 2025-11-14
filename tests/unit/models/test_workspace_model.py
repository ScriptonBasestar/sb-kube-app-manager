"""Workspace models 테스트."""

from pathlib import Path

import pytest

from sbkube.exceptions import ConfigValidationError
from sbkube.models.workspace_model import (
    GlobalDefaults,
    PhaseConfig,
    WorkspaceConfig,
    WorkspaceMetadata,
)


class TestWorkspaceMetadata:
    """WorkspaceMetadata 테스트."""

    def test_valid_metadata(self) -> None:
        """유효한 메타데이터 테스트."""
        metadata = WorkspaceMetadata(
            name="production-deployment",
            description="Production infrastructure",
            environment="prod",
            tags=["production", "multi-phase"],
        )

        assert metadata.name == "production-deployment"
        assert metadata.description == "Production infrastructure"
        assert metadata.environment == "prod"
        assert metadata.tags == ["production", "multi-phase"]

    def test_minimal_metadata(self) -> None:
        """최소 필수 필드만 있는 메타데이터 테스트."""
        metadata = WorkspaceMetadata(name="simple-workspace")

        assert metadata.name == "simple-workspace"
        assert metadata.description is None
        assert metadata.environment is None
        assert metadata.tags == []

    def test_invalid_name_pattern(self) -> None:
        """잘못된 이름 패턴 테스트."""
        with pytest.raises(ConfigValidationError):
            WorkspaceMetadata(name="invalid name with spaces")

        with pytest.raises(ConfigValidationError):
            WorkspaceMetadata(name="invalid@name")


class TestGlobalDefaults:
    """GlobalDefaults 테스트."""

    def test_default_values(self) -> None:
        """기본값 테스트."""
        defaults = GlobalDefaults()

        assert defaults.kubeconfig is None
        assert defaults.context is None
        assert defaults.helm_repos == {}
        assert defaults.timeout == 600
        assert defaults.on_failure == "stop"

    def test_custom_values(self) -> None:
        """커스텀 값 테스트."""
        defaults = GlobalDefaults(
            kubeconfig="~/.kube/config",
            context="prod-cluster",
            timeout=900,
            on_failure="rollback",
            helm_repos={
                "grafana": {"url": "https://grafana.github.io/helm-charts"}
            },
        )

        assert defaults.kubeconfig == "~/.kube/config"
        assert defaults.context == "prod-cluster"
        assert defaults.timeout == 900
        assert defaults.on_failure == "rollback"
        assert "grafana" in defaults.helm_repos


class TestPhaseConfig:
    """PhaseConfig 테스트."""

    def test_valid_phase(self) -> None:
        """유효한 Phase 설정 테스트."""
        phase = PhaseConfig(
            description="Infrastructure phase",
            source="p1-kube/sources.yaml",
            app_groups=["a000_network", "a001_storage"],
            depends_on=[],
            timeout=900,
        )

        assert phase.description == "Infrastructure phase"
        assert phase.source == "p1-kube/sources.yaml"
        assert phase.app_groups == ["a000_network", "a001_storage"]
        assert phase.depends_on == []
        assert phase.timeout == 900

    def test_minimal_phase(self) -> None:
        """최소 필수 필드만 있는 Phase 테스트."""
        phase = PhaseConfig(
            description="Simple phase",
            source="config/sources.yaml",
            app_groups=["app1"],
        )

        assert phase.app_groups == ["app1"]
        assert phase.depends_on == []
        assert phase.timeout is None
        assert phase.on_failure is None
        assert phase.env == {}

    def test_empty_app_groups(self) -> None:
        """빈 app_groups 테스트."""
        with pytest.raises(ConfigValidationError):
            PhaseConfig(
                description="Invalid phase",
                source="sources.yaml",
                app_groups=[],
            )

    def test_invalid_app_group_name(self) -> None:
        """잘못된 app_group 이름 테스트."""
        with pytest.raises(ConfigValidationError):
            PhaseConfig(
                description="Invalid phase",
                source="sources.yaml",
                app_groups=["invalid group name"],
            )


class TestWorkspaceConfig:
    """WorkspaceConfig 테스트."""

    def test_valid_workspace(self) -> None:
        """유효한 Workspace 설정 테스트."""
        workspace = WorkspaceConfig(
            version="1.0",
            metadata=WorkspaceMetadata(name="test-workspace"),
            phases={
                "p1-infra": PhaseConfig(
                    description="Infrastructure",
                    source="p1-kube/sources.yaml",
                    app_groups=["a000_network"],
                ),
                "p2-data": PhaseConfig(
                    description="Data layer",
                    source="p2-kube/sources.yaml",
                    app_groups=["a100_postgres"],
                    depends_on=["p1-infra"],
                ),
            },
        )

        assert workspace.version == "1.0"
        assert workspace.metadata.name == "test-workspace"
        assert len(workspace.phases) == 2
        assert "p1-infra" in workspace.phases
        assert "p2-data" in workspace.phases

    def test_invalid_version_format(self) -> None:
        """잘못된 버전 형식 테스트."""
        with pytest.raises(ConfigValidationError):
            WorkspaceConfig(
                version="1",  # 잘못된 형식
                metadata=WorkspaceMetadata(name="test"),
                phases={
                    "p1": PhaseConfig(
                        description="Test",
                        source="sources.yaml",
                        app_groups=["app1"],
                    )
                },
            )

    def test_empty_phases(self) -> None:
        """빈 phases 테스트."""
        with pytest.raises(ConfigValidationError):
            WorkspaceConfig(
                version="1.0",
                metadata=WorkspaceMetadata(name="test"),
                phases={},
            )

    def test_invalid_phase_dependency(self) -> None:
        """존재하지 않는 Phase 의존성 테스트."""
        with pytest.raises(ConfigValidationError) as exc_info:
            WorkspaceConfig(
                version="1.0",
                metadata=WorkspaceMetadata(name="test"),
                phases={
                    "p1": PhaseConfig(
                        description="Phase 1",
                        source="sources.yaml",
                        app_groups=["app1"],
                        depends_on=["nonexistent"],
                    )
                },
            )

        assert "non-existent" in str(exc_info.value).lower()

    def test_circular_dependency(self) -> None:
        """순환 의존성 테스트."""
        with pytest.raises(ConfigValidationError) as exc_info:
            WorkspaceConfig(
                version="1.0",
                metadata=WorkspaceMetadata(name="test"),
                phases={
                    "p1": PhaseConfig(
                        description="Phase 1",
                        source="sources.yaml",
                        app_groups=["app1"],
                        depends_on=["p2"],
                    ),
                    "p2": PhaseConfig(
                        description="Phase 2",
                        source="sources.yaml",
                        app_groups=["app2"],
                        depends_on=["p1"],
                    ),
                },
            )

        assert "circular" in str(exc_info.value).lower()

    def test_get_phase_order(self) -> None:
        """Phase 실행 순서 계산 테스트."""
        workspace = WorkspaceConfig(
            version="1.0",
            metadata=WorkspaceMetadata(name="test"),
            phases={
                "p1-infra": PhaseConfig(
                    description="Infrastructure",
                    source="p1/sources.yaml",
                    app_groups=["network"],
                    depends_on=[],
                ),
                "p2-data": PhaseConfig(
                    description="Data",
                    source="p2/sources.yaml",
                    app_groups=["postgres"],
                    depends_on=["p1-infra"],
                ),
                "p3-app": PhaseConfig(
                    description="Application",
                    source="p3/sources.yaml",
                    app_groups=["api"],
                    depends_on=["p2-data"],
                ),
            },
        )

        order = workspace.get_phase_order()

        # p1 → p2 → p3 순서여야 함
        assert order.index("p1-infra") < order.index("p2-data")
        assert order.index("p2-data") < order.index("p3-app")

    def test_get_phase_config(self) -> None:
        """Phase 설정 조회 테스트."""
        workspace = WorkspaceConfig(
            version="1.0",
            metadata=WorkspaceMetadata(name="test"),
            phases={
                "p1": PhaseConfig(
                    description="Phase 1",
                    source="sources.yaml",
                    app_groups=["app1"],
                )
            },
        )

        phase = workspace.get_phase_config("p1")
        assert phase.description == "Phase 1"

        with pytest.raises(KeyError):
            workspace.get_phase_config("nonexistent")

    def test_resolve_source_path(self, tmp_path: Path) -> None:
        """sources.yaml 경로 해석 테스트."""
        workspace = WorkspaceConfig(
            version="1.0",
            metadata=WorkspaceMetadata(name="test"),
            phases={
                "p1": PhaseConfig(
                    description="Phase 1",
                    source="p1-kube/sources.yaml",
                    app_groups=["app1"],
                )
            },
        )

        workspace_dir = tmp_path / "workspace"
        workspace_dir.mkdir()

        source_path = workspace.resolve_source_path("p1", workspace_dir)

        expected = (workspace_dir / "p1-kube" / "sources.yaml").resolve()
        assert source_path == expected

    def test_global_field_alias(self) -> None:
        """'global' 필드 alias 테스트."""
        workspace_dict = {
            "version": "1.0",
            "metadata": {"name": "test"},
            "global": {
                "kubeconfig": "~/.kube/config",
                "timeout": 900,
            },
            "phases": {
                "p1": {
                    "description": "Test",
                    "source": "sources.yaml",
                    "app_groups": ["app1"],
                }
            },
        }

        workspace = WorkspaceConfig(**workspace_dict)

        assert workspace.global_config.kubeconfig == "~/.kube/config"
        assert workspace.global_config.timeout == 900

    def test_complex_dependency_graph(self) -> None:
        """복잡한 의존성 그래프 테스트."""
        workspace = WorkspaceConfig(
            version="1.0",
            metadata=WorkspaceMetadata(name="complex"),
            phases={
                "p1": PhaseConfig(
                    description="Phase 1",
                    source="p1/sources.yaml",
                    app_groups=["app1"],
                ),
                "p2": PhaseConfig(
                    description="Phase 2",
                    source="p2/sources.yaml",
                    app_groups=["app2"],
                    depends_on=["p1"],
                ),
                "p3": PhaseConfig(
                    description="Phase 3",
                    source="p3/sources.yaml",
                    app_groups=["app3"],
                    depends_on=["p1"],
                ),
                "p4": PhaseConfig(
                    description="Phase 4",
                    source="p4/sources.yaml",
                    app_groups=["app4"],
                    depends_on=["p2", "p3"],
                ),
            },
        )

        order = workspace.get_phase_order()

        # p1이 가장 먼저
        assert order[0] == "p1"
        # p4가 가장 마지막
        assert order[-1] == "p4"
        # p2, p3은 p1 이후, p4 이전
        assert order.index("p2") > order.index("p1")
        assert order.index("p3") > order.index("p1")
        assert order.index("p4") > order.index("p2")
        assert order.index("p4") > order.index("p3")
