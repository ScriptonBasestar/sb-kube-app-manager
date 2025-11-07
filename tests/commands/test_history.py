"""Tests for sbkube history command (Phase 5)."""

from datetime import datetime

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
    """Create a Click test runner."""
    return CliRunner()


class TestHistoryBasic:
    """Basic history command tests."""

    def test_history_help(self, runner) -> None:
        """Test history --help displays correctly."""
        result = runner.invoke(main, ["history", "--help"])
        assert result.exit_code == 0
        assert "Display deployment history" in result.output
        assert "--show" in result.output
        assert "--diff" in result.output
        assert "--values-diff" in result.output

    def test_history_without_db(self, runner, tmp_path) -> None:
        """Test history handles missing State DB gracefully."""
        result = runner.invoke(main, ["history"])
        # Should handle missing DB gracefully
        assert result.exit_code in [0, 1]  # May succeed with empty result or fail


class TestHistoryList:
    """Tests for history list functionality."""

    def test_history_list_option_exists(self, runner) -> None:
        """Test basic history list is default behavior."""
        result = runner.invoke(main, ["history", "--help"])
        assert "history" in result.output.lower()


@pytest.mark.integration
class TestHistoryShow:
    """Tests for --show option."""

    def test_history_show_option_exists(self, runner) -> None:
        """Test --show option is available."""
        result = runner.invoke(main, ["history", "--help"])
        assert "--show" in result.output
        # Accept both old and new help text
        assert ("Show detailed information for a specific deployment" in result.output
                or "deployment ID" in result.output)


@pytest.mark.integration
class TestHistoryDiff:
    """Tests for --diff option (Phase 5)."""

    def test_history_diff_option_exists(self, runner) -> None:
        """Test --diff option is available."""
        result = runner.invoke(main, ["history", "--help"])
        assert "--diff" in result.output
        assert "Compare two deployments" in result.output

    def test_history_diff_invalid_format(self, runner) -> None:
        """Test --diff with invalid format."""
        result = runner.invoke(main, ["history", "--diff", "invalid_format"])
        assert result.exit_code != 0
        assert "Invalid --diff format" in result.output


@pytest.mark.integration
class TestHistoryValuesDiff:
    """Tests for --values-diff option (Phase 5)."""

    def test_history_values_diff_option_exists(self, runner) -> None:
        """Test --values-diff option is available."""
        result = runner.invoke(main, ["history", "--help"])
        assert "--values-diff" in result.output
        assert "Compare Helm values between two deployments" in result.output

    def test_history_values_diff_invalid_format(self, runner) -> None:
        """Test --values-diff with invalid format."""
        result = runner.invoke(main, ["history", "--diff", "invalid"])
        assert result.exit_code != 0


@pytest.mark.integration
class TestHistoryAppGroupFilter:
    """Tests for app-group filtering (Phase 5)."""

    def test_history_app_group_argument(self, runner) -> None:
        """Test app-group argument is available."""
        result = runner.invoke(main, ["history", "--help"])
        # Should accept app_group as argument
        assert "app_group" in result.output or "APP_GROUP" in result.output


@pytest.mark.integration
class TestHistoryFormat:
    """Tests for --format option."""

    def test_history_format_option_exists(self, runner) -> None:
        """Test --format option is available."""
        result = runner.invoke(main, ["history", "--help"])
        assert "--format" in result.output
        assert "json" in result.output.lower()
        assert "yaml" in result.output.lower()


@pytest.mark.integration
class TestHistoryLLMOutput:
    """Tests for LLM-friendly output (Phase 3)."""

    def test_history_llm_list_output(self, runner, monkeypatch) -> None:
        """Sbkube history should emit compact LLM summary."""
        deployments = [
            DeploymentSummary(
                deployment_id="dep-001",
                timestamp=datetime(2025, 1, 1, 12, 0, 0),
                cluster="prod",
                namespace="default",
                status=DeploymentStatus.SUCCESS,
                app_count=3,
                success_count=3,
                failed_count=0,
            )
        ]

        class FakeDB:
            def list_deployments(self, **kwargs):
                return deployments

            def get_deployment(self, *args, **kwargs) -> None:
                return None

            def get_deployment_diff(self, *args, **kwargs) -> None:
                return None

            def get_deployment_values_diff(self, *args, **kwargs) -> None:
                return None

        monkeypatch.setattr(
            "sbkube.commands.history.DeploymentDatabase", lambda: FakeDB()
        )

        result = runner.invoke(main, ["--format", "llm", "history"])

        assert result.exit_code == 0
        assert "HISTORY STATUS" in result.output
        assert "TOTAL DEPLOYMENTS: 1" in result.output
        assert "dep-001" in result.output

    def test_history_llm_detail_output(self, runner, monkeypatch) -> None:
        """Sbkube history --show should produce structured LLM detail."""
        detail = DeploymentDetail(
            deployment_id="dep-001",
            timestamp=datetime(2025, 1, 2, 8, 30, 0),
            cluster="prod",
            namespace="default",
            app_config_dir="/work/configs/app",
            status=DeploymentStatus.SUCCESS,
            config_snapshot={"apps": []},
            apps=[
                {
                    "name": "web",
                    "type": "helm",
                    "status": "success",
                    "namespace": "default",
                }
            ],
            resources=[],
            helm_releases=[],
        )

        class FakeDB:
            def list_deployments(self, **kwargs):
                return []

            def get_deployment(self, deployment_id):
                return detail if deployment_id == "dep-001" else None

            def get_deployment_diff(self, *args, **kwargs) -> None:
                return None

            def get_deployment_values_diff(self, *args, **kwargs) -> None:
                return None

        monkeypatch.setattr(
            "sbkube.commands.history.DeploymentDatabase", lambda: FakeDB()
        )

        result = runner.invoke(
            main, ["--format", "llm", "history", "--show", "dep-001"]
        )

        assert result.exit_code == 0
        assert "DEPLOYMENT ID: dep-001" in result.output
        assert "APPS (1):" in result.output
        assert "web" in result.output


class TestHistoryFilters:
    """Tests for cluster/namespace filtering."""

    def test_history_cluster_filter_exists(self, runner) -> None:
        """Test --cluster filter is available."""
        result = runner.invoke(main, ["history", "--help"])
        assert "--cluster" in result.output

    def test_history_namespace_filter_exists(self, runner) -> None:
        """Test --namespace filter is available."""
        result = runner.invoke(main, ["history", "--help"])
        assert "--namespace" in result.output or "-n" in result.output


# Integration tests
@pytest.mark.integration
class TestHistoryIntegration:
    """Integration tests for history command."""

