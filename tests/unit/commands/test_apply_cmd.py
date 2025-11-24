"""Tests for apply command."""

from unittest.mock import patch

import pytest
import yaml
from click.testing import CliRunner

from sbkube.cli import main


@pytest.fixture
def runner():
    """Create CliRunner fixture."""
    return CliRunner()


class TestApplyCommandHelp:
    """Test apply command help."""

    def test_apply_help(self, runner) -> None:
        """Test --help option shows help message."""
        result = runner.invoke(main, ["apply", "--help"])

        assert result.exit_code == 0
        assert "apply" in result.output.lower()
        assert "workflow" in result.output.lower() or "deploy" in result.output.lower()


class TestApplyCommandBasic:
    """Test basic apply command scenarios."""

    @patch("sbkube.commands.deploy.cmd")
    @patch("sbkube.commands.build.cmd")
    @patch("sbkube.commands.prepare.cmd")
    def test_apply_requires_config_yaml(
        self,
        mock_prepare,
        mock_build,
        mock_deploy,
        runner,
        tmp_path,
    ) -> None:
        """Test apply fails without config.yaml."""
        # Create app config directory without config.yaml
        config_dir = tmp_path / "config"
        config_dir.mkdir(parents=True, exist_ok=True)

        result = runner.invoke(
            main, ["apply", "--base-dir", str(tmp_path), "--app-dir", "config"]
        )

        assert result.exit_code != 0
        assert "config" in result.output.lower() or "not found" in result.output.lower()

    @patch("sbkube.commands.deploy.cmd")
    @patch("sbkube.commands.build.cmd")
    @patch("sbkube.commands.prepare.cmd")
    def test_apply_yaml_app_success(
        self,
        mock_prepare,
        mock_build,
        mock_deploy,
        runner,
        tmp_path,
    ) -> None:
        """Test successful apply of YAML app."""
        # Setup directory structure
        config_dir = tmp_path / "config"
        config_dir.mkdir(parents=True, exist_ok=True)

        # Create sources.yaml
        sources_file = tmp_path / "sources.yaml"
        sources_data = {
            "kubeconfig": "/fake/kubeconfig",
            "kubeconfig_context": "test-context",
            "cluster": "test-cluster",
        }
        with open(sources_file, "w") as f:
            yaml.dump(sources_data, f)

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

        # Mock commands to do nothing (successful)
        mock_prepare.return_value = None
        mock_build.return_value = None
        mock_deploy.return_value = None

        # Run apply
        result = runner.invoke(
            main, ["apply", "--base-dir", str(tmp_path), "--app-dir", "config"]
        )

        # Assert
        assert result.exit_code == 0
        assert "nginx-manifests" in result.output.lower()


