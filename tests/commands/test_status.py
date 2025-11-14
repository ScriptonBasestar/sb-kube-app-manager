"""Tests for sbkube status command (Phase 1-7)."""

import pytest
from click.testing import CliRunner

from sbkube.cli import main


@pytest.fixture
def runner():
    """Create a Click test runner."""
    return CliRunner()


class TestStatusBasic:
    """Basic status command tests."""

    def test_status_help(self, runner) -> None:
        """Test status --help displays correctly."""
        result = runner.invoke(main, ["status", "--help"])
        assert result.exit_code == 0
        assert "Display application and cluster status" in result.output
        assert "--by-group" in result.output
        assert "--deps" in result.output
        assert "--health-check" in result.output

    def test_status_requires_sources_yaml(self, runner, tmp_path) -> None:
        """Test status fails without sources.yaml."""
        result = runner.invoke(main, ["status", "--base-dir", str(tmp_path)])
        assert result.exit_code != 0
        assert "sources.yaml not found" in result.output


class TestStatusByGroup:
    """Tests for --by-group option (Phase 4)."""

    def test_status_by_group_option_exists(self, runner) -> None:
        """Test --by-group option is available."""
        result = runner.invoke(main, ["status", "--help"])
        assert "--by-group" in result.output
        assert "Group applications by app-group" in result.output


@pytest.mark.integration
class TestStatusDeps:
    """Tests for --deps option (Phase 6)."""

    def test_status_deps_option_exists(self, runner) -> None:
        """Test --deps option is available."""
        result = runner.invoke(main, ["status", "--help"])
        assert "--deps" in result.output
        assert "Show dependency tree" in result.output

    @pytest.mark.unit
    def test_status_deps_without_config(self, runner, tmp_path) -> None:
        """Test --deps fails gracefully without config.yaml."""
        # Create minimal sources.yaml
        sources_file = tmp_path / "sources.yaml"
        sources_file.write_text("""
kubeconfig: ~/.kube/config
kubeconfig_context: test-context
cluster: test-cluster
""")

        result = runner.invoke(main, ["status", "--deps", "--base-dir", str(tmp_path)])
        # Should fail because config.yaml is missing
        assert result.exit_code != 0


class TestStatusHealthCheck:
    """Tests for --health-check option (Phase 7)."""

    def test_status_health_check_option_exists(self, runner) -> None:
        """Test --health-check option is available."""
        result = runner.invoke(main, ["status", "--help"])
        assert "--health-check" in result.output
        assert "Show detailed health check status" in result.output


@pytest.mark.integration
class TestStatusManaged:
    """Tests for --managed option (Phase 4)."""

    def test_status_managed_option_exists(self, runner) -> None:
        """Test --managed option is available."""
        result = runner.invoke(main, ["status", "--help"])
        assert "--managed" in result.output
        assert "Show only sbkube-managed applications" in result.output


class TestStatusUnhealthy:
    """Tests for --unhealthy option (Phase 4)."""

    def test_status_unhealthy_option_exists(self, runner) -> None:
        """Test --unhealthy option is available."""
        result = runner.invoke(main, ["status", "--help"])
        assert "--unhealthy" in result.output
        assert "Show only unhealthy resources" in result.output


class TestStatusShowNotes:
    """Tests for --show-notes option (Documentation as Code feature)."""

    def test_status_show_notes_option_exists(self, runner) -> None:
        """Test --show-notes option is available."""
        result = runner.invoke(main, ["status", "--help"])
        assert "--show-notes" in result.output
        assert "Show application notes" in result.output


class TestStatusAppGroup:
    """Tests for app-group argument (Phase 4)."""

    def test_status_specific_app_group(self, runner) -> None:
        """Test status with specific app-group argument."""
        result = runner.invoke(main, ["status", "--help"])
        assert "app_group" in result.output or "APP_GROUP" in result.output


class TestStatusLLMOutput:
    """Tests for LLM-friendly output format (Phase 3)."""

    def test_status_with_llm_format_help(self, runner) -> None:
        """Test --format option is available."""
        result = runner.invoke(main, ["--help"])
        assert "--format" in result.output
        assert "llm" in result.output

    def test_status_requires_sources_even_with_llm_format(
        self, runner, tmp_path
    ) -> None:
        """Test status with --format llm still requires sources.yaml."""
        result = runner.invoke(
            main, ["--format", "llm", "status", "--base-dir", str(tmp_path)]
        )
        assert result.exit_code != 0
        # Should still show error about missing sources.yaml


class TestStatusOptionCombinations:
    """Tests for option combinations."""

    def test_status_by_group_and_health_check(self, runner) -> None:
        """Test combining --by-group and --health-check."""
        result = runner.invoke(main, ["status", "--help"])
        # Both options should be available
        assert "--by-group" in result.output
        assert "--health-check" in result.output

    def test_status_managed_and_unhealthy(self, runner) -> None:
        """Test combining --managed and --unhealthy."""
        result = runner.invoke(main, ["status", "--help"])
        assert "--managed" in result.output
        assert "--unhealthy" in result.output


# Integration tests (require actual cluster)
@pytest.mark.integration
class TestStatusIntegration:
    """Integration tests for status command."""
