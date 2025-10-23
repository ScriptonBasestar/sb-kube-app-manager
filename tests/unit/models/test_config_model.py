"""
SBKube Configuration Model Tests (v3 API)

Tests for all app types and the main SBKubeConfig model.
"""

import pytest

from sbkube.exceptions import ConfigValidationError
from sbkube.models.config_model import (
    ActionApp,
    ExecApp,
    GitApp,
    HelmApp,
    HttpApp,
    KustomizeApp,
    SBKubeConfig,
    YamlApp,
)

# ============================================================================
# HelmApp Tests
# ============================================================================


class TestHelmApp:
    """Tests for HelmApp model."""

    def test_remote_chart_basic(self):
        """Test remote chart with minimal configuration."""
        app = HelmApp(
            type="helm",
            chart="bitnami/redis",
            version="17.13.2",
        )
        assert app.type == "helm"
        assert app.chart == "bitnami/redis"
        assert app.version == "17.13.2"
        assert app.is_remote_chart() is True
        assert app.get_repo_name() == "bitnami"
        assert app.get_chart_name() == "redis"

    def test_remote_chart_with_values(self):
        """Test remote chart with values files."""
        app = HelmApp(
            type="helm",
            chart="bitnami/postgresql",
            version="12.5.0",
            values=["values.yaml", "secrets.yaml"],
        )
        assert app.values == ["values.yaml", "secrets.yaml"]

    def test_remote_chart_with_set_values(self):
        """Test remote chart with --set values."""
        app = HelmApp(
            type="helm",
            chart="bitnami/nginx",
            set_values={"replicaCount": 3, "service.type": "LoadBalancer"},
        )
        assert app.set_values["replicaCount"] == 3
        assert app.set_values["service.type"] == "LoadBalancer"

    def test_local_chart_relative_path(self):
        """Test local chart with relative path."""
        app = HelmApp(
            type="helm",
            chart="./charts/my-app",
        )
        assert app.is_remote_chart() is False
        assert app.get_repo_name() is None
        assert app.get_chart_name() == "my-app"

    def test_local_chart_absolute_path(self):
        """Test local chart with absolute path."""
        app = HelmApp(
            type="helm",
            chart="/opt/charts/backend",
        )
        assert app.is_remote_chart() is False
        assert app.get_chart_name() == "backend"

    def test_helm_app_with_overrides(self):
        """Test HelmApp with overrides and removes (backward compatibility)."""
        app = HelmApp(
            type="helm",
            chart="bitnami/redis",
            overrides=["configmap.yaml", "secret.yaml"],
            removes=["tests/*", "docs/*"],
        )
        assert app.overrides == ["configmap.yaml", "secret.yaml"]
        assert app.removes == ["tests/*", "docs/*"]

    def test_helm_app_with_namespace_override(self):
        """Test HelmApp with namespace override."""
        app = HelmApp(
            type="helm",
            chart="bitnami/redis",
            namespace="custom-namespace",
        )
        assert app.namespace == "custom-namespace"

    def test_helm_app_with_labels_and_annotations(self):
        """Test HelmApp with labels and annotations."""
        app = HelmApp(
            type="helm",
            chart="bitnami/redis",
            labels={"app": "redis", "env": "prod"},
            annotations={"version": "1.0.0"},
        )
        assert app.labels == {"app": "redis", "env": "prod"}
        assert app.annotations == {"version": "1.0.0"}

    def test_helm_app_with_dependencies(self):
        """Test HelmApp with dependencies."""
        app = HelmApp(
            type="helm",
            chart="my-org/backend",
            depends_on=["redis", "postgresql"],
        )
        assert app.depends_on == ["redis", "postgresql"]

    def test_helm_app_enabled_flag(self):
        """Test HelmApp enabled flag."""
        app_enabled = HelmApp(type="helm", chart="bitnami/redis", enabled=True)
        app_disabled = HelmApp(type="helm", chart="bitnami/redis", enabled=False)
        assert app_enabled.enabled is True
        assert app_disabled.enabled is False

    def test_helm_app_empty_chart_validation(self):
        """Test that empty chart raises validation error."""
        with pytest.raises(ConfigValidationError) as exc_info:
            HelmApp(type="helm", chart="")
        assert "chart cannot be empty" in str(exc_info.value)

    def test_helm_app_whitespace_chart_validation(self):
        """Test that whitespace-only chart raises validation error."""
        with pytest.raises(ConfigValidationError) as exc_info:
            HelmApp(type="helm", chart="   ")
        assert "chart cannot be empty" in str(exc_info.value)


