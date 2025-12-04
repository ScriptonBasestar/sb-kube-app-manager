"""Tests for chart_path_resolver module."""

from pathlib import Path
from unittest.mock import MagicMock, patch

import pytest

from sbkube.utils.chart_path_resolver import (
    ChartPathResult,
    LegacyVersion,
    check_legacy_chart_paths,
    print_legacy_migration_hint,
    resolve_chart_path,
    resolve_local_chart_path,
    resolve_remote_chart_path,
)


class TestLegacyVersion:
    """Test LegacyVersion enum."""

    def test_version_values(self) -> None:
        """Test enum values."""
        assert LegacyVersion.V070.value == "v0.7.0"
        assert LegacyVersion.V071.value == "v0.7.1"
        assert LegacyVersion.NONE.value is None


class TestChartPathResult:
    """Test ChartPathResult dataclass."""

    def test_requires_migration_false_when_none(self) -> None:
        """Test requires_migration is False when legacy_version is NONE."""
        result = ChartPathResult(
            chart_path=Path("/some/path"),
            found=True,
            legacy_version=LegacyVersion.NONE,
        )
        assert result.requires_migration is False

    def test_requires_migration_true_for_v070(self) -> None:
        """Test requires_migration is True for v0.7.0."""
        result = ChartPathResult(
            chart_path=None,
            found=False,
            legacy_version=LegacyVersion.V070,
            legacy_path=Path("/legacy/path"),
        )
        assert result.requires_migration is True

    def test_requires_migration_true_for_v071(self) -> None:
        """Test requires_migration is True for v0.7.1."""
        result = ChartPathResult(
            chart_path=None,
            found=False,
            legacy_version=LegacyVersion.V071,
            legacy_path=Path("/legacy/path"),
        )
        assert result.requires_migration is True


class TestCheckLegacyChartPaths:
    """Test check_legacy_chart_paths function."""

    def test_finds_v071_legacy_path(self, tmp_path: Path) -> None:
        """Test detection of v0.7.1 legacy path structure."""
        charts_dir = tmp_path / "charts"
        charts_dir.mkdir(exist_ok=True)

        # Create legacy v0.7.1 structure: charts/{chart-name}/
        legacy_path = charts_dir / "nginx"
        legacy_path.mkdir(exist_ok=True)
        (legacy_path / "Chart.yaml").write_text("name: nginx")

        version, path = check_legacy_chart_paths(charts_dir, "nginx")

        assert version == LegacyVersion.V071
        assert path == legacy_path

    def test_finds_v070_legacy_path(self, tmp_path: Path) -> None:
        """Test detection of v0.7.0 legacy path structure."""
        charts_dir = tmp_path / "charts"
        charts_dir.mkdir(exist_ok=True)

        # Create legacy v0.7.0 structure: charts/{chart-name}/{chart-name}/
        parent_path = charts_dir / "nginx"
        parent_path.mkdir(exist_ok=True)
        legacy_path = parent_path / "nginx"
        legacy_path.mkdir(exist_ok=True)
        (legacy_path / "Chart.yaml").write_text("name: nginx")

        version, path = check_legacy_chart_paths(charts_dir, "nginx")

        assert version == LegacyVersion.V070
        assert path == legacy_path

    def test_prefers_v071_over_v070(self, tmp_path: Path) -> None:
        """Test that v0.7.1 is detected first if both exist."""
        charts_dir = tmp_path / "charts"
        charts_dir.mkdir(exist_ok=True)

        # Create both legacy structures
        # v0.7.1: charts/{chart-name}/
        v071_path = charts_dir / "nginx"
        v071_path.mkdir(exist_ok=True)
        (v071_path / "Chart.yaml").write_text("name: nginx")

        # v0.7.0: charts/{chart-name}/{chart-name}/
        v070_path = v071_path / "nginx"
        v070_path.mkdir(exist_ok=True)
        (v070_path / "Chart.yaml").write_text("name: nginx")

        version, path = check_legacy_chart_paths(charts_dir, "nginx")

        # Should find v0.7.1 first
        assert version == LegacyVersion.V071
        assert path == v071_path

    def test_returns_none_when_no_legacy(self, tmp_path: Path) -> None:
        """Test returns NONE when no legacy paths exist."""
        charts_dir = tmp_path / "charts"
        charts_dir.mkdir(exist_ok=True)

        version, path = check_legacy_chart_paths(charts_dir, "nginx")

        assert version == LegacyVersion.NONE
        assert path is None

    def test_ignores_directory_without_chart_yaml(self, tmp_path: Path) -> None:
        """Test ignores directories without Chart.yaml."""
        charts_dir = tmp_path / "charts"
        charts_dir.mkdir(exist_ok=True)

        # Create directory without Chart.yaml
        legacy_path = charts_dir / "nginx"
        legacy_path.mkdir(exist_ok=True)
        # No Chart.yaml created

        version, path = check_legacy_chart_paths(charts_dir, "nginx")

        assert version == LegacyVersion.NONE
        assert path is None


