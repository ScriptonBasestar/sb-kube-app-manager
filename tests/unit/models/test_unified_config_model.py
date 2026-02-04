"""Tests for UnifiedConfig model (v0.10.0+)."""

from pathlib import Path

import pytest

from sbkube.exceptions import ConfigValidationError
from sbkube.models.unified_config_model import (
    PhaseReference,
    UnifiedConfig,
    UnifiedSettings,
)


class TestUnifiedSettings:
    """UnifiedSettings 테스트."""

    def test_default_values(self) -> None:
        """기본값 테스트."""
        settings = UnifiedSettings()

        assert settings.kubeconfig is None
        assert settings.kubeconfig_context is None
        assert settings.namespace == "default"
        assert settings.timeout == 600
        assert settings.on_failure == "stop"
        assert settings.parallel is False
        assert settings.parallel_apps is False
        assert settings.max_workers == 4

    def test_custom_values(self) -> None:
        """커스텀 값 테스트."""
        settings = UnifiedSettings(
            kubeconfig="~/.kube/config",
            kubeconfig_context="prod-cluster",
            namespace="production",
            timeout=300,
            on_failure="rollback",
            parallel=True,
            max_workers=8,
        )

        assert settings.kubeconfig == "~/.kube/config"
        assert settings.kubeconfig_context == "prod-cluster"
        assert settings.namespace == "production"
        assert settings.timeout == 300
        assert settings.on_failure == "rollback"
        assert settings.parallel is True
        assert settings.max_workers == 8

    def test_helm_repos_normalization(self) -> None:
        """Helm repos 정규화 테스트 (string shorthand)."""
        settings = UnifiedSettings(
            helm_repos={
                "grafana": "https://grafana.github.io/helm-charts",
                "bitnami": {"url": "https://charts.bitnami.com/bitnami"},
            }
        )

        assert "grafana" in settings.helm_repos
        assert "bitnami" in settings.helm_repos
        # String shorthand should be converted to dict
        assert settings.helm_repos["grafana"].url == "https://grafana.github.io/helm-charts"

    def test_invalid_max_workers(self) -> None:
        """잘못된 max_workers 테스트."""
        with pytest.raises(ConfigValidationError):
            UnifiedSettings(max_workers=0)

        with pytest.raises(ConfigValidationError):
            UnifiedSettings(max_workers=100)

    def test_invalid_timeout(self) -> None:
        """잘못된 timeout 테스트."""
        with pytest.raises(ConfigValidationError):
            UnifiedSettings(timeout=0)

        with pytest.raises(ConfigValidationError):
            UnifiedSettings(timeout=10000)


class TestPhaseReference:
    """PhaseReference 테스트."""

    def test_external_source(self) -> None:
        """외부 소스 참조 테스트."""
        phase = PhaseReference(
            description="Infrastructure",
            source="p1-kube/sbkube.yaml",
            depends_on=["base"],
        )

        assert phase.source == "p1-kube/sbkube.yaml"
        assert phase.depends_on == ["base"]
        assert len(phase.apps) == 0

    def test_inline_apps(self) -> None:
        """인라인 앱 정의 테스트."""
        from sbkube.models.config_model import HelmApp

        phase = PhaseReference(
            description="Application",
            apps={
                "nginx": HelmApp(
                    type="helm",
                    chart="bitnami/nginx",
                    version="15.0.0",
                ),
            },
        )

        assert phase.source is None
        assert "nginx" in phase.apps
        assert phase.apps["nginx"].chart == "bitnami/nginx"

    def test_source_and_apps_conflict(self) -> None:
        """source와 apps 동시 정의 오류 테스트."""
        from sbkube.models.config_model import HelmApp

        with pytest.raises(ConfigValidationError) as exc_info:
            PhaseReference(
                source="p1-kube/sbkube.yaml",
                apps={
                    "nginx": HelmApp(type="helm", chart="bitnami/nginx"),
                },
            )

        assert "both" in str(exc_info.value).lower()

    def test_empty_phase(self) -> None:
        """source도 apps도 없는 Phase 오류 테스트."""
        with pytest.raises(ConfigValidationError) as exc_info:
            PhaseReference(description="Empty phase")

        assert "either" in str(exc_info.value).lower()


