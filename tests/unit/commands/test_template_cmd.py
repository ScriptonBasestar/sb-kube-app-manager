"""Tests for template command."""

from pathlib import Path
from unittest.mock import MagicMock, patch

import pytest
import yaml
from click.testing import CliRunner

from sbkube.cli import main


@pytest.fixture
def runner():
    """Create CliRunner fixture."""
    return CliRunner()


class TestTemplateCommandHelp:
    """Test template command help."""

    def test_template_help(self, runner) -> None:
        """Test --help option shows help message."""
        result = runner.invoke(main, ["template", "--help"])

        assert result.exit_code == 0
        assert "template" in result.output.lower()
        assert "render" in result.output.lower() or "yaml" in result.output.lower()


class TestTemplateCommandBasic:
    """Test basic template command scenarios."""

    @patch("sbkube.commands.template.run_command")
    def test_template_requires_config_yaml(
        self,
        mock_run_command,
        runner,
        tmp_path,
    ) -> None:
        """Test template fails without config.yaml."""
        # Create app config directory without config.yaml
        config_dir = tmp_path / "config"
        config_dir.mkdir(parents=True, exist_ok=True)

        result = runner.invoke(
            main, ["template", "--base-dir", str(tmp_path), "--app-dir", "config"]
        )

        assert result.exit_code != 0
        assert "config" in result.output.lower() or "not found" in result.output.lower()

    @patch("sbkube.commands.template.run_command")
    def test_template_helm_app_success(
        self,
        mock_run_command,
        runner,
        tmp_path,
    ) -> None:
        """Test successful template rendering of Helm app."""
        # Setup directory structure
        config_dir = tmp_path / "config"
        config_dir.mkdir(parents=True, exist_ok=True)

        # Create config.yaml with Helm app
        config_file = config_dir / "config.yaml"
        config_data = {
            "namespace": "default",
            "apps": {
                "nginx": {
                    "type": "helm",
                    "enabled": True,
                    "chart": "bitnami/nginx",
                    "version": "15.0.0",
                }
            },
        }
        with open(config_file, "w") as f:
            yaml.dump(config_data, f)

        # Create built chart (simulating build step)
        sbkube_dir = tmp_path / ".sbkube"
        build_dir = sbkube_dir / "build" / "nginx"
        build_dir.mkdir(parents=True)
        (build_dir / "Chart.yaml").write_text("name: nginx\nversion: 15.0.0")
        (build_dir / "values.yaml").write_text("replicaCount: 1")

        # Create templates directory
        templates_dir = build_dir / "templates"
        templates_dir.mkdir()
        (templates_dir / "deployment.yaml").write_text("""
apiVersion: apps/v1
kind: Deployment
metadata:
  name: nginx
spec:
  replicas: 1
""")

        # Mock successful helm template command
        mock_run_command.return_value = (
            0,
            """
apiVersion: apps/v1
kind: Deployment
metadata:
  name: nginx
spec:
  replicas: 1
""",
            "",
        )

        # Run template
        result = runner.invoke(
            main, ["template", "--base-dir", str(tmp_path), "--app-dir", "config"]
        )

        # Assert
        assert result.exit_code == 0
        assert "nginx" in result.output.lower()
        # Check that helm template was called
        assert mock_run_command.called

    @patch("sbkube.commands.template.run_command")
    def test_template_yaml_app_success(
        self,
        mock_run_command,
        runner,
        tmp_path,
    ) -> None:
        """Test successful template rendering of YAML app."""
        # Setup directory structure
        config_dir = tmp_path / "config"
        config_dir.mkdir(parents=True, exist_ok=True)

        # Create manifest file
        manifests_dir = config_dir / "manifests"
        manifests_dir.mkdir()
        manifest_file = manifests_dir / "deployment.yaml"
        manifest_file.write_text(
            """
apiVersion: apps/v1
kind: Deployment
metadata:
  name: nginx
spec:
  replicas: 1
"""
        )

        # Create config.yaml with YAML app
        config_file = config_dir / "config.yaml"
        config_data = {
            "namespace": "default",
            "apps": {
                "nginx-manifests": {
                    "type": "yaml",
                    "enabled": True,
                    "manifests": ["manifests/deployment.yaml"],
                }
            },
        }
        with open(config_file, "w") as f:
            yaml.dump(config_data, f)

        # Run template
        result = runner.invoke(
            main, ["template", "--base-dir", str(tmp_path), "--app-dir", "config"]
        )

        # Assert
        assert result.exit_code == 0
        assert "nginx-manifests" in result.output.lower()

    @patch("sbkube.commands.template.run_command")
    def test_template_http_app_success(
        self,
        mock_run_command,
        runner,
        tmp_path,
    ) -> None:
        """Test successful template rendering of HTTP app."""
        # Setup directory structure
        config_dir = tmp_path / "config"
        config_dir.mkdir(parents=True, exist_ok=True)

        # Create build directory (simulating build step)
        sbkube_dir = tmp_path / ".sbkube"
        build_dir = sbkube_dir / "build" / "my-http"
        build_dir.mkdir(parents=True)
        (build_dir / "deployment.yaml").write_text(
            """
apiVersion: apps/v1
kind: Deployment
metadata:
  name: nginx
spec:
  replicas: 1
"""
        )

        # Create config.yaml with HTTP app
        config_file = config_dir / "config.yaml"
        config_data = {
            "namespace": "default",
            "apps": {
                "my-http": {
                    "type": "http",
                    "enabled": True,
                    "url": "https://example.com/manifest.yaml",
                    "dest": "manifests/external.yaml",
                }
            },
        }
        with open(config_file, "w") as f:
            yaml.dump(config_data, f)

        # Run template
        result = runner.invoke(
            main, ["template", "--base-dir", str(tmp_path), "--app-dir", "config"]
        )

        # Assert
        assert result.exit_code == 0
        assert "my-http" in result.output.lower()


