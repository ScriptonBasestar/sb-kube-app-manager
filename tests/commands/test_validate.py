"""Tests for sbkube validate command with --app-dir support."""

import pytest
from click.testing import CliRunner
from pathlib import Path
from sbkube.cli import main


@pytest.fixture
def runner():
    """Create Click CLI test runner."""
    return CliRunner()


@pytest.fixture
def temp_project(tmp_path):
    """Create temporary project structure for testing."""
    # Create project structure
    # examples/basic/config.yaml
    basic_dir = tmp_path / "examples" / "basic"
    basic_dir.mkdir(parents=True)

    config_content = """namespace: test
apps:
  redis:
    type: helm
    enabled: true
    specs:
      repo: bitnami
      chart: redis
      version: "17.0.0"
"""
    (basic_dir / "config.yaml").write_text(config_content)

    # examples/custom/custom.yaml
    custom_dir = tmp_path / "examples" / "custom"
    custom_dir.mkdir(parents=True)
    (custom_dir / "custom.yaml").write_text(config_content)

    # Root config.yaml
    (tmp_path / "config.yaml").write_text(config_content)

    # sources.yaml
    sources_content = """kubeconfig: ~/.kube/config
kubeconfig_context: default
helm_repos:
  bitnami:
    url: https://charts.bitnami.com/bitnami
"""
    (tmp_path / "sources.yaml").write_text(sources_content)

    return tmp_path


class TestValidateHelp:
    """Test validate --help command."""

    def test_validate_help(self, runner):
        """Test validate --help displays correctly."""
        result = runner.invoke(main, ["validate", "--help"])
        assert result.exit_code == 0
        assert "config.yaml/toml 또는 sources.yaml/toml 파일을 JSON 스키마 및 데이터 모델로 검증합니다" in result.output
        assert "--app-dir" in result.output
        assert "--config-file" in result.output


class TestValidateExplicitPath:
    """Test validate with explicit file path (backward compatibility)."""

    def test_validate_explicit_path(self, runner, temp_project):
        """Test validate with explicit file path."""
        config_file = temp_project / "examples" / "basic" / "config.yaml"
        result = runner.invoke(main, ["validate", str(config_file)])

        # Should succeed (file exists and valid)
        assert result.exit_code == 0
        assert "유효성 검사 완료" in result.output

    def test_validate_explicit_path_sources(self, runner, temp_project):
        """Test validate with explicit sources.yaml path."""
        sources_file = temp_project / "sources.yaml"
        result = runner.invoke(main, ["validate", str(sources_file)])

        # Should succeed (file exists and valid)
        assert result.exit_code == 0
        assert "유효성 검사 완료" in result.output

    def test_validate_explicit_path_nonexistent(self, runner, temp_project):
        """Test validate with non-existent file."""
        nonexistent = temp_project / "nonexistent.yaml"
        result = runner.invoke(main, ["validate", str(nonexistent)])

        # Should fail with Click error (file doesn't exist)
        assert result.exit_code != 0


class TestValidateAppDir:
    """Test validate with --app-dir option."""

    def test_validate_app_dir(self, runner, temp_project):
        """Test validate with --app-dir option."""
        result = runner.invoke(
            main,
            ["validate", "--app-dir", "examples/basic", "--base-dir", str(temp_project)]
        )

        # Should succeed
        assert result.exit_code == 0
        assert "Using app directory" in result.output
        assert "유효성 검사 완료" in result.output

    def test_validate_app_dir_custom_config(self, runner, temp_project):
        """Test validate with --app-dir and --config-file."""
        result = runner.invoke(
            main,
            [
                "validate",
                "--app-dir", "examples/custom",
                "--config-file", "custom.yaml",
                "--base-dir", str(temp_project)
            ]
        )

        # Should succeed
        assert result.exit_code == 0
        assert "Config file: custom.yaml" in result.output
        assert "유효성 검사 완료" in result.output

    def test_validate_app_dir_nonexistent(self, runner, temp_project):
        """Test validate with non-existent app directory."""
        result = runner.invoke(
            main,
            ["validate", "--app-dir", "nonexistent", "--base-dir", str(temp_project)]
        )

        # Should fail with clear error message
        assert result.exit_code != 0
        assert "App directory not found" in result.output
        assert "💡 Check directory path" in result.output

    def test_validate_app_dir_missing_config(self, runner, temp_project):
        """Test validate with app-dir but missing config file."""
        # Create empty directory
        empty_dir = temp_project / "empty"
        empty_dir.mkdir()

        result = runner.invoke(
            main,
            ["validate", "--app-dir", "empty", "--base-dir", str(temp_project)]
        )

        # Should fail with clear error message
        assert result.exit_code != 0
        assert "Config file not found" in result.output
        assert "💡 Use --config-file" in result.output


