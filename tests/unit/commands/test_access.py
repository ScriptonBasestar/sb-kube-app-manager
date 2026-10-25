"""Tests for ``sbkube access verify`` and ``sbkube access audit`` (no cluster)."""

import subprocess
from pathlib import Path
from unittest.mock import patch

import pytest
import yaml
from click.testing import CliRunner

from sbkube.cli import main
from sbkube.models.access_model import AccessSettings
from sbkube.utils import access_checks

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


NAMESPACES = ["agent-access", "kube-system", "prod"]


def _expected_answer(args: list[str]) -> subprocess.CompletedProcess:
    """Answer each can-i like a correctly configured readonly credential."""
    if "can-i" not in args:  # kubectl get namespaces -o name
        return _proc(0, "".join(f"namespace/{n}\n" for n in NAMESPACES))
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

    with patch("sbkube.utils.access_checks.subprocess.run", side_effect=fake_run):
        result = _run(["verify", "-f", str(setup["config"])])

    assert result.exit_code == 0, result.output
    tails = [" ".join(c[c.index("can-i") + 1 :]) for c in calls if "can-i" in c]
    cluster_wide = [
        "get secrets -A",
        "list secrets -A",
        "watch secrets -A",
        "list pods -A",
        "list nodes",
        "list customresourcedefinitions.apiextensions.k8s.io",
        "create deployments.apps -A",
        "delete pods -A",
        "create serviceaccounts --subresource=token -n agent-access",
    ]
    assert tails[: len(cluster_wide)] == cluster_wide
    per_namespace = sorted(tails[len(cluster_wide) :])
    assert per_namespace == sorted(
        f"{verb} {resource} -n {ns}"
        for verb, resource in (
            ("get", "secrets"),
            ("list", "secrets"),
            ("watch", "secrets"),
            ("create", "deployments.apps"),
            ("delete", "pods"),
        )
        for ns in NAMESPACES
    )
    namespace_call = next(c for c in calls if "can-i" not in c)
    assert namespace_call[-4:] == ["get", "namespaces", "-o", "name"]
    assert namespace_call[1:5] == [
        "--kubeconfig",
        str(setup["readonly"]),
        "--context",
        CTX,
    ]
    assert "all 3 namespaces" in result.output
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

    with patch("sbkube.utils.access_checks.subprocess.run", side_effect=fake_run):
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
    with patch("sbkube.utils.access_checks.subprocess.run", return_value=proc):
        result = _run(["verify", "-f", str(setup["config"])])

    assert result.exit_code == 1
    assert "ERROR" in result.output


def test_run_can_i_distinguishes_no_from_error() -> None:
    ro = Path("/x")
    with patch(
        "sbkube.utils.access_checks.subprocess.run", return_value=_proc(1, "no\n")
    ):
        assert access_checks.run_can_i(ro, CTX, ("get", "secrets")).answer == "no"
    with patch(
        "sbkube.utils.access_checks.subprocess.run", return_value=_proc(0, "yes\n")
    ):
        assert access_checks.run_can_i(ro, CTX, ("get", "pods")).answer == "yes"
    with patch(
        "sbkube.utils.access_checks.subprocess.run",
        return_value=_proc(1, "", "Unauthorized"),
    ):
        assert access_checks.run_can_i(ro, CTX, ("get", "pods")).answer == "error"


def test_run_can_i_handles_missing_kubectl_and_timeout() -> None:
    ro = Path("/x")
    with patch(
        "sbkube.utils.access_checks.subprocess.run", side_effect=FileNotFoundError
    ):
        assert access_checks.run_can_i(ro, CTX, ("get", "pods")).answer == "error"
    timeout = subprocess.TimeoutExpired("kubectl", 30)
    with patch("sbkube.utils.access_checks.subprocess.run", side_effect=timeout):
        assert access_checks.run_can_i(ro, CTX, ("get", "pods")).answer == "error"


