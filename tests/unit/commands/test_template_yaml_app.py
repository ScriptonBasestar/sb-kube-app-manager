"""Unit tests for template.py - template_yaml_app and template_http_app functions.

Tests verify:
- YAML app rendering (combining multiple YAML files)
- HTTP app rendering (copying downloaded files)
- Build directory vs original files
- Error scenarios
"""

from pathlib import Path
from unittest.mock import MagicMock

import pytest

from sbkube.commands.template import template_http_app, template_yaml_app
from sbkube.models.config_model import HttpApp, YamlApp
from sbkube.utils.output_manager import OutputManager


class TestTemplateYamlAppBasic:
    """Test basic YAML app rendering."""

    def test_template_from_build_directory(self, tmp_path: Path) -> None:
        """Test rendering from build/ directory."""
        # Arrange
        build_dir = tmp_path / "build"
        build_dir.mkdir(exist_ok=True)

        app_build_dir = build_dir / "my-app"
        app_build_dir.mkdir(exist_ok=True)
        (app_build_dir / "deployment.yaml").write_text(
            "apiVersion: apps/v1\nkind: Deployment"
        )
        (app_build_dir / "service.yaml").write_text("apiVersion: v1\nkind: Service")

        rendered_dir = tmp_path / "rendered"
        rendered_dir.mkdir(exist_ok=True)

        app = YamlApp(
            type="yaml",
            manifests=["deployment.yaml", "service.yaml"],
        )

        output = MagicMock(spec=OutputManager)

        # Act
        result = template_yaml_app(
            app_name="my-app",
            app=app,
            base_dir=tmp_path,
            build_dir=build_dir,
            app_config_dir=tmp_path / "config",
            rendered_dir=rendered_dir,
            output=output,
        )

        # Assert
        assert result is True
        rendered_file = rendered_dir / "my-app.yaml"
        assert rendered_file.exists()
        content = rendered_file.read_text()
        assert "apiVersion: apps/v1" in content
        assert "apiVersion: v1" in content
        assert "---" in content  # Separator between files

    def test_template_from_original_files(self, tmp_path: Path) -> None:
        """Test rendering from original files (no build/)."""
        # Arrange
        app_config_dir = tmp_path / "config"
        app_config_dir.mkdir(exist_ok=True)

        (app_config_dir / "deployment.yaml").write_text(
            "apiVersion: apps/v1\nkind: Deployment"
        )
        (app_config_dir / "service.yaml").write_text("apiVersion: v1\nkind: Service")

        build_dir = tmp_path / "build"
        build_dir.mkdir(exist_ok=True)
        # No app_name subdirectory in build/

        rendered_dir = tmp_path / "rendered"
        rendered_dir.mkdir(exist_ok=True)

        app = YamlApp(
            type="yaml",
            manifests=["deployment.yaml", "service.yaml"],
        )

        output = MagicMock(spec=OutputManager)

        # Act
        result = template_yaml_app(
            app_name="my-app",
            app=app,
            base_dir=tmp_path,
            build_dir=build_dir,
            app_config_dir=app_config_dir,
            rendered_dir=rendered_dir,
            output=output,
        )

        # Assert
        assert result is True
        rendered_file = rendered_dir / "my-app.yaml"
        assert rendered_file.exists()
        content = rendered_file.read_text()
        assert "Deployment" in content
        assert "Service" in content

    def test_template_single_file(self, tmp_path: Path) -> None:
        """Test rendering single YAML file."""
        # Arrange
        build_dir = tmp_path / "build"
        build_dir.mkdir(exist_ok=True)

        app_build_dir = build_dir / "my-app"
        app_build_dir.mkdir(exist_ok=True)
        (app_build_dir / "manifest.yaml").write_text(
            "apiVersion: apps/v1\nkind: Deployment"
        )

        rendered_dir = tmp_path / "rendered"
        rendered_dir.mkdir(exist_ok=True)

        app = YamlApp(
            type="yaml",
            manifests=["manifest.yaml"],
        )

        output = MagicMock(spec=OutputManager)

        # Act
        result = template_yaml_app(
            app_name="my-app",
            app=app,
            base_dir=tmp_path,
            build_dir=build_dir,
            app_config_dir=tmp_path / "config",
            rendered_dir=rendered_dir,
            output=output,
        )

        # Assert
        assert result is True
        rendered_file = rendered_dir / "my-app.yaml"
        assert rendered_file.exists()
        assert "Deployment" in rendered_file.read_text()


