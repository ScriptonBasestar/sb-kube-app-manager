import click
from pathlib import Path
from rich.console import Console

from sbkube.utils.common import run_command
from sbkube.utils.file_loader import load_config_file
from sbkube.utils.cli_check import check_helm_installed_or_exit, print_kube_connection_help
from sbkube.utils.helm_util import get_installed_charts
from sbkube.models.config_model import (
    AppInfoScheme,
    AppInstallHelmSpec,
    AppInstallActionSpec,
    AppExecSpec,
)

console = Console()

@click.command(name="deploy")
@click.option("--app-dir", default="config", help="앱 구성 디렉토리 (내부 config.yaml|yml|toml) 자동 탐색")
@click.option("--base-dir", default=".", help="프로젝트 루트 디렉토리 (기본: 현재 경로)")
@click.option("--dry-run", is_flag=True, default=False, help="실제로 적용하지 않고 dry-run")
@click.option("--app", "app_name", default=None, help="배포할 특정 앱 이름 (지정하지 않으면 모든 앱 배포)")
@click.option("--config-file", "config_file_name", default=None, help="사용할 설정 파일 이름 (app-dir 내부, 기본값: config.yaml 자동 탐색)")
@click.pass_context
def cmd(ctx, app_dir, base_dir, dry_run, app_name, config_file_name):
    """Helm chart 및 YAML, exec 명령을 클러스터에 적용"""
    check_helm_installed_or_exit()

    cli_namespace = ctx.obj.get('namespace')

    BASE_DIR = Path(base_dir).resolve()
    app_config_path_obj = Path(app_dir)
    BUILD_DIR = BASE_DIR / app_config_path_obj / "build"
    VALUES_DIR = BASE_DIR / app_config_path_obj / "values"

    config_file_path = None
    if config_file_name:
        config_file_path = (BASE_DIR / app_config_path_obj / config_file_name).resolve()
        if not config_file_path.exists() or not config_file_path.is_file():
            console.print(f"[red]❌ 지정된 설정 파일을 찾을 수 없습니다: {config_file_path}[/red]")
            raise click.Abort()
    else:
        for ext in [".yaml", ".yml", ".toml"]:
            candidate = (BASE_DIR / app_config_path_obj / f"config{ext}").resolve()
            if candidate.exists():
                config_file_path = candidate
                break

        if not config_file_path or not config_file_path.exists():
            console.print(f"[red]❌ 앱 설정 파일이 존재하지 않습니다: {BASE_DIR / app_config_path_obj}/config.[yaml|yml|toml][/red]")
            raise click.Abort()

    apps_config_dict = load_config_file(str(config_file_path))

    apps_to_deploy = []
    for app_dict in apps_config_dict.get("apps", []):
        try:
            app_info = AppInfoScheme(**app_dict)
            if app_name is None or app_info.name == app_name:
                apps_to_deploy.append(app_info)
        except Exception as e:
            app_name_for_error = app_dict.get('name', '알 수 없는 앱')
            console.print(f"[red]❌ 앱 정보 '{app_name_for_error}' 처리 중 오류 발생 (AppInfoScheme 변환 실패): {e}[/red]")
            console.print(f"    [yellow]L 해당 앱 설정을 건너뜁니다: {app_dict}[/yellow]")
            continue

    if app_name is not None and not apps_to_deploy:
        console.print(f"[red]❌ 지정된 앱 '{app_name}'을 찾을 수 없습니다.[/red]")
        raise click.Abort()

    if not apps_to_deploy:
        console.print("[yellow]⚠️ 배포할 앱이 설정 파일에 없습니다.[/yellow]")
        return

    for app_info in apps_to_deploy:
        app_type = app_info.type
        name = app_info.name
        
        current_ns = None
        if cli_namespace:
            current_ns = cli_namespace
        elif app_info.namespace and app_info.namespace not in ["!ignore", "!none", "!false", ""]:
            current_ns = app_info.namespace
        elif apps_config_dict.get("namespace") and apps_config_dict.get("namespace") not in ["!ignore", "!none", "!false", ""]:
            current_ns = apps_config_dict.get("namespace")

        spec_obj = None
        try:
            if app_type == "install-helm":
                spec_obj = AppInstallHelmSpec(**app_info.specs)
            elif app_type == "install-yaml":
                spec_obj = AppInstallActionSpec(**app_info.specs)
            elif app_type == "exec":
                spec_obj = AppExecSpec(**app_info.specs)
            else:
                continue
        except Exception as e:
            console.print(f"[red]❌ 앱 '{name}' (타입: {app_type})의 Spec 데이터 검증/변환 중 오류: {e}[/red]")
            console.print(f"    [yellow]L 해당 앱 설정을 건너뜁니다. Specs: {app_info.specs}[/yellow]")
            continue
        
        console.print(f"[magenta]➡️  앱 '{name}' (타입: {app_type}, 네임스페이스: {current_ns or '기본값'}) 배포 시작[/magenta]")

        if app_type == "install-helm":
            release_name = app_info.path or name
            chart_path_in_build = app_info.path or name
            chart_dir_to_install = BUILD_DIR / chart_path_in_build

            if not chart_dir_to_install.exists():
                console.print(f"[red]❌ 앱 '{name}': Helm 차트 디렉토리가 빌드 위치에 존재하지 않습니다: {chart_dir_to_install}[/red]")
                console.print(f"    [yellow]L 'sbkube build' 명령을 먼저 실행했는지 확인하세요.[/yellow]")
                continue

            is_installed = release_name in get_installed_charts(current_ns) if current_ns else False
            if is_installed:
                console.print(f"[yellow]⚠️  앱 '{name}': Helm 릴리스 '{release_name}'(ns: {current_ns or 'default'})가 이미 설치되어 있습니다. 건너뜁니다.[/yellow]")
                continue

            helm_cmd_list = ["helm", "install", release_name, str(chart_dir_to_install)]
            if current_ns:
                helm_cmd_list.extend(["--namespace", current_ns, "--create-namespace"])
            else:
                helm_cmd_list.append("--create-namespace")

            for vf_rel_path in spec_obj.values:
                abs_vf_path = Path(vf_rel_path) if Path(vf_rel_path).is_absolute() else VALUES_DIR / vf_rel_path
                if abs_vf_path.exists():
                    helm_cmd_list.extend(["--values", str(abs_vf_path)])
                    console.print(f"    [green]✓ values 파일 사용: {abs_vf_path}[/green]")
                else:
                    console.print(f"    [yellow]⚠️  values 파일 없음 (건너뜀): {abs_vf_path}[/yellow]")
            
            if dry_run:
                helm_cmd_list.append("--dry-run")

            console.print(f"    [cyan]$ {' '.join(helm_cmd_list)}[/cyan]")
            return_code, stdout, stderr = run_command(helm_cmd_list, check=False)

            if return_code != 0:
                console.print(f"[red]❌ 앱 '{name}': Helm 작업 실패 (릴리스: {release_name}):[/red]")
                if stdout: console.print(f"    [blue]STDOUT:[/blue] {stdout.strip()}")
                if stderr: console.print(f"    [red]STDERR:[/red] {stderr.strip()}")
            else:
                ns_msg = f" (네임스페이스: {current_ns})" if current_ns else ""
                console.print(f"[bold green]✅ 앱 '{name}': Helm 릴리스 '{release_name}' 배포 완료{ns_msg}[/bold green]")

        elif app_type == "install-yaml":
            for action_spec in spec_obj.actions:
                action_type = action_spec.type
                action_path_str = action_spec.path
                
                target_yaml_path_str = ""
                if action_path_str.startswith("http://") or action_path_str.startswith("https://"):
                    target_yaml_path_str = action_path_str
                    console.print(f"    [grey]URL에서 YAML 처리 시도: {target_yaml_path_str}[/grey]")
                else:
                    path_candidate = BASE_DIR / app_config_path_obj / action_path_str
                    if Path(action_path_str).is_absolute():
                         target_yaml_path_str = action_path_str
                    elif path_candidate.exists():
                         target_yaml_path_str = str(path_candidate.resolve())
                    else:
                         base_dir_candidate = BASE_DIR / action_path_str
                         if base_dir_candidate.exists():
                              target_yaml_path_str = str(base_dir_candidate.resolve())
                         else:
                              console.print(f"[red]❌ 앱 '{name}': YAML 파일 경로를 확인할 수 없습니다: '{action_path_str}'. 관련 경로들을 확인하세요.[/red]")
                              console.print(f"    [yellow]L 확인한 경로: 절대경로, {path_candidate}, {base_dir_candidate}[/yellow]")
                              continue

                if not target_yaml_path_str:
                    continue

                kubectl_cmd_list = ["kubectl"]
                if action_type in ["apply", "create", "delete"]:
                    kubectl_cmd_list.append(action_type)
                    kubectl_cmd_list.extend(["-f", target_yaml_path_str])
                else:
                    console.print(f"[red]❌ 앱 '{name}': 지원하지 않는 YAML 액션 타입 '{action_type}' 입니다. (지원: apply, create, delete)[/red]")
                    continue
                
                if current_ns:
                    kubectl_cmd_list.extend(["-n", current_ns])
                
                if dry_run:
                    kubectl_cmd_list.append("--dry-run=client")

                console.print(f"    [cyan]$ {' '.join(kubectl_cmd_list)}[/cyan]")
                return_code, stdout, stderr = run_command(kubectl_cmd_list, check=False)

                if return_code != 0:
                    if "Unable to connect to the server" in stderr or "no such host" in stderr:
                        print_kube_connection_help()
                    console.print(f"[red]❌ 앱 '{name}': YAML 작업 ('{action_type}' on '{target_yaml_path_str}') 실패:[/red]")
                    if stdout: console.print(f"    [blue]STDOUT:[/blue] {stdout.strip()}")
                    if stderr: console.print(f"    [red]STDERR:[/red] {stderr.strip()}")
                else:
                    console.print(f"[green]✅ 앱 '{name}': YAML 작업 ('{action_type}' on '{target_yaml_path_str}') 완료[/green]")

        elif app_type == "exec":
            for raw_cmd_str in spec_obj.commands:
                console.print(f"    [cyan]$ {raw_cmd_str}[/cyan]")
                return_code, stdout, stderr = run_command(raw_cmd_str, check=False, cwd=BASE_DIR)
                if return_code != 0:
                    console.print(f"[red]❌ 앱 '{name}': 명령어 실행 실패 ('{raw_cmd_str}'):[/red]")
                    if stdout: console.print(f"    [blue]STDOUT:[/blue] {stdout.strip()}")
                    if stderr: console.print(f"    [red]STDERR:[/red] {stderr.strip()}")
                else:
                    if stdout: console.print(f"    [grey]STDOUT:[/grey] {stdout.strip()}")
                    console.print(f"[green]✅ 앱 '{name}': 명령어 실행 완료 ('{raw_cmd_str}')[/green]")
        
        console.print("")

    console.print("[bold blue]✨ 모든 앱 배포 작업 완료 ✨[/bold blue]")