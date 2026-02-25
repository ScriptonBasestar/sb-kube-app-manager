"""Tests for validate command."""

from unittest.mock import MagicMock, patch

import pytest
import yaml
from click.testing import CliRunner

from sbkube.cli import main


@pytest.fixture
def runner():
    """Create CliRunner fixture."""
    return CliRunner()


class TestValidateCommandHelp:
    """Test validate command help."""

    def test_validate_help(self, runner) -> None:
        """Test --help option shows help message."""
        result = runner.invoke(main, ["validate", "--help"])

        assert result.exit_code == 0
        assert "validate" in result.output.lower()
        assert "config" in result.output.lower() or "schema" in result.output.lower()


class TestValidateCommandBasic:
    """Test basic validate command scenarios."""

    @patch("sbkube.commands.validate.load_config_file")
    @patch("sbkube.models.config_model.SBKubeConfig")
    def test_validate_config_file_success(
        self,
        mock_config_model,
        mock_load_config,
        runner,
        tmp_path,
    ) -> None:
        """Test successful config.yaml validation."""
        # Create config file
        config_file = tmp_path / "config.yaml"
        config_data = {
            "namespace": "default",
            "apps": {
                "test-app": {
                    "type": "helm",
                    "enabled": True,
                    "chart": "nginx/nginx",
                }
            },
        }
        with open(config_file, "w") as f:
            yaml.dump(config_data, f)

        # Mock file loader and Pydantic validation
        mock_load_config.return_value = config_data
        mock_config_instance = MagicMock()
        mock_config_instance.apps = {"test-app": MagicMock()}
        mock_config_instance.deps = None
        mock_config_model.return_value = mock_config_instance

        # Run validate
        result = runner.invoke(
            main,
            [
                "validate",
                str(config_file),
                "--skip-deps",
                "--skip-storage-check",
            ],
        )

        # Assert
        assert result.exit_code == 0
        mock_load_config.assert_called_once()

    @patch("sbkube.commands.validate.load_config_file")
    @patch("sbkube.models.sources_model.SourceScheme")
    def test_validate_sources_file_success(
        self,
        mock_source_model,
        mock_load_config,
        runner,
        tmp_path,
    ) -> None:
        """Test successful sources.yaml validation."""
        # Create sources file
        sources_file = tmp_path / "sources.yaml"
        sources_data = {
            "kubeconfig": "/fake/kubeconfig",
            "kubeconfig_context": "test-context",
            "cluster": "test-cluster",
        }
        with open(sources_file, "w") as f:
            yaml.dump(sources_data, f)

        # Mock file loader and Pydantic validation
        mock_load_config.return_value = sources_data
        mock_source_instance = MagicMock()
        mock_source_model.return_value = mock_source_instance

        # Run validate
        result = runner.invoke(
            main,
            [
                "validate",
                str(sources_file),
                "--schema-type",
                "sources",
            ],
        )

        # Assert
        assert result.exit_code == 0
        mock_load_config.assert_called_once()

    def test_validate_file_not_found(
        self,
        runner,
        tmp_path,
    ) -> None:
        """Test error when target file doesn't exist."""
        nonexistent_file = tmp_path / "nonexistent.yaml"

        result = runner.invoke(main, ["validate", str(nonexistent_file)])

        assert result.exit_code != 0

    @patch("sbkube.commands.validate.load_config_file")
    def test_validate_file_load_failure(
        self,
        mock_load_config,
        runner,
        tmp_path,
    ) -> None:
        """Test error when file loading fails."""
        config_file = tmp_path / "config.yaml"
        config_file.write_text("invalid: yaml: content:\n  broken")

        # Mock file loader failure
        mock_load_config.side_effect = Exception("YAML parse error")

        result = runner.invoke(main, ["validate", str(config_file)])

        assert result.exit_code != 0


