"""Unit tests for deploy_exec_app() and deploy_noop_app() functions.

Tests verify:
- ExecApp: Custom command execution
- NoopApp: No-operation placeholder apps
"""

from pathlib import Path
from unittest.mock import MagicMock, patch

import pytest

from sbkube.commands.deploy import deploy_exec_app, deploy_noop_app
from sbkube.models.config_model import ExecApp, NoopApp
from sbkube.utils.output_manager import OutputManager


class TestDeployExecApp:
    """Test ExecApp deployment."""

    @patch("sbkube.commands.deploy.run_command")
    def test_exec_app_success(self, mock_run_command, tmp_path: Path) -> None:
        """Test successful exec app deployment."""
        # Arrange
        app = ExecApp(
            type="exec",
            commands=["echo 'Hello from exec app'"],
        )

        mock_run_command.return_value = (0, "Hello from exec app", "")
        output = MagicMock(spec=OutputManager)

        # Act
        result = deploy_exec_app(
            app_name="test-exec",
            app=app,
            base_dir=tmp_path,
            output=output,
            dry_run=False,
        )

        # Assert
        assert result is True
        mock_run_command.assert_called_once()

    @patch("sbkube.commands.deploy.run_command")
    def test_exec_app_failure(self, mock_run_command, tmp_path: Path) -> None:
        """Test exec app deployment failure."""
        # Arrange
        app = ExecApp(
            type="exec",
            commands=["exit 1"],
        )

        mock_run_command.return_value = (1, "", "Command failed")
        output = MagicMock(spec=OutputManager)

        # Act
        result = deploy_exec_app(
            app_name="test-exec-fail",
            app=app,
            base_dir=tmp_path,
            output=output,
            dry_run=False,
        )

        # Assert
        assert result is False

    @patch("sbkube.commands.deploy.run_command")
    def test_exec_app_dry_run(self, mock_run_command, tmp_path: Path) -> None:
        """Test exec app in dry-run mode."""
        # Arrange
        app = ExecApp(
            type="exec",
            commands=["kubectl apply -f manifest.yaml"],
        )

        output = MagicMock(spec=OutputManager)

        # Act
        result = deploy_exec_app(
            app_name="test-exec-dryrun",
            app=app,
            base_dir=tmp_path,
            output=output,
            dry_run=True,
        )

        # Assert
        assert result is True
        # In dry-run mode, command should not be executed
        mock_run_command.assert_not_called()

    @patch("sbkube.commands.deploy.run_command")
    def test_exec_app_with_multiple_commands(
        self, mock_run_command, tmp_path: Path
    ) -> None:
        """Test exec app with multiple commands."""
        # Arrange
        app = ExecApp(
            type="exec",
            commands=["echo 'Step 1'", "echo 'Step 2'", "echo 'Step 3'"],
        )

        mock_run_command.return_value = (0, "Success", "")
        output = MagicMock(spec=OutputManager)

        # Act
        result = deploy_exec_app(
            app_name="test-exec-multi",
            app=app,
            base_dir=tmp_path,
            output=output,
            dry_run=False,
        )

        # Assert
        assert result is True
        # Multiple commands should result in multiple calls
        assert mock_run_command.call_count == 3


class TestDeployNoopApp:
    """Test NoopApp deployment."""

    def test_noop_app_always_succeeds(self, tmp_path: Path) -> None:
        """Test that noop app always succeeds."""
        # Arrange
        app = NoopApp(
            type="noop",
            description="Placeholder for future implementation",
        )

        output = MagicMock(spec=OutputManager)

        # Act
        result = deploy_noop_app(
            app_name="test-noop",
            app=app,
            base_dir=tmp_path,
            app_config_dir=tmp_path / "config",
            output=output,
            dry_run=False,
        )

        # Assert
        assert result is True

    def test_noop_app_dry_run(self, tmp_path: Path) -> None:
        """Test noop app in dry-run mode."""
        # Arrange
        app = NoopApp(
            type="noop",
            description="Test placeholder",
        )

        output = MagicMock(spec=OutputManager)

        # Act
        result = deploy_noop_app(
            app_name="test-noop-dryrun",
            app=app,
            base_dir=tmp_path,
            app_config_dir=tmp_path / "config",
            output=output,
            dry_run=True,
        )

        # Assert
        assert result is True

    def test_noop_app_outputs_description(self, tmp_path: Path) -> None:
        """Test that noop app outputs the description."""
        # Arrange
        description = "This app is not yet implemented"
        app = NoopApp(
            type="noop",
            description=description,
        )

        output = MagicMock(spec=OutputManager)

        # Act
        result = deploy_noop_app(
            app_name="test-noop-desc",
            app=app,
            base_dir=tmp_path,
            app_config_dir=tmp_path / "config",
            output=output,
            dry_run=False,
        )

        # Assert
        assert result is True
        # Verify output was called (noop app prints info)
        output.print.assert_called()

    def test_noop_app_without_description(self, tmp_path: Path) -> None:
        """Test noop app without explicit description."""
        # Arrange
        app = NoopApp(type="noop")

        output = MagicMock(spec=OutputManager)

        # Act
        result = deploy_noop_app(
            app_name="test-noop-no-desc",
            app=app,
            base_dir=tmp_path,
            app_config_dir=tmp_path / "config",
            output=output,
            dry_run=False,
        )

        # Assert
        assert result is True