# ============================================================================
# YamlApp Tests
# ============================================================================


class TestYamlApp:
    """Tests for YamlApp model."""

    def test_yaml_app_basic(self):
        """Test YamlApp with minimal configuration."""
        app = YamlApp(
            type="yaml",
            files=["deployment.yaml", "service.yaml"],
        )
        assert app.type == "yaml"
        assert app.files == ["deployment.yaml", "service.yaml"]

    def test_yaml_app_with_namespace(self):
        """Test YamlApp with custom namespace."""
        app = YamlApp(
            type="yaml",
            files=["manifest.yaml"],
            namespace="custom-ns",
        )
        assert app.namespace == "custom-ns"

    def test_yaml_app_with_labels(self):
        """Test YamlApp with labels and annotations."""
        app = YamlApp(
            type="yaml",
            files=["manifest.yaml"],
            labels={"app": "frontend"},
            annotations={"owner": "team-a"},
        )
        assert app.labels == {"app": "frontend"}
        assert app.annotations == {"owner": "team-a"}

    def test_yaml_app_with_dependencies(self):
        """Test YamlApp with dependencies."""
        app = YamlApp(
            type="yaml",
            files=["manifest.yaml"],
            depends_on=["backend"],
        )
        assert app.depends_on == ["backend"]

    def test_yaml_app_empty_files_validation(self):
        """Test that empty files list raises validation error."""
        with pytest.raises(ConfigValidationError) as exc_info:
            YamlApp(type="yaml", files=[])
        assert "files cannot be empty" in str(exc_info.value)


# ============================================================================
# ActionApp Tests
# ============================================================================


class TestActionApp:
    """Tests for ActionApp model."""

    def test_action_app_basic(self):
        """Test ActionApp with minimal configuration."""
        app = ActionApp(
            type="action",
            actions=[
                {"type": "apply", "path": "setup.yaml"},
                {"type": "create", "path": "configmap.yaml"},
            ],
        )
        assert app.type == "action"
        assert len(app.actions) == 2
        assert app.actions[0]["type"] == "apply"

    def test_action_app_with_namespace(self):
        """Test ActionApp with custom namespace."""
        app = ActionApp(
            type="action",
            actions=[{"type": "apply", "path": "manifest.yaml"}],
            namespace="custom-ns",
        )
        assert app.namespace == "custom-ns"

    def test_action_app_with_dependencies(self):
        """Test ActionApp with dependencies."""
        app = ActionApp(
            type="action",
            actions=[{"type": "apply", "path": "post-install.yaml"}],
            depends_on=["database", "cache"],
        )
        assert app.depends_on == ["database", "cache"]

    def test_action_app_empty_actions_validation(self):
        """Test that empty actions list raises validation error."""
        with pytest.raises(ConfigValidationError) as exc_info:
            ActionApp(type="action", actions=[])
        assert "actions cannot be empty" in str(exc_info.value)


# ============================================================================
# ExecApp Tests
# ============================================================================


