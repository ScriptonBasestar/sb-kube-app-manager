"""Tests for ``sbkube access issue`` (kubectl is always mocked)."""

import logging
import os
import stat
import subprocess
from pathlib import Path
from unittest.mock import patch

import pytest
import yaml
from click.testing import CliRunner

from sbkube.cli import main
from sbkube.utils import access_issue

SERVER = "https://10.0.0.1:6443"
CTX = "prod"
SENTINEL = "SENTINELTOKENVALUE123"
ADMIN_CERT = "ADMINCERTDATA"
ADMIN_KEY = "ADMINKEYDATA"
RUN = "sbkube.utils.access_issue.subprocess.run"
TTY = "sbkube.commands.access_issue._is_interactive"


def _admin(path: Path, cluster: dict | None = None) -> Path:
    path.write_text(
        yaml.safe_dump(
            {
                "apiVersion": "v1",
                "kind": "Config",
                "current-context": CTX,
                "clusters": [
                    {
                        "name": "c",
                        "cluster": cluster
                        or {
                            "server": SERVER,
                            "certificate-authority-data": "Q0E=",
                            "tls-server-name": "kube.example",
                            "proxy-url": "http://proxy:3128",
                            "insecure-skip-tls-verify": False,
                            "extensions": [{"name": "drop-me"}],
                        },
                    }
                ],
                "contexts": [{"name": CTX, "context": {"cluster": "c", "user": "adm"}}],
                "users": [
                    {
                        "name": "adm",
                        "user": {
                            "client-certificate-data": ADMIN_CERT,
                            "client-key-data": ADMIN_KEY,
                        },
                    }
                ],
            }
        )
    )
    return path


def _proc(rc: int, out: str = "", err: str = "") -> subprocess.CompletedProcess:
    return subprocess.CompletedProcess([], rc, stdout=out, stderr=err)


def _kubectl(
    token: str = SENTINEL + "\n", can_i: str = "yes", calls: list | None = None
):
    def fake(command, **kwargs):
        if calls is not None:
            calls.append(list(command))
        assert kwargs.get("shell") is None
        if "token" in command:
            return _proc(0, token)
        return _proc(0 if can_i == "yes" else 1, can_i + "\n")

    return fake


@pytest.fixture
def env(tmp_path: Path) -> dict:
    admin = _admin(tmp_path / "admin")
    readonly = tmp_path / "readonly"
    readonly.write_text("{}")
    deploy = tmp_path / "deploy"
    token_dir = tmp_path / "tokens"
    config = tmp_path / "sbkube.yaml"
    config.write_text(
        yaml.safe_dump(
            {
                "apiVersion": "sbkube/v1",
                "metadata": {"name": "t"},
                "settings": {
                    "kubeconfig": str(admin),
                    "kubeconfig_context": CTX,
                    "access": {
                        "namespace": "agent-access",
                        "token_dir": str(token_dir),
                        "readonly": {"kubeconfig": str(readonly)},
                        "deployer": {"kubeconfig": str(deploy), "token_ttl": "2h"},
                    },
                },
                "apps": {},
            }
        )
    )
    return {
        "admin": admin,
        "readonly": readonly,
        "deploy": deploy,
        "token": token_dir / "deploy.token",
        "token_dir": token_dir,
        "config": config,
        "tmp": tmp_path,
    }


def _issue(env: dict, *extra: str, globals_: tuple[str, ...] = ()):
    return CliRunner().invoke(
        main,
        [*globals_, "access", "issue", "-f", str(env["config"]), *extra],
        env={"COLUMNS": "200"},
    )


def _mode(path: Path) -> int:
    return stat.S_IMODE(path.stat().st_mode)


def _all_text(result) -> str:
    return result.output + str(result.exception or "")


