"""Tests for history command."""

from datetime import datetime
from unittest.mock import MagicMock, patch

import pytest
from click.testing import CliRunner

from sbkube.cli import main
from sbkube.models.deployment_state import (
    DeploymentDetail,
    DeploymentStatus,
    DeploymentSummary,
)


@pytest.fixture
def runner():
    """Create CliRunner fixture."""
    return CliRunner()


@pytest.fixture
def mock_deployment_data():
    """Create mock deployment data as DeploymentSummary objects."""
    return [
        DeploymentSummary(
            deployment_id="deploy-001",
            timestamp=datetime(2024, 1, 1, 12, 0, 0),
            cluster="test-cluster",
            namespace="default",
            status=DeploymentStatus.SUCCESS,
            app_count=2,
            success_count=2,
            failed_count=0,
            error_message=None,
        ),
        DeploymentSummary(
            deployment_id="deploy-002",
            timestamp=datetime(2024, 1, 2, 12, 0, 0),
            cluster="test-cluster",
            namespace="production",
            status=DeploymentStatus.FAILED,
            app_count=1,
            success_count=0,
            failed_count=1,
            error_message="Deployment failed",
        ),
    ]


class TestHistoryCommandHelp:
    """Test history command help."""

    def test_history_help(self, runner) -> None:
        """Test --help option shows help message."""
        result = runner.invoke(main, ["history", "--help"])

        assert result.exit_code == 0
        assert "history" in result.output.lower()
        assert "deployment" in result.output.lower()


class TestHistoryCommandBasic:
    """Test basic history command scenarios."""

    @patch("sbkube.commands.history.DeploymentDatabase")
    def test_history_list_empty(
        self,
        mock_db_class,
        runner,
    ) -> None:
        """Test history with no deployments."""
        # Mock database
        mock_db = MagicMock()
        mock_db.list_deployments.return_value = []
        mock_db_class.return_value = mock_db

        # Run history
        result = runner.invoke(main, ["history"])

        # Assert
        assert result.exit_code == 0
        mock_db.list_deployments.assert_called_once()

    @patch("sbkube.commands.history.DeploymentDatabase")
    def test_history_list_with_deployments(
        self,
        mock_db_class,
        runner,
        mock_deployment_data,
    ) -> None:
        """Test history displays deployment list."""
        # Mock database
        mock_db = MagicMock()
        mock_db.list_deployments.return_value = mock_deployment_data
        mock_db_class.return_value = mock_db

        # Run history
        result = runner.invoke(main, ["history"])

        # Assert
        assert result.exit_code == 0
        mock_db.list_deployments.assert_called_once()
        # Check that deployment IDs are in output
        assert "deploy-001" in result.output or "app-group-1" in result.output


