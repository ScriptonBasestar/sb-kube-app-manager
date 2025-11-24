"""Unit tests for history.py command.

Tests verify:
- Basic history listing
- Deployment detail view
- Deployment comparison (diff)
- Output format handling
- Error handling
"""

from unittest.mock import MagicMock, patch

from click.testing import CliRunner

from sbkube.commands.history import cmd


class TestHistoryBasic:
    """Test basic history command functionality."""

    @patch("sbkube.commands.history.DeploymentDatabase")
    def test_history_basic_list(self, mock_db_class):
        """Test basic deployment history listing."""
        # Arrange
        mock_db = MagicMock()
        mock_db_class.return_value = mock_db  # Direct return value, no context manager
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
        mock_db_class.return_value = mock_db  # Direct return value, no context manager
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
        mock_db_class.return_value = mock_db  # Direct return value, no context manager
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
        mock_db_class.return_value = mock_db  # Direct return value, no context manager
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
        mock_db_class.return_value = mock_db  # Direct return value, no context manager

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

    @patch("sbkube.commands.history._print_deployment_diff")
    @patch("sbkube.commands.history._serialize_diff")
    @patch("sbkube.commands.history.DeploymentDatabase")
    def test_history_diff_success(self, mock_db_class, mock_serialize, mock_print):
        """Test successful deployment diff."""
        # Arrange
        mock_db = MagicMock()
        mock_db_class.return_value = mock_db  # Direct return value, no context manager

        # Mock diff result
        mock_diff_result = {
            "deployment1": {"id": 1, "status": "success"},
            "deployment2": {"id": 2, "status": "success"},
        }
        mock_db.get_deployment_diff.return_value = mock_diff_result

        # Mock serialization result
        mock_serialize.return_value = {
            "deployment1": {"id": 1, "status": "success"},
            "deployment2": {"id": 2, "status": "success"},
        }

        # Act
        runner = CliRunner()
        result = runner.invoke(
            cmd, ["--diff", "dep_20250101_120000,dep_20250102_120000"], obj={"format": "human"}
        )

        # Assert
        assert result.exit_code == 0
        mock_db.get_deployment_diff.assert_called_once_with(
            "dep_20250101_120000", "dep_20250102_120000"
        )

    @patch("sbkube.commands.history.DeploymentDatabase")
    def test_history_diff_invalid_format(self, mock_db_class):
        """Test diff with invalid ID format."""
        # Arrange
        mock_db = MagicMock()
        mock_db_class.return_value = mock_db  # Direct return value, no context manager

        # Act
        runner = CliRunner()
        result = runner.invoke(cmd, ["--diff", "invalid_format"], obj={"format": "human"})

        # Assert
        assert result.exit_code != 0

    @patch("sbkube.commands.history.DeploymentDatabase")
    def test_history_diff_not_found(self, mock_db_class):
        """Test diff when deployment not found."""
        # Arrange
        mock_db = MagicMock()
        mock_db_class.return_value = mock_db  # Direct return value, no context manager
        mock_db.get_deployment_diff.return_value = None

        # Act
        runner = CliRunner()
        result = runner.invoke(
            cmd, ["--diff", "dep_20250101_120000,dep_20250102_120000"], obj={"format": "human"}
        )

        # Assert
        assert result.exit_code != 0

    @patch("sbkube.commands.history._print_values_diff")
    @patch("sbkube.commands.history._serialize_values_diff")
    @patch("sbkube.commands.history.DeploymentDatabase")
    def test_history_values_diff_success(self, mock_db_class, mock_serialize, mock_print):
        """Test successful Helm values diff."""
        # Arrange
        mock_db = MagicMock()
        mock_db_class.return_value = mock_db  # Direct return value, no context manager

        # Mock values diff result
        mock_values_diff = {
            "deployment1": {"id": 1},
            "deployment2": {"id": 2},
            "values_diffs": [],
        }
        mock_db.get_deployment_values_diff.return_value = mock_values_diff

        # Mock serialization result
        mock_serialize.return_value = mock_values_diff

        # Act
        runner = CliRunner()
        result = runner.invoke(
            cmd, ["--values-diff", "dep_20250101_120000,dep_20250102_120000"], obj={"format": "human"}
        )

        # Assert
        assert result.exit_code == 0
        mock_db.get_deployment_values_diff.assert_called_once_with(
            "dep_20250101_120000", "dep_20250102_120000"
        )

    @patch("sbkube.commands.history.DeploymentDatabase")
    def test_history_values_diff_not_found(self, mock_db_class):
        """Test values diff when deployment not found."""
        # Arrange
        mock_db = MagicMock()
        mock_db_class.return_value = mock_db  # Direct return value, no context manager
        mock_db.get_deployment_values_diff.return_value = None

        # Act
        runner = CliRunner()
        result = runner.invoke(
            cmd, ["--values-diff", "dep_20250101_120000,dep_20250102_120000"], obj={"format": "human"}
        )

        # Assert
        assert result.exit_code != 0


class TestHistoryOutputFormats:
    """Test different output format handling."""

    @patch("sbkube.commands.history.DeploymentDatabase")
    def test_history_json_format(self, mock_db_class):
        """Test JSON output format."""
        # Arrange
        mock_db = MagicMock()
        mock_db_class.return_value = mock_db  # Direct return value, no context manager
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
        mock_db_class.return_value = mock_db  # Direct return value, no context manager
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
        mock_db_class.return_value = mock_db  # Direct return value, no context manager
        mock_db.list_deployments.return_value = []

        # Act
        runner = CliRunner()
        result = runner.invoke(cmd, ["redis"], obj={"format": "human"})

        # Assert
        assert result.exit_code == 0


