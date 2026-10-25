"""Tests for the deploy gate (sbkube/utils/deploy_gate.py)."""

import contextvars
import json
import os
import re
import shlex
import sqlite3
import subprocess
import sys
import threading
from datetime import timedelta
from pathlib import Path

import click
import pytest
from click.testing import CliRunner

from sbkube.cli import SbkubeGroup, main
from sbkube.commands import gate as gate_command
from sbkube.exceptions import ConfigurationError
from sbkube.utils import deploy_gate, deploy_gate_config
from sbkube.utils.datetime_utils import utc_now
from sbkube.utils.deploy_gate import (
    CLUSTER_MUTATING_COMMANDS,
    GATE_FILE_NAME,
    READ_ONLY_COMMANDS,
    DeployGateError,
    find_gate_files,
    is_gated,
    resolve_gate,
    run_gate,
)

REPO_ROOT = Path(__file__).resolve().parents[3]

# Every source file that issues a cluster-mutating helm/kubectl call, mapped to
# the registered commands that reach it. Non-mutating mentions (dry runs,
# `auth can-i`, docstrings, model literals) are listed with an empty tuple.
MUTATION_SITE_FILES: dict[str, tuple[str, ...]] = {
    "sbkube/commands/deploy.py": ("deploy", "apply"),
    "sbkube/commands/delete.py": ("delete",),
    "sbkube/commands/upgrade.py": ("upgrade",),
    "sbkube/commands/migrate.py": ("migrate",),
    "sbkube/state/rollback.py": ("rollback",),
    "sbkube/utils/hook_executor.py": ("deploy", "apply"),
    "sbkube/utils/prune_helper.py": ("apply",),
    "sbkube/utils/helm_command_builder.py": ("deploy", "apply"),
    "sbkube/utils/access_checks.py": (),
    # `kubectl create token` is a TokenRequest (a credential, not a workload
    # mutation) and `access` is read-only for the gate (see READ_ONLY_COMMANDS).
    "sbkube/utils/access_issue.py": (),
    # Same TokenRequest via node-only SSH; no workload/RBAC mutations here.
    "sbkube/utils/access_admin.py": (),
    "sbkube/commands/check_updates.py": (),
    "sbkube/diagnostics/kubernetes_checks.py": (),
    "sbkube/models/config_model.py": (),
    "sbkube/utils/cluster_config.py": (),
    "sbkube/validators/environment_validators.py": (),
    "sbkube/validators/pre_deployment_validators.py": (),
}

_TOOL = re.compile(r'"(helm|kubectl)"')
_VERB = re.compile(
    r'"(install|upgrade|uninstall|rollback|apply|delete|create|patch|replace)"'
)


def _python_command(code: str) -> str:
    return f"{shlex.quote(sys.executable)} -c {shlex.quote(code)}"


FAIL = _python_command("import sys; sys.exit(3)")
PASS = _python_command(
    "import os, sys; open('gate-called', 'w').write("
    "sys.argv[1] + ' ' + os.environ['SBKUBE_GATE_OPERATION'])"
)


def _write_gate(directory: Path, body: str) -> Path:
    directory.mkdir(parents=True, exist_ok=True)
    path = directory / GATE_FILE_NAME
    path.write_text(body, encoding="utf-8")
    return path


def _workspace(tmp_path: Path) -> Path:
    root = tmp_path / "ws"
    root.mkdir()
    (root / ".sbkube-workspace").write_text("anchors: {}\n", encoding="utf-8")
    return root


def _global_gate(root: Path, mode: str, command: str = FAIL, extra: str = "") -> Path:
    return _write_gate(
        root, f"deploy_gate:\n  command: {json.dumps(command)}\n  mode: {mode}\n{extra}"
    )


def _gated_group(record: list[str]) -> click.Group:
    """A fresh SbkubeGroup with a fake mutating command, registered the real way."""

    @click.group(cls=SbkubeGroup)
    def group() -> None:
        pass

    @click.command(name="deploy")
    @click.argument("target", required=False)
    @click.option("--dry-run", "dry_run", is_flag=True)
    def fake_deploy(target: str | None, dry_run: bool) -> None:
        record.append(f"ran {target}")

    group.add_command(fake_deploy)
    return group


