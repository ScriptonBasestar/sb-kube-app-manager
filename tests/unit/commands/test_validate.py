"""Unit tests for validate.py command.

Tests verify:
- Basic validation execution
- Dependency/storage flag handling
- Multi-app-group validation
- JSON schema validation
- Pydantic model validation
- Error handling
"""

from unittest.mock import MagicMock, patch

import pytest
from click.testing import CliRunner

from sbkube.commands.validate import cmd


class TestValidateBasic:
    """Test basic validate command functionality."""

    @pytest.fixture
    def config_yaml(self, app_dir):
        """Create minimal valid config.yaml."""
        config_file = app_dir / "config.yaml"
        config_file.write_text(
            """
apps:
  nginx:
    type: helm
    chart: nginx/nginx
"""
        )
        return config_file

    @patch("sbkube.commands.validate.load_config_file")
    @patch("sbkube.commands.validate.SBKubeConfig")
    def test_validate_basic_success(
        self, mock_config_class, mock_load_config, config_yaml
    ):
        """Test successful basic validation."""
        # Arrange
        mock_load_config.return_value = {
            "apps": {"nginx": {"type": "helm", "chart": "nginx/nginx"}}
        }
        mock_config = MagicMock()
        mock_config.apps = {"nginx": MagicMock()}
        mock_config_class.return_value = mock_config

        # Act
        runner = CliRunner()
        result = runner.invoke(cmd, ["-v", str(config_yaml)], obj={"format": "human"})

        # Assert
        assert result.exit_code == 0
        assert "유효성 검사 완료" in result.output or "validated successfully" in result.output
        mock_load_config.assert_called_once()

    @patch("sbkube.commands.validate.load_config_file")
    def test_validate_file_load_failure(self, mock_load_config, config_yaml):
        """Test validation when file loading fails."""
        # Arrange
        mock_load_config.side_effect = Exception("File read error")

        # Act
        runner = CliRunner()
        result = runner.invoke(cmd, [str(config_yaml)], obj={"format": "human"})

        # Assert
        assert result.exit_code != 0
        assert "로딩 실패" in result.output or "실패" in result.output


class TestValidateFlags:
    """Test validation flag handling."""

    @pytest.fixture
    def config_yaml(self, app_dir):
        """Create config.yaml."""
        config_file = app_dir / "config.yaml"
        config_file.write_text("apps: {}")
        return config_file

    @patch("sbkube.commands.validate.load_config_file")
    @patch("sbkube.commands.validate.SBKubeConfig")
    def test_validate_skip_deps_flag(self, mock_config_class, mock_load_config, config_yaml):
        """Test --skip-deps flag skips dependency validation."""
        # Arrange
        mock_load_config.return_value = {"apps": {}}
        mock_config = MagicMock()
        mock_config.apps = {}
        mock_config_class.return_value = mock_config

        # Act
        runner = CliRunner()
        result = runner.invoke(
            cmd, [str(config_yaml), "--skip-deps"], obj={"format": "human"}
        )

        # Assert
        assert result.exit_code == 0

    def test_validate_conflicting_deps_flags(self, config_yaml):
        """Test error when --skip-deps and --strict-deps are both specified."""
        # Act
        runner = CliRunner()
        result = runner.invoke(
            cmd,
            [str(config_yaml), "--skip-deps", "--strict-deps"],
            obj={"format": "human"},
        )

        # Assert
        assert result.exit_code != 0
        assert "함께 사용할 수 없습니다" in result.output or "cannot be used together" in result.output

    @patch("sbkube.commands.validate.load_config_file")
    @patch("sbkube.commands.validate.SBKubeConfig")
    def test_validate_skip_storage_check_flag(
        self, mock_config_class, mock_load_config, config_yaml
    ):
        """Test --skip-storage-check flag skips storage validation."""
        # Arrange
        mock_load_config.return_value = {"apps": {}}
        mock_config = MagicMock()
        mock_config.apps = {}
        mock_config_class.return_value = mock_config

        # Act
        runner = CliRunner()
        result = runner.invoke(
            cmd,
            [str(config_yaml), "--skip-storage-check"],
            obj={"format": "human"},
        )

        # Assert
        assert result.exit_code == 0

    def test_validate_conflicting_storage_flags(self, config_yaml):
        """Test error when --skip-storage-check and --strict-storage-check are both specified."""
        # Act
        runner = CliRunner()
        result = runner.invoke(
            cmd,
            [
                str(config_yaml),
                "--skip-storage-check",
                "--strict-storage-check",
            ],
            obj={"format": "human"},
        )

        # Assert
        assert result.exit_code != 0
        assert "함께 사용할 수 없습니다" in result.output or "cannot be used together" in result.output