class TestExecApp:
    """Tests for ExecApp model."""

    def test_exec_app_basic(self):
        """Test ExecApp with minimal configuration."""
        app = ExecApp(
            type="exec",
            commands=["echo 'Deployment completed'", "kubectl get pods"],
        )
        assert app.type == "exec"
        assert len(app.commands) == 2
        assert app.commands[0] == "echo 'Deployment completed'"

    def test_exec_app_with_dependencies(self):
        """Test ExecApp with dependencies."""
        app = ExecApp(
            type="exec",
            commands=["./post-deploy.sh"],
            depends_on=["app1", "app2"],
        )
        assert app.depends_on == ["app1", "app2"]

    def test_exec_app_enabled_flag(self):
        """Test ExecApp enabled flag."""
        app = ExecApp(
            type="exec",
            commands=["echo test"],
            enabled=False,
        )
        assert app.enabled is False

    def test_exec_app_empty_commands_validation(self):
        """Test that empty commands list raises validation error."""
        with pytest.raises(ConfigValidationError) as exc_info:
            ExecApp(type="exec", commands=[])
        assert "commands cannot be empty" in str(exc_info.value)


# ============================================================================
# GitApp Tests
# ============================================================================


class TestGitApp:
    """Tests for GitApp model."""

    def test_git_app_basic(self):
        """Test GitApp with minimal configuration."""
        app = GitApp(
            type="git",
            repo="https://github.com/user/repo",
        )
        assert app.type == "git"
        assert app.repo == "https://github.com/user/repo"
        assert app.branch == "main"  # default

    def test_git_app_with_path_and_branch(self):
        """Test GitApp with path and custom branch."""
        app = GitApp(
            type="git",
            repo="https://github.com/user/repo",
            path="k8s/manifests",
            branch="develop",
        )
        assert app.path == "k8s/manifests"
        assert app.branch == "develop"

    def test_git_app_with_ref(self):
        """Test GitApp with specific ref (commit/tag)."""
        app = GitApp(
            type="git",
            repo="https://github.com/user/repo",
            ref="v1.2.3",
        )
        assert app.ref == "v1.2.3"

    def test_git_app_with_namespace(self):
        """Test GitApp with namespace."""
        app = GitApp(
            type="git",
            repo="https://github.com/user/repo",
            namespace="custom-ns",
        )
        assert app.namespace == "custom-ns"

    def test_git_app_with_dependencies(self):
        """Test GitApp with dependencies."""
        app = GitApp(
            type="git",
            repo="https://github.com/user/repo",
            depends_on=["base-config"],
        )
        assert app.depends_on == ["base-config"]

    def test_git_app_empty_repo_validation(self):
        """Test that empty repo raises validation error."""
        with pytest.raises(ConfigValidationError) as exc_info:
            GitApp(type="git", repo="")
        assert "repo cannot be empty" in str(exc_info.value)


# ============================================================================
# KustomizeApp Tests
# ============================================================================


class TestKustomizeApp:
    """Tests for KustomizeApp model."""

    def test_kustomize_app_basic(self):
        """Test KustomizeApp with minimal configuration."""
        app = KustomizeApp(
            type="kustomize",
            path="overlays/production",
        )
        assert app.type == "kustomize"
        assert app.path == "overlays/production"

    def test_kustomize_app_with_namespace(self):
        """Test KustomizeApp with namespace."""
        app = KustomizeApp(
            type="kustomize",
            path="base",
            namespace="prod",
        )
        assert app.namespace == "prod"

    def test_kustomize_app_with_dependencies(self):
        """Test KustomizeApp with dependencies."""
        app = KustomizeApp(
            type="kustomize",
            path="overlays/staging",
            depends_on=["secrets"],
        )
        assert app.depends_on == ["secrets"]


# ============================================================================
# HttpApp Tests
# ============================================================================


