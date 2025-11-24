"""Unit tests for deploy.py - deploy_kustomize_app function.

Tests verify:
- Kustomize app deployment
- kustomization.yaml handling
- Namespace handling
- Label injection
- Dry-run mode
"""

from pathlib import Path
from unittest.mock import MagicMock, patch

from sbkube.commands.deploy import deploy_kustomize_app
from sbkube.models.config_model import KustomizeApp
from sbkube.utils.output_manager import OutputManager


class TestDeployKustomizeAppBasic:
    """Test basic Kustomize app deployment scenarios."""

    @patch("sbkube.commands.deploy.run_command")
    def test_deploy_kustomize_app_success(self, mock_run_command, tmp_path: Path) -> None:
        """Test successful Kustomize app deployment."""
        # Arrange
        app_config_dir = tmp_path / "app_001_nginx"
        app_config_dir.mkdir(exist_ok=True)

        # Create kustomization directory
        kustomize_dir = app_config_dir / "kustomize"
        kustomize_dir.mkdir(exist_ok=True)

        # Create kustomization.yaml
        kustomization_file = kustomize_dir / "kustomization.yaml"
        kustomization_file.write_text("""
apiVersion: kustomize.config.k8s.io/v1beta1
kind: Kustomization
resources:
  - deployment.yaml
""")

        # Create deployment.yaml
        deployment_file = kustomize_dir / "deployment.yaml"
        deployment_file.write_text("apiVersion: apps/v1\nkind: Deployment")

        app = KustomizeApp(
            type="kustomize",
            path="kustomize",
            namespace="default",
        )

        # Mock responses:
        # 1. kustomize build
        # 2. kubectl apply
        mock_run_command.side_effect = [
            (0, "apiVersion: apps/v1\nkind: Deployment", ""),  # kustomize build
            (0, "deployment.apps/nginx created", ""),  # kubectl apply
        ]
        output = MagicMock(spec=OutputManager)

        # Act
        result = deploy_kustomize_app(
            app_name="nginx",
            app=app,
            base_dir=tmp_path,
            app_config_dir=app_config_dir,
            output=output,
            dry_run=False,
        )

        # Assert
        assert result is True
        # Verify both kustomize build and kubectl apply were called
        assert mock_run_command.call_count == 2

        # First call should be kustomize build
        first_call = mock_run_command.call_args_list[0][0][0]
        assert "kustomize" in first_call or "kubectl" in first_call
        assert "build" in first_call

        # Second call should be kubectl apply
        second_call = mock_run_command.call_args_list[1][0][0]
        assert "kubectl" in second_call
        assert "apply" in second_call

    @patch("sbkube.commands.deploy.run_command")
    def test_deploy_kustomize_app_dry_run(self, mock_run_command, tmp_path: Path) -> None:
        """Test Kustomize app deployment in dry-run mode."""
        # Arrange
        app_config_dir = tmp_path / "app_001_nginx"
        app_config_dir.mkdir(exist_ok=True)

        kustomize_dir = app_config_dir / "kustomize"
        kustomize_dir.mkdir(exist_ok=True)

        kustomization_file = kustomize_dir / "kustomization.yaml"
        kustomization_file.write_text("apiVersion: kustomize.config.k8s.io/v1beta1\nkind: Kustomization")

        app = KustomizeApp(
            type="kustomize",
            path="kustomize",
            namespace="default",
        )

        mock_run_command.side_effect = [
            (0, "apiVersion: apps/v1\nkind: Deployment", ""),
            (0, "deployment.apps/nginx configured (dry run)", ""),
        ]
        output = MagicMock(spec=OutputManager)

        # Act
        result = deploy_kustomize_app(
            app_name="nginx",
            app=app,
            base_dir=tmp_path,
            app_config_dir=app_config_dir,
            output=output,
            dry_run=True,
        )

        # Assert
        assert result is True
        # Verify --dry-run was included in kubectl apply
        second_call = mock_run_command.call_args_list[1][0][0]
        assert "--dry-run=client" in second_call or "--dry-run" in second_call


