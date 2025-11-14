"""Unit tests for rollback.py command.

Tests verify:
- List rollback points functionality
- Rollback simulation (dry-run)
- Actual rollback execution
- Error handling
- Helper function behavior
"""

from datetime import datetime
from pathlib import Path
from unittest.mock import MagicMock, patch

import click
import pytest
from click.testing import CliRunner

from sbkube.commands.rollback import (
    _list_rollback_points,
    _print_rollback_result,
    _print_rollback_simulation,
    cmd,
)
from sbkube.exceptions import RollbackError


class TestRollbackListPoints:
    """Test rollback points listing functionality."""

    @patch("sbkube.commands.rollback.RollbackManager")
    def test_list_rollback_points_success(self, mock_manager_class) -> None:
        """Test successful listing of rollback points."""
        # Arrange
        mock_manager = MagicMock()
        mock_manager_class.return_value = mock_manager

        mock_manager.list_rollback_points.return_value = [
            {
                "deployment_id": "dep_20250131_143022",
                "timestamp": "2025-01-31T14:30:22",
                "apps": 3,
                "status": "success",
                "can_rollback": True,
            },
            {
                "deployment_id": "dep_20250130_095510",
                "timestamp": "2025-01-30T09:55:10",
                "apps": 3,
                "status": "success",
                "can_rollback": True,
            },
        ]

        # Act
        runner = CliRunner()
        result = runner.invoke(
            cmd,
            [
                "--list",
                "--cluster",
                "production",
                "--namespace",
                "default",
                "--base-dir",
                ".",
                "--app-dir",
                "apps",
            ],
        )

        # Assert
        assert result.exit_code == 0
        assert "dep_20250131_143022" in result.output
        assert "dep_20250130_095510" in result.output
        mock_manager.list_rollback_points.assert_called_once()

    @patch("sbkube.commands.rollback.RollbackManager")
    def test_list_rollback_points_no_results(self, mock_manager_class) -> None:
        """Test listing when no rollback points exist."""
        # Arrange
        mock_manager = MagicMock()
        mock_manager_class.return_value = mock_manager
        mock_manager.list_rollback_points.return_value = []

        # Act
        runner = CliRunner()
        result = runner.invoke(
            cmd,
            [
                "--list",
                "--cluster",
                "production",
                "--namespace",
                "default",
            ],
        )

        # Assert
        assert result.exit_code == 0
        assert "No rollback points found" in result.output

    def test_list_rollback_points_missing_cluster(self) -> None:
        """Test error when --cluster is missing."""
        # Act
        runner = CliRunner()
        result = runner.invoke(
            cmd,
            [
                "--list",
                "--namespace",
                "default",
            ],
        )

        # Assert
        assert result.exit_code != 0
        assert "--cluster and --namespace are required" in result.output

    def test_list_rollback_points_missing_namespace(self) -> None:
        """Test error when --namespace is missing."""
        # Act
        runner = CliRunner()
        result = runner.invoke(
            cmd,
            [
                "--list",
                "--cluster",
                "production",
            ],
        )

        # Assert
        assert result.exit_code != 0
        assert "--cluster and --namespace are required" in result.output


