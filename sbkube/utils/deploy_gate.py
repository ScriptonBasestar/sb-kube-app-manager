"""Pre-run deploy gate for every cluster-mutating sbkube command.

A repository opts in by placing ``sbkube-gate.yaml`` files::

    # <workspace root>/sbkube-gate.yaml  (next to .sbkube-workspace) -- global
    deploy_gate:
      command: "uv run scripts/full_ci_gate.py gate"
      mode: enforce            # enforce | warn | off
      precedence: asymmetric   # asymmetric | individual | global (global file only)
      allow_override: false    # global file only

    # <phase or app-group dir>/sbkube-gate.yaml -- individual
    deploy_gate:
      mode: off

Design notes
------------
* **One enforcement point.** :class:`sbkube.cli.SbkubeGroup` wraps the callback
  of every command listed in :data:`CLUSTER_MUTATING_COMMANDS` when it is
  registered. Commands do not call the gate themselves, so a new command cannot
  forget it; ``tests/unit/utils/test_deploy_gate.py`` fails when a registered
  command is classified neither as mutating nor as read-only.
* **Gate files are separate from ``sbkube.yaml``.** The gate files can then be
  edit-protected without protecting every app configuration.
* **No file, no gate.** Without any ``sbkube-gate.yaml`` the commands behave
  exactly as before.
* **``mode`` has no default.** ``settings_merger`` drops child values equal to a
  field default, so a defaulted ``mode`` would make an individual ``off``
  indistinguishable from "unset". Here an unset ``mode`` is ``None`` and the
  precedence rules below decide explicitly.
* **Fail closed.** An unreadable or invalid gate file refuses the command.
* **No environment bypass.** Skipping requires ``--skip-deploy-gate=<reason>``
  from an interactive terminal and is recorded in the state DB. An environment
  variable would leak into agent shells through ``.envrc``.
"""

from __future__ import annotations

import getpass
import os
import shlex
import subprocess
import sys
import threading
from collections.abc import Callable
from pathlib import Path
from typing import Any

import click

from sbkube.exceptions import SbkubeError
from sbkube.utils.deploy_gate_config import (
    GATE_FILE_NAME,
    DeployGateFile,
    DeployGateSettings,
    GateFiles,
    GateSource,
    ResolvedGate,
    find_gate_files,
    load_gate_file,
    resolve_gate,
)

__all__ = [
    "CLUSTER_MUTATING_COMMANDS",
    "GATE_FILE_NAME",
    "READ_ONLY_COMMANDS",
    "DeployGateError",
    "DeployGateFile",
    "DeployGateSettings",
    "GateFiles",
    "GateSource",
    "ResolvedGate",
    "find_gate_files",
    "install_gate",
    "is_gated",
    "load_gate_file",
    "resolve_gate",
    "run_gate",
]

SKIP_OPTION_NAME = "skip_deploy_gate"

# Commands that change cluster state. Every registered command must appear in
# exactly one of these two sets (enforced by tests).
CLUSTER_MUTATING_COMMANDS: frozenset[str] = frozenset(
    {"deploy", "apply", "upgrade", "delete", "rollback", "migrate"}
)
READ_ONLY_COMMANDS: frozenset[str] = frozenset(
    {
        "prepare",
        "build",
        "template",
        "status",
        "history",
        "init",
        "check-updates",
        "validate",
        "version",
        "doctor",
    }
)


# Gated callbacks currently running in this process. ``apply`` runs ``deploy``
# in-process (``ctx.invoke``, workspace worker threads); only the outermost
# gated command runs the gate. Process-wide on purpose: worker threads do not
# inherit context variables.
_gate_depth = 0
_gate_depth_lock = threading.Lock()


class DeployGateError(SbkubeError):
    """Raised when the deploy gate refuses a command."""


def gate_start_directory(command_name: str, params: dict[str, Any]) -> Path:
    """Directory from which gate files are looked up for a parsed command."""
    if command_name == "rollback":
        # A rollback acts on a recorded deployment, not on --base-dir/--app-dir
        # (those only feed --list), so look up where it was deployed from.
        recorded = _recorded_app_dir(params.get("deployment_id"))
        if recorded is not None:
            return recorded
        return Path(params.get("base_dir") or ".") / (params.get("app_dir") or ".")
    config_file = params.get("config_file")
    if config_file:
        return Path(config_file).parent
    target = params.get("target")
    if target:
        return Path(target)
    return Path.cwd()


def _recorded_app_dir(deployment_id: str | None) -> Path | None:
    if not deployment_id:
        return None
    from sbkube.state.database import DeploymentDatabase

    deployment = DeploymentDatabase().get_deployment(deployment_id)
    if deployment is None:
        return None
    app_dir = Path(deployment.app_config_dir)
    return app_dir if app_dir.is_absolute() and app_dir.is_dir() else None


def gate_operation(command_name: str, params: dict[str, Any]) -> str:
    """Operation name passed to the gate command."""
    if command_name == "apply" and params.get("prune_disabled"):
        return "prune"
    return command_name


