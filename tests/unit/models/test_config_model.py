"""SBKube Configuration Model Tests (v3 API).

Tests for all app types and the main SBKubeConfig model.
"""

import pytest

from sbkube.exceptions import ConfigValidationError
from sbkube.models.config_model import (
    ActionApp,
    ActionSpec,
    ExecApp,
    GitApp,
    HelmApp,
    HookApp,
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

    def test_remote_chart_basic(self) -> None:
        """Test remote chart with minimal configuration."""
        app = HelmApp(
            type="helm",
            chart="grafana/grafana",
            version="6.50.0",
        )
        assert app.type == "helm"
        assert app.chart == "grafana/grafana"
        assert app.version == "6.50.0"
        assert app.is_remote_chart() is True
        assert app.get_repo_name() == "grafana"
        assert app.get_chart_name() == "grafana"

    def test_remote_chart_with_values(self) -> None:
        """Test remote chart with values files."""
        app = HelmApp(
            type="helm",
            chart="cloudnative-pg/cloudnative-pg",
            version="0.18.0",
            values=["values.yaml", "secrets.yaml"],
        )
        assert app.values == ["values.yaml", "secrets.yaml"]

    def test_remote_chart_with_set_values(self) -> None:
        """Test remote chart with --set values."""
        app = HelmApp(
            type="helm",
            chart="ingress-nginx/ingress-nginx",
            set_values={"replicaCount": 3, "service.type": "LoadBalancer"},
        )
        assert app.set_values["replicaCount"] == 3
        assert app.set_values["service.type"] == "LoadBalancer"

    def test_local_chart_relative_path(self) -> None:
        """Test local chart with relative path."""
        app = HelmApp(
            type="helm",
            chart="./charts/my-app",
        )
        assert app.is_remote_chart() is False
        assert app.get_repo_name() is None
        assert app.get_chart_name() == "my-app"

    def test_local_chart_absolute_path(self) -> None:
        """Test local chart with absolute path."""
        app = HelmApp(
            type="helm",
            chart="/opt/charts/backend",
        )
        assert app.is_remote_chart() is False
        assert app.get_chart_name() == "backend"

    def test_helm_app_with_overrides(self) -> None:
        """Test HelmApp with overrides and removes."""
        app = HelmApp(
            type="helm",
            chart="grafana/grafana",
            overrides=["configmap.yaml", "secret.yaml"],
            removes=["tests/*", "docs/*"],
        )
        assert app.overrides == ["configmap.yaml", "secret.yaml"]
        assert app.removes == ["tests/*", "docs/*"]

    def test_helm_app_with_namespace_override(self) -> None:
        """Test HelmApp with namespace override."""
        app = HelmApp(
            type="helm",
            chart="grafana/grafana",
            namespace="custom-namespace",
        )
        assert app.namespace == "custom-namespace"

    def test_helm_app_with_labels_and_annotations(self) -> None:
        """Test HelmApp with labels and annotations."""
        app = HelmApp(
            type="helm",
            chart="grafana/grafana",
            labels={"app": "grafana", "env": "prod"},
            annotations={"version": "1.0.0"},
        )
        assert app.labels == {"app": "grafana", "env": "prod"}
        assert app.annotations == {"version": "1.0.0"}

    def test_helm_app_with_dependencies(self) -> None:
        """Test HelmApp with dependencies."""
        app = HelmApp(
            type="helm",
            chart="my-org/backend",
            depends_on=["grafana", "cloudnative-pg"],
        )
        assert app.depends_on == ["grafana", "cloudnative-pg"]

    def test_helm_app_enabled_flag(self) -> None:
        """Test HelmApp enabled flag."""
        app_enabled = HelmApp(type="helm", chart="grafana/grafana", enabled=True)
        app_disabled = HelmApp(type="helm", chart="grafana/grafana", enabled=False)
        assert app_enabled.enabled is True
        assert app_disabled.enabled is False

    def test_helm_app_empty_chart_validation(self) -> None:
        """Test that empty chart raises validation error."""
        with pytest.raises(ConfigValidationError) as exc_info:
            HelmApp(type="helm", chart="")
        assert "chart cannot be empty" in str(exc_info.value)

    def test_helm_app_whitespace_chart_validation(self) -> None:
        """Test that whitespace-only chart raises validation error."""
        with pytest.raises(ConfigValidationError) as exc_info:
            HelmApp(type="helm", chart="   ")
        assert "chart cannot be empty" in str(exc_info.value)

    def test_helm_app_oci_protocol_validation(self) -> None:
        """Test that OCI protocol in chart field raises validation error."""
        with pytest.raises(ConfigValidationError) as exc_info:
            HelmApp(
                type="helm", chart="oci://registry-1.docker.io/bitnamicharts/supabase"
            )
        error_message = str(exc_info.value)
        assert "Direct OCI protocol in 'chart' field is not supported" in error_message
        assert "sources.yaml" in error_message
        assert "oci_registries" in error_message

    def test_helm_app_oci_github_registry_validation(self) -> None:
        """Test OCI protocol validation with GitHub Container Registry."""
        with pytest.raises(ConfigValidationError) as exc_info:
            HelmApp(type="helm", chart="oci://ghcr.io/myorg/charts/myapp")
        error_message = str(exc_info.value)
        assert "Direct OCI protocol" in error_message
        assert "sources.yaml" in error_message

    def test_helm_app_oci_truecharts_validation(self) -> None:
        """Test OCI protocol validation with TrueCharts registry."""
        with pytest.raises(ConfigValidationError) as exc_info:
            HelmApp(type="helm", chart="oci://tccr.io/truecharts/browserless-chrome")
        error_message = str(exc_info.value)
        assert "Direct OCI protocol" in error_message
        assert "Example for Docker Hub Bitnami charts" in error_message


# ============================================================================
# YamlApp Tests
# ============================================================================


class TestYamlApp:
    """Tests for YamlApp model."""

    def test_yaml_app_basic(self) -> None:
        """Test YamlApp with minimal configuration."""
        app = YamlApp(
            type="yaml",
            manifests=["deployment.yaml", "service.yaml"],
        )
        assert app.type == "yaml"
        assert app.manifests == ["deployment.yaml", "service.yaml"]

    def test_yaml_app_with_namespace(self) -> None:
        """Test YamlApp with custom namespace."""
        app = YamlApp(
            type="yaml",
            manifests=["manifest.yaml"],
            namespace="custom-ns",
        )
        assert app.namespace == "custom-ns"

    def test_yaml_app_with_labels(self) -> None:
        """Test YamlApp with labels and annotations."""
        app = YamlApp(
            type="yaml",
            manifests=["manifest.yaml"],
            labels={"app": "frontend"},
            annotations={"owner": "team-a"},
        )
        assert app.labels == {"app": "frontend"}
        assert app.annotations == {"owner": "team-a"}

    def test_yaml_app_with_dependencies(self) -> None:
        """Test YamlApp with dependencies."""
        app = YamlApp(
            type="yaml",
            manifests=["manifest.yaml"],
            depends_on=["backend"],
        )
        assert app.depends_on == ["backend"]

    def test_yaml_app_empty_manifests_validation(self) -> None:
        """Test that empty manifests list raises validation error."""
        with pytest.raises(ConfigValidationError) as exc_info:
            YamlApp(type="yaml", manifests=[])
        assert "manifests cannot be empty" in str(exc_info.value)


# ============================================================================
# ActionApp Tests
# ============================================================================


class TestActionSpec:
    """Tests for ActionSpec model."""

    def test_action_spec_apply_basic(self) -> None:
        """Test ActionSpec with apply type."""
        action = ActionSpec(type="apply", path="manifests/deployment.yaml")
        assert action.type == "apply"
        assert action.path == "manifests/deployment.yaml"
        assert action.namespace is None

    def test_action_spec_delete_basic(self) -> None:
        """Test ActionSpec with delete type."""
        action = ActionSpec(type="delete", path="manifests/old-resource.yaml")
        assert action.type == "delete"
        assert action.path == "manifests/old-resource.yaml"

    def test_action_spec_with_namespace(self) -> None:
        """Test ActionSpec with custom namespace."""
        action = ActionSpec(
            type="apply", path="manifests/service.yaml", namespace="custom-ns"
        )
        assert action.namespace == "custom-ns"

    def test_action_spec_default_type(self) -> None:
        """Test ActionSpec defaults to 'apply' type."""
        action = ActionSpec(path="manifests/configmap.yaml")
        assert action.type == "apply"

    def test_action_spec_empty_path_validation(self) -> None:
        """Test that empty path raises validation error."""
        with pytest.raises(ConfigValidationError) as exc_info:
            ActionSpec(type="apply", path="")
        assert "path cannot be empty" in str(exc_info.value).lower()

    def test_action_spec_whitespace_path_validation(self) -> None:
        """Test that whitespace-only path raises validation error."""
        with pytest.raises(ConfigValidationError) as exc_info:
            ActionSpec(type="apply", path="   ")
        assert "path cannot be empty" in str(exc_info.value).lower()

    def test_action_spec_kubectl_command_validation(self) -> None:
        """Test that kubectl command in path raises validation error."""
        with pytest.raises(ConfigValidationError) as exc_info:
            ActionSpec(
                type="apply",
                path="kubectl label node polypia-sheepdog1 topology.kubernetes.io/zone=polypia-sheepdog1",
            )
        assert "should be a file path, not a command" in str(exc_info.value).lower()
        assert "type: exec" in str(exc_info.value).lower()

    def test_action_spec_helm_command_validation(self) -> None:
        """Test that helm command in path raises validation error."""
        with pytest.raises(ConfigValidationError) as exc_info:
            ActionSpec(type="apply", path="helm install myapp charts/myapp")
        assert "should be a file path, not a command" in str(exc_info.value).lower()

    def test_action_spec_path_trimming(self) -> None:
        """Test that path is trimmed of whitespace."""
        action = ActionSpec(type="apply", path="  manifests/deployment.yaml  ")
        assert action.path == "manifests/deployment.yaml"


class TestActionApp:
    """Tests for ActionApp model."""

    def test_action_app_basic(self) -> None:
        """Test ActionApp with minimal configuration."""
        app = ActionApp(
            type="action",
            actions=[
                {"type": "apply", "path": "setup.yaml"},
                {"type": "delete", "path": "configmap.yaml"},
            ],
        )
        assert app.type == "action"
        assert len(app.actions) == 2
        assert app.actions[0].type == "apply"
        assert app.actions[0].path == "setup.yaml"
        assert app.actions[1].type == "delete"

    def test_action_app_with_namespace(self) -> None:
        """Test ActionApp with custom namespace."""
        app = ActionApp(
            type="action",
            actions=[{"type": "apply", "path": "manifest.yaml"}],
            namespace="custom-ns",
        )
        assert app.namespace == "custom-ns"

    def test_action_app_with_dependencies(self) -> None:
        """Test ActionApp with dependencies."""
        app = ActionApp(
            type="action",
            actions=[{"type": "apply", "path": "post-install.yaml"}],
            depends_on=["database", "cache"],
        )
        assert app.depends_on == ["database", "cache"]

    def test_action_app_empty_actions_validation(self) -> None:
        """Test that empty actions list raises validation error."""
        with pytest.raises(ConfigValidationError) as exc_info:
            ActionApp(type="action", actions=[])
        assert "must have at least one action" in str(exc_info.value).lower()

    def test_action_app_action_with_namespace_override(self) -> None:
        """Test ActionApp with action-level namespace override."""
        app = ActionApp(
            type="action",
            actions=[
                {"type": "apply", "path": "app.yaml", "namespace": "app-ns"},
                {"type": "apply", "path": "db.yaml", "namespace": "db-ns"},
            ],
            namespace="default-ns",
        )
        assert app.namespace == "default-ns"
        assert app.actions[0].namespace == "app-ns"
        assert app.actions[1].namespace == "db-ns"

    def test_action_app_invalid_action_missing_path(self) -> None:
        """Test that action without path raises validation error."""
        with pytest.raises(ConfigValidationError) as exc_info:
            ActionApp(
                type="action",
                actions=[{"type": "apply"}],  # Missing 'path'
            )
        assert "path" in str(exc_info.value).lower()

    def test_action_app_invalid_action_wrong_command(self) -> None:
        """Test that action with command instead of path raises validation error."""
        with pytest.raises(ConfigValidationError) as exc_info:
            ActionApp(
                type="action",
                actions=[
                    {
                        "type": "apply",
                        "path": "kubectl label node polypia-sheepdog1 topology.kubernetes.io/zone=polypia-sheepdog1",
                    }
                ],
            )
        assert "should be a file path, not a command" in str(exc_info.value).lower()
        assert "type: exec" in str(exc_info.value).lower()


# ============================================================================
# ExecApp Tests
# ============================================================================


class TestExecApp:
    """Tests for ExecApp model."""

    def test_exec_app_basic(self) -> None:
        """Test ExecApp with minimal configuration."""
        app = ExecApp(
            type="exec",
            commands=["echo 'Deployment completed'", "kubectl get pods"],
        )
        assert app.type == "exec"
        assert len(app.commands) == 2
        assert app.commands[0] == "echo 'Deployment completed'"

    def test_exec_app_with_dependencies(self) -> None:
        """Test ExecApp with dependencies."""
        app = ExecApp(
            type="exec",
            commands=["./post-deploy.sh"],
            depends_on=["app1", "app2"],
        )
        assert app.depends_on == ["app1", "app2"]

    def test_exec_app_enabled_flag(self) -> None:
        """Test ExecApp enabled flag."""
        app = ExecApp(
            type="exec",
            commands=["echo test"],
            enabled=False,
        )
        assert app.enabled is False

    def test_exec_app_empty_commands_validation(self) -> None:
        """Test that empty commands list raises validation error."""
        with pytest.raises(ConfigValidationError) as exc_info:
            ExecApp(type="exec", commands=[])
        assert "commands cannot be empty" in str(exc_info.value)


# ============================================================================
# GitApp Tests
# ============================================================================


class TestGitApp:
    """Tests for GitApp model."""

    def test_git_app_basic(self) -> None:
        """Test GitApp with minimal configuration."""
        app = GitApp(
            type="git",
            repo="https://github.com/user/repo",
        )
        assert app.type == "git"
        assert app.repo == "https://github.com/user/repo"
        assert app.branch == "main"  # default

    def test_git_app_with_path_and_branch(self) -> None:
        """Test GitApp with path and custom branch."""
        app = GitApp(
            type="git",
            repo="https://github.com/user/repo",
            path="k8s/manifests",
            branch="develop",
        )
        assert app.path == "k8s/manifests"
        assert app.branch == "develop"

    def test_git_app_with_ref(self) -> None:
        """Test GitApp with specific ref (commit/tag)."""
        app = GitApp(
            type="git",
            repo="https://github.com/user/repo",
            ref="v1.2.3",
        )
        assert app.ref == "v1.2.3"

    def test_git_app_with_namespace(self) -> None:
        """Test GitApp with namespace."""
        app = GitApp(
            type="git",
            repo="https://github.com/user/repo",
            namespace="custom-ns",
        )
        assert app.namespace == "custom-ns"

    def test_git_app_with_dependencies(self) -> None:
        """Test GitApp with dependencies."""
        app = GitApp(
            type="git",
            repo="https://github.com/user/repo",
            depends_on=["base-config"],
        )
        assert app.depends_on == ["base-config"]

    def test_git_app_empty_repo_validation(self) -> None:
        """Test that empty repo raises validation error."""
        with pytest.raises(ConfigValidationError) as exc_info:
            GitApp(type="git", repo="")
        assert "repo cannot be empty" in str(exc_info.value)


# ============================================================================
# KustomizeApp Tests
# ============================================================================


class TestKustomizeApp:
    """Tests for KustomizeApp model."""

    def test_kustomize_app_basic(self) -> None:
        """Test KustomizeApp with minimal configuration."""
        app = KustomizeApp(
            type="kustomize",
            path="overlays/production",
        )
        assert app.type == "kustomize"
        assert app.path == "overlays/production"

    def test_kustomize_app_with_namespace(self) -> None:
        """Test KustomizeApp with namespace."""
        app = KustomizeApp(
            type="kustomize",
            path="base",
            namespace="prod",
        )
        assert app.namespace == "prod"

    def test_kustomize_app_with_dependencies(self) -> None:
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

    def test_http_app_basic(self) -> None:
        """Test HttpApp with minimal configuration."""
        app = HttpApp(
            type="http",
            url="https://raw.githubusercontent.com/example/repo/main/manifest.yaml",
            dest="manifests/external.yaml",
        )
        assert app.type == "http"
        assert app.url.startswith("https://")
        assert app.dest == "manifests/external.yaml"

    def test_http_app_with_headers(self) -> None:
        """Test HttpApp with custom headers."""
        app = HttpApp(
            type="http",
            url="https://api.example.com/manifest.yaml",
            dest="manifest.yaml",
            headers={"Authorization": "Bearer token123"},
        )
        assert app.headers == {"Authorization": "Bearer token123"}

    def test_http_app_with_dependencies(self) -> None:
        """Test HttpApp with dependencies."""
        app = HttpApp(
            type="http",
            url="https://example.com/manifest.yaml",
            dest="manifest.yaml",
            depends_on=["base"],
        )
        assert app.depends_on == ["base"]

    def test_http_app_empty_url_validation(self) -> None:
        """Test that empty URL raises validation error."""
        with pytest.raises(ConfigValidationError) as exc_info:
            HttpApp(type="http", url="", dest="manifest.yaml")
        assert "url cannot be empty" in str(exc_info.value)

    def test_http_app_invalid_url_validation(self) -> None:
        """Test that non-HTTP URL raises validation error."""
        with pytest.raises(ConfigValidationError) as exc_info:
            HttpApp(
                type="http", url="ftp://example.com/file.yaml", dest="manifest.yaml"
            )
        assert "url must start with http:// or https://" in str(exc_info.value)


# ============================================================================
# HookApp Tests (Phase 4)
# ============================================================================


class TestHookApp:
    """Tests for HookApp model (Phase 4: Hook as First-class App)."""

    def test_hook_app_basic(self) -> None:
        """Test HookApp with minimal configuration."""
        app = HookApp(
            type="hook",
            tasks=[
                {
                    "type": "command",
                    "name": "verify-deployment",
                    "command": "kubectl get pods",
                }
            ],
        )
        assert app.type == "hook"
        assert len(app.tasks) == 1
        assert app.tasks[0].type == "command"
        assert app.tasks[0].name == "verify-deployment"

    def test_hook_app_with_multiple_tasks(self) -> None:
        """Test HookApp with multiple tasks."""
        app = HookApp(
            type="hook",
            tasks=[
                {
                    "type": "manifests",
                    "name": "deploy-config",
                    "files": ["manifests/config.yaml"],
                },
                {
                    "type": "inline",
                    "name": "create-secret",
                    "content": {"apiVersion": "v1", "kind": "Secret"},
                },
                {
                    "type": "command",
                    "name": "verify",
                    "command": "kubectl get pods",
                },
            ],
        )
        assert len(app.tasks) == 3
        assert app.tasks[0].type == "manifests"
        assert app.tasks[1].type == "inline"
        assert app.tasks[2].type == "command"

    def test_hook_app_with_namespace(self) -> None:
        """Test HookApp with custom namespace."""
        app = HookApp(
            type="hook",
            tasks=[{"type": "command", "name": "test", "command": "echo test"}],
            namespace="custom-ns",
        )
        assert app.namespace == "custom-ns"

    def test_hook_app_with_dependencies(self) -> None:
        """Test HookApp with dependencies."""
        app = HookApp(
            type="hook",
            tasks=[{"type": "command", "name": "test", "command": "echo test"}],
            depends_on=["cert-manager", "database"],
        )
        assert app.depends_on == ["cert-manager", "database"]

    def test_hook_app_with_validation(self) -> None:
        """Test HookApp with validation rules."""
        app = HookApp(
            type="hook",
            tasks=[
                {
                    "type": "manifests",
                    "name": "deploy-config",
                    "files": ["config.yaml"],
                }
            ],
            validation={
                "kind": "ConfigMap",
                "wait_for_ready": True,
                "timeout": 120,
            },
        )
        assert app.validation is not None
        assert app.validation["kind"] == "ConfigMap"
        assert app.validation["wait_for_ready"] is True

    def test_hook_app_with_dependency_config(self) -> None:
        """Test HookApp with dependency configuration."""
        app = HookApp(
            type="hook",
            tasks=[{"type": "command", "name": "test", "command": "echo test"}],
            dependency={
                "depends_on": ["app1"],
                "wait_for": [
                    {
                        "kind": "Deployment",
                        "namespace": "default",
                        "label_selector": "app=myapp",
                    }
                ],
            },
        )
        assert app.dependency is not None
        assert app.dependency["depends_on"] == ["app1"]
        assert len(app.dependency["wait_for"]) == 1

    def test_hook_app_with_rollback_policy(self) -> None:
        """Test HookApp with rollback policy."""
        app = HookApp(
            type="hook",
            tasks=[{"type": "command", "name": "test", "command": "echo test"}],
            rollback={
                "enabled": True,
                "on_failure": "always",
                "commands": ["kubectl delete configmap test"],
            },
        )
        assert app.rollback is not None
        assert app.rollback["enabled"] is True
        assert app.rollback["on_failure"] == "always"

    def test_hook_app_enabled_flag(self) -> None:
        """Test HookApp enabled flag."""
        app_enabled = HookApp(
            type="hook",
            tasks=[{"type": "command", "name": "test", "command": "echo test"}],
            enabled=True,
        )
        app_disabled = HookApp(
            type="hook",
            tasks=[{"type": "command", "name": "test", "command": "echo test"}],
            enabled=False,
        )
        assert app_enabled.enabled is True
        assert app_disabled.enabled is False

    def test_hook_app_empty_tasks_allowed(self) -> None:
        """Test HookApp with empty tasks (should be allowed, but warned in deploy)."""
        app = HookApp(type="hook", tasks=[])
        assert app.type == "hook"
        assert len(app.tasks) == 0

    def test_hook_app_no_hooks_field(self) -> None:
        """Test that HookApp does not have hooks field (prevent recursion)."""
        app = HookApp(
            type="hook",
            tasks=[{"type": "command", "name": "test", "command": "echo test"}],
        )
        # HookApp should not have a 'hooks' attribute
        assert not hasattr(app, "hooks")

    def test_hook_app_with_labels_and_annotations(self) -> None:
        """Test HookApp with labels and annotations."""
        app = HookApp(
            type="hook",
            tasks=[{"type": "command", "name": "test", "command": "echo test"}],
            labels={"app": "hook-app", "env": "prod"},
            annotations={"version": "1.0.0", "owner": "team-platform"},
        )
        assert app.labels == {"app": "hook-app", "env": "prod"}
        assert app.annotations == {"version": "1.0.0", "owner": "team-platform"}

    def test_hook_app_with_all_phase3_features(self) -> None:
        """Test HookApp with all Phase 3 features combined."""
        app = HookApp(
            type="hook",
            tasks=[
                {
                    "type": "manifests",
                    "name": "deploy-config",
                    "files": ["config.yaml"],
                }
            ],
            namespace="test-ns",
            depends_on=["database"],
            validation={
                "kind": "ConfigMap",
                "wait_for_ready": True,
                "timeout": 60,
            },
            dependency={
                "depends_on": ["database"],
                "wait_for": [{"kind": "Pod", "namespace": "test-ns"}],
            },
            rollback={
                "enabled": True,
                "on_failure": "always",
                "commands": ["kubectl delete configmap test"],
            },
            labels={"app": "hook-app"},
            annotations={"version": "1.0.0"},
            enabled=True,
        )
        assert app.type == "hook"
        assert app.namespace == "test-ns"
        assert app.depends_on == ["database"]
        assert app.validation is not None
        assert app.dependency is not None
        assert app.rollback is not None
        assert app.labels == {"app": "hook-app"}
        assert app.annotations == {"version": "1.0.0"}
        assert app.enabled is True


# ============================================================================
# SBKubeConfig Tests
# ============================================================================


class TestSBKubeConfig:
    """Tests for SBKubeConfig main model."""

    def test_sbkube_config_basic(self) -> None:
        """Test SBKubeConfig with minimal configuration."""
        config = SBKubeConfig(
            namespace="production",
            apps={
                "grafana": HelmApp(
                    type="helm", chart="grafana/grafana", version="6.50.0"
                ),
            },
        )
        assert config.namespace == "production"
        assert "grafana" in config.apps
        assert config.apps["grafana"].type == "helm"

    def test_sbkube_config_multiple_apps(self) -> None:
        """Test SBKubeConfig with multiple apps of different types."""
        config = SBKubeConfig(
            namespace="default",
            apps={
                "grafana": HelmApp(type="helm", chart="grafana/grafana"),
                "backend": YamlApp(type="yaml", manifests=["deployment.yaml"]),
                "init": ExecApp(type="exec", commands=["echo 'Starting'"]),
            },
        )
        assert len(config.apps) == 3
        assert config.apps["grafana"].type == "helm"
        assert config.apps["backend"].type == "yaml"
        assert config.apps["init"].type == "exec"

    def test_sbkube_config_namespace_inheritance(self) -> None:
        """Test that apps inherit namespace from global config."""
        config = SBKubeConfig(
            namespace="production",
            apps={
                "app1": HelmApp(type="helm", chart="grafana/grafana"),
                "app2": YamlApp(type="yaml", manifests=["manifest.yaml"]),
            },
        )
        # After validation, namespace should be inherited
        assert config.apps["app1"].namespace == "production"
        assert config.apps["app2"].namespace == "production"

    def test_sbkube_config_namespace_override(self) -> None:
        """Test that app-specific namespace overrides global namespace."""
        config = SBKubeConfig(
            namespace="production",
            apps={
                "app1": HelmApp(
                    type="helm", chart="grafana/grafana", namespace="custom-ns"
                ),
            },
        )
        # App-specific namespace should not be overridden
        assert config.apps["app1"].namespace == "custom-ns"

    def test_sbkube_config_global_labels(self) -> None:
        """Test SBKubeConfig with global labels and annotations."""
        config = SBKubeConfig(
            namespace="production",
            apps={
                "grafana": HelmApp(type="helm", chart="grafana/grafana"),
            },
            global_labels={"env": "prod", "team": "platform"},
            global_annotations={"owner": "devops"},
        )
        assert config.global_labels == {"env": "prod", "team": "platform"}
        assert config.global_annotations == {"owner": "devops"}

    def test_sbkube_config_get_enabled_apps(self) -> None:
        """Test get_enabled_apps method."""
        config = SBKubeConfig(
            namespace="default",
            apps={
                "app1": HelmApp(type="helm", chart="grafana/grafana", enabled=True),
                "app2": HelmApp(
                    type="helm", chart="ingress-nginx/ingress-nginx", enabled=False
                ),
                "app3": YamlApp(type="yaml", manifests=["manifest.yaml"], enabled=True),
            },
        )
        enabled_apps = config.get_enabled_apps()
        assert len(enabled_apps) == 2
        assert "app1" in enabled_apps
        assert "app3" in enabled_apps
        assert "app2" not in enabled_apps

    def test_sbkube_config_get_apps_by_type(self) -> None:
        """Test get_apps_by_type method."""
        config = SBKubeConfig(
            namespace="default",
            apps={
                "grafana": HelmApp(type="helm", chart="grafana/grafana"),
                "ingress": HelmApp(type="helm", chart="ingress-nginx/ingress-nginx"),
                "backend": YamlApp(type="yaml", manifests=["deployment.yaml"]),
            },
        )
        helm_apps = config.get_apps_by_type("helm")
        assert len(helm_apps) == 2
        assert "grafana" in helm_apps
        assert "ingress" in helm_apps

    def test_sbkube_config_deployment_order_simple(self) -> None:
        """Test get_deployment_order with simple dependencies."""
        config = SBKubeConfig(
            namespace="default",
            apps={
                "grafana": HelmApp(type="helm", chart="grafana/grafana"),
                "backend": HelmApp(
                    type="helm", chart="my-org/backend", depends_on=["grafana"]
                ),
            },
        )
        order = config.get_deployment_order()
        assert order.index("grafana") < order.index("backend")

    def test_sbkube_config_deployment_order_complex(self) -> None:
        """Test get_deployment_order with complex dependency graph."""
        config = SBKubeConfig(
            namespace="default",
            apps={
                "database": HelmApp(type="helm", chart="cloudnative-pg/cloudnative-pg"),
                "cache": HelmApp(type="helm", chart="grafana/grafana"),
                "backend": HelmApp(
                    type="helm",
                    chart="my-org/backend",
                    depends_on=["database", "cache"],
                ),
                "frontend": HelmApp(
                    type="helm", chart="my-org/frontend", depends_on=["backend"]
                ),
            },
        )
        order = config.get_deployment_order()
        # database and cache must come before backend
        assert order.index("database") < order.index("backend")
        assert order.index("cache") < order.index("backend")
        # backend must come before frontend
        assert order.index("backend") < order.index("frontend")

    def test_sbkube_config_invalid_dependency(self) -> None:
        """Test that referencing non-existent dependency raises error."""
        with pytest.raises(ConfigValidationError) as exc_info:
            SBKubeConfig(
                namespace="default",
                apps={
                    "backend": HelmApp(
                        type="helm",
                        chart="my-org/backend",
                        depends_on=["non-existent-app"],
                    ),
                },
            )
        assert "depends on non-existent app" in str(exc_info.value)

    def test_sbkube_config_circular_dependency(self) -> None:
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

    def test_sbkube_config_invalid_app_name(self) -> None:
        """Test that invalid Kubernetes app names raise validation error."""
        with pytest.raises(ConfigValidationError):
            SBKubeConfig(
                namespace="default",
                apps={
                    "Invalid_Name": HelmApp(type="helm", chart="grafana/grafana"),
                },
            )
        # Should fail Kubernetes naming validation

    def test_sbkube_config_invalid_namespace(self) -> None:
        """Test that invalid Kubernetes namespace raises validation error."""
        with pytest.raises(ConfigValidationError):
            SBKubeConfig(
                namespace="Invalid_Namespace",
                apps={
                    "grafana": HelmApp(type="helm", chart="grafana/grafana"),
                },
            )
        # Should fail Kubernetes naming validation

    def test_sbkube_config_with_hook_app(self) -> None:
        """Test SBKubeConfig with HookApp (Phase 4)."""
        config = SBKubeConfig(
            namespace="default",
            apps={
                "cert-manager": HelmApp(type="helm", chart="jetstack/cert-manager"),
                "post-deploy-hooks": HookApp(
                    type="hook",
                    tasks=[
                        {
                            "type": "command",
                            "name": "verify-deployment",
                            "command": "kubectl get pods",
                        }
                    ],
                    depends_on=["cert-manager"],
                ),
            },
        )
        assert "post-deploy-hooks" in config.apps
        assert config.apps["post-deploy-hooks"].type == "hook"
        assert isinstance(config.apps["post-deploy-hooks"], HookApp)

    def test_sbkube_config_hook_app_deployment_order(self) -> None:
        """Test deployment order with HookApp dependencies."""
        config = SBKubeConfig(
            namespace="default",
            apps={
                "database": HelmApp(type="helm", chart="cloudnative-pg/cloudnative-pg"),
                "verify-db": HookApp(
                    type="hook",
                    tasks=[
                        {
                            "type": "command",
                            "name": "verify",
                            "command": "kubectl get pods -l app=postgres",
                        }
                    ],
                    depends_on=["database"],
                ),
                "backend": HelmApp(
                    type="helm",
                    chart="my-org/backend",
                    depends_on=["verify-db"],
                ),
            },
        )
        order = config.get_deployment_order()
        # database must come before verify-db
        assert order.index("database") < order.index("verify-db")
        # verify-db must come before backend
        assert order.index("verify-db") < order.index("backend")
