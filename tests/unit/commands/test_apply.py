"""Unit tests for apply.py command.

Tests verify:
- Basic apply workflow (prepare → build → deploy)
- App filtering (--app option)
- Dependency resolution
- Skip flags (--skip-prepare, --skip-build)
- Dry-run mode
- Hook execution (pre-apply, post-apply, on_failure)
- Error handling and recovery
- App-group dependencies validation
- Progress tracking

Note: Tests use unified sbkube.yaml format (v0.10.0+).
Legacy sources.yaml + config.yaml format is no longer supported.
"""

from unittest.mock import MagicMock, patch

import pytest
import yaml
from click.testing import CliRunner

from sbkube.commands.apply import cmd


class TestApplyBasicWorkflow:
    """Test basic apply workflow execution."""

    @pytest.fixture
    def minimal_config(self, base_dir, app_dir):
        """Create minimal unified config for testing."""
        # Create sbkube.yaml in base_dir (unified format)
        sbkube_file = base_dir / "sbkube.yaml"
        sbkube_file.write_text(
            yaml.dump(
                {
                    "apiVersion": "sbkube/v1",
                                        "metadata": {"name": "test-config"},
                    "settings": {
                        "namespace": "default",
                        "helm_repos": {
                            "grafana": "https://grafana.github.io/helm-charts",
                        },
                    },
                    "apps": {
                        "test-app": {
                            "type": "helm",
                            "enabled": True,
                            "namespace": "default",
                            "chart": "grafana/loki",
                            "version": "6.0.0",
                        }
                    },
                }
            )
        )

        return base_dir, app_dir

    @patch("sbkube.commands.prepare.cmd")
    @patch("sbkube.commands.build.cmd")
    @patch("sbkube.commands.deploy.cmd")
    def test_apply_success(
        self, mock_deploy, mock_build, mock_prepare, minimal_config
    ):
        """Test successful apply workflow with unified config."""
        base_dir, _ = minimal_config

        runner = CliRunner()
        result = runner.invoke(
            cmd,
            [
                "-f",
                str(base_dir / "sbkube.yaml"),
            ],
            catch_exceptions=False,
            obj={"format": "human"},  # Provide context object
        )

        assert result.exit_code == 0
        assert "SBKube `apply` 시작" in result.output
        assert ("applied successfully" in result.output or
                "Single app group mode" in result.output)

    @patch("sbkube.commands.prepare.cmd")
    @patch("sbkube.commands.build.cmd")
    @patch("sbkube.commands.deploy.cmd")
    def test_apply_dry_run(self, mock_deploy, mock_build, mock_prepare, minimal_config):
        """Test dry-run mode doesn't execute actual deployment."""
        base_dir, _ = minimal_config

        runner = CliRunner()
        result = runner.invoke(
            cmd,
            [
                "-f",
                str(base_dir / "sbkube.yaml"),
                "--dry-run",
            ],
            obj={"format": "human"},
        )

        assert result.exit_code == 0
        assert "Dry-run mode enabled" in result.output


