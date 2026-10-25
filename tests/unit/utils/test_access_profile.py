"""Local-only access profile selection and scope regressions."""

import base64
import contextvars
import json
import time
from pathlib import Path
from typing import Any
from unittest.mock import patch

import click
import pytest

from sbkube.utils.access_profile import (
    AccessProfileError,
    SelectedProfile,
    access_owner_config,
    current_profile,
    install_profile,
    select_profile,
)
from sbkube.utils.target_resolver import resolve_target


def _jwt(subject: str, exp: float | None = None) -> str:
    def encoded(value: dict) -> str:
        return (
            base64.urlsafe_b64encode(json.dumps(value).encode()).rstrip(b"=").decode()
        )

    claims: dict[str, Any] = {"sub": subject}
    if exp is not None:
        claims["exp"] = exp
    return f"{encoded({'alg': 'none'})}.{encoded(claims)}.signature"


def _kubeconfig(
    path: Path,
    *,
    token: str | None,
    token_file: str | None = None,
    context: str = "home",
    server: str = "https://home:6443",
    ca: bytes = b"public-ca",
) -> Path:
    credential = f"tokenFile: {token_file}" if token_file else f"token: {token}"
    path.write_text(
        "contexts:\n"
        f"- name: {context}\n  context: {{cluster: home, user: agent}}\n"
        "clusters:\n"
        f"- name: home\n  cluster: {{server: {server}, certificate-authority-data: {base64.b64encode(ca).decode()}}}\n"
        f"users:\n- name: agent\n  user: {{{credential}}}\n"
    )
    return path


def _config(
    root: Path,
    readonly: Path,
    deployer: Path,
    *,
    context: str = "home",
    legacy: str | None = None,
    auto_profile: bool = True,
) -> Path:
    config = root / "sbkube.yaml"
    config.write_text(
        "apiVersion: sbkube/v1\nsettings:\n"
        f"  kubeconfig: {legacy or root / 'admin-missing'}\n"
        f"  kubeconfig_context: {context}\n"
        "  access:\n"
        f"    auto_profile: {str(auto_profile).lower()}\n"
        "    namespace: agent-access\n"
        "    readonly:\n"
        f"      kubeconfig: {readonly}\n"
        "      service_account: agent-readonly\n"
        "    deployer:\n"
        f"      kubeconfig: {deployer}\n"
        "      service_account: sbkube-deployer\n"
    )
    return config


def _profiles(root: Path) -> tuple[Path, Path, Path]:
    readonly = _kubeconfig(
        root / "readonly",
        token=_jwt("system:serviceaccount:agent-access:agent-readonly"),
    )
    deployer = _kubeconfig(
        root / "deployer",
        token=_jwt(
            "system:serviceaccount:agent-access:sbkube-deployer", time.time() + 3600
        ),
    )
    return _config(root, readonly, deployer), readonly, deployer


@pytest.mark.parametrize(
    "command", ["apply", "deploy", "delete", "upgrade", "rollback"]
)
def test_mutating_commands_select_deployer_even_when_dry_run(
    tmp_path: Path, command: str
) -> None:
    config, _, deployer = _profiles(tmp_path)

    selected = select_profile(
        command, {"config_file": str(config), "dry_run": True}, {}
    )

    assert selected is not None
    assert selected.kubeconfig == deployer
    assert selected.principal.endswith(":sbkube-deployer")


def test_status_selects_readonly(tmp_path: Path) -> None:
    config, readonly, _ = _profiles(tmp_path)

    selected = select_profile("status", {"config_file": str(config)}, {})

    assert selected is not None
    assert selected.kubeconfig == readonly
    assert selected.principal.endswith(":agent-readonly")


def test_no_access_or_disabled_profile_returns_none_without_credentials(
    tmp_path: Path,
) -> None:
    config = tmp_path / "sbkube.yaml"
    config.write_text(
        "apiVersion: sbkube/v1\nsettings:\n  access:\n    auto_profile: false\n"
    )

    assert select_profile("deploy", {"config_file": str(config)}, {}) is None
    (tmp_path / "no-access.yaml").write_text("apiVersion: sbkube/v1\nsettings: {}\n")
    assert (
        select_profile("status", {"config_file": str(tmp_path / "no-access.yaml")}, {})
        is None
    )


def test_auto_profile_rejects_inherited_helm_override_but_disabled_mode_is_compatible(
    monkeypatch, tmp_path: Path
) -> None:
    config, readonly, deployer = _profiles(tmp_path)
    sentinel = "admin-token-sentinel"
    monkeypatch.setenv("HELM_KUBETOKEN", sentinel)

    with patch("sbkube.utils.access_profile.cluster_identity") as identity:
        with pytest.raises(
            AccessProfileError, match="inherited HELM_KUBE override"
        ) as raised:
            select_profile("status", {"config_file": str(config)}, {})
    identity.assert_not_called()
    assert sentinel not in str(raised.value)

    disabled = _config(tmp_path, readonly, deployer, auto_profile=False)
    assert select_profile("status", {"config_file": str(disabled)}, {}) is None


