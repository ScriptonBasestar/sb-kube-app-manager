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

    def test_rollback_help(self, runner) -> None:
        """Test rollback --help displays correctly."""
        result = runner.invoke(main, ["rollback", "--help"])
        assert result.exit_code == 0
        assert "rollback" in result.output.lower()
        assert "--dry-run" in result.output
        assert "--force" in result.output

    def test_rollback_requires_deployment_id(self, runner) -> None:
        """Test rollback requires deployment ID argument."""
        result = runner.invoke(main, ["rollback"])
        # Should fail without deployment_id
        assert result.exit_code != 0


class TestRollbackDryRun:
    """Tests for --dry-run option."""

    def test_rollback_dry_run_option_exists(self, runner) -> None:
        """Test --dry-run option is available."""
        result = runner.invoke(main, ["rollback", "--help"])
        assert "--dry-run" in result.output
        # Check for dry-run related text (multiple variations accepted)
        assert (
            "without actual rollback" in result.output.lower()
            or "simulate" in result.output.lower()
            or "plan" in result.output.lower()
        )


@pytest.mark.integration
class TestRollbackForce:
    """Tests for --force option."""

    def test_rollback_force_option_exists(self, runner) -> None:
        """Test --force option is available."""
        result = runner.invoke(main, ["rollback", "--help"])
        assert "--force" in result.output
        assert (
            "without confirmation" in result.output.lower()
            or "force" in result.output.lower()
        )


@pytest.mark.integration
class TestRollbackList:
    """Tests for --list option."""

    def test_rollback_list_option_exists(self, runner) -> None:
        """Test --list option is available."""
        result = runner.invoke(main, ["rollback", "--help"])
        assert "--list" in result.output


@pytest.mark.integration
class TestRollbackValidation:
    """Tests for rollback validation."""

    def test_rollback_invalid_deployment_id(self, runner) -> None:
        """Test rollback with non-existent deployment ID."""
        result = runner.invoke(main, ["rollback", "dep_nonexistent"])
        # Should fail gracefully
        assert result.exit_code != 0


# Integration tests
@pytest.mark.integration
class TestRollbackIntegration:
    """Integration tests for rollback command."""