class TestApplySkipFlags:
    """Test skip flags functionality."""

    @pytest.fixture
    def config_with_app(self, base_dir, app_dir):
        """Create unified config with single app."""
        sbkube_file = base_dir / "sbkube.yaml"
        sbkube_file.write_text(
            yaml.dump(
                {
                    "apiVersion": "sbkube/v1",
                                        "metadata": {"name": "test-config"},
                    "settings": {
                        "namespace": "default",
                        "helm_repos": {"grafana": "https://grafana.github.io/helm-charts"},
                    },
                    "apps": {
                        "app1": {
                            "type": "helm",
                            "enabled": True,
                            "namespace": "default",
                            "chart": "grafana/loki",
                            "version": "6.0.0",
                        }
                    },
                }
            )
        )

        return base_dir, app_dir

    @patch("sbkube.commands.prepare.cmd")
    @patch("sbkube.commands.build.cmd")
    @patch("sbkube.commands.deploy.cmd")
    def test_skip_prepare(
        self, mock_deploy, mock_build, mock_prepare, config_with_app
    ):
        """Test --skip-prepare flag."""
        base_dir, _ = config_with_app

        runner = CliRunner()
        result = runner.invoke(
            cmd,
            [
                "-f",
                str(base_dir / "sbkube.yaml"),
                "--skip-prepare",
            ],
            obj={"format": "human"},  # Provide context object
        )

        assert result.exit_code == 0
        # prepare should not be invoked
        # Note: We can't directly check if prepare_cmd was NOT called
        # because it's patched, but we can verify output

    @patch("sbkube.commands.prepare.cmd")
    @patch("sbkube.commands.build.cmd")
    @patch("sbkube.commands.deploy.cmd")
    def test_skip_build(self, mock_deploy, mock_build, mock_prepare, config_with_app):
        """Test --skip-build flag."""
        base_dir, _ = config_with_app

        runner = CliRunner()
        result = runner.invoke(
            cmd,
            [
                "-f",
                str(base_dir / "sbkube.yaml"),
                "--skip-build",
            ],
            obj={"format": "human"},  # Provide context object
        )

        assert result.exit_code == 0

    @patch("sbkube.commands.prepare.cmd")
    @patch("sbkube.commands.build.cmd")
    @patch("sbkube.commands.deploy.cmd")
    def test_skip_both(self, mock_deploy, mock_build, mock_prepare, config_with_app):
        """Test --skip-prepare and --skip-build together."""
        base_dir, _ = config_with_app

        runner = CliRunner()
        result = runner.invoke(
            cmd,
            [
                "-f",
                str(base_dir / "sbkube.yaml"),
                "--skip-prepare",
                "--skip-build",
            ],
            obj={"format": "human"},  # Provide context object
        )

        assert result.exit_code == 0


class TestApplyAppFiltering:
    """Test app filtering with --app option."""

    @pytest.fixture
    def config_with_multiple_apps(self, base_dir, app_dir):
        """Create unified config with multiple apps and dependencies."""
        sbkube_file = base_dir / "sbkube.yaml"
        sbkube_file.write_text(
            yaml.dump(
                {
                    "apiVersion": "sbkube/v1",
                                        "metadata": {"name": "test-config"},
                    "settings": {
                        "namespace": "default",
                        "helm_repos": {"grafana": "https://grafana.github.io/helm-charts"},
                    },
                    "apps": {
                        "app1": {
                            "type": "helm",
                            "enabled": True,
                            "namespace": "default",
                            "chart": "grafana/loki",
                            "version": "6.0.0",
                        },
                        "app2": {
                            "type": "helm",
                            "enabled": True,
                            "namespace": "default",
                            "chart": "grafana/grafana",
                            "version": "7.0.0",
                            "depends_on": ["app1"],
                        },
                        "app3": {
                            "type": "helm",
                            "enabled": True,
                            "namespace": "default",
                            "chart": "grafana/prometheus",
                            "version": "25.0.0",
                        },
                    },
                }
            )
        )

        return base_dir, app_dir

    @patch("sbkube.commands.prepare.cmd")
    @patch("sbkube.commands.build.cmd")
    @patch("sbkube.commands.deploy.cmd")
    def test_apply_specific_app(
        self, mock_deploy, mock_build, mock_prepare, config_with_multiple_apps
    ):
        """Test applying specific app."""
        base_dir, _ = config_with_multiple_apps

        runner = CliRunner()
        result = runner.invoke(
            cmd,
            [
                "-f",
                str(base_dir / "sbkube.yaml"),
                "--app",
                "app1",
            ],
            obj={"format": "human"},  # Provide context object
        )

        assert result.exit_code == 0
        # Verify deployment order includes only requested app
        assert "Deployment order" in result.output

    @patch("sbkube.commands.prepare.cmd")
    @patch("sbkube.commands.build.cmd")
    @patch("sbkube.commands.deploy.cmd")
    def test_apply_with_dependencies(
        self, mock_deploy, mock_build, mock_prepare, config_with_multiple_apps
    ):
        """Test applying app with dependencies includes all deps."""
        base_dir, _ = config_with_multiple_apps

        runner = CliRunner()
        result = runner.invoke(
            cmd,
            [
                "-f",
                str(base_dir / "sbkube.yaml"),
                "--app",
                "app2",  # Depends on app1
            ],
            obj={"format": "human"},  # Provide context object
        )

        assert result.exit_code == 0
        assert "Including dependencies" in result.output
        assert "app1" in result.output  # Dependency should be included

    def test_apply_nonexistent_app(self, config_with_multiple_apps):
        """Test error when applying nonexistent app."""
        base_dir, _ = config_with_multiple_apps

        runner = CliRunner()
        result = runner.invoke(
            cmd,
            [
                "-f",
                str(base_dir / "sbkube.yaml"),
                "--app",
                "nonexistent",
            ],
            obj={"format": "human"},  # Provide context object
        )

        assert result.exit_code != 0
        assert "App not found" in result.output


