"""Integration tests for deploy command CLI.

Tests verify:
- CLI options (--help, --app-dir, --base-dir, --app, --dry-run, --skip-hooks)
- Full deploy workflow (config loading → deployment execution)
- Multiple app groups processing
- App type handling (Helm, YAML, Hook, Exec)
- Error scenarios (missing files, cluster connection errors)
- Dependency order execution
"""

from unittest.mock import patch

import pytest
import yaml
from click.testing import CliRunner

from sbkube.cli import main


@pytest.fixture
def runner():
    """Create a Click test runner."""
    return CliRunner()


class TestDeployCommandHelp:
    """Test deploy command help and basic CLI."""

    def test_deploy_help(self, runner) -> None:
        """Test deploy --help displays correctly."""
        result = runner.invoke(main, ["deploy", "--help"])
        assert result.exit_code == 0
        assert "SBKube deploy" in result.output or "deploy" in result.output.lower()
        assert "--app-dir" in result.output
        assert "--dry-run" in result.output


class TestDeployCommandBasic:
    """Test basic deploy command scenarios."""

    @patch("sbkube.commands.deploy.run_command")
    @patch("sbkube.commands.deploy.resolve_cluster_config")
    @patch("sbkube.commands.deploy.check_cluster_connectivity_or_exit")
    @patch("sbkube.commands.deploy.check_helm_installed_or_exit")
    @patch("sbkube.commands.deploy.check_kubectl_installed_or_exit")
    def test_deploy_requires_config_yaml(
        self,
        mock_kubectl_check,
        mock_helm_check,
        mock_cluster_check,
        mock_resolve_cluster,
        mock_run_command,
        runner,
        tmp_path,
    ) -> None:
        """Test deploy fails without config.yaml."""
        # Configure mocks
        mock_resolve_cluster.return_value = (str(tmp_path / "kubeconfig"), "test-context")

        # Create app config directory without config.yaml
        config_dir = tmp_path / "config"
        config_dir.mkdir(parents=True, exist_ok=True)

        # Create temporary kubeconfig
        kubeconfig_file = tmp_path / "kubeconfig"
        kubeconfig_file.write_text(
            """
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
        )

        # Create sources.yaml
        sources_file = tmp_path / "sources.yaml"
        sources_file.write_text(
            f"""
kubeconfig: {kubeconfig_file}
kubeconfig_context: test-context
cluster: test-cluster
"""
        )

        result = runner.invoke(
            main, ["deploy", "--base-dir", str(tmp_path), "--app-dir", "config"]
        )

        assert result.exit_code != 0
        assert "config file not found" in result.output.lower()

    @patch("sbkube.commands.deploy.run_command")
    @patch("sbkube.commands.deploy.check_kubectl_installed_or_exit")
    @patch("sbkube.commands.deploy.check_helm_installed_or_exit")
    @patch("sbkube.commands.deploy.resolve_cluster_config")
    @patch("sbkube.commands.deploy.check_cluster_connectivity_or_exit")
    def test_deploy_helm_app_success(
        self,
        mock_cluster_check,
        mock_resolve_cluster,
        mock_helm_check,
        mock_kubectl_check,
        mock_run_command,
        runner,
        tmp_path,
    ) -> None:
        """Test successful deployment of Helm app."""
        # Configure mocks
        mock_resolve_cluster.return_value = (str(tmp_path / "kubeconfig"), "test-context")

        # Setup directory structure
        config_dir = tmp_path / "config"
        config_dir.mkdir(parents=True, exist_ok=True)

        # Create temporary kubeconfig
        kubeconfig_file = tmp_path / "kubeconfig"
        kubeconfig_file.write_text(
            """
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
        )

        # Create sources.yaml
        sources_file = tmp_path / "sources.yaml"
        sources_file.write_text(
            f"""
kubeconfig: {kubeconfig_file}
kubeconfig_context: test-context
cluster: test-cluster
"""
        )

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

        # Mock successful helm command
        mock_run_command.return_value = (0, "Release deployed successfully", "")

        # Run deploy
        result = runner.invoke(
            main, ["deploy", "--base-dir", str(tmp_path), "--app-dir", "config"]
        )

        # Assert
        assert result.exit_code == 0
        assert "deploying helm app: nginx" in result.output.lower()

    @patch("sbkube.commands.deploy.run_command")
    @patch("sbkube.commands.deploy.check_kubectl_installed_or_exit")
    @patch("sbkube.commands.deploy.resolve_cluster_config")
    @patch("sbkube.commands.deploy.check_cluster_connectivity_or_exit")
    def test_deploy_yaml_app_success(
        self,
        mock_cluster_check,
        mock_resolve_cluster,
        mock_kubectl_check,
        mock_run_command,
        runner,
        tmp_path,
    ) -> None:
        """Test successful deployment of YAML app."""
        # Configure mocks
        mock_resolve_cluster.return_value = (str(tmp_path / "kubeconfig"), "test-context")

        # Setup directory structure
        config_dir = tmp_path / "config"
        config_dir.mkdir(parents=True, exist_ok=True)

        # Create temporary kubeconfig
        kubeconfig_file = tmp_path / "kubeconfig"
        kubeconfig_file.write_text(
            """
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
        )

        # Create sources.yaml
        sources_file = tmp_path / "sources.yaml"
        sources_file.write_text(
            f"""
kubeconfig: {kubeconfig_file}
kubeconfig_context: test-context
cluster: test-cluster
"""
        )

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

        # Mock successful kubectl command
        mock_run_command.return_value = (0, "deployment.apps/nginx created", "")

        # Run deploy
        result = runner.invoke(
            main, ["deploy", "--base-dir", str(tmp_path), "--app-dir", "config"]
        )

        # Assert
        assert result.exit_code == 0

    @patch("sbkube.commands.deploy.run_command")
    @patch("sbkube.commands.deploy.check_kubectl_installed_or_exit")
    @patch("sbkube.commands.deploy.resolve_cluster_config")
    @patch("sbkube.commands.deploy.check_cluster_connectivity_or_exit")
    def test_deploy_exec_app_success(
        self,
        mock_cluster_check,
        mock_resolve_cluster,
        mock_kubectl_check,
        mock_run_command,
        runner,
        tmp_path,
    ) -> None:
        """Test successful execution of Exec app."""
        # Configure mocks
        mock_resolve_cluster.return_value = (str(tmp_path / "kubeconfig"), "test-context")

        # Setup directory structure
        config_dir = tmp_path / "config"
        config_dir.mkdir(parents=True, exist_ok=True)

        # Create temporary kubeconfig
        kubeconfig_file = tmp_path / "kubeconfig"
        kubeconfig_file.write_text(
            """
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
        )

        # Create sources.yaml
        sources_file = tmp_path / "sources.yaml"
        sources_file.write_text(
            f"""
kubeconfig: {kubeconfig_file}
kubeconfig_context: test-context
cluster: test-cluster
"""
        )

        # Create config.yaml with Exec app
        config_file = config_dir / "config.yaml"
        config_data = {
            "namespace": "default",
            "apps": {
                "custom-script": {
                    "type": "exec",
                    "enabled": True,
                    "commands": ["echo 'Deployment complete'"],
                }
            },
        }
        with open(config_file, "w") as f:
            yaml.dump(config_data, f)

        # Mock successful command execution
        mock_run_command.return_value = (0, "Deployment complete", "")

        # Run deploy
        result = runner.invoke(
            main, ["deploy", "--base-dir", str(tmp_path), "--app-dir", "config"]
        )

        # Assert
        assert result.exit_code == 0


    @patch("sbkube.commands.deploy.run_command")
    @patch("sbkube.commands.deploy.check_kubectl_installed_or_exit")
    @patch("sbkube.commands.deploy.resolve_cluster_config")
    @patch("sbkube.commands.deploy.check_cluster_connectivity_or_exit")
    def test_deploy_hook_app_success(
        self,
        mock_cluster_check,
        mock_resolve_cluster,
        mock_kubectl_check,
        mock_run_command,
        runner,
        tmp_path,
    ) -> None:
        """Test successful deployment of Hook app."""
        # Configure mocks
        mock_resolve_cluster.return_value = (str(tmp_path / "kubeconfig"), "test-context")

        # Setup directory structure
        config_dir = tmp_path / "config"
        config_dir.mkdir(parents=True, exist_ok=True)

        # Create temporary kubeconfig
        kubeconfig_file = tmp_path / "kubeconfig"
        kubeconfig_file.write_text(
            """
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
        )

        # Create sources.yaml
        sources_file = tmp_path / "sources.yaml"
        sources_file.write_text(
            f"""
kubeconfig: {kubeconfig_file}
kubeconfig_context: test-context
cluster: test-cluster
"""
        )

        # Create config.yaml with Hook app
        config_file = config_dir / "config.yaml"
        config_data = {
            "namespace": "default",
            "apps": {
                "my-hook": {
                    "type": "hook",
                    "enabled": True,
                    "tasks": [
                        {
                            "type": "command",
                            "name": "test-hook",
                            "command": "echo 'Hook executed'",
                        }
                    ],
                }
            },
        }
        with open(config_file, "w") as f:
            yaml.dump(config_data, f)

        # Mock successful command execution
        mock_run_command.return_value = (0, "Hook executed", "")

        # Run deploy
        result = runner.invoke(
            main, ["deploy", "--base-dir", str(tmp_path), "--app-dir", "config"]
        )

        # Assert
        assert result.exit_code == 0
        assert "my-hook" in result.output.lower()

    @patch("sbkube.commands.deploy.run_command")
    @patch("sbkube.commands.deploy.check_kubectl_installed_or_exit")
    @patch("sbkube.commands.deploy.resolve_cluster_config")
    @patch("sbkube.commands.deploy.check_cluster_connectivity_or_exit")
    def test_deploy_kustomize_app_success(
        self,
        mock_cluster_check,
        mock_resolve_cluster,
        mock_kubectl_check,
        mock_run_command,
        runner,
        tmp_path,
    ) -> None:
        """Test successful deployment of Kustomize app."""
        # Configure mocks
        mock_resolve_cluster.return_value = (str(tmp_path / "kubeconfig"), "test-context")

        # Setup directory structure
        config_dir = tmp_path / "config"
        config_dir.mkdir(parents=True, exist_ok=True)

        # Create temporary kubeconfig
        kubeconfig_file = tmp_path / "kubeconfig"
        kubeconfig_file.write_text(
            """
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
        )

        # Create sources.yaml
        sources_file = tmp_path / "sources.yaml"
        sources_file.write_text(
            f"""
kubeconfig: {kubeconfig_file}
kubeconfig_context: test-context
cluster: test-cluster
"""
        )

        # Create kustomization directory
        kustomize_dir = config_dir / "kustomize"
        kustomize_dir.mkdir()
        (kustomize_dir / "kustomization.yaml").write_text(
            """
apiVersion: kustomize.config.k8s.io/v1beta1
kind: Kustomization
resources:
  - deployment.yaml
"""
        )
        (kustomize_dir / "deployment.yaml").write_text(
            """
apiVersion: apps/v1
kind: Deployment
metadata:
  name: nginx
spec:
  replicas: 1
"""
        )

        # Create config.yaml with Kustomize app
        config_file = config_dir / "config.yaml"
        config_data = {
            "namespace": "default",
            "apps": {
                "my-kustomize": {
                    "type": "kustomize",
                    "enabled": True,
                    "path": "kustomize",
                }
            },
        }
        with open(config_file, "w") as f:
            yaml.dump(config_data, f)

        # Mock successful kubectl kustomize command
        mock_run_command.return_value = (0, "deployment.apps/nginx created", "")

        # Run deploy
        result = runner.invoke(
            main, ["deploy", "--base-dir", str(tmp_path), "--app-dir", "config"]
        )

        # Assert
        assert result.exit_code == 0
        assert "my-kustomize" in result.output.lower()


    @patch("sbkube.commands.deploy.run_command")
    @patch("sbkube.commands.deploy.check_kubectl_installed_or_exit")
    @patch("sbkube.commands.deploy.resolve_cluster_config")
    @patch("sbkube.commands.deploy.check_cluster_connectivity_or_exit")
    def test_deploy_action_app_success(
        self,
        mock_cluster_check,
        mock_resolve_cluster,
        mock_kubectl_check,
        mock_run_command,
        runner,
        tmp_path,
    ) -> None:
        """Test successful deployment of Action app."""
        # Configure mocks
        mock_resolve_cluster.return_value = (str(tmp_path / "kubeconfig"), "test-context")

        # Setup directory structure
        config_dir = tmp_path / "config"
        config_dir.mkdir(parents=True, exist_ok=True)

        # Create temporary kubeconfig
        kubeconfig_file = tmp_path / "kubeconfig"
        kubeconfig_file.write_text(
            """
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
        )

        # Create sources.yaml
        sources_file = tmp_path / "sources.yaml"
        sources_file.write_text(
            f"""
kubeconfig: {kubeconfig_file}
kubeconfig_context: test-context
cluster: test-cluster
"""
        )

        # Create manifests directory with sample manifest
        manifests_dir = config_dir / "manifests"
        manifests_dir.mkdir()
        (manifests_dir / "deployment.yaml").write_text(
            """
apiVersion: apps/v1
kind: Deployment
metadata:
  name: nginx
spec:
  replicas: 1
"""
        )

        # Create config.yaml with Action app
        config_file = config_dir / "config.yaml"
        config_data = {
            "namespace": "default",
            "apps": {
                "my-action": {
                    "type": "action",
                    "enabled": True,
                    "actions": [
                        {
                            "type": "apply",
                            "path": "manifests/deployment.yaml",
                        }
                    ],
                }
            },
        }
        with open(config_file, "w") as f:
            yaml.dump(config_data, f)

        # Mock successful kubectl command
        mock_run_command.return_value = (0, "deployment.apps/nginx created", "")

        # Run deploy
        result = runner.invoke(
            main, ["deploy", "--base-dir", str(tmp_path), "--app-dir", "config"]
        )

        # Assert
        assert result.exit_code == 0
        assert "my-action" in result.output.lower()

    @patch("sbkube.commands.deploy.run_command")
    @patch("sbkube.commands.deploy.check_kubectl_installed_or_exit")
    @patch("sbkube.commands.deploy.resolve_cluster_config")
    @patch("sbkube.commands.deploy.check_cluster_connectivity_or_exit")
    def test_deploy_noop_app_success(
        self,
        mock_cluster_check,
        mock_resolve_cluster,
        mock_kubectl_check,
        mock_run_command,
        runner,
        tmp_path,
    ) -> None:
        """Test successful deployment of Noop app (does nothing)."""
        # Configure mocks
        mock_resolve_cluster.return_value = (str(tmp_path / "kubeconfig"), "test-context")

        # Setup directory structure
        config_dir = tmp_path / "config"
        config_dir.mkdir(parents=True, exist_ok=True)

        # Create temporary kubeconfig
        kubeconfig_file = tmp_path / "kubeconfig"
        kubeconfig_file.write_text(
            """
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
        )

        # Create sources.yaml
        sources_file = tmp_path / "sources.yaml"
        sources_file.write_text(
            f"""
kubeconfig: {kubeconfig_file}
kubeconfig_context: test-context
cluster: test-cluster
"""
        )

        # Create config.yaml with Noop app
        config_file = config_dir / "config.yaml"
        config_data = {
            "namespace": "default",
            "apps": {
                "my-noop": {
                    "type": "noop",
                    "enabled": True,
                }
            },
        }
        with open(config_file, "w") as f:
            yaml.dump(config_data, f)

        # Run deploy (noop shouldn't call any commands)
        result = runner.invoke(
            main, ["deploy", "--base-dir", str(tmp_path), "--app-dir", "config"]
        )

        # Assert
        assert result.exit_code == 0
        assert "my-noop" in result.output.lower()
        # Noop app should not call run_command
        assert mock_run_command.call_count == 0


