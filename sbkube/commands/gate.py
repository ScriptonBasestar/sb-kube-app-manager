"""``sbkube gate``: human-side controls of the deploy gate."""

import os
from pathlib import Path

import click

from sbkube.utils.datetime_utils import utc_now
from sbkube.utils.deploy_gate import (
    DeployGateError,
    _is_interactive,
    find_gate_files,
    process_lineage,
    process_table,
    record_gate_grant,
    resolve_gate,
)
from sbkube.utils.deploy_gate_config import GATE_FILE_NAME, parse_grant_ttl


@click.group(name="gate")
def cmd() -> None:
    """배포 게이트를 사람이 제어합니다."""


@cmd.command(name="grant")
@click.option(
    "--pid",
    type=int,
    required=True,
    help="권한을 줄 에이전트 세션 프로세스 PID (예: Claude Code의 CLAUDE_PID).",
)
@click.option("--reason", required=True, help="기록할 사유.")
@click.option(
    "--target",
    type=click.Path(exists=True, file_okay=False, path_type=Path),
    default=Path(),
    show_default=True,
    help="게이트 파일을 찾을 디렉토리.",
)
def grant(pid: int, reason: str, target: Path) -> None:
    """에이전트 세션이 게이트 명령 없이 배포하도록 허용합니다 (사람이 터미널에서 실행).

    허용은 그 PID에서 파생된 프로세스에만 적용되며, 전역 sbkube-gate.yaml의
    deploy_gate.agent_grant.ttl이 지나거나 (unlimited면) 그 프로세스가
    끝나면 사라집니다.
    """
    if not reason.strip():
        raise click.UsageError("--reason must not be empty.")
    if not _is_interactive():
        raise click.UsageError(
            "sbkube gate grant is only accepted from an interactive terminal "
            "(stdin and stderr must be a TTY)."
        )
    gate = resolve_gate(*find_gate_files(target))
    if gate is None or gate.command_dir is None:
        raise click.UsageError(f"no deploy gate is configured for {target}.")
    if gate.agent_grant is None:
        raise click.UsageError(
            f"{gate.command_dir / GATE_FILE_NAME} does not enable agent grants "
            "(deploy_gate.agent_grant)."
        )

    table = process_table()
    if pid <= 1 or pid not in table:
        raise DeployGateError(f"no running process with PID {pid}.")
    # Granting an ancestor of this terminal would cover the operator's own
    # shell and everything started from it.
    if any(ancestor == pid for ancestor, _ in process_lineage(table, os.getpid())):
        raise DeployGateError(
            f"PID {pid} is an ancestor of this terminal; grant the agent's "
            "session process instead."
        )

    ttl = parse_grant_ttl(gate.agent_grant.ttl)
    expires_at = None if ttl is None else utc_now() + ttl
    record_gate_grant(
        gate_dir=gate.command_dir.resolve(),
        pid=pid,
        pid_started=table[pid][1],
        expires_at=expires_at,
        reason=reason.strip(),
    )
    until = (
        f"until PID {pid} ends"
        if expires_at is None
        else f"until {expires_at:%Y-%m-%d %H:%M} UTC or PID {pid} ends"
    )
    click.echo(f"agent grant for PID {pid} on {gate.command_dir}: {until}")
