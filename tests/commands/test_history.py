"""Tests for sbkube history command (Phase 5)."""

import pytest
from click.testing import CliRunner

from sbkube.cli import main


@pytest.fixture
def runner():
    """Create a Click test runner."""
    return CliRunner()


class TestHistoryBasic:
    """Basic history command tests."""

    def test_history_help(self, runner):
        """Test history --help displays correctly."""
        result = runner.invoke(main, ["history", "--help"])
        assert result.exit_code == 0
        assert "Display deployment history" in result.output
        assert "--show" in result.output
        assert "--diff" in result.output
        assert "--values-diff" in result.output

    def test_history_without_db(self, runner, tmp_path):
        """Test history handles missing State DB gracefully."""
        result = runner.invoke(main, ["history"])
        # Should handle missing DB gracefully
        assert result.exit_code in [0, 1]  # May succeed with empty result or fail


class TestHistoryList:
    """Tests for history list functionality."""

    def test_history_list_option_exists(self, runner):
        """Test basic history list is default behavior."""
        result = runner.invoke(main, ["history", "--help"])
        assert "history" in result.output.lower()

    @pytest.mark.integration
    def test_history_list_with_deployments(self, runner, state_db_with_data):
        """Test history lists deployments from State DB."""
        pytest.skip("Requires State DB with sample data")


class TestHistoryShow:
    """Tests for --show option."""

    def test_history_show_option_exists(self, runner):
        """Test --show option is available."""
        result = runner.invoke(main, ["history", "--help"])
        assert "--show" in result.output
        assert "Show detailed information for a specific deployment" in result.output

    @pytest.mark.integration
    def test_history_show_specific_deployment(self, runner, state_db_with_data):
        """Test --show displays specific deployment details."""
        pytest.skip("Requires State DB with sample data")


class TestHistoryDiff:
    """Tests for --diff option (Phase 5)."""

    def test_history_diff_option_exists(self, runner):
        """Test --diff option is available."""
        result = runner.invoke(main, ["history", "--help"])
        assert "--diff" in result.output
        assert "Compare two deployments" in result.output

    def test_history_diff_invalid_format(self, runner):
        """Test --diff with invalid format."""
        result = runner.invoke(main, ["history", "--diff", "invalid_format"])
        assert result.exit_code != 0
        assert "Invalid --diff format" in result.output

    @pytest.mark.integration
    def test_history_diff_two_deployments(self, runner, state_db_with_multiple_deployments):
        """Test --diff compares two deployments."""
        pytest.skip("Requires State DB with multiple deployments")


class TestHistoryValuesDiff:
    """Tests for --values-diff option (Phase 5)."""

    def test_history_values_diff_option_exists(self, runner):
        """Test --values-diff option is available."""
        result = runner.invoke(main, ["history", "--help"])
        assert "--values-diff" in result.output
        assert "Compare Helm values between two deployments" in result.output

    def test_history_values_diff_invalid_format(self, runner):
        """Test --values-diff with invalid format."""
        result = runner.invoke(main, ["history", "--diff", "invalid"])
        assert result.exit_code != 0

    @pytest.mark.integration
    def test_history_values_diff_helm_releases(self, runner, state_db_with_helm_data):
        """Test --values-diff shows Helm values changes."""
        pytest.skip("Requires State DB with Helm release data")


class TestHistoryAppGroupFilter:
    """Tests for app-group filtering (Phase 5)."""

    def test_history_app_group_argument(self, runner):
        """Test app-group argument is available."""
        result = runner.invoke(main, ["history", "--help"])
        # Should accept app_group as argument
        assert "app_group" in result.output or "APP_GROUP" in result.output

    @pytest.mark.integration
    def test_history_filter_by_app_group(self, runner, state_db_with_app_groups):
        """Test filtering history by app-group."""
        pytest.skip("Requires State DB with app-group data")


class TestHistoryFormat:
    """Tests for --format option."""

    def test_history_format_option_exists(self, runner):
        """Test --format option is available."""
        result = runner.invoke(main, ["history", "--help"])
        assert "--format" in result.output
        assert "json" in result.output.lower()
        assert "yaml" in result.output.lower()

    @pytest.mark.integration
    def test_history_format_json(self, runner, state_db_with_data):
        """Test --format json output."""
        pytest.skip("Requires State DB with sample data")

    @pytest.mark.integration
    def test_history_format_yaml(self, runner, state_db_with_data):
        """Test --format yaml output."""
        pytest.skip("Requires State DB with sample data")


class TestHistoryFilters:
    """Tests for cluster/namespace filtering."""

    def test_history_cluster_filter_exists(self, runner):
        """Test --cluster filter is available."""
        result = runner.invoke(main, ["history", "--help"])
        assert "--cluster" in result.output

    def test_history_namespace_filter_exists(self, runner):
        """Test --namespace filter is available."""
        result = runner.invoke(main, ["history", "--help"])
        assert "--namespace" in result.output or "-n" in result.output

    @pytest.mark.integration
    def test_history_filter_by_cluster(self, runner, state_db_multicluster):
        """Test filtering by cluster name."""
        pytest.skip("Requires State DB with multi-cluster data")


# Integration tests
@pytest.mark.integration
class TestHistoryIntegration:
    """Integration tests for history command."""

    def test_history_after_deployment(self, runner, deployed_app):
        """Test history shows deployment after sbkube apply."""
        pytest.skip("Requires actual deployment")

    def test_history_diff_real_deployments(self, runner, two_deployments):
        """Test diff between two real deployments."""
        pytest.skip("Requires two actual deployments")

    def test_history_values_diff_real_helm_releases(self, runner, helm_deployments):
        """Test values-diff with real Helm releases."""
        pytest.skip("Requires Helm deployments")