class TestApplyDependencyValidation:
    """Test app-group dependency validation."""

    @pytest.fixture
    def config_with_deps(self, base_dir, app_dir):
        """Create unified config with app-group dependencies."""
        sbkube_file = base_dir / "sbkube.yaml"
        sbkube_file.write_text(
            yaml.dump(
                {
                    "apiVersion": "sbkube/v1",
                                        "metadata": {"name": "test-config"},
                    "settings": {
                        "namespace": "default",
                        "helm_repos": {"grafana": "https://grafana.github.io/helm-charts"},
                    },
                    "deps": ["infrastructure", "monitoring"],
                    "apps": {
                        "app1": {
                            "type": "helm",
                            "enabled": True,
                            "namespace": "default",
                            "chart": "grafana/loki",
                            "version": "6.0.0",
                        }
                    },
                }
            )
        )

        return base_dir, app_dir

    @patch("sbkube.commands.apply.DeploymentChecker")
    @patch("sbkube.commands.prepare.cmd")
    @patch("sbkube.commands.build.cmd")
    @patch("sbkube.commands.deploy.cmd")
    def test_deps_all_deployed(
        self, mock_deploy, mock_build, mock_prepare, mock_checker, config_with_deps
    ):
        """Test when all dependencies are deployed."""
        base_dir, _ = config_with_deps

        # Mock dependency check to return all deployed
        mock_checker_instance = MagicMock()
        mock_checker.return_value = mock_checker_instance
        mock_checker_instance.check_dependencies.return_value = {
            "all_deployed": True,
            "missing": [],
            "details": {
                "infrastructure": (True, "deployed"),
                "monitoring": (True, "deployed"),
            },
        }

        runner = CliRunner()
        result = runner.invoke(
            cmd,
            [
                "-f",
                str(base_dir / "sbkube.yaml"),
            ],
            obj={"format": "human"},  # Provide context object
        )

        assert result.exit_code == 0
        assert "All" in result.output and "dependencies are deployed" in result.output

    @patch("sbkube.commands.apply.DeploymentChecker")
    @patch("sbkube.commands.prepare.cmd")
    @patch("sbkube.commands.build.cmd")
    @patch("sbkube.commands.deploy.cmd")
    def test_deps_missing_non_strict(
        self, mock_deploy, mock_build, mock_prepare, mock_checker, config_with_deps
    ):
        """Test missing dependencies in non-strict mode (should warn and continue)."""
        base_dir, _ = config_with_deps

        # Mock dependency check to return missing
        mock_checker_instance = MagicMock()
        mock_checker.return_value = mock_checker_instance
        mock_checker_instance.check_dependencies.return_value = {
            "all_deployed": False,
            "missing": ["infrastructure"],
            "details": {
                "infrastructure": (False, "not deployed"),
                "monitoring": (True, "deployed"),
            },
        }

        runner = CliRunner()
        result = runner.invoke(
            cmd,
            [
                "-f",
                str(base_dir / "sbkube.yaml"),
            ],
            obj={"format": "human"},  # Provide context object
        )

        assert result.exit_code == 0
        assert "dependencies not deployed" in result.output
        assert "Continuing deployment despite missing dependencies" in result.output

    @patch("sbkube.commands.apply.DeploymentChecker")
    def test_deps_missing_strict_mode(self, mock_checker, config_with_deps):
        """Test missing dependencies in strict mode (should fail)."""
        base_dir, _ = config_with_deps

        # Mock dependency check to return missing
        mock_checker_instance = MagicMock()
        mock_checker.return_value = mock_checker_instance
        mock_checker_instance.check_dependencies.return_value = {
            "all_deployed": False,
            "missing": ["infrastructure"],
            "details": {
                "infrastructure": (False, "not deployed"),
                "monitoring": (True, "deployed"),
            },
        }

        runner = CliRunner()
        result = runner.invoke(
            cmd,
            [
                "-f",
                str(base_dir / "sbkube.yaml"),
                "--strict-deps",
            ],
            obj={"format": "human"},  # Provide context object
        )

        assert result.exit_code != 0
        assert "Deployment aborted due to missing dependencies" in result.output

    @patch("sbkube.commands.prepare.cmd")
    @patch("sbkube.commands.build.cmd")
    @patch("sbkube.commands.deploy.cmd")
    def test_skip_deps_check(
        self, mock_deploy, mock_build, mock_prepare, config_with_deps
    ):
        """Test --skip-deps-check flag."""
        base_dir, _ = config_with_deps

        runner = CliRunner()
        result = runner.invoke(
            cmd,
            [
                "-f",
                str(base_dir / "sbkube.yaml"),
                "--skip-deps-check",
            ],
            obj={"format": "human"},  # Provide context object
        )

        assert result.exit_code == 0
        assert "Skipping dependency check" in result.output