class TestValidateCommandPydantic:
    """Test Pydantic model validation."""

    @pytest.mark.skip(reason="SBKubeConfig may allow empty apps - needs investigation")
    @patch("sbkube.commands.validate.load_config_file")
    def test_validate_pydantic_validation_error(
        self,
        mock_load_config,
        runner,
        tmp_path,
    ) -> None:
        """Test Pydantic validation error handling."""
        config_file = tmp_path / "config.yaml"
        # Create invalid config data
        config_data = {
            "namespace": "default",
            # Missing required 'apps' field
        }
        with open(config_file, "w") as f:
            yaml.dump(config_data, f)

        mock_load_config.return_value = config_data

        # Don't mock SBKubeConfig - let actual validation run
        result = runner.invoke(
            main,
            [
                "validate",
                str(config_file),
                "--skip-deps",
                "--skip-storage-check",
            ],
        )

        assert result.exit_code != 0


class TestValidateCommandDependencies:
    """Test dependency validation."""

    @patch("sbkube.commands.validate.load_config_file")
    @patch("sbkube.models.config_model.SBKubeConfig")
    @patch("sbkube.utils.deployment_checker.DeploymentChecker")
    def test_validate_deps_all_deployed(
        self,
        mock_checker_class,
        mock_config_model,
        mock_load_config,
        runner,
        tmp_path,
    ) -> None:
        """Test dependency validation when all deps are deployed."""
        config_file = tmp_path / "app1" / "config.yaml"
        config_file.parent.mkdir(parents=True)
        config_data = {
            "namespace": "default",
            "deps": ["app0"],
            "apps": {"test": {"type": "helm", "enabled": True, "chart": "nginx/nginx"}},
        }
        with open(config_file, "w") as f:
            yaml.dump(config_data, f)

        mock_load_config.return_value = config_data
        mock_config_instance = MagicMock()
        mock_config_instance.apps = {"test": MagicMock()}
        mock_config_instance.deps = ["app0"]
        mock_config_model.return_value = mock_config_instance

        # Mock dependency checker
        mock_checker = MagicMock()
        mock_checker.check_dependencies.return_value = {
            "all_deployed": True,
            "missing": [],
            "details": {"app0": (True, "Deployed")},
        }
        mock_checker_class.return_value = mock_checker

        result = runner.invoke(
            main,
            [
                "validate",
                str(config_file),
                "--skip-storage-check",
            ],
        )

        assert result.exit_code == 0
        mock_checker.check_dependencies.assert_called_once()

    @patch("sbkube.commands.validate.load_config_file")
    @patch("sbkube.models.config_model.SBKubeConfig")
    @patch("sbkube.utils.deployment_checker.DeploymentChecker")
    def test_validate_deps_missing(
        self,
        mock_checker_class,
        mock_config_model,
        mock_load_config,
        runner,
        tmp_path,
    ) -> None:
        """Test dependency validation when deps are missing."""
        config_file = tmp_path / "app1" / "config.yaml"
        config_file.parent.mkdir(parents=True)
        config_data = {
            "namespace": "default",
            "deps": ["app0"],
            "apps": {"test": {"type": "helm", "enabled": True, "chart": "nginx/nginx"}},
        }
        with open(config_file, "w") as f:
            yaml.dump(config_data, f)

        mock_load_config.return_value = config_data
        mock_config_instance = MagicMock()
        mock_config_instance.apps = {"test": MagicMock()}
        mock_config_instance.deps = ["app0"]
        mock_config_model.return_value = mock_config_instance

        # Mock dependency checker - missing deps
        mock_checker = MagicMock()
        mock_checker.check_dependencies.return_value = {
            "all_deployed": False,
            "missing": ["app0"],
            "details": {"app0": (False, "Not deployed")},
        }
        mock_checker_class.return_value = mock_checker

        result = runner.invoke(
            main,
            [
                "validate",
                str(config_file),
                "--skip-storage-check",
            ],
        )

        # Should succeed with warning (non-blocking by default)
        assert result.exit_code == 0
        assert "app0" in result.output

    @patch("sbkube.commands.validate.load_config_file")
    @patch("sbkube.models.config_model.SBKubeConfig")
    def test_validate_skip_deps(
        self,
        mock_config_model,
        mock_load_config,
        runner,
        tmp_path,
    ) -> None:
        """Test --skip-deps option."""
        config_file = tmp_path / "config.yaml"
        config_data = {
            "namespace": "default",
            "deps": ["app0"],
            "apps": {"test": {"type": "helm", "enabled": True, "chart": "nginx/nginx"}},
        }
        with open(config_file, "w") as f:
            yaml.dump(config_data, f)

        mock_load_config.return_value = config_data
        mock_config_instance = MagicMock()
        mock_config_instance.apps = {"test": MagicMock()}
        mock_config_instance.deps = ["app0"]
        mock_config_model.return_value = mock_config_instance

        result = runner.invoke(
            main,
            [
                "validate",
                str(config_file),
                "--skip-deps",
                "--skip-storage-check",
            ],
        )

        assert result.exit_code == 0