# --- one enforcement point -------------------------------------------------


def test_every_cluster_mutating_command_is_gated() -> None:
    registered = set(main.commands)
    unclassified = registered - CLUSTER_MUTATING_COMMANDS - READ_ONLY_COMMANDS
    assert not unclassified, f"classify new commands in deploy_gate.py: {unclassified}"
    assert not CLUSTER_MUTATING_COMMANDS & READ_ONLY_COMMANDS
    assert CLUSTER_MUTATING_COMMANDS <= registered

    for name, command in main.commands.items():
        assert is_gated(command) == (name in CLUSTER_MUTATING_COMMANDS), name
        option_names = {p.name for p in command.params}
        assert ("skip_deploy_gate" in option_names) == (
            name in CLUSTER_MUTATING_COMMANDS
        ), name

    scanned = set()
    for path in sorted((REPO_ROOT / "sbkube").rglob("*.py")):
        source = path.read_text(encoding="utf-8")
        if _TOOL.search(source) and (
            _VERB.search(source) or "HelmCommand.UPGRADE" in source
        ):
            scanned.add(path.relative_to(REPO_ROOT).as_posix())
    assert scanned == set(MUTATION_SITE_FILES), (
        "helm/kubectl call sites changed; classify them in MUTATION_SITE_FILES and "
        "make sure every command reaching a mutation is in CLUSTER_MUTATING_COMMANDS"
    )
    for reached_by in MUTATION_SITE_FILES.values():
        assert set(reached_by) <= CLUSTER_MUTATING_COMMANDS


def test_deploy_gate_runs_once_for_nested_invocation(tmp_path: Path) -> None:
    root = _workspace(tmp_path)
    _global_gate(root, "enforce", command=PASS)
    record: list[str] = []

    @click.command(name="deploy")
    @click.argument("target", required=False)
    def inner(target: str | None) -> None:
        record.append("inner")

    @click.command(name="apply")
    @click.argument("target", required=False)
    @click.pass_context
    def outer(ctx: click.Context, target: str | None) -> None:
        ctx.invoke(inner, target=target)

    @click.group(cls=SbkubeGroup)
    def group() -> None:
        pass

    group.add_command(inner)
    group.add_command(outer)
    result = CliRunner().invoke(group, ["apply", str(root)])
    assert result.exit_code == 0, result.output
    assert record == ["inner"]
    assert (root / "gate-called").read_text() == "apply apply"


def test_gate_depth_is_per_context_not_per_process(monkeypatch) -> None:
    gated_calls: list[str] = []
    monkeypatch.setattr(
        deploy_gate, "run_gate", lambda name, kw, skip: gated_calls.append(name)
    )
    inside = threading.Event()
    release = threading.Event()

    def slow() -> None:
        inside.set()
        assert release.wait(5)

    first = deploy_gate.gate_callback("first", lambda: slow())
    second = deploy_gate.gate_callback("second", lambda: None)

    worker = threading.Thread(target=first)
    worker.start()
    assert inside.wait(5)
    # An independent invocation overlapping the first still runs its own gate
    second()
    release.set()
    worker.join(5)
    assert gated_calls == ["first", "second"]


def test_gate_depth_propagates_through_copied_context(monkeypatch) -> None:
    gated_calls: list[str] = []
    monkeypatch.setattr(
        deploy_gate, "run_gate", lambda name, kw, skip: gated_calls.append(name)
    )
    inner = deploy_gate.gate_callback("inner", lambda: None)

    def outer_body() -> None:
        thread = threading.Thread(target=contextvars.copy_context().run, args=(inner,))
        thread.start()
        thread.join(5)

    deploy_gate.gate_callback("outer", outer_body)()
    assert gated_calls == ["outer"]


# --- precedence ------------------------------------------------------------


