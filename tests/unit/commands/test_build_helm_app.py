"""Unit tests for build.py - build_helm_app function.

Tests verify:
- Remote chart building
- Local chart building
- Legacy path handling
- Customization options (overrides, removes)
- Error scenarios
"""

from pathlib import Path
from unittest.mock import MagicMock

from sbkube.commands.build import build_helm_app
from sbkube.models.config_model import HelmApp
from sbkube.utils.output_manager import OutputManager


class TestBuildHelmAppBasic:
    """Test basic Helm app build scenarios."""

    def test_build_remote_chart_success(self, tmp_path: Path) -> None:
        """Test building a remote chart with existing source."""
        # Arrange
        charts_dir = tmp_path / "charts"
        charts_dir.mkdir(exist_ok=True)

        # Create source chart structure (modern v0.8.0+ format)
        source_chart_dir = charts_dir / "bitnami" / "nginx-15.0.0"
        source_chart_dir.mkdir(parents=True, exist_ok=True)
        (source_chart_dir / "Chart.yaml").write_text("name: nginx\nversion: 15.0.0")
        (source_chart_dir / "values.yaml").write_text("replicaCount: 1")

        build_dir = tmp_path / "build"
        build_dir.mkdir(exist_ok=True)

        app = HelmApp(
            type="helm",
            chart="bitnami/nginx",
            version="15.0.0",
        )

        output = MagicMock(spec=OutputManager)

        # Act
        result = build_helm_app(
            app_name="nginx",
            app=app,
            base_dir=tmp_path,
            charts_dir=charts_dir,
            build_dir=build_dir,
            app_config_dir=tmp_path / "config",
            output=output,
            dry_run=False,
        )

        # Assert
        assert result is True
        # Verify build directory created
        app_build_dir = build_dir / "nginx"
        assert app_build_dir.exists()
        assert (app_build_dir / "Chart.yaml").exists()

    def test_build_local_chart_relative_path(self, tmp_path: Path) -> None:
        """Test building a local chart with relative path."""
        # Arrange
        app_config_dir = tmp_path / "config"
        app_config_dir.mkdir(exist_ok=True)

        # Create local chart
        local_chart_dir = app_config_dir / "my-chart"
        local_chart_dir.mkdir(exist_ok=True)
        (local_chart_dir / "Chart.yaml").write_text("name: my-chart\nversion: 1.0.0")

        build_dir = tmp_path / "build"
        build_dir.mkdir(exist_ok=True)

        app = HelmApp(
            type="helm",
            chart="./my-chart",  # Relative path
        )

        output = MagicMock(spec=OutputManager)

        # Act
        result = build_helm_app(
            app_name="my-app",
            app=app,
            base_dir=tmp_path,
            charts_dir=tmp_path / "charts",
            build_dir=build_dir,
            app_config_dir=app_config_dir,
            output=output,
            dry_run=False,
        )

        # Assert
        assert result is True
        app_build_dir = build_dir / "my-app"
        assert app_build_dir.exists()
        assert (app_build_dir / "Chart.yaml").exists()

    def test_build_dry_run_mode(self, tmp_path: Path) -> None:
        """Test dry-run mode doesn't create files."""
        # Arrange
        charts_dir = tmp_path / "charts"
        charts_dir.mkdir(exist_ok=True)

        source_chart_dir = charts_dir / "bitnami" / "nginx-15.0.0"
        source_chart_dir.mkdir(parents=True, exist_ok=True)
        (source_chart_dir / "Chart.yaml").write_text("name: nginx\nversion: 15.0.0")

        build_dir = tmp_path / "build"
        build_dir.mkdir(exist_ok=True)

        app = HelmApp(
            type="helm",
            chart="bitnami/nginx",
            version="15.0.0",
        )

        output = MagicMock(spec=OutputManager)

        # Act
        result = build_helm_app(
            app_name="nginx",
            app=app,
            base_dir=tmp_path,
            charts_dir=charts_dir,
            build_dir=build_dir,
            app_config_dir=tmp_path / "config",
            output=output,
            dry_run=True,  # Dry-run mode
        )

        # Assert
        assert result is True
        # Build directory should NOT be created in dry-run
        app_build_dir = build_dir / "nginx"
        assert not app_build_dir.exists()


class TestBuildHelmAppErrors:
    """Test error scenarios."""

    def test_chart_not_found(self, tmp_path: Path) -> None:
        """Test error when chart source not found."""
        # Arrange
        charts_dir = tmp_path / "charts"
        charts_dir.mkdir(exist_ok=True)

        build_dir = tmp_path / "build"
        build_dir.mkdir(exist_ok=True)

        app = HelmApp(
            type="helm",
            chart="bitnami/nginx",
            version="15.0.0",
        )

        output = MagicMock(spec=OutputManager)

        # Act
        result = build_helm_app(
            app_name="nginx",
            app=app,
            base_dir=tmp_path,
            charts_dir=charts_dir,
            build_dir=build_dir,
            app_config_dir=tmp_path / "config",
            output=output,
            dry_run=False,
        )

        # Assert
        assert result is False
        output.print_error.assert_called()