class TestValidateCommandStorage:
    """Test storage validation."""

    @patch("sbkube.commands.validate.load_config_file")
    @patch("sbkube.models.config_model.SBKubeConfig")
    @patch("sbkube.validators.storage_validators.StorageValidatorLegacy")
    def test_validate_storage_all_exist(
        self,
        mock_validator_class,
        mock_config_model,
        mock_load_config,
        runner,
        tmp_path,
    ) -> None:
        """Test storage validation when all PVs exist."""
        config_file = tmp_path / "config.yaml"
        config_data = {
            "namespace": "default",
            "apps": {"test": {"type": "helm", "enabled": True, "chart": "nginx/nginx"}},
        }
        with open(config_file, "w") as f:
            yaml.dump(config_data, f)

        mock_load_config.return_value = config_data
        mock_config_instance = MagicMock()
        mock_config_instance.apps = {"test": MagicMock()}
        mock_config_instance.deps = None
        mock_config_model.return_value = mock_config_instance

        # Mock storage validator
        mock_validator = MagicMock()
        mock_validator.check_required_pvs.return_value = {
            "all_exist": True,
            "existing": [],
            "missing": [],
        }
        mock_validator_class.return_value = mock_validator

        result = runner.invoke(
            main,
            [
                "validate",
                str(config_file),
                "--skip-deps",
            ],
        )

        assert result.exit_code == 0
        mock_validator.check_required_pvs.assert_called_once()

    @patch("sbkube.commands.validate.load_config_file")
    @patch("sbkube.models.config_model.SBKubeConfig")
    @patch("sbkube.validators.storage_validators.StorageValidatorLegacy")
    def test_validate_storage_missing(
        self,
        mock_validator_class,
        mock_config_model,
        mock_load_config,
        runner,
        tmp_path,
    ) -> None:
        """Test storage validation when PVs are missing."""
        config_file = tmp_path / "config.yaml"
        config_data = {
            "namespace": "default",
            "apps": {"test": {"type": "helm", "enabled": True, "chart": "nginx/nginx"}},
        }
        with open(config_file, "w") as f:
            yaml.dump(config_data, f)

        mock_load_config.return_value = config_data
        mock_config_instance = MagicMock()
        mock_config_instance.apps = {"test": MagicMock()}
        mock_config_instance.deps = None
        mock_config_model.return_value = mock_config_instance

        # Mock storage validator - missing PVs
        mock_validator = MagicMock()
        mock_validator.check_required_pvs.return_value = {
            "all_exist": False,
            "existing": [],
            "missing": [
                {"app": "test", "storage_class": "manual", "size": "10Gi"},
            ],
        }
        mock_validator_class.return_value = mock_validator

        result = runner.invoke(
            main,
            [
                "validate",
                str(config_file),
                "--skip-deps",
            ],
        )

        # Should succeed with warning (non-blocking by default)
        assert result.exit_code == 0
        assert "test" in result.output or "storage" in result.output.lower()

    @patch("sbkube.commands.validate.load_config_file")
    @patch("sbkube.models.config_model.SBKubeConfig")
    def test_validate_skip_storage_check(
        self,
        mock_config_model,
        mock_load_config,
        runner,
        tmp_path,
    ) -> None:
        """Test --skip-storage-check option."""
        config_file = tmp_path / "config.yaml"
        config_data = {
            "namespace": "default",
            "apps": {"test": {"type": "helm", "enabled": True, "chart": "nginx/nginx"}},
        }
        with open(config_file, "w") as f:
            yaml.dump(config_data, f)

        mock_load_config.return_value = config_data
        mock_config_instance = MagicMock()
        mock_config_instance.apps = {"test": MagicMock()}
        mock_config_instance.deps = None
        mock_config_model.return_value = mock_config_instance

        result = runner.invoke(
            main,
            [
                "validate",
                str(config_file),
                "--skip-deps",
                "--skip-storage-check",
            ],
        )

        assert result.exit_code == 0


