import click
from pathlib import Path
from rich.console import Console

from sbkube.utils.common import run_command
from sbkube.utils.file_loader import load_config_file
from sbkube.utils.cli_check import check_helm_installed_or_exit, check_kubectl_installed_or_exit
from sbkube.utils.helm_util import get_installed_charts
from sbkube.models.config_model import (
    AppInfoScheme,
    AppInstallHelmSpec,
    AppInstallActionSpec
)

console = Console()

def check_resource_exists(resource_type: str, resource_name: str, namespace: str | None) -> bool:
    """지정된 리소스가 Kubernetes 클러스터에 존재하는지 확인합니다."""
    cmd = ["kubectl", "get", resource_type, resource_name]
    if namespace:
        cmd.extend(["--namespace", namespace])
    return_code, stdout, _ = run_command(cmd, check=False, timeout=10)
    return return_code == 0 and resource_name in stdout

@click.command(name="delete")
@click.option("--app-dir", "app_config_dir_name", default="config", help="앱 설정 파일이 위치한 디렉토리 이름 (base-dir 기준)")
@click.option("--base-dir", default=".", type=click.Path(exists=True, file_okay=False, dir_okay=True), help="프로젝트 루트 디렉토리")
@click.option("--app", "target_app_name", default=None, help="특정 앱만 삭제 (지정하지 않으면 모든 앱 대상)")
@click.option("--skip-not-found", is_flag=True, help="삭제 대상 리소스가 없을 경우 오류 대신 건너뜁니다.")
@click.option("--config-file", "config_file_name", default=None, help="사용할 설정 파일 이름 (app-dir 내부, 기본값: config.yaml 자동 탐색)")
@click.pass_context
def cmd(ctx, app_config_dir_name: str, base_dir: str, target_app_name: str | None, skip_not_found: bool, config_file_name: str | None):
    """config.yaml/toml에 정의된 애플리케이션을 삭제합니다 (Helm 릴리스, Kubectl 리소스 등)."""
    console.print(f"[bold blue]✨ `delete` 작업 시작 (앱 설정: '{app_config_dir_name}', 기준 경로: '{base_dir}') ✨[/bold blue]")

    cli_namespace = ctx.obj.get('namespace')

    BASE_DIR = Path(base_dir).resolve()
    APP_CONFIG_DIR = BASE_DIR / app_config_dir_name

    if not APP_CONFIG_DIR.is_dir():
        console.print(f"[red]❌ 앱 설정 디렉토리가 존재하지 않습니다: {APP_CONFIG_DIR}[/red]")
        raise click.Abort()

    config_file_path = None
    if config_file_name:
        config_file_path = APP_CONFIG_DIR / config_file_name
        if not config_file_path.exists() or not config_file_path.is_file():
            console.print(f"[red]❌ 지정된 설정 파일을 찾을 수 없습니다: {config_file_path}[/red]")
            raise click.Abort()
    else:
        for ext in [".yaml", ".yml", ".toml"]:
            candidate = APP_CONFIG_DIR / f"config{ext}"
            if candidate.exists() and candidate.is_file():
                config_file_path = candidate
                break
        
        if not config_file_path:
            console.print(f"[red]❌ 앱 목록 설정 파일을 찾을 수 없습니다: {APP_CONFIG_DIR}/config.[yaml|yml|toml][/red]")
            raise click.Abort()
    console.print(f"[green]ℹ️ 앱 목록 설정 파일 사용: {config_file_path}[/green]")

    apps_config_dict = load_config_file(str(config_file_path))
    global_namespace_from_config = apps_config_dict.get("config", {}).get("namespace")

    delete_total_apps = 0
    delete_success_apps = 0
    delete_skipped_apps = 0

    apps_to_process = []
    if target_app_name:
        found_target_app = False
        for app_dict in apps_config_dict.get("apps", []):
            if app_dict.get("name") == target_app_name:
                apps_to_process.append(app_dict)
                found_target_app = True
                break
        if not found_target_app:
            console.print(f"[red]❌ 삭제 대상 앱 '{target_app_name}'을(를) 설정 파일에서 찾을 수 없습니다.[/red]")
            raise click.Abort()
    else:
        apps_to_process = apps_config_dict.get("apps", [])

    if not apps_to_process:
        console.print("[yellow]⚠️ 설정 파일에 삭제할 앱이 정의되어 있지 않습니다.[/yellow]")
        console.print(f"[bold blue]✨ `delete` 작업 완료 (처리할 앱 없음) ✨[/bold blue]")
        return

    for app_dict in apps_to_process:
        try:
            app_info = AppInfoScheme(**app_dict)
        except Exception as e:
            app_name_for_error = app_dict.get('name', '알 수 없는 앱')
            console.print(f"[red]❌ 앱 정보 '{app_name_for_error}' 처리 중 오류 (AppInfoScheme 변환 실패): {e}[/red]")
            console.print(f"    [yellow]L 해당 앱 설정을 건너뜁니다.[/yellow]")
            delete_skipped_apps +=1
            continue
        
        if app_info.type not in ["install-helm", "install-yaml", "install-action"]:
            continue

        delete_total_apps += 1
        app_name = app_info.name
        app_type = app_info.type
        app_release_name = app_info.release_name or app_name

        console.print(f"[magenta]➡️  앱 '{app_name}' (타입: {app_type}, 릴리스명: '{app_release_name}') 삭제 시도...[/magenta]")

        current_namespace = None
        if app_info.namespace and app_info.namespace not in ["!ignore", "!none", "!false", ""]:
            current_namespace = app_info.namespace
        elif cli_namespace:
            current_namespace = cli_namespace
        elif global_namespace_from_config:
            current_namespace = global_namespace_from_config
        else:
            if app_type == "install-helm":
                 current_namespace = "default"

        if current_namespace:
            console.print(f"    [grey]ℹ️ 네임스페이스 사용: {current_namespace}[/grey]")
        else:
            console.print(f"    [grey]ℹ️ 네임스페이스 미지정 (현재 컨텍스트의 기본값 사용 또는 리소스에 따라 다름)[/grey]")

        delete_command_executed = False
        delete_successful_for_app = False

        if app_type == "install-helm":
            check_helm_installed_or_exit()
            installed_charts = get_installed_charts(current_namespace)
            if app_release_name not in installed_charts:
                console.print(f"[yellow]⚠️ Helm 릴리스 '{app_release_name}'(네임스페이스: {current_namespace or '-'})가 설치되어 있지 않습니다.[/yellow]")
                if skip_not_found:
                    console.print(f"    [grey]L `--skip-not-found` 옵션으로 건너뜁니다.[/grey]")
                    delete_skipped_apps += 1
                    console.print("")
                    continue
                else:
                    delete_skipped_apps +=1
                    console.print("")
                    continue
            
            helm_cmd = ["helm", "uninstall", app_release_name]
            if current_namespace:
                helm_cmd.extend(["--namespace", current_namespace])
            
            console.print(f"    [cyan]$ {' '.join(helm_cmd)}[/cyan]")
            return_code, stdout, stderr = run_command(helm_cmd, check=False, timeout=300)
            if return_code == 0:
                console.print(f"[green]✅ Helm 릴리스 '{app_release_name}' 삭제 완료.[/green]")
                if stdout: console.print(f"    [grey]Helm STDOUT: {stdout.strip()}[/grey]")
                delete_successful_for_app = True
                delete_command_executed = True
            else:
                console.print(f"[red]❌ Helm 릴리스 '{app_release_name}' 삭제 실패:[/red]")
                if stdout: console.print(f"    [blue]STDOUT:[/blue] {stdout.strip()}")
                if stderr: console.print(f"    [red]STDERR:[/red] {stderr.strip()}")

        elif app_type == "install-yaml":
            check_kubectl_installed_or_exit()
            spec_obj = None
            if app_info.specs:
                try:
                    spec_obj = AppInstallActionSpec(**app_info.specs)
                except Exception as e:
                    console.print(f"[red]❌ 앱 '{app_name}': YAML Spec 정보 파싱 실패 (무시하고 진행): {e}[/red]")
                    spec_obj = AppInstallActionSpec(actions=[])
            else:
                console.print(f"[yellow]⚠️ 앱 '{app_name}': YAML Spec 정보('actions')가 없어 삭제할 파일 목록을 알 수 없습니다. 건너뜁니다.[/yellow]")
                delete_skipped_apps += 1
                console.print("")
                continue

            if not spec_obj or not spec_obj.actions:
                console.print(f"[yellow]⚠️ 앱 '{app_name}': 삭제할 YAML 파일 액션('actions')이 지정되지 않았습니다. 건너뜁니다.[/yellow]")
                delete_skipped_apps += 1
                console.print("")
                continue

            yaml_delete_successful_files = 0
            yaml_delete_failed_files = 0

            for action in reversed(spec_obj.actions):
                if action.type not in ["apply", "create"]:
                    continue
                
                file_path = Path(action.path)
                abs_yaml_path = file_path
                if not abs_yaml_path.is_absolute():
                    abs_yaml_path = APP_CONFIG_DIR / file_path
                
                if not abs_yaml_path.exists() or not abs_yaml_path.is_file():
                    console.print(f"    [yellow]⚠️ YAML 삭제 대상 파일을 찾을 수 없음 (건너뜀): {abs_yaml_path}[/yellow]")
                    yaml_delete_failed_files +=1
                    continue

                kubectl_cmd = ["kubectl", "delete", "-f", str(abs_yaml_path)]
                if current_namespace:
                    kubectl_cmd.extend(["--namespace", current_namespace])
                if skip_not_found:
                    kubectl_cmd.append("--ignore-not-found=true")

                console.print(f"    [cyan]$ {' '.join(kubectl_cmd)}[/cyan]")
                return_code, stdout, stderr = run_command(kubectl_cmd, check=False, timeout=120)
                if return_code == 0:
                    console.print(f"[green]    ✅ YAML '{abs_yaml_path.name}' 삭제 요청 성공.[/green]")
                    if stdout: console.print(f"        [grey]Kubectl STDOUT: {stdout.strip()}[/grey]")
                    yaml_delete_successful_files += 1
                    delete_command_executed = True
                else:
                    console.print(f"[red]    ❌ YAML '{abs_yaml_path.name}' 삭제 실패:[/red]")
                    if stdout: console.print(f"        [blue]STDOUT:[/blue] {stdout.strip()}")
                    if stderr: console.print(f"        [red]STDERR:[/red] {stderr.strip()}")
                    yaml_delete_failed_files +=1
            
            if yaml_delete_failed_files == 0 and yaml_delete_successful_files > 0:
                delete_successful_for_app = True
            elif yaml_delete_failed_files == 0 and yaml_delete_successful_files == 0 and not delete_command_executed:
                if skip_not_found:
                    delete_successful_for_app = True 
                    console.print(f"    [yellow]ℹ️ 앱 '{app_name}': 모든 YAML 리소스가 이미 삭제되었거나 대상이 없었습니다 (skip-not-found).[/yellow]")
            
            console.print(f"    [grey]YAML 삭제 요약 (파일 기준): 성공 {yaml_delete_successful_files}, 실패 {yaml_delete_failed_files}[/grey]")

        elif app_type == "install-action":
            spec_obj = None
            uninstall_action_defined = False
            if app_info.specs:
                try:
                    spec_obj = AppInstallActionSpec(**app_info.specs)
                    if spec_obj.uninstall and spec_obj.uninstall.get("script"):
                        uninstall_action_defined = True
                except Exception as e:
                    console.print(f"[red]❌ 앱 '{app_name}': Action Spec 정보 파싱 실패: {e}[/red]")

            if not uninstall_action_defined:
                console.print(f"[yellow]⚠️ 앱 '{app_name}' (타입: {app_type}): `specs.uninstall.script`가 정의되지 않아 자동으로 삭제할 수 없습니다. 건너뜁니다.[/yellow]")
                delete_skipped_apps += 1
                console.print("")
                continue

            for raw_cmd_str in spec_obj.uninstall.get("script", []):
                console.print(f"    [cyan]$ {raw_cmd_str}[/cyan]")
                return_code, stdout, stderr = run_command(raw_cmd_str, check=False, cwd=BASE_DIR)
                if return_code != 0:
                    console.print(f"[red]❌ 앱 '{app_name}': uninstall 스크립트 실행 실패 ('{raw_cmd_str}'):[/red]")
                    if stdout: console.print(f"    [blue]STDOUT:[/blue] {stdout.strip()}")
                    if stderr: console.print(f"    [red]STDERR:[/red] {stderr.strip()}")
                    delete_successful_for_app = False
                    break
                else:
                    if stdout: console.print(f"    [grey]STDOUT:[/grey] {stdout.strip()}")
                    console.print(f"[green]✅ 앱 '{app_name}': uninstall 스크립트 실행 완료 ('{raw_cmd_str}')[/green]")
                    delete_successful_for_app = True
            delete_command_executed = True 

        else:
            console.print(f"[yellow]⚠️ 앱 '{app_name}' (타입: {app_type}): 이 타입에 대한 자동 삭제 로직이 아직 정의되지 않았습니다. 건너뜁니다.[/yellow]")
            delete_skipped_apps += 1
            console.print("")
            continue

        if delete_successful_for_app:
            delete_success_apps += 1
        elif not delete_command_executed and skip_not_found:
            delete_success_apps +=1

        console.print("")

    console.print(f"[bold blue]✨ `delete` 작업 요약 ✨[/bold blue]")
    if delete_total_apps > 0:
        console.print(f"[green]    총 {delete_total_apps}개 앱 대상 중 {delete_success_apps}개 삭제 성공 (또는 이미 삭제됨).[/green]")
        if delete_skipped_apps > 0:
            console.print(f"[yellow]    {delete_skipped_apps}개 앱 건너뜀 (지원되지 않는 타입, 설정 오류, 리소스 없음 등).[/yellow]")
        if (delete_total_apps - delete_success_apps - delete_skipped_apps) > 0:
             console.print(f"[red]    {delete_total_apps - delete_success_apps - delete_skipped_apps}개 앱 삭제 실패.[/red]")
    elif target_app_name and not apps_to_process:
        pass 
    else:
        console.print("[yellow]    삭제할 대상으로 지정된 앱이 없었습니다.[/yellow]")
    console.print(f"[bold blue]✨ `delete` 작업 완료 ✨[/bold blue]")
