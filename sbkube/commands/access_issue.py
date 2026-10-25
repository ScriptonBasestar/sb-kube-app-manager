"""``sbkube access issue``: mint a short-lived deployer token (human only)."""

from datetime import timedelta
from pathlib import Path

import click
from rich.markup import escape

from sbkube.commands.access import (
    DEFAULT_CONFIG_FILE,
    _expand,
    _require_access,
    console,
)
from sbkube.models.access_model import MIN_TOKEN_TTL_SECONDS, parse_go_duration_seconds
from sbkube.utils.access_checks import run_can_i
from sbkube.utils.access_issue import (
    TOKEN_FILE_NAME,
    TokenIssueError,
    build_deployer_kubeconfig,
    dump_kubeconfig,
    ensure_private_dir,
    mint_token,
    overwrite_problem,
    same_file,
    write_private_file,
)
from sbkube.utils.access_kubeconfig import KubeconfigError, read_kubeconfig
from sbkube.utils.datetime_utils import utc_now_aware
from sbkube.utils.deploy_gate import _is_interactive, require_human_terminal


def _validated_ttl(ttl: str) -> tuple[str, float]:
    try:
        seconds = parse_go_duration_seconds(ttl)
    except ValueError as e:
        raise click.UsageError(f"--ttl: {e}") from e
    if seconds < MIN_TOKEN_TTL_SECONDS:
        raise click.UsageError(
            f"--ttl {ttl!r} is below the 10m minimum (TokenRequest expirationSeconds >= 600)"
        )
    return ttl, seconds


@click.command(name="issue")
@click.option(
    "--ttl",
    default=None,
    help="토큰 수명 (Go 형식, 최소 10m). 기본값은 settings.access.deployer.token_ttl.",
)
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
def issue(ctx: click.Context, ttl: str | None, config_file: Path) -> None:
    """배포용 ServiceAccount 토큰을 발급해 tokenFile과 deployer kubeconfig를 씁니다.

    사람이 터미널에서 실행합니다. 토큰은 출력하지 않고 mode 600 파일에만 둡니다.
    """
    require_human_terminal("sbkube access issue", _is_interactive)
    settings, access = _require_access(config_file)
    obj = ctx.obj or {}
    deployer = access.deployer
    if deployer.kubeconfig is None:
        raise click.ClickException(
            "settings.access.deployer.kubeconfig is not set; nowhere to write."
        )
    context = obj.get("context") or settings.kubeconfig_context
    if not context:
        raise click.ClickException(
            "no context: set settings.kubeconfig_context or pass --context."
        )
    admin_setting = obj.get("kubeconfig") or settings.kubeconfig
    if not admin_setting:
        raise click.ClickException(
            "no admin kubeconfig: set settings.kubeconfig or pass --kubeconfig."
        )
    duration, seconds = _validated_ttl(ttl if ttl is not None else deployer.token_ttl)

    admin = _expand(admin_setting)
    deployer_path = _expand(deployer.kubeconfig).absolute()
    token_path = (_expand(access.token_dir) / TOKEN_FILE_NAME).absolute()
    others = {"admin": admin}
    if access.readonly.kubeconfig:
        others["readonly"] = _expand(access.readonly.kubeconfig)
    for role, other in others.items():
        if same_file(deployer_path, other) or same_file(token_path, other):
            raise click.ClickException(
                f"deployer kubeconfig/token path must not be the {role} kubeconfig ({other})."
            )
    if not admin.is_file():
        raise click.ClickException(f"admin kubeconfig not found: {admin}")
    problem = overwrite_problem(deployer_path)
    if problem is not None:
        raise click.ClickException(problem)
    try:
        kubeconfig = build_deployer_kubeconfig(
            read_kubeconfig(admin), context, admin, token_path
        )
    except KubeconfigError as e:
        raise click.ClickException(str(e)) from e

    try:
        token = mint_token(
            admin, context, access.namespace, deployer.service_account, duration
        )
        ensure_private_dir(token_path.parent)
        write_private_file(token_path, token + "\n")
        del token
        write_private_file(deployer_path, dump_kubeconfig(kubeconfig))
    except TokenIssueError as e:
        raise click.ClickException(f"token not issued: {e}") from e

    expires = utc_now_aware() + timedelta(seconds=seconds)
    console.print(f"[green]token file[/green]  {escape(str(token_path))} (mode 600)")
    console.print(f"[green]kubeconfig[/green]  {escape(str(deployer_path))} (mode 600)")
    console.print(
        f"expires    {expires.astimezone():%Y-%m-%d %H:%M:%S %Z} "
        f"({expires:%Y-%m-%d %H:%M:%S} UTC); renew with `sbkube access issue`."
    )

    result = run_can_i(deployer_path, context, ("create", "deployments.apps", "-A"))
    console.print(f"can-i create deployments.apps -A: {escape(result.answer)}")
    if result.answer != "yes":
        detail = f" ({escape(result.detail)})" if result.detail else ""
        console.print(
            f"[red]deployer check failed{detail}[/red]: the token was written, but "
            "either the deployer ServiceAccount lacks rights or the cluster is unreachable."
        )
        ctx.exit(1)
    console.print("[green]deployer credential works.[/green]")
