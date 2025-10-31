"""Tests for sbkube rollback command."""

import pytest
from click.testing import CliRunner

from sbkube.cli import main


@pytest.fixture
def runner():
    """Create a Click test runner."""
    return CliRunner()


class TestRollbackBasic:
    """Basic rollback command tests."""

    def test_rollback_help(self, runner):
        """Test rollback --help displays correctly."""
        result = runner.invoke(main, ["rollback", "--help"])
        assert result.exit_code == 0
        assert "rollback" in result.output.lower()
        assert "--dry-run" in result.output
        assert "--force" in result.output

    def test_rollback_requires_deployment_id(self, runner):
        """Test rollback requires deployment ID argument."""
        result = runner.invoke(main, ["rollback"])
        # Should fail without deployment_id
        assert result.exit_code != 0


class TestRollbackDryRun:
    """Tests for --dry-run option."""

    def test_rollback_dry_run_option_exists(self, runner):
        """Test --dry-run option is available."""
        result = runner.invoke(main, ["rollback", "--help"])
        assert "--dry-run" in result.output
        assert "without actual rollback" in result.output.lower() or "plan" in result.output.lower()

    @pytest.mark.integration
    def test_rollback_dry_run_shows_plan(self, runner, state_db_with_data):
        """Test --dry-run displays rollback plan without executing."""
        pytest.skip("Requires State DB with deployment data")


class TestRollbackForce:
    """Tests for --force option."""

    def test_rollback_force_option_exists(self, runner):
        """Test --force option is available."""
        result = runner.invoke(main, ["rollback", "--help"])
        assert "--force" in result.output
        assert "without confirmation" in result.output.lower() or "force" in result.output.lower()

    @pytest.mark.integration
    def test_rollback_force_skips_confirmation(self, runner, state_db_with_data):
        """Test --force skips user confirmation."""
        pytest.skip("Requires State DB and cluster")


class TestRollbackList:
    """Tests for --list option."""

    def test_rollback_list_option_exists(self, runner):
        """Test --list option is available."""
        result = runner.invoke(main, ["rollback", "--help"])
        assert "--list" in result.output

    @pytest.mark.integration
    def test_rollback_list_shows_available_deployments(self, runner, state_db_with_data):
        """Test --list displays rollback candidates."""
        pytest.skip("Requires State DB with deployment history")


class TestRollbackValidation:
    """Tests for rollback validation."""

    def test_rollback_invalid_deployment_id(self, runner):
        """Test rollback with non-existent deployment ID."""
        result = runner.invoke(main, ["rollback", "dep_nonexistent"])
        # Should fail gracefully
        assert result.exit_code != 0

    @pytest.mark.integration
    def test_rollback_target_validation(self, runner, state_db_with_data):
        """Test rollback validates target deployment exists."""
        pytest.skip("Requires State DB")


# Integration tests
@pytest.mark.integration
class TestRollbackIntegration:
    """Integration tests for rollback command."""

    def test_rollback_actual_deployment(self, runner, deployed_apps):
        """Test rollback with actual deployment."""
        pytest.skip("Requires actual deployment history")

    def test_rollback_restores_state(self, runner, two_deployments):
        """Test rollback restores previous deployment state."""
        pytest.skip("Requires two actual deployments")

    def test_rollback_updates_state_db(self, runner, deployment_with_state):
        """Test rollback updates State DB correctly."""
        pytest.skip("Requires deployment with State DB")

    def test_rollback_helm_releases(self, runner, helm_releases):
        """Test rollback reverts Helm releases."""
        pytest.skip("Requires Helm releases")