def _node_config(env: dict) -> None:
    config = yaml.safe_load(env["config"].read_text())
    config["settings"].pop("kubeconfig")
    config["settings"]["access"]["admin"] = {
        "ssh_host": "operator@node-lan",
        "expected_hostname": "node1",
    }
    env["config"].write_text(yaml.safe_dump(config))
    _admin(env["readonly"])
    data = yaml.safe_load(env["readonly"].read_text())
    data["users"] = [
        {"name": "adm", "user": {"tokenFile": str(env["tmp"] / "readonly.token")}}
    ]
    env["readonly"].write_text(yaml.safe_dump(data))
    env["admin"].unlink()


def test_node_issue_without_local_admin(
    env: dict, caplog: pytest.LogCaptureFixture
) -> None:
    _node_config(env)
    calls: list = []
    caplog.set_level(logging.DEBUG)
    outputs = iter([_proc(0, "node1\n"), _proc(0, "Q0E="), _proc(0, SENTINEL)])

    def command_run(command, **kwargs):
        if command[0] == "ssh":
            return next(outputs)
        return _kubectl(calls=calls)(command, **kwargs)

    with (
        patch(TTY, return_value=True),
        patch(
            "sbkube.utils.access_admin.subprocess.run",
            side_effect=command_run,
        ) as remote,
    ):
        result = _issue(env)
    assert result.exit_code == 0, result.output
    assert remote.call_count == 4
    assert env["token"].read_text().strip() == SENTINEL
    assert SENTINEL not in _all_text(result) + caplog.text + env["deploy"].read_text()
    assert ADMIN_KEY not in env["deploy"].read_text()
    assert str(env["readonly"]) not in remote.call_args_list[2].args[0][-1]
    assert (
        yaml.safe_load(env["deploy"].read_text())["clusters"][0]["cluster"]["server"]
        == SERVER
    )


def test_node_issue_ca_mismatch_leaves_files_absent(env: dict) -> None:
    _node_config(env)
    with (
        patch(TTY, return_value=True),
        patch(
            "sbkube.utils.access_admin.subprocess.run",
            side_effect=[_proc(0, "node1"), _proc(0, "Tk9UQ0E=")],
        ) as remote,
    ):
        result = _issue(env)
    assert result.exit_code != 0
    assert "CA does not match" in result.output
    assert remote.call_count == 2
    assert not env["token_dir"].exists()
    assert not env["deploy"].exists()


def test_node_issue_collision_stops_before_ssh(env: dict) -> None:
    _node_config(env)
    config = yaml.safe_load(env["config"].read_text())
    config["settings"]["access"]["deployer"]["kubeconfig"] = str(env["readonly"])
    env["config"].write_text(yaml.safe_dump(config))
    with (
        patch(TTY, return_value=True),
        patch("sbkube.utils.access_admin.subprocess.run") as remote,
    ):
        result = _issue(env)
    assert result.exit_code != 0
    remote.assert_not_called()


@pytest.mark.parametrize("ref", ["deploy.token", "~/deploy.token"])
def test_ca_file_collision_is_protected(env: dict, ref: str) -> None:
    ca_parent = env["tmp"] / "~" if ref.startswith("~") else env["tmp"]
    ca_parent.mkdir(exist_ok=True)
    ca_file = ca_parent / "deploy.token"
    ca_file.write_text("public-ca")
    data = yaml.safe_load(env["admin"].read_text())
    data["clusters"][0]["cluster"] = {"server": SERVER, "certificate-authority": ref}
    env["admin"].write_text(yaml.safe_dump(data))
    config = yaml.safe_load(env["config"].read_text())
    config["settings"]["access"]["token_dir"] = str(ca_parent)
    env["config"].write_text(yaml.safe_dump(config))
    with patch(TTY, return_value=True), patch(RUN) as run:
        result = _issue(env)
    assert result.exit_code != 0
    assert "must not be" in result.output
    run.assert_not_called()
    assert ca_file.read_text() == "public-ca"


# --- guards ----------------------------------------------------------------


def test_refuses_without_tty(env: dict) -> None:
    with patch(RUN) as run:
        result = _issue(env)
    assert result.exit_code != 0
    assert "interactive terminal" in result.output
    run.assert_not_called()
    assert not env["token_dir"].exists()
    assert not env["deploy"].exists()