class TestBuildHelmAppLegacyPaths:
    """Test legacy path detection."""

    def test_legacy_v071_path_detected(self, tmp_path: Path) -> None:
        """Test detection of v0.7.1 legacy chart path."""
        # Arrange
        charts_dir = tmp_path / "charts"
        charts_dir.mkdir(exist_ok=True)

        # Create legacy v0.7.1 path: charts/nginx/
        legacy_chart_dir = charts_dir / "nginx"
        legacy_chart_dir.mkdir(exist_ok=True)
        (legacy_chart_dir / "Chart.yaml").write_text("name: nginx\nversion: 15.0.0")

        build_dir = tmp_path / "build"
        build_dir.mkdir(exist_ok=True)

        app = HelmApp(
            type="helm",
            chart="bitnami/nginx",
            version="15.0.0",
        )

        output = MagicMock(spec=OutputManager)

        # Act
        result = build_helm_app(
            app_name="nginx",
            app=app,
            base_dir=tmp_path,
            charts_dir=charts_dir,
            build_dir=build_dir,
            app_config_dir=tmp_path / "config",
            output=output,
            dry_run=False,
        )

        # Assert
        assert result is False
        # Verify error message about legacy path
        output.print_error.assert_called()
        call_args = str(output.print_error.call_args)
        assert "legacy" in call_args.lower()

    def test_legacy_v070_path_detected(self, tmp_path: Path) -> None:
        """Test detection of v0.7.0 legacy chart path."""
        # Arrange
        charts_dir = tmp_path / "charts"
        charts_dir.mkdir(exist_ok=True)

        # Create legacy v0.7.0 path: charts/nginx/nginx/
        legacy_outer = charts_dir / "nginx"
        legacy_outer.mkdir(exist_ok=True)
        legacy_inner = legacy_outer / "nginx"
        legacy_inner.mkdir(exist_ok=True)
        (legacy_inner / "Chart.yaml").write_text("name: nginx\nversion: 15.0.0")

        build_dir = tmp_path / "build"
        build_dir.mkdir(exist_ok=True)

        app = HelmApp(
            type="helm",
            chart="bitnami/nginx",
            version="15.0.0",
        )

        output = MagicMock(spec=OutputManager)

        # Act
        result = build_helm_app(
            app_name="nginx",
            app=app,
            base_dir=tmp_path,
            charts_dir=charts_dir,
            build_dir=build_dir,
            app_config_dir=tmp_path / "config",
            output=output,
            dry_run=False,
        )

        # Assert
        assert result is False
        output.print_error.assert_called()
        call_args = str(output.print_error.call_args)
        assert "legacy" in call_args.lower()


class TestBuildHelmAppCustomization:
    """Test chart customization features."""

    def test_build_with_overrides(self, tmp_path: Path) -> None:
        """Test building with override files."""
        # Arrange
        charts_dir = tmp_path / "charts"
        charts_dir.mkdir(exist_ok=True)

        source_chart_dir = charts_dir / "bitnami" / "nginx-15.0.0"
        source_chart_dir.mkdir(parents=True, exist_ok=True)
        (source_chart_dir / "Chart.yaml").write_text("name: nginx\nversion: 15.0.0")
        (source_chart_dir / "values.yaml").write_text("replicaCount: 1")

        # Create overrides directory: overrides/{app_name}/
        app_config_dir = tmp_path / "config"
        app_config_dir.mkdir(exist_ok=True)
        overrides_base = app_config_dir / "overrides" / "nginx"
        overrides_base.mkdir(parents=True, exist_ok=True)

        # Create override file
        override_file = overrides_base / "custom-values.yaml"
        override_file.write_text("replicaCount: 3")

        build_dir = tmp_path / "build"
        build_dir.mkdir(exist_ok=True)

        app = HelmApp(
            type="helm",
            chart="bitnami/nginx",
            version="15.0.0",
            overrides=["custom-values.yaml"],  # File within overrides/nginx/
        )

        output = MagicMock(spec=OutputManager)

        # Act
        result = build_helm_app(
            app_name="nginx",
            app=app,
            base_dir=tmp_path,
            charts_dir=charts_dir,
            build_dir=build_dir,
            app_config_dir=app_config_dir,
            output=output,
            dry_run=False,
        )

        # Assert
        assert result is True
        # Verify override file was copied to build directory
        override_target = build_dir / "nginx" / "custom-values.yaml"
        assert override_target.exists()

    def test_build_with_removes(self, tmp_path: Path) -> None:
        """Test building with file/directory removal patterns."""
        # Arrange
        charts_dir = tmp_path / "charts"
        charts_dir.mkdir(exist_ok=True)

        source_chart_dir = charts_dir / "bitnami" / "nginx-15.0.0"
        source_chart_dir.mkdir(parents=True, exist_ok=True)
        (source_chart_dir / "Chart.yaml").write_text("name: nginx\nversion: 15.0.0")
        (source_chart_dir / "values.yaml").write_text("replicaCount: 1")

        # Create templates directory with files to remove
        templates_dir = source_chart_dir / "templates"
        templates_dir.mkdir(exist_ok=True)
        (templates_dir / "deployment.yaml").write_text("apiVersion: apps/v1")
        (templates_dir / "service.yaml").write_text("apiVersion: v1")

        build_dir = tmp_path / "build"
        build_dir.mkdir(exist_ok=True)

        app = HelmApp(
            type="helm",
            chart="bitnami/nginx",
            version="15.0.0",
            removes=["templates/service.yaml"],  # Remove service template
        )

        output = MagicMock(spec=OutputManager)

        # Act
        result = build_helm_app(
            app_name="nginx",
            app=app,
            base_dir=tmp_path,
            charts_dir=charts_dir,
            build_dir=build_dir,
            app_config_dir=tmp_path / "config",
            output=output,
            dry_run=False,
        )

        # Assert
        assert result is True
        # Verify service.yaml was removed
        build_templates = build_dir / "nginx" / "templates"
        assert (build_templates / "deployment.yaml").exists()
        assert not (build_templates / "service.yaml").exists()