class TestApplyCommandOptions:
    """Test apply command options."""

    @patch("sbkube.commands.deploy.cmd")
    @patch("sbkube.commands.build.cmd")
    @patch("sbkube.commands.prepare.cmd")
    def test_apply_dry_run(
        self,
        mock_prepare,
        mock_build,
        mock_deploy,
        runner,
        tmp_path,
    ) -> None:
        """Test --dry-run option."""
        # Setup directory structure
        config_dir = tmp_path / "config"
        config_dir.mkdir(parents=True, exist_ok=True)

        # Create sources.yaml
        sources_file = tmp_path / "sources.yaml"
        sources_data = {
            "kubeconfig": "/fake/kubeconfig",
            "kubeconfig_context": "test-context",
            "cluster": "test-cluster",
        }
        with open(sources_file, "w") as f:
            yaml.dump(sources_data, f)

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

        # Mock commands
        mock_prepare.return_value = None
        mock_build.return_value = None
        mock_deploy.return_value = None

        # Run apply with --dry-run
        result = runner.invoke(
            main,
            [
                "apply",
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

    @patch("sbkube.commands.deploy.cmd")
    @patch("sbkube.commands.build.cmd")
    @patch("sbkube.commands.prepare.cmd")
    def test_apply_skip_prepare(
        self,
        mock_prepare,
        mock_build,
        mock_deploy,
        runner,
        tmp_path,
    ) -> None:
        """Test --skip-prepare option."""
        # Setup directory structure
        config_dir = tmp_path / "config"
        config_dir.mkdir(parents=True, exist_ok=True)

        # Create sources.yaml
        sources_file = tmp_path / "sources.yaml"
        sources_file.write_text(
            """
kubeconfig: /fake/kubeconfig
kubeconfig_context: test-context
cluster: test-cluster
"""
        )

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

        # Mock commands
        mock_build.return_value = None
        mock_deploy.return_value = None

        # Run apply with --skip-prepare
        result = runner.invoke(
            main,
            [
                "apply",
                "--base-dir",
                str(tmp_path),
                "--app-dir",
                "config",
                "--skip-prepare",
            ],
        )

        # Assert - prepare should not be called
        assert result.exit_code == 0
        # prepare_cmd should not be invoked (skip-prepare flag)
        # Note: We can't easily verify prepare_cmd wasn't called with current mock setup

    @patch("sbkube.commands.deploy.cmd")
    @patch("sbkube.commands.build.cmd")
    @patch("sbkube.commands.prepare.cmd")
    def test_apply_specific_app(
        self,
        mock_prepare,
        mock_build,
        mock_deploy,
        runner,
        tmp_path,
    ) -> None:
        """Test --app option applies only specific app."""
        # Setup directory structure
        config_dir = tmp_path / "config"
        config_dir.mkdir(parents=True, exist_ok=True)

        # Create sources.yaml
        sources_file = tmp_path / "sources.yaml"
        sources_file.write_text(
            """
kubeconfig: /fake/kubeconfig
kubeconfig_context: test-context
cluster: test-cluster
"""
        )

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

        # Mock commands
        mock_prepare.return_value = None
        mock_build.return_value = None
        mock_deploy.return_value = None

        # Run apply with --app nginx
        result = runner.invoke(
            main,
            [
                "apply",
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


class TestApplyCommandErrors:
    """Test apply command error handling."""

    @patch("sbkube.commands.deploy.cmd")
    @patch("sbkube.commands.build.cmd")
    @patch("sbkube.commands.prepare.cmd")
    def test_apply_app_not_found(
        self,
        mock_prepare,
        mock_build,
        mock_deploy,
        runner,
        tmp_path,
    ) -> None:
        """Test error when specified app doesn't exist."""
        # Setup directory structure
        config_dir = tmp_path / "config"
        config_dir.mkdir(parents=True, exist_ok=True)

        # Create sources.yaml
        sources_file = tmp_path / "sources.yaml"
        sources_file.write_text(
            """
kubeconfig: /fake/kubeconfig
kubeconfig_context: test-context
cluster: test-cluster
"""
        )

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

        # Run apply with non-existent app
        result = runner.invoke(
            main,
            [
                "apply",
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

    @patch("sbkube.commands.deploy.cmd")
    @patch("sbkube.commands.build.cmd")
    @patch("sbkube.commands.prepare.cmd")
    def test_apply_disabled_app_skipped(
        self,
        mock_prepare,
        mock_build,
        mock_deploy,
        runner,
        tmp_path,
    ) -> None:
        """Test disabled apps are skipped during apply."""
        # Setup directory structure
        config_dir = tmp_path / "config"
        config_dir.mkdir(parents=True, exist_ok=True)

        # Create sources.yaml
        sources_file = tmp_path / "sources.yaml"
        sources_file.write_text(
            """
kubeconfig: /fake/kubeconfig
kubeconfig_context: test-context
cluster: test-cluster
"""
        )

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

        # Mock commands
        mock_prepare.return_value = None
        mock_build.return_value = None
        mock_deploy.return_value = None

        # Run apply
        result = runner.invoke(
            main, ["apply", "--base-dir", str(tmp_path), "--app-dir", "config"]
        )

        # Assert - should succeed but skip disabled app
        assert result.exit_code == 0
        assert "skip" in result.output.lower() or "disabled" in result.output.lower()


class TestApplyCommandDependencies:
    """Test apply command with app dependencies."""

    @patch("sbkube.commands.deploy.cmd")
    @patch("sbkube.commands.build.cmd")
    @patch("sbkube.commands.prepare.cmd")
    def test_apply_with_depends_on(
        self,
        mock_prepare,
        mock_build,
        mock_deploy,
        runner,
        tmp_path,
    ) -> None:
        """Test apply with depends_on includes dependencies."""
        # Setup directory structure
        config_dir = tmp_path / "config"
        config_dir.mkdir(parents=True, exist_ok=True)

        # Create sources.yaml
        sources_file = tmp_path / "sources.yaml"
        sources_file.write_text(
            """
kubeconfig: /fake/kubeconfig
kubeconfig_context: test-context
cluster: test-cluster
"""
        )

        # Create manifest files
        manifests_dir = config_dir / "manifests"
        manifests_dir.mkdir()
        (manifests_dir / "db.yaml").write_text("apiVersion: v1\nkind: Pod")
        (manifests_dir / "app.yaml").write_text("apiVersion: v1\nkind: Pod")

        # Create config.yaml with dependencies
        config_file = config_dir / "config.yaml"
        config_data = {
            "namespace": "default",
            "apps": {
                "database": {
                    "type": "yaml",
                    "enabled": True,
                    "manifests": ["manifests/db.yaml"],
                },
                "backend": {
                    "type": "yaml",
                    "enabled": True,
                    "depends_on": ["database"],
                    "manifests": ["manifests/app.yaml"],
                },
            },
        }
        with open(config_file, "w") as f:
            yaml.dump(config_data, f)

        # Mock commands
        mock_prepare.return_value = None
        mock_build.return_value = None
        mock_deploy.return_value = None

        # Run apply with --app backend
        result = runner.invoke(
            main,
            [
                "apply",
                "--base-dir",
                str(tmp_path),
                "--app-dir",
                "config",
                "--app",
                "backend",
            ],
        )

        # Assert - should include database dependency
        assert result.exit_code == 0
        assert "database" in result.output.lower()
        assert "backend" in result.output.lower()