@pytest.mark.parametrize("ttl", ["5m", "599s", "1h1h", "abc", "0"])
def test_ttl_validation(env: dict, ttl: str) -> None:
    with patch(TTY, return_value=True), patch(RUN) as run:
        result = _issue(env, "--ttl", ttl)
    assert result.exit_code != 0
    assert "--ttl" in result.output
    run.assert_not_called()


def test_same_path_refusals(env: dict) -> None:
    for role in ("admin", "readonly"):
        config = yaml.safe_load(env["config"].read_text())
        config["settings"]["access"]["deployer"]["kubeconfig"] = str(env[role])
        env["config"].write_text(yaml.safe_dump(config))
        with patch(TTY, return_value=True), patch(RUN) as run:
            result = _issue(env)
        assert result.exit_code != 0, role
        assert f"must not be the {role} kubeconfig" in result.output
        run.assert_not_called()
    assert "client-certificate-data" in env["admin"].read_text()


def test_same_path_via_symlink(env: dict) -> None:
    link = env["tmp"] / "link"
    link.symlink_to(env["admin"])
    config = yaml.safe_load(env["config"].read_text())
    config["settings"]["access"]["deployer"]["kubeconfig"] = str(link)
    env["config"].write_text(yaml.safe_dump(config))
    with patch(TTY, return_value=True), patch(RUN) as run:
        result = _issue(env)
    assert result.exit_code != 0
    run.assert_not_called()


# --- happy path ------------------------------------------------------------


def test_issue_writes_files_and_hides_token(
    env: dict, caplog: pytest.LogCaptureFixture
) -> None:
    calls: list = []
    caplog.set_level(logging.DEBUG)
    with patch(TTY, return_value=True), patch(RUN, side_effect=_kubectl(calls=calls)):
        result = _issue(env)

    assert result.exit_code == 0, result.output
    mint = calls[0]
    assert mint == [
        "kubectl",
        "--kubeconfig",
        str(env["admin"]),
        "--context",
        CTX,
        "-n",
        "agent-access",
        "create",
        "token",
        "sbkube-deployer",
        "--duration",
        "2h",
    ]
    assert SENTINEL not in " ".join(" ".join(c) for c in calls)
    assert env["token"].read_text() == SENTINEL + "\n"
    assert _mode(env["token"]) == 0o600
    assert _mode(env["token_dir"]) == 0o700
    assert _mode(env["deploy"]) == 0o600
    canai = calls[-1]
    assert canai[1:5] == ["--kubeconfig", str(env["deploy"]), "--context", CTX]
    assert canai[-4:] == ["can-i", "create", "deployments.apps", "-A"]
    for text in (_all_text(result), caplog.text, env["deploy"].read_text()):
        assert SENTINEL not in text
    assert "UTC" in result.output
    assert "expires" in result.output
    assert not [p for p in env["token_dir"].iterdir() if p.name.endswith(".tmp")]


def test_ttl_override_is_passed_to_kubectl(env: dict) -> None:
    calls: list = []
    with patch(TTY, return_value=True), patch(RUN, side_effect=_kubectl(calls=calls)):
        result = _issue(env, "--ttl", "45m")
    assert result.exit_code == 0, result.output
    assert calls[0][-2:] == ["--duration", "45m"]


def test_global_context_and_kubeconfig_override(env: dict) -> None:
    other = _admin(env["tmp"] / "other")
    data = yaml.safe_load(other.read_text())
    data["contexts"][0]["name"] = "staging"
    other.write_text(yaml.safe_dump(data))
    calls: list = []
    with patch(TTY, return_value=True), patch(RUN, side_effect=_kubectl(calls=calls)):
        result = _issue(
            env, globals_=("--kubeconfig", str(other), "--context", "staging")
        )
    assert result.exit_code == 0, result.output
    assert calls[0][1:5] == ["--kubeconfig", str(other), "--context", "staging"]
    written = yaml.safe_load(env["deploy"].read_text())
    assert written["current-context"] == "staging"


