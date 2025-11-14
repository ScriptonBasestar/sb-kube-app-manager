"""Unit tests for deploy.py - deploy_yaml_app function.

Tests verify:
- YAML manifest deployment
- Namespace handling
- Label injection
- Variable expansion
- Dry-run mode
"""

from pathlib import Path
from unittest.mock import MagicMock, patch

import pytest

from sbkube.commands.deploy import deploy_yaml_app
from sbkube.models.config_model import YamlApp
from sbkube.utils.output_manager import OutputManager


class TestDeployYamlAppBasic:
    """Test basic YAML app deployment scenarios."""

    @patch("sbkube.commands.deploy.run_command")
    def test_deploy_yaml_app_success(self, mock_run_command, tmp_path: Path) -> None:
        """Test successful YAML app deployment."""
        # Arrange
        app_config_dir = tmp_path / "app_001_nginx"
        app_config_dir.mkdir(exist_ok=True)

        # Create manifest file
        manifest_file = app_config_dir / "deployment.yaml"
        manifest_file.write_text("apiVersion: apps/v1\nkind: Deployment")

        app = YamlApp(
            type="yaml",
            manifests=["deployment.yaml"],
            namespace="default",
        )

        mock_run_command.return_value = (0, "deployment.apps/nginx created", "")
        output = MagicMock(spec=OutputManager)

        # Act
        result = deploy_yaml_app(
            app_name="nginx",
            app=app,
            base_dir=tmp_path,
            app_config_dir=app_config_dir,
            output=output,
            dry_run=False,
        )

        # Assert
        assert result is True
        # Verify kubectl apply was called
        mock_run_command.assert_called()
        call_args = mock_run_command.call_args[0][0]
        assert "kubectl" in call_args
        assert "apply" in call_args
        assert "-f" in call_args

    @patch("sbkube.commands.deploy.run_command")
    def test_deploy_yaml_app_dry_run(self, mock_run_command, tmp_path: Path) -> None:
        """Test YAML app deployment in dry-run mode."""
        # Arrange
        app_config_dir = tmp_path / "app_001_nginx"
        app_config_dir.mkdir(exist_ok=True)

        manifest_file = app_config_dir / "deployment.yaml"
        manifest_file.write_text("apiVersion: apps/v1\nkind: Deployment")

        app = YamlApp(
            type="yaml",
            manifests=["deployment.yaml"],
            namespace="default",
        )

        mock_run_command.return_value = (0, "deployment.apps/nginx configured (dry run)", "")
        output = MagicMock(spec=OutputManager)

        # Act
        result = deploy_yaml_app(
            app_name="nginx",
            app=app,
            base_dir=tmp_path,
            app_config_dir=app_config_dir,
            output=output,
            dry_run=True,
        )

        # Assert
        assert result is True
        # Verify --dry-run was included
        call_args = mock_run_command.call_args[0][0]
        assert "--dry-run=client" in call_args or "--dry-run" in call_args


class TestDeployYamlAppNamespace:
    """Test namespace handling."""

    @patch("sbkube.commands.deploy.run_command")
    def test_app_namespace_override(self, mock_run_command, tmp_path: Path) -> None:
        """Test that app.namespace overrides config namespace."""
        # Arrange
        app_config_dir = tmp_path / "app_001_nginx"
        app_config_dir.mkdir(exist_ok=True)

        manifest_file = app_config_dir / "deployment.yaml"
        manifest_file.write_text("apiVersion: apps/v1\nkind: Deployment")

        app = YamlApp(
            type="yaml",
            manifests=["deployment.yaml"],
            namespace="app-ns",  # App-specific namespace
        )

        mock_run_command.return_value = (0, "deployment.apps/nginx created", "")
        output = MagicMock(spec=OutputManager)

        # Act
        result = deploy_yaml_app(
            app_name="nginx",
            app=app,
            base_dir=tmp_path,
            app_config_dir=app_config_dir,
            output=output,
            config_namespace="config-ns",  # Config namespace (should be overridden)
            dry_run=False,
        )

        # Assert
        assert result is True
        call_args = mock_run_command.call_args[0][0]
        # Should use app namespace, not config namespace
        assert "-n" in call_args or "--namespace" in call_args
        assert "app-ns" in call_args

    @patch("sbkube.commands.deploy.run_command")
    def test_config_namespace_fallback(self, mock_run_command, tmp_path: Path) -> None:
        """Test fallback to config namespace when app.namespace not set."""
        # Arrange
        app_config_dir = tmp_path / "app_001_nginx"
        app_config_dir.mkdir(exist_ok=True)

        manifest_file = app_config_dir / "deployment.yaml"
        manifest_file.write_text("apiVersion: apps/v1\nkind: Deployment")

        app = YamlApp(
            type="yaml",
            manifests=["deployment.yaml"],
            # No namespace specified
        )

        mock_run_command.return_value = (0, "deployment.apps/nginx created", "")
        output = MagicMock(spec=OutputManager)

        # Act
        result = deploy_yaml_app(
            app_name="nginx",
            app=app,
            base_dir=tmp_path,
            app_config_dir=app_config_dir,
            output=output,
            config_namespace="config-ns",  # Should use this
            dry_run=False,
        )

        # Assert
        assert result is True
        call_args = mock_run_command.call_args[0][0]
        assert "config-ns" in call_args


