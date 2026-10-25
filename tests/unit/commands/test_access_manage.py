"""Mock-only CLI regressions for human access initialization and revocation."""

import base64
import json
import logging
import stat
import subprocess
from pathlib import Path
from unittest.mock import patch

import pytest
import yaml
from click.testing import CliRunner

from sbkube.cli import main
from sbkube.utils.deploy_gate import DeployGateError

CTX = "cluster-a"
SERVER = "https://127.0.0.1:6443"
CA = b"public-server-ca"
SENTINEL = "NEVER-PRINT-READONLY-TOKEN"
TTY = "sbkube.commands.access_manage._is_interactive"


def _proc(rc: int = 0, out: str = "", err: str = "") -> subprocess.CompletedProcess:
    return subprocess.CompletedProcess([], rc, stdout=out, stderr=err)


def _admin(path: Path) -> None:
    path.write_text(
        yaml.safe_dump(
            {
                "apiVersion": "v1",
                "kind": "Config",
                "clusters": [
                    {
                        "name": "cluster",
                        "cluster": {
                            "server": SERVER,
                            "certificate-authority-data": base64.b64encode(CA).decode(),
                        },
                    }
                ],
                "contexts": [
                    {"name": CTX, "context": {"cluster": "cluster", "user": "admin"}}
                ],
                "current-context": CTX,
                "users": [{"name": "admin", "user": {"client-key-data": "PRIVATE"}}],
            },
            sort_keys=False,
        )
    )


@pytest.fixture
def env(tmp_path: Path) -> dict[str, Path]:
    admin = tmp_path / "admin"
    _admin(admin)
    readonly, deployer, token_dir = (
        tmp_path / "readonly",
        tmp_path / "deployer",
        tmp_path / "tokens",
    )
    config = tmp_path / "sbkube.yaml"
    config.write_text(
        yaml.safe_dump(
            {
                "apiVersion": "sbkube/v1",
                "metadata": {"name": "test"},
                "settings": {
                    "kubeconfig": str(admin),
                    "kubeconfig_context": CTX,
                    "access": {
                        "namespace": "agent-access",
                        "token_dir": str(token_dir),
                        "readonly": {"kubeconfig": str(readonly)},
                        "deployer": {"kubeconfig": str(deployer)},
                    },
                },
                "apps": {},
            },
            sort_keys=False,
        )
    )
    return {
        "admin": admin,
        "readonly": readonly,
        "deployer": deployer,
        "token_dir": token_dir,
        "config": config,
        "tmp": tmp_path,
    }


def _access(env: dict[str, Path], command: str, *args: str):
    return CliRunner().invoke(
        main,
        ["access", command, "-f", str(env["config"]), *args],
        env={"COLUMNS": "200"},
    )


def _secret() -> str:
    return json.dumps(
        {
            "kind": "Secret",
            "type": "kubernetes.io/service-account-token",
            "metadata": {
                "name": "agent-readonly-token",
                "namespace": "agent-access",
                "annotations": {"kubernetes.io/service-account.name": "agent-readonly"},
            },
            "data": {"token": base64.b64encode(SENTINEL.encode()).decode()},
        }
    )


def _init_run(calls: list[list[str]]):
    """A shared `subprocess.run` fake: only public apply and secret JSON are returned."""

    def run(command, **kwargs):
        calls.append(list(command))
        assert kwargs.get("shell") is None
        if "apply" in command:
            assert "apiVersion: v1" in kwargs["input"]
            return _proc()
        if "get" in command and "secret" in command:
            return _proc(out=_secret())
        raise AssertionError(f"unexpected subprocess call: {command}")

    return run


def _mode(path: Path) -> int:
    return stat.S_IMODE(path.stat().st_mode)


def _all_text(result, caplog: pytest.LogCaptureFixture) -> str:
    return str(result.output) + str(result.exception or "") + caplog.text


