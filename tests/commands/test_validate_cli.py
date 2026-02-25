"""Tests for sbkube validate command with --app-dir support."""

import pytest
from click.testing import CliRunner

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
    chart: grafana/loki
    version: "17.0.0"
    enabled: true
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
  grafana:
    url: https://grafana.github.io/helm-charts
"""
    (tmp_path / "sources.yaml").write_text(sources_content)

    return tmp_path


class TestValidateHelp:
    """Test validate --help command."""

    def test_validate_help(self, runner) -> None:
        """Test validate --help displays correctly."""
        result = runner.invoke(main, ["validate", "--help"])
        assert result.exit_code == 0
        assert (
            "config.yaml/toml 또는 sources.yaml/toml 파일을 JSON 스키마 및 데이터 모델로 검증합니다"
            in result.output
        )
        assert "--app-dir" not in result.output
        assert "--config-file" not in result.output


class TestValidateExplicitPath:
    """Test validate with explicit file path (backward compatibility)."""

    def test_validate_explicit_path(self, runner, temp_project) -> None:
        """Test validate with explicit file path."""
        config_file = temp_project / "examples" / "basic" / "config.yaml"
        result = runner.invoke(main, ["validate", "-v", str(config_file)])

        # Should succeed (file exists and valid)
        assert result.exit_code == 0
        assert "유효성 검사 완료" in result.output

    def test_validate_explicit_path_sources(self, runner, temp_project) -> None:
        """Test validate with explicit sources.yaml path."""
        sources_file = temp_project / "sources.yaml"
        result = runner.invoke(main, ["validate", "-v", str(sources_file)])

        # Should succeed (file exists and valid)
        assert result.exit_code == 0
        assert "유효성 검사 완료" in result.output

    def test_validate_explicit_path_nonexistent(self, runner, temp_project) -> None:
        """Test validate with non-existent file."""
        nonexistent = temp_project / "nonexistent.yaml"
        result = runner.invoke(main, ["validate", str(nonexistent)])

        # Should fail with Click error (file doesn't exist)
        assert result.exit_code != 0


class TestValidateTargetDir:
    """Test validate with positional TARGET directory."""

    def test_validate_target_dir(self, runner, temp_project) -> None:
        """Test validate with positional TARGET directory."""
        result = runner.invoke(
            main,
            [
                "validate",
                "-v",
                str(temp_project / "examples" / "basic"),
            ],
        )

        # Should succeed
        assert result.exit_code == 0
        assert "Validating app group: basic" in result.output
        assert "유효성 검사 완료" in result.output
        assert "validated successfully" in result.output

    def test_validate_target_file_custom_config(self, runner, temp_project) -> None:
        """Test validate with explicit custom config file path."""
        result = runner.invoke(
            main,
            [
                "validate",
                "-v",
                str(temp_project / "examples" / "custom" / "custom.yaml"),
                "--schema-type",
                "config",  # Required for non-standard filenames
            ],
        )

        # Should succeed
        assert result.exit_code == 0
        assert "유효성 검사 완료" in result.output

    def test_validate_target_dir_nonexistent(self, runner, temp_project) -> None:
        """Test validate with non-existent target directory."""
        result = runner.invoke(
            main,
            ["validate", str(temp_project / "nonexistent")],
        )

        # Should fail with clear error message
        assert result.exit_code != 0
        # Accept either error message format
        assert (
            "Target path not found" in result.output
            or "App directory not found" in result.output
            or "Config file not found" in result.output
        )

    def test_validate_target_dir_missing_config(self, runner, temp_project) -> None:
        """Test validate with target dir but missing config file."""
        # Create empty directory
        empty_dir = temp_project / "empty"
        empty_dir.mkdir()

        result = runner.invoke(main, ["validate", str(empty_dir)])

        # Should fail with clear error message
        assert result.exit_code != 0
        assert "Config file not found" in result.output
        assert (
            "validation failed" in result.output
            or "Failed to validate" in result.output
        )


class TestValidateCurrentDir:
    """Test validate without arguments (current directory fallback)."""

    def test_validate_current_dir(self, runner, temp_project) -> None:
        """Test validate without arguments uses current directory (auto-discovery)."""
        # Create app directories at root level (not under examples/)
        app1_dir = temp_project / "app1"
        app1_dir.mkdir()
        config_content = """namespace: test
apps:
  redis:
    type: helm
    chart: grafana/loki
    enabled: true
