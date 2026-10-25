"""Tests for ``sbkube access verify`` and ``sbkube access audit`` (no cluster)."""

import subprocess
from pathlib import Path
from unittest.mock import patch

import pytest
import yaml
from click.testing import CliRunner

from sbkube.cli import main
from sbkube.commands import access
from sbkube.models.access_model import AccessSettings

SERVER = "https://10.0.0.1:6443"
CTX = "prod"
# Values that must never appear in any output.
SECRET_TOKEN = "SUPERSECRETTOKENVALUE"
SECRET_CERT = "SUPERSECRETCERTDATA"
SECRET_KEY = "SUPERSECRETKEYDATA"


def _kubeconfig(
    path: Path,
    *,
    user: str = "u",
    user_body: dict | None = None,
    server: str = SERVER,
    context: str = CTX,
) -> Path:
    path.write_text(
        yaml.safe_dump(
            {
                "apiVersion": "v1",
                "kind": "Config",
                "current-context": context,
                "clusters": [{"name": "c", "cluster": {"server": server}}],
                "contexts": [
                    {"name": context, "context": {"cluster": "c", "user": user}}
                ],
                "users": [{"name": user, "user": user_body or {"token": SECRET_TOKEN}}],
            }
        )
    )
    return path


def _admin_body() -> dict:
    return {
        "client-certificate-data": SECRET_CERT,
        "client-key-data": SECRET_KEY,
    }


def _write_config(
    tmp_path: Path,
    *,
    admin: Path | None,
    readonly: Path | None,
    extra: list | None = None,
) -> Path:
    settings: dict = {"kubeconfig_context": CTX}
    if admin is not None:
        settings["kubeconfig"] = str(admin)
    access_block: dict = {"readonly": {"extra_rules": extra or []}}
    if readonly is not None:
        access_block["readonly"]["kubeconfig"] = str(readonly)
    settings["access"] = access_block
    config = tmp_path / "sbkube.yaml"
    config.write_text(
        yaml.safe_dump(
            {
                "apiVersion": "sbkube/v1",
                "metadata": {"name": "t"},
                "settings": settings,
                "apps": {},
            }
        )
    )
    return config


def _run(args: list[str], env: dict | None = None):
    return CliRunner().invoke(
        main, ["access", *args], env={"COLUMNS": "200", **(env or {})}
    )


def _proc(rc: int, out: str = "", err: str = "") -> subprocess.CompletedProcess:
    return subprocess.CompletedProcess([], rc, stdout=out, stderr=err)


def _expected_answer(args: list[str]) -> subprocess.CompletedProcess:
    """Answer each can-i like a correctly configured readonly credential."""
    tail = args[args.index("can-i") + 1 :]
    if tail[0] in ("get", "list") and "secrets" not in tail:
        return _proc(0, "yes\n")
    return _proc(1, "no\n")


@pytest.fixture
def setup(tmp_path: Path) -> dict:
    admin = _kubeconfig(tmp_path / "admin", user_body=_admin_body())
    readonly = _kubeconfig(tmp_path / "readonly")
    return {
        "admin": admin,
        "readonly": readonly,
        "config": _write_config(tmp_path, admin=admin, readonly=readonly),
        "tmp": tmp_path,
    }


# --- registration ----------------------------------------------------------


def test_access_is_registered_and_not_gated() -> None:
    from sbkube.utils.deploy_gate import CLUSTER_MUTATING_COMMANDS, is_gated

    assert "access" in main.commands
    assert "access" not in CLUSTER_MUTATING_COMMANDS
    assert not is_gated(main.commands["access"])


# --- verify ----------------------------------------------------------------


def test_verify_passes_and_runs_expected_checks(setup: dict) -> None:
    calls: list[list[str]] = []

    def fake_run(command, **kwargs):
        calls.append(command)
        assert kwargs.get("shell") is None
        return _expected_answer(command)

    with patch("sbkube.commands.access.subprocess.run", side_effect=fake_run):
        result = _run(["verify", "-f", str(setup["config"])])

    assert result.exit_code == 0, result.output
    tails = [" ".join(c[c.index("can-i") + 1 :]) for c in calls]
    assert tails == [
        "get secrets -A",
        "list pods -A",
        "list nodes",
        "list customresourcedefinitions.apiextensions.k8s.io",
        "create deployments.apps -A",
        "delete pods -A",
    ]
    first = calls[0]
    assert first[:5] == [
        "kubectl",
        "--kubeconfig",
        str(setup["readonly"]),
        "--context",
        CTX,
    ]
    assert "PASS" in result.output
    for secret in (SECRET_TOKEN, SECRET_CERT, SECRET_KEY):
        assert secret not in result.output


