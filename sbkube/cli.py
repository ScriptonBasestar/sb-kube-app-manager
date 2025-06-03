import click
import logging
from pathlib import Path
from rich.console import Console
from rich.table import Table

# kubernetes 패키지를 사용하기 위한 임포트
try:
    from kubernetes import config as kube_config
    from kubernetes.config.config_exception import ConfigException
    KUBERNETES_AVAILABLE = True
except ImportError:
    KUBERNETES_AVAILABLE = False

from sbkube.commands import prepare, build, template, deploy, upgrade, delete, validate, version
from sbkube.utils.cli_check import check_helm_installed_or_exit, check_kubectl_installed_or_exit
# 기존 print_kube_connection_help, print_helm_connection_help는 display_kubeconfig_info 및 SbkubeGroup.invoke에서 직접 처리 또는 대체


console = Console()

def display_kubeconfig_info(kubeconfig_path: str | None = None, context_name: str | None = None):
    """Kubeconfig 파일 정보를 파싱하여 현재 컨텍스트, 사용 가능한 컨텍스트 목록 및 연결 방법을 안내합니다."""
    if not KUBERNETES_AVAILABLE:
        console.print("[red]❌ `kubernetes` 파이썬 패키지를 찾을 수 없습니다.[/red]")
        console.print("   [yellow]L `pip install kubernetes` 또는 `poetry add kubernetes`로 설치해주세요.[/yellow]")
        return

    console.print("[bold blue]✨ Kubernetes 설정 정보 ✨[/bold blue]")
    resolved_kubeconfig_path = str(Path(kubeconfig_path).expanduser()) if kubeconfig_path else None
    default_kubeconfig_path_text = "~/.kube/config"
    if resolved_kubeconfig_path and Path(resolved_kubeconfig_path).is_absolute():
        default_kubeconfig_path_text = resolved_kubeconfig_path
    elif kubeconfig_path: # 상대경로 등이지만 명시된 경우
        default_kubeconfig_path_text = kubeconfig_path

    try:
        contexts, active_context = kube_config.list_kube_config_contexts(config_file=resolved_kubeconfig_path)
    except ConfigException as e:
        console.print(f"[yellow]⚠️ Kubeconfig 파일을 로드할 수 없습니다 (경로: {default_kubeconfig_path_text}).[/yellow]")
        console.print(f"   [dim]오류: {e}[/dim]")
        console.print("\n[bold yellow]💡 연결 방법 안내:[/bold yellow]")
        console.print("   1. KUBECONFIG 환경 변수를 설정하세요:")
        console.print("      [cyan]export KUBECONFIG=/path/to/your/kubeconfig[/cyan]")
        console.print("   2. 또는 `sbkube` 명령어에 옵션을 사용하세요:")
        console.print("      [cyan]sbkube --kubeconfig /path/to/your/kubeconfig <command>[/cyan]")
        console.print("      [cyan]sbkube --context <your_context_name> <command>[/cyan]")
        return
    except Exception as e:
        console.print(f"[red]❌ Kubeconfig 정보 로드 중 예상치 못한 오류 발생: {e}[/red]")
        return

    if not contexts:
        console.print(f"[yellow]⚠️ 사용 가능한 Kubernetes 컨텍스트가 Kubeconfig 파일({default_kubeconfig_path_text})에 없습니다.[/yellow]")
        return

    current_active_display_name = "N/A"
    if active_context:
        current_active_display_name = active_context.get('name', 'N/A')
    
    # 사용자가 --context 옵션으로 특정 컨텍스트를 지정한 경우, 해당 컨텍스트를 활성 컨텍스트처럼 강조
    specified_context_active = False
    if context_name and any(c.get('name') == context_name for c in contexts):
        current_active_display_name = context_name
        specified_context_active = True
        console.print(f"   [green]지정된 컨텍스트:[/green] [bold cyan]{current_active_display_name}[/bold cyan]")
    elif active_context:
        console.print(f"   [green]현재 활성 컨텍스트:[/green] [bold cyan]{current_active_display_name}[/bold cyan]")
        cluster_name = active_context.get('context', {}).get('cluster')
        if cluster_name:
             console.print(f"     [dim]└ Cluster: {cluster_name}[/dim]")
    else:
        console.print("   [yellow]⚠️ 활성 컨텍스트를 확인할 수 없습니다.[/yellow]")

    table = Table(title=f"사용 가능한 컨텍스트 (from: {default_kubeconfig_path_text})", show_lines=True)
    table.add_column("활성", style="magenta", justify="center")
    table.add_column("컨텍스트 이름", style="cyan", no_wrap=True)
    table.add_column("클러스터", style="green")
    table.add_column("사용자", style="yellow")
    table.add_column("네임스페이스", style="blue")

    for c_info in sorted(contexts, key=lambda x: x.get('name', '')):
        ctx_name = c_info.get('name', 'N/A')
        is_active_symbol = ""
        if specified_context_active and ctx_name == context_name:
            is_active_symbol = "* (지정됨)"
        elif not specified_context_active and active_context and active_context.get('name') == ctx_name:
            is_active_symbol = "*"
            
        cluster = c_info.get('context', {}).get('cluster', 'N/A')
        user = c_info.get('context', {}).get('user', 'N/A')
        namespace = c_info.get('context', {}).get('namespace', 'default')
        table.add_row(is_active_symbol, ctx_name, cluster, user, namespace)
    
    console.print(table)
    console.print("\n[bold yellow]💡 다른 컨텍스트 사용 방법:[/bold yellow]")
    console.print("   1. `kubectl`로 컨텍스트 변경:")
    console.print("      [cyan]kubectl config use-context <context_name>[/cyan]")
    console.print("   2. `sbkube` 명령어에 옵션 사용:")
    console.print("      [cyan]sbkube --context <context_name> <command>[/cyan]")
    console.print("   3. KUBECONFIG 환경 변수 (여러 파일 관리 시):")
    console.print("      [cyan]export KUBECONFIG=~/.kube/config:/path/to/other/config[/cyan]")
    console.print("      (이 경우 현재 활성 컨텍스트는 첫 번째 유효한 파일의 현재 컨텍스트를 따릅니다)")


