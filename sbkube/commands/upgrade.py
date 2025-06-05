import subprocess
import json
import click
from pathlib import Path
from rich.console import Console

from sbkube.utils.file_loader import load_config_file
from sbkube.utils.cli_check import check_helm_installed_or_exit
from sbkube.models.config_model import (
    AppInfoScheme,
    AppInstallHelmSpec,
)

console = Console()

@click.command(name="upgrade")
@click.option("--app-dir", "app_config_dir_name", default="config", help="앱 설정 파일이 위치한 디렉토리 이름 (base-dir 기준)")
@click.option("--base-dir", default=".", type=click.Path(exists=True, file_okay=False, dir_okay=True), help="프로젝트 루트 디렉토리")
@click.option("--namespace", "cli_namespace", default=None, help="업그레이드 작업을 수행할 기본 네임스페이스 (없으면 앱별 또는 최상위 설정 따름)")
@click.option("--app", "target_app_name", default=None, help="특정 앱만 업그레이드 (지정하지 않으면 모든 install-helm 타입 앱 대상)")
@click.option("--dry-run", is_flag=True, default=False, help="실제 업그레이드를 수행하지 않고, 실행될 명령만 출력 (helm --dry-run)")
@click.option("--no-install", "skip_install", is_flag=True, default=False, help="릴리스가 존재하지 않을 경우 새로 설치하지 않음 (helm upgrade의 --install 플래그 비활성화)")
@click.option("--config-file", "config_file_name", default=None, help="사용할 설정 파일 이름 (app-dir 내부, 기본값: config.yaml 자동 탐색)")
def cmd(app_config_dir_name: str, base_dir: str, cli_namespace: str | None, target_app_name: str | None, dry_run: bool, skip_install: bool, config_file_name: str | None):
    """config.yaml/toml에 정의된 Helm 애플리케이션을 업그레이드하거나 새로 설치합니다 (install-helm 타입 대상)."""
    console.print(f"[bold blue]✨ `upgrade` 작업 시작 (앱 설정: '{app_config_dir_name}', 기준 경로: '{base_dir}') ✨[/bold blue]")
    check_helm_installed_or_exit()

    BASE_DIR = Path(base_dir).resolve()
    APP_CONFIG_DIR = BASE_DIR / app_config_dir_name
    
    # 빌드된 차트가 위치한 디렉토리 (예: my_project/config/build/)
    BUILD_DIR = APP_CONFIG_DIR / "build"
    # Values 파일들이 위치할 수 있는 디렉토리 (예: my_project/config/values/)
    VALUES_DIR = APP_CONFIG_DIR / "values"

    if not APP_CONFIG_DIR.is_dir():
        console.print(f"[red]❌ 앱 설정 디렉토리가 존재하지 않습니다: {APP_CONFIG_DIR}[/red]")
        raise click.Abort()

    config_file_path = None
    if config_file_name:
        # --config-file 옵션이 지정된 경우
        config_file_path = APP_CONFIG_DIR / config_file_name
        if not config_file_path.exists() or not config_file_path.is_file():
            console.print(f"[red]❌ 지정된 설정 파일을 찾을 수 없습니다: {config_file_path}[/red]")
            raise click.Abort()
    else:
        # 자동 탐색
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

    upgrade_total_apps = 0
    upgrade_success_apps = 0
    upgrade_skipped_apps = 0 # 타입 불일치 등으로 스킵

    apps_to_process = []
    if target_app_name:
        found_target_app = False
        for app_dict in apps_config_dict.get("apps", []):
            if app_dict.get("name") == target_app_name:
                if app_dict.get("type") == "install-helm":
                    apps_to_process.append(app_dict)
                    found_target_app = True
                else:
                    console.print(f"[yellow]⚠️ 앱 '{target_app_name}' (타입: {app_dict.get('type')})은 'install-helm' 타입이 아니므로 `upgrade` 대상이 아닙니다.[/yellow]")
                    # 이 경우는 특정 앱을 지정했으나 타입이 맞지 않아 스킵하는 것이므로 별도 처리
                    console.print(f"[bold blue]✨ `upgrade` 작업 완료 (대상 앱 타입 아님) ✨[/bold blue]")
                    return # 여기서 종료
                break
        if not found_target_app:
            console.print(f"[red]❌ 업그레이드 대상 앱 '{target_app_name}'을(를) 설정 파일에서 찾을 수 없습니다.[/red]")
            raise click.Abort()
    else:
        for app_dict in apps_config_dict.get("apps", []):
            if app_dict.get("type") == "install-helm":
                apps_to_process.append(app_dict)

    if not apps_to_process:
        console.print("[yellow]⚠️ 설정 파일에 업그레이드할 'install-helm' 타입의 앱이 정의되어 있지 않습니다.[/yellow]")
        console.print(f"[bold blue]✨ `upgrade` 작업 완료 (처리할 앱 없음) ✨[/bold blue]")
        return

    for app_dict in apps_to_process:
        try:
            app_info = AppInfoScheme(**app_dict)
        except Exception as e:
            app_name_for_error = app_dict.get('name', '알 수 없는 install-helm 앱')
            console.print(f"[red]❌ 앱 정보 '{app_name_for_error}' 처리 중 오류 (AppInfoScheme 변환 실패): {e}[/red]")
            console.print(f"    [yellow]L 해당 앱 설정을 건너뜁니다.[/yellow]")
            upgrade_skipped_apps +=1
            continue
        
        # 타입은 위에서 이미 install-helm으로 필터링 되었음
        upgrade_total_apps += 1
        app_name = app_info.name
        app_release_name = app_info.release_name or app_name

        console.print(f"[magenta]➡️  Helm 앱 '{app_name}' (릴리스명: '{app_release_name}') 업그레이드/설치 시도...[/magenta]")

        # 빌드된 차트 경로 확인 (build.py에서 app_name으로 생성됨)
        built_chart_path = BUILD_DIR / app_name
        if not built_chart_path.exists() or not built_chart_path.is_dir():
            console.print(f"[red]❌ 앱 '{app_name}': 빌드된 Helm 차트 디렉토리를 찾을 수 없습니다: {built_chart_path}[/red]")
            console.print(f"    [yellow]L 'sbkube build' 명령을 먼저 실행하여 '{app_name}' 앱을 빌드했는지 확인하세요.[/yellow]")
            upgrade_skipped_apps +=1 # 실패로 간주하고 스킵
            console.print("")
            continue
        console.print(f"    [grey]ℹ️ 대상 차트 경로: {built_chart_path}[/grey]")

        current_namespace = None
        if app_info.namespace and app_info.namespace not in ["!ignore", "!none", "!false", ""]:
            current_namespace = app_info.namespace
        elif cli_namespace:
            current_namespace = cli_namespace
        elif global_namespace_from_config:
            current_namespace = global_namespace_from_config
        # Helm upgrade 시 네임스페이스가 없으면 default를 사용하도록 명시 (명령어 실행 시)
        # 또는 --create-namespace 와 함께 사용하면 네임스페이스가 없으면 생성함.
        
        helm_upgrade_cmd = ["helm", "upgrade", app_release_name, str(built_chart_path)]
        
        if not skip_install: # 기본적으로 --install 사용
            helm_upgrade_cmd.append("--install")
        
        if current_namespace:
            helm_upgrade_cmd.extend(["--namespace", current_namespace])
            # 네임스페이스가 없으면 생성하는 옵션 (deploy와 동작 일관성)
            # AppInfoScheme.create_namespace 또는 Spec 필드에서 가져올 수 있음
            if app_info.create_namespace:
                helm_upgrade_cmd.append("--create-namespace")
                console.print(f"    [grey]ℹ️ 네임스페이스 사용 (필요시 생성): {current_namespace}[/grey]")
            else:
                console.print(f"    [grey]ℹ️ 네임스페이스 사용: {current_namespace}[/grey]")
        else: # 네임스페이스가 최종적으로 결정되지 않으면 helm은 default 사용
            console.print(f"    [grey]ℹ️ 네임스페이스 미지정 (Helm이 'default' 네임스페이스 사용 또는 차트 내 정의 따름)[/grey]")
            # 만약 이 경우에도 --create-namespace를 쓰고 싶다면, 'default'를 명시적으로 지정해야 함

        # Values 파일 처리 (AppInstallHelmSpec 사용)
        values_files_to_apply = []
        if app_info.specs:
            try:
                spec_obj = AppInstallHelmSpec(**app_info.specs)
                if spec_obj.values:
                    console.print(f"    [grey]🔩 Values 파일 적용 시도...[/grey]")
                    for vf_rel_path_str in spec_obj.values:
                        vf_path = Path(vf_rel_path_str)
                        abs_vf_path = vf_path if vf_path.is_absolute() else VALUES_DIR / vf_path
                        if abs_vf_path.exists() and abs_vf_path.is_file():
                            helm_upgrade_cmd.extend(["--values", str(abs_vf_path)])
                            console.print(f"        [green]✓ Values 파일 사용: {abs_vf_path}[/green]")
                            values_files_to_apply.append(str(abs_vf_path))
                        else:
                            console.print(f"        [yellow]⚠️ Values 파일 없음 (건너뜀): {abs_vf_path} (원본: '{vf_rel_path_str}')[/yellow]")
            except Exception as e:
                console.print(f"[yellow]⚠️ 앱 '{app_name}': Spec에서 values 정보 처리 중 오류 (무시하고 진행): {e}[/yellow]")
        
        # TODO: set, set_string, set_file 등의 추가 Helm 옵션 지원 (app_info.specs에서 가져옴)

        if dry_run:
            helm_upgrade_cmd.append("--dry-run") # Helm 3+ 에서는 --dry-run 만 사용
            console.print(f"    [yellow]🌵 Dry-run 모드 활성화됨.[/yellow]")

        console.print(f"    [cyan]$ {' '.join(helm_upgrade_cmd)}[/cyan]")
        try:
            # TODO: 환경변수 전달 기능 (app_info.env 또는 spec_obj.env)
            result = subprocess.run(helm_upgrade_cmd, capture_output=True, text=True, check=True, timeout=600) # timeout 늘림
            console.print(f"[green]✅ Helm 앱 '{app_release_name}' 업그레이드/설치 성공.[/green]")
            if result.stdout and dry_run: # dry-run 시에는 stdout이 중요
                 console.print(f"    [blue]Dry-run 결과 (STDOUT):[/blue] {result.stdout.strip()}")
            elif result.stdout: # 실제 실행 시 간단한 성공 메시지 외 stdout은 grey로
                 console.print(f"    [grey]Helm STDOUT: {result.stdout.strip()}[/grey]")
            if result.stderr: # stderr은 항상 주의깊게 표시
                 console.print(f"    [yellow]Helm STDERR: {result.stderr.strip()}[/yellow]")
            upgrade_success_apps += 1
        except subprocess.CalledProcessError as e:
            console.print(f"[red]❌ Helm 앱 '{app_release_name}' 업그레이드/설치 실패:[/red]")
            if e.stdout: console.print(f"    [blue]STDOUT:[/blue] {e.stdout.strip()}")
            if e.stderr: console.print(f"    [red]STDERR:[/red] {e.stderr.strip()}")
        except subprocess.TimeoutExpired:
            console.print(f"[red]❌ Helm 앱 '{app_release_name}' 업그레이드/설치 시간 초과 (600초).[/red]")
        except Exception as e:
            console.print(f"[red]❌ Helm 앱 '{app_release_name}' 업그레이드/설치 중 예상치 못한 오류: {e}[/red]")
            import traceback
            console.print(f"[grey]{traceback.format_exc()}[/grey]")
        finally:
            console.print("") # 각 앱 처리 후 구분선

    console.print(f"[bold blue]✨ `upgrade` 작업 요약 ✨[/bold blue]")
    if upgrade_total_apps > 0:
        console.print(f"[green]    총 {upgrade_total_apps}개 'install-helm' 앱 대상 중 {upgrade_success_apps}개 업그레이드/설치 성공.[/green]")
        if upgrade_skipped_apps > 0:
            console.print(f"[yellow]    {upgrade_skipped_apps}개 앱 건너뜀 (설정 오류, 빌드된 차트 없음 등).[/yellow]")
        failed_apps = upgrade_total_apps - upgrade_success_apps - upgrade_skipped_apps
        if failed_apps > 0:
             console.print(f"[red]    {failed_apps}개 앱 업그레이드/설치 실패.[/red]")
    elif target_app_name and not apps_to_process: # 특정 앱을 지정했으나 대상이 없었던 경우 (위에서 이미 메시지 출력 후 종료)
        pass 
    else:
        console.print("[yellow]    업그레이드/설치할 'install-helm' 타입의 앱이 없었습니다.[/yellow]")
    console.print(f"[bold blue]✨ `upgrade` 작업 완료 ✨[/bold blue]")