def is_non_mutating_invocation(command_name: str, params: dict[str, Any]) -> bool:
    """Dry runs and listings do not change the cluster and are not gated."""
    if params.get("dry_run"):
        return True
    return command_name == "rollback" and bool(params.get("list_points"))


def _is_interactive() -> bool:
    return sys.stdin.isatty() and sys.stderr.isatty()


def _warn(message: str) -> None:
    # stderr keeps machine-readable stdout (--format json/yaml/llm) intact.
    click.secho(f"⚠️  {message}", fg="yellow", err=True)


def _operator() -> str | None:
    try:
        return getpass.getuser()
    except OSError:  # no USER/LOGNAME and no passwd entry (containers)
        return None


def record_gate_skip(
    *, operation: str, target_dir: Path, reason: str, gate_file: Path | None
) -> None:
    """Persist a human skip in the state DB."""
    from sbkube.state.database import DeploymentDatabase

    DeploymentDatabase().record_deploy_gate_skip(
        operation=operation,
        target_dir=str(target_dir),
        gate_file=str(gate_file) if gate_file else None,
        reason=reason,
        operator=_operator(),
    )


def run_gate(
    command_name: str,
    params: dict[str, Any],
    skip_reason: str | None,
    *,
    interactive: Callable[[], bool] = _is_interactive,
) -> None:
    """Run the deploy gate for one invocation, raising when it refuses."""
    if skip_reason is not None:
        if not skip_reason.strip():
            raise click.UsageError("--skip-deploy-gate requires a non-empty reason.")
        if skip_reason.lstrip().startswith("-"):
            # `--skip-deploy-gate --dry-run` would take the next option as the reason.
            raise click.UsageError(
                "--skip-deploy-gate reason must not start with '-'; "
                "use --skip-deploy-gate=<reason>."
            )
        if not interactive():
            raise click.UsageError(
                "--skip-deploy-gate is only accepted from an interactive terminal "
                "(stdin and stderr must be a TTY)."
            )

    if is_non_mutating_invocation(command_name, params):
        return

    start = gate_start_directory(command_name, params)
    gate = resolve_gate(*find_gate_files(start))
    if gate is None:
        if skip_reason is not None:
            _warn("--skip-deploy-gate ignored: no deploy gate is configured here.")
        return

    for message in gate.warnings:
        _warn(message)
    if gate.mode == "off":
        return

    operation = gate_operation(command_name, params)
    if skip_reason is not None:
        assert gate.command_dir is not None
        gate_file = gate.command_dir / GATE_FILE_NAME
        record_gate_skip(
            operation=operation,
            target_dir=start.resolve(),
            reason=skip_reason.strip(),
            gate_file=gate_file,
        )
        _warn(
            f"deploy gate skipped for '{operation}' by operator: {skip_reason.strip()}"
        )
        return

    assert gate.command is not None and gate.command_dir is not None
    argv = [*shlex.split(gate.command), operation]
    env = {
        **os.environ,
        "SBKUBE_GATE_OPERATION": operation,
        "SBKUBE_GATE_TARGET": str(start.resolve()),
    }
    try:
        result = subprocess.run(argv, cwd=gate.command_dir, env=env, check=False)
        returncode = result.returncode
        failure = f"exit code {returncode}"
    except OSError as e:
        returncode = None
        failure = str(e)

    if returncode == 0:
        return
    message = f"deploy gate refused '{operation}' ({failure}): {gate.command}"
    if gate.mode == "warn":
        _warn(f"{message} -- continuing because mode=warn")
        return
    raise DeployGateError(
        f"{message}. Fix the gate condition, or skip it as a human from a terminal "
        f"with --skip-deploy-gate=<reason>."
    )


def gate_callback(
    command_name: str, callback: Callable[..., Any]
) -> Callable[..., Any]:
    """Wrap a command callback so the gate runs before it."""

    def gated(*args: Any, **kwargs: Any) -> Any:
        global _gate_depth
        skip_reason = kwargs.pop(SKIP_OPTION_NAME, None)
        with _gate_depth_lock:
            outermost = _gate_depth == 0
            _gate_depth += 1
        try:
            if outermost:
                run_gate(command_name, kwargs, skip_reason)
            return callback(*args, **kwargs)
        finally:
            with _gate_depth_lock:
                _gate_depth -= 1

    gated.__sbkube_deploy_gate__ = True  # type: ignore[attr-defined]
    gated.__wrapped__ = callback  # type: ignore[attr-defined]
    return gated


def install_gate(command: click.Command) -> None:
    """Add ``--skip-deploy-gate`` and the gate wrapper to a mutating command."""
    if command.callback is None or getattr(
        command.callback, "__sbkube_deploy_gate__", False
    ):
        return
    command.params.append(
        click.Option(
            ["--skip-deploy-gate", SKIP_OPTION_NAME],
            metavar="REASON",
            default=None,
            help=(
                "Skip the deploy gate once (humans only, interactive terminal, reason "
                "recorded in the state DB)."
            ),
        )
    )
    command.callback = gate_callback(command.name or "", command.callback)


def is_gated(command: click.Command) -> bool:
    return bool(getattr(command.callback, "__sbkube_deploy_gate__", False))