def test_generated_kubeconfig_content(env: dict) -> None:
    with patch(TTY, return_value=True), patch(RUN, side_effect=_kubectl()):
        assert _issue(env).exit_code == 0
    data = yaml.safe_load(env["deploy"].read_text())

    assert data["current-context"] == CTX
    assert data["contexts"] == [
        {"name": CTX, "context": {"cluster": "c", "user": "deploy"}}
    ]
    assert data["clusters"] == [
        {
            "name": "c",
            "cluster": {
                "server": SERVER,
                "certificate-authority-data": "Q0E=",
                "tls-server-name": "kube.example",
                "proxy-url": "http://proxy:3128",
                "insecure-skip-tls-verify": False,
            },
        }
    ]
    user = data["users"]
    assert user == [{"name": "deploy", "user": {"tokenFile": str(env["token"])}}]
    assert Path(user[0]["user"]["tokenFile"]).is_absolute()
    text = env["deploy"].read_text()
    assert ADMIN_CERT not in text
    assert ADMIN_KEY not in text


def test_relative_ca_path_becomes_absolute(env: dict) -> None:
    _admin(env["admin"], {"server": SERVER, "certificate-authority": "ca.crt"})
    with patch(TTY, return_value=True), patch(RUN, side_effect=_kubectl()):
        assert _issue(env).exit_code == 0
    cluster = yaml.safe_load(env["deploy"].read_text())["clusters"][0]["cluster"]
    assert cluster["certificate-authority"] == str(env["admin"].parent / "ca.crt")


# --- failures write nothing ------------------------------------------------


def test_kubectl_failure_writes_nothing(env: dict) -> None:
    fail = _proc(1, "", 'error: serviceaccounts "sbkube-deployer" not found\nmore')
    with patch(TTY, return_value=True), patch(RUN, return_value=fail):
        result = _issue(env)
    assert result.exit_code != 0
    assert "not found" in result.output
    assert "more" not in result.output
    assert not env["token_dir"].exists()
    assert not env["deploy"].exists()


@pytest.mark.parametrize("token", ["", "\n", "   \n", "two parts\n", "a\nb\n"])
def test_bad_token_output_is_refused(env: dict, token: str) -> None:
    with patch(TTY, return_value=True), patch(RUN, side_effect=_kubectl(token=token)):
        result = _issue(env)
    assert result.exit_code != 0
    assert "token not issued" in result.output
    assert not env["token_dir"].exists()
    assert not env["deploy"].exists()
    assert "two parts" not in _all_text(result)


@pytest.mark.parametrize(
    "error", [FileNotFoundError(), subprocess.TimeoutExpired("kubectl", 30)]
)
def test_kubectl_missing_or_timeout(env: dict, error: Exception) -> None:
    with patch(TTY, return_value=True), patch(RUN, side_effect=error):
        result = _issue(env)
    assert result.exit_code != 0
    assert not env["deploy"].exists()


def test_failed_write_keeps_old_files(tmp_path: Path) -> None:
    target = tmp_path / "f"
    target.write_text("old")
    with (
        patch("sbkube.utils.access_issue.os.replace", side_effect=OSError("boom")),
        pytest.raises(access_issue.TokenIssueError),
    ):
        access_issue.write_private_file(target, "new")
    assert target.read_text() == "old"
    assert not [p for p in tmp_path.iterdir() if p.name.endswith(".tmp")]


def test_write_private_file_modes_and_replace(tmp_path: Path) -> None:
    target = tmp_path / "f"
    target.write_text("old")
    target.chmod(0o644)
    access_issue.write_private_file(target, "new")
    assert target.read_text() == "new"
    assert _mode(target) == 0o600