class TestPrintLegacyMigrationHint:
    """Test print_legacy_migration_hint function."""

    def test_prints_v071_hint(self, tmp_path: Path) -> None:
        """Test prints correct hints for v0.7.1."""
        output = MagicMock()
        console = MagicMock()
        output.get_console.return_value = console

        charts_dir = tmp_path / "charts"
        legacy_path = charts_dir / "nginx"

        print_legacy_migration_hint(
            output,
            LegacyVersion.V071,
            legacy_path,
            charts_dir,
        )

        output.print_error.assert_called_once()
        assert "v0.7.1" in output.print_error.call_args[0][0]

        output.print_warning.assert_called_once()
        assert "older version" in output.print_warning.call_args[0][0]

        # Check console output
        assert console.print.call_count == 4  # Migration steps

    def test_prints_v070_hint(self, tmp_path: Path) -> None:
        """Test prints correct hints for v0.7.0."""
        output = MagicMock()
        console = MagicMock()
        output.get_console.return_value = console

        charts_dir = tmp_path / "charts"
        legacy_path = charts_dir / "nginx" / "nginx"

        print_legacy_migration_hint(
            output,
            LegacyVersion.V070,
            legacy_path,
            charts_dir,
        )

        output.print_error.assert_called_once()
        assert "v0.7.0" in output.print_error.call_args[0][0]

        output.print_warning.assert_called_once()
        assert "very old version" in output.print_warning.call_args[0][0]


class TestResolveRemoteChartPath:
    """Test resolve_remote_chart_path function."""

    def test_finds_modern_chart_path(self, tmp_path: Path) -> None:
        """Test finds chart in modern v0.8.0+ path structure."""
        charts_dir = tmp_path / "charts"
        charts_dir.mkdir(exist_ok=True)

        # Create modern structure: charts/{repo}/{chart-name}-{version}/
        chart_path = charts_dir / "bitnami" / "nginx-1.0.0"
        chart_path.mkdir(parents=True)
        (chart_path / "Chart.yaml").write_text("name: nginx")

        # Mock HelmApp
        app = MagicMock()
        app.get_chart_path.return_value = chart_path

        result = resolve_remote_chart_path(app, charts_dir)

        assert result.found is True
        assert result.chart_path == chart_path
        assert result.legacy_version == LegacyVersion.NONE

    def test_detects_legacy_v071_path(self, tmp_path: Path) -> None:
        """Test detects legacy v0.7.1 path structure."""
        charts_dir = tmp_path / "charts"
        charts_dir.mkdir(exist_ok=True)

        # Create legacy v0.7.1 structure
        legacy_path = charts_dir / "nginx"
        legacy_path.mkdir(exist_ok=True)
        (legacy_path / "Chart.yaml").write_text("name: nginx")

        # Mock HelmApp - modern path doesn't exist
        app = MagicMock()
        app.get_chart_path.return_value = charts_dir / "bitnami" / "nginx-1.0.0"
        app.get_chart_name.return_value = "nginx"

        output = MagicMock()
        output.get_console.return_value = MagicMock()

        result = resolve_remote_chart_path(app, charts_dir, output)

        assert result.found is False
        assert result.requires_migration is True
        assert result.legacy_version == LegacyVersion.V071
        assert result.legacy_path == legacy_path

    def test_returns_not_found_when_no_chart(self, tmp_path: Path) -> None:
        """Test returns not found when chart doesn't exist anywhere."""
        charts_dir = tmp_path / "charts"
        charts_dir.mkdir(exist_ok=True)

        app = MagicMock()
        app.get_chart_path.return_value = charts_dir / "bitnami" / "nginx-1.0.0"
        app.get_chart_name.return_value = "nginx"

        output = MagicMock()
        result = resolve_remote_chart_path(app, charts_dir, output)

        assert result.found is False
        assert result.chart_path is None
        assert result.legacy_version == LegacyVersion.NONE
        output.print_error.assert_called_once()
        output.print_warning.assert_called_once()


