"""Tests for prepare command."""

from unittest.mock import patch

import pytest
import yaml
from click.testing import CliRunner

from sbkube.cli import main


@pytest.fixture
def runner():
    """Create CliRunner fixture."""
    return CliRunner()


class TestPrepareCommandHelp:
    """Test prepare command help."""

    def test_prepare_help(self, runner) -> None:
        """Test --help option shows help message."""
        result = runner.invoke(main, ["prepare", "--help"])

        assert result.exit_code == 0
        assert "prepare" in result.output.lower()
        assert "chart" in result.output.lower() or "download" in result.output.lower()


class TestPrepareCommandBasic:
    """Test basic prepare command scenarios."""

    @patch("sbkube.commands.prepare.check_helm_installed_or_exit")
    @patch("sbkube.commands.prepare.run_command")
    def test_prepare_requires_config_yaml(
        self,
        mock_run_command,
        mock_helm_check,
        runner,
        tmp_path,
    ) -> None:
        """Test prepare fails without config.yaml."""
        # Create app config directory without config.yaml
        config_dir = tmp_path / "config"
        config_dir.mkdir(parents=True, exist_ok=True)

        result = runner.invoke(
            main, ["prepare", "--base-dir", str(tmp_path), "--app-dir", "config"]
        )

        assert result.exit_code != 0
        assert "config" in result.output.lower() or "not found" in result.output.lower()


    @patch("sbkube.commands.prepare.resolve_cluster_config")
    @patch("sbkube.commands.prepare.check_helm_installed_or_exit")
    @patch("sbkube.commands.prepare.run_command")
    def test_prepare_helm_app_success(
        self,
        mock_run_command,
        mock_helm_check,
        mock_resolve_cluster,
        runner,
        tmp_path,
    ) -> None:
        """Test successful Helm app preparation."""
        # Setup directory structure
        config_dir = tmp_path / "config"
        config_dir.mkdir(parents=True, exist_ok=True)

        # Create a fake kubeconfig file
        kubeconfig_file = tmp_path / "kubeconfig"
        kubeconfig_data = """
apiVersion: v1
kind: Config
current-context: test-context
contexts:
- name: test-context
  context:
    cluster: test-cluster
    user: test-user
clusters:
- name: test-cluster
  cluster:
    server: https://localhost:6443
users:
- name: test-user
  user:
    token: fake-token
"""
        kubeconfig_file.write_text(kubeconfig_data)

        # Create sources.yaml
        sources_file = tmp_path / "sources.yaml"
        sources_data = {
            "kubeconfig": str(kubeconfig_file),
            "kubeconfig_context": "test-context",
            "cluster": "test-cluster",
            "helm_repos": {
                "bitnami": "https://charts.bitnami.com/bitnami",
            },
        }
        with open(sources_file, "w") as f:
            yaml.dump(sources_data, f)

        # Create config.yaml with Helm app
        config_file = config_dir / "config.yaml"
        config_data = {
            "namespace": "default",
            "apps": {
                "redis": {
                    "type": "helm",
                    "enabled": True,
                    "chart": "bitnami/redis",
                    "version": "17.0.0",
                }
            },
        }
        with open(config_file, "w") as f:
            yaml.dump(config_data, f)

        # Mock cluster config resolution (skip kubectl validation)
        mock_resolve_cluster.return_value = ("/fake/kubeconfig", "test-context")

        # Mock run_command to simulate helm operations
        mock_run_command.return_value = (0, "", "")

        # Run prepare
        result = runner.invoke(
            main, ["prepare", "--base-dir", str(tmp_path), "--app-dir", "config"]
        )

        # Assert
        assert result.exit_code == 0
        assert "redis" in result.output.lower()

    @patch("sbkube.commands.prepare.resolve_cluster_config")
    @patch("sbkube.commands.prepare.check_helm_installed_or_exit")
    @patch("sbkube.commands.prepare.run_command")
    def test_prepare_http_app_success(
        self,
        mock_run_command,
        mock_helm_check,
        mock_resolve_cluster,
        runner,
        tmp_path,
    ) -> None:
        """Test successful HTTP app preparation."""
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

        # Create config.yaml with HTTP app
        config_file = config_dir / "config.yaml"
        config_data = {
            "namespace": "default",
            "apps": {
                "external-manifest": {
                    "type": "http",
                    "enabled": True,
                    "url": "https://example.com/manifest.yaml",
                    "dest": "manifests/external.yaml",
                }
            },
        }
        with open(config_file, "w") as f:
            yaml.dump(config_data, f)

        # Mock cluster config resolution
        mock_resolve_cluster.return_value = ("/fake/kubeconfig", "test-context")

        # Mock run_command for wget/curl
        mock_run_command.return_value = (0, "", "")

        # Run prepare
        result = runner.invoke(
            main, ["prepare", "--base-dir", str(tmp_path), "--app-dir", "config"]
        )

        # Assert
        assert result.exit_code == 0
        assert "external-manifest" in result.output.lower()

    @patch("sbkube.commands.prepare.resolve_cluster_config")
    @patch("sbkube.commands.prepare.check_helm_installed_or_exit")
    @patch("sbkube.commands.prepare.run_command")
    def test_prepare_git_app_success(
        self,
        mock_run_command,
        mock_helm_check,
        mock_resolve_cluster,
        runner,
        tmp_path,
    ) -> None:
        """Test successful Git app preparation."""
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

        # Create config.yaml with Git app
        config_file = config_dir / "config.yaml"
        config_data = {
            "namespace": "default",
            "apps": {
                "git-repo": {
                    "type": "git",
                    "enabled": True,
                    "repo": "https://github.com/example/manifests.git",
                    "path": "k8s/manifests",
                }
            },
        }
        with open(config_file, "w") as f:
            yaml.dump(config_data, f)

        # Mock cluster config resolution
        mock_resolve_cluster.return_value = ("/fake/kubeconfig", "test-context")

        # Mock run_command for git clone
        mock_run_command.return_value = (0, "", "")

        # Run prepare
        result = runner.invoke(
            main, ["prepare", "--base-dir", str(tmp_path), "--app-dir", "config"]
        )

        # Assert
        assert result.exit_code == 0
        assert "git-repo" in result.output.lower()