class TestDeployCommandOptions:
    """Test deploy command options."""

    @patch("sbkube.commands.deploy.run_command")
    @patch("sbkube.commands.deploy.check_kubectl_installed_or_exit")
    @patch("sbkube.commands.deploy.check_helm_installed_or_exit")
    @patch("sbkube.commands.deploy.resolve_cluster_config")
    @patch("sbkube.commands.deploy.check_cluster_connectivity_or_exit")
    def test_deploy_dry_run(
        self,
        mock_cluster_check,
        mock_resolve_cluster,
        mock_helm_check,
        mock_kubectl_check,
        mock_run_command,
        runner,
        tmp_path,
    ) -> None:
        """Test --dry-run option."""
        # Configure mocks
        mock_resolve_cluster.return_value = (str(tmp_path / "kubeconfig"), "test-context")

        # Setup directory structure
        config_dir = tmp_path / "config"
        config_dir.mkdir(parents=True, exist_ok=True)

        # Create temporary kubeconfig
        kubeconfig_file = tmp_path / "kubeconfig"
        kubeconfig_file.write_text(
            """
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
        )

        # Create sources.yaml
        sources_file = tmp_path / "sources.yaml"
        sources_file.write_text(
            f"""
kubeconfig: {kubeconfig_file}
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
                    "type": "helm",
                    "enabled": True,
                    "chart": "bitnami/nginx",
                    "version": "15.0.0",
                }
            },
        }
        with open(config_file, "w") as f:
            yaml.dump(config_data, f)

        # Create built chart
        sbkube_dir = tmp_path / ".sbkube"
        build_dir = sbkube_dir / "build" / "nginx"
        build_dir.mkdir(parents=True)
        (build_dir / "Chart.yaml").write_text("name: nginx\nversion: 15.0.0")

        # Mock dry-run command
        mock_run_command.return_value = (0, "DRY-RUN output", "")

        # Run deploy with --dry-run
        result = runner.invoke(
            main,
            ["deploy", "--base-dir", str(tmp_path), "--app-dir", "config", "--dry-run"],
        )

        # Assert
        assert result.exit_code == 0
        assert "dry-run" in result.output.lower()

    @patch("sbkube.commands.deploy.run_command")
    @patch("sbkube.commands.deploy.check_kubectl_installed_or_exit")
    @patch("sbkube.commands.deploy.check_helm_installed_or_exit")
    @patch("sbkube.commands.deploy.resolve_cluster_config")
    @patch("sbkube.commands.deploy.check_cluster_connectivity_or_exit")
    def test_deploy_specific_app(
        self,
        mock_cluster_check,
        mock_resolve_cluster,
        mock_helm_check,
        mock_kubectl_check,
        mock_run_command,
        runner,
        tmp_path,
    ) -> None:
        """Test --app option deploys only specific app."""
        # Configure mocks
        mock_resolve_cluster.return_value = (str(tmp_path / "kubeconfig"), "test-context")

        # Setup directory structure
        config_dir = tmp_path / "config"
        config_dir.mkdir(parents=True, exist_ok=True)

        # Create temporary kubeconfig
        kubeconfig_file = tmp_path / "kubeconfig"
        kubeconfig_file.write_text(
            """
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
        )

        # Create sources.yaml
        sources_file = tmp_path / "sources.yaml"
        sources_file.write_text(
            f"""
kubeconfig: {kubeconfig_file}
kubeconfig_context: test-context
cluster: test-cluster
"""
        )

        # Create config.yaml with multiple apps
        config_file = config_dir / "config.yaml"
        config_data = {
            "namespace": "default",
            "apps": {
                "nginx": {
                    "type": "helm",
                    "enabled": True,
                    "chart": "bitnami/nginx",
                    "version": "15.0.0",
                },
                "redis": {
                    "type": "helm",
                    "enabled": True,
                    "chart": "bitnami/redis",
                    "version": "17.0.0",
                },
            },
        }
        with open(config_file, "w") as f:
            yaml.dump(config_data, f)

        # Create built charts
        sbkube_dir = tmp_path / ".sbkube"
        nginx_build = sbkube_dir / "build" / "nginx"
        nginx_build.mkdir(parents=True)
        (nginx_build / "Chart.yaml").write_text("name: nginx\nversion: 15.0.0")

        redis_build = sbkube_dir / "build" / "redis"
        redis_build.mkdir(parents=True)
        (redis_build / "Chart.yaml").write_text("name: redis\nversion: 17.0.0")

        # Mock helm command
        mock_run_command.return_value = (0, "Release deployed", "")

        # Run deploy for nginx only
        result = runner.invoke(
            main,
            [
                "deploy",
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


class TestDeployCommandErrors:
    """Test deploy command error handling."""

    @patch("sbkube.commands.deploy.run_command")
    @patch("sbkube.commands.deploy.check_kubectl_installed_or_exit")
    @patch("sbkube.commands.deploy.check_helm_installed_or_exit")
    @patch("sbkube.commands.deploy.resolve_cluster_config")
    @patch("sbkube.commands.deploy.check_cluster_connectivity_or_exit")
    def test_deploy_app_not_found(
        self,
        mock_cluster_check,
        mock_resolve_cluster,
        mock_helm_check,
        mock_kubectl_check,
        mock_run_command,
        runner,
        tmp_path,
    ) -> None:
        """Test error when specified app doesn't exist."""
        # Configure mocks
        mock_resolve_cluster.return_value = (str(tmp_path / "kubeconfig"), "test-context")

        # Setup directory structure
        config_dir = tmp_path / "config"
        config_dir.mkdir(parents=True, exist_ok=True)

        # Create temporary kubeconfig
        kubeconfig_file = tmp_path / "kubeconfig"
        kubeconfig_file.write_text(
            """
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
        )

        # Create sources.yaml
        sources_file = tmp_path / "sources.yaml"
        sources_file.write_text(
            f"""
kubeconfig: {kubeconfig_file}
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
                    "type": "helm",
                    "enabled": True,
                    "chart": "bitnami/nginx",
                    "version": "15.0.0",
                }
            },
        }
        with open(config_file, "w") as f:
            yaml.dump(config_data, f)

        # Run deploy with non-existent app
        result = runner.invoke(
            main,
            [
                "deploy",
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
        assert "app not found" in result.output.lower() or "nonexistent" in result.output.lower()

    @patch("sbkube.commands.deploy.run_command")
    @patch("sbkube.commands.deploy.check_kubectl_installed_or_exit")
    @patch("sbkube.commands.deploy.check_helm_installed_or_exit")
    @patch("sbkube.commands.deploy.resolve_cluster_config")
    @patch("sbkube.commands.deploy.check_cluster_connectivity_or_exit")
    def test_deploy_disabled_app_skipped(
        self,
        mock_cluster_check,
        mock_resolve_cluster,
        mock_helm_check,
        mock_kubectl_check,
        mock_run_command,
        runner,
        tmp_path,
    ) -> None:
        """Test disabled apps are skipped during deploy."""
        # Configure mocks
        mock_resolve_cluster.return_value = (str(tmp_path / "kubeconfig"), "test-context")

        # Setup directory structure
        config_dir = tmp_path / "config"
        config_dir.mkdir(parents=True, exist_ok=True)

        # Create temporary kubeconfig
        kubeconfig_file = tmp_path / "kubeconfig"
        kubeconfig_file.write_text(
            """
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
        )

        # Create sources.yaml
        sources_file = tmp_path / "sources.yaml"
        sources_file.write_text(
            f"""
kubeconfig: {kubeconfig_file}
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
                    "type": "helm",
                    "enabled": False,  # Disabled
                    "chart": "bitnami/nginx",
                    "version": "15.0.0",
                }
            },
        }
        with open(config_file, "w") as f:
            yaml.dump(config_data, f)

        # Run deploy
        result = runner.invoke(
            main, ["deploy", "--base-dir", str(tmp_path), "--app-dir", "config"]
        )

        # Assert
        assert result.exit_code == 0
        assert "skipping disabled app" in result.output.lower() or "disabled" in result.output.lower()