@pytest.mark.parametrize(
    ("global_extra", "global_mode", "individual_mode", "expected"),
    [
        # asymmetric (default): tightening wins, loosening needs allow_override
        ("", "warn", "enforce", "enforce"),
        ("", "enforce", "off", "enforce"),
        ("  allow_override: true\n", "enforce", "off", "off"),
        ("  precedence: asymmetric\n", "enforce", "warn", "enforce"),
        # individual: individual always wins
        ("  precedence: individual\n", "enforce", "off", "off"),
        ("  precedence: individual\n", "off", "enforce", "enforce"),
        # global: tightening wins, loosening loses
        ("  precedence: global\n", "enforce", "off", "enforce"),
        ("  precedence: global\n", "warn", "enforce", "enforce"),
    ],
)
def test_deploy_gate_precedence_asymmetric_default(
    tmp_path: Path,
    global_extra: str,
    global_mode: str,
    individual_mode: str,
    expected: str,
) -> None:
    root = _workspace(tmp_path)
    _global_gate(root, global_mode, extra=global_extra)
    phase = root / "ph1"
    _write_gate(phase, f"deploy_gate:\n  mode: {individual_mode}\n")

    gate = resolve_gate(*find_gate_files(phase / "app"))

    assert gate is not None
    assert gate.mode == expected
    assert len(gate.warnings) == 1  # any disagreement warns
    assert str(root / GATE_FILE_NAME) in gate.warnings[0]
    assert str(phase / GATE_FILE_NAME) in gate.warnings[0]


def test_deploy_gate_mismatch_warns_and_runs(tmp_path: Path) -> None:
    root = _workspace(tmp_path)
    _global_gate(root, "enforce", command=PASS)
    phase = root / "ph1"
    _write_gate(phase, "deploy_gate:\n  mode: off\n")
    record: list[str] = []

    result = CliRunner().invoke(_gated_group(record), ["deploy", str(phase)])

    assert result.exit_code == 0, result.output
    assert record == [f"ran {phase}"]
    assert "deploy gate settings disagree" in result.output
    assert (root / "gate-called").read_text() == "deploy deploy"


def test_deploy_gate_agreeing_settings_do_not_warn(tmp_path: Path) -> None:
    root = _workspace(tmp_path)
    _global_gate(root, "enforce")
    _write_gate(root / "ph1", "deploy_gate:\n  mode: enforce\n")
    gate = resolve_gate(*find_gate_files(root / "ph1"))
    assert gate is not None and gate.mode == "enforce" and gate.warnings == ()


@pytest.mark.parametrize(
    "individual_body",
    [
        "deploy_gate:\n  mode: off\n  precedence: individual\n",
        "deploy_gate:\n  mode: off\n  allow_override: true\n",
        "deploy_gate:\n  mode: warn\n  command: 'true'\n",
        "deploy_gate:\n  mode: off\n  timeout: 5\n",
    ],
)
def test_deploy_gate_individual_cannot_set_global_only_keys(
    tmp_path: Path, individual_body: str
) -> None:
    root = _workspace(tmp_path)
    _global_gate(root, "enforce")
    _write_gate(root / "ph1", individual_body)
    with pytest.raises(ConfigurationError):
        resolve_gate(*find_gate_files(root / "ph1"))


@pytest.mark.parametrize(
    "global_body",
    [
        "deploy_gate:\n  command: 'true'\n",  # mode missing
        "deploy_gate:\n  mode: enforce\n",  # command missing
        "deploy_gate:\n  mode: sometimes\n  command: 'true'\n",
        "deploy_gate:\n  mode: enforce\n  command: 'true'\n  typo: 1\n",
        "deploy_gate: [\n",
        "deploy_gate:\n  mode: enforce\n  command: 'true'\n  timeout: 0\n",
        "deploy_gate:\n  mode: enforce\n  command: 'true'\n  timeout: soon\n",
    ],
)
def test_deploy_gate_invalid_config_fails_closed(
    tmp_path: Path, global_body: str
) -> None:
    root = _workspace(tmp_path)
    _write_gate(root, global_body)
    with pytest.raises(ConfigurationError):
        resolve_gate(*find_gate_files(root))


# --- enforcement -----------------------------------------------------------


def test_deploy_gate_enforce_refuses_on_failure(tmp_path: Path) -> None:
    root = _workspace(tmp_path)
    _global_gate(root, "enforce", command=FAIL)
    record: list[str] = []

    result = CliRunner().invoke(_gated_group(record), ["deploy", str(root)])

    assert result.exit_code != 0
    assert isinstance(result.exception, DeployGateError)
    assert record == []


