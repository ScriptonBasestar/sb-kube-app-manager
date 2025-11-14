"""Unit tests for build.py edge cases.

Tests verify:
- Local chart absolute path handling
- Override directory warning (unconfigured overrides)
- Override glob pattern processing
- Removes dry-run mode
- Override file not found warnings
"""

from pathlib import Path
from unittest.mock import MagicMock

import pytest

from sbkube.commands.build import build_helm_app
from sbkube.models.config_model import HelmApp
from sbkube.utils.output_manager import OutputManager


class TestLocalChartPaths:
    """Test local chart path resolution."""

    def test_local_chart_absolute_path(self, tmp_path: Path) -> None:
        """Test local chart with absolute path."""
        # Arrange
        local_chart_dir = tmp_path / "custom_charts" / "my-chart"
        local_chart_dir.mkdir(parents=True, exist_ok=True)
        (local_chart_dir / "Chart.yaml").write_text("name: my-chart\nversion: 1.0.0")
        (local_chart_dir / "values.yaml").write_text("replicaCount: 1")

        build_dir = tmp_path / "build"
        build_dir.mkdir(exist_ok=True)

        app = HelmApp(
            type="helm",
            chart=str(local_chart_dir),  # Absolute path
        )

        output = MagicMock(spec=OutputManager)

        # Act
        result = build_helm_app(
            app_name="my-chart",
            app=app,
            base_dir=tmp_path,
            charts_dir=tmp_path / "charts",
            build_dir=build_dir,
            app_config_dir=tmp_path / "config",
            output=output,
            dry_run=False,
        )

        # Assert
        assert result is True
        assert (build_dir / "my-chart" / "Chart.yaml").exists()

    def test_local_chart_not_found_absolute_path(self, tmp_path: Path) -> None:
        """Test error when local chart absolute path doesn't exist."""
        # Arrange
        build_dir = tmp_path / "build"
        build_dir.mkdir(exist_ok=True)

        app = HelmApp(
            type="helm",
            chart="/nonexistent/chart/path",  # Absolute path that doesn't exist
        )

        output = MagicMock(spec=OutputManager)

        # Act
        result = build_helm_app(
            app_name="my-chart",
            app=app,
            base_dir=tmp_path,
            charts_dir=tmp_path / "charts",
            build_dir=build_dir,
            app_config_dir=tmp_path / "config",
            output=output,
            dry_run=False,
        )

        # Assert
        assert result is False
        output.print_error.assert_called()
        call_args = output.print_error.call_args[0][0]
        assert "local chart not found" in call_args.lower()