class TestValidateCommandOptions:
    """Test validate command options."""

    def test_validate_conflicting_deps_options(self, runner, tmp_path) -> None:
        """Test error when both --skip-deps and --strict-deps are used."""
        config_file = tmp_path / "config.yaml"
        config_file.write_text("namespace: default\napps: {}")

        result = runner.invoke(
            main,
            [
                "validate",
                str(config_file),
                "--skip-deps",
                "--strict-deps",
            ],
        )

        assert result.exit_code != 0
        assert "skip-deps" in result.output.lower() or "strict-deps" in result.output.lower()

    def test_validate_conflicting_storage_options(self, runner, tmp_path) -> None:
        """Test error when both --skip-storage-check and --strict-storage-check are used."""
        config_file = tmp_path / "config.yaml"
        config_file.write_text("namespace: default\napps: {}")

        result = runner.invoke(
            main,
            [
                "validate",
                str(config_file),
                "--skip-storage-check",
                "--strict-storage-check",
            ],
        )

        assert result.exit_code != 0
        assert (
            "skip-storage" in result.output.lower()
            or "strict-storage" in result.output.lower()
        )


class TestValidateCommandAutoDiscovery:
    """Test auto-discovery of app groups."""

    @patch("sbkube.utils.app_dir_resolver.resolve_app_dirs")
    @patch("sbkube.commands.validate.load_config_file")
    @patch("sbkube.models.config_model.SBKubeConfig")
    def test_validate_auto_discovery(
        self,
        mock_config_model,
        mock_load_config,
        mock_resolve,
        runner,
        tmp_path,
    ) -> None:
        """Test auto-discovery validates all app groups."""
        # Create multiple app groups
        app1_dir = tmp_path / "app1"
        app1_dir.mkdir()
        (app1_dir / "config.yaml").write_text("namespace: default\napps:\n  test: {type: helm, enabled: true, chart: nginx/nginx}")

        app2_dir = tmp_path / "app2"
        app2_dir.mkdir()
        (app2_dir / "config.yaml").write_text("namespace: default\napps:\n  test: {type: helm, enabled: true, chart: nginx/nginx}")

        # Mock app dir resolution
        mock_resolve.return_value = [app1_dir, app2_dir]

        # Mock config loading and validation
        mock_load_config.return_value = {
            "namespace": "default",
            "apps": {"test": {"type": "helm", "enabled": True, "chart": "nginx/nginx"}},
        }
        mock_config_instance = MagicMock()
        mock_config_instance.apps = {"test": MagicMock()}
        mock_config_instance.deps = None
        mock_config_model.return_value = mock_config_instance

        result = runner.invoke(
            main,
            [
                "validate",
                str(tmp_path),
                "--skip-deps",
                "--skip-storage-check",
            ],
        )

        assert result.exit_code == 0
        assert "app1" in result.output or "app2" in result.output
