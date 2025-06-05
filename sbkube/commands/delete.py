import subprocess
import click
from pathlib import Path
from rich.console import Console
import yaml # kubectl delete 시 YAML 파싱용

from sbkube.utils.file_loader import load_config_file
from sbkube.utils.cli_check import check_helm_installed_or_exit, check_kubectl_installed_or_exit
from sbkube.utils.helm_util import get_installed_charts
from sbkube.models.config_model import (
    AppInfoScheme,
    AppInstallHelmSpec,
    AppInstallKubectlSpec,
    AppInstallActionSpec # uninstall 액션 지원을 위해
)
from sbkube.models import get_spec_model

console = Console()

# kubectl get 함수 (리소스 존재 확인용)
def check_resource_exists(resource_type: str, resource_name: str, namespace: str | None) -> bool:
    """지정된 리소스가 Kubernetes 클러스터에 존재하는지 확인합니다."""
    cmd = ["kubectl", "get", resource_type, resource_name]
    if namespace:
        cmd.extend(["--namespace", namespace])
    try:
        result = subprocess.run(cmd, capture_output=True, text=True, check=False, timeout=10) # check=False로 오류 발생 안하게
        # console.print(f"[grey]kubectl get for {resource_type}/{resource_name} in ns '{namespace}': stdout: {result.stdout.strip()}, stderr: {result.stderr.strip()}, code: {result.returncode}[/grey]")
        return result.returncode == 0 and resource_name in result.stdout # 이름이 stdout에 포함되는지까지 확인
    except subprocess.TimeoutExpired:
        console.print(f"[yellow]⚠️ '{resource_type}/{resource_name}' 존재 확인 중 kubectl timeout.[/yellow]")
        return False
    except Exception as e:
        console.print(f"[yellow]⚠️ '{resource_type}/{resource_name}' 존재 확인 중 오류: {e}[/yellow]")
        return False

