"""SBKube v0.8.0 chart path structure tests.

Tests for new repo/chart-version path structure to prevent chart name collisions.
"""

from pathlib import Path

import pytest

from sbkube.models.config_model import HelmApp
from sbkube.utils.output_manager import OutputManager


@pytest.fixture
def output_manager():
    """OutputManager fixture."""
    return OutputManager(format_type="human")


class TestChartPathStructure:
    """New chart path structure tests (v0.8.0)."""

    def test_get_chart_path_with_version(self):
        """Test chart path with explicit version."""
        app = HelmApp(type="helm", chart="grafana/loki", version="18.0.0")
        charts_dir = Path(".sbkube/charts")

        chart_path = app.get_chart_path(charts_dir)

        assert chart_path == Path(".sbkube/charts/grafana/loki-18.0.0")

    def test_get_chart_path_without_version(self):
        """Test chart path without version (should use 'latest')."""
        app = HelmApp(type="helm", chart="grafana/loki")
        charts_dir = Path(".sbkube/charts")

        chart_path = app.get_chart_path(charts_dir)

        assert chart_path == Path(".sbkube/charts/grafana/loki-latest")

    def test_get_chart_path_different_repos_same_chart(self):
        """Test different repos with same chart name don't collide."""
        app1 = HelmApp(type="helm", chart="grafana/loki", version="18.0.0")
        app2 = HelmApp(type="helm", chart="my-company/redis", version="1.0.0")
        charts_dir = Path(".sbkube/charts")

        path1 = app1.get_chart_path(charts_dir)
        path2 = app2.get_chart_path(charts_dir)

        # Paths should be different
        assert path1 != path2
        assert path1 == Path(".sbkube/charts/grafana/loki-18.0.0")
        assert path2 == Path(".sbkube/charts/my-company/redis-1.0.0")

    def test_get_chart_path_same_chart_different_versions(self):
        """Test same chart with different versions don't collide."""
        app1 = HelmApp(type="helm", chart="grafana/loki", version="18.0.0")
        app2 = HelmApp(type="helm", chart="grafana/loki", version="19.0.0")
        charts_dir = Path(".sbkube/charts")

        path1 = app1.get_chart_path(charts_dir)
        path2 = app2.get_chart_path(charts_dir)

        # Paths should be different
        assert path1 != path2
        assert path1 == Path(".sbkube/charts/grafana/loki-18.0.0")
        assert path2 == Path(".sbkube/charts/grafana/loki-19.0.0")

    def test_get_chart_path_local_chart_returns_none(self):
        """Test local chart returns None (no path generation needed)."""
        app = HelmApp(type="helm", chart="./my-chart")
        charts_dir = Path(".sbkube/charts")

        chart_path = app.get_chart_path(charts_dir)

        assert chart_path is None

    def test_get_version_or_default_with_version(self):
        """Test get_version_or_default with explicit version."""
        app = HelmApp(type="helm", chart="grafana/loki", version="18.0.0")

        assert app.get_version_or_default() == "18.0.0"

    def test_get_version_or_default_without_version(self):
        """Test get_version_or_default without version returns 'latest'."""
        app = HelmApp(type="helm", chart="grafana/loki")

        assert app.get_version_or_default() == "latest"


class TestBuildWithNewPaths:
    """Test build command with new path structure."""

    def test_build_with_new_path_structure(self, tmp_path, output_manager):
        """Test build finds chart in new path structure."""
        from sbkube.commands.build import build_helm_app

        # Create new path structure: charts/grafana/loki-18.0.0/
        chart_dir = tmp_path / "charts" / "grafana" / "redis-18.0.0"
        chart_dir.mkdir(parents=True)
        (chart_dir / "Chart.yaml").write_text("name: redis\nversion: 18.0.0")
        (chart_dir / "values.yaml").write_text("replicaCount: 1")
        (chart_dir / "templates").mkdir()
        (chart_dir / "templates" / "deployment.yaml").write_text("kind: Deployment")

        app = HelmApp(type="helm", chart="grafana/loki", version="18.0.0")
        build_dir = tmp_path / "build"

        success = build_helm_app(
            app_name="redis",
            app=app,
            base_dir=tmp_path,
            charts_dir=tmp_path / "charts",
            build_dir=build_dir,
            app_config_dir=tmp_path,
            output=output_manager,
        )

        assert success
        assert (build_dir / "redis" / "Chart.yaml").exists()

    def test_build_detects_legacy_v071_path(self, tmp_path, output_manager):
        """Test build detects legacy v0.7.1 path and shows migration guide."""
        from sbkube.commands.build import build_helm_app

        # Create legacy v0.7.1 path: charts/redis/
        legacy_chart_dir = tmp_path / "charts" / "redis"
        legacy_chart_dir.mkdir(parents=True)
        (legacy_chart_dir / "Chart.yaml").write_text("name: redis\nversion: 18.0.0")

        app = HelmApp(type="helm", chart="grafana/loki", version="18.0.0")
        build_dir = tmp_path / "build"

        # Should fail and detect legacy path
        success = build_helm_app(
            app_name="redis",
            app=app,
            base_dir=tmp_path,
            charts_dir=tmp_path / "charts",
            build_dir=build_dir,
            app_config_dir=tmp_path,
            output=output_manager,
        )

        assert not success
        # Migration guide should be shown (checked via output_manager if needed)

    def test_build_multiple_charts_same_name_different_repos(
        self, tmp_path, output_manager
    ):
        """Test build with multiple charts having same name from different repos."""
        from sbkube.commands.build import build_helm_app

        # Create charts: grafana/loki-18.0.0 and my-company/redis-1.0.0
        bitnami_chart = tmp_path / "charts" / "grafana" / "redis-18.0.0"
        bitnami_chart.mkdir(parents=True)
        (bitnami_chart / "Chart.yaml").write_text("name: redis\nversion: 18.0.0")
        (bitnami_chart / "templates").mkdir()

        custom_chart = tmp_path / "charts" / "my-company" / "redis-1.0.0"
        custom_chart.mkdir(parents=True)
        (custom_chart / "Chart.yaml").write_text("name: redis\nversion: 1.0.0")
        (custom_chart / "templates").mkdir()

        # Build both
        app1 = HelmApp(type="helm", chart="grafana/loki", version="18.0.0")
        app2 = HelmApp(type="helm", chart="my-company/redis", version="1.0.0")

        build_dir = tmp_path / "build"

        success1 = build_helm_app(
            app_name="redis-grafana",
            app=app1,
            base_dir=tmp_path,
            charts_dir=tmp_path / "charts",
            build_dir=build_dir,
            app_config_dir=tmp_path,
            output=output_manager,
        )

        success2 = build_helm_app(
            app_name="redis-custom",
            app=app2,
            base_dir=tmp_path,
            charts_dir=tmp_path / "charts",
            build_dir=build_dir,
            app_config_dir=tmp_path,
            output=output_manager,
        )

        # Both should succeed
        assert success1
        assert success2
        assert (build_dir / "redis-grafana" / "Chart.yaml").exists()
        assert (build_dir / "redis-custom" / "Chart.yaml").exists()

        # Verify correct versions
        bitnami_version = (build_dir / "redis-grafana" / "Chart.yaml").read_text()
        custom_version = (build_dir / "redis-custom" / "Chart.yaml").read_text()
        assert "version: 18.0.0" in bitnami_version
        assert "version: 1.0.0" in custom_version
