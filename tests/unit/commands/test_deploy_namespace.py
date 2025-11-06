"""Unit tests for namespace handling in deployment commands.

Tests verify that all app types (YAML, Action, Kustomize) correctly respect
namespace settings from both config-level and app-level configurations.
"""

from unittest.mock import patch

from sbkube.commands.deploy import (
    deploy_action_app,
    deploy_kustomize_app,
    deploy_yaml_app,
)
from sbkube.models.config_model import ActionApp, KustomizeApp, YamlApp


class TestYamlAppNamespaceHandling:
    """Test namespace handling for YAML-type apps."""

    @patch("sbkube.commands.deploy.run_command")
    def test_uses_config_namespace_when_app_namespace_is_none(
        self, mock_run_command, tmp_path
    ):
        """YAML app should use config.namespace when app.namespace is None."""
        # Arrange
        mock_run_command.return_value = (0, "", "")

        manifest_file = tmp_path / "test-secret.yaml"
        manifest_file.write_text(
            """
apiVersion: v1
kind: Secret
metadata:
  name: test-secret
stringData:
  key: value
"""
        )

        app = YamlApp(
            type="yaml",
            enabled=True,
            manifests=["test-secret.yaml"],
            namespace=None,  # No app-level namespace
        )

        # Act
        result = deploy_yaml_app(
            app_name="test-app",
            app=app,
            base_dir=tmp_path,
            app_config_dir=tmp_path,
            kubeconfig=None,
            context=None,
            dry_run=False,
            apps_config=None,
            sbkube_work_dir=None,
            config_namespace="test-namespace",  # Config-level namespace
        )

        # Assert
        assert result is True
        mock_run_command.assert_called_once()
        cmd = mock_run_command.call_args[0][0]
        assert "--namespace" in cmd
        assert "test-namespace" in cmd

    @patch("sbkube.commands.deploy.run_command")
    def test_uses_app_namespace_when_explicitly_set(self, mock_run_command, tmp_path):
        """YAML app should use app.namespace when explicitly set (overrides config)."""
        # Arrange
        mock_run_command.return_value = (0, "", "")

        manifest_file = tmp_path / "test-secret.yaml"
        manifest_file.write_text(
            """
apiVersion: v1
kind: Secret
metadata:
  name: test-secret
stringData:
  key: value
"""
        )

        app = YamlApp(
            type="yaml",
            enabled=True,
            manifests=["test-secret.yaml"],
            namespace="app-specific-namespace",  # App-level override
        )

        # Act
        result = deploy_yaml_app(
            app_name="test-app",
            app=app,
            base_dir=tmp_path,
            app_config_dir=tmp_path,
            kubeconfig=None,
            context=None,
            dry_run=False,
            apps_config=None,
            sbkube_work_dir=None,
            config_namespace="config-namespace",  # Should be ignored
        )

        # Assert
        assert result is True
        mock_run_command.assert_called_once()
        cmd = mock_run_command.call_args[0][0]
        assert "--namespace" in cmd
        assert "app-specific-namespace" in cmd
        assert "config-namespace" not in cmd

    @patch("sbkube.commands.deploy.run_command")
    def test_no_namespace_flag_when_both_are_none(self, mock_run_command, tmp_path):
        """YAML app should not add --namespace flag when both app and config namespaces are None."""
        # Arrange
        mock_run_command.return_value = (0, "", "")

        manifest_file = tmp_path / "test-secret.yaml"
        manifest_file.write_text(
            """
apiVersion: v1
kind: Secret
metadata:
  name: test-secret
stringData:
  key: value
"""
        )

        app = YamlApp(
            type="yaml", enabled=True, manifests=["test-secret.yaml"], namespace=None
        )

        # Act
        result = deploy_yaml_app(
            app_name="test-app",
            app=app,
            base_dir=tmp_path,
            app_config_dir=tmp_path,
            kubeconfig=None,
            context=None,
            dry_run=False,
            apps_config=None,
            sbkube_work_dir=None,
            config_namespace=None,  # No config namespace either
        )

        # Assert
        assert result is True
        mock_run_command.assert_called_once()
        cmd = mock_run_command.call_args[0][0]
        assert "--namespace" not in cmd