def test_verify_server_mismatch_fails_before_kubectl(setup: dict) -> None:
    _kubeconfig(setup["readonly"], server="https://evil.example:6443")
    with patch("sbkube.utils.access_checks.subprocess.run") as run:
        result = _run(["verify", "-f", str(setup["config"])])

    assert result.exit_code == 1
    assert "mismatch" in result.output
    run.assert_not_called()


def test_verify_readonly_kubeconfig_missing_file(setup: dict) -> None:
    setup["readonly"].unlink()
    with patch("sbkube.utils.access_checks.subprocess.run") as run:
        result = _run(["verify", "-f", str(setup["config"])])

    assert result.exit_code == 1
    assert "not found" in result.output
    run.assert_not_called()


def test_verify_context_missing_in_readonly(setup: dict) -> None:
    _kubeconfig(setup["readonly"], context="other")
    with patch("sbkube.utils.access_checks.subprocess.run") as run:
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
    checks = dict(access_checks.build_checks(access_settings))
    for expected in (
        ("get", "certificates.cert-manager.io", "-A"),
        ("list", "certificates.cert-manager.io", "-A"),
        ("get", "pods.cert-manager.io", "-A", "--subresource=log"),
        ("get", "certificates", "-A"),
        ("get", "pods", "-A", "--subresource=log"),
        ("get", "deployments.apps/web", "-A"),
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
        if "can-i" in command:
            seen.append(" ".join(command[command.index("can-i") + 1 :]))
        return _expected_answer(command)

    with patch("sbkube.utils.access_checks.subprocess.run", side_effect=fake_run):
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

    with patch("sbkube.utils.access_checks.subprocess.run", side_effect=fake_run):
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


# --- namespace-scoped bindings ---------------------------------------------


def _answering(deny_free: set[str] | None = None, namespaces=NAMESPACES):
    """Fake kubectl: correct answers, except ``yes`` for the can-i strings given."""
    leaks = deny_free or set()

    def fake_run(command, **kwargs):
        if "can-i" not in command:
            return _proc(0, "".join(f"namespace/{n}\n" for n in namespaces))
        tail = " ".join(command[command.index("can-i") + 1 :])
        if tail in leaks:
            return _proc(0, "yes\n")
        return _expected_answer(command)

    return fake_run


def test_verify_catches_namespace_scoped_secret_binding(setup: dict) -> None:
    fake = _answering({"get secrets -n prod"})
    with patch("sbkube.utils.access_checks.subprocess.run", side_effect=fake):
        result = _run(["verify", "-f", str(setup["config"])])

    assert result.exit_code == 1
    assert "yes in: prod" in result.output
    # the -A rows alone would have passed
    assert "FAIL" in result.output


def test_verify_caps_listed_offending_namespaces(setup: dict) -> None:
    many = [f"ns{i:02d}" for i in range(15)]
    leaks = {f"delete pods -n {n}" for n in many}
    fake = _answering(leaks, namespaces=many)
    with patch("sbkube.utils.access_checks.subprocess.run", side_effect=fake):
        result = _run(["verify", "-f", str(setup["config"])])

    assert result.exit_code == 1
    assert "ns09" in result.output
    assert "ns10" not in result.output
    assert "(+5 more)" in result.output  # 15 offenders, 10 shown


def test_verify_always_checks_access_namespace(setup: dict) -> None:
    calls: list[str] = []
    base = _answering(namespaces=["prod"])

    def fake(command, **kwargs):
        calls.append(" ".join(command))
        return base(command, **kwargs)

    with patch("sbkube.utils.access_checks.subprocess.run", side_effect=fake):
        result = _run(["verify", "-f", str(setup["config"])])

    assert result.exit_code == 0, result.output
    assert any(c.endswith("can-i get secrets -n agent-access") for c in calls)
    assert "all 2 namespaces" in result.output


def test_verify_namespace_listing_failure_is_error(setup: dict) -> None:
    base = _answering()

    def fake(command, **kwargs):
        if "can-i" not in command:
            return _proc(
                1, "", "Error from server (Forbidden): namespaces is forbidden"
            )
        return base(command, **kwargs)

    with patch("sbkube.utils.access_checks.subprocess.run", side_effect=fake):
        result = _run(["verify", "-f", str(setup["config"])])

    assert result.exit_code == 1
    assert "ERROR" in result.output
    assert "forbidden" in result.output.lower()


def test_verify_token_minting_must_be_denied(setup: dict) -> None:
    leak = "create serviceaccounts --subresource=token -n agent-access"
    with patch(
        "sbkube.utils.access_checks.subprocess.run", side_effect=_answering({leak})
    ):
        result = _run(["verify", "-f", str(setup["config"])])
    assert result.exit_code == 1
    assert "serviceaccounts --subresource=token" in result.output


def test_verify_per_namespace_error_is_error_not_pass(setup: dict) -> None:
    base = _answering()

    def fake(command, **kwargs):
        if "can-i" in command and command[-1] == "prod":
            return _proc(
                1, "", "Unable to connect to the server: dial tcp: i/o timeout"
            )
        return base(command, **kwargs)

    with patch("sbkube.utils.access_checks.subprocess.run", side_effect=fake):
        result = _run(["verify", "-f", str(setup["config"])])
    assert result.exit_code == 1
    assert "ERROR" in result.output


# --- error classification --------------------------------------------------


def test_run_can_i_ignores_benign_certificates_warning() -> None:
    warning = "Warning: resource type 'certificates' is not namespace scoped"
    with patch(
        "sbkube.utils.access_checks.subprocess.run",
        return_value=_proc(0, "yes\n", warning),
    ):
        assert (
            access_checks.run_can_i(Path("/x"), CTX, ("get", "certificates")).answer
            == "yes"
        )
    with patch(
        "sbkube.utils.access_checks.subprocess.run",
        return_value=_proc(1, "no\n", warning),
    ):
        assert (
            access_checks.run_can_i(Path("/x"), CTX, ("get", "certificates")).answer
            == "no"
        )


@pytest.mark.parametrize(
    "stderr",
    [
        "Unable to connect: x509: certificate signed by unknown authority",
        "tls: failed to verify certificate: x509: certificate has expired",
    ],
)
def test_run_can_i_tls_failures_are_errors(stderr: str) -> None:
    with patch(
        "sbkube.utils.access_checks.subprocess.run",
        return_value=_proc(1, "no\n", stderr),
    ):
        assert (
            access_checks.run_can_i(Path("/x"), CTX, ("get", "pods")).answer == "error"
        )


# --- malformed kubeconfig --------------------------------------------------


@pytest.mark.parametrize(
    "mutate",
    [
        lambda d: d["contexts"][0]["context"].update(cluster=["a"]),
        lambda d: d["contexts"][0].update(context="notamapping"),
        lambda d: d["clusters"][0].update(name=["c"]),
        lambda d: d["clusters"][0].update(cluster={"server": {"x": 1}}),
        lambda d: d["clusters"][0].update(cluster="oops"),
    ],
)
def test_context_server_malformed_raises_kubeconfig_error(
    tmp_path: Path, mutate
) -> None:
    from sbkube.utils.access_kubeconfig import (
        KubeconfigError,
        context_server,
        read_kubeconfig,
    )

    path = _kubeconfig(tmp_path / "kc")
    data = read_kubeconfig(path)
    mutate(data)
    try:
        context_server(data, CTX, path)
    except KubeconfigError as e:
        assert str(path) in str(e)
    else:
        # an unusable cluster name is simply not resolvable, never a TypeError
        assert context_server(data, CTX, path) is None


def test_verify_malformed_readonly_kubeconfig_names_file(setup: dict) -> None:
    data = yaml.safe_load(setup["readonly"].read_text())
    data["contexts"][0]["context"]["cluster"] = ["not", "a", "string"]
    setup["readonly"].write_text(yaml.safe_dump(data))
    with patch("sbkube.utils.access_checks.subprocess.run") as run:
        result = _run(["verify", "-f", str(setup["config"])])

    assert result.exit_code == 1
    assert "readonly" in result.output
    assert "Traceback" not in result.output
    run.assert_not_called()