def test_workspace_root_owns_access_and_parent_is_not_implicitly_inherited(
    tmp_path: Path,
) -> None:
    root = tmp_path / "workspace"
    child = root / "phase" / "app"
    child.mkdir(parents=True)
    (root / ".sbkube-workspace").write_text("anchors: {}\n")
    config, readonly, _ = _profiles(root)
    (child / "sbkube.yaml").write_text("apiVersion: sbkube/v1\nsettings: {}\n")

    selected = select_profile("status", {"target": str(child)}, {})
    assert (
        selected is not None
        and selected.owner == config
        and selected.kubeconfig == readonly
    )

    outside = tmp_path / "outside" / "child"
    outside.mkdir(parents=True)
    (tmp_path / "outside" / "sbkube.yaml").write_text(config.read_text())
    assert select_profile("status", {"base_dir": str(outside)}, {}) is None


@pytest.mark.parametrize("command", ["apply", "deploy"])
def test_explicit_target_uses_native_upward_config_without_workspace_marker(
    tmp_path: Path, command: str
) -> None:
    root = tmp_path / "cluster"
    child = root / "phase" / "app"
    child.mkdir(parents=True)
    config, _, deployer = _profiles(root)
    native = resolve_target(str(child), base_dir=Path.cwd())

    selected = select_profile(command, {"target": str(child)}, {})

    assert native.config_file == config
    assert access_owner_config({"target": str(child)}) == native.config_file
    assert selected is not None and selected.owner == config
    assert selected.kubeconfig == deployer


def test_explicit_target_with_local_no_access_config_does_not_inherit_parent(
    tmp_path: Path,
) -> None:
    root = tmp_path / "cluster"
    child = root / "phase" / "app"
    child.mkdir(parents=True)
    _profiles(root)
    child_config = child / "sbkube.yaml"
    child_config.write_text("apiVersion: sbkube/v1\nsettings: {}\n")

    assert access_owner_config({"target": str(child)}) == child_config
    assert select_profile("apply", {"target": str(child)}, {}) is None


@pytest.mark.parametrize("token_file", [False, True])
def test_readonly_token_may_be_inline_or_file_without_expiry(
    tmp_path: Path, token_file: bool
) -> None:
    readonly_token = _jwt("system:serviceaccount:agent-access:agent-readonly")
    token_path = tmp_path / "readonly.token"
    if token_file:
        token_path.write_text(readonly_token)
    readonly = _kubeconfig(
        tmp_path / "readonly",
        token=None if token_file else readonly_token,
        token_file=token_path.name if token_file else None,
    )
    deployer = _kubeconfig(
        tmp_path / "deployer",
        token=_jwt(
            "system:serviceaccount:agent-access:sbkube-deployer", time.time() + 3600
        ),
    )
    config = _config(tmp_path, readonly, deployer)

    assert select_profile("status", {"config_file": str(config)}, {}) is not None


@pytest.mark.parametrize(
    ("command", "token", "needle"),
    [
        ("status", "not-a-real-token", "access init"),
        ("deploy", "not-a-real-token", "access issue"),
        (
            "deploy",
            _jwt("system:serviceaccount:agent-access:sbkube-deployer"),
            "access issue",
        ),
        (
            "deploy",
            _jwt("system:serviceaccount:agent-access:sbkube-deployer", time.time() - 1),
            "access issue",
        ),
    ],
)
def test_invalid_missing_or_expired_tokens_refuse_without_leaking_token(
    tmp_path: Path, command: str, token: str, needle: str
) -> None:
    config, readonly, deployer = _profiles(tmp_path)
    target = readonly if command == "status" else deployer
    _kubeconfig(target, token=token)

    with pytest.raises(AccessProfileError, match=needle) as raised:
        select_profile(command, {"config_file": str(config)}, {})
    assert token not in str(raised.value)


@pytest.mark.parametrize("difference", ["server", "ca"])
def test_readonly_deployer_identity_mismatch_refuses(
    tmp_path: Path, difference: str
) -> None:
    config, _, deployer = _profiles(tmp_path)
    if difference == "server":
        _kubeconfig(
            deployer,
            token=_jwt(
                "system:serviceaccount:agent-access:sbkube-deployer", time.time() + 3600
            ),
            server="https://other:6443",
        )
    else:
        _kubeconfig(
            deployer,
            token=_jwt(
                "system:serviceaccount:agent-access:sbkube-deployer", time.time() + 3600
            ),
            ca=b"other-ca",
        )

    with pytest.raises(AccessProfileError, match="different clusters"):
        select_profile("deploy", {"config_file": str(config)}, {})


@pytest.mark.parametrize("obj", [{"context": "other"}, {"kubeconfig": "/different"}])
def test_cli_profile_conflict_never_silently_overrides(
    tmp_path: Path, obj: dict
) -> None:
    config, _, _ = _profiles(tmp_path)

    with pytest.raises(AccessProfileError, match="conflicts"):
        select_profile("status", {"config_file": str(config)}, obj)