class TestActionAppNamespaceHandling:
    """Test namespace handling for Action-type apps."""

    @patch("sbkube.commands.deploy.run_command")
    def test_uses_config_namespace_when_app_namespace_is_none(
        self, mock_run_command, tmp_path
    ):
        """Action app should use config.namespace when app.namespace is None."""
        # Arrange
        mock_run_command.return_value = (0, "", "")

        manifest_file = tmp_path / "test-manifest.yaml"
        manifest_file.write_text(
            """
apiVersion: v1
kind: ConfigMap
metadata:
  name: test-cm
"""
        )

        app = ActionApp(
            type="action",
            enabled=True,
            actions=[{"type": "apply", "path": "test-manifest.yaml"}],
            namespace=None,  # No app-level namespace
        )

        # Act
        result = deploy_action_app(
            app_name="test-action-app",
            app=app,
            base_dir=tmp_path,
            app_config_dir=tmp_path,
            kubeconfig=None,
            context=None,
            dry_run=False,
            config_namespace="action-namespace",  # Config-level namespace
        )

        # Assert
        assert result is True
        mock_run_command.assert_called_once()
        cmd = mock_run_command.call_args[0][0]
        assert "--namespace" in cmd
        assert "action-namespace" in cmd

    @patch("sbkube.commands.deploy.run_command")
    def test_uses_app_namespace_when_explicitly_set(self, mock_run_command, tmp_path):
        """Action app should use app.namespace when explicitly set."""
        # Arrange
        mock_run_command.return_value = (0, "", "")

        manifest_file = tmp_path / "test-manifest.yaml"
        manifest_file.write_text(
            """
apiVersion: v1
kind: ConfigMap
metadata:
  name: test-cm
"""
        )

        app = ActionApp(
            type="action",
            enabled=True,
            actions=[{"type": "apply", "path": "test-manifest.yaml"}],
            namespace="app-action-namespace",  # App-level override
        )

        # Act
        result = deploy_action_app(
            app_name="test-action-app",
            app=app,
            base_dir=tmp_path,
            app_config_dir=tmp_path,
            kubeconfig=None,
            context=None,
            dry_run=False,
            config_namespace="config-namespace",  # Should be ignored
        )

        # Assert
        assert result is True
        mock_run_command.assert_called_once()
        cmd = mock_run_command.call_args[0][0]
        assert "--namespace" in cmd
        assert "app-action-namespace" in cmd
        assert "config-namespace" not in cmd


class TestKustomizeAppNamespaceHandling:
    """Test namespace handling for Kustomize-type apps."""

    @patch("sbkube.commands.deploy.run_command")
    def test_uses_config_namespace_when_app_namespace_is_none(
        self, mock_run_command, tmp_path
    ):
        """Kustomize app should use config.namespace when app.namespace is None."""
        # Arrange
        mock_run_command.return_value = (0, "", "")

        kustomize_dir = tmp_path / "kustomize"
        kustomize_dir.mkdir()
        (kustomize_dir / "kustomization.yaml").write_text(
            """
apiVersion: kustomize.config.k8s.io/v1beta1
kind: Kustomization
resources:
  - deployment.yaml
"""
        )

        app = KustomizeApp(
            type="kustomize",
            enabled=True,
            path="kustomize",
            namespace=None,  # No app-level namespace
        )

        # Act
        result = deploy_kustomize_app(
            app_name="test-kustomize-app",
            app=app,
            base_dir=tmp_path,
            app_config_dir=tmp_path,
            kubeconfig=None,
            context=None,
            dry_run=False,
            config_namespace="kustomize-namespace",  # Config-level namespace
        )

        # Assert
        assert result is True
        mock_run_command.assert_called_once()
        cmd = mock_run_command.call_args[0][0]
        assert "--namespace" in cmd
        assert "kustomize-namespace" in cmd

    @patch("sbkube.commands.deploy.run_command")
    def test_uses_app_namespace_when_explicitly_set(self, mock_run_command, tmp_path):
        """Kustomize app should use app.namespace when explicitly set."""
        # Arrange
        mock_run_command.return_value = (0, "", "")

        kustomize_dir = tmp_path / "kustomize"
        kustomize_dir.mkdir()
        (kustomize_dir / "kustomization.yaml").write_text(
            """
apiVersion: kustomize.config.k8s.io/v1beta1
kind: Kustomization
resources:
  - deployment.yaml
"""
        )

        app = KustomizeApp(
            type="kustomize",
            enabled=True,
            path="kustomize",
            namespace="app-kustomize-namespace",  # App-level override
        )

        # Act
        result = deploy_kustomize_app(
            app_name="test-kustomize-app",
            app=app,
            base_dir=tmp_path,
            app_config_dir=tmp_path,
            kubeconfig=None,
            context=None,
            dry_run=False,
            config_namespace="config-namespace",  # Should be ignored
        )

        # Assert
        assert result is True
        mock_run_command.assert_called_once()
        cmd = mock_run_command.call_args[0][0]
        assert "--namespace" in cmd
        assert "app-kustomize-namespace" in cmd
        assert "config-namespace" not in cmd