def test_init_print_is_public_and_needs_neither_tty_nor_cluster(
    env: dict[str, Path],
) -> None:
    with patch("subprocess.run") as run:
        result = _access(env, "init", "--print")
    assert result.exit_code == 0, result.output
    assert result.output.count("---") == 7
    assert "kind: Namespace" in result.output
    assert "kind: ClusterRole" in result.output
    run.assert_not_called()
    assert not env["token_dir"].exists()


def test_init_refuses_non_tty_before_cluster_calls(env: dict[str, Path]) -> None:
    with patch(TTY, return_value=False), patch("subprocess.run") as run:
        result = _access(env, "init")
    assert result.exit_code != 0
    assert "interactive terminal" in result.output
    run.assert_not_called()


def test_init_local_admin_writes_private_credentials_without_token_leak(
    env: dict[str, Path], caplog: pytest.LogCaptureFixture
) -> None:
    caplog.set_level(logging.DEBUG)
    calls: list[list[str]] = []
    with (
        patch(TTY, return_value=True),
        patch("subprocess.run", side_effect=_init_run(calls)),
    ):
        result = _access(env, "init")
    assert result.exit_code == 0, result.output
    readonly_token = env["token_dir"] / "readonly.token"
    assert readonly_token.read_text().strip() == SENTINEL
    assert (
        _mode(readonly_token)
        == _mode(env["readonly"])
        == _mode(env["deployer"])
        == 0o600
    )
    assert _mode(env["token_dir"]) == 0o700
    readonly = yaml.safe_load(env["readonly"].read_text())
    deployer = yaml.safe_load(env["deployer"].read_text())
    assert readonly["users"][0]["name"] == "readonly"
    assert deployer["users"][0]["name"] == "deploy"
    assert (
        SENTINEL
        not in _all_text(result, caplog)
        + env["readonly"].read_text()
        + env["deployer"].read_text()
    )
    assert len(calls) == 3


def test_init_reruns_over_its_generated_outputs(env: dict[str, Path]) -> None:
    for _ in range(2):
        calls: list[list[str]] = []
        with (
            patch(TTY, return_value=True),
            patch("subprocess.run", side_effect=_init_run(calls)),
        ):
            result = _access(env, "init")
        assert result.exit_code == 0, result.output
        assert len(calls) == 3


@pytest.mark.parametrize(
    "change",
    [
        {"type": "Opaque"},
        {"metadata": {"name": "wrong", "namespace": "agent-access"}},
        {
            "metadata": {
                "name": "agent-readonly-token",
                "namespace": "agent-access",
                "annotations": {"kubernetes.io/service-account.name": "wrong"},
            }
        },
    ],
)
def test_init_refuses_wrong_existing_secret_before_apply(
    env: dict[str, Path], change: dict
) -> None:
    secret = json.loads(_secret())
    secret.update(change)
    calls: list[list[str]] = []

    def run(command, **kwargs):
        calls.append(list(command))
        assert "apply" not in command
        return _proc(out=json.dumps(secret))

    with patch(TTY, return_value=True), patch("subprocess.run", side_effect=run):
        result = _access(env, "init")
    assert result.exit_code != 0
    assert "Secret" in result.output
    assert len(calls) == 1
    assert not env["token_dir"].exists()


@pytest.mark.parametrize(
    "kind", ["inline-token", "client-cert", "cross-role", "symlink", "ca-collision"]
)
def test_init_refuses_unsafe_output_before_subprocess(
    env: dict[str, Path], kind: str
) -> None:
    config = yaml.safe_load(env["config"].read_text())
    if kind == "inline-token":
        env["readonly"].write_text(
            yaml.safe_dump(
                {"users": [{"name": "readonly", "user": {"token": "manual"}}]}
            )
        )
    elif kind == "client-cert":
        env["readonly"].write_text(
            yaml.safe_dump(
                {
                    "users": [
                        {
                            "name": "readonly",
                            "user": {"client-certificate-data": "manual"},
                        }
                    ]
                }
            )
        )
    elif kind == "cross-role":
        config["settings"]["access"]["deployer"]["kubeconfig"] = str(env["readonly"])
    elif kind == "symlink":
        env["deployer"].symlink_to(env["readonly"])
    else:
        token = env["token_dir"] / "readonly.token"
        token.parent.mkdir()
        token.write_text("public-ca")
        env["readonly"].write_text(
            yaml.safe_dump(
                {
                    "clusters": [
                        {
                            "name": "cluster",
                            "cluster": {
                                "server": SERVER,
                                "certificate-authority": str(token),
                            },
                        }
                    ],
                    "contexts": [{"name": CTX, "context": {"cluster": "cluster"}}],
                    "users": [],
                }
            )
        )
    env["config"].write_text(yaml.safe_dump(config))
    with patch(TTY, return_value=True), patch("subprocess.run") as run:
        result = _access(env, "init")
    assert result.exit_code != 0
    run.assert_not_called()