class TestRollbackDryRun:
    """Test rollback dry-run (simulation) mode."""

    @patch("sbkube.commands.rollback.RollbackManager")
    def test_rollback_dry_run_success(self, mock_manager_class) -> None:
        """Test successful rollback simulation."""
        # Arrange
        mock_manager = MagicMock()
        mock_manager_class.return_value = mock_manager

        mock_manager.rollback_deployment.return_value = {
            "current_deployment": "dep_20250131_143022",
            "target_deployment": "dep_20250130_095510",
            "actions": [
                {
                    "type": "helm_rollback",
                    "details": {
                        "release": "nginx",
                        "from_revision": 3,
                        "to_revision": 2,
                    },
                },
                {
                    "type": "resource_delete",
                    "details": {
                        "kind": "ConfigMap",
                        "name": "test-config",
                    },
                },
            ],
        }

        # Act
        runner = CliRunner()
        result = runner.invoke(
            cmd,
            [
                "dep_20250131_143022",
                "--dry-run",
            ],
        )

        # Assert
        assert result.exit_code == 0
        assert "Rollback Simulation" in result.output
        assert "nginx" in result.output
        assert "ConfigMap/test-config" in result.output

    @patch("sbkube.commands.rollback.RollbackManager")
    def test_rollback_dry_run_with_target(self, mock_manager_class) -> None:
        """Test dry-run with specific target deployment."""
        # Arrange
        mock_manager = MagicMock()
        mock_manager_class.return_value = mock_manager

        mock_manager.rollback_deployment.return_value = {
            "current_deployment": "dep_20250131_143022",
            "target_deployment": "dep_20250129_120000",
            "actions": [],
        }

        # Act
        runner = CliRunner()
        result = runner.invoke(
            cmd,
            [
                "dep_20250131_143022",
                "--target",
                "dep_20250129_120000",
                "--dry-run",
            ],
        )

        # Assert
        assert result.exit_code == 0
        # Verify RollbackRequest was created with target
        call_args = mock_manager.rollback_deployment.call_args[0][0]
        assert call_args.target_deployment_id == "dep_20250129_120000"


class TestRollbackExecution:
    """Test actual rollback execution."""

    @patch("sbkube.commands.rollback.RollbackManager")
    def test_rollback_success(self, mock_manager_class) -> None:
        """Test successful rollback execution."""
        # Arrange
        mock_manager = MagicMock()
        mock_manager_class.return_value = mock_manager

        mock_manager.rollback_deployment.return_value = {
            "success": True,
            "rollbacks": [
                {
                    "app": "nginx",
                    "type": "helm",
                    "actions": [
                        {
                            "type": "helm_rollback",
                            "release": "nginx",
                        }
                    ],
                }
            ],
            "errors": [],
        }

        # Act
        runner = CliRunner()
        result = runner.invoke(
            cmd,
            [
                "dep_20250131_143022",
            ],
        )

        # Assert
        assert result.exit_code == 0
        assert "Rollback completed successfully" in result.output
        assert "nginx" in result.output

    @patch("sbkube.commands.rollback.RollbackManager")
    def test_rollback_with_specific_apps(self, mock_manager_class) -> None:
        """Test rollback of specific apps only."""
        # Arrange
        mock_manager = MagicMock()
        mock_manager_class.return_value = mock_manager

        mock_manager.rollback_deployment.return_value = {
            "success": True,
            "rollbacks": [{"app": "traefik", "type": "helm", "actions": []}],
            "errors": [],
        }

        # Act
        runner = CliRunner()
        result = runner.invoke(
            cmd,
            [
                "dep_20250131_143022",
                "--app",
                "traefik",
                "--app",
                "coredns",
            ],
        )

        # Assert
        assert result.exit_code == 0
        # Verify app_names were passed correctly
        call_args = mock_manager.rollback_deployment.call_args[0][0]
        assert call_args.app_names == ["traefik", "coredns"]

    @patch("sbkube.commands.rollback.RollbackManager")
    def test_rollback_with_errors(self, mock_manager_class) -> None:
        """Test rollback execution with some failures."""
        # Arrange
        mock_manager = MagicMock()
        mock_manager_class.return_value = mock_manager

        mock_manager.rollback_deployment.return_value = {
            "success": False,
            "rollbacks": [
                {"app": "nginx", "type": "helm", "actions": []},
            ],
            "errors": [
                {"app": "redis", "error": "Release not found"},
            ],
        }

        # Act
        runner = CliRunner()
        result = runner.invoke(
            cmd,
            [
                "dep_20250131_143022",
            ],
        )

        # Assert
        assert result.exit_code == 0
        assert "Rollback completed with errors" in result.output
        assert "redis" in result.output
        assert "Release not found" in result.output

    @patch("sbkube.commands.rollback.RollbackManager")
    def test_rollback_force_flag(self, mock_manager_class) -> None:
        """Test rollback with --force flag."""
        # Arrange
        mock_manager = MagicMock()
        mock_manager_class.return_value = mock_manager

        mock_manager.rollback_deployment.return_value = {
            "success": True,
            "rollbacks": [],
            "errors": [],
        }

        # Act
        runner = CliRunner()
        result = runner.invoke(
            cmd,
            [
                "dep_20250131_143022",
                "--force",
            ],
        )

        # Assert
        assert result.exit_code == 0
        # Verify force flag was passed
        call_args = mock_manager.rollback_deployment.call_args[0][0]
        assert call_args.force is True