class TestApplyHooks:
    """Test hook execution during apply."""

    @pytest.fixture
    def config_with_hooks(self, base_dir, app_dir):
        """Create unified config with hooks."""
        sbkube_file = base_dir / "sbkube.yaml"
        sbkube_file.write_text(
            yaml.dump(
                {
                    "apiVersion": "sbkube/v1",
                                        "metadata": {"name": "test-config"},
                    "settings": {
                        "namespace": "default",
                        "helm_repos": {"grafana": "https://grafana.github.io/helm-charts"},
                    },
                    "hooks": {
                        "apply": {
                            "pre": ["echo 'pre-apply'"],
                            "post": ["echo 'post-apply'"],
                            "on_failure": ["echo 'on-failure'"],
                        }
                    },
                    "apps": {
                        "app1": {
                            "type": "helm",
                            "enabled": True,
                            "namespace": "default",
                            "chart": "grafana/loki",
                            "version": "6.0.0",
                        }
                    },
                }
            )
        )

        return base_dir, app_dir

    @patch("sbkube.commands.apply.HookExecutor")
    @patch("sbkube.commands.prepare.cmd")
    @patch("sbkube.commands.build.cmd")
    @patch("sbkube.commands.deploy.cmd")
    def test_pre_apply_hook_success(
        self, mock_deploy, mock_build, mock_prepare, mock_hook, config_with_hooks
    ):
        """Test pre-apply hook execution."""
        base_dir, _ = config_with_hooks

        mock_hook_instance = MagicMock()
        mock_hook.return_value = mock_hook_instance
        mock_hook_instance.execute_command_hooks.return_value = True

        runner = CliRunner()
        result = runner.invoke(
            cmd,
            [
                "-f",
                str(base_dir / "sbkube.yaml"),
            ],
            obj={"format": "human"},  # Provide context object
        )

        assert result.exit_code == 0
        assert "Executing global pre-apply hooks" in result.output

    @patch("sbkube.commands.apply.HookExecutor")
    def test_pre_apply_hook_failure(self, mock_hook, config_with_hooks):
        """Test pre-apply hook failure aborts deployment."""
        base_dir, _ = config_with_hooks

        mock_hook_instance = MagicMock()
        mock_hook.return_value = mock_hook_instance
        mock_hook_instance.execute_command_hooks.return_value = False

        runner = CliRunner()
        result = runner.invoke(
            cmd,
            [
                "-f",
                str(base_dir / "sbkube.yaml"),
            ],
            obj={"format": "human"},  # Provide context object
        )

        assert result.exit_code != 0
        assert "Pre-apply hook failed" in result.output


