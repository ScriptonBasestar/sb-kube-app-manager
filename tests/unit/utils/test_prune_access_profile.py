"""Pruning keeps an active access profile through app-level contexts."""

from pathlib import Path
from unittest.mock import MagicMock, patch

import pytest

from sbkube.models.config_model import AppConfig, HelmApp, YamlApp
from sbkube.utils.access_profile import AccessProfileError, SelectedProfile, _selected
from sbkube.utils.prune_helper import (
    _prune_helm_app,
    _prune_yaml_app,
    prune_disabled_apps,
)


@pytest.fixture
def selected(tmp_path: Path) -> SelectedProfile:
    return SelectedProfile(
        tmp_path / "deployer",
        "home",
        {"context": "home", "server": "https://home", "ca_sha256": "a" * 64},
        None,
        tmp_path,
        "system:serviceaccount:agent-access:sbkube-deployer",
    )


@pytest.fixture
def active_profile(selected: SelectedProfile):
    marker = _selected.set(selected)
    try:
        yield selected
    finally:
        _selected.reset(marker)


def test_prune_helm_with_same_app_context_uses_selected_credential(
    active_profile: SelectedProfile,
) -> None:
    app = HelmApp(
        chart="repo/chart",
        version="1.0.0",
        release_name="web",
        namespace="default",
        context="home",
        enabled=False,
    )
    output = MagicMock()
    with (
        patch(
            "sbkube.utils.helm_util.get_installed_charts", return_value=["web"]
        ) as charts,
        patch("sbkube.utils.prune_helper.run_command", return_value=(0, "", "")) as run,
    ):
        assert _prune_helm_app("web", app, "legacy", "legacy", output, False)

    assert charts.call_args.kwargs == {
        "context": "home",
        "kubeconfig": str(active_profile.kubeconfig),
    }
    assert "--kubeconfig" in run.call_args.args[0]
    assert str(active_profile.kubeconfig) in run.call_args.args[0]


def test_prune_yaml_with_same_app_context_uses_selected_credential(
    tmp_path: Path, active_profile: SelectedProfile
) -> None:
    manifest = tmp_path / "app.yaml"
    manifest.write_text("apiVersion: v1\nkind: ConfigMap\nmetadata: {name: app}\n")
    app = YamlApp(manifests=[manifest.name], context="home", enabled=False)
    output = MagicMock()
    with patch(
        "sbkube.utils.prune_helper.run_command", return_value=(0, "", "")
    ) as run:
        assert _prune_yaml_app("app", app, "legacy", "legacy", tmp_path, output, False)

    command = run.call_args.args[0]
    assert command[0:2] == ["kubectl", "delete"]
    assert command[command.index("--kubeconfig") + 1] == str(active_profile.kubeconfig)
    assert command[command.index("--context") + 1] == "home"


@pytest.mark.parametrize(
    "app",
    [
        HelmApp(
            chart="repo/chart",
            version="1.0.0",
            release_name="app",
            namespace="default",
            context="other",
            enabled=False,
        ),
        YamlApp(manifests=["app.yaml"], context="other", enabled=False),
    ],
)
def test_other_app_context_refuses_before_prune_tools(
    tmp_path: Path, active_profile: SelectedProfile, app
) -> None:
    output = MagicMock()
    with (
        patch("sbkube.utils.helm_util.get_installed_charts") as charts,
        patch("sbkube.utils.prune_helper.run_command") as run,
        pytest.raises(AccessProfileError, match="context differs"),
    ):
        if isinstance(app, HelmApp):
            _prune_helm_app("app", app, "legacy", "legacy", output, False)
        else:
            _prune_yaml_app("app", app, "legacy", "legacy", tmp_path, output, False)
    charts.assert_not_called()
    run.assert_not_called()


def test_prune_prevalidates_all_apps_before_any_mutation(
    tmp_path: Path, active_profile: SelectedProfile
) -> None:
    apps: list[tuple[str, AppConfig]] = [
        (
            "first",
            HelmApp(
                chart="repo/chart",
                version="1.0.0",
                release_name="first",
                namespace="default",
                context="home",
                enabled=False,
            ),
        ),
        (
            "other",
            HelmApp(
                chart="repo/chart",
                version="1.0.0",
                release_name="other",
                namespace="default",
                context="other",
                enabled=False,
            ),
        ),
    ]
    output = MagicMock()
    with (
        patch("sbkube.utils.helm_util.get_installed_charts") as charts,
        patch("sbkube.utils.prune_helper.run_command") as run,
        pytest.raises(AccessProfileError, match="context differs"),
    ):
        prune_disabled_apps(
            apps,
            str(active_profile.kubeconfig),
            active_profile.context,
            tmp_path,
            output,
        )
    charts.assert_not_called()
    run.assert_not_called()


def test_prune_prevalidation_probe_reaches_first_tool_when_scan_is_disabled(
    tmp_path: Path, active_profile: SelectedProfile
) -> None:
    apps: list[tuple[str, AppConfig]] = [
        (
            "first",
            HelmApp(
                chart="repo/chart",
                version="1.0.0",
                release_name="first",
                namespace="default",
                context="home",
                enabled=False,
            ),
        ),
        (
            "other",
            HelmApp(
                chart="repo/chart",
                version="1.0.0",
                release_name="other",
                namespace="default",
                context="other",
                enabled=False,
            ),
        ),
    ]
    output = MagicMock()
    with (
        patch("sbkube.utils.prune_helper.validate_profile_document"),
        patch("sbkube.utils.helm_util.get_installed_charts") as charts,
        pytest.raises(AccessProfileError, match="context differs"),
    ):
        prune_disabled_apps(
            apps,
            str(active_profile.kubeconfig),
            active_profile.context,
            tmp_path,
            output,
        )
    charts.assert_called_once()