def test_init_node_bootstrap_descriptor_needs_no_local_admin(
    env: dict[str, Path],
) -> None:
    config = yaml.safe_load(env["config"].read_text())
    config["settings"].pop("kubeconfig")
    config["settings"]["access"]["admin"] = {
        "ssh_host": "operator@node",
        "expected_hostname": "node1",
    }
    env["config"].write_text(yaml.safe_dump(config))
    env["readonly"].write_text(
        yaml.safe_dump(
            {
                "clusters": [
                    {
                        "name": "cluster",
                        "cluster": {
                            "server": SERVER,
                            "certificate-authority-data": base64.b64encode(CA).decode(),
                        },
                    }
                ],
                "contexts": [{"name": CTX, "context": {"cluster": "cluster"}}],
                "users": [],
            }
        )
    )
    env["admin"].unlink()
    output = iter(["node1\n", base64.b64encode(CA).decode(), _secret(), "", _secret()])

    def run(command, **kwargs):
        assert command[0] == "ssh"
        return _proc(out=next(output))

    with (
        patch(TTY, return_value=True),
        patch("subprocess.run", side_effect=run) as remote,
    ):
        result = _access(env, "init")
    assert result.exit_code == 0, result.output
    assert remote.call_count == 5
    assert env["token_dir"].joinpath("readonly.token").read_text().strip() == SENTINEL


def test_init_node_allows_root_readonly_source_for_bootstrap_and_repeat(
    env: dict[str, Path],
) -> None:
    config = yaml.safe_load(env["config"].read_text())
    config["settings"]["kubeconfig"] = str(env["readonly"])
    config["settings"]["access"]["admin"] = {
        "ssh_host": "operator@node",
        "expected_hostname": "node1",
    }
    env["config"].write_text(yaml.safe_dump(config))
    env["readonly"].write_text(
        yaml.safe_dump(
            {
                "clusters": [
                    {
                        "name": "cluster",
                        "cluster": {
                            "server": SERVER,
                            "certificate-authority-data": base64.b64encode(CA).decode(),
                        },
                    }
                ],
                "contexts": [{"name": CTX, "context": {"cluster": "cluster"}}],
                "users": [],
            }
        )
    )
    env["admin"].unlink()

    for _ in range(2):
        output = iter(
            ["node1\n", base64.b64encode(CA).decode(), _secret(), "", _secret()]
        )

        def run(command, output=output, **kwargs):
            assert command[0] == "ssh"
            return _proc(out=next(output))

        with (
            patch(TTY, return_value=True),
            patch("subprocess.run", side_effect=run) as remote,
        ):
            result = _access(env, "init")
        assert result.exit_code == 0, result.output
        assert remote.call_count == 5
    assert env["token_dir"].joinpath("readonly.token").read_text().strip() == SENTINEL


def test_revoke_requires_explicit_profile(env: dict[str, Path]) -> None:
    result = _access(env, "revoke")
    assert result.exit_code != 0
    assert "--profile" in result.output