def test_verify_fails_when_secrets_readable(setup: dict) -> None:
    def fake_run(command, **kwargs):
        return _proc(0, "yes\n")

    with patch("sbkube.commands.access.subprocess.run", side_effect=fake_run):
        result = _run(["verify", "-f", str(setup["config"])])

    assert result.exit_code == 1
    assert "FAIL" in result.output


@pytest.mark.parametrize(
    "proc",
    [
        _proc(1, "", "error: You must be logged in to the server (Unauthorized)"),
        _proc(
            1,
            "no\n",
            "Unable to connect to the server: dial tcp 10.0.0.1:6443: connection refused",
        ),
        _proc(1, "", "error: token has expired"),
        _proc(2, "", "error: something odd"),
        _proc(0, "", ""),
    ],
)
def test_verify_reports_errors_not_no(setup: dict, proc) -> None:
    with patch("sbkube.commands.access.subprocess.run", return_value=proc):
        result = _run(["verify", "-f", str(setup["config"])])

    assert result.exit_code == 1
    assert "ERROR" in result.output


def test_run_can_i_distinguishes_no_from_error() -> None:
    ro = Path("/x")
    with patch("sbkube.commands.access.subprocess.run", return_value=_proc(1, "no\n")):
        assert access.run_can_i(ro, CTX, ("get", "secrets")).answer == "no"
    with patch("sbkube.commands.access.subprocess.run", return_value=_proc(0, "yes\n")):
        assert access.run_can_i(ro, CTX, ("get", "pods")).answer == "yes"
    with patch(
        "sbkube.commands.access.subprocess.run",
        return_value=_proc(1, "", "Unauthorized"),
    ):
        assert access.run_can_i(ro, CTX, ("get", "pods")).answer == "error"


def test_run_can_i_handles_missing_kubectl_and_timeout() -> None:
    ro = Path("/x")
    with patch("sbkube.commands.access.subprocess.run", side_effect=FileNotFoundError):
        assert access.run_can_i(ro, CTX, ("get", "pods")).answer == "error"
    timeout = subprocess.TimeoutExpired("kubectl", 30)
    with patch("sbkube.commands.access.subprocess.run", side_effect=timeout):
        assert access.run_can_i(ro, CTX, ("get", "pods")).answer == "error"


def test_verify_server_mismatch_fails_before_kubectl(setup: dict) -> None:
    _kubeconfig(setup["readonly"], server="https://evil.example:6443")
    with patch("sbkube.commands.access.subprocess.run") as run:
        result = _run(["verify", "-f", str(setup["config"])])

    assert result.exit_code == 1
    assert "mismatch" in result.output
    run.assert_not_called()


def test_verify_readonly_kubeconfig_missing_file(setup: dict) -> None:
    setup["readonly"].unlink()
    with patch("sbkube.commands.access.subprocess.run") as run:
        result = _run(["verify", "-f", str(setup["config"])])

    assert result.exit_code == 1
    assert "not found" in result.output
    run.assert_not_called()


def test_verify_context_missing_in_readonly(setup: dict) -> None:
    _kubeconfig(setup["readonly"], context="other")
    with patch("sbkube.commands.access.subprocess.run") as run:
        result = _run(["verify", "-f", str(setup["config"])])

    assert result.exit_code == 1
    assert "not found in readonly kubeconfig" in result.output
    run.assert_not_called()


def test_verify_admin_kubeconfig_missing(setup: dict) -> None:
    setup["admin"].unlink()
    result = _run(["verify", "-f", str(setup["config"])])
    assert result.exit_code == 1
    assert "admin kubeconfig" in result.output


def test_verify_without_access_block(tmp_path: Path) -> None:
    config = tmp_path / "sbkube.yaml"
    config.write_text(
        yaml.safe_dump(
            {"apiVersion": "sbkube/v1", "metadata": {"name": "t"}, "apps": {}}
        )
    )
    result = _run(["verify", "-f", str(config)])
    assert result.exit_code != 0
    assert "settings.access" in result.output


def test_verify_without_readonly_kubeconfig(tmp_path: Path) -> None:
    config = _write_config(tmp_path, admin=tmp_path / "a", readonly=None)
    result = _run(["verify", "-f", str(config)])
    assert result.exit_code != 0
    assert "readonly.kubeconfig" in result.output