class TestDeployKustomizeAppNamespace:
    """Test namespace handling."""

    @patch("sbkube.commands.deploy.run_command")
    def test_app_namespace_override(self, mock_run_command, tmp_path: Path) -> None:
        """Test that app.namespace overrides config namespace."""
        # Arrange
        app_config_dir = tmp_path / "app_001_nginx"
        app_config_dir.mkdir(exist_ok=True)

        kustomize_dir = app_config_dir / "kustomize"
        kustomize_dir.mkdir(exist_ok=True)
        kustomization_file = kustomize_dir / "kustomization.yaml"
        kustomization_file.write_text("apiVersion: kustomize.config.k8s.io/v1beta1\nkind: Kustomization")

        app = KustomizeApp(
            type="kustomize",
            path="kustomize",
            namespace="app-ns",  # App-specific namespace
        )

        mock_run_command.side_effect = [
            (0, "apiVersion: apps/v1\nkind: Deployment", ""),
            (0, "deployment.apps/nginx created", ""),
        ]
        output = MagicMock(spec=OutputManager)

        # Act
        result = deploy_kustomize_app(
            app_name="nginx",
            app=app,
            base_dir=tmp_path,
            app_config_dir=app_config_dir,
            output=output,
            config_namespace="config-ns",  # Should be overridden
            dry_run=False,
        )

        # Assert
        assert result is True
        second_call = mock_run_command.call_args_list[1][0][0]
        # Should use app namespace
        assert "-n" in second_call or "--namespace" in second_call
        assert "app-ns" in second_call


class TestDeployKustomizeAppErrors:
    """Test error scenarios."""

    @patch("sbkube.commands.deploy.run_command")
    def test_kustomize_path_not_found(self, mock_run_command, tmp_path: Path) -> None:
        """Test error when kustomize path doesn't exist."""
        # Arrange
        app_config_dir = tmp_path / "app_001_nginx"
        app_config_dir.mkdir(exist_ok=True)

        app = KustomizeApp(
            type="kustomize",
            path="missing",  # Path doesn't exist
            namespace="default",
        )

        output = MagicMock(spec=OutputManager)

        # Act
        result = deploy_kustomize_app(
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
        call_args = output.print_error.call_args[0][0]
        assert "not found" in call_args.lower()

    @patch("sbkube.commands.deploy.run_command")
    def test_kustomize_build_failure(self, mock_run_command, tmp_path: Path) -> None:
        """Test handling of kustomize build failure."""
        # Arrange
        app_config_dir = tmp_path / "app_001_nginx"
        app_config_dir.mkdir(exist_ok=True)

        kustomize_dir = app_config_dir / "kustomize"
        kustomize_dir.mkdir(exist_ok=True)
        kustomization_file = kustomize_dir / "kustomization.yaml"
        kustomization_file.write_text("invalid yaml")

        app = KustomizeApp(
            type="kustomize",
            path="kustomize",
            namespace="default",
        )

        # Mock kustomize build failure
        mock_run_command.return_value = (1, "", "Error: invalid kustomization.yaml")
        output = MagicMock(spec=OutputManager)

        # Act
        result = deploy_kustomize_app(
            app_name="nginx",
            app=app,
            base_dir=tmp_path,
            app_config_dir=app_config_dir,
            output=output,
            dry_run=False,
        )

        # Assert
        assert result is False

    @patch("sbkube.commands.deploy.run_command")
    def test_kubectl_apply_failure(self, mock_run_command, tmp_path: Path) -> None:
        """Test handling of kubectl apply failure after successful kustomize build."""
        # Arrange
        app_config_dir = tmp_path / "app_001_nginx"
        app_config_dir.mkdir(exist_ok=True)

        kustomize_dir = app_config_dir / "kustomize"
        kustomize_dir.mkdir(exist_ok=True)
        kustomization_file = kustomize_dir / "kustomization.yaml"
        kustomization_file.write_text("apiVersion: kustomize.config.k8s.io/v1beta1\nkind: Kustomization")

        app = KustomizeApp(
            type="kustomize",
            path="kustomize",
            namespace="default",
        )

        # Mock: kustomize build succeeds, kubectl apply fails
        mock_run_command.side_effect = [
            (0, "apiVersion: apps/v1\nkind: Deployment", ""),  # kustomize build OK
            (1, "", "Error: namespace not found"),  # kubectl apply fails
        ]
        output = MagicMock(spec=OutputManager)

        # Act
        result = deploy_kustomize_app(
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
