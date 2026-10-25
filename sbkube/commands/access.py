"""``sbkube access``: agent access boundary (readonly / deployer credentials).

Stage 1 is read-only: ``verify`` asks the API server what the readonly
credential may do, ``audit`` reports where admin-like credentials are reachable
without touching the cluster. Neither prints a credential value.
"""

import os
from dataclasses import dataclass
from pathlib import Path

import click
from rich.console import Console
from rich.markup import escape
from rich.table import Table

from sbkube.exceptions import SbkubeError
from sbkube.models.access_model import AccessSettings
from sbkube.models.unified_config_model import UnifiedConfig, UnifiedSettings
from sbkube.utils.access_checks import (
    OUTCOME_STYLE,
    PASS,
    verify_rows,
)
from sbkube.utils.access_kubeconfig import (
    CLIENT_CERT,
    KubeconfigError,
    KubeconfigUser,
    context_names,
    context_server,
    list_users,
    read_kubeconfig,
)
from sbkube.utils.file_loader import load_config_file

DEFAULT_CONFIG_FILE = "sbkube.yaml"
console = Console()


@click.group(name="access")
def cmd() -> None:
    """에이전트 접근 경계(읽기 전용/배포 자격증명)를 점검합니다."""


# ---------------------------------------------------------------------------
# Settings loading
# ---------------------------------------------------------------------------


def _load_settings(config_file: Path) -> UnifiedSettings:
    """Global settings of a unified ``sbkube.yaml``."""
    try:
        data = load_config_file(str(config_file))
        if not str(data.get("apiVersion", "")).startswith("sbkube/"):
            raise click.ClickException(
                f"{config_file} is not a unified sbkube config (apiVersion: sbkube/v1)."
            )
        return UnifiedConfig(**data).settings
    except SbkubeError as e:
        raise click.ClickException(f"cannot load {config_file}: {e}") from e


def _require_access(config_file: Path) -> tuple[UnifiedSettings, AccessSettings]:
    if not config_file.is_file():
        raise click.ClickException(f"config file not found: {config_file}")
    settings = _load_settings(config_file)
    if settings.access is None:
        raise click.ClickException(
            f"{config_file} has no settings.access block; nothing to verify."
        )
    return settings, settings.access


def _expand(path: str) -> Path:
    return Path(path).expanduser()


# ---------------------------------------------------------------------------
# verify
# ---------------------------------------------------------------------------


def _sanity_check(readonly: Path, admin: Path | None, context: str) -> str | None:
    """Cluster-free check; returns a failure message or ``None``."""
    if not readonly.is_file():
        return f"readonly kubeconfig not found: {readonly}"
    try:
        readonly_data = read_kubeconfig(readonly)
    except KubeconfigError as e:
        return str(e)
    if context not in context_names(readonly_data):
        return f"context {context!r} not found in readonly kubeconfig {readonly}"
    try:
        readonly_server = context_server(readonly_data, context, readonly)
    except KubeconfigError as e:
        return str(e)
    if readonly_server is None:
        return f"context {context!r} in {readonly} has no single cluster server"

    if admin is None or not admin.is_file():
        return (
            "admin kubeconfig (settings.kubeconfig) not found; "
            "cannot compare the API server"
        )
    try:
        admin_data = read_kubeconfig(admin)
    except KubeconfigError as e:
        return str(e)
    try:
        admin_server = context_server(admin_data, context, admin)
    except KubeconfigError as e:
        return str(e)
    if admin_server is None:
        return f"context {context!r} not found in admin kubeconfig {admin}"
    if readonly_server != admin_server:
        return (
            f"API server mismatch for context {context!r}: readonly kubeconfig "
            f"points at {readonly_server}, admin kubeconfig at {admin_server}"
        )
    return None


@cmd.command(name="verify")
@click.option(
    "-f",
    "--file",
    "config_file",
    type=click.Path(path_type=Path, dir_okay=False),
    default=DEFAULT_CONFIG_FILE,
    show_default=True,
    help="sbkube.yaml 경로.",
)
@click.pass_context
def verify(ctx: click.Context, config_file: Path) -> None:
    """읽기 전용 자격증명이 기대한 권한만 갖는지 `kubectl auth can-i`로 확인합니다.

    클러스터를 바꾸지 않습니다. 하나라도 어긋나거나 확인하지 못하면 종료 코드 1입니다.
    """
    settings, access = _require_access(config_file)
    obj = ctx.obj or {}
    if access.readonly.kubeconfig is None:
        raise click.ClickException(
            "settings.access.readonly.kubeconfig is not set; nothing to verify."
        )
    context = obj.get("context") or settings.kubeconfig_context
    if not context:
        raise click.ClickException(
            "no context: set settings.kubeconfig_context or pass --context."
        )
    admin_path = obj.get("kubeconfig") or settings.kubeconfig
    readonly = _expand(access.readonly.kubeconfig)

    problem = _sanity_check(
        readonly, _expand(admin_path) if admin_path else None, context
    )
    if problem is not None:
        console.print(f"[red]FAIL[/red] {escape(problem)}")
        ctx.exit(1)

    table = Table(title=f"readonly access: {readonly} (context {context})")
    for column in ("check", "expected", "actual", "result"):
        table.add_column(column)
    failed = False
    for check, expected, actual, passed in verify_rows(readonly, context, access):
        failed = failed or passed != PASS
        table.add_row(escape(check), expected, escape(actual), OUTCOME_STYLE[passed])
    console.print(table)

    if failed:
        console.print(
            "[red]readonly credential does not match the expected access.[/red]"
        )
        ctx.exit(1)
    console.print("[green]readonly credential matches the expected access.[/green]")