class SbkubeGroup(click.Group):
    def invoke(self, ctx: click.Context):
        # 이 메소드는 invoke_without_command=True 와 main 콜백 로직에 의해
        # 실제 서브커맨드가 실행될 때만 호출됩니다.
        # 'sbkube' 단독 실행 시에는 main 콜백에서 display_kubeconfig_info() 실행 후 ctx.exit() 됩니다.

        if ctx.invoked_subcommand:
            # console.print(f"[SbkubeGroup.invoke] Prerequisite checks for: {ctx.invoked_subcommand}", style="dim")
            
            # Kubernetes/Helm 연결이 필요한 명령어들에 대해 검사 수행
            # 'version', 'validate', 'init' (향후), 'template' 등은 제외 가능
            # 'template'은 helm template을 사용하므로 helm은 필요하나 kubectl 연결은 필요 없을 수 있음.
            commands_requiring_kubectl_connection = ['deploy', 'upgrade', 'delete', 'prepare'] # prepare도 helm repo add/update 시 kubectl 설정에 민감할 수 있음
            commands_requiring_helm = ['template', 'deploy', 'upgrade', 'delete', 'prepare', 'build'] # build도 helm pull등을 위해

            if ctx.invoked_subcommand in commands_requiring_kubectl_connection:
                # console.print(f"[SbkubeGroup.invoke] Running kubectl checks for {ctx.invoked_subcommand}", style="dim")
                check_kubectl_installed_or_exit(kubeconfig=ctx.obj.get('kubeconfig'), kubecontext=ctx.obj.get('context'))
            
            if ctx.invoked_subcommand in commands_requiring_helm:
                # console.print(f"[SbkubeGroup.invoke] Running helm checks for {ctx.invoked_subcommand}", style="dim")
                check_helm_installed_or_exit()
        
        return super().invoke(ctx)

@click.group(cls=SbkubeGroup, invoke_without_command=True)
@click.option('--kubeconfig', envvar='KUBECONFIG', type=click.Path(exists=False, dir_okay=False, resolve_path=False),
              help='Kubernetes 설정 파일 경로. KUBECONFIG 환경변수보다 우선 적용됩니다.')
@click.option('--context', 
              help='사용할 Kubernetes 컨텍스트 이름. KUBECONTEXT 환경변수 또는 현재 활성 컨텍스트를 따릅니다.') # envvar='KUBECONTEXT' (표준은 아님)
@click.option('-v', '--verbose', is_flag=True, help="상세 로깅을 활성화합니다.")
@click.pass_context
def main(ctx: click.Context, kubeconfig: str | None, context: str | None, verbose: bool):
    """sbkube: Kubernetes 애플리케이션 관리를 위한 CLI 도구.\n\n    Helm 차트, YAML 매니페스트, Git 저장소 등을 사용하여 애플리케이션을 준비, 빌드, 배포, 업그레이드, 삭제합니다.\n    인수 없이 실행하면 현재 Kubernetes 설정 정보를 보여줍니다.
    """
    ctx.ensure_object(dict)
    ctx.obj['kubeconfig'] = kubeconfig
    ctx.obj['context'] = context # click이 자동으로 KUBECONTEXT envvar를 읽도록 하려면 envvar 지정 필요
    ctx.obj['verbose'] = verbose

    if verbose:
        # TODO: 로깅 레벨 및 포맷 설정 개선 (e.g., logging.getLogger("sbkube").setLevel)
        logging.basicConfig(level=logging.DEBUG, format='%(asctime)s - %(levelname)s - %(name)s - %(message)s')
        console.print("[dim]상세 로깅 활성화됨.[/dim]")

    if ctx.invoked_subcommand is None:
        # `sbkube`가 서브커맨드 없이 실행된 경우
        display_kubeconfig_info(kubeconfig_path=kubeconfig, context_name=context)
        ctx.exit() # 여기서 종료하여 도움말 등이 자동으로 뜨는 것을 방지

# 기존 명령어 추가 부분은 그대로 유지
main.add_command(prepare.cmd)
main.add_command(build.cmd)
main.add_command(template.cmd)
main.add_command(deploy.cmd)
main.add_command(upgrade.cmd)
main.add_command(delete.cmd)
main.add_command(validate.cmd)
main.add_command(version.cmd)

if __name__ == "__main__":
    main()