def test_loose_existing_token_dir_is_refused_not_chmoded(env: dict) -> None:
    env["token_dir"].mkdir()
    env["token_dir"].chmod(0o755)
    with patch(TTY, return_value=True), patch(RUN) as run:
        result = _issue(env)
    assert result.exit_code != 0
    assert "chmod 700" in result.output
    assert _mode(env["token_dir"]) == 0o755
    run.assert_not_called()
    assert not env["deploy"].exists()


def test_private_existing_token_dir_is_accepted(env: dict) -> None:
    env["token_dir"].mkdir()
    env["token_dir"].chmod(0o700)
    with patch(TTY, return_value=True), patch(RUN, side_effect=_kubectl()):
        assert _issue(env).exit_code == 0


def test_unwritable_deployer_dir_is_refused_before_mint(env: dict) -> None:
    config = yaml.safe_load(env["config"].read_text())
    missing = env["tmp"] / "nope" / "deploy"
    config["settings"]["access"]["deployer"]["kubeconfig"] = str(missing)
    env["config"].write_text(yaml.safe_dump(config))
    with patch(TTY, return_value=True), patch(RUN) as run:
        result = _issue(env)
    assert result.exit_code != 0
    run.assert_not_called()
    assert not env["token_dir"].exists()


def test_kubeconfig_write_failure_reports_token_written(env: dict) -> None:
    real = access_issue.write_private_file

    def flaky(path: Path, content: str) -> None:
        if path == env["deploy"]:
            raise access_issue.TokenIssueError("disk full")
        real(path, content)

    with (
        patch(TTY, return_value=True),
        patch(RUN, side_effect=_kubectl()),
        patch("sbkube.commands.access_issue.write_private_file", side_effect=flaky),
    ):
        result = _issue(env)
    assert result.exit_code != 0
    assert "token WAS written" in result.output
    assert str(env["token"]) in result.output
    assert env["token"].exists()
    assert SENTINEL not in _all_text(result)


def test_token_dir_that_is_a_file_is_refused(env: dict) -> None:
    env["token_dir"].write_text("not a dir")
    with patch(TTY, return_value=True), patch(RUN, side_effect=_kubectl()):
        result = _issue(env)
    assert result.exit_code != 0
    assert "token not issued" in result.output
    assert not env["deploy"].exists()
    assert SENTINEL not in _all_text(result)


# --- overwrite rule --------------------------------------------------------


def _existing(
    path: Path, user_body: dict | None, extra_users: list | None = None
) -> None:
    users = [] if user_body is None else [{"name": "deploy", "user": user_body}]
    path.write_text(
        yaml.safe_dump(
            {"apiVersion": "v1", "kind": "Config", "users": users + (extra_users or [])}
        )
    )


@pytest.mark.parametrize(
    "body",
    [
        {"client-certificate-data": "x", "client-key-data": "y"},
        {"token": "abc"},
        {"exec": {"command": "gke-gcloud-auth-plugin"}},
        {"auth-provider": {"name": "gcp"}},
        {"username": "u", "password": "p"},
        {"tokenFile": "/t", "token": "abc"},
        {"tokenFile": "/t", "client-key": "/k"},
        {},
    ],
)
def test_refuses_to_overwrite_non_generated(env: dict, body: dict) -> None:
    _existing(env["deploy"], body)
    before = env["deploy"].read_text()
    with patch(TTY, return_value=True), patch(RUN) as run:
        result = _issue(env)
    assert result.exit_code != 0
    assert "refusing to overwrite" in result.output
    assert env["deploy"].read_text() == before
    run.assert_not_called()


def test_refuses_when_any_user_is_not_token_file_only(env: dict) -> None:
    _existing(
        env["deploy"],
        {"tokenFile": "/t"},
        [{"name": "adm", "user": {"client-key-data": "k"}}],
    )
    with patch(TTY, return_value=True), patch(RUN) as run:
        result = _issue(env)
    assert result.exit_code != 0
    run.assert_not_called()