class TestTemplateYamlAppErrors:
    """Test error scenarios for YAML app."""

    def test_no_yaml_files_in_build(self, tmp_path: Path) -> None:
        """Test error when no YAML files found in build directory."""
        # Arrange
        build_dir = tmp_path / "build"
        build_dir.mkdir(exist_ok=True)

        app_build_dir = build_dir / "my-app"
        app_build_dir.mkdir(exist_ok=True)
        # No YAML files

        rendered_dir = tmp_path / "rendered"
        rendered_dir.mkdir(exist_ok=True)

        app = YamlApp(
            type="yaml",
            manifests=["deployment.yaml"],
        )

        output = MagicMock(spec=OutputManager)

        # Act
        result = template_yaml_app(
            app_name="my-app",
            app=app,
            base_dir=tmp_path,
            build_dir=build_dir,
            app_config_dir=tmp_path / "config",
            rendered_dir=rendered_dir,
            output=output,
        )

        # Assert
        assert result is False
        output.print_error.assert_called()

    def test_file_not_found_in_original_path(self, tmp_path: Path) -> None:
        """Test warning when original file not found."""
        # Arrange
        app_config_dir = tmp_path / "config"
        app_config_dir.mkdir(exist_ok=True)

        build_dir = tmp_path / "build"
        build_dir.mkdir(exist_ok=True)

        rendered_dir = tmp_path / "rendered"
        rendered_dir.mkdir(exist_ok=True)

        app = YamlApp(
            type="yaml",
            manifests=["nonexistent.yaml"],
        )

        output = MagicMock(spec=OutputManager)

        # Act
        result = template_yaml_app(
            app_name="my-app",
            app=app,
            base_dir=tmp_path,
            build_dir=build_dir,
            app_config_dir=app_config_dir,
            rendered_dir=rendered_dir,
            output=output,
        )

        # Assert
        # When no files found, it returns False
        assert result is False