class TestRollbackErrors:
    """Test error handling scenarios."""

    def test_rollback_missing_deployment_id(self) -> None:
        """Test error when deployment_id is not provided."""
        # Act
        runner = CliRunner()
        result = runner.invoke(cmd, [])

        # Assert
        assert result.exit_code != 0
        assert "deployment_id is required" in result.output
        assert "Use --list" in result.output

    @patch("sbkube.commands.rollback.RollbackManager")
    def test_rollback_manager_error(self, mock_manager_class) -> None:
        """Test handling of RollbackManager errors."""
        # Arrange
        mock_manager = MagicMock()
        mock_manager_class.return_value = mock_manager

        mock_manager.rollback_deployment.side_effect = RollbackError(
            "Deployment not found"
        )

        # Act
        runner = CliRunner()
        result = runner.invoke(
            cmd,
            [
                "dep_20250131_143022",
            ],
        )

        # Assert
        assert result.exit_code != 0
        assert "Rollback failed" in result.output

    @patch("sbkube.commands.rollback.RollbackManager")
    def test_rollback_unexpected_error(self, mock_manager_class) -> None:
        """Test handling of unexpected errors."""
        # Arrange
        mock_manager = MagicMock()
        mock_manager_class.return_value = mock_manager

        mock_manager.rollback_deployment.side_effect = Exception(
            "Unexpected database error"
        )

        # Act
        runner = CliRunner()
        result = runner.invoke(
            cmd,
            [
                "dep_20250131_143022",
            ],
        )

        # Assert
        assert result.exit_code != 0
        assert "Unexpected error" in result.output


class TestRollbackHelperFunctions:
    """Test helper functions directly."""

    def test_print_rollback_simulation(self, capsys) -> None:
        """Test rollback simulation output formatting."""
        # Arrange
        result = {
            "current_deployment": "dep_20250131_143022",
            "target_deployment": "dep_20250130_095510",
            "actions": [
                {
                    "type": "helm_rollback",
                    "details": {
                        "release": "nginx",
                        "from_revision": 3,
                        "to_revision": 2,
                    },
                },
                {
                    "type": "resource_delete",
                    "details": {
                        "kind": "ConfigMap",
                        "name": "test-config",
                    },
                },
                {
                    "type": "resource_restore",
                    "details": {
                        "kind": "Secret",
                        "name": "api-key",
                    },
                },
            ],
        }

        # Act
        _print_rollback_simulation(result)
        captured = capsys.readouterr()

        # Assert
        assert "dep_20250131_143022" in captured.out
        assert "dep_20250130_095510" in captured.out
        assert "nginx" in captured.out
        assert "ConfigMap/test-config" in captured.out
        assert "Secret/api-key" in captured.out

    def test_print_rollback_result_success(self, capsys) -> None:
        """Test successful rollback result formatting."""
        # Arrange
        result = {
            "success": True,
            "rollbacks": [
                {
                    "app": "nginx",
                    "type": "helm",
                    "actions": [
                        {
                            "type": "helm_rollback",
                            "release": "nginx",
                        }
                    ],
                }
            ],
            "errors": [],
        }

        # Act
        _print_rollback_result(result)
        captured = capsys.readouterr()

        # Assert
        assert "Rollback completed successfully" in captured.out
        assert "nginx" in captured.out

    def test_print_rollback_result_with_errors(self, capsys) -> None:
        """Test rollback result formatting with errors."""
        # Arrange
        result = {
            "success": False,
            "rollbacks": [{"app": "nginx", "type": "helm", "actions": []}],
            "errors": [
                {"app": "redis", "error": "Release not found"},
            ],
        }

        # Act
        _print_rollback_result(result)
        captured = capsys.readouterr()

        # Assert
        assert "Rollback completed with errors" in captured.out
        assert "redis" in captured.out
        assert "Release not found" in captured.out