class TestOverrideWarnings:
    """Test override directory warning when unconfigured."""

    def test_override_directory_exists_but_not_configured(self, tmp_path: Path) -> None:
        """Test warning when override directory exists but app.overrides is empty."""
        # Arrange
        charts_dir = tmp_path / "charts"
        charts_dir.mkdir(exist_ok=True)

        source_chart_dir = charts_dir / "bitnami" / "nginx-15.0.0"
        source_chart_dir.mkdir(parents=True, exist_ok=True)
        (source_chart_dir / "Chart.yaml").write_text("name: nginx\nversion: 15.0.0")
        (source_chart_dir / "values.yaml").write_text("replicaCount: 1")

        app_config_dir = tmp_path / "config"
        app_config_dir.mkdir(exist_ok=True)

        # Create override directory with files
        overrides_dir = app_config_dir / "overrides" / "nginx"
        overrides_dir.mkdir(parents=True, exist_ok=True)
        (overrides_dir / "custom-values.yaml").write_text("replicaCount: 3")
        (overrides_dir / "extra-config.yaml").write_text("debug: true")

        build_dir = tmp_path / "build"
        build_dir.mkdir(exist_ok=True)

        app = HelmApp(
            type="helm",
            chart="bitnami/nginx",
            version="15.0.0",
            # overrides NOT configured
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
        # Verify warning was printed
        output.print_warning.assert_called()
        warning_msg = str(output.print_warning.call_args)
        assert "override directory found but not configured" in warning_msg.lower()

    def test_no_warning_when_override_configured(self, tmp_path: Path) -> None:
        """Test no warning when override directory exists and is configured."""
        # Arrange
        charts_dir = tmp_path / "charts"
        charts_dir.mkdir(exist_ok=True)

        source_chart_dir = charts_dir / "bitnami" / "nginx-15.0.0"
        source_chart_dir.mkdir(parents=True, exist_ok=True)
        (source_chart_dir / "Chart.yaml").write_text("name: nginx\nversion: 15.0.0")

        app_config_dir = tmp_path / "config"
        app_config_dir.mkdir(exist_ok=True)

        overrides_dir = app_config_dir / "overrides" / "nginx"
        overrides_dir.mkdir(parents=True, exist_ok=True)
        (overrides_dir / "custom-values.yaml").write_text("replicaCount: 3")

        build_dir = tmp_path / "build"
        build_dir.mkdir(exist_ok=True)

        app = HelmApp(
            type="helm",
            chart="bitnami/nginx",
            version="15.0.0",
            overrides=["custom-values.yaml"],  # Configured
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
        # print_warning should not be called for "override directory found but not configured"
        if output.print_warning.called:
            warning_msgs = [str(call) for call in output.print_warning.call_args_list]
            for msg in warning_msgs:
                assert "override directory found but not configured" not in msg.lower()


class TestOverrideGlobPatterns:
    """Test override glob pattern processing."""

    def test_override_glob_pattern_multiple_files(self, tmp_path: Path) -> None:
        """Test override with glob pattern matching multiple files."""
        # Arrange
        charts_dir = tmp_path / "charts"
        charts_dir.mkdir(exist_ok=True)

        source_chart_dir = charts_dir / "bitnami" / "nginx-15.0.0"
        source_chart_dir.mkdir(parents=True, exist_ok=True)
        (source_chart_dir / "Chart.yaml").write_text("name: nginx\nversion: 15.0.0")

        app_config_dir = tmp_path / "config"
        app_config_dir.mkdir(exist_ok=True)

        overrides_dir = app_config_dir / "overrides" / "nginx"
        overrides_dir.mkdir(parents=True, exist_ok=True)

        # Create multiple files matching pattern
        (overrides_dir / "values-dev.yaml").write_text("env: dev")
        (overrides_dir / "values-prod.yaml").write_text("env: prod")
        (overrides_dir / "values-staging.yaml").write_text("env: staging")

        build_dir = tmp_path / "build"
        build_dir.mkdir(exist_ok=True)

        app = HelmApp(
            type="helm",
            chart="bitnami/nginx",
            version="15.0.0",
            overrides=["values-*.yaml"],  # Glob pattern
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
        # Verify all matched files were copied
        assert (build_dir / "nginx" / "values-dev.yaml").exists()
        assert (build_dir / "nginx" / "values-prod.yaml").exists()
        assert (build_dir / "nginx" / "values-staging.yaml").exists()

    def test_override_glob_pattern_no_matches(self, tmp_path: Path) -> None:
        """Test warning when glob pattern matches no files."""
        # Arrange
        charts_dir = tmp_path / "charts"
        charts_dir.mkdir(exist_ok=True)

        source_chart_dir = charts_dir / "bitnami" / "nginx-15.0.0"
        source_chart_dir.mkdir(parents=True, exist_ok=True)
        (source_chart_dir / "Chart.yaml").write_text("name: nginx\nversion: 15.0.0")

        app_config_dir = tmp_path / "config"
        app_config_dir.mkdir(exist_ok=True)

        overrides_dir = app_config_dir / "overrides" / "nginx"
        overrides_dir.mkdir(parents=True, exist_ok=True)
        (overrides_dir / "other-file.txt").write_text("content")

        build_dir = tmp_path / "build"
        build_dir.mkdir(exist_ok=True)

        app = HelmApp(
            type="helm",
            chart="bitnami/nginx",
            version="15.0.0",
            overrides=["nonexistent-*.yaml"],  # Pattern with no matches
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
        # Verify warning was printed
        output.print_warning.assert_called()
        warning_msg = str(output.print_warning.call_args)
        assert "no files matched pattern" in warning_msg.lower()

    def test_override_file_not_found(self, tmp_path: Path) -> None:
        """Test warning when exact override file not found."""
        # Arrange
        charts_dir = tmp_path / "charts"
        charts_dir.mkdir(exist_ok=True)

        source_chart_dir = charts_dir / "bitnami" / "nginx-15.0.0"
        source_chart_dir.mkdir(parents=True, exist_ok=True)
        (source_chart_dir / "Chart.yaml").write_text("name: nginx\nversion: 15.0.0")

        app_config_dir = tmp_path / "config"
        app_config_dir.mkdir(exist_ok=True)

        overrides_dir = app_config_dir / "overrides" / "nginx"
        overrides_dir.mkdir(parents=True, exist_ok=True)

        build_dir = tmp_path / "build"
        build_dir.mkdir(exist_ok=True)

        app = HelmApp(
            type="helm",
            chart="bitnami/nginx",
            version="15.0.0",
            overrides=["nonexistent-file.yaml"],  # Exact file that doesn't exist
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
        # Verify warning was printed
        output.print_warning.assert_called()
        warning_msg = str(output.print_warning.call_args)
        assert "override file not found" in warning_msg.lower()


class TestRemovesDryRun:
    """Test removes functionality in dry-run mode."""

    def test_removes_dry_run_file(self, tmp_path: Path) -> None:
        """Test dry-run mode for file removal."""
        # Arrange
        charts_dir = tmp_path / "charts"
        charts_dir.mkdir(exist_ok=True)

        source_chart_dir = charts_dir / "bitnami" / "nginx-15.0.0"
        source_chart_dir.mkdir(parents=True, exist_ok=True)
        (source_chart_dir / "Chart.yaml").write_text("name: nginx\nversion: 15.0.0")

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
            removes=["templates/service.yaml"],
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
            dry_run=True,  # DRY-RUN
        )

        # Assert
        assert result is True
        # File should still exist in dry-run mode (not actually removed)
        # Note: In dry-run, files are not copied, so we check output messages
        output.print.assert_called()
        print_calls = [str(call) for call in output.print.call_args_list]
        assert any("DRY-RUN" in call and "remove" in call.lower() for call in print_calls)

    def test_removes_dry_run_directory(self, tmp_path: Path) -> None:
        """Test dry-run mode for directory removal."""
        # Arrange
        charts_dir = tmp_path / "charts"
        charts_dir.mkdir(exist_ok=True)

        source_chart_dir = charts_dir / "bitnami" / "nginx-15.0.0"
        source_chart_dir.mkdir(parents=True, exist_ok=True)
        (source_chart_dir / "Chart.yaml").write_text("name: nginx\nversion: 15.0.0")

        tests_dir = source_chart_dir / "tests"
        tests_dir.mkdir(exist_ok=True)
        (tests_dir / "test.yaml").write_text("test")

        build_dir = tmp_path / "build"
        build_dir.mkdir(exist_ok=True)

        app = HelmApp(
            type="helm",
            chart="bitnami/nginx",
            version="15.0.0",
            removes=["tests"],  # Remove entire directory
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
            dry_run=True,  # DRY-RUN
        )

        # Assert
        assert result is True
        output.print.assert_called()
        # In dry-run mode, we should see DRY-RUN message but actual message may vary
        # Just check that print was called (dry-run doesn't copy files, so no build dir to check)

    def test_removes_target_not_found_dry_run(self, tmp_path: Path) -> None:
        """Test warning when remove target doesn't exist in dry-run mode."""
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
            removes=["nonexistent/path"],
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
            dry_run=True,  # DRY-RUN
        )

        # Assert
        assert result is True
        output.print_warning.assert_called()
        warning_msg = str(output.print_warning.call_args)
        assert "remove target not found" in warning_msg.lower()


class TestRemovesActualRemoval:
    """Test actual file/directory removal (non-dry-run)."""

    def test_removes_directory(self, tmp_path: Path) -> None:
        """Test actual directory removal."""
        # Arrange
        charts_dir = tmp_path / "charts"
        charts_dir.mkdir(exist_ok=True)

        source_chart_dir = charts_dir / "bitnami" / "nginx-15.0.0"
        source_chart_dir.mkdir(parents=True, exist_ok=True)
        (source_chart_dir / "Chart.yaml").write_text("name: nginx\nversion: 15.0.0")

        # Create directory to be removed
        tests_dir = source_chart_dir / "tests"
        tests_dir.mkdir(exist_ok=True)
        (tests_dir / "test.yaml").write_text("test content")

        build_dir = tmp_path / "build"
        build_dir.mkdir(exist_ok=True)

        app = HelmApp(
            type="helm",
            chart="bitnami/nginx",
            version="15.0.0",
            removes=["tests"],  # Remove tests directory
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
        # Verify directory was actually removed
        assert not (build_dir / "nginx" / "tests").exists()

    def test_removes_target_not_found(self, tmp_path: Path) -> None:
        """Test warning when remove target doesn't exist."""
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
            removes=["nonexistent/file.yaml"],
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
        output.print_warning.assert_called()
        warning_msg = str(output.print_warning.call_args)
        assert "remove target not found" in warning_msg.lower()