def test_verify_missing_config_file(tmp_path: Path) -> None:
    result = _run(["verify", "-f", str(tmp_path / "nope.yaml")])
    assert result.exit_code != 0
    assert "not found" in result.output


def test_build_checks_expands_extra_rules() -> None:
    access_settings = AccessSettings(
        readonly={
            "extra_rules": [
                {
                    "apiGroups": ["cert-manager.io", ""],
                    "resources": ["certificates", "pods/log"],
                    "verbs": ["get", "list"],
                },
                {
                    "apiGroups": ["apps"],
                    "resources": ["deployments"],
                    "verbs": ["get"],
                    "resourceNames": ["web"],
                },
                {"verbs": ["get"], "nonResourceURLs": ["/healthz"]},
            ]
        }
    )
    checks = dict(access.build_checks(access_settings))
    for expected in (
        ("get", "certificates.cert-manager.io", "-A"),
        ("list", "certificates.cert-manager.io", "-A"),
        ("get", "pods.cert-manager.io", "-A", "--subresource=log"),
        ("get", "certificates", "-A"),
        ("get", "pods", "-A", "--subresource=log"),
        ("get", "deployments.apps/web"),
        ("get", "/healthz"),
    ):
        assert checks[expected] == "yes", expected
    # base table is still first and unchanged
    assert list(checks)[0] == ("get", "secrets", "-A")
    assert checks[("get", "secrets", "-A")] == "no"


def test_verify_runs_extra_rule_checks(tmp_path: Path) -> None:
    admin = _kubeconfig(tmp_path / "admin", user_body=_admin_body())
    readonly = _kubeconfig(tmp_path / "readonly")
    config = _write_config(
        tmp_path,
        admin=admin,
        readonly=readonly,
        extra=[
            {
                "apiGroups": ["cert-manager.io"],
                "resources": ["certificates"],
                "verbs": ["get"],
            }
        ],
    )
    seen: list[str] = []

    def fake_run(command, **kwargs):
        seen.append(" ".join(command[command.index("can-i") + 1 :]))
        return _expected_answer(command)

    with patch("sbkube.commands.access.subprocess.run", side_effect=fake_run):
        result = _run(["verify", "-f", str(config)])

    assert result.exit_code == 0, result.output
    assert "get certificates.cert-manager.io -A" in seen


# --- audit -----------------------------------------------------------------


def test_audit_classifies_credentials_without_leaking(tmp_path: Path) -> None:
    kc = tmp_path / "kc"
    kc.write_text(
        yaml.safe_dump(
            {
                "contexts": [
                    {"name": "adm", "context": {"cluster": "c", "user": "admin"}},
                    {"name": "tok", "context": {"cluster": "c", "user": "bot"}},
                    {"name": "ex", "context": {"cluster": "c", "user": "oidc"}},
                ],
                "users": [
                    {"name": "admin", "user": _admin_body()},
                    {"name": "bot", "user": {"token": SECRET_TOKEN}},
                    {"name": "tf", "user": {"tokenFile": "/secret/path-to-token"}},
                    {
                        "name": "oidc",
                        "user": {"exec": {"command": "gke-gcloud-auth-plugin"}},
                    },
                    {"name": "legacy", "user": {"auth-provider": {"name": "gcp"}}},
                ],
            }
        )
    )
    result = _run(
        ["audit", "-f", str(tmp_path / "none.yaml")], env={"KUBECONFIG": str(kc)}
    )

    assert result.exit_code == 0, result.output
    out = result.output
    assert "client-cert (admin-like)" in out
    assert "token" in out
    assert "exec" in out
    assert "adm" in out
    assert "KUBECONFIG reaches" in out
    for secret in (SECRET_TOKEN, SECRET_CERT, SECRET_KEY):
        assert secret not in out


def test_audit_classification_units() -> None:
    from sbkube.utils.access_kubeconfig import classify_credential

    assert classify_credential({"client-key": "/k"}) == "client-cert (admin-like)"
    assert classify_credential({"token": "x", "client-certificate-data": "y"}) == (
        "client-cert (admin-like)"
    )
    assert classify_credential({"tokenFile": "/t"}) == "token"
    assert classify_credential({"exec": {}}) == "exec"
    assert classify_credential({"auth-provider": {}}) == "exec"
    assert classify_credential({}) == "other"


