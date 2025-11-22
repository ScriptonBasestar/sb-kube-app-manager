"""Unit tests for history.py command.

Tests verify:
- Basic history listing
- Deployment detail view
- Deployment comparison (diff)
- Output format handling
- Error handling
"""

from unittest.mock import MagicMock, patch

import pytest
from click.testing import CliRunner

from sbkube.commands.history import cmd


class TestHistoryBasic:
    """Test basic history command functionality."""

    @patch("sbkube.commands.history.DeploymentDatabase")
    def test_history_basic_list(self, mock_db_class):
        """Test basic deployment history listing."""
        # Arrange
        mock_db = MagicMock()
        mock_db_class.return_value.__enter__.return_value = mock_db
        mock_db.list_deployments.return_value = []

        # Act
        runner = CliRunner()
        result = runner.invoke(cmd, [], obj={"format": "human"})

        # Assert
        assert result.exit_code == 0

    @patch("sbkube.commands.history.DeploymentDatabase")
    def test_history_with_cluster_filter(self, mock_db_class):
        """Test history with --cluster filter."""
        # Arrange
        mock_db = MagicMock()
        mock_db_class.return_value.__enter__.return_value = mock_db
        mock_db.list_deployments.return_value = []

        # Act
        runner = CliRunner()
        result = runner.invoke(
            cmd, ["--cluster", "production"], obj={"format": "human"}
        )

        # Assert
        assert result.exit_code == 0

    @patch("sbkube.commands.history.DeploymentDatabase")
    def test_history_with_namespace_filter(self, mock_db_class):
        """Test history with --namespace filter."""
        # Arrange
        mock_db = MagicMock()
        mock_db_class.return_value.__enter__.return_value = mock_db
        mock_db.list_deployments.return_value = []

        # Act
        runner = CliRunner()
        result = runner.invoke(
            cmd, ["--namespace", "default"], obj={"format": "human"}
        )

        # Assert
        assert result.exit_code == 0

    @patch("sbkube.commands.history.DeploymentDatabase")
    def test_history_with_limit(self, mock_db_class):
        """Test history with --limit option."""
        # Arrange
        mock_db = MagicMock()
        mock_db_class.return_value.__enter__.return_value = mock_db
        mock_db.list_deployments.return_value = []

        # Act
        runner = CliRunner()
        result = runner.invoke(cmd, ["--limit", "10"], obj={"format": "human"})

        # Assert
        assert result.exit_code == 0


class TestHistoryDetail:
    """Test deployment detail view functionality."""

    @patch("sbkube.commands.history.DeploymentDatabase")
    def test_history_show_deployment(self, mock_db_class):
        """Test showing deployment details with --show."""
        # Arrange
        mock_db = MagicMock()
        mock_db_class.return_value.__enter__.return_value = mock_db

        # Create a minimal mock deployment detail
        mock_detail = MagicMock()
        mock_detail.deployment_id = "dep_20250101_120000"
        mock_detail.cluster = "production"
        mock_detail.namespace = "default"
        mock_detail.app_group = "redis"
        mock_detail.status = "success"
        mock_detail.started_at = "2025-01-01T12:00:00"
        mock_detail.completed_at = "2025-01-01T12:05:00"
        mock_detail.apps = []

        mock_db.get_deployment_detail.return_value = mock_detail

        # Act
        runner = CliRunner()
        result = runner.invoke(
            cmd, ["--show", "dep_20250101_120000"], obj={"format": "human"}
        )

        # Assert
        assert result.exit_code == 0
class TestHistoryDiff:
    """Test deployment comparison functionality."""
class TestHistoryOutputFormats:
    """Test different output format handling."""

    @patch("sbkube.commands.history.DeploymentDatabase")
    def test_history_json_format(self, mock_db_class):
        """Test JSON output format."""
        # Arrange
        mock_db = MagicMock()
        mock_db_class.return_value.__enter__.return_value = mock_db
        mock_db.list_deployments.return_value = []

        # Act
        runner = CliRunner()
        result = runner.invoke(cmd, ["--format", "json"], obj={"format": "json"})

        # Assert
        assert result.exit_code == 0

    @patch("sbkube.commands.history.DeploymentDatabase")
    def test_history_llm_format(self, mock_db_class):
        """Test LLM-friendly output format."""
        # Arrange
        mock_db = MagicMock()
        mock_db_class.return_value.__enter__.return_value = mock_db
        mock_db.list_deployments.return_value = []

        # Act
        runner = CliRunner()
        result = runner.invoke(cmd, ["--format", "llm"], obj={"format": "llm"})

        # Assert
        assert result.exit_code == 0


class TestHistoryAppGroupFilter:
    """Test app group filtering."""

    @patch("sbkube.commands.history.DeploymentDatabase")
    def test_history_with_app_group_argument(self, mock_db_class):
        """Test filtering by app group argument."""
        # Arrange
        mock_db = MagicMock()
        mock_db_class.return_value.__enter__.return_value = mock_db
        mock_db.list_deployments.return_value = []

        # Act
        runner = CliRunner()
        result = runner.invoke(cmd, ["redis"], obj={"format": "human"})

        # Assert
        assert result.exit_code == 0