class TestHttpApp:
    """Tests for HttpApp model."""

    def test_http_app_basic(self):
        """Test HttpApp with minimal configuration."""
        app = HttpApp(
            type="http",
            url="https://raw.githubusercontent.com/example/repo/main/manifest.yaml",
            dest="manifests/external.yaml",
        )
        assert app.type == "http"
        assert app.url.startswith("https://")
        assert app.dest == "manifests/external.yaml"

    def test_http_app_with_headers(self):
        """Test HttpApp with custom headers."""
        app = HttpApp(
            type="http",
            url="https://api.example.com/manifest.yaml",
            dest="manifest.yaml",
            headers={"Authorization": "Bearer token123"},
        )
        assert app.headers == {"Authorization": "Bearer token123"}

    def test_http_app_with_dependencies(self):
        """Test HttpApp with dependencies."""
        app = HttpApp(
            type="http",
            url="https://example.com/manifest.yaml",
            dest="manifest.yaml",
            depends_on=["base"],
        )
        assert app.depends_on == ["base"]

    def test_http_app_empty_url_validation(self):
        """Test that empty URL raises validation error."""
        with pytest.raises(ConfigValidationError) as exc_info:
            HttpApp(type="http", url="", dest="manifest.yaml")
        assert "url cannot be empty" in str(exc_info.value)

    def test_http_app_invalid_url_validation(self):
        """Test that non-HTTP URL raises validation error."""
        with pytest.raises(ConfigValidationError) as exc_info:
            HttpApp(type="http", url="ftp://example.com/file.yaml", dest="manifest.yaml")
        assert "url must start with http:// or https://" in str(exc_info.value)


# ============================================================================
# SBKubeConfig Tests
# ============================================================================