"""
        (app1_dir / "config.yaml").write_text(config_content)

        result = runner.invoke(main, ["validate", "-v", str(temp_project)])

        # Should succeed (auto-discovers app directories)
        assert result.exit_code == 0
        assert "SBKube `validate` 시작" in result.output
        assert "유효성 검사 완료" in result.output

    def test_validate_current_dir_missing_config(self, runner, tmp_path) -> None:
        """Test validate without arguments in directory without config.yaml."""
        # Empty directory
        empty_dir = tmp_path / "empty"
        empty_dir.mkdir()

        result = runner.invoke(main, ["validate", str(empty_dir)])

        # Should fail with helpful error message (no app directories found)
        assert result.exit_code != 0
        assert "Config file not found" in result.output


class TestValidatePriorityLogic:
    """Test file resolution priority logic."""

    def test_explicit_path_validation(self, runner, temp_project) -> None:
        """Test explicit file path validation works."""
        config_file = temp_project / "config.yaml"

        result = runner.invoke(main, ["validate", str(config_file)])

        # Should use explicit path (not app-dir) — heading shows the file path
        assert result.exit_code == 0
        assert "config.yaml" in result.output

    def test_target_dir_validation(self, runner, temp_project) -> None:
        """Test target directory validation works."""
        result = runner.invoke(
            main,
            [
                "validate",
                str(temp_project / "examples" / "basic"),
            ],
        )

        # Should use provided target directory
        assert result.exit_code == 0
        assert "Validating app group: basic" in result.output
        assert "validated successfully" in result.output


class TestValidateSchemaType:
    """Test --schema-type option compatibility."""

    def test_validate_with_schema_type(self, runner, temp_project) -> None:
        """Test validate with --schema-type option."""
        config_file = temp_project / "config.yaml"

        result = runner.invoke(
            main, ["validate", str(config_file), "--schema-type", "config"]
        )

        # Should succeed
        assert result.exit_code == 0

    def test_validate_sources_with_schema_type(self, runner, temp_project) -> None:
        """Test validate sources.yaml with --schema-type."""
        sources_file = temp_project / "sources.yaml"

        result = runner.invoke(
            main, ["validate", str(sources_file), "--schema-type", "sources"]
        )

        # Should succeed
        assert result.exit_code == 0


class TestValidateIntegration:
    """Integration tests for validate command."""

    def test_validate_workflow(self, runner, temp_project) -> None:
        """Test typical validate workflow."""
        # Step 1: Validate with explicit path
        result1 = runner.invoke(main, ["validate", str(temp_project / "config.yaml")])
        assert result1.exit_code == 0

        # Step 2: Validate with --app-dir
        result2 = runner.invoke(
            main,
            [
                "validate",
                str(temp_project / "examples" / "basic"),
            ],
        )
        assert result2.exit_code == 0

        # Step 3: Validate sources.yaml
        result3 = runner.invoke(main, ["validate", str(temp_project / "sources.yaml")])
        assert result3.exit_code == 0


class TestValidateEdgeCases:
    """Test edge cases and error conditions."""

    def test_validate_empty_config(self, runner, tmp_path) -> None:
        """Test validation with empty config file."""
        empty_config = tmp_path / "empty.yaml"
        empty_config.write_text("")

        result = runner.invoke(main, ["validate", str(empty_config)])

        # Should fail with clear error
        assert result.exit_code != 0
        # Error message may be in Korean: "파일 타입을 유추할 수 없습니다"
        assert (
            "Configuration validation failed" in result.output
            or "Empty" in result.output
            or "유추할 수 없습니다" in result.output
            or "schema-type" in result.output
        )

    def test_validate_malformed_yaml(self, runner, tmp_path) -> None:
        """Test validation with malformed YAML."""
        bad_yaml = tmp_path / "bad.yaml"
        bad_yaml.write_text("namespace: test\napps:\n  - invalid: [unclosed")

        result = runner.invoke(main, ["validate", str(bad_yaml)])

        # Should fail with YAML parse error
        assert result.exit_code != 0

    def test_validate_missing_required_fields(self, runner, tmp_path) -> None:
        """Test validation with missing required fields."""
        incomplete_config = tmp_path / "incomplete.yaml"
        incomplete_config.write_text("""
apps:
  redis:
    type: helm
    # Missing 'chart' field - should fail validation
""")

        result = runner.invoke(main, ["validate", str(incomplete_config)])

        # Should fail with field requirement error
        assert result.exit_code != 0
        assert "chart" in result.output.lower() or "required" in result.output.lower()

    def test_validate_nonexistent_file(self, runner) -> None:
        """Test validation with nonexistent file."""
        result = runner.invoke(main, ["validate", "/nonexistent/config.yaml"])

        # Should fail with file not found error
        assert result.exit_code != 0
        assert (
            "not found" in result.output.lower()
            or "does not exist" in result.output.lower()
            or "target path not found" in result.output.lower()
        )

    def test_validate_directory_instead_of_file(self, runner, tmp_path) -> None:
        """Test validation when given a directory path."""
        result = runner.invoke(main, ["validate", str(tmp_path)])

        # Should fail with appropriate error
        assert result.exit_code != 0

    def test_validate_circular_dependency(self, runner, tmp_path) -> None:
        """Test validation with circular dependency."""
        circular_config = tmp_path / "circular.yaml"
        circular_config.write_text("""namespace: test
apps:
  app-a:
    type: helm
    chart: example/app-a
    depends_on:
      - app-b
  app-b:
    type: helm
    chart: example/app-b
    depends_on:
      - app-a
""")

        result = runner.invoke(main, ["validate", str(circular_config)])

        # Should fail with circular dependency error
        assert result.exit_code != 0
        assert "circular" in result.output.lower() or "cycle" in result.output.lower()

    def test_validate_invalid_app_name(self, runner, tmp_path) -> None:
        """Test validation with invalid Kubernetes app name."""
        invalid_name_config = tmp_path / "invalid_name.yaml"
        invalid_name_config.write_text("""namespace: test
apps:
  Invalid_Name_With_Underscores:
    type: helm
    chart: example/test
""")

        result = runner.invoke(main, ["validate", str(invalid_name_config)])

        # Should fail with naming validation error
        assert result.exit_code != 0

    def test_validate_nonexistent_dependency(self, runner, tmp_path) -> None:
        """Test validation with dependency on nonexistent app."""
        bad_dep_config = tmp_path / "bad_dep.yaml"
        bad_dep_config.write_text("""namespace: test
apps:
  app-a:
    type: helm
    chart: example/app-a
    depends_on:
      - nonexistent-app
""")

        result = runner.invoke(main, ["validate", str(bad_dep_config)])

        # Should fail with dependency validation error
        assert result.exit_code != 0
        assert (
            "nonexistent" in result.output.lower()
            or "not found" in result.output.lower()
        )
