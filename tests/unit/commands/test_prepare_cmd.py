"""Tests for prepare command."""

from pathlib import Path
from unittest.mock import MagicMock, patch

import pytest
import yaml
from click.testing import CliRunner

from sbkube.cli import main


@pytest.fixture
def runner():
    """Create CliRunner fixture."""
    return CliRunner()


class TestPrepareCommandHelp:
    """Test prepare command help."""

    def test_prepare_help(self, runner) -> None:
        """Test --help option shows help message."""
        result = runner.invoke(main, ["prepare", "--help"])

        assert result.exit_code == 0
        assert "prepare" in result.output.lower()
        assert "chart" in result.output.lower() or "download" in result.output.lower()


class TestPrepareCommandBasic:
    """Test basic prepare command scenarios."""

    @patch("sbkube.commands.prepare.check_helm_installed_or_exit")
    @patch("sbkube.commands.prepare.run_command")
    def test_prepare_requires_config_yaml(
        self,
        mock_run_command,
        mock_helm_check,
        runner,
        tmp_path,
    ) -> None:
        """Test prepare fails without config.yaml."""
        # Create app config directory without config.yaml
        config_dir = tmp_path / "config"
        config_dir.mkdir(parents=True, exist_ok=True)

        result = runner.invoke(
            main, ["prepare", "--base-dir", str(tmp_path), "--app-dir", "config"]
        )

        assert result.exit_code != 0
        assert "config" in result.output.lower() or "not found" in result.output.lower()


class TestPrepareCommandErrors:
    """Test prepare command error handling."""

    @patch("sbkube.commands.prepare.check_helm_installed_or_exit")
    @patch("sbkube.commands.prepare.run_command")
    def test_prepare_app_not_found(
        self,
        mock_run_command,
        mock_helm_check,
        runner,
        tmp_path,
    ) -> None:
        """Test error when specified app doesn't exist."""
        # Setup directory structure
        config_dir = tmp_path / "config"
        config_dir.mkdir(parents=True, exist_ok=True)

        # Create config.yaml
        config_file = config_dir / "config.yaml"
        config_data = {
            "namespace": "default",
            "apps": {
                "test": {
                    "type": "hook",
                    "enabled": True,
                    "tasks": [{"type": "command", "name": "test", "command": "echo test"}],
                }
            },
        }
        with open(config_file, "w") as f:
            yaml.dump(config_data, f)

        # Run prepare with non-existent app
        result = runner.invoke(
            main,
            [
                "prepare",
                "--base-dir",
                str(tmp_path),
                "--app-dir",
                "config",
                "--app",
                "nonexistent",
            ],
        )

        # Assert
        assert result.exit_code != 0
        assert (
            "not found" in result.output.lower() or "nonexistent" in result.output.lower()
        )
