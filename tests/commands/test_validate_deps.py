"""Tests for validate command dependency validation features."""

import pytest
from click.testing import CliRunner

from sbkube.cli import main


@pytest.fixture
def temp_app_with_deps(tmp_path):
    """Create a temporary app directory with dependencies."""
    app_dir = tmp_path / "test_app"
    app_dir.mkdir()

    config_content = """
namespace: test
deps:
  - app_dep1
  - app_dep2
apps:
  nginx:
    type: helm
    chart: grafana/nginx
    version: 15.0.0
"""
    (app_dir / "config.yaml").write_text(config_content)
    return app_dir


class TestValidateDepsOptions:
    """Test suite for --skip-deps and --strict-deps options."""

    def test_validate_skip_deps_option(self, temp_app_with_deps) -> None:
        """Test --skip-deps option skips dependency validation."""
        runner = CliRunner()
        result = runner.invoke(
            main,
            [
                "validate",
                str(temp_app_with_deps / "config.yaml"),
                "--skip-deps",
            ],
        )

        # Should succeed (deps validation skipped)
        assert result.exit_code == 0
        assert "의존성 검증 건너뜀" in result.output

    def test_validate_strict_deps_option(self, temp_app_with_deps) -> None:
        """Test --strict-deps option with missing dependencies."""
        runner = CliRunner()
        result = runner.invoke(
            main,
            [
                "validate",
                str(temp_app_with_deps / "config.yaml"),
                "--strict-deps",
            ],
        )

        # Should fail or warn (deps not deployed)
        # Note: This will fail if dependencies are not actually deployed
        assert "의존성" in result.output

    def test_validate_conflicting_options(self, temp_app_with_deps) -> None:
        """Test that --skip-deps and --strict-deps cannot be used together."""
        runner = CliRunner()
        result = runner.invoke(
            main,
            [
                "validate",
                str(temp_app_with_deps / "config.yaml"),
                "--skip-deps",
                "--strict-deps",
            ],
        )

        # Should fail due to conflicting options
        assert result.exit_code != 0
        assert "함께 사용할 수 없습니다" in result.output

    def test_validate_default_deps_behavior(self, temp_app_with_deps) -> None:
        """Test default dependency validation behavior (non-blocking warning)."""
        runner = CliRunner()
        result = runner.invoke(
            main,
            [
                "validate",
                str(temp_app_with_deps / "config.yaml"),
            ],
        )

        # Should succeed but may show warnings about missing deps
        # Default behavior is non-blocking
        assert "의존성" in result.output or result.exit_code == 0
