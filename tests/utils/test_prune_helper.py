"""Tests for prune_helper module."""

from unittest.mock import MagicMock, patch

from sbkube.models.config_model import (
    ExecApp,
    HelmApp,
    NoopApp,
    SBKubeConfig,
    YamlApp,
)
from sbkube.utils.prune_helper import find_disabled_apps_to_prune, prune_disabled_apps


def _make_config(apps: dict) -> SBKubeConfig:
    """Helper to build SBKubeConfig with given apps dict."""
    return SBKubeConfig(namespace="default", apps=apps)


def _make_output() -> MagicMock:
    """Create a mock OutputManager."""
    output = MagicMock()
    output.print = MagicMock()
    output.print_section = MagicMock()
    return output


# ============================================================================
# find_disabled_apps_to_prune tests
# ============================================================================


class TestFindDisabledAppsToPrune:
    def test_empty_config(self) -> None:
        config = _make_config({})
        result = find_disabled_apps_to_prune(config)
        assert result == []

    def test_all_enabled(self) -> None:
        config = _make_config(
            {
                "app1": HelmApp(chart="repo/chart", enabled=True),
                "app2": YamlApp(manifests=["m.yaml"], enabled=True),
            }
        )
        result = find_disabled_apps_to_prune(config)
        assert result == []

    def test_with_disabled_helm(self) -> None:
        config = _make_config(
            {
                "enabled-app": HelmApp(chart="repo/chart", enabled=True),
                "disabled-helm": HelmApp(chart="repo/other", enabled=False),
            }
        )
        result = find_disabled_apps_to_prune(config)
        assert len(result) == 1
        assert result[0][0] == "disabled-helm"

    def test_with_disabled_yaml(self) -> None:
        config = _make_config(
            {
                "disabled-yaml": YamlApp(manifests=["deploy.yaml"], enabled=False),
            }
        )
        result = find_disabled_apps_to_prune(config)
        assert len(result) == 1
        assert result[0][0] == "disabled-yaml"

    def test_excludes_unsupported_types(self) -> None:
        """exec, noop types should not be pruned."""
        config = _make_config(
            {
                "disabled-exec": ExecApp(commands=["echo hi"], enabled=False),
                "disabled-noop": NoopApp(enabled=False),
                "disabled-helm": HelmApp(chart="repo/chart", enabled=False),
            }
        )
        result = find_disabled_apps_to_prune(config)
        assert len(result) == 1
        assert result[0][0] == "disabled-helm"

    def test_multiple_disabled(self) -> None:
        config = _make_config(
            {
                "helm1": HelmApp(chart="a/b", enabled=False),
                "yaml1": YamlApp(manifests=["x.yaml"], enabled=False),
                "helm2": HelmApp(chart="c/d", enabled=True),
            }
        )
        result = find_disabled_apps_to_prune(config)
        assert len(result) == 2
        names = [r[0] for r in result]
        assert "helm1" in names
        assert "yaml1" in names


# ============================================================================
# prune_disabled_apps tests
# ============================================================================


