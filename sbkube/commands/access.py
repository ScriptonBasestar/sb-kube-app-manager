"""``sbkube access``: agent access boundary (readonly / deployer credentials).

Stage 1 is read-only: ``verify`` asks the API server what the readonly
credential may do, ``audit`` reports where admin-like credentials are reachable
without touching the cluster. Neither prints a credential value.
"""

import os
import subprocess
from dataclasses import dataclass
from pathlib import Path

import click
from rich.console import Console
from rich.markup import escape
from rich.table import Table

from sbkube.exceptions import SbkubeError
from sbkube.models.access_model import AccessPolicyRule, AccessSettings
from sbkube.models.unified_config_model import UnifiedConfig, UnifiedSettings
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
KUBECTL_TIMEOUT_SECONDS = 30

# What the readonly credential must (not) be able to do: (can-i args, expected).
BASE_CHECKS: tuple[tuple[tuple[str, ...], str], ...] = (
    (("get", "secrets", "-A"), "no"),
    (("list", "pods", "-A"), "yes"),
    (("list", "nodes"), "yes"),
    (("list", "customresourcedefinitions.apiextensions.k8s.io"), "yes"),
    (("create", "deployments.apps", "-A"), "no"),
    (("delete", "pods", "-A"), "no"),
)

# stderr fragments meaning kubectl could not get an answer from the API server.
_ERROR_MARKERS = (
    "unauthorized",
    "connection refused",
    "unable to connect",
    "dial tcp",
    "i/o timeout",
    "no such host",
    "token has expired",
    "token is expired",
    "expired",
    "must be logged in",
    "certificate",
)

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


@dataclass(frozen=True)
class CanIResult:
    """Outcome of one ``kubectl auth can-i``: ``yes``, ``no`` or ``error``."""

    answer: str
    detail: str = ""


def run_can_i(kubeconfig: Path, context: str, args: tuple[str, ...]) -> CanIResult:
    """Ask the API server via ``kubectl auth can-i``; errors are never a ``no``."""
    command = [
        "kubectl",
        "--kubeconfig",
        str(kubeconfig),
        "--context",
        context,
        "auth",
        "can-i",
        *args,
    ]
    try:
        proc = subprocess.run(  # noqa: S603
            command,
            capture_output=True,
            text=True,
            timeout=KUBECTL_TIMEOUT_SECONDS,
            check=False,
        )
    except FileNotFoundError:
        return CanIResult("error", "kubectl not found in PATH")
    except subprocess.TimeoutExpired:
        return CanIResult("error", f"kubectl timed out ({KUBECTL_TIMEOUT_SECONDS}s)")

    stdout = proc.stdout.strip()
    stderr = proc.stderr.strip()
    first_word = stdout.split(maxsplit=1)[0] if stdout else ""
    detail = (stderr.splitlines() or [""])[0][:200]

    if any(marker in stderr.lower() for marker in _ERROR_MARKERS):
        return CanIResult("error", detail)
    if proc.returncode == 0 and first_word == "yes":
        return CanIResult("yes")
    if proc.returncode == 1 and first_word == "no":
        return CanIResult("no")
    return CanIResult("error", detail or f"kubectl exited {proc.returncode}")


def _resource_targets(rule: AccessPolicyRule) -> list[tuple[str, ...]]:
    """can-i argument tails (after the verb) that a rule says must be allowed."""
    targets: list[tuple[str, ...]] = []
    for group in rule.api_groups or [""]:
        for resource in rule.resources:
            base, _, subresource = resource.partition("/")
            name = base if group in ("", "*") else f"{base}.{group}"
            flags = [f"--subresource={subresource}"] if subresource else []
            if rule.resource_names:
                targets.extend((f"{name}/{n}", *flags) for n in rule.resource_names)
            else:
                targets.append((name, "-A", *flags))
    targets.extend((url,) for url in rule.non_resource_urls)
    return targets


def build_checks(access: AccessSettings) -> list[tuple[tuple[str, ...], str]]:
    """Expected can-i table: the base table plus every ``extra_rules`` entry."""
    checks = list(BASE_CHECKS)
    for rule in access.readonly.extra_rules:
        for verb in rule.verbs:
            checks.extend(((verb, *tail), "yes") for tail in _resource_targets(rule))
    seen: set[tuple[str, ...]] = set()
    unique = []
    for args, expected in checks:
        if args not in seen:
            seen.add(args)
            unique.append((args, expected))
    return unique


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
    readonly_server = context_server(readonly_data, context)
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
    admin_server = context_server(admin_data, context)
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
    for args, expected in build_checks(access):
        result = run_can_i(readonly, context, args)
        if result.answer == "error":
            outcome, actual = "[red]ERROR[/red]", escape(result.detail or "error")
        elif result.answer == expected:
            outcome, actual = "[green]PASS[/green]", result.answer
        else:
            outcome, actual = "[red]FAIL[/red]", result.answer
        failed = failed or outcome != "[green]PASS[/green]"
        table.add_row(escape(" ".join(args)), expected, actual, outcome)
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
