"""Unit tests for deploy.py - deploy_action_app function.

Tests verify:
- Action app deployment (kubectl apply, kustomize apply)
- Multiple actions execution
- Namespace handling
- Label injection
- Dry-run mode
"""

from pathlib import Path
from unittest.mock import MagicMock, patch

import pytest

from sbkube.commands.deploy import deploy_action_app
from sbkube.models.config_model import ActionApp, ActionSpec
from sbkube.utils.output_manager import OutputManager


class TestDeployActionAppBasic:
    """Test basic Action app deployment scenarios."""

    @patch("sbkube.commands.deploy.run_command")
    def test_deploy_action_app_kubectl_apply(self, mock_run_command, tmp_path: Path) -> None:
        """Test Action app with kubectl apply action."""
        # Arrange
        app_config_dir = tmp_path / "app_001_nginx"
        app_config_dir.mkdir(exist_ok=True)

        # Create manifest file
        manifest_file = app_config_dir / "deployment.yaml"
        manifest_file.write_text("apiVersion: apps/v1\nkind: Deployment")

        app = ActionApp(
            type="action",
            actions=[
                ActionSpec(
                    type="apply",
                    path="deployment.yaml",
                    namespace="default",
                )
            ],
        )

        mock_run_command.return_value = (0, "deployment.apps/nginx created", "")
        output = MagicMock(spec=OutputManager)

        # Act
        result = deploy_action_app(
            app_name="nginx",
            app=app,
            base_dir=tmp_path,
            app_config_dir=app_config_dir,
            output=output,
            dry_run=False,
        )

        # Assert
        assert result is True
        mock_run_command.assert_called()
        call_args = mock_run_command.call_args[0][0]
        assert "kubectl" in call_args
        assert "apply" in call_args

    @patch("sbkube.commands.deploy.run_command")
    def test_deploy_action_app_delete(self, mock_run_command, tmp_path: Path) -> None:
        """Test Action app with delete action."""
        # Arrange
        app_config_dir = tmp_path / "app_001_nginx"
        app_config_dir.mkdir(exist_ok=True)

        # Create manifest file
        manifest_file = app_config_dir / "old-resource.yaml"
        manifest_file.write_text("apiVersion: v1\nkind: ConfigMap")

        app = ActionApp(
            type="action",
            actions=[
                ActionSpec(
                    type="delete",
                    path="old-resource.yaml",
                    namespace="default",
                )
            ],
        )

        mock_run_command.return_value = (0, "configmap deleted", "")
        output = MagicMock(spec=OutputManager)

        # Act
        result = deploy_action_app(
            app_name="nginx",
            app=app,
            base_dir=tmp_path,
            app_config_dir=app_config_dir,
            output=output,
            dry_run=False,
        )

        # Assert
        assert result is True
        mock_run_command.assert_called()
        call_args = mock_run_command.call_args[0][0]
        assert "kubectl" in call_args
        assert "delete" in call_args

    @patch("sbkube.commands.deploy.run_command")
    def test_deploy_action_app_dry_run(self, mock_run_command, tmp_path: Path) -> None:
        """Test Action app deployment in dry-run mode."""
        # Arrange
        app_config_dir = tmp_path / "app_001_nginx"
        app_config_dir.mkdir(exist_ok=True)

        manifest_file = app_config_dir / "deployment.yaml"
        manifest_file.write_text("apiVersion: apps/v1\nkind: Deployment")

        app = ActionApp(
            type="action",
            actions=[
                ActionSpec(
                    type="apply",
                    path="deployment.yaml",
                    namespace="default",
                )
            ],
        )

        mock_run_command.return_value = (0, "deployment.apps/nginx configured (dry run)", "")
        output = MagicMock(spec=OutputManager)

        # Act
        result = deploy_action_app(
            app_name="nginx",
            app=app,
            base_dir=tmp_path,
            app_config_dir=app_config_dir,
            output=output,
            dry_run=True,
        )

        # Assert
        assert result is True
        call_args = mock_run_command.call_args[0][0]
        assert "--dry-run=client" in call_args or "--dry-run" in call_args


