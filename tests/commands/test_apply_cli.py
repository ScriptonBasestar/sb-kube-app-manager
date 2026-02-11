"""Tests for sbkube apply command."""

import pytest
from click.testing import CliRunner

from sbkube.cli import main


@pytest.fixture
def runner():
    """Create a Click test runner."""
    return CliRunner()


class TestApplyBasic:
    """Basic apply command tests."""

    def test_apply_help(self, runner) -> None:
        """Test apply --help displays correctly."""
        result = runner.invoke(main, ["apply", "--help"])
        assert result.exit_code == 0
        assert "SBKube apply" in result.output or "전체 워크플로우" in result.output
        assert "TARGET" in result.output
        assert "--app-dir" in result.output
        assert "--dry-run" in result.output

    def test_apply_requires_sources_yaml(self, runner, tmp_path) -> None:
        """Test apply fails without sources.yaml."""
        result = runner.invoke(main, ["apply", "--base-dir", str(tmp_path)])
        # apply should fail when no app directories found or invalid config
        assert result.exit_code != 0


class TestApplyOptions:
    """Tests for apply command options."""

    def test_apply_dry_run_option_exists(self, runner) -> None:
        """Test --dry-run option is available."""
        result = runner.invoke(main, ["apply", "--help"])
        assert "--dry-run" in result.output
        assert "Dry-run" in result.output or "실제 배포하지 않음" in result.output

    def test_apply_skip_prepare_option_exists(self, runner) -> None:
        """Test --skip-prepare option is available."""
        result = runner.invoke(main, ["apply", "--help"])
        assert "--skip-prepare" in result.output
        assert "prepare" in result.output

    def test_apply_skip_build_option_exists(self, runner) -> None:
        """Test --skip-build option is available."""
        result = runner.invoke(main, ["apply", "--help"])
        assert "--skip-build" in result.output
        assert "build" in result.output

    def test_apply_skip_deps_check_option_exists(self, runner) -> None:
        """Test --skip-deps-check option is available."""
        result = runner.invoke(main, ["apply", "--help"])
        assert "--skip-deps-check" in result.output

    def test_apply_strict_deps_option_exists(self, runner) -> None:
        """Test --strict-deps option is available."""
        result = runner.invoke(main, ["apply", "--help"])
        assert "--strict-deps" in result.output

    def test_apply_app_option_exists(self, runner) -> None:
        """Test --app option is available."""
        result = runner.invoke(main, ["apply", "--help"])
        assert "--app" in result.output

    def test_apply_phase_option_exists(self, runner) -> None:
        """Test --phase option is available."""
        result = runner.invoke(main, ["apply", "--help"])
        assert "--phase" in result.output

    def test_apply_parallel_options_exist(self, runner) -> None:
        """Test workspace parallel options are exposed in apply."""
        result = runner.invoke(main, ["apply", "--help"])
        assert "--parallel / --no-parallel" in result.output
        assert "--parallel-apps / --no-parallel-apps" in result.output
        assert "--max-workers" in result.output


class TestApplyConfigValidation:
    """Tests for config file validation in apply command."""

    def test_apply_with_missing_config_file(self, runner, tmp_path) -> None:
        """Test apply fails gracefully with missing config file."""
        # Create app directory without config.yaml
        app_dir = tmp_path / "test_app"
        app_dir.mkdir()

        result = runner.invoke(
            main, ["apply", "--base-dir", str(tmp_path), "--app-dir", "test_app"]
        )

        # Should fail with config not found error
        assert result.exit_code != 0

    def test_apply_with_invalid_config_file(self, runner, tmp_path) -> None:
        """Test apply fails gracefully with invalid config file."""
        # Create app directory with invalid config.yaml
        app_dir = tmp_path / "test_app"
        app_dir.mkdir()
        (app_dir / "config.yaml").write_text("invalid: [unclosed")

        result = runner.invoke(
            main, ["apply", "--base-dir", str(tmp_path), "--app-dir", "test_app"]
        )

        # Should fail with parsing error
        assert result.exit_code != 0

    def test_apply_warns_legacy_options(self, runner, tmp_path) -> None:
        """Legacy options should emit deprecation warnings."""
        app_dir = tmp_path / "test_app"
        app_dir.mkdir()
        result = runner.invoke(
            main, ["apply", "--base-dir", str(tmp_path), "--app-dir", "test_app"]
        )
        assert result.exit_code != 0
        assert "'--app-dir' is deprecated" in result.output
        assert "'--base-dir' is deprecated" in result.output

    def test_apply_rejects_target_with_phase(self, runner, tmp_path) -> None:
        """TARGET and --phase should be mutually exclusive."""
        (tmp_path / "sbkube.yaml").write_text(
            "apiVersion: sbkube/v1\nmetadata:\n  name: test\napps: {}\n"
        )
        result = runner.invoke(main, ["apply", str(tmp_path), "--phase", "p1-infra"])
        assert result.exit_code != 0
        assert "Cannot use positional TARGET and --phase together." in result.output


@pytest.mark.integration
class TestApplyIntegration:
    """Integration tests for apply command (requires cluster)."""

    def test_apply_integration_placeholder(self) -> None:
        """Placeholder for future integration tests."""
        # Integration tests will be added when cluster is available
        pytest.skip("Integration tests require Kubernetes cluster")