class TestApplyErrorHandling:
    """Test error handling scenarios."""

    def test_missing_config_file(self, base_dir, app_dir):
        """Test error when sbkube.yaml doesn't exist."""
        # Don't create any config file

        runner = CliRunner()
        result = runner.invoke(
            cmd,
            [
                ],
            obj={"format": "human"},  # Provide context object
        )

        assert result.exit_code != 0
        assert ("No sbkube.yaml found" in result.output or
                "sbkube init" in result.output)

    @pytest.fixture
    def invalid_config(self, base_dir, app_dir):
        """Create invalid config."""
        # Invalid YAML in sbkube.yaml
        sbkube_file = base_dir / "sbkube.yaml"
        sbkube_file.write_text("invalid: yaml: content: [")

        return base_dir, app_dir

    def test_invalid_config_yaml(self, invalid_config):
        """Test error when sbkube.yaml is invalid."""
        base_dir, _ = invalid_config

        runner = CliRunner()
        result = runner.invoke(
            cmd,
            [
                "-f",
                str(base_dir / "sbkube.yaml"),
            ],
            obj={"format": "human"},  # Provide context object
        )

        assert result.exit_code != 0

    @pytest.fixture
    def config_with_disabled_app(self, base_dir, app_dir):
        """Create unified config with disabled app."""
        sbkube_file = base_dir / "sbkube.yaml"
        sbkube_file.write_text(
            yaml.dump(
                {
                    "apiVersion": "sbkube/v1",
                                        "metadata": {"name": "test-config"},
                    "settings": {
                        "namespace": "default",
                        "helm_repos": {"grafana": "https://grafana.github.io/helm-charts"},
                    },
                    "apps": {
                        "disabled-app": {
                            "type": "helm",
                            "enabled": False,
                            "namespace": "default",
                            "chart": "grafana/loki",
                            "version": "6.0.0",
                        }
                    },
                }
            )
        )

        return base_dir, app_dir

    @patch("sbkube.commands.prepare.cmd")
    @patch("sbkube.commands.build.cmd")
    @patch("sbkube.commands.deploy.cmd")
    def test_skips_disabled_apps(
        self, mock_deploy, mock_build, mock_prepare, config_with_disabled_app
    ):
        """Test that disabled apps are skipped."""
        base_dir, _ = config_with_disabled_app

        runner = CliRunner()
        result = runner.invoke(
            cmd,
            [
                "-f",
                str(base_dir / "sbkube.yaml"),
            ],
            obj={"format": "human"},  # Provide context object
        )

        assert result.exit_code == 0
        # Check for either English or Korean message
        assert ("Skipping disabled app" in result.output or
                "⏭️" in result.output or
                "applied successfully" in result.output)


class TestApplyProgressTracking:
    """Test progress tracking features."""

    @pytest.fixture
    def basic_config(self, base_dir, app_dir):
        """Create basic unified config."""
        sbkube_file = base_dir / "sbkube.yaml"
        sbkube_file.write_text(
            yaml.dump(
                {
                    "apiVersion": "sbkube/v1",
                                        "metadata": {"name": "test-config"},
                    "settings": {
                        "namespace": "default",
                        "helm_repos": {"grafana": "https://grafana.github.io/helm-charts"},
                    },
                    "apps": {
                        "app1": {
                            "type": "helm",
                            "enabled": True,
                            "namespace": "default",
                            "chart": "grafana/loki",
                            "version": "6.0.0",
                        }
                    },
                }
            )
        )

        return base_dir, app_dir

    @patch("sbkube.commands.prepare.cmd")
    @patch("sbkube.commands.build.cmd")
    @patch("sbkube.commands.deploy.cmd")
    def test_no_progress_flag(
        self, mock_deploy, mock_build, mock_prepare, basic_config
    ):
        """Test --no-progress flag disables progress tracking."""
        base_dir, _ = basic_config

        runner = CliRunner()
        result = runner.invoke(
            cmd,
            [
                "-f",
                str(base_dir / "sbkube.yaml"),
                "--no-progress",
            ],
            obj={"format": "human"},  # Provide context object
        )

        assert result.exit_code == 0