class TestTemplateHttpAppBasic:
    """Test basic HTTP app rendering."""

    def test_template_from_build_directory(self, tmp_path: Path) -> None:
        """Test rendering HTTP app from build/ directory."""
        # Arrange
        build_dir = tmp_path / "build"
        build_dir.mkdir(exist_ok=True)

        app_build_dir = build_dir / "prometheus"
        app_build_dir.mkdir(exist_ok=True)
        (app_build_dir / "prometheus.yaml").write_text(
            "apiVersion: monitoring.coreos.com/v1"
        )

        rendered_dir = tmp_path / "rendered"
        rendered_dir.mkdir(exist_ok=True)

        app = HttpApp(
            type="http",
            url="https://example.com/prometheus.yaml",
            dest="prometheus.yaml",
        )

        output = MagicMock(spec=OutputManager)

        # Act
        result = template_http_app(
            app_name="prometheus",
            app=app,
            base_dir=tmp_path,
            build_dir=build_dir,
            app_config_dir=tmp_path / "config",
            rendered_dir=rendered_dir,
            output=output,
        )

        # Assert
        assert result is True
        # HTTP app files are copied with app_name prefix
        rendered_file = rendered_dir / "prometheus-prometheus.yaml"
        assert rendered_file.exists()

    def test_template_from_original_download(self, tmp_path: Path) -> None:
        """Test rendering from original downloaded file (no build/)."""
        # Arrange
        app_config_dir = tmp_path / "config"
        app_config_dir.mkdir(exist_ok=True)

        downloaded_file = app_config_dir / "prometheus.yaml"
        downloaded_file.write_text("apiVersion: monitoring.coreos.com/v1")

        build_dir = tmp_path / "build"
        build_dir.mkdir(exist_ok=True)
        # No app subdirectory in build/

        rendered_dir = tmp_path / "rendered"
        rendered_dir.mkdir(exist_ok=True)

        app = HttpApp(
            type="http",
            url="https://example.com/prometheus.yaml",
            dest="prometheus.yaml",
        )

        output = MagicMock(spec=OutputManager)

        # Act
        result = template_http_app(
            app_name="prometheus",
            app=app,
            base_dir=tmp_path,
            build_dir=build_dir,
            app_config_dir=app_config_dir,
            rendered_dir=rendered_dir,
            output=output,
        )

        # Assert
        assert result is True
        rendered_file = rendered_dir / "prometheus-prometheus.yaml"
        assert rendered_file.exists()

    def test_template_multiple_files_in_build(self, tmp_path: Path) -> None:
        """Test rendering when build directory has multiple files."""
        # Arrange
        build_dir = tmp_path / "build"
        build_dir.mkdir(exist_ok=True)

        app_build_dir = build_dir / "prometheus"
        app_build_dir.mkdir(exist_ok=True)
        (app_build_dir / "prometheus.yaml").write_text("content1")
        (app_build_dir / "rules.yaml").write_text("content2")

        rendered_dir = tmp_path / "rendered"
        rendered_dir.mkdir(exist_ok=True)

        app = HttpApp(
            type="http",
            url="https://example.com/prometheus.yaml",
            dest="prometheus.yaml",
        )

        output = MagicMock(spec=OutputManager)

        # Act
        result = template_http_app(
            app_name="prometheus",
            app=app,
            base_dir=tmp_path,
            build_dir=build_dir,
            app_config_dir=tmp_path / "config",
            rendered_dir=rendered_dir,
            output=output,
        )

        # Assert
        assert result is True
        # Both files should be copied
        assert (rendered_dir / "prometheus-prometheus.yaml").exists()
        assert (rendered_dir / "prometheus-rules.yaml").exists()


class TestTemplateHttpAppErrors:
    """Test error scenarios for HTTP app."""

    def test_no_files_in_build_directory(self, tmp_path: Path) -> None:
        """Test error when build directory is empty."""
        # Arrange
        build_dir = tmp_path / "build"
        build_dir.mkdir(exist_ok=True)

        app_build_dir = build_dir / "prometheus"
        app_build_dir.mkdir(exist_ok=True)
        # No files

        rendered_dir = tmp_path / "rendered"
        rendered_dir.mkdir(exist_ok=True)

        app = HttpApp(
            type="http",
            url="https://example.com/prometheus.yaml",
            dest="prometheus.yaml",
        )

        output = MagicMock(spec=OutputManager)

        # Act
        result = template_http_app(
            app_name="prometheus",
            app=app,
            base_dir=tmp_path,
            build_dir=build_dir,
            app_config_dir=tmp_path / "config",
            rendered_dir=rendered_dir,
            output=output,
        )

        # Assert
        assert result is False
        output.print_error.assert_called()

    def test_downloaded_file_not_found(self, tmp_path: Path) -> None:
        """Test error when original downloaded file doesn't exist."""
        # Arrange
        app_config_dir = tmp_path / "config"
        app_config_dir.mkdir(exist_ok=True)

        build_dir = tmp_path / "build"
        build_dir.mkdir(exist_ok=True)

        rendered_dir = tmp_path / "rendered"
        rendered_dir.mkdir(exist_ok=True)

        app = HttpApp(
            type="http",
            url="https://example.com/prometheus.yaml",
            dest="nonexistent.yaml",
        )

        output = MagicMock(spec=OutputManager)

        # Act
        result = template_http_app(
            app_name="prometheus",
            app=app,
            base_dir=tmp_path,
            build_dir=build_dir,
            app_config_dir=app_config_dir,
            rendered_dir=rendered_dir,
            output=output,
        )

        # Assert
        assert result is False
        output.print_error.assert_called()