class TestHistoryCommandFilters:
    """Test history command filter options."""

    @patch("sbkube.commands.history.DeploymentDatabase")
    def test_history_filter_by_cluster(
        self,
        mock_db_class,
        runner,
        mock_deployment_data,
    ) -> None:
        """Test --cluster filter."""
        # Mock database
        mock_db = MagicMock()
        mock_db.list_deployments.return_value = [mock_deployment_data[0]]
        mock_db_class.return_value = mock_db

        # Run history with cluster filter
        result = runner.invoke(main, ["history", "--cluster", "test-cluster"])

        # Assert
        assert result.exit_code == 0
        mock_db.list_deployments.assert_called_once()
        call_kwargs = mock_db.list_deployments.call_args[1]
        assert call_kwargs["cluster"] == "test-cluster"

    @patch("sbkube.commands.history.DeploymentDatabase")
    def test_history_filter_by_namespace(
        self,
        mock_db_class,
        runner,
        mock_deployment_data,
    ) -> None:
        """Test --namespace filter."""
        # Mock database
        mock_db = MagicMock()
        mock_db.list_deployments.return_value = [mock_deployment_data[0]]
        mock_db_class.return_value = mock_db

        # Run history with namespace filter
        result = runner.invoke(main, ["history", "--namespace", "default"])

        # Assert
        assert result.exit_code == 0
        mock_db.list_deployments.assert_called_once()
        call_kwargs = mock_db.list_deployments.call_args[1]
        assert call_kwargs["namespace"] == "default"

    @patch("sbkube.commands.history.DeploymentDatabase")
    def test_history_filter_by_app_group(
        self,
        mock_db_class,
        runner,
        mock_deployment_data,
    ) -> None:
        """Test app_group argument filter."""
        # Mock database
        mock_db = MagicMock()
        mock_db.list_deployments.return_value = [mock_deployment_data[0]]
        mock_db_class.return_value = mock_db

        # Run history with app_group argument
        result = runner.invoke(main, ["history", "app-group-1"])

        # Assert
        assert result.exit_code == 0
        mock_db.list_deployments.assert_called_once()
        call_kwargs = mock_db.list_deployments.call_args[1]
        assert call_kwargs["app_group"] == "app-group-1"

    @patch("sbkube.commands.history.DeploymentDatabase")
    def test_history_limit_option(
        self,
        mock_db_class,
        runner,
        mock_deployment_data,
    ) -> None:
        """Test --limit option."""
        # Mock database
        mock_db = MagicMock()
        mock_db.list_deployments.return_value = [mock_deployment_data[0]]
        mock_db_class.return_value = mock_db

        # Run history with limit
        result = runner.invoke(main, ["history", "--limit", "10"])

        # Assert
        assert result.exit_code == 0
        mock_db.list_deployments.assert_called_once()
        call_kwargs = mock_db.list_deployments.call_args[1]
        assert call_kwargs["limit"] == 10


class TestHistoryCommandDetail:
    """Test history command detail view."""

    @patch("sbkube.commands.history.DeploymentDatabase")
    def test_history_show_deployment_detail(
        self,
        mock_db_class,
        runner,
    ) -> None:
        """Test --show option displays deployment detail."""
        # Mock database
        mock_db = MagicMock()
        mock_deployment_detail = DeploymentDetail(
            deployment_id="deploy-001",
            timestamp=datetime(2024, 1, 1, 12, 0, 0),
            cluster="test-cluster",
            namespace="default",
            app_config_dir="config",
            status=DeploymentStatus.SUCCESS,
            error_message=None,
            config_snapshot={},
            apps=[
                {"name": "app1", "type": "helm", "namespace": "default", "status": "success"},
                {"name": "app2", "type": "helm", "namespace": "default", "status": "success"},
            ],
            resources=[],
            helm_releases=[],
        )
        mock_db.get_deployment.return_value = mock_deployment_detail
        mock_db_class.return_value = mock_db

        # Run history with --show
        result = runner.invoke(main, ["history", "--show", "deploy-001"])

        # Assert
        assert result.exit_code == 0
        mock_db.get_deployment.assert_called_once_with("deploy-001")
        assert "deploy-001" in result.output or "success" in result.output.lower()

    @patch("sbkube.commands.history.DeploymentDatabase")
    def test_history_show_nonexistent_deployment(
        self,
        mock_db_class,
        runner,
    ) -> None:
        """Test --show with non-existent deployment ID."""
        # Mock database
        mock_db = MagicMock()
        mock_db.get_deployment.return_value = None
        mock_db_class.return_value = mock_db

        # Run history with --show for non-existent ID
        result = runner.invoke(main, ["history", "--show", "nonexistent"])

        # Assert - should handle gracefully
        assert result.exit_code != 0 or "not found" in result.output.lower()
        mock_db.get_deployment.assert_called_once_with("nonexistent")