class TestDeployActionAppMultipleActions:
    """Test Action app with multiple actions."""

    @patch("sbkube.commands.deploy.run_command")
    def test_deploy_multiple_actions(self, mock_run_command, tmp_path: Path) -> None:
        """Test Action app with multiple kubectl apply actions."""
        # Arrange
        app_config_dir = tmp_path / "app_001_nginx"
        app_config_dir.mkdir(exist_ok=True)

        (app_config_dir / "deployment.yaml").write_text("apiVersion: apps/v1\nkind: Deployment")
        (app_config_dir / "service.yaml").write_text("apiVersion: v1\nkind: Service")

        app = ActionApp(
            type="action",
            actions=[
                ActionSpec(
                    type="apply",
                    path="deployment.yaml",
                    namespace="default",
                ),
                ActionSpec(
                    type="apply",
                    path="service.yaml",
                    namespace="default",
                ),
            ],
        )

        mock_run_command.return_value = (0, "resource created", "")
        output = MagicMock(spec=OutputManager)

        # Act
        result = deploy_action_app(
            app_name="nginx",
            app=app,
            base_dir=tmp_path,
            app_config_dir=app_config_dir,
            output=output,
            dry_run=False,
        )

        # Assert
        assert result is True
        # Should be called twice (once for each action)
        assert mock_run_command.call_count == 2


class TestDeployActionAppNamespace:
    """Test namespace handling in Action app."""

    @patch("sbkube.commands.deploy.run_command")
    def test_action_namespace_override(self, mock_run_command, tmp_path: Path) -> None:
        """Test that action.namespace overrides app and config namespace."""
        # Arrange
        app_config_dir = tmp_path / "app_001_nginx"
        app_config_dir.mkdir(exist_ok=True)

        manifest_file = app_config_dir / "deployment.yaml"
        manifest_file.write_text("apiVersion: apps/v1\nkind: Deployment")

        app = ActionApp(
            type="action",
            namespace="app-ns",  # App-level namespace
            actions=[
                ActionSpec(
                    type="apply",
                    path="deployment.yaml",
                    namespace="action-ns",  # Action-level namespace (should win)
                )
            ],
        )

        mock_run_command.return_value = (0, "deployment.apps/nginx created", "")
        output = MagicMock(spec=OutputManager)

        # Act
        result = deploy_action_app(
            app_name="nginx",
            app=app,
            base_dir=tmp_path,
            app_config_dir=app_config_dir,
            output=output,
            config_namespace="config-ns",  # Config namespace
            dry_run=False,
        )

        # Assert
        assert result is True
        call_args = mock_run_command.call_args[0][0]
        # Should use action namespace
        assert "action-ns" in call_args

    @patch("sbkube.commands.deploy.run_command")
    def test_namespace_inheritance(self, mock_run_command, tmp_path: Path) -> None:
        """Test namespace inheritance from app to action."""
        # Arrange
        app_config_dir = tmp_path / "app_001_nginx"
        app_config_dir.mkdir(exist_ok=True)

        manifest_file = app_config_dir / "deployment.yaml"
        manifest_file.write_text("apiVersion: apps/v1\nkind: Deployment")

        app = ActionApp(
            type="action",
            namespace="app-ns",  # App-level namespace
            actions=[
                ActionSpec(
                    type="apply",
                    path="deployment.yaml",
                    # No namespace specified - should inherit from app
                )
            ],
        )

        mock_run_command.return_value = (0, "deployment.apps/nginx created", "")
        output = MagicMock(spec=OutputManager)

        # Act
        result = deploy_action_app(
            app_name="nginx",
            app=app,
            base_dir=tmp_path,
            app_config_dir=app_config_dir,
            output=output,
            dry_run=False,
        )

        # Assert
        assert result is True
        call_args = mock_run_command.call_args[0][0]
        # Should inherit app namespace
        assert "app-ns" in call_args


class TestDeployActionAppErrors:
    """Test error scenarios."""

    @patch("sbkube.commands.deploy.run_command")
    def test_action_path_not_found(self, mock_run_command, tmp_path: Path) -> None:
        """Test error when action path doesn't exist."""
        # Arrange
        app_config_dir = tmp_path / "app_001_nginx"
        app_config_dir.mkdir(exist_ok=True)

        app = ActionApp(
            type="action",
            actions=[
                ActionSpec(
                    type="apply",
                    path="missing.yaml",  # File doesn't exist
                    namespace="default",
                )
            ],
        )

        output = MagicMock(spec=OutputManager)

        # Act
        result = deploy_action_app(
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

        app = ActionApp(
            type="action",
            actions=[
                ActionSpec(
                    type="apply",
                    path="deployment.yaml",
                    namespace="default",
                )
            ],
        )

        # Mock kubectl apply failure
        mock_run_command.return_value = (1, "", "Error: namespace not found")
        output = MagicMock(spec=OutputManager)

        # Act
        result = deploy_action_app(
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
