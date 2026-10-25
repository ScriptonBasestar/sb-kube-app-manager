"""Human-only access RBAC initialization and credential revocation."""

from pathlib import Path

import click
import yaml

from sbkube.commands.access import DEFAULT_CONFIG_FILE, _require_access, console
from sbkube.utils.access_issue import (
    TokenIssueError,
    dump_kubeconfig,
    ensure_private_dir,
    write_private_file,
)
from sbkube.utils.access_kubeconfig import KubeconfigError
from sbkube.utils.access_manage import (
    admin_session,
    check_readonly_secret,
    init_outputs,
    readonly_token,
    revoke_deployer,
)
from sbkube.utils.access_templates import (
    AccessTemplateError,
    access_manifests,
    readonly_secret_name,
)
from sbkube.utils.deploy_gate import _is_interactive, require_human_terminal


@click.command(name="init")
@click.option(
    "--print",
    "print_only",
    is_flag=True,
    help="RBAC 매니페스트만 출력합니다. 클러스터에 접속하지 않습니다.",
)
@click.option(
    "-f",
    "--file",
    "config_file",
    type=click.Path(path_type=Path, dir_okay=False),
    default=DEFAULT_CONFIG_FILE,
    show_default=True,
)
@click.pass_context
def init_cmd(ctx: click.Context, print_only: bool, config_file: Path) -> None:
    """RBAC과 읽기 전용 kubeconfig를 초기화합니다(사람 전용)."""
    settings, access = _require_access(config_file)
    try:
        manifests = yaml.safe_dump_all(access_manifests(access), sort_keys=False)
    except AccessTemplateError as e:
        raise click.ClickException(str(e)) from e
    if print_only:
        click.echo(manifests, nl=False)
        return
    require_human_terminal("sbkube access init", _is_interactive)
    applied = False
    attempted = False
    try:
        session = admin_session(settings, access, ctx.obj or {})
        outputs = init_outputs(access, session)
        session.verify()
        check_readonly_secret(session, access)
        # The built-in sequence keeps the existing polypia names and immutable roleRefs.
        attempted = True
        session.run(["apply", "-f", "-"], manifests)
        applied = True
        token = readonly_token(session, access)
        ensure_private_dir(outputs.readonly_token.parent)
        write_private_file(outputs.readonly_token, token + "\n")
        del token
        write_private_file(outputs.readonly, dump_kubeconfig(outputs.readonly_config))
        write_private_file(outputs.deployer, dump_kubeconfig(outputs.deployer_config))
    except (TokenIssueError, KubeconfigError) as e:
        state = (
            "RBAC was applied; credential files may be partially written"
            if applied
            else "apply may have partially changed RBAC"
            if attempted
            else "no cluster mutations attempted"
        )
        raise click.ClickException(f"{state}: {e}") from e
    console.print("[green]access RBAC and readonly credential initialized.[/green]")
    console.print(
        "deployer kubeconfig is ready; run `sbkube access issue` to issue a short-lived token, then `sbkube access verify`."
    )


@click.command(name="revoke")
@click.option(
    "--profile",
    type=click.Choice(["readonly", "deployer", "all"]),
    required=True,
    help="회수할 자격증명을 명시적으로 선택합니다.",
)
@click.option(
    "-f",
    "--file",
    "config_file",
    type=click.Path(path_type=Path, dir_okay=False),
    default=DEFAULT_CONFIG_FILE,
    show_default=True,
)
@click.pass_context
def revoke_cmd(ctx: click.Context, profile: str, config_file: Path) -> None:
    """읽기 전용 Secret 삭제 또는 deployer SA 재생성으로 토큰을 회수합니다."""
    require_human_terminal("sbkube access revoke", _is_interactive)
    settings, access = _require_access(config_file)
    completed: list[str] = []
    try:
        session = admin_session(settings, access, ctx.obj or {})
        session.verify()
        if profile in {"readonly", "all"}:
            check_readonly_secret(session, access)
            session.run(
                [
                    "-n",
                    access.namespace,
                    "delete",
                    "secret",
                    readonly_secret_name(access),
                    "--ignore-not-found",
                    "--wait=true",
                    "--timeout=20s",
                ]
            )
            completed.append("readonly Secret deleted")
        if profile in {"deployer", "all"}:
            revoke_deployer(session, access)
            completed.append("deployer ServiceAccount recreated")
    except (TokenIssueError, KubeconfigError) as e:
        state = (
            "; ".join(completed)
            or "revocation did not complete; the last API request may have changed state"
        )
        raise click.ClickException(f"{state}: {e}") from e
    console.print("[green]" + "; ".join(completed) + ".[/green]")
    console.print(
        "Local credential files are retained. Run init for readonly renewal, or issue for deployer renewal. Token rejection may take the API server's cache interval."
    )