@pytest.mark.parametrize("content", ["", "just text: [", "- a\n- b\n"])
def test_refuses_unparseable_existing_file(env: dict, content: str) -> None:
    env["deploy"].write_text(content)
    with patch(TTY, return_value=True), patch(RUN) as run:
        result = _issue(env)
    assert result.exit_code != 0
    assert env["deploy"].read_text() == content
    run.assert_not_called()


def test_overwrites_generated_shape(env: dict) -> None:
    _existing(env["deploy"], {"tokenFile": str(env["token"])})
    with patch(TTY, return_value=True), patch(RUN, side_effect=_kubectl()):
        result = _issue(env)
    assert result.exit_code == 0, result.output
    data = yaml.safe_load(env["deploy"].read_text())
    assert data["users"][0]["user"]["tokenFile"] == str(env["token"])


def test_overwrites_manual_handoff_shape_via_symlinked_token_path(env: dict) -> None:
    real_dir = env["tmp"] / "real"
    real_dir.mkdir(mode=0o700)
    real_dir.chmod(0o700)
    (real_dir / "deploy.token").write_text("old\n")
    _existing(env["deploy"], {"tokenFile": str(real_dir / "deploy.token")})
    env["token_dir"].symlink_to(real_dir)
    with patch(TTY, return_value=True), patch(RUN, side_effect=_kubectl()):
        result = _issue(env)
    assert result.exit_code == 0, result.output


def test_refuses_overwrite_when_token_file_points_elsewhere(env: dict) -> None:
    _existing(env["deploy"], {"tokenFile": "/old/path/deploy.token"})
    with patch(TTY, return_value=True), patch(RUN) as run:
        result = _issue(env)
    assert result.exit_code != 0
    assert "refusing to overwrite" in result.output
    run.assert_not_called()


def test_refuses_overwrite_of_wrong_user_name_or_two_users(env: dict) -> None:
    for users in (
        [{"name": "other", "user": {"tokenFile": str(env["token"])}}],
        [
            {"name": "deploy", "user": {"tokenFile": str(env["token"])}},
            {"name": "second", "user": {"tokenFile": str(env["token"])}},
        ],
    ):
        env["deploy"].write_text(yaml.safe_dump({"users": users}))
        with patch(TTY, return_value=True), patch(RUN) as run:
            result = _issue(env)
        assert result.exit_code != 0
        run.assert_not_called()


def test_relative_token_file_in_existing_kubeconfig_resolves_against_it(
    env: dict,
) -> None:
    _existing(env["deploy"], {"tokenFile": "tokens/deploy.token"})
    with patch(TTY, return_value=True), patch(RUN, side_effect=_kubectl()):
        assert _issue(env).exit_code == 0


# --- token / deployer path collisions with referenced credentials ------------


def _set_user(path: Path, user: dict) -> None:
    data = yaml.safe_load(path.read_text())
    data["users"] = [{"name": "adm", "user": user}]
    path.write_text(yaml.safe_dump(data))


def test_readonly_token_file_equal_to_token_path_is_refused(env: dict) -> None:
    env["readonly"].write_text(
        yaml.safe_dump(
            {"users": [{"name": "ro", "user": {"tokenFile": str(env["token"])}}]}
        )
    )
    with patch(TTY, return_value=True), patch(RUN) as run:
        result = _issue(env)
    assert result.exit_code != 0
    assert "credential file of the readonly kubeconfig" in result.output
    run.assert_not_called()
    assert not env["token_dir"].exists()


def test_admin_credential_files_are_protected(env: dict) -> None:
    for key in ("tokenFile", "client-key", "client-certificate"):
        _admin(env["admin"])
        _set_user(env["admin"], {key: str(env["token"])})
        with patch(TTY, return_value=True), patch(RUN) as run:
            result = _issue(env)
        assert result.exit_code != 0, key
        assert "credential file of the admin kubeconfig" in result.output
        run.assert_not_called()


def test_admin_credential_file_equal_to_deployer_path_is_refused(env: dict) -> None:
    _set_user(env["admin"], {"client-key": str(env["deploy"])})
    with patch(TTY, return_value=True), patch(RUN) as run:
        result = _issue(env)
    assert result.exit_code != 0
    run.assert_not_called()