class TestTemplateCommandOptions:
    """Test template command options."""

    @patch("sbkube.commands.template.run_command")
    def test_template_dry_run(
        self,
        mock_run_command,
        runner,
        tmp_path,
    ) -> None:
        """Test --dry-run option."""
        # Setup directory structure
        config_dir = tmp_path / "config"
        config_dir.mkdir(parents=True, exist_ok=True)

        # Create manifest file
        manifests_dir = config_dir / "manifests"
        manifests_dir.mkdir()
        (manifests_dir / "deployment.yaml").write_text(
            """
apiVersion: apps/v1
kind: Deployment
metadata:
  name: nginx
"""
        )

        # Create config.yaml with YAML app
        config_file = config_dir / "config.yaml"
        config_data = {
            "namespace": "default",
            "apps": {
                "nginx": {
                    "type": "yaml",
                    "enabled": True,
                    "manifests": ["manifests/deployment.yaml"],
                }
            },
        }
        with open(config_file, "w") as f:
            yaml.dump(config_data, f)

        # Run template with --dry-run
        result = runner.invoke(
            main,
            [
                "template",
                "--base-dir",
                str(tmp_path),
                "--app-dir",
                "config",
                "--dry-run",
            ],
        )

        # Assert
        assert result.exit_code == 0
        assert "dry-run" in result.output.lower() or "nginx" in result.output.lower()

    @patch("sbkube.commands.template.run_command")
    def test_template_specific_app(
        self,
        mock_run_command,
        runner,
        tmp_path,
    ) -> None:
        """Test --app option renders only specific app."""
        # Setup directory structure
        config_dir = tmp_path / "config"
        config_dir.mkdir(parents=True, exist_ok=True)

        # Create manifest files
        manifests_dir = config_dir / "manifests"
        manifests_dir.mkdir()
        (manifests_dir / "nginx.yaml").write_text("apiVersion: v1\nkind: Pod")
        (manifests_dir / "redis.yaml").write_text("apiVersion: v1\nkind: Pod")

        # Create config.yaml with multiple apps
        config_file = config_dir / "config.yaml"
        config_data = {
            "namespace": "default",
            "apps": {
                "nginx": {
                    "type": "yaml",
                    "enabled": True,
                    "manifests": ["manifests/nginx.yaml"],
                },
                "redis": {
                    "type": "yaml",
                    "enabled": True,
                    "manifests": ["manifests/redis.yaml"],
                },
            },
        }
        with open(config_file, "w") as f:
            yaml.dump(config_data, f)

        # Run template with --app nginx
        result = runner.invoke(
            main,
            [
                "template",
                "--base-dir",
                str(tmp_path),
                "--app-dir",
                "config",
                "--app",
                "nginx",
            ],
        )

        # Assert
        assert result.exit_code == 0
        assert "nginx" in result.output.lower()


class TestTemplateCommandErrors:
    """Test template command error handling."""

    @patch("sbkube.commands.template.run_command")
    def test_template_app_not_found(
        self,
        mock_run_command,
        runner,
        tmp_path,
    ) -> None:
        """Test error when specified app doesn't exist."""
        # Setup directory structure
        config_dir = tmp_path / "config"
        config_dir.mkdir(parents=True, exist_ok=True)

        # Create config.yaml
        config_file = config_dir / "config.yaml"
        config_data = {
            "namespace": "default",
            "apps": {
                "nginx": {
                    "type": "yaml",
                    "enabled": True,
                    "manifests": ["manifests/deployment.yaml"],
                }
            },
        }
        with open(config_file, "w") as f:
            yaml.dump(config_data, f)

        # Run template with non-existent app
        result = runner.invoke(
            main,
            [
                "template",
                "--base-dir",
                str(tmp_path),
                "--app-dir",
                "config",
                "--app",
                "nonexistent",
            ],
        )

        # Assert
        assert result.exit_code != 0
        assert (
            "not found" in result.output.lower() or "nonexistent" in result.output.lower()
        )

    @patch("sbkube.commands.template.run_command")
    def test_template_disabled_app_skipped(
        self,
        mock_run_command,
        runner,
        tmp_path,
    ) -> None:
        """Test disabled apps are skipped during template."""
        # Setup directory structure
        config_dir = tmp_path / "config"
        config_dir.mkdir(parents=True, exist_ok=True)

        # Create config.yaml with disabled app
        config_file = config_dir / "config.yaml"
        config_data = {
            "namespace": "default",
            "apps": {
                "nginx": {
                    "type": "yaml",
                    "enabled": False,
                    "manifests": ["manifests/deployment.yaml"],
                }
            },
        }
        with open(config_file, "w") as f:
            yaml.dump(config_data, f)

        # Run template
        result = runner.invoke(
            main, ["template", "--base-dir", str(tmp_path), "--app-dir", "config"]
        )

        # Assert - should succeed but skip disabled app
        assert result.exit_code == 0