def test_selected_profile_resolve_enforces_child_cluster_and_legacy_path(
    tmp_path: Path,
) -> None:
    config, readonly, _ = _profiles(tmp_path)
    missing_legacy = tmp_path / "old-admin"
    _config(tmp_path, readonly, tmp_path / "deployer", legacy=str(missing_legacy))
    selected = select_profile("status", {"config_file": str(config)}, {})
    assert selected is not None

    with pytest.raises(AccessProfileError, match="context differs"):
        selected.resolve(None, "other")
    foreign = _kubeconfig(
        tmp_path / "foreign",
        token=_jwt("system:serviceaccount:agent-access:agent-readonly"),
        server="https://other:6443",
    )
    with pytest.raises(AccessProfileError, match="different access cluster"):
        selected.resolve(str(foreign), None)
    with pytest.raises(AccessProfileError, match="cannot verify missing"):
        selected.resolve(str(tmp_path / "missing-foreign"), None)
    assert selected.resolve(str(missing_legacy), None) == (str(readonly), "home")


def test_install_profile_restores_click_and_contextvar_after_exception(
    monkeypatch, tmp_path: Path
) -> None:
    selected = SelectedProfile(
        tmp_path / "readonly",
        "home",
        {"context": "home", "server": "https://home", "ca_sha256": "a" * 64},
        None,
        tmp_path,
        "subject",
    )
    monkeypatch.setattr(
        "sbkube.utils.access_profile.select_profile", lambda *_: selected
    )
    observed: dict[str, object] = {}

    def nested_callback() -> None:
        observed["nested"] = current_profile()

    nested = click.Command("status", callback=nested_callback)
    install_profile(nested)

    def callback() -> None:
        ctx = click.get_current_context()
        observed["obj"] = dict(ctx.obj)
        observed["profile"] = current_profile()
        observed["copied"] = contextvars.copy_context().run(current_profile)
        nested_ctx = click.Context(nested, parent=ctx)
        with nested_ctx:
            assert nested.callback is not None
            nested.callback()
        raise RuntimeError("boom")

    command = click.Command("status", callback=callback)
    install_profile(command)
    ctx = click.Context(command, obj={"kubeconfig": "before", "context": "before"})
    with ctx, pytest.raises(RuntimeError, match="boom"):
        assert command.callback is not None
        command.callback()

    assert observed["obj"] == {
        "kubeconfig": str(selected.kubeconfig),
        "context": "home",
    }
    assert observed["profile"] == selected == observed["copied"]
    assert observed["nested"] == selected
    assert ctx.obj == {"kubeconfig": "before", "context": "before"}
    assert current_profile() is None


def test_anchor_only_workspace_marker_uses_outer_cluster_config_for_explicit_and_child(
    tmp_path: Path,
) -> None:
    workspace = tmp_path / "workspace"
    cluster = workspace / "cluster" / "ph4"
    child = cluster / "app"
    child.mkdir(parents=True)
    (workspace / ".sbkube-workspace").write_text("anchors: {}\n")
    config, _, _ = _profiles(cluster)
    child_config = child / "sbkube.yaml"
    child_config.write_text("apiVersion: sbkube/v1\nsettings: {}\n")

    assert access_owner_config({"config_file": str(config)}) == config
    assert access_owner_config({"config_file": str(child_config)}) == config


def test_sibling_cluster_roots_remain_independent_inside_anchor_only_workspace(
    tmp_path: Path,
) -> None:
    workspace = tmp_path / "workspace"
    workspace.mkdir()
    (workspace / ".sbkube-workspace").write_text("anchors: {}\n")
    alpha = workspace / "alpha"
    beta = workspace / "beta"
    alpha_child = alpha / "app"
    beta_child = beta / "app"
    alpha_child.mkdir(parents=True)
    beta_child.mkdir(parents=True)
    alpha_config, _, _ = _profiles(alpha)
    beta_config, _, _ = _profiles(beta)

    assert access_owner_config({"target": str(alpha_child)}) == alpha_config
    assert access_owner_config({"target": str(beta_child)}) == beta_config


@pytest.mark.parametrize(
    "child_settings",
    [
        "settings:\n  kubeconfig_context: other\n",
        "settings: {}\napps:\n  child:\n    context: other\n",
    ],
)
def test_child_context_conflict_refuses_during_selection_before_callback(
    tmp_path: Path, child_settings: str
) -> None:
    root = tmp_path / "root"
    child = root / "child"
    child.mkdir(parents=True)
    (root / ".sbkube-workspace").write_text("anchors: {}\n")
    _profiles(root)
    child_config = child / "sbkube.yaml"
    child_config.write_text(f"apiVersion: sbkube/v1\n{child_settings}")

    with pytest.raises(AccessProfileError, match="differs"):
        select_profile("deploy", {"config_file": str(child_config)}, {})


def test_rollback_list_bypasses_profile_and_target_id_does_not_become_path(
    tmp_path: Path,
) -> None:
    config, _, deployer = _profiles(tmp_path)

    assert (
        select_profile("rollback", {"list_points": True, "target": "deployment-id"}, {})
        is None
    )
    selected = select_profile(
        "rollback", {"target": "deployment-id", "base_dir": str(tmp_path)}, {}
    )
    assert selected is not None
    assert selected.owner == config
    assert selected.kubeconfig == deployer