def test_deploy_gate_warn_mode_continues_on_failure(tmp_path: Path) -> None:
    root = _workspace(tmp_path)
    _global_gate(root, "warn", command=FAIL)
    record: list[str] = []

    result = CliRunner().invoke(_gated_group(record), ["deploy", str(root)])

    assert result.exit_code == 0, result.output
    assert record == [f"ran {root}"]
    assert "continuing because mode=warn" in result.output


HANG = _python_command("import time; time.sleep(30)")


def test_deploy_gate_timeout_refuses_under_enforce(tmp_path: Path) -> None:
    root = _workspace(tmp_path)
    _global_gate(root, "enforce", command=HANG, extra="  timeout: 0.5\n")
    record: list[str] = []

    result = CliRunner().invoke(_gated_group(record), ["deploy", str(root)])

    assert isinstance(result.exception, DeployGateError)
    assert "timed out after 0.5s" in str(result.exception)
    assert record == []


def test_deploy_gate_timeout_warns_under_warn(tmp_path: Path) -> None:
    root = _workspace(tmp_path)
    _global_gate(root, "warn", command=HANG, extra="  timeout: 0.5\n")
    record: list[str] = []

    result = CliRunner().invoke(_gated_group(record), ["deploy", str(root)])

    assert result.exit_code == 0, result.output
    assert record == [f"ran {root}"]
    assert "timed out after 0.5s" in result.output


def test_deploy_gate_dry_run_is_not_gated(tmp_path: Path) -> None:
    root = _workspace(tmp_path)
    _global_gate(root, "enforce", command=FAIL)
    record: list[str] = []

    result = CliRunner().invoke(
        _gated_group(record), ["deploy", str(root), "--dry-run"]
    )

    assert result.exit_code == 0, result.output
    assert record == [f"ran {root}"]


def test_deploy_gate_operation_for_prune(tmp_path: Path) -> None:
    root = _workspace(tmp_path)
    _global_gate(root, "enforce", command=PASS)
    run_gate("apply", {"target": str(root), "prune_disabled": True}, None)
    assert (root / "gate-called").read_text() == "prune prune"


def test_deploy_gate_without_workspace_uses_nearest_file(tmp_path: Path) -> None:
    project = tmp_path / "project"
    _write_gate(
        project, f"deploy_gate:\n  command: {json.dumps(FAIL)}\n  mode: enforce\n"
    )
    with pytest.raises(DeployGateError):
        run_gate("delete", {"target": str(project / "app")}, None)


# --- human skip ------------------------------------------------------------