def test_audit_strict_exit_code(tmp_path: Path) -> None:
    admin = _kubeconfig(tmp_path / "admin", user_body=_admin_body())
    env = {"KUBECONFIG": str(admin)}
    missing = str(tmp_path / "none.yaml")
    assert _run(["audit", "-f", missing], env=env).exit_code == 0
    assert _run(["audit", "-f", missing, "--strict"], env=env).exit_code == 1

    clean = _kubeconfig(tmp_path / "clean")
    result = _run(["audit", "-f", missing, "--strict"], env={"KUBECONFIG": str(clean)})
    assert result.exit_code == 0
    assert "no admin-like credential" in result.output


def test_audit_flags_settings_kubeconfig_when_access_configured(setup: dict) -> None:
    result = _run(
        ["audit", "-f", str(setup["config"]), "--strict"],
        env={"KUBECONFIG": str(setup["readonly"])},
    )
    assert result.exit_code == 1
    assert "agents run as admin" in result.output
    for secret in (SECRET_TOKEN, SECRET_CERT, SECRET_KEY):
        assert secret not in result.output


def test_audit_settings_kubeconfig_without_access_is_not_a_finding(
    tmp_path: Path,
) -> None:
    admin = _kubeconfig(tmp_path / "admin", user_body=_admin_body())
    config = tmp_path / "sbkube.yaml"
    config.write_text(
        yaml.safe_dump(
            {
                "apiVersion": "sbkube/v1",
                "metadata": {"name": "t"},
                "settings": {"kubeconfig": str(admin), "kubeconfig_context": CTX},
                "apps": {},
            }
        )
    )
    clean = _kubeconfig(tmp_path / "clean")
    result = _run(
        ["audit", "-f", str(config), "--strict"], env={"KUBECONFIG": str(clean)}
    )
    assert result.exit_code == 0
    assert "client-cert" in result.output


def test_audit_flags_readonly_kubeconfig_with_client_cert(tmp_path: Path) -> None:
    admin = _kubeconfig(tmp_path / "admin", user_body=_admin_body())
    bad_readonly = _kubeconfig(tmp_path / "ro", user_body=_admin_body())
    config = _write_config(tmp_path, admin=admin, readonly=bad_readonly)
    clean = _kubeconfig(tmp_path / "clean")
    result = _run(
        ["audit", "-f", str(config), "--strict"], env={"KUBECONFIG": str(clean)}
    )
    assert result.exit_code == 1
    assert "access.readonly.kubeconfig" in result.output


def test_audit_reports_unreadable_files(tmp_path: Path) -> None:
    broken = tmp_path / "broken"
    broken.write_text("users: [unclosed\n  - " + SECRET_TOKEN)
    gone = tmp_path / "gone"
    sep = ":"
    result = _run(
        ["audit", "-f", str(tmp_path / "none.yaml"), "--strict"],
        env={"KUBECONFIG": f"{broken}{sep}{gone}"},
    )
    assert result.exit_code == 0, result.output
    assert result.output.count("unreadable:") == 2
    assert SECRET_TOKEN not in result.output


def test_audit_defaults_to_home_kube_config(tmp_path: Path) -> None:
    home = tmp_path / "home"
    (home / ".kube").mkdir(parents=True)
    _kubeconfig(home / ".kube" / "config", user_body=_admin_body())
    result = _run(
        ["audit", "-f", str(tmp_path / "none.yaml"), "--strict"],
        env={"HOME": str(home), "KUBECONFIG": ""},
    )
    assert result.exit_code == 1
    assert "KUBECONFIG reaches" in result.output


def test_verify_global_context_and_kubeconfig_override(setup: dict) -> None:
    alt_admin = _kubeconfig(
        setup["tmp"] / "alt-admin", user_body=_admin_body(), context="alt"
    )
    _kubeconfig(setup["readonly"], context="alt")
    seen: list[list[str]] = []

    def fake_run(command, **kwargs):
        seen.append(command)
        return _expected_answer(command)

    with patch("sbkube.commands.access.subprocess.run", side_effect=fake_run):
        result = CliRunner().invoke(
            main,
            [
                "--kubeconfig",
                str(alt_admin),
                "--context",
                "alt",
                "access",
                "verify",
                "-f",
                str(setup["config"]),
            ],
            env={"COLUMNS": "200"},
        )

    assert result.exit_code == 0, result.output
    assert seen[0][3:5] == ["--context", "alt"]
