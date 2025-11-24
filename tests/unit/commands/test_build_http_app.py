"""Unit tests for build.py - build_http_app function.

Tests verify:
- HTTP app building (copy downloaded file to build/)
- Dry-run mode
- Error scenarios
"""

from pathlib import Path
from unittest.mock import MagicMock

from sbkube.commands.build import build_http_app
from sbkube.models.config_model import HttpApp
from sbkube.utils.output_manager import OutputManager


class TestBuildHttpAppBasic:
    """Test basic HTTP app build scenarios."""

    def test_build_http_app_success(self, tmp_path: Path) -> None:
        """Test building HTTP app successfully."""
        # Arrange
        app_config_dir = tmp_path / "config"
        app_config_dir.mkdir(exist_ok=True)

        # Create downloaded file (from prepare step)
        downloaded_file = app_config_dir / "app.yaml"
        downloaded_file.write_text("apiVersion: v1\nkind: ConfigMap")

        build_dir = tmp_path / "build"
        build_dir.mkdir(exist_ok=True)

        app = HttpApp(
            type="http",
            url="https://example.com/app.yaml",
            dest="app.yaml",
        )

        output = MagicMock(spec=OutputManager)

        # Act
        result = build_http_app(
            app_name="my-app",
            app=app,
            base_dir=tmp_path,
            build_dir=build_dir,
            app_config_dir=app_config_dir,
            output=output,
            dry_run=False,
        )

        # Assert
        assert result is True
        # Verify file copied to build directory
        target_file = build_dir / "my-app" / "app.yaml"
        assert target_file.exists()
        assert target_file.read_text() == "apiVersion: v1\nkind: ConfigMap"

    def test_build_http_app_dry_run(self, tmp_path: Path) -> None:
        """Test dry-run mode doesn't copy files."""
        # Arrange
        app_config_dir = tmp_path / "config"
        app_config_dir.mkdir(exist_ok=True)

        downloaded_file = app_config_dir / "app.yaml"
        downloaded_file.write_text("apiVersion: v1\nkind: ConfigMap")

        build_dir = tmp_path / "build"
        build_dir.mkdir(exist_ok=True)

        app = HttpApp(
            type="http",
            url="https://example.com/app.yaml",
            dest="app.yaml",
        )

        output = MagicMock(spec=OutputManager)

        # Act
        result = build_http_app(
            app_name="my-app",
            app=app,
            base_dir=tmp_path,
            build_dir=build_dir,
            app_config_dir=app_config_dir,
            output=output,
            dry_run=True,  # Dry-run mode
        )

        # Assert
        assert result is True
        # File should NOT be copied in dry-run
        target_file = build_dir / "my-app" / "app.yaml"
        assert not target_file.exists()


class TestBuildHttpAppErrors:
    """Test error scenarios."""

    def test_downloaded_file_not_found(self, tmp_path: Path) -> None:
        """Test error when downloaded file doesn't exist."""
        # Arrange
        app_config_dir = tmp_path / "config"
        app_config_dir.mkdir(exist_ok=True)

        # Downloaded file does NOT exist
        build_dir = tmp_path / "build"
        build_dir.mkdir(exist_ok=True)

        app = HttpApp(
            type="http",
            url="https://example.com/app.yaml",
            dest="app.yaml",
        )

        output = MagicMock(spec=OutputManager)

        # Act
        result = build_http_app(
            app_name="my-app",
            app=app,
            base_dir=tmp_path,
            build_dir=build_dir,
            app_config_dir=app_config_dir,
            output=output,
            dry_run=False,
        )

        # Assert
        assert result is False
        output.print_error.assert_called()
        # Verify error message mentions prepare
        call_args = str(output.print_error.call_args)
        assert "not found" in call_args.lower()


class TestBuildHttpAppFileTypes:
    """Test various file types."""

    def test_build_yaml_file(self, tmp_path: Path) -> None:
        """Test building YAML manifest."""
        # Arrange
        app_config_dir = tmp_path / "config"
        app_config_dir.mkdir(exist_ok=True)

        downloaded_file = app_config_dir / "manifest.yaml"
        downloaded_file.write_text(
            "apiVersion: v1\nkind: Service\nmetadata:\n  name: my-service"
        )

        build_dir = tmp_path / "build"
        build_dir.mkdir(exist_ok=True)

        app = HttpApp(
            type="http",
            url="https://example.com/manifest.yaml",
            dest="manifest.yaml",
        )

        output = MagicMock(spec=OutputManager)

        # Act
        result = build_http_app(
            app_name="svc-app",
            app=app,
            base_dir=tmp_path,
            build_dir=build_dir,
            app_config_dir=app_config_dir,
            output=output,
            dry_run=False,
        )

        # Assert
        assert result is True
        target_file = build_dir / "svc-app" / "manifest.yaml"
        assert target_file.exists()

    def test_build_json_file(self, tmp_path: Path) -> None:
        """Test building JSON manifest."""
        # Arrange
        app_config_dir = tmp_path / "config"
        app_config_dir.mkdir(exist_ok=True)

        downloaded_file = app_config_dir / "config.json"
        downloaded_file.write_text('{"apiVersion": "v1", "kind": "ConfigMap"}')

        build_dir = tmp_path / "build"
        build_dir.mkdir(exist_ok=True)

        app = HttpApp(
            type="http",
            url="https://example.com/config.json",
            dest="config.json",
        )

        output = MagicMock(spec=OutputManager)

        # Act
        result = build_http_app(
            app_name="json-app",
            app=app,
            base_dir=tmp_path,
            build_dir=build_dir,
            app_config_dir=app_config_dir,
            output=output,
            dry_run=False,
        )

        # Assert
        assert result is True
        target_file = build_dir / "json-app" / "config.json"
        assert target_file.exists()
        assert target_file.read_text() == '{"apiVersion": "v1", "kind": "ConfigMap"}'