class TestValidateMultiAppGroup:
    """Test multi-app-group validation (auto-discovery)."""

    @pytest.fixture
    def multi_app_structure(self, base_dir):
        """Create multiple app group directories."""
        # Create app group 1
        app1_dir = base_dir / "redis"
        app1_dir.mkdir(parents=True, exist_ok=True)
        (app1_dir / "config.yaml").write_text("apps: {redis: {type: helm, chart: redis/redis}}")

        # Create app group 2
        app2_dir = base_dir / "nginx"
        app2_dir.mkdir(parents=True, exist_ok=True)
        (app2_dir / "config.yaml").write_text("apps: {nginx: {type: helm, chart: nginx/nginx}}")

        return base_dir, [app1_dir, app2_dir]

    @patch("sbkube.utils.app_dir_resolver.resolve_app_dirs")
    @patch("sbkube.commands.validate.load_config_file")
    @patch("sbkube.commands.validate.SBKubeConfig")
    def test_validate_all_app_groups_success(
        self,
        mock_config_class,
        mock_load_config,
        mock_resolve_app_dirs,
        multi_app_structure,
    ):
        """Test validation of all app groups (auto-discovery)."""
        # Arrange
        base_dir, app_dirs = multi_app_structure
        mock_resolve_app_dirs.return_value = app_dirs

        mock_load_config.return_value = {"apps": {}}
        mock_config = MagicMock()
        mock_config.apps = {}
        mock_config_class.return_value = mock_config

        # Act
        runner = CliRunner()
        result = runner.invoke(
            cmd, ["--base-dir", str(base_dir)], obj={"format": "human"}
        )

        # Assert
        assert result.exit_code == 0
        assert "All app groups validated successfully" in result.output or "성공" in result.output
        # Should validate both app groups
        assert mock_load_config.call_count == 2

    @patch("sbkube.utils.app_dir_resolver.resolve_app_dirs")
    @patch("sbkube.commands.validate.load_config_file")
    @patch("sbkube.commands.validate.SBKubeConfig")
    def test_validate_specific_app_group(
        self,
        mock_config_class,
        mock_load_config,
        mock_resolve_app_dirs,
        multi_app_structure,
    ):
        """Test validation of a specific app group with --app-dir."""
        # Arrange
        base_dir, app_dirs = multi_app_structure
        mock_resolve_app_dirs.return_value = [app_dirs[0]]  # Only redis

        mock_load_config.return_value = {"apps": {}}
        mock_config = MagicMock()
        mock_config.apps = {}
        mock_config_class.return_value = mock_config

        # Act
        runner = CliRunner()
        result = runner.invoke(
            cmd,
            ["--base-dir", str(base_dir), "--app-dir", "redis"],
            obj={"format": "human"},
        )

        # Assert
        assert result.exit_code == 0
        # Should validate only one app group
        mock_load_config.assert_called_once()


class TestValidateSchemaValidation:
    """Test JSON schema validation functionality."""

    @pytest.fixture
    def config_with_schema(self, base_dir, app_dir):
        """Create config file and JSON schema."""
        # Create schema directory and file
        schema_dir = base_dir / "schemas"
        schema_dir.mkdir(parents=True, exist_ok=True)
        schema_file = schema_dir / "config.schema.json"
        schema_file.write_text('{"type": "object"}')

        # Create config file
        config_file = app_dir / "config.yaml"
        config_file.write_text("apps: {}")
        return config_file, schema_file

    @patch("sbkube.commands.validate.load_config_file")
    @patch("sbkube.commands.validate.load_json_schema")
    def test_validate_json_schema_load_failure(
        self, mock_load_schema, mock_load_config, config_with_schema
    ):
        """Test handling of JSON schema loading failure."""
        # Arrange
        config_file, _ = config_with_schema
        mock_load_config.return_value = {"apps": {}}
        mock_load_schema.side_effect = Exception("Schema parse error")

        # Act
        runner = CliRunner()
        result = runner.invoke(cmd, [str(config_file)], obj={"format": "human"})

        # Assert
        assert result.exit_code != 0