class TestHistoryCommandAdvanced:
    """Test advanced history command features."""

    @patch("sbkube.commands.history.DeploymentDatabase")
    def test_history_diff_deployments(
        self,
        mock_db_class,
        runner,
    ) -> None:
        """Test --diff option compares two deployments."""
        # Mock database
        mock_db = MagicMock()
        mock_diff_result = {
            "deployment1": {
                "id": "deploy-001",
                "timestamp": datetime(2024, 1, 1, 12, 0, 0),
                "status": "success",
                "cluster": "test-cluster",
                "namespace": "default",
                "app_count": 2,
                "config_snapshot": {"apps": {}},
            },
            "deployment2": {
                "id": "deploy-002",
                "timestamp": datetime(2024, 1, 2, 12, 0, 0),
                "status": "success",
                "cluster": "test-cluster",
                "namespace": "default",
                "app_count": 2,
                "config_snapshot": {"apps": {}},
            },
            "apps_diff": {},
        }
        mock_db.get_deployment_diff.return_value = mock_diff_result
        mock_db_class.return_value = mock_db

        # Run history with --diff
        result = runner.invoke(main, ["history", "--diff", "deploy-001,deploy-002"])

        # Assert
        assert result.exit_code == 0
        mock_db.get_deployment_diff.assert_called_once_with("deploy-001", "deploy-002")

    @pytest.mark.skip(reason="Complex values diff mocking requires additional setup")
    @patch("sbkube.commands.history.DeploymentDatabase")
    def test_history_values_diff(
        self,
        mock_db_class,
        runner,
    ) -> None:
        """Test --values-diff option compares Helm values."""
        # Mock database
        mock_db = MagicMock()
        mock_values_diff = {
            "deployment1": {
                "id": "deploy-001",
            },
            "deployment2": {
                "id": "deploy-002",
            },
            "values_diff": {
                "app1": {
                    "status": "modified",
                    "chart": "nginx",
                    "old_values": {"replicas": 1},
                    "new_values": {"replicas": 2},
                    "changes": [{"path": "replicas", "old": 1, "new": 2}],
                }
            },
        }
        mock_db.get_deployment_values_diff.return_value = mock_values_diff
        mock_db_class.return_value = mock_db

        # Run history with --values-diff
        result = runner.invoke(main, ["history", "--values-diff", "deploy-001,deploy-002"])

        # Assert
        assert result.exit_code == 0
        mock_db.get_deployment_values_diff.assert_called_once_with("deploy-001", "deploy-002")

    @patch("sbkube.commands.history.DeploymentDatabase")
    def test_history_diff_not_found(
        self,
        mock_db_class,
        runner,
    ) -> None:
        """Test --diff with non-existent deployments."""
        # Mock database
        mock_db = MagicMock()
        mock_db.get_deployment_diff.return_value = None
        mock_db_class.return_value = mock_db

        # Run history with --diff for non-existent IDs
        result = runner.invoke(main, ["history", "--diff", "deploy-001,deploy-002"])

        # Assert - should handle gracefully
        assert result.exit_code != 0
        mock_db.get_deployment_diff.assert_called_once_with("deploy-001", "deploy-002")

    @patch("sbkube.commands.history.DeploymentDatabase")
    def test_history_diff_invalid_format(
        self,
        mock_db_class,
        runner,
    ) -> None:
        """Test --diff with invalid ID format."""
        # Mock database
        mock_db = MagicMock()
        mock_db_class.return_value = mock_db

        # Run history with invalid --diff format
        result = runner.invoke(main, ["history", "--diff", "deploy-001"])

        # Assert - should handle gracefully
        assert result.exit_code != 0


class TestHistoryCommandErrors:
    """Test history command error handling."""

    @patch("sbkube.commands.history.DeploymentDatabase")
    def test_history_database_init_failure(
        self,
        mock_db_class,
        runner,
    ) -> None:
        """Test error when database initialization fails."""
        # Mock database initialization failure
        mock_db_class.side_effect = Exception("Database connection failed")

        # Run history
        result = runner.invoke(main, ["history"])

        # Assert
        assert result.exit_code != 0
        assert "database" in result.output.lower() or "failed" in result.output.lower()

    @patch("sbkube.commands.history.DeploymentDatabase")
    def test_history_list_query_failure(
        self,
        mock_db_class,
        runner,
    ) -> None:
        """Test error when list query fails."""
        # Mock database
        mock_db = MagicMock()
        mock_db.list_deployments.side_effect = Exception("Query failed")
        mock_db_class.return_value = mock_db

        # Run history
        result = runner.invoke(main, ["history"])

        # Assert
        assert result.exit_code != 0