def test_relative_credential_path_resolves_against_its_kubeconfig(env: dict) -> None:
    rel = os.path.relpath(env["token"], env["readonly"].parent)
    env["readonly"].write_text(
        yaml.safe_dump({"users": [{"name": "ro", "user": {"tokenFile": rel}}]})
    )
    with patch(TTY, return_value=True), patch(RUN) as run:
        result = _issue(env)
    assert result.exit_code != 0
    run.assert_not_called()


def test_credential_reference_through_symlink_is_refused(env: dict) -> None:
    link = env["tmp"] / "alias.token"
    env["token_dir"].mkdir(mode=0o700)
    env["token"].write_text("x\n")
    link.symlink_to(env["token"])
    env["readonly"].write_text(
        yaml.safe_dump({"users": [{"name": "ro", "user": {"tokenFile": str(link)}}]})
    )
    with patch(TTY, return_value=True), patch(RUN) as run:
        result = _issue(env)
    assert result.exit_code != 0
    run.assert_not_called()


def test_unreadable_existing_readonly_kubeconfig_is_refused(env: dict) -> None:
    env["readonly"].write_text("just text: [")
    with patch(TTY, return_value=True), patch(RUN) as run:
        result = _issue(env)
    assert result.exit_code != 0
    assert str(env["readonly"]) in result.output
    run.assert_not_called()


def test_missing_readonly_kubeconfig_is_skipped_but_not_writable_target(
    env: dict,
) -> None:
    env["readonly"].unlink()
    with patch(TTY, return_value=True), patch(RUN, side_effect=_kubectl()):
        assert _issue(env).exit_code == 0


def test_token_path_equal_to_deployer_path_is_refused(env: dict) -> None:
    config = yaml.safe_load(env["config"].read_text())
    config["settings"]["access"]["deployer"]["kubeconfig"] = str(env["token"])
    env["config"].write_text(yaml.safe_dump(config))
    with patch(TTY, return_value=True), patch(RUN) as run:
        result = _issue(env)
    assert result.exit_code != 0
    assert "different files" in result.output
    run.assert_not_called()


# --- can-i handling --------------------------------------------------------


def test_can_i_no_is_failure_with_hint(env: dict) -> None:
    with patch(TTY, return_value=True), patch(RUN, side_effect=_kubectl(can_i="no")):
        result = _issue(env)
    assert result.exit_code == 1
    assert "deployer check failed" in result.output
    assert env["token"].exists()  # written, as the hint says
    assert SENTINEL not in _all_text(result)


def test_can_i_error_is_failure(env: dict) -> None:
    def fake(command, **kwargs):
        if "token" in command:
            return _proc(0, SENTINEL)
        return _proc(1, "", "error: You must be logged in to the server (Unauthorized)")

    with patch(TTY, return_value=True), patch(RUN, side_effect=fake):
        result = _issue(env)
    assert result.exit_code == 1
    assert "Unauthorized" in result.output
    assert "deployer check failed" in result.output
    assert SENTINEL not in _all_text(result)


# --- registration / secrecy ------------------------------------------------


def test_issue_registered_and_not_gated() -> None:
    from sbkube.utils.deploy_gate import CLUSTER_MUTATING_COMMANDS

    assert "issue" in main.commands["access"].commands  # type: ignore[attr-defined]
    assert "access" not in CLUSTER_MUTATING_COMMANDS


def test_token_never_in_environment_or_kwargs(env: dict) -> None:
    seen: list = []

    def fake(command, **kwargs):
        seen.append(kwargs)
        return _kubectl()(command, **kwargs)

    with patch(TTY, return_value=True), patch(RUN, side_effect=fake):
        assert _issue(env).exit_code == 0
    assert all("env" not in k for k in seen)
    assert SENTINEL not in repr(seen)
    assert SENTINEL not in " ".join(os.environ.values())