class TestPruneHelmApp:
    @patch("sbkube.utils.prune_helper.run_command")
    @patch("sbkube.utils.prune_helper._prune_helm_app")
    def test_prune_helm_installed(self, mock_prune_helm, mock_run) -> None:
        """Installed Helm app should be uninstalled."""
        mock_prune_helm.return_value = True
        output = _make_output()

        apps = [("my-app", HelmApp(chart="repo/chart", enabled=False))]
        result = prune_disabled_apps(
            apps_to_prune=apps,
            kubeconfig="/kube/config",
            context="my-ctx",
            app_config_dir=MagicMock(),
            output=output,
            dry_run=False,
        )
        assert result is True
        mock_prune_helm.assert_called_once()

    @patch("sbkube.utils.helm_util.get_installed_charts", return_value={})
    def test_prune_helm_not_installed(self, mock_charts) -> None:
        """Helm app not installed should be skipped."""
        from sbkube.utils.prune_helper import _prune_helm_app

        output = _make_output()
        result = _prune_helm_app(
            app_name="my-app",
            app_config=HelmApp(chart="repo/chart", enabled=False, namespace="default"),
            kubeconfig=None,
            context=None,
            output=output,
            dry_run=False,
        )
        assert result is True

    @patch(
        "sbkube.utils.helm_util.get_installed_charts",
        return_value={"my-app": {"name": "my-app"}},
    )
    @patch("sbkube.utils.prune_helper.run_command", return_value=(0, "", ""))
    def test_prune_helm_installed_succeeds(self, mock_run, mock_charts) -> None:
        """Installed Helm app should execute helm uninstall."""
        from sbkube.utils.prune_helper import _prune_helm_app

        output = _make_output()
        result = _prune_helm_app(
            app_name="my-app",
            app_config=HelmApp(chart="repo/chart", enabled=False, namespace="test-ns"),
            kubeconfig="/kube/config",
            context="ctx",
            output=output,
            dry_run=False,
        )
        assert result is True
        mock_run.assert_called_once()
        cmd_args = mock_run.call_args[0][0]
        assert "helm" in cmd_args
        assert "uninstall" in cmd_args
        assert "my-app" in cmd_args

    @patch(
        "sbkube.utils.helm_util.get_installed_charts",
        return_value={"my-app": {"name": "my-app"}},
    )
    def test_prune_helm_dry_run(self, mock_charts) -> None:
        """Dry run should not execute helm uninstall."""
        from sbkube.utils.prune_helper import _prune_helm_app

        output = _make_output()
        result = _prune_helm_app(
            app_name="my-app",
            app_config=HelmApp(chart="repo/chart", enabled=False, namespace="default"),
            kubeconfig=None,
            context=None,
            output=output,
            dry_run=True,
        )
        assert result is True


class TestPruneYamlApp:
    @patch("sbkube.utils.prune_helper.run_command", return_value=(0, "", ""))
    def test_prune_yaml_app(self, mock_run, tmp_path) -> None:
        """YAML app should run kubectl delete -f for each manifest."""
        from sbkube.utils.prune_helper import _prune_yaml_app

        # Create a manifest file
        manifest = tmp_path / "deploy.yaml"
        manifest.write_text("apiVersion: v1\nkind: Pod")

        output = _make_output()
        app = YamlApp(manifests=[str(manifest)], enabled=False, namespace="test-ns")
        result = _prune_yaml_app(
            app_name="my-yaml",
            app_config=app,
            kubeconfig=None,
            context=None,
            app_config_dir=tmp_path,
            output=output,
            dry_run=False,
        )
        assert result is True
        mock_run.assert_called_once()

    def test_prune_yaml_dry_run(self, tmp_path) -> None:
        """Dry run should not execute kubectl delete."""
        from sbkube.utils.prune_helper import _prune_yaml_app

        manifest = tmp_path / "deploy.yaml"
        manifest.write_text("apiVersion: v1\nkind: Pod")

        output = _make_output()
        app = YamlApp(manifests=[str(manifest)], enabled=False, namespace="test-ns")
        result = _prune_yaml_app(
            app_name="my-yaml",
            app_config=app,
            kubeconfig=None,
            context=None,
            app_config_dir=tmp_path,
            output=output,
            dry_run=True,
        )
        assert result is True


class TestPruneDryRun:
    @patch(
        "sbkube.utils.helm_util.get_installed_charts",
        return_value={"helm-app": {"name": "helm-app"}},
    )
    def test_full_dry_run(self, mock_charts, tmp_path) -> None:
        """Full prune with dry_run should not call run_command."""
        output = _make_output()
        apps = [
            ("helm-app", HelmApp(chart="repo/chart", enabled=False, namespace="default")),
        ]

        with patch("sbkube.utils.prune_helper.run_command") as mock_run:
            result = prune_disabled_apps(
                apps_to_prune=apps,
                kubeconfig=None,
                context=None,
                app_config_dir=tmp_path,
                output=output,
                dry_run=True,
            )
            assert result is True
            mock_run.assert_not_called()
