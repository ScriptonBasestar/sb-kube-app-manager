"""Active access profiles constrain child command environments only."""

import os
import subprocess
from pathlib import Path
from unittest.mock import MagicMock, patch

import pytest

from sbkube.commands.deploy import deploy_exec_app
from sbkube.models.config_model import ExecApp
from sbkube.utils.access_profile import (
    AccessProfileError,
    SelectedProfile,
    _selected,
    profile_environment,
)
from sbkube.utils.hook_executor import HookExecutor
from sbkube.utils.output_manager import OutputManager

TOKEN = "DO-NOT-EXPORT-TOKEN"


def _kubeconfig(path: Path, current_context: str = "home") -> Path:
    path.write_text(
        f"current-context: {current_context}\n"
        "contexts:\n- name: home\n  context: {cluster: home}\n"
        "clusters:\n- name: home\n  cluster: {server: https://home:6443}\n"
        f"users:\n- name: agent\n  user: {{token: {TOKEN}}}\n"
    )
    return path


@pytest.fixture
def selected(tmp_path: Path) -> SelectedProfile:
    return SelectedProfile(
        _kubeconfig(tmp_path / "deployer"),
        "home",
        {"context": "home", "server": "https://home:6443", "ca_sha256": "a" * 64},
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


def test_profile_environment_without_active_profile_returns_unmodified_copy() -> None:
    inherited = {
        "KUBECONFIG": "/admin",
        "HELM_KUBETOKEN": "admin-token",
        "OTHER": "value",
    }

    child = profile_environment(inherited)

    assert child == inherited
    assert child is not inherited


def test_active_profile_overwrites_only_child_kubeconfig(
    active_profile: SelectedProfile,
) -> None:
    inherited = {
        "KUBECONFIG": "/admin",
        "HELM_KUBETOKEN": "admin-token",
        "HELM_KUBECONTEXT": "admin-context",
        "HELM_KUBEAPISERVER": "https://admin:6443",
        "HELM_KUBECAFILE": "/admin-ca",
        "HELM_KUBEINSECURE_SKIP_TLS_VERIFY": "true",
        "HELM_KUBETLS_SERVER_NAME": "admin",
        "HELM_KUBEASUSER": "admin",
        "HELM_KUBEASGROUPS": "system:masters",
        "OTHER": "value",
    }

    child = profile_environment(inherited)

    assert child["KUBECONFIG"] == str(active_profile.kubeconfig.absolute())
    assert inherited["KUBECONFIG"] == "/admin"
    assert any(key.startswith("HELM_KUBE") for key in inherited)
    assert not any(key.startswith("HELM_KUBE") for key in child)
    assert TOKEN not in child.values()


def test_active_profile_refuses_current_context_mismatch(
    selected: SelectedProfile,
) -> None:
    _kubeconfig(selected.kubeconfig, current_context="other")
    marker = _selected.set(selected)
    try:
        with pytest.raises(AccessProfileError, match="current-context differs"):
            profile_environment({"KUBECONFIG": "/admin"})
    finally:
        _selected.reset(marker)


def test_active_profile_refuses_explicit_hook_kubeconfig_conflict(
    active_profile: SelectedProfile,
) -> None:
    with pytest.raises(AccessProfileError, match="explicit hook KUBECONFIG conflicts"):
        profile_environment({"KUBECONFIG": "/admin"}, {"KUBECONFIG": "/admin"})


def test_active_profile_refuses_kubeconfig_path_list(selected: SelectedProfile) -> None:
    listed = SelectedProfile(
        Path(f"{selected.kubeconfig}{os.pathsep}/another"),
        selected.context,
        selected.identity,
        selected.legacy_kubeconfig,
        selected.owner,
        selected.principal,
    )
    marker = _selected.set(listed)
    try:
        with pytest.raises(AccessProfileError, match="exactly one file"):
            profile_environment({})
    finally:
        _selected.reset(marker)


def test_active_profile_refuses_explicit_helm_override_without_value_leakage(
    active_profile: SelectedProfile,
) -> None:
    override = "admin-token-sentinel"
    with pytest.raises(AccessProfileError, match="HELM_KUBE override") as raised:
        profile_environment({}, {"HELM_KUBETOKEN": override})
    assert override not in str(raised.value)


def test_raw_hook_receives_profile_kubeconfig_without_global_mutation(
    monkeypatch, tmp_path: Path, active_profile: SelectedProfile
) -> None:
    monkeypatch.setenv("KUBECONFIG", "/admin")
    executor = HookExecutor(base_dir=tmp_path, env={"HOOK": "enabled"})
    completed = subprocess.CompletedProcess([], 0, "", "")
    with (
        patch("sbkube.utils.hook_executor.is_exec_allowed", return_value=True),
        patch(
            "sbkube.utils.hook_executor.subprocess.run", return_value=completed
        ) as run,
    ):
        assert executor._execute_single_command("vault read", "pre")

    command = run.call_args.args[0]
    child_env = run.call_args.kwargs["env"]
    assert child_env["KUBECONFIG"] == str(active_profile.kubeconfig.absolute())
    assert child_env["HOOK"] == "enabled"
    assert TOKEN not in command
    assert TOKEN not in child_env.values()
    assert os.environ["KUBECONFIG"] == "/admin"


@pytest.mark.parametrize(
    "executor",
    [
        lambda path: HookExecutor(base_dir=path, kubeconfig="/foreign", context="home"),
        lambda path: HookExecutor(base_dir=path, env={"KUBECONFIG": "/foreign"}),
        lambda path: HookExecutor(
            base_dir=path, env={"HELM_KUBETOKEN": "admin-token-sentinel"}
        ),
    ],
)
def test_raw_hook_profile_conflicts_stop_before_subprocess(
    tmp_path: Path, active_profile: SelectedProfile, executor
) -> None:
    with (
        patch("sbkube.utils.hook_executor.is_exec_allowed", return_value=True),
        patch("sbkube.utils.hook_executor.subprocess.run") as run,
    ):
        assert executor(tmp_path)._execute_single_command("vault read", "pre") is False
    run.assert_not_called()


def test_exec_app_uses_profile_environment_only_when_active(
    monkeypatch, tmp_path: Path, active_profile: SelectedProfile
) -> None:
    monkeypatch.setenv("KUBECONFIG", "/admin")
    output = MagicMock(spec=OutputManager)
    app = ExecApp(type="exec", commands=["vault read"])
    with (
        patch("sbkube.commands.deploy.is_exec_allowed", return_value=True),
        patch("sbkube.commands.deploy.run_command", return_value=(0, "", "")) as run,
    ):
        assert deploy_exec_app("vault", app, tmp_path, output)

    assert run.call_args.args == ("vault read",)
    assert run.call_args.kwargs["timeout"] == 60
    assert run.call_args.kwargs["cwd"] == tmp_path
    child_env = run.call_args.kwargs["env"]
    assert child_env["KUBECONFIG"] == str(active_profile.kubeconfig.absolute())
    assert TOKEN not in child_env.values()
    assert os.environ["KUBECONFIG"] == "/admin"


def test_exec_app_keeps_inactive_run_command_kwargs(tmp_path: Path) -> None:
    output = MagicMock(spec=OutputManager)
    app = ExecApp(type="exec", commands=["echo inactive"])
    with (
        patch("sbkube.commands.deploy.is_exec_allowed", return_value=True),
        patch("sbkube.commands.deploy.run_command", return_value=(0, "", "")) as run,
    ):
        assert deploy_exec_app("inactive", app, tmp_path, output)

    run.assert_called_once_with("echo inactive", timeout=60)