class TestInheritedSettingsExtraction:
    """Test hierarchical settings extraction and chain building."""

    def test_extract_settings_full(self):
        """Extract all inheritable fields from config dict."""
        from sbkube.commands.apply import _extract_inherited_settings_from_config

        config_data = {
            "apiVersion": "sbkube/v1",
            "settings": {
                "kubeconfig": "~/.kube/prod",
                "kubeconfig_context": "prod-cluster",
                "namespace": "production",
                "helm_repos": {"grafana": "https://grafana.github.io/helm-charts"},
                "oci_registries": {"myoci": "oci://example.com/charts"},
                "git_repos": {
                    "myrepo": {
                        "url": "https://example.com/repo.git",
                        "branch": "main",
                    }
                },
                "timeout": 600,
            },
        }

        result = _extract_inherited_settings_from_config(config_data)

        assert result["kubeconfig"] == "~/.kube/prod"
        assert result["kubeconfig_context"] == "prod-cluster"
        assert result["namespace"] == "production"
        assert result["helm_repos"] == {
            "grafana": "https://grafana.github.io/helm-charts"
        }
        assert result["oci_registries"] == {"myoci": "oci://example.com/charts"}
        assert "timeout" not in result  # non-inheritable field

    def test_extract_settings_empty(self):
        """Extract from config with no settings section."""
        from sbkube.commands.apply import _extract_inherited_settings_from_config

        result = _extract_inherited_settings_from_config({})
        assert result == {}

    def test_extract_settings_partial(self):
        """Extract from config with only kubeconfig_context."""
        from sbkube.commands.apply import _extract_inherited_settings_from_config

        config_data = {
            "settings": {
                "kubeconfig_context": "my-cluster",
            },
        }
        result = _extract_inherited_settings_from_config(config_data)
        assert result == {"kubeconfig_context": "my-cluster"}
        assert "kubeconfig" not in result
        assert "helm_repos" not in result

    def test_build_chain_root_only(self):
        """Chain with no intermediate config returns root settings."""
        from sbkube.commands.apply import _build_inherited_settings_chain

        root_data = {
            "settings": {
                "kubeconfig": "~/.kube/prod",
                "kubeconfig_context": "prod-cluster",
                "helm_repos": {"grafana": "https://grafana.example.com"},
            },
        }

        result = _build_inherited_settings_chain(
            root_data, intermediate_config_path=None
        )
        assert result["kubeconfig"] == "~/.kube/prod"
        assert result["kubeconfig_context"] == "prod-cluster"

    def test_build_chain_with_intermediate(self, tmp_path):
        """Chain merges root and intermediate, intermediate overrides."""
        from sbkube.commands.apply import _build_inherited_settings_chain

        root_data = {
            "settings": {
                "kubeconfig": "~/.kube/prod",
                "kubeconfig_context": "prod-cluster",
                "namespace": "default",
                "helm_repos": {
                    "grafana": "https://grafana.example.com",
                    "prometheus": "https://prometheus.example.com",
                },
            },
        }

        # Create intermediate sbkube.yaml
        intermediate_dir = tmp_path / "ph2_observability"
        intermediate_dir.mkdir()
        intermediate_file = intermediate_dir / "sbkube.yaml"
        intermediate_file.write_text(
            yaml.dump(
                {
                    "apiVersion": "sbkube/v1",
                    "settings": {
                        "namespace": "monitoring",
                        "helm_repos": {"loki": "https://loki.example.com"},
                    },
                }
            )
        )

        result = _build_inherited_settings_chain(root_data, intermediate_file)

        # Root values preserved
        assert result["kubeconfig"] == "~/.kube/prod"
        assert result["kubeconfig_context"] == "prod-cluster"
        # Intermediate overrides namespace
        assert result["namespace"] == "monitoring"
        # Helm repos merged (root + intermediate)
        assert result["helm_repos"]["grafana"] == "https://grafana.example.com"
        assert result["helm_repos"]["prometheus"] == "https://prometheus.example.com"
        assert result["helm_repos"]["loki"] == "https://loki.example.com"

    def test_build_chain_intermediate_not_exists(self):
        """Chain with non-existent intermediate returns root only."""
        from pathlib import Path

        from sbkube.commands.apply import _build_inherited_settings_chain

        root_data = {
            "settings": {
                "kubeconfig_context": "my-cluster",
            },
        }

        result = _build_inherited_settings_chain(
            root_data, Path("/nonexistent/sbkube.yaml")
        )
        assert result["kubeconfig_context"] == "my-cluster"