class TestUnifiedConfig:
    """UnifiedConfig 테스트."""

    def test_minimal_config(self) -> None:
        """최소 설정 테스트."""
        config = UnifiedConfig()

        assert config.apiVersion == "sbkube/v1"
        # metadata defaults to empty dict
        assert config.metadata == {}
        assert config.settings.namespace == "default"
        assert len(config.apps) == 0
        assert len(config.phases) == 0

    def test_metadata_with_none(self) -> None:
        """metadata가 None일 때 name 자동 추가 테스트."""
        config = UnifiedConfig(metadata=None)

        # Validator adds 'name' when metadata is None
        assert config.metadata.get("name") == "unnamed"

    def test_full_config(self) -> None:
        """전체 설정 테스트."""
        config = UnifiedConfig(
            apiVersion="sbkube/v1",
            metadata={
                "name": "my-deployment",
                "environment": "prod",
            },
            settings=UnifiedSettings(
                kubeconfig="~/.kube/config",
                namespace="production",
            ),
            phases={
                "p1-infra": PhaseReference(
                    source="p1-kube/sbkube.yaml",
                ),
                "p2-app": PhaseReference(
                    source="p2-kube/sbkube.yaml",
                    depends_on=["p1-infra"],
                ),
            },
        )

        assert config.metadata["name"] == "my-deployment"
        assert config.settings.namespace == "production"
        assert len(config.phases) == 2

    def test_invalid_api_version(self) -> None:
        """잘못된 apiVersion 테스트."""
        with pytest.raises(ConfigValidationError):
            UnifiedConfig(apiVersion="v1")  # Missing sbkube/ prefix

        with pytest.raises(ConfigValidationError):
            UnifiedConfig(apiVersion="kubernetes/v1")  # Wrong prefix

    def test_phase_order(self) -> None:
        """Phase 실행 순서 테스트."""
        config = UnifiedConfig(
            phases={
                "p3-monitoring": PhaseReference(
                    source="p3.yaml",
                    depends_on=["p2-app"],
                ),
                "p1-infra": PhaseReference(
                    source="p1.yaml",
                ),
                "p2-app": PhaseReference(
                    source="p2.yaml",
                    depends_on=["p1-infra"],
                ),
            },
        )

        order = config.get_phase_order()

        assert order.index("p1-infra") < order.index("p2-app")
        assert order.index("p2-app") < order.index("p3-monitoring")

    def test_nonexistent_phase_dependency(self) -> None:
        """존재하지 않는 Phase 의존성 테스트."""
        with pytest.raises(ConfigValidationError) as exc_info:
            UnifiedConfig(
                phases={
                    "p1": PhaseReference(
                        source="p1.yaml",
                        depends_on=["nonexistent"],
                    ),
                },
            )

        assert "non-existent" in str(exc_info.value).lower()

    def test_circular_dependency(self) -> None:
        """순환 의존성 테스트."""
        with pytest.raises(ConfigValidationError) as exc_info:
            UnifiedConfig(
                phases={
                    "a": PhaseReference(source="a.yaml", depends_on=["b"]),
                    "b": PhaseReference(source="b.yaml", depends_on=["c"]),
                    "c": PhaseReference(source="c.yaml", depends_on=["a"]),
                },
            )

        assert "circular" in str(exc_info.value).lower()

    def test_complex_dependency_graph(self) -> None:
        """복잡한 의존성 그래프 테스트."""
        config = UnifiedConfig(
            phases={
                "base": PhaseReference(source="base.yaml"),
                "net": PhaseReference(source="net.yaml", depends_on=["base"]),
                "storage": PhaseReference(source="storage.yaml", depends_on=["base"]),
                "db": PhaseReference(
                    source="db.yaml", depends_on=["net", "storage"]
                ),
                "app": PhaseReference(source="app.yaml", depends_on=["db"]),
            },
        )

        order = config.get_phase_order()

        # base must be first
        assert order[0] == "base"
        # app must be last
        assert order[-1] == "app"
        # net and storage after base, before db
        assert order.index("net") > order.index("base")
        assert order.index("storage") > order.index("base")
        assert order.index("db") > order.index("net")
        assert order.index("db") > order.index("storage")

    def test_resolve_source_path(self, tmp_path: Path) -> None:
        """소스 경로 해석 테스트."""
        config = UnifiedConfig(
            phases={
                "p1": PhaseReference(source="p1-kube/sbkube.yaml"),
            },
        )

        resolved = config.resolve_source_path("p1", tmp_path)

        assert resolved == (tmp_path / "p1-kube" / "sbkube.yaml").resolve()

    def test_resolve_source_path_inline(self, tmp_path: Path) -> None:
        """인라인 앱의 소스 경로 해석 테스트."""
        from sbkube.models.config_model import HelmApp

        config = UnifiedConfig(
            phases={
                "p1": PhaseReference(
                    apps={"nginx": HelmApp(type="helm", chart="bitnami/nginx")},
                ),
            },
        )

        resolved = config.resolve_source_path("p1", tmp_path)

        assert resolved is None  # Inline apps have no source path


class TestUnifiedConfigFromLegacy:
    """Legacy 파일 변환 테스트."""

    def test_from_legacy_files_sources_only(self, tmp_path: Path) -> None:
        """sources.yaml만 있는 경우 테스트."""
        sources_yaml = tmp_path / "sources.yaml"
        sources_yaml.write_text("""
kubeconfig: ~/.kube/config
kubeconfig_context: test-context
helm_repos:
  grafana:
    url: https://grafana.github.io/helm-charts
""")

        config = UnifiedConfig.from_legacy_files(
            sources_path=sources_yaml,
        )

        assert config.settings.kubeconfig == "~/.kube/config"
        assert config.settings.kubeconfig_context == "test-context"
        assert "grafana" in config.settings.helm_repos

    def test_from_legacy_files_workspace(self, tmp_path: Path) -> None:
        """workspace.yaml 변환 테스트."""
        workspace_yaml = tmp_path / "workspace.yaml"
        workspace_yaml.write_text("""
version: "1.0"
metadata:
  name: test-workspace
  environment: prod
global:
  timeout: 900
phases:
  p1:
    description: "Phase 1"
    source: p1/sources.yaml
    app_groups:
      - app1
""")

        config = UnifiedConfig.from_legacy_files(
            workspace_path=workspace_yaml,
        )

        assert config.metadata["name"] == "test-workspace"
        assert config.settings.timeout == 900
        assert "p1" in config.phases