class TestValidateSourcesFile:
    """Test validation of sources.yaml file."""

    @pytest.fixture
    def sources_yaml(self, base_dir):
        """Create sources.yaml file."""
        sources_file = base_dir / "sources.yaml"
        sources_file.write_text(
            """
helm:
  - name: nginx
    repo: https://charts.nginx.com
"""
        )
        return sources_file

    @patch("sbkube.commands.validate.load_config_file")
    @patch("sbkube.commands.validate.SourceScheme")
    def test_validate_sources_yaml_success(
        self, mock_source_class, mock_load_config, sources_yaml
    ):
        """Test validation of sources.yaml file."""
        # Arrange
        mock_load_config.return_value = {
            "helm": [{"name": "nginx", "repo": "https://charts.nginx.com"}]
        }
        mock_source = MagicMock()
        mock_source_class.return_value = mock_source

        # Act
        runner = CliRunner()
        result = runner.invoke(
            cmd,
            ["-v", str(sources_yaml), "--schema-type", "sources"],
            obj={"format": "human"},
        )

        # Assert
        assert result.exit_code == 0
        assert "유효성 검사 완료" in result.output or "validated successfully" in result.output
        mock_source_class.assert_called_once()

    @patch("sbkube.commands.validate.load_config_file")
    @patch("sbkube.commands.validate.SourceScheme")
    def test_validate_sources_yaml_pydantic_failure(
        self, mock_source_class, mock_load_config, sources_yaml
    ):
        """Test Pydantic validation failure for sources.yaml."""
        # Arrange
        from pydantic import ValidationError as PydanticValidationError

        mock_load_config.return_value = {"helm": [{"invalid": "field"}]}
        mock_source_class.side_effect = PydanticValidationError.from_exception_data(
            "SourceScheme",
            [
                {
                    "type": "missing",
                    "loc": ("helm", 0, "name"),
                    "msg": "Field required",
                    "input": {"invalid": "field"},
                }
            ],
        )

        # Act
        runner = CliRunner()
        result = runner.invoke(
            cmd,
            [str(sources_yaml), "--schema-type", "sources"],
            obj={"format": "human"},
        )

        # Assert
        assert result.exit_code != 0
        assert "Pydantic 모델 검증 실패" in result.output or "검증 실패" in result.output


class TestValidateErrorHandling:
    """Test error handling scenarios."""

    def test_validate_file_type_inference_failure(self, app_dir):
        """Test error when file type cannot be inferred from filename."""
        # Arrange
        unknown_file = app_dir / "unknown.yaml"
        unknown_file.write_text("test: value")

        # Act
        runner = CliRunner()
        result = runner.invoke(cmd, [str(unknown_file)], obj={"format": "human"})

        # Assert
        assert result.exit_code != 0
        assert "파일 타입" in result.output or "유추할 수 없습니다" in result.output

    @patch("sbkube.utils.app_dir_resolver.resolve_app_dirs")
    def test_validate_app_dir_resolution_failure(self, mock_resolve, base_dir):
        """Test error when app directory resolution fails."""
        # Arrange
        mock_resolve.side_effect = ValueError("No app directories found")

        # Act
        runner = CliRunner()
        result = runner.invoke(
            cmd, ["--base-dir", str(base_dir)], obj={"format": "human"}
        )

        # Assert
        assert result.exit_code != 0

    @patch("sbkube.utils.app_dir_resolver.resolve_app_dirs")
    @patch("sbkube.commands.validate.load_config_file")
    def test_validate_multi_app_partial_failure(
        self, mock_load_config, mock_resolve, base_dir
    ):
        """Test multi-app validation with some failures."""
        # Arrange
        app1_dir = base_dir / "app1"
        app1_dir.mkdir(parents=True, exist_ok=True)
        (app1_dir / "config.yaml").write_text("apps: {}")

        app2_dir = base_dir / "app2"
        app2_dir.mkdir(parents=True, exist_ok=True)
        (app2_dir / "config.yaml").write_text("apps: {}")

        mock_resolve.return_value = [app1_dir, app2_dir]

        # First call succeeds, second fails
        mock_load_config.side_effect = [
            {"apps": {}},
            Exception("Load failed"),
        ]

        # Act
        runner = CliRunner()
        result = runner.invoke(
            cmd, ["--base-dir", str(base_dir)], obj={"format": "human"}
        )

        # Assert
        assert result.exit_code != 0
        assert "Some app groups failed" in result.output or "실패" in result.output