class TestSBKubeConfig:
    """Tests for SBKubeConfig main model."""

    def test_sbkube_config_basic(self):
        """Test SBKubeConfig with minimal configuration."""
        config = SBKubeConfig(
            namespace="production",
            apps={
                "redis": HelmApp(type="helm", chart="bitnami/redis", version="17.13.2"),
            },
        )
        assert config.namespace == "production"
        assert "redis" in config.apps
        assert config.apps["redis"].type == "helm"

    def test_sbkube_config_multiple_apps(self):
        """Test SBKubeConfig with multiple apps of different types."""
        config = SBKubeConfig(
            namespace="default",
            apps={
                "redis": HelmApp(type="helm", chart="bitnami/redis"),
                "backend": YamlApp(type="yaml", files=["deployment.yaml"]),
                "init": ExecApp(type="exec", commands=["echo 'Starting'"]),
            },
        )
        assert len(config.apps) == 3
        assert config.apps["redis"].type == "helm"
        assert config.apps["backend"].type == "yaml"
        assert config.apps["init"].type == "exec"

    def test_sbkube_config_namespace_inheritance(self):
        """Test that apps inherit namespace from global config."""
        config = SBKubeConfig(
            namespace="production",
            apps={
                "app1": HelmApp(type="helm", chart="bitnami/redis"),
                "app2": YamlApp(type="yaml", files=["manifest.yaml"]),
            },
        )
        # After validation, namespace should be inherited
        assert config.apps["app1"].namespace == "production"
        assert config.apps["app2"].namespace == "production"

    def test_sbkube_config_namespace_override(self):
        """Test that app-specific namespace overrides global namespace."""
        config = SBKubeConfig(
            namespace="production",
            apps={
                "app1": HelmApp(type="helm", chart="bitnami/redis", namespace="custom-ns"),
            },
        )
        # App-specific namespace should not be overridden
        assert config.apps["app1"].namespace == "custom-ns"

    def test_sbkube_config_global_labels(self):
        """Test SBKubeConfig with global labels and annotations."""
        config = SBKubeConfig(
            namespace="production",
            apps={
                "redis": HelmApp(type="helm", chart="bitnami/redis"),
            },
            global_labels={"env": "prod", "team": "platform"},
            global_annotations={"owner": "devops"},
        )
        assert config.global_labels == {"env": "prod", "team": "platform"}
        assert config.global_annotations == {"owner": "devops"}

    def test_sbkube_config_get_enabled_apps(self):
        """Test get_enabled_apps method."""
        config = SBKubeConfig(
            namespace="default",
            apps={
                "app1": HelmApp(type="helm", chart="bitnami/redis", enabled=True),
                "app2": HelmApp(type="helm", chart="bitnami/nginx", enabled=False),
                "app3": YamlApp(type="yaml", files=["manifest.yaml"], enabled=True),
            },
        )
        enabled_apps = config.get_enabled_apps()
        assert len(enabled_apps) == 2
        assert "app1" in enabled_apps
        assert "app3" in enabled_apps
        assert "app2" not in enabled_apps

    def test_sbkube_config_get_apps_by_type(self):
        """Test get_apps_by_type method."""
        config = SBKubeConfig(
            namespace="default",
            apps={
                "redis": HelmApp(type="helm", chart="bitnami/redis"),
                "nginx": HelmApp(type="helm", chart="bitnami/nginx"),
                "backend": YamlApp(type="yaml", files=["deployment.yaml"]),
            },
        )
        helm_apps = config.get_apps_by_type("helm")
        assert len(helm_apps) == 2
        assert "redis" in helm_apps
        assert "nginx" in helm_apps

    def test_sbkube_config_deployment_order_simple(self):
        """Test get_deployment_order with simple dependencies."""
        config = SBKubeConfig(
            namespace="default",
            apps={
                "redis": HelmApp(type="helm", chart="bitnami/redis"),
                "backend": HelmApp(type="helm", chart="my-org/backend", depends_on=["redis"]),
            },
        )
        order = config.get_deployment_order()
        assert order.index("redis") < order.index("backend")

    def test_sbkube_config_deployment_order_complex(self):
        """Test get_deployment_order with complex dependency graph."""
        config = SBKubeConfig(
            namespace="default",
            apps={
                "database": HelmApp(type="helm", chart="bitnami/postgresql"),
                "cache": HelmApp(type="helm", chart="bitnami/redis"),
                "backend": HelmApp(
                    type="helm", chart="my-org/backend", depends_on=["database", "cache"]
                ),
                "frontend": HelmApp(type="helm", chart="my-org/frontend", depends_on=["backend"]),
            },
        )
        order = config.get_deployment_order()
        # database and cache must come before backend
        assert order.index("database") < order.index("backend")
        assert order.index("cache") < order.index("backend")
        # backend must come before frontend
        assert order.index("backend") < order.index("frontend")

    def test_sbkube_config_invalid_dependency(self):
        """Test that referencing non-existent dependency raises error."""
        with pytest.raises(ConfigValidationError) as exc_info:
            SBKubeConfig(
                namespace="default",
                apps={
                    "backend": HelmApp(
                        type="helm", chart="my-org/backend", depends_on=["non-existent-app"]
                    ),
                },
            )
        assert "depends on non-existent app" in str(exc_info.value)

    def test_sbkube_config_circular_dependency(self):
        """Test that circular dependencies are detected."""
        with pytest.raises(ConfigValidationError) as exc_info:
            SBKubeConfig(
                namespace="default",
                apps={
                    "app1": HelmApp(type="helm", chart="chart1", depends_on=["app2"]),
                    "app2": HelmApp(type="helm", chart="chart2", depends_on=["app1"]),
                },
            )
        assert "Circular dependency detected" in str(exc_info.value)

    def test_sbkube_config_invalid_app_name(self):
        """Test that invalid Kubernetes app names raise validation error."""
        with pytest.raises(ConfigValidationError):
            SBKubeConfig(
                namespace="default",
                apps={
                    "Invalid_Name": HelmApp(type="helm", chart="bitnami/redis"),
                },
            )
        # Should fail Kubernetes naming validation

    def test_sbkube_config_invalid_namespace(self):
        """Test that invalid Kubernetes namespace raises validation error."""
        with pytest.raises(ConfigValidationError):
            SBKubeConfig(
                namespace="Invalid_Namespace",
                apps={
                    "redis": HelmApp(type="helm", chart="bitnami/redis"),
                },
            )
        # Should fail Kubernetes naming validation