class TestNamespaceHandlingConsistency:
    """Test consistency of namespace handling across all app types."""

    @patch("sbkube.commands.deploy.run_command")
    def test_yaml_and_action_apps_behave_identically(self, mock_run_command, tmp_path):
        """YAML and Action apps should behave identically for namespace handling."""
        # Arrange
        mock_run_command.return_value = (0, "", "")

        manifest_file = tmp_path / "test.yaml"
        manifest_file.write_text(
            """
apiVersion: v1
kind: ConfigMap
metadata:
  name: test
"""
        )

        yaml_app = YamlApp(
            type="yaml", enabled=True, manifests=["test.yaml"], namespace=None
        )

        action_app = ActionApp(
            type="action",
            enabled=True,
            actions=[{"type": "apply", "path": "test.yaml"}],
            namespace=None,
        )

        # Act - Deploy YAML app
        deploy_yaml_app(
            app_name="yaml-app",
            app=yaml_app,
            base_dir=tmp_path,
            app_config_dir=tmp_path,
            kubeconfig=None,
            context=None,
            dry_run=False,
            apps_config=None,
            sbkube_work_dir=None,
            config_namespace="test-ns",
        )

        yaml_cmd = mock_run_command.call_args[0][0]
        mock_run_command.reset_mock()

        # Act - Deploy Action app
        deploy_action_app(
            app_name="action-app",
            app=action_app,
            base_dir=tmp_path,
            app_config_dir=tmp_path,
            kubeconfig=None,
            context=None,
            dry_run=False,
            config_namespace="test-ns",
        )

        action_cmd = mock_run_command.call_args[0][0]

        # Assert - Both should have --namespace flag
        assert "--namespace" in yaml_cmd
        assert "--namespace" in action_cmd
        assert "test-ns" in yaml_cmd
        assert "test-ns" in action_cmd


class TestNamespaceHandlingEdgeCases:
    """Test edge cases for namespace handling."""

    @patch("sbkube.commands.deploy.run_command")
    def test_empty_string_namespace_is_treated_as_none(
        self, mock_run_command, tmp_path
    ):
        """Empty string namespace should be treated as None and use config.namespace."""
        # Arrange
        mock_run_command.return_value = (0, "", "")

        manifest_file = tmp_path / "test.yaml"
        manifest_file.write_text(
            """
apiVersion: v1
kind: Secret
metadata:
  name: test-secret
"""
        )

        # Create app with empty string namespace (simulates YAML parsing edge case)
        app = YamlApp(type="yaml", enabled=True, manifests=["test.yaml"], namespace="")

        # Act
        result = deploy_yaml_app(
            app_name="test-app",
            app=app,
            base_dir=tmp_path,
            app_config_dir=tmp_path,
            kubeconfig=None,
            context=None,
            dry_run=False,
            apps_config=None,
            sbkube_work_dir=None,
            config_namespace="fallback-ns",
        )

        # Assert
        assert result is True
        mock_run_command.assert_called_once()
        cmd = mock_run_command.call_args[0][0]
        # Empty string is falsy in Python, so should fallback to config_namespace
        assert "--namespace" in cmd
        assert "fallback-ns" in cmd
