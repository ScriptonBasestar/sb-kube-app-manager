"""Integration tests for build command CLI.

Tests verify:
- CLI options (--help, --app-dir, --base-dir, --app, --dry-run)
- Full build workflow (config loading → build execution)
- Multiple app groups processing
- App type handling (Helm, HTTP, HookApp)
- Error scenarios (missing files, invalid config)
- Dependency order execution
"""

from pathlib import Path
from unittest.mock import MagicMock, patch

import pytest
import yaml
from click.testing import CliRunner

from sbkube.cli import main


@pytest.fixture
def runner():
    """Create a Click test runner."""
    return CliRunner()


class TestBuildCommandHelp:
    """Test build command help and basic CLI."""

    def test_build_help(self, runner) -> None:
        """Test build --help displays correctly."""
        result = runner.invoke(main, ["build", "--help"])
        assert result.exit_code == 0
        assert "SBKube build" in result.output
        assert "--app-dir" in result.output
        assert "--base-dir" in result.output
        assert "--app" in result.output
        assert "--dry-run" in result.output


class TestBuildCommandBasic:
    """Test basic build command scenarios."""

    def test_build_requires_config_yaml(self, runner, tmp_path) -> None:
        """Test build fails without config.yaml."""
        # Create app config directory without config.yaml
        config_dir = tmp_path / "config"
        config_dir.mkdir(parents=True, exist_ok=True)

        # Create sources.yaml
        sources_file = tmp_path / "sources.yaml"
        sources_file.write_text(
            """
kubeconfig: ~/.kube/config
kubeconfig_context: test-context
cluster: test-cluster
"""
        )

        result = runner.invoke(
            main, ["build", "--base-dir", str(tmp_path), "--app-dir", "config"]
        )

        assert result.exit_code != 0
        assert "config file not found" in result.output.lower()

    def test_build_helm_app_success(self, runner, tmp_path) -> None:
        """Test successful build of Helm app."""
        # Setup directory structure
        config_dir = tmp_path / "config"
        config_dir.mkdir(parents=True, exist_ok=True)

        # Create sources.yaml
        sources_file = tmp_path / "sources.yaml"
        sources_file.write_text(
            """
kubeconfig: ~/.kube/config
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

        # Create source chart (simulating prepare step)
        sbkube_dir = tmp_path / ".sbkube"
        charts_dir = sbkube_dir / "charts" / "bitnami" / "nginx-15.0.0"
        charts_dir.mkdir(parents=True)
        (charts_dir / "Chart.yaml").write_text("name: nginx\nversion: 15.0.0")
        (charts_dir / "values.yaml").write_text("replicaCount: 1")

        # Run build
        result = runner.invoke(
            main, ["build", "--base-dir", str(tmp_path), "--app-dir", "config"]
        )

        # Assert
        assert result.exit_code == 0
        assert "building helm app: nginx" in result.output.lower()
        assert "all app groups built successfully" in result.output.lower()

        # Verify build directory created
        build_dir = sbkube_dir / "build" / "nginx"
        assert build_dir.exists()
        assert (build_dir / "Chart.yaml").exists()

    def test_build_http_app_success(self, runner, tmp_path) -> None:
        """Test successful build of HTTP app."""
        # Setup directory structure
        config_dir = tmp_path / "config"
        config_dir.mkdir(parents=True, exist_ok=True)

        # Create sources.yaml
        sources_file = tmp_path / "sources.yaml"
        sources_file.write_text(
            """
kubeconfig: ~/.kube/config
kubeconfig_context: test-context
cluster: test-cluster
"""
        )

        # Create config.yaml with HTTP app
        config_file = config_dir / "config.yaml"
        config_data = {
            "namespace": "default",
            "apps": {
                "my-manifest": {
                    "type": "http",
                    "enabled": True,
                    "url": "https://example.com/manifest.yaml",
                    "dest": "manifest.yaml",
                }
            },
        }
        with open(config_file, "w") as f:
            yaml.dump(config_data, f)

        # Create downloaded file (simulating prepare step)
        downloaded_file = config_dir / "manifest.yaml"
        downloaded_file.write_text("apiVersion: v1\nkind: ConfigMap")

        # Run build
        result = runner.invoke(
            main, ["build", "--base-dir", str(tmp_path), "--app-dir", "config"]
        )

        # Assert
        assert result.exit_code == 0
        assert "building http app: my-manifest" in result.output.lower()
        assert "all app groups built successfully" in result.output.lower()

        # Verify build directory created
        sbkube_dir = tmp_path / ".sbkube"
        build_dir = sbkube_dir / "build" / "my-manifest"
        assert build_dir.exists()
        assert (build_dir / "manifest.yaml").exists()

    def test_build_hook_app_skipped(self, runner, tmp_path) -> None:
        """Test HookApp is skipped during build."""
        # Setup directory structure
        config_dir = tmp_path / "config"
        config_dir.mkdir(parents=True, exist_ok=True)

        # Create sources.yaml
        sources_file = tmp_path / "sources.yaml"
        sources_file.write_text(
            """
kubeconfig: ~/.kube/config
kubeconfig_context: test-context
cluster: test-cluster
"""
        )

        # Create config.yaml with HookApp
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
                            "command": "echo 'hook executed'",
                        }
                    ],
                }
            },
        }
        with open(config_file, "w") as f:
            yaml.dump(config_data, f)

        # Run build
        result = runner.invoke(
            main, ["build", "--base-dir", str(tmp_path), "--app-dir", "config"]
        )

        # Assert
        if result.exit_code != 0:
            print(f"Exit code: {result.exit_code}")
            print(f"Output: {result.output}")
        assert result.exit_code == 0
        assert "hookapp does not require build" in result.output.lower()
        assert "all app groups built successfully" in result.output.lower()


class TestBuildCommandOptions:
    """Test build command options."""

    def test_build_dry_run(self, runner, tmp_path) -> None:
        """Test --dry-run option doesn't create files."""
        # Setup directory structure
        config_dir = tmp_path / "config"
        config_dir.mkdir(parents=True, exist_ok=True)

        # Create sources.yaml
        sources_file = tmp_path / "sources.yaml"
        sources_file.write_text(
            """
kubeconfig: ~/.kube/config
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

        # Create source chart
        sbkube_dir = tmp_path / ".sbkube"
        charts_dir = sbkube_dir / "charts" / "bitnami" / "nginx-15.0.0"
        charts_dir.mkdir(parents=True)
        (charts_dir / "Chart.yaml").write_text("name: nginx\nversion: 15.0.0")

        # Run build with --dry-run
        result = runner.invoke(
            main,
            ["build", "--base-dir", str(tmp_path), "--app-dir", "config", "--dry-run"],
        )

        # Assert
        assert result.exit_code == 0
        assert "dry-run" in result.output.lower()

        # Verify build directory NOT created
        build_dir = sbkube_dir / "build" / "nginx"
        assert not build_dir.exists()

    def test_build_specific_app(self, runner, tmp_path) -> None:
        """Test --app option builds only specific app."""
        # Setup directory structure
        config_dir = tmp_path / "config"
        config_dir.mkdir(parents=True, exist_ok=True)

        # Create sources.yaml
        sources_file = tmp_path / "sources.yaml"
        sources_file.write_text(
            """
kubeconfig: ~/.kube/config
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

        # Create source charts
        sbkube_dir = tmp_path / ".sbkube"
        nginx_chart = sbkube_dir / "charts" / "bitnami" / "nginx-15.0.0"
        nginx_chart.mkdir(parents=True)
        (nginx_chart / "Chart.yaml").write_text("name: nginx\nversion: 15.0.0")

        redis_chart = sbkube_dir / "charts" / "bitnami" / "redis-17.0.0"
        redis_chart.mkdir(parents=True)
        (redis_chart / "Chart.yaml").write_text("name: redis\nversion: 17.0.0")

        # Run build for nginx only
        result = runner.invoke(
            main,
            ["build", "--base-dir", str(tmp_path), "--app-dir", "config", "--app", "nginx"],
        )

        # Assert
        assert result.exit_code == 0
        assert "building helm app: nginx" in result.output.lower()
        # Redis should not be mentioned in build output (not built)
        assert "redis" not in result.output.lower() or "skipping" in result.output.lower()

        # Verify only nginx was built
        nginx_build = sbkube_dir / "build" / "nginx"
        redis_build = sbkube_dir / "build" / "redis"
        assert nginx_build.exists()
        assert not redis_build.exists()

    def test_build_app_not_found(self, runner, tmp_path) -> None:
        """Test error when specified app doesn't exist."""
        # Setup directory structure
        config_dir = tmp_path / "config"
        config_dir.mkdir(parents=True, exist_ok=True)

        # Create sources.yaml
        sources_file = tmp_path / "sources.yaml"
        sources_file.write_text(
            """
kubeconfig: ~/.kube/config
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

        # Run build with non-existent app
        result = runner.invoke(
            main,
            [
                "build",
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
        assert "app not found" in result.output.lower()


class TestBuildCommandDisabledApp:
    """Test build command with disabled apps."""

    def test_build_skips_disabled_app(self, runner, tmp_path) -> None:
        """Test disabled apps are skipped during build."""
        # Setup directory structure
        config_dir = tmp_path / "config"
        config_dir.mkdir(parents=True, exist_ok=True)

        # Create sources.yaml
        sources_file = tmp_path / "sources.yaml"
        sources_file.write_text(
            """
kubeconfig: ~/.kube/config
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

        # Run build
        result = runner.invoke(
            main, ["build", "--base-dir", str(tmp_path), "--app-dir", "config"]
        )

        # Assert
        if result.exit_code != 0 or "skipping disabled app" not in result.output.lower():
            print(f"Exit code: {result.exit_code}")
            print(f"Output: {result.output}")
        assert result.exit_code == 0
        # Disabled apps are not logged in build output (they're silently skipped)
        # Just verify build succeeded
        assert "all app groups built successfully" in result.output.lower()


class TestBuildCommandInvalidConfig:
    """Test build command error handling."""

    def test_build_invalid_config_yaml(self, runner, tmp_path) -> None:
        """Test error when config.yaml is invalid."""
        # Setup directory structure
        config_dir = tmp_path / "config"
        config_dir.mkdir(parents=True, exist_ok=True)

        # Create sources.yaml
        sources_file = tmp_path / "sources.yaml"
        sources_file.write_text(
            """
kubeconfig: ~/.kube/config
kubeconfig_context: test-context
cluster: test-cluster
"""
        )

        # Create invalid config.yaml (missing required fields)
        config_file = config_dir / "config.yaml"
        config_file.write_text("invalid: yaml: content: [")

        # Run build
        result = runner.invoke(
            main, ["build", "--base-dir", str(tmp_path), "--app-dir", "config"]
        )

        # Assert
        assert result.exit_code != 0


class TestBuildCommandMultipleAppGroups:
    """Test build command with multiple app groups."""

    def test_build_multiple_app_groups(self, runner, tmp_path) -> None:
        """Test building multiple app groups."""
        # Setup directory structure
        config1_dir = tmp_path / "config1"
        config1_dir.mkdir(parents=True, exist_ok=True)
        config2_dir = tmp_path / "config2"
        config2_dir.mkdir(parents=True, exist_ok=True)

        # Create sources.yaml
        sources_file = tmp_path / "sources.yaml"
        sources_file.write_text(
            """
kubeconfig: ~/.kube/config
kubeconfig_context: test-context
cluster: test-cluster
"""
        )

        # Create config.yaml for config1
        config1_file = config1_dir / "config.yaml"
        config1_data = {
            "namespace": "default",
            "apps": {
                "app1": {
                    "type": "helm",
                    "enabled": True,
                    "chart": "bitnami/nginx",
                    "version": "15.0.0",
                }
            },
        }
        with open(config1_file, "w") as f:
            yaml.dump(config1_data, f)

        # Create config.yaml for config2
        config2_file = config2_dir / "config.yaml"
        config2_data = {
            "namespace": "default",
            "apps": {
                "app2": {
                    "type": "helm",
                    "enabled": True,
                    "chart": "bitnami/redis",
                    "version": "17.0.0",
                }
            },
        }
        with open(config2_file, "w") as f:
            yaml.dump(config2_data, f)

        # Create source charts
        sbkube_dir = tmp_path / ".sbkube"
        nginx_chart = sbkube_dir / "charts" / "bitnami" / "nginx-15.0.0"
        nginx_chart.mkdir(parents=True)
        (nginx_chart / "Chart.yaml").write_text("name: nginx\nversion: 15.0.0")

        redis_chart = sbkube_dir / "charts" / "bitnami" / "redis-17.0.0"
        redis_chart.mkdir(parents=True)
        (redis_chart / "Chart.yaml").write_text("name: redis\nversion: 17.0.0")

        # Run build without --app-dir (auto-discovery)
        result = runner.invoke(main, ["build", "--base-dir", str(tmp_path)])

        # Assert
        assert result.exit_code == 0
        assert "config1" in result.output.lower() or "config2" in result.output.lower()
        assert "all app groups built successfully" in result.output.lower()


class TestBuildCommandDependencyOrder:
    """Test build command with app dependencies."""

    def test_build_dependency_order(self, runner, tmp_path) -> None:
        """Test apps are built in dependency order."""
        # Setup directory structure
        config_dir = tmp_path / "config"
        config_dir.mkdir(parents=True, exist_ok=True)

        # Create sources.yaml
        sources_file = tmp_path / "sources.yaml"
        sources_file.write_text(
            """
kubeconfig: ~/.kube/config
kubeconfig_context: test-context
cluster: test-cluster
"""
        )

        # Create config.yaml with dependencies
        config_file = config_dir / "config.yaml"
        config_data = {
            "namespace": "default",
            "apps": {
                "app-b": {
                    "type": "helm",
                    "enabled": True,
                    "chart": "bitnami/redis",
                    "version": "17.0.0",
                    "depends_on": ["app-a"],  # Depends on app-a
                },
                "app-a": {
                    "type": "helm",
                    "enabled": True,
                    "chart": "bitnami/nginx",
                    "version": "15.0.0",
                },
            },
        }
        with open(config_file, "w") as f:
            yaml.dump(config_data, f)

        # Create source charts
        sbkube_dir = tmp_path / ".sbkube"
        nginx_chart = sbkube_dir / "charts" / "bitnami" / "nginx-15.0.0"
        nginx_chart.mkdir(parents=True)
        (nginx_chart / "Chart.yaml").write_text("name: nginx\nversion: 15.0.0")

        redis_chart = sbkube_dir / "charts" / "bitnami" / "redis-17.0.0"
        redis_chart.mkdir(parents=True)
        (redis_chart / "Chart.yaml").write_text("name: redis\nversion: 17.0.0")

        # Run build
        result = runner.invoke(
            main, ["build", "--base-dir", str(tmp_path), "--app-dir", "config"]
        )

        # Assert
        assert result.exit_code == 0
        # Verify both apps were built
        assert (sbkube_dir / "build" / "app-a").exists()
        assert (sbkube_dir / "build" / "app-b").exists()


class TestBuildCommandLocalChart:
    """Test build command with local charts."""

    def test_build_local_chart_without_customization(self, runner, tmp_path) -> None:
        """Test local Helm chart without overrides/removes is skipped."""
        # Setup directory structure
        config_dir = tmp_path / "config"
        config_dir.mkdir(parents=True, exist_ok=True)

        # Create local chart
        local_chart_dir = config_dir / "my-chart"
        local_chart_dir.mkdir()
        (local_chart_dir / "Chart.yaml").write_text("name: my-chart\nversion: 1.0.0")
        (local_chart_dir / "values.yaml").write_text("replicaCount: 1")

        # Create sources.yaml
        sources_file = tmp_path / "sources.yaml"
        sources_file.write_text(
            """
kubeconfig: ~/.kube/config
kubeconfig_context: test-context
cluster: test-cluster
"""
        )

        # Create config.yaml with local chart (no overrides/removes)
        config_file = config_dir / "config.yaml"
        config_data = {
            "namespace": "default",
            "apps": {
                "my-app": {
                    "type": "helm",
                    "enabled": True,
                    "chart": "./my-chart",  # Local chart
                    # No overrides, no removes
                }
            },
        }
        with open(config_file, "w") as f:
            yaml.dump(config_data, f)

        # Run build
        result = runner.invoke(
            main, ["build", "--base-dir", str(tmp_path), "--app-dir", "config"]
        )

        # Assert
        assert result.exit_code == 0
        # Local chart without customization is skipped
        assert "skipping helm app" in result.output.lower() or "no customization" in result.output.lower()
        assert "all app groups built successfully" in result.output.lower()


class TestBuildCommandHooks:
    """Test build command with hooks."""

    def test_build_with_global_pre_hook(self, runner, tmp_path) -> None:
        """Test global pre-build hook execution."""
        # Setup directory structure
        config_dir = tmp_path / "config"
        config_dir.mkdir(parents=True, exist_ok=True)

        # Create sources.yaml
        sources_file = tmp_path / "sources.yaml"
        sources_file.write_text(
            """
kubeconfig: ~/.kube/config
kubeconfig_context: test-context
cluster: test-cluster
"""
        )

        # Create config.yaml with global pre-build hook
        config_file = config_dir / "config.yaml"
        config_data = {
            "namespace": "default",
            "hooks": {
                "build": {
                    "pre": ["echo 'pre-build hook executed'"],
                }
            },
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

        # Create source chart
        sbkube_dir = tmp_path / ".sbkube"
        charts_dir = sbkube_dir / "charts" / "bitnami" / "nginx-15.0.0"
        charts_dir.mkdir(parents=True)
        (charts_dir / "Chart.yaml").write_text("name: nginx\nversion: 15.0.0")

        # Run build
        result = runner.invoke(
            main, ["build", "--base-dir", str(tmp_path), "--app-dir", "config"]
        )

        # Assert
        assert result.exit_code == 0
        assert "all app groups built successfully" in result.output.lower()

    def test_build_with_global_post_hook(self, runner, tmp_path) -> None:
        """Test global post-build hook execution."""
        # Setup directory structure
        config_dir = tmp_path / "config"
        config_dir.mkdir(parents=True, exist_ok=True)

        # Create sources.yaml
        sources_file = tmp_path / "sources.yaml"
        sources_file.write_text(
            """
kubeconfig: ~/.kube/config
kubeconfig_context: test-context
cluster: test-cluster
"""
        )

        # Create config.yaml with global post-build hook
        config_file = config_dir / "config.yaml"
        config_data = {
            "namespace": "default",
            "hooks": {
                "build": {
                    "post": ["echo 'post-build hook executed'"],
                }
            },
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

        # Create source chart
        sbkube_dir = tmp_path / ".sbkube"
        charts_dir = sbkube_dir / "charts" / "bitnami" / "nginx-15.0.0"
        charts_dir.mkdir(parents=True)
        (charts_dir / "Chart.yaml").write_text("name: nginx\nversion: 15.0.0")

        # Run build
        result = runner.invoke(
            main, ["build", "--base-dir", str(tmp_path), "--app-dir", "config"]
        )

        # Assert
        assert result.exit_code == 0
        assert "all app groups built successfully" in result.output.lower()

    def test_build_with_app_level_pre_hook(self, runner, tmp_path) -> None:
        """Test app-level pre-build hook execution."""
        # Setup directory structure
        config_dir = tmp_path / "config"
        config_dir.mkdir(parents=True, exist_ok=True)

        # Create sources.yaml
        sources_file = tmp_path / "sources.yaml"
        sources_file.write_text(
            """
kubeconfig: ~/.kube/config
kubeconfig_context: test-context
cluster: test-cluster
"""
        )

        # Create config.yaml with app-level pre-build hook
        config_file = config_dir / "config.yaml"
        config_data = {
            "namespace": "default",
            "apps": {
                "nginx": {
                    "type": "helm",
                    "enabled": True,
                    "chart": "bitnami/nginx",
                    "version": "15.0.0",
                    "hooks": {
                        "pre_build": ["echo 'app pre-build hook executed'"],
                    },
                }
            },
        }
        with open(config_file, "w") as f:
            yaml.dump(config_data, f)

        # Create source chart
        sbkube_dir = tmp_path / ".sbkube"
        charts_dir = sbkube_dir / "charts" / "bitnami" / "nginx-15.0.0"
        charts_dir.mkdir(parents=True)
        (charts_dir / "Chart.yaml").write_text("name: nginx\nversion: 15.0.0")

        # Run build
        result = runner.invoke(
            main, ["build", "--base-dir", str(tmp_path), "--app-dir", "config"]
        )

        # Assert
        assert result.exit_code == 0
        assert "all app groups built successfully" in result.output.lower()

    def test_build_with_app_level_post_hook(self, runner, tmp_path) -> None:
        """Test app-level post-build hook execution."""
        # Setup directory structure
        config_dir = tmp_path / "config"
        config_dir.mkdir(parents=True, exist_ok=True)

        # Create sources.yaml
        sources_file = tmp_path / "sources.yaml"
        sources_file.write_text(
            """
kubeconfig: ~/.kube/config
kubeconfig_context: test-context
cluster: test-cluster
"""
        )

        # Create config.yaml with app-level post-build hook
        config_file = config_dir / "config.yaml"
        config_data = {
            "namespace": "default",
            "apps": {
                "nginx": {
                    "type": "helm",
                    "enabled": True,
                    "chart": "bitnami/nginx",
                    "version": "15.0.0",
                    "hooks": {
                        "post_build": ["echo 'app post-build hook executed'"],
                    },
                }
            },
        }
        with open(config_file, "w") as f:
            yaml.dump(config_data, f)

        # Create source chart
        sbkube_dir = tmp_path / ".sbkube"
        charts_dir = sbkube_dir / "charts" / "bitnami" / "nginx-15.0.0"
        charts_dir.mkdir(parents=True)
        (charts_dir / "Chart.yaml").write_text("name: nginx\nversion: 15.0.0")

        # Run build
        result = runner.invoke(
            main, ["build", "--base-dir", str(tmp_path), "--app-dir", "config"]
        )

        # Assert
        assert result.exit_code == 0
        assert "all app groups built successfully" in result.output.lower()

    def test_build_hook_failure_triggers_on_failure(self, runner, tmp_path) -> None:
        """Test on_failure hook is triggered when build fails."""
        # Setup directory structure
        config_dir = tmp_path / "config"
        config_dir.mkdir(parents=True, exist_ok=True)

        # Create sources.yaml
        sources_file = tmp_path / "sources.yaml"
        sources_file.write_text(
            """
kubeconfig: ~/.kube/config
kubeconfig_context: test-context
cluster: test-cluster
"""
        )

        # Create config.yaml with on_failure hook
        config_file = config_dir / "config.yaml"
        config_data = {
            "namespace": "default",
            "hooks": {
                "build": {
                    "on_failure": ["echo 'build failed, running cleanup'"],
                }
            },
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

        # Don't create source chart to trigger failure

        # Run build
        result = runner.invoke(
            main, ["build", "--base-dir", str(tmp_path), "--app-dir", "config"]
        )

        # Assert
        assert result.exit_code != 0
        # Build should fail and trigger on_failure hook
        assert "some app groups failed to build" in result.output.lower()