class TestValidateCurrentDir:
    """Test validate without arguments (current directory fallback)."""

    def test_validate_current_dir(self, runner, temp_project):
        """Test validate without arguments uses current directory."""
        result = runner.invoke(
            main,
            ["validate", "--base-dir", str(temp_project)]
        )

        # Should succeed (root config.yaml exists)
        assert result.exit_code == 0
        assert "Using current directory" in result.output
        assert "유효성 검사 완료" in result.output

    def test_validate_current_dir_missing_config(self, runner, tmp_path):
        """Test validate without arguments in directory without config.yaml."""
        # Empty directory
        empty_dir = tmp_path / "empty"
        empty_dir.mkdir()

        result = runner.invoke(
            main,
            ["validate", "--base-dir", str(empty_dir)]
        )

        # Should fail with helpful error message
        assert result.exit_code != 0
        assert "Config file not found" in result.output
        assert "💡 Solutions:" in result.output
        assert "Provide explicit path" in result.output
        assert "Use --app-dir" in result.output


class TestValidatePriorityLogic:
    """Test file resolution priority logic."""

    def test_explicit_path_overrides_app_dir(self, runner, temp_project):
        """Test that explicit path takes precedence over --app-dir."""
        config_file = temp_project / "config.yaml"

        result = runner.invoke(
            main,
            [
                "validate",
                str(config_file),
                "--app-dir", "examples/basic",
                "--base-dir", str(temp_project)
            ]
        )

        # Should use explicit path (not app-dir)
        assert result.exit_code == 0
        assert "Using explicit file path" in result.output

    def test_app_dir_overrides_current_dir(self, runner, temp_project):
        """Test that --app-dir takes precedence over current directory."""
        result = runner.invoke(
            main,
            ["validate", "--app-dir", "examples/basic", "--base-dir", str(temp_project)]
        )

        # Should use app-dir (not current dir)
        assert result.exit_code == 0
        assert "Using app directory" in result.output
        assert "Using current directory" not in result.output


class TestValidateSchemaType:
    """Test --schema-type option compatibility."""

    def test_validate_with_schema_type(self, runner, temp_project):
        """Test validate with --schema-type option."""
        config_file = temp_project / "config.yaml"

        result = runner.invoke(
            main,
            ["validate", str(config_file), "--schema-type", "config"]
        )

        # Should succeed
        assert result.exit_code == 0

    def test_validate_sources_with_schema_type(self, runner, temp_project):
        """Test validate sources.yaml with --schema-type."""
        sources_file = temp_project / "sources.yaml"

        result = runner.invoke(
            main,
            ["validate", str(sources_file), "--schema-type", "sources"]
        )

        # Should succeed
        assert result.exit_code == 0


class TestValidateIntegration:
    """Integration tests for validate command."""

    def test_validate_workflow(self, runner, temp_project):
        """Test typical validate workflow."""
        # Step 1: Validate with explicit path
        result1 = runner.invoke(
            main,
            ["validate", str(temp_project / "config.yaml")]
        )
        assert result1.exit_code == 0

        # Step 2: Validate with --app-dir
        result2 = runner.invoke(
            main,
            ["validate", "--app-dir", "examples/basic", "--base-dir", str(temp_project)]
        )
        assert result2.exit_code == 0

        # Step 3: Validate sources.yaml
        result3 = runner.invoke(
            main,
            ["validate", str(temp_project / "sources.yaml")]
        )
        assert result3.exit_code == 0