def test_revoke_readonly_deletes_only_its_secret(env: dict[str, Path]) -> None:
    calls: list[list[str]] = []

    def run(command, **kwargs):
        calls.append(list(command))
        if "get" in command:
            return _proc(out=_secret())
        return _proc()

    with patch(TTY, return_value=True), patch("subprocess.run", side_effect=run):
        result = _access(env, "revoke", "--profile", "readonly")
    assert result.exit_code == 0, result.output
    assert len(calls) == 2
    assert calls[0][-5:] == [
        "secret",
        "agent-readonly-token",
        "--ignore-not-found",
        "-o",
        "json",
    ]
    assert calls[1][-6:] == [
        "delete",
        "secret",
        "agent-readonly-token",
        "--ignore-not-found",
        "--wait=true",
        "--timeout=20s",
    ]


def test_revoke_readonly_refuses_foreign_secret_before_delete(
    env: dict[str, Path],
) -> None:
    secret = json.loads(_secret())
    secret["metadata"]["annotations"]["kubernetes.io/service-account.name"] = "foreign"
    calls: list[list[str]] = []

    def run(command, **kwargs):
        calls.append(list(command))
        assert "delete" not in command
        return _proc(out=json.dumps(secret))

    with patch(TTY, return_value=True), patch("subprocess.run", side_effect=run):
        result = _access(env, "revoke", "--profile", "readonly")
    assert result.exit_code != 0
    assert "Secret" in result.output
    assert len(calls) == 1


def test_revoke_deployer_preserves_metadata_but_replaces_identity(
    env: dict[str, Path],
) -> None:
    calls: list[tuple[list[str], dict]] = []
    service_account = {
        "apiVersion": "v1",
        "kind": "ServiceAccount",
        "metadata": {
            "name": "sbkube-deployer",
            "namespace": "agent-access",
            "uid": "old",
            "resourceVersion": "9",
            "labels": {"keep": "yes"},
        },
        "imagePullSecrets": [{"name": "registry"}],
        "secrets": [{"name": "old-token"}],
    }

    def run(command, **kwargs):
        calls.append((list(command), kwargs))
        if "get" in command:
            return _proc(out=json.dumps(service_account))
        return _proc()

    with patch(TTY, return_value=True), patch("subprocess.run", side_effect=run):
        result = _access(env, "revoke", "--profile", "deployer")
    assert result.exit_code == 0, result.output
    assert ["get", "serviceaccount"] == calls[0][0][-6:-4]
    assert "delete" in calls[1][0]
    assert "create" in calls[2][0]
    replacement = yaml.safe_load(calls[2][1]["input"])
    assert replacement["metadata"]["labels"] == {"keep": "yes"}
    assert replacement["imagePullSecrets"] == [{"name": "registry"}]
    assert "uid" not in replacement["metadata"]
    assert "resourceVersion" not in replacement["metadata"]
    assert "secrets" not in replacement


def test_revoke_reports_deployer_partial_state(env: dict[str, Path]) -> None:
    calls = 0

    def run(command, **kwargs):
        nonlocal calls
        calls += 1
        if "get" in command:
            return _proc(
                out=json.dumps(
                    {
                        "kind": "ServiceAccount",
                        "metadata": {
                            "name": "sbkube-deployer",
                            "namespace": "agent-access",
                        },
                    }
                )
            )
        if "create" in command:
            return _proc(rc=1, err="SECRET")
        return _proc()

    with patch(TTY, return_value=True), patch("subprocess.run", side_effect=run):
        result = _access(env, "revoke", "--profile", "deployer")
    assert result.exit_code != 0
    assert "deleted, but recreation failed" in result.output
    assert "SECRET" not in result.output
    assert calls == 3


def test_gate_refusal_prevents_init_subprocess(env: dict[str, Path]) -> None:
    with (
        patch(TTY, return_value=True),
        patch(
            "sbkube.utils.deploy_gate.run_gate",
            side_effect=DeployGateError("gate denied"),
        ),
        patch("subprocess.run") as run,
    ):
        result = _access(env, "init")
    assert result.exit_code != 0
    assert "gate denied" in str(result.exception)
    run.assert_not_called()