class TestDeployYamlAppMultipleManifests:
    """Test deployment with multiple manifests."""

    @patch("sbkube.commands.deploy.run_command")
    def test_deploy_multiple_manifests(self, mock_run_command, tmp_path: Path) -> None:
        """Test deploying multiple YAML manifests."""
        # Arrange
        app_config_dir = tmp_path / "app_001_nginx"
        app_config_dir.mkdir(exist_ok=True)

        # Create multiple manifest files
        (app_config_dir / "deployment.yaml").write_text("apiVersion: apps/v1\nkind: Deployment")
        (app_config_dir / "service.yaml").write_text("apiVersion: v1\nkind: Service")

        app = YamlApp(
            type="yaml",
            manifests=["deployment.yaml", "service.yaml"],
            namespace="default",
        )

        mock_run_command.return_value = (0, "resource created", "")
        output = MagicMock(spec=OutputManager)

        # Act
        result = deploy_yaml_app(
            app_name="nginx",
            app=app,
            base_dir=tmp_path,
            app_config_dir=app_config_dir,
            output=output,
            dry_run=False,
        )

        # Assert
        assert result is True
        # Should be called twice (once for each manifest)
        assert mock_run_command.call_count == 2


class TestDeployYamlAppErrors:
    """Test error scenarios."""

    @patch("sbkube.commands.deploy.run_command")
    def test_manifest_file_not_found(self, mock_run_command, tmp_path: Path) -> None:
        """Test error when manifest file doesn't exist."""
        # Arrange
        app_config_dir = tmp_path / "app_001_nginx"
        app_config_dir.mkdir(exist_ok=True)

        app = YamlApp(
            type="yaml",
            manifests=["missing.yaml"],  # File doesn't exist
            namespace="default",
        )

        output = MagicMock(spec=OutputManager)

        # Act
        result = deploy_yaml_app(
            app_name="nginx",
            app=app,
            base_dir=tmp_path,
            app_config_dir=app_config_dir,
            output=output,
            dry_run=False,
        )

        # Assert
        assert result is False
        output.print_error.assert_called()

    @patch("sbkube.commands.deploy.run_command")
    def test_kubectl_apply_failure(self, mock_run_command, tmp_path: Path) -> None:
        """Test handling of kubectl apply failure."""
        # Arrange
        app_config_dir = tmp_path / "app_001_nginx"
        app_config_dir.mkdir(exist_ok=True)

        manifest_file = app_config_dir / "deployment.yaml"
        manifest_file.write_text("apiVersion: apps/v1\nkind: Deployment")

        app = YamlApp(
            type="yaml",
            manifests=["deployment.yaml"],
            namespace="default",
        )

        # Mock kubectl apply failure
        mock_run_command.return_value = (1, "", "Error: namespace not found")
        output = MagicMock(spec=OutputManager)

        # Act
        result = deploy_yaml_app(
            app_name="nginx",
            app=app,
            base_dir=tmp_path,
            app_config_dir=app_config_dir,
            output=output,
            dry_run=False,
        )

        # Assert
        assert result is False
        output.print_error.assert_called()