class TestResolveLocalChartPath:
    """Test resolve_local_chart_path function."""

    def test_resolves_relative_path_with_dot_slash(self, tmp_path: Path) -> None:
        """Test resolves relative path starting with ./"""
        app_config_dir = tmp_path / "apps" / "myapp"
        app_config_dir.mkdir(parents=True)

        chart_path = app_config_dir / "charts" / "mychart"
        chart_path.mkdir(parents=True)
        (chart_path / "Chart.yaml").write_text("name: mychart")

        app = MagicMock()
        app.chart = "./charts/mychart"

        result = resolve_local_chart_path(app, app_config_dir)

        assert result.found is True
        assert result.chart_path == chart_path

    def test_resolves_absolute_path(self, tmp_path: Path) -> None:
        """Test resolves absolute path."""
        app_config_dir = tmp_path / "apps" / "myapp"
        app_config_dir.mkdir(parents=True)

        chart_path = tmp_path / "shared-charts" / "mychart"
        chart_path.mkdir(parents=True)
        (chart_path / "Chart.yaml").write_text("name: mychart")

        app = MagicMock()
        app.chart = str(chart_path)

        result = resolve_local_chart_path(app, app_config_dir)

        assert result.found is True
        assert result.chart_path == chart_path

    def test_resolves_simple_name(self, tmp_path: Path) -> None:
        """Test resolves simple chart name relative to app_config_dir."""
        app_config_dir = tmp_path / "apps" / "myapp"
        app_config_dir.mkdir(parents=True)

        chart_path = app_config_dir / "mychart"
        chart_path.mkdir(exist_ok=True)
        (chart_path / "Chart.yaml").write_text("name: mychart")

        app = MagicMock()
        app.chart = "mychart"

        result = resolve_local_chart_path(app, app_config_dir)

        assert result.found is True
        assert result.chart_path == chart_path

    def test_returns_not_found_for_missing_chart(self, tmp_path: Path) -> None:
        """Test returns not found for missing local chart."""
        app_config_dir = tmp_path / "apps" / "myapp"
        app_config_dir.mkdir(parents=True)

        app = MagicMock()
        app.chart = "./nonexistent"

        output = MagicMock()
        result = resolve_local_chart_path(app, app_config_dir, output)

        assert result.found is False
        assert result.chart_path is None
        output.print_error.assert_called_once()


class TestResolveChartPath:
    """Test resolve_chart_path function."""

    def test_prefers_build_directory(self, tmp_path: Path) -> None:
        """Test prefers build directory over source chart."""
        charts_dir = tmp_path / "charts"
        build_dir = tmp_path / "build"
        app_config_dir = tmp_path / "apps" / "myapp"

        build_dir.mkdir(exist_ok=True)
        app_config_dir.mkdir(parents=True)

        # Create both source and build
        build_path = build_dir / "nginx"
        build_path.mkdir(exist_ok=True)
        (build_path / "Chart.yaml").write_text("name: nginx")

        app = MagicMock()
        app.is_remote_chart.return_value = True

        result = resolve_chart_path(
            app, "nginx", charts_dir, build_dir, app_config_dir
        )

        assert result.found is True
        assert result.chart_path == build_path

    def test_skips_build_when_disabled(self, tmp_path: Path) -> None:
        """Test skips build directory when check_build_first is False."""
        charts_dir = tmp_path / "charts"
        build_dir = tmp_path / "build"
        app_config_dir = tmp_path / "apps" / "myapp"

        charts_dir.mkdir(exist_ok=True)
        build_dir.mkdir(exist_ok=True)
        app_config_dir.mkdir(parents=True)

        # Create build directory
        build_path = build_dir / "nginx"
        build_path.mkdir(exist_ok=True)
        (build_path / "Chart.yaml").write_text("name: nginx")

        # Create modern chart path
        chart_path = charts_dir / "bitnami" / "nginx-1.0.0"
        chart_path.mkdir(parents=True)
        (chart_path / "Chart.yaml").write_text("name: nginx")

        app = MagicMock()
        app.is_remote_chart.return_value = True
        app.get_chart_path.return_value = chart_path

        result = resolve_chart_path(
            app, "nginx", charts_dir, build_dir, app_config_dir,
            check_build_first=False
        )

        assert result.found is True
        assert result.chart_path == chart_path  # Not build_path

    def test_resolves_local_chart(self, tmp_path: Path) -> None:
        """Test resolves local chart when not remote."""
        charts_dir = tmp_path / "charts"
        build_dir = tmp_path / "build"
        app_config_dir = tmp_path / "apps" / "myapp"

        charts_dir.mkdir(exist_ok=True)
        build_dir.mkdir(exist_ok=True)
        app_config_dir.mkdir(parents=True)

        chart_path = app_config_dir / "mychart"
        chart_path.mkdir(exist_ok=True)
        (chart_path / "Chart.yaml").write_text("name: mychart")

        app = MagicMock()
        app.is_remote_chart.return_value = False
        app.chart = "mychart"

        result = resolve_chart_path(
            app, "myapp", charts_dir, build_dir, app_config_dir
        )

        assert result.found is True
        assert result.chart_path == chart_path