@click.command(name="delete")
@click.option("--app-dir", "app_config_dir_name", default="config", help="앱 설정 파일이 위치한 디렉토리 이름 (base-dir 기준)")
@click.option("--base-dir", default=".", type=click.Path(exists=True, file_okay=False, dir_okay=True), help="프로젝트 루트 디렉토리")
@click.option("--namespace", "cli_namespace", default=None, help="삭제 작업을 수행할 기본 네임스페이스 (없으면 앱별 설정 또는 최상위 설정 따름)")
@click.option("--app", "target_app_name", default=None, help="특정 앱만 삭제 (지정하지 않으면 모든 앱 대상)")
@click.option("--skip-not-found", is_flag=True, help="삭제 대상 리소스가 없을 경우 오류 대신 건너뜁니다.")
def cmd(app_config_dir_name: str, base_dir: str, cli_namespace: str | None, target_app_name: str | None, skip_not_found: bool):
    """config.yaml/toml에 정의된 애플리케이션을 삭제합니다 (Helm 릴리스, Kubectl 리소스 등)."""
    console.print(f"[bold blue]✨ `delete` 작업 시작 (앱 설정: '{app_config_dir_name}', 기준 경로: '{base_dir}') ✨[/bold blue]")
    # 필요한 CLI 도구 가용성 검사는 각 앱 타입 처리 시 수행

    BASE_DIR = Path(base_dir).resolve()
    APP_CONFIG_DIR = BASE_DIR / app_config_dir_name
    # YAML 파일들이 위치할 수 있는 디렉토리 (예: my_project/config/yamls/)
    YAMLS_DIR = APP_CONFIG_DIR / "yamls"

    if not APP_CONFIG_DIR.is_dir():
        console.print(f"[red]❌ 앱 설정 디렉토리가 존재하지 않습니다: {APP_CONFIG_DIR}[/red]")
        raise click.Abort()

    config_file_path = None
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
    
    # 최상위 네임스페이스 설정
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
        
        # 삭제 대상 앱 타입: install-helm, install-kubectl, install-action 등
        if app_info.type not in ["install-helm", "install-kubectl", "install-action"]:
            # console.print(f"[grey]ℹ️ 앱 '{app_info.name}' (타입: {app_info.type}): 이 타입은 `delete` 대상이 아닙니다. 건너뜁니다.[/grey]")
            # delete_skipped_apps +=1 # 명시적으로 삭제 대상이 아닌 것은 스킵 카운트에서 제외
            continue

        delete_total_apps += 1
        app_name = app_info.name
        app_type = app_info.type
        app_release_name = app_info.release_name or app_name # Helm 릴리스 이름 등

        console.print(f"[magenta]➡️  앱 '{app_name}' (타입: {app_type}, 릴리스명: '{app_release_name}') 삭제 시도...[/magenta]")

        # 네임스페이스 결정 로직 (deploy.py와 유사)
        current_namespace = None
        if app_info.namespace and app_info.namespace not in ["!ignore", "!none", "!false", ""]:
            current_namespace = app_info.namespace
        elif cli_namespace:
            current_namespace = cli_namespace
        elif global_namespace_from_config:
            current_namespace = global_namespace_from_config
        else: # 명시된 네임스페이스가 없으면 default 사용 (Helm uninstall 등에서 필요)
            if app_type == "install-helm": # Helm은 default를 명시해야 함
                 current_namespace = "default"
            # kubectl은 네임스페이스 없이 실행하면 현재 컨텍스트의 기본 네임스페이스 사용

        if current_namespace:
            console.print(f"    [grey]ℹ️ 네임스페이스 사용: {current_namespace}[/grey]")
        else:
            console.print(f"    [grey]ℹ️ 네임스페이스 미지정 (현재 컨텍스트의 기본값 사용 또는 리소스에 따라 다름)[/grey]")

        delete_command_executed = False
        delete_successful_for_app = False

        if app_type == "install-helm":
            check_helm_installed_or_exit()
            spec_obj = None
            if app_info.specs: # specs가 있는 경우에만 파싱 시도
                try:
                    spec_obj = AppInstallHelmSpec(**app_info.specs)
                except Exception as e:
                    console.print(f"[red]❌ 앱 '{app_name}': Helm Spec 정보 파싱 실패 (무시하고 진행): {e}[/red]")
            
            # Helm 릴리스 존재 확인
            installed_charts = get_installed_charts(current_namespace) # current_namespace가 None이어도 괜찮음
            if app_release_name not in installed_charts:
                console.print(f"[yellow]⚠️ Helm 릴리스 '{app_release_name}'(네임스페이스: {current_namespace or '-'})가 설치되어 있지 않습니다.[/yellow]")
                if skip_not_found:
                    console.print(f"    [grey]L `--skip-not-found` 옵션으로 건너뜁니다.[/grey]")
                    delete_skipped_apps += 1
                    console.print("")
                    continue # 다음 앱으로
                else:
                    # 오류로 처리하지 않고, 삭제할 것이 없으므로 성공처럼 처리하거나, 카운트를 다르게 할 수 있음.
                    # 여기서는 삭제할 대상이 없으므로 건너뛰는 것으로 처리 (실패는 아님)
                    delete_skipped_apps +=1 # 명시적 스킵으로 카운트
                    console.print("")
                    continue
            
            helm_cmd = ["helm", "uninstall", app_release_name]
            if current_namespace:
                helm_cmd.extend(["--namespace", current_namespace])
            
            console.print(f"    [cyan]$ {' '.join(helm_cmd)}[/cyan]")
            try:
                result = subprocess.run(helm_cmd, capture_output=True, text=True, check=True, timeout=300)
                console.print(f"[green]✅ Helm 릴리스 '{app_release_name}' 삭제 완료.[/green]")
                if result.stdout: console.print(f"    [grey]Helm STDOUT: {result.stdout.strip()}[/grey]")
                delete_successful_for_app = True
                delete_command_executed = True
            except subprocess.CalledProcessError as e:
                console.print(f"[red]❌ Helm 릴리스 '{app_release_name}' 삭제 실패:[/red]")
                if e.stdout: console.print(f"    [blue]STDOUT:[/blue] {e.stdout.strip()}")
                if e.stderr: console.print(f"    [red]STDERR:[/red] {e.stderr.strip()}")
            except subprocess.TimeoutExpired:
                console.print(f"[red]❌ Helm 릴리스 '{app_release_name}' 삭제 시간 초과.[/red]")
            except Exception as e:
                console.print(f"[red]❌ Helm 릴리스 '{app_release_name}' 삭제 중 예상치 못한 오류: {e}[/red]")

        elif app_type == "install-kubectl":
            check_kubectl_installed_or_exit()
            spec_obj = None
            if app_info.specs:
                try:
                    spec_obj = AppInstallKubectlSpec(**app_info.specs)
                except Exception as e:
                    console.print(f"[red]❌ 앱 '{app_name}': Kubectl Spec 정보 파싱 실패 (무시하고 진행): {e}[/red]")
                    spec_obj = AppInstallKubectlSpec(paths=[]) # 빈 paths로 초기화하여 아래 로직 진행
            else:
                console.print(f"[yellow]⚠️ 앱 '{app_name}': Kubectl Spec 정보('paths')가 없어 삭제할 파일 목록을 알 수 없습니다. 건너뜁니다.[/yellow]")
                delete_skipped_apps += 1
                console.print("")
                continue

            if not spec_obj or not spec_obj.paths:
                console.print(f"[yellow]⚠️ 앱 '{app_name}': 삭제할 Kubectl YAML 파일 경로('paths')가 지정되지 않았습니다. 건너뜁니다.[/yellow]")
                delete_skipped_apps += 1
                console.print("")
                continue

            kubectl_delete_successful_files = 0
            kubectl_delete_failed_files = 0
            kubectl_delete_skipped_files = 0 # 리소스가 존재하지 않아 스킵된 경우

            for file_rel_path_str in reversed(spec_obj.paths): # 생성의 역순으로 삭제 시도
                file_rel_path = Path(file_rel_path_str)
                abs_yaml_path = file_rel_path
                if not abs_yaml_path.is_absolute():
                    abs_yaml_path = YAMLS_DIR / file_rel_path
                
                if not abs_yaml_path.exists() or not abs_yaml_path.is_file():
                    console.print(f"    [yellow]⚠️ Kubectl 삭제 대상 YAML 파일을 찾을 수 없음 (건너뜀): {abs_yaml_path}[/yellow]")
                    kubectl_delete_failed_files +=1 # 파일 자체가 없으면 실패로 간주
                    continue
                
                # YAML 파일을 파싱하여 리소스 정보 추출 (선택적: 존재 확인 강화용)
                # 실제 kubectl delete -f는 파일 내 모든 리소스를 대상으로 하므로, 개별 리소스 확인은 복잡할 수 있음
                # 여기서는 파일 단위로 delete 시도하고, skip-not-found 시 kubectl의 --ignore-not-found 옵션 활용

                kubectl_cmd = ["kubectl", "delete", "-f", str(abs_yaml_path)]
                if current_namespace:
                    kubectl_cmd.extend(["--namespace", current_namespace])
                if skip_not_found:
                    kubectl_cmd.append("--ignore-not-found=true")

                console.print(f"    [cyan]$ {' '.join(kubectl_cmd)}[/cyan]")
                try:
                    result = subprocess.run(kubectl_cmd, capture_output=True, text=True, check=True, timeout=120)
                    console.print(f"[green]    ✅ Kubectl YAML '{abs_yaml_path.name}' 삭제 요청 성공.[/green]")
                    if result.stdout: console.print(f"        [grey]Kubectl STDOUT: {result.stdout.strip()}[/grey]")
                    kubectl_delete_successful_files += 1
                    delete_command_executed = True # 하나라도 실행되면 True
                except subprocess.CalledProcessError as e:
                    # ignore-not-found가 true일 때, 리소스가 없어서 아무것도 삭제되지 않아도 returncode가 0일 수 있음.
                    # 따라서 stderr에 "not found" 메시지가 있는지 등으로 추가 판단 필요하나, 여기선 kubectl 결과에 의존.
                    console.print(f"[red]    ❌ Kubectl YAML '{abs_yaml_path.name}' 삭제 실패:[/red]")
                    if e.stdout: console.print(f"        [blue]STDOUT:[/blue] {e.stdout.strip()}")
                    if e.stderr: console.print(f"        [red]STDERR:[/red] {e.stderr.strip()}")
                    kubectl_delete_failed_files +=1
                except subprocess.TimeoutExpired:
                    console.print(f"[red]    ❌ Kubectl YAML '{abs_yaml_path.name}' 삭제 시간 초과.[/red]")
                    kubectl_delete_failed_files +=1
                except Exception as e:
                    console.print(f"[red]    ❌ Kubectl YAML '{abs_yaml_path.name}' 삭제 중 예상치 못한 오류: {e}[/red]")
                    kubectl_delete_failed_files +=1
            
            if kubectl_delete_failed_files == 0 and kubectl_delete_successful_files > 0:
                delete_successful_for_app = True
            elif kubectl_delete_failed_files == 0 and kubectl_delete_successful_files == 0 and delete_command_executed == False:
                # 실행된 명령도 없고, 성공도 실패도 없으면 (아마도 파일 목록이 비었거나, 모두 skip된 경우) - 성공으로 간주할지 결정 필요
                # 여기서는 skip_not_found 시 이런 상황이 발생 가능. 앱 자체는 성공으로 본다.
                if skip_not_found:
                    delete_successful_for_app = True 
                    console.print(f"    [yellow]ℹ️ 앱 '{app_name}': 모든 Kubectl 리소스가 이미 삭제되었거나 대상이 없었습니다 (skip-not-found).[/yellow]")
                # else: # skip-not-found가 아닌데 아무것도 실행/성공/실패가 없으면 이상한 상황
                    # console.print(f"    [yellow]⚠️ 앱 '{app_name}': Kubectl 삭제 작업에서 아무런 변경사항이 없습니다.[/yellow]")
            
            console.print(f"    [grey]Kubectl 삭제 요약 (파일 기준): 성공 {kubectl_delete_successful_files}, 실패 {kubectl_delete_failed_files}, 스킵(리소스 없음 등) {kubectl_delete_skipped_files}[/grey]")

        elif app_type == "install-action":
            spec_obj = None
            uninstall_action_defined = False
            if app_info.specs:
                try:
                    spec_obj = AppInstallActionSpec(**app_info.specs)
                    if spec_obj.uninstall and spec_obj.uninstall.get("script"): # uninstall 스크립트가 정의되어 있는지 확인
                        uninstall_action_defined = True
                except Exception as e:
                    console.print(f"[red]❌ 앱 '{app_name}': Action Spec 정보 파싱 실패: {e}[/red]")

            if not uninstall_action_defined:
                console.print(f"[yellow]⚠️ 앱 '{app_name}' (타입: {app_type}): `specs.uninstall.script`가 정의되지 않아 자동으로 삭제할 수 없습니다. 건너뜁니다.[/yellow]")
                delete_skipped_apps += 1
                console.print("")
                continue

            # uninstall 스크립트 실행 로직 (deploy.py의 action 실행 로직과 유사하게 구성)
            # TODO: uninstall 스크립트 실행 로직 구현 (deploy.py 참조)
            console.print(f"[yellow]앱 '{app_name}': Action 기반 삭제 (uninstall 스크립트 실행)는 아직 구현되지 않았습니다.[/yellow]")
            # 여기서는 임시로 스킵 처리
            delete_skipped_apps += 1 

        else:
            console.print(f"[yellow]⚠️ 앱 '{app_name}' (타입: {app_type}): 이 타입에 대한 자동 삭제 로직이 아직 정의되지 않았습니다. 건너뜁니다.[/yellow]")
            delete_skipped_apps += 1
            console.print("")
            continue

        if delete_successful_for_app:
            delete_success_apps += 1
        elif not delete_command_executed and skip_not_found: # 명령 실행도 안됐고, skip-not-found면 성공처럼 간주
            delete_success_apps +=1 # 이런 경우도 성공 카운트에 포함 (이미 없었으므로)
        # else: 실패 카운트는 따로 하지 않고, 전체 성공/스킵/총계로 표시

        console.print("") # 각 앱 처리 후 구분선

    console.print(f"[bold blue]✨ `delete` 작업 요약 ✨[/bold blue]")
    if delete_total_apps > 0:
        console.print(f"[green]    총 {delete_total_apps}개 앱 대상 중 {delete_success_apps}개 삭제 성공 (또는 이미 삭제됨).[/green]")
        if delete_skipped_apps > 0:
            console.print(f"[yellow]    {delete_skipped_apps}개 앱 건너뜀 (지원되지 않는 타입, 설정 오류, 리소스 없음 등).[/yellow]")
        if (delete_total_apps - delete_success_apps - delete_skipped_apps) > 0:
             console.print(f"[red]    {delete_total_apps - delete_success_apps - delete_skipped_apps}개 앱 삭제 실패.[/red]")
    elif target_app_name and not apps_to_process: # 특정 앱 지정했는데 위에서 못 찾은 경우 이미 처리됨
        pass 
    else: # 처리 대상 앱이 처음부터 없었던 경우
        console.print("[yellow]    삭제할 대상으로 지정된 앱이 없었습니다.[/yellow]")
    console.print(f"[bold blue]✨ `delete` 작업 완료 ✨[/bold blue]")