# ---------------------------------------------------------------------------
# audit
# ---------------------------------------------------------------------------


@dataclass
class _AuditFile:
    path: Path
    roles: list[str]


def _kubeconfig_env_files() -> list[Path]:
    raw = os.environ.get("KUBECONFIG", "")
    if raw:
        return [_expand(p) for p in raw.split(os.pathsep) if p]
    default = Path("~/.kube/config").expanduser()
    return [default] if default.exists() else []


def _collect_audit_files(
    settings: UnifiedSettings | None,
) -> list[_AuditFile]:
    files: dict[Path, _AuditFile] = {}

    def add(path: Path, role: str) -> None:
        entry = files.setdefault(path.resolve(), _AuditFile(path, []))
        if role not in entry.roles:
            entry.roles.append(role)

    for path in _kubeconfig_env_files():
        add(path, "KUBECONFIG")
    if settings is not None:
        if settings.kubeconfig:
            add(_expand(settings.kubeconfig), "settings.kubeconfig")
        if settings.access and settings.access.readonly.kubeconfig:
            add(_expand(settings.access.readonly.kubeconfig), "access.readonly")
    return list(files.values())


def _admin_users_for(
    users: list[KubeconfigUser], data: dict, context: str | None
) -> list[KubeconfigUser]:
    """Client-cert users the sbkube context would use (all, if it is unknown)."""
    admin = [u for u in users if u.admin_like]
    wanted = context or data.get("current-context")
    if not isinstance(wanted, str):
        return admin
    return [u for u in admin if wanted in u.contexts]


@cmd.command(name="audit")
@click.option(
    "-f",
    "--file",
    "config_file",
    type=click.Path(path_type=Path, dir_okay=False),
    default=DEFAULT_CONFIG_FILE,
    show_default=True,
    help="sbkube.yaml 경로 (없으면 설정 검사를 건너뜁니다).",
)
@click.option(
    "--strict",
    is_flag=True,
    help="관리자 수준 자격증명 발견 시 종료 코드 1.",
)
@click.pass_context
def audit(ctx: click.Context, config_file: Path, strict: bool) -> None:
    """관리자 수준 자격증명이 닿는 경로를 보고합니다 (클러스터 호출 없음, 값은 출력하지 않음)."""
    settings: UnifiedSettings | None = None
    if config_file.is_file():
        settings = _load_settings(config_file)
    else:
        console.print(
            f"[yellow]{escape(str(config_file))} not found; skipping settings checks.[/yellow]"
        )
    access_configured = settings is not None and settings.access is not None

    table = Table(title="kubeconfig credentials")
    for column in ("file", "reached via", "user", "credential", "contexts"):
        table.add_column(column)
    findings: list[str] = []
    problems: list[str] = []

    for entry in _collect_audit_files(settings):
        try:
            data = read_kubeconfig(entry.path)
        except KubeconfigError as e:
            problems.append(str(e))
            continue
        users = list_users(data)
        via = ", ".join(entry.roles)
        for user in users:
            table.add_row(
                escape(str(entry.path)),
                via,
                escape(user.name),
                user.credential,
                escape(", ".join(user.contexts) or "-"),
            )
        admin = [u for u in users if u.admin_like]
        label = str(entry.path)

        if "KUBECONFIG" in entry.roles:
            findings.extend(
                f"KUBECONFIG reaches {CLIENT_CERT} user {u.name!r} in {label}"
                for u in admin
            )
        if "settings.kubeconfig" in entry.roles and access_configured:
            context = settings.kubeconfig_context if settings else None
            findings.extend(
                f"settings.kubeconfig {label} uses {CLIENT_CERT} user {u.name!r} "
                "while settings.access is configured (agents run as admin)"
                for u in _admin_users_for(users, data, context)
            )
        if "access.readonly" in entry.roles:
            findings.extend(
                f"access.readonly.kubeconfig {label} contains {CLIENT_CERT} "
                f"user {u.name!r}"
                for u in admin
            )

    console.print(table)
    for problem in problems:
        console.print(f"[yellow]unreadable:[/yellow] {escape(problem)}")
    if findings:
        console.print("[red]findings:[/red]")
        for finding in findings:
            console.print(f"  - {escape(finding)}")
    else:
        console.print("[green]no admin-like credential reachable.[/green]")

    if strict and findings:
        ctx.exit(1)