class TestPrepareCommandOptions:
    """Test prepare command options."""

    @patch("sbkube.commands.prepare.resolve_cluster_config")
    @patch("sbkube.commands.prepare.check_helm_installed_or_exit")
    @patch("sbkube.commands.prepare.run_command")
    def test_prepare_dry_run(
        self,
        mock_run_command,
        mock_helm_check,
        mock_resolve_cluster,
        runner,
        tmp_path,
    ) -> None:
        """Test --dry-run option."""
        # Setup directory structure
        config_dir = tmp_path / "config"
        config_dir.mkdir(parents=True, exist_ok=True)

        # Create a fake kubeconfig file
        kubeconfig_file = tmp_path / "kubeconfig"
        kubeconfig_file.write_text("""
apiVersion: v1
kind: Config
current-context: test-context
contexts:
- name: test-context
  context:
    cluster: test-cluster
""")

        # Create sources.yaml
        sources_file = tmp_path / "sources.yaml"
        sources_data = {
            "kubeconfig": str(kubeconfig_file),
            "kubeconfig_context": "test-context",
            "cluster": "test-cluster",
            "helm_repos": {
                "bitnami": "https://charts.bitnami.com/bitnami",
            },
        }
        with open(sources_file, "w") as f:
            yaml.dump(sources_data, f)

        # Create config.yaml
        config_file = config_dir / "config.yaml"
        config_data = {
            "namespace": "default",
            "apps": {
                "redis": {
                    "type": "helm",
                    "enabled": True,
                    "chart": "bitnami/redis",
                    "version": "17.0.0",
                }
            },
        }
        with open(config_file, "w") as f:
            yaml.dump(config_data, f)

        # Mock cluster config resolution
        mock_resolve_cluster.return_value = ("/fake/kubeconfig", "test-context")

        # Run prepare with --dry-run
        result = runner.invoke(
            main,
            [
                "prepare",
                "--base-dir",
                str(tmp_path),
                "--app-dir",
                "config",
                "--dry-run",
            ],
        )

        # Assert - should succeed but not actually run helm commands
        assert result.exit_code == 0
        assert "dry-run" in result.output.lower() or "redis" in result.output.lower()

    @patch("sbkube.commands.prepare.resolve_cluster_config")
    @patch("sbkube.commands.prepare.check_helm_installed_or_exit")
    @patch("sbkube.commands.prepare.run_command")
    def test_prepare_disabled_app_skipped(
        self,
        mock_run_command,
        mock_helm_check,
        mock_resolve_cluster,
        runner,
        tmp_path,
    ) -> None:
        """Test disabled apps are skipped."""
        # Setup directory structure
        config_dir = tmp_path / "config"
        config_dir.mkdir(parents=True, exist_ok=True)

        # Create a fake kubeconfig file
        kubeconfig_file = tmp_path / "kubeconfig"
        kubeconfig_file.write_text("""
apiVersion: v1
kind: Config
current-context: test-context
""")

        # Create sources.yaml
        sources_file = tmp_path / "sources.yaml"
        sources_data = {
            "kubeconfig": str(kubeconfig_file),
            "kubeconfig_context": "test-context",
            "cluster": "test-cluster",
            "helm_repos": {
                "bitnami": "https://charts.bitnami.com/bitnami",
            },
        }
        with open(sources_file, "w") as f:
            yaml.dump(sources_data, f)

        # Create config.yaml with disabled app
        config_file = config_dir / "config.yaml"
        config_data = {
            "namespace": "default",
            "apps": {
                "redis": {
                    "type": "helm",
                    "enabled": False,
                    "chart": "bitnami/redis",
                }
            },
        }
        with open(config_file, "w") as f:
            yaml.dump(config_data, f)

        # Mock cluster config resolution
        mock_resolve_cluster.return_value = ("/fake/kubeconfig", "test-context")

        # Run prepare
        result = runner.invoke(
            main, ["prepare", "--base-dir", str(tmp_path), "--app-dir", "config"]
        )

        # Assert - should skip disabled app
        assert result.exit_code == 0
        assert "skip" in result.output.lower() or "disabled" in result.output.lower()


class TestPrepareCommandErrors:
    """Test prepare command error handling."""

    @patch("sbkube.commands.prepare.check_helm_installed_or_exit")
    @patch("sbkube.commands.prepare.run_command")
    def test_prepare_app_not_found(
        self,
        mock_run_command,
        mock_helm_check,
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
                "test": {
                    "type": "hook",
                    "enabled": True,
                    "tasks": [{"type": "command", "name": "test", "command": "echo test"}],
                }
            },
        }
        with open(config_file, "w") as f:
            yaml.dump(config_data, f)

        # Run prepare with non-existent app
        result = runner.invoke(
            main,
            [
                "prepare",
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