def test_skip_deploy_gate_requires_tty_and_reason(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    monkeypatch.setenv("HOME", str(tmp_path / "home"))
    (tmp_path / "home").mkdir()
    root = _workspace(tmp_path)
    _global_gate(root, "enforce", command=FAIL)
    params = {"target": str(root)}

    with pytest.raises(click.UsageError, match="interactive terminal"):
        run_gate("deploy", params, "hotfix", interactive=lambda: False)
    with pytest.raises(click.UsageError, match="non-empty reason"):
        run_gate("deploy", params, "  ", interactive=lambda: True)

    # The CLI path checks the real terminal; CliRunner is not one.
    record: list[str] = []
    result = CliRunner().invoke(
        _gated_group(record), ["deploy", str(root), "--skip-deploy-gate=hotfix"]
    )
    assert result.exit_code != 0
    assert "interactive terminal" in result.output
    assert record == []

    run_gate("deploy", params, "  incident 42 ", interactive=lambda: True)

    db_path = tmp_path / "home" / ".sbkube" / "deployments.db"
    with sqlite3.connect(db_path) as connection:
        rows = connection.execute(
            "SELECT operation, target_dir, gate_file, reason FROM deploy_gate_skips"
        ).fetchall()
    assert rows == [
        ("deploy", str(root.resolve()), str(root / GATE_FILE_NAME), "incident 42")
    ]


def test_skip_deploy_gate_has_no_environment_bypass() -> None:
    for module in (deploy_gate, deploy_gate_config):
        source = Path(module.__file__ or "").read_text(encoding="utf-8")
        assert "os.environ.get" not in source and "getenv" not in source
    option = next(
        p for p in main.commands["deploy"].params if p.name == "skip_deploy_gate"
    )
    assert option.envvar is None


# --- no configuration ------------------------------------------------------


def test_no_deploy_gate_config_keeps_behavior(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    def no_subprocess(*args: object, **kwargs: object) -> None:
        raise AssertionError("gate command must not run without configuration")

    monkeypatch.setattr(deploy_gate.subprocess, "run", no_subprocess)
    root = _workspace(tmp_path)  # a workspace with no gate file
    record: list[str] = []

    result = CliRunner().invoke(_gated_group(record), ["deploy", str(root / "app")])

    assert result.exit_code == 0, result.output
    assert record == [f"ran {root / 'app'}"]
    assert result.output == ""
    assert find_gate_files(root) == (None, (), True)


# --- coverage of the command's whole target ---------------------------------


def test_deploy_gate_workspace_root_sees_stricter_phase(tmp_path: Path) -> None:
    root = _workspace(tmp_path)
    _global_gate(root, "warn", command=FAIL)
    _write_gate(root / "phaseA", "deploy_gate:\n  mode: enforce\n")
    _write_gate(root / ".sbkube" / "cache", "deploy_gate:\n  mode: off\n")

    gate = resolve_gate(*find_gate_files(root))

    assert gate is not None and gate.mode == "enforce"
    with pytest.raises(DeployGateError):
        run_gate("apply", {"target": str(root)}, None)


def test_deploy_gate_workspace_root_keeps_global_for_ungoverned_dirs(
    tmp_path: Path,
) -> None:
    root = _workspace(tmp_path)
    _global_gate(root, "enforce", extra="  allow_override: true\n")
    _write_gate(root / "dev", "deploy_gate:\n  mode: off\n")

    at_root = resolve_gate(*find_gate_files(root))
    at_dev = resolve_gate(*find_gate_files(root / "dev"))

    assert at_root is not None and at_root.mode == "enforce"
    assert at_dev is not None and at_dev.mode == "off"


def test_deploy_gate_without_workspace_subdir_cannot_loosen(tmp_path: Path) -> None:
    project = tmp_path / "project"
    _write_gate(
        project, f"deploy_gate:\n  command: {json.dumps(FAIL)}\n  mode: enforce\n"
    )
    _write_gate(project / "app", "deploy_gate:\n  mode: off\n")

    gate = resolve_gate(*find_gate_files(project / "app"))

    assert gate is not None and gate.mode == "enforce"
    assert gate.warnings


# --- start directory per real command ----------------------------------------


def test_deploy_gate_params_match_real_commands() -> None:
    read_by_gate = {
        "deploy": {"target", "config_file", "dry_run"},
        "apply": {"target", "config_file", "dry_run", "prune_disabled"},
        "upgrade": {"target", "config_file", "dry_run"},
        "delete": {"target", "config_file", "dry_run"},
        "rollback": {"deployment_id", "base_dir", "app_dir", "dry_run", "list_points"},
        "migrate": {"target", "dry_run"},
    }
    assert set(read_by_gate) == CLUSTER_MUTATING_COMMANDS
    for name, expected in read_by_gate.items():
        params = {p.name for p in main.commands[name].params}
        assert expected <= params, (name, expected - params)


def test_deploy_gate_rollback_uses_recorded_app_dir(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    from sbkube.models.deployment_state import DeploymentCreate
    from sbkube.state.database import DeploymentDatabase

    monkeypatch.setenv("HOME", str(tmp_path / "home"))
    (tmp_path / "home").mkdir()
    root = _workspace(tmp_path)
    _global_gate(root, "enforce", command=FAIL)
    app_dir = root / "ph1" / "app"
    app_dir.mkdir(parents=True)
    DeploymentDatabase().create_deployment(
        DeploymentCreate(
            deployment_id="dep-1",
            cluster="c",
            namespace="n",
            app_config_dir=str(app_dir),
            config_file_path=str(app_dir / "sbkube.yaml"),
            command="deploy",
            config_snapshot={},
        )
    )
    elsewhere = tmp_path / "elsewhere"
    elsewhere.mkdir()
    monkeypatch.chdir(elsewhere)

    with pytest.raises(DeployGateError):
        run_gate("rollback", {"deployment_id": "dep-1"}, None)


def test_deploy_gate_migrate_uses_target(tmp_path: Path) -> None:
    root = _workspace(tmp_path)
    _global_gate(root, "enforce", command=FAIL)
    with pytest.raises(DeployGateError):
        run_gate("migrate", {"target": str(root / "ph1")}, None)


def test_skip_deploy_gate_rejects_option_like_reason(tmp_path: Path) -> None:
    root = _workspace(tmp_path)
    _global_gate(root, "enforce")
    with pytest.raises(click.UsageError, match="must not start with"):
        run_gate("deploy", {"target": str(root)}, "--dry-run", interactive=lambda: True)


# --- agent grant -------------------------------------------------------------

AGENT = 4242  # the granted agent session process in the fake process tables


def _grant_workspace(tmp_path: Path, monkeypatch: pytest.MonkeyPatch, ttl: str) -> Path:
    monkeypatch.setenv("HOME", str(tmp_path / "home"))
    (tmp_path / "home").mkdir()
    root = _workspace(tmp_path)
    _global_gate(
        root, "enforce", command=FAIL, extra=f"  agent_grant:\n    ttl: {ttl}\n"
    )
    return root


def _grant(root: Path, expires_at: object, pid: int = AGENT) -> None:
    deploy_gate.record_gate_grant(
        gate_dir=root.resolve(),
        pid=pid,
        pid_started="Wed Oct 22 10:00:00 2026",
        expires_at=expires_at,
        reason="test",
    )


def _descends_from(
    monkeypatch: pytest.MonkeyPatch,
    session: int,
    started: str = "Wed Oct 22 10:00:00 2026",
) -> None:
    table = {os.getpid(): (session, "Wed Oct 22 10:05:00 2026"), session: (1, started)}
    monkeypatch.setattr(deploy_gate, "process_table", lambda: table)


def test_gate_grant_ttl_expires(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch, capsys: pytest.CaptureFixture[str]
) -> None:
    root = _grant_workspace(tmp_path, monkeypatch, "1h")
    now = utc_now()
    _grant(root, now + timedelta(hours=1))
    _descends_from(monkeypatch, AGENT)
    params = {"target": str(root)}

    monkeypatch.setattr(deploy_gate, "utc_now", lambda: now + timedelta(minutes=30))
    run_gate("deploy", params, None)
    assert (
        f"agent grant for session PID {AGENT}, 30 min left" in capsys.readouterr().err
    )

    monkeypatch.setattr(deploy_gate, "utc_now", lambda: now + timedelta(hours=2))
    with pytest.raises(DeployGateError, match="exit code 3"):
        run_gate("deploy", params, None)


def test_gate_grant_unlimited_ends_with_session(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch, capsys: pytest.CaptureFixture[str]
) -> None:
    root = _grant_workspace(tmp_path, monkeypatch, "unlimited")
    _grant(root, None)
    params = {"target": str(root)}

    _descends_from(monkeypatch, AGENT)
    run_gate("deploy", params, None)
    assert f"until session PID {AGENT} ends" in capsys.readouterr().err

    # The session ended: its PID is gone from the process table.
    monkeypatch.setattr(deploy_gate, "process_table", lambda: {})
    with pytest.raises(DeployGateError, match="exit code 3"):
        run_gate("deploy", params, None)

    # The PID was reused by a later process: the start time no longer matches.
    _descends_from(monkeypatch, AGENT, started="Thu Oct 23 09:00:00 2026")
    with pytest.raises(DeployGateError, match="exit code 3"):
        run_gate("deploy", params, None)


def test_gate_grant_not_shared_across_sessions(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    root = _grant_workspace(tmp_path, monkeypatch, "unlimited")
    _grant(root, None)
    params = {"target": str(root)}

    _descends_from(monkeypatch, 5555)  # another agent session
    with pytest.raises(DeployGateError, match="exit code 3"):
        run_gate("deploy", params, None)

    # A grant for another gate (another workspace) does not apply here either.
    other = tmp_path / "other"
    other.mkdir()
    _grant(other, None, pid=5555)
    with pytest.raises(DeployGateError, match="exit code 3"):
        run_gate("deploy", params, None)


def test_gate_grant_needs_config_and_terminal(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    monkeypatch.setenv("HOME", str(tmp_path / "home"))
    (tmp_path / "home").mkdir()
    root = _workspace(tmp_path)
    _global_gate(root, "enforce")
    args = ["gate", "grant", "--pid", str(os.getpid()), "--reason", "r"]

    # CliRunner is not a terminal.
    result = CliRunner().invoke(main, [*args, "--target", str(root)])
    assert result.exit_code != 0
    assert "interactive terminal" in result.output

    monkeypatch.setattr(gate_command, "_is_interactive", lambda: True)
    result = CliRunner().invoke(main, [*args, "--target", str(root)])
    assert result.exit_code != 0
    assert "does not enable agent grants" in result.output

    # agent_grant is a global-only key.
    _write_gate(root / "phase", "deploy_gate:\n  agent_grant:\n    ttl: 1h\n")
    with pytest.raises(ConfigurationError, match="agent_grant may only be set"):
        resolve_gate(*find_gate_files(root))

    with pytest.raises(ValueError, match="invalid agent_grant.ttl"):
        deploy_gate_config.parse_grant_ttl("90")


def test_gate_grant_command_records_real_process(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    root = _grant_workspace(tmp_path, monkeypatch, "1h")
    monkeypatch.setattr(gate_command, "_is_interactive", lambda: True)
    args = ["gate", "grant", "--reason", "r", "--target", str(root)]

    # The operator's own terminal (an ancestor) cannot be granted.
    result = CliRunner().invoke(main, [*args, "--pid", str(os.getppid())])
    assert result.exit_code != 0
    assert "ancestor of this terminal" in str(result.exception)

    session = subprocess.Popen([sys.executable, "-c", "import time; time.sleep(60)"])
    try:
        result = CliRunner().invoke(main, [*args, "--pid", str(session.pid)])
        assert result.exit_code == 0, result.output
        assert f"agent grant for PID {session.pid}" in result.output
        # This test process does not descend from the granted session.
        with pytest.raises(DeployGateError, match="exit code 3"):
            run_gate("deploy", {"target": str(root)}, None)
    finally:
        session.kill()
        session.wait()

    db_path = tmp_path / "home" / ".sbkube" / "deployments.db"
    with sqlite3.connect(db_path) as connection:
        rows = connection.execute(
            "SELECT pid, gate_dir, reason, expires_at IS NOT NULL FROM deploy_gate_grants"
        ).fetchall()
    assert rows == [(session.pid, str(root.resolve()), "r", 1)]


def test_gate_grant_unreadable_process_list_runs_gate(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch, capsys: pytest.CaptureFixture[str]
) -> None:
    root = _grant_workspace(tmp_path, monkeypatch, "unlimited")
    _grant(root, None)

    def broken() -> dict[int, tuple[int, str]]:
        raise DeployGateError("cannot list processes: ps exited 1")

    monkeypatch.setattr(deploy_gate, "process_table", broken)
    with pytest.raises(DeployGateError, match="exit code 3"):
        run_gate("deploy", {"target": str(root)}, None)
    assert "agent grant not checked" in capsys.readouterr().err


def test_gate_grant_command_refuses_unknown_pid(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    root = _grant_workspace(tmp_path, monkeypatch, "1h")
    monkeypatch.setattr(gate_command, "_is_interactive", lambda: True)
    monkeypatch.setattr(gate_command, "process_table", lambda: {1: (0, "x")})
    for pid in ("1", "999999"):
        result = CliRunner().invoke(
            main,
            ["gate", "grant", "--pid", pid, "--reason", "r", "--target", str(root)],
        )
        assert result.exit_code != 0
        assert "no running process" in str(result.exception)


def test_gate_grant_process_lineage_reads_real_ps() -> None:
    lineage = deploy_gate.process_lineage(deploy_gate.process_table(), os.getpid())
    pids = [pid for pid, _ in lineage]
    assert pids[:2] == [os.getpid(), os.getppid()]
    assert all(started for _, started in lineage)
