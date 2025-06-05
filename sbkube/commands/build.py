import shutil
import click
from pathlib import Path
from rich.console import Console

from sbkube.utils.file_loader import load_config_file
from sbkube.models.config_model import (
    AppInfoScheme,
    AppPullHelmSpec,
    AppPullHelmOciSpec,
    AppPullGitSpec,
    AppCopySpec,
    CopyPair
)

console = Console()

@click.command(name="build")
@click.option("--app-dir", "app_config_dir_name", default="config", help="앱 설정 파일이 위치한 디렉토리 이름 (base-dir 기준)")
@click.option("--base-dir", default=".", type=click.Path(exists=True, file_okay=False, dir_okay=True), help="프로젝트 루트 디렉토리")
@click.option("--app", "app_name", default=None, help="빌드할 특정 앱 이름 (지정하지 않으면 모든 앱 빌드)")
@click.option("--config-file", "config_file_name", default=None, help="사용할 설정 파일 이름 (app-dir 내부, 기본값: config.yaml 자동 탐색)")
def cmd(app_config_dir_name: str, base_dir: str, app_name: str | None, config_file_name: str | None):
    """
    `prepare` 단계의 결과물과 로컬 소스를 사용하여 배포 가능한 애플리케이션 빌드 결과물을 생성합니다.

    이 명령어는 `config.[yaml|toml]` 파일에 정의된 'pull-helm', 'pull-helm-oci', 
    'pull-git', 'copy-app' 타입의 애플리케이션들을 주로 대상으로 하며,
    이들의 소스를 `<base_dir>/<app_dir>/build/<app_name>/` 경로에 최종 빌드합니다.

    주요 작업:
    - 대상 앱 타입: 'pull-helm', 'pull-helm-oci', 'pull-git', 'copy-app'.
      (다른 타입의 앱은 이 단계에서 특별한 빌드 로직이 없을 수 있습니다.)
    - Helm 차트 준비:
        - `prepare` 단계에서 다운로드된 Helm 차트 (`<base_dir>/charts/...`)를 
          빌드 디렉토리 (`<app_dir>/build/<app_name>`)로 복사합니다.
        - `specs.overrides`: 지정된 파일들을 빌드된 차트 내에 덮어씁니다.
          (원본은 `<app_dir>/overrides/<app_name>/...` 경로에서 가져옴)
        - `specs.removes`: 빌드된 차트 내에서 지정된 파일 또는 디렉토리를 삭제합니다.
    - Git 소스 준비:
        - `prepare` 단계에서 클론된 Git 저장소 (`<base_dir>/repos/...`)의 내용을
          `specs.paths` 정의에 따라 빌드 디렉토리로 복사합니다.
    - 로컬 파일 복사 (`copy-app` 타입):
        - `specs.paths`에 정의된 로컬 파일/디렉토리를 빌드 디렉토리로 복사합니다.

    빌드 결과물은 주로 `template` 또는 `deploy` 명령어에서 사용됩니다.
    빌드 작업 전, 기존 빌드 디렉토리 (`<app_dir>/build/`)는 삭제됩니다.
    """
    
    console.print(f"[bold blue]✨ `build` 작업 시작 (앱 설정: '{app_config_dir_name}', 기준 경로: '{base_dir}') ✨[/bold blue]")

    BASE_DIR = Path(base_dir).resolve()
    APP_CONFIG_DIR = BASE_DIR / app_config_dir_name 

    CHARTS_DIR = BASE_DIR / "charts"
    REPOS_DIR = BASE_DIR / "repos"

    BUILD_DIR = APP_CONFIG_DIR / "build"
    OVERRIDES_DIR = APP_CONFIG_DIR / "overrides"

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

    console.print(f"[cyan]🔄 기존 빌드 디렉토리 정리 중: {BUILD_DIR}[/cyan]")
    try:
        if BUILD_DIR.exists():
            shutil.rmtree(BUILD_DIR)
        BUILD_DIR.mkdir(parents=True, exist_ok=True)
        console.print(f"[green]✅ 빌드 디렉토리 준비 완료: {BUILD_DIR}[/green]")
    except OSError as e:
        console.print(f"[red]❌ 빌드 디렉토리 정리/생성 실패: {e}. 권한 등을 확인하세요.[/red]")
        raise click.Abort()
    console.print("")

    build_total_apps = 0
    build_success_apps = 0

    app_info_list_to_build = []
    for app_dict in apps_config_dict.get("apps", []):
        try:
            app_info = AppInfoScheme(**app_dict)
            if app_info.type in ["pull-helm", "pull-helm-oci", "pull-git", "copy-app"]:
                if app_name is None or app_info.name == app_name:
                    app_info_list_to_build.append(app_info)
            else:
                if app_name is None or app_info.name == app_name:
                    console.print(f"[yellow]ℹ️ 앱 '{app_info.name}' (타입: {app_info.type}): 이 타입은 `build` 단계에서 처리 대상이 아닙니다. 건너뜁니다.[/yellow]")
        except Exception as e:
            app_name_for_error = app_dict.get('name', '알 수 없는 앱')
            console.print(f"[red]❌ 앱 정보 '{app_name_for_error}' 처리 중 오류 (AppInfoScheme 변환 실패): {e}[/red]")
            console.print(f"    [yellow]L 해당 앱 설정을 건너뜁니다: {app_dict}[/yellow]")
            continue

    if app_name is not None and not app_info_list_to_build:
        console.print(f"[red]❌ 지정된 앱 '{app_name}'을 찾을 수 없거나 빌드할 수 없는 타입입니다.[/red]")
        raise click.Abort()

    if not app_info_list_to_build:
        if app_name is not None:
            console.print(f"[yellow]⚠️ 앱 '{app_name}'은 빌드 대상이 아닙니다.[/yellow]")
        else:
            console.print("[yellow]⚠️ 빌드할 앱이 설정 파일에 없거나, 지원하는 타입의 앱이 없습니다.[/yellow]")
        console.print(f"[bold blue]✨ `build` 작업 완료 (처리할 앱 없음) ✨[/bold blue]")
        return

    for app_info in app_info_list_to_build:
        build_total_apps += 1
        app_name = app_info.name
        app_type = app_info.type

        console.print(f"[magenta]➡️  앱 '{app_name}' (타입: {app_type}) 빌드 시작...[/magenta]")

        spec_obj = None
        try:
            if app_type == "pull-helm":
                spec_obj = AppPullHelmSpec(**app_info.specs)
            elif app_type == "pull-helm-oci":
                spec_obj = AppPullHelmOciSpec(**app_info.specs)
            elif app_type == "pull-git":
                spec_obj = AppPullGitSpec(**app_info.specs)
            elif app_type == "copy-app":
                spec_obj = AppCopySpec(**app_info.specs)
        except Exception as e:
            console.print(f"[red]❌ 앱 '{app_name}' (타입: {app_type})의 Spec 데이터 검증/변환 중 오류: {e}[/red]")
            console.print(f"    [yellow]L 이 앱의 빌드를 건너뜁니다. Specs: {app_info.specs}[/yellow]")
            console.print("")
            continue
        
        # pull-helm, pull-helm-oci 타입의 경우 dest 값을 빌드 디렉토리 이름으로 사용
        if app_type in ["pull-helm", "pull-helm-oci"]:
            app_build_dest_name = spec_obj.dest or spec_obj.chart
        else:
            app_build_dest_name = app_name

        app_final_build_path = BUILD_DIR / app_build_dest_name

        try:
            if app_final_build_path.exists():
                console.print(f"    [yellow]🔄 기존 앱 빌드 디렉토리 삭제: {app_final_build_path}[/yellow]")
                shutil.rmtree(app_final_build_path)

            if app_type in ["pull-helm", "pull-helm-oci"]:
                prepared_chart_dir_name = spec_obj.dest or spec_obj.chart
                source_chart_path_in_chartsdir = CHARTS_DIR / prepared_chart_dir_name

                if not source_chart_path_in_chartsdir.exists() or not source_chart_path_in_chartsdir.is_dir():
                    console.print(f"[red]❌ 앱 '{app_name}': `prepare` 단계에서 준비된 Helm 차트 소스를 찾을 수 없습니다: {source_chart_path_in_chartsdir}[/red]")
                    console.print(f"    [yellow]L 'sbkube prepare' 명령을 먼저 실행했는지, '{app_config_dir_name}/config.yaml'의 `dest` 필드가 올바른지 확인하세요.[/yellow]")
                    raise FileNotFoundError(f"Prepared chart not found: {source_chart_path_in_chartsdir}")

                console.print(f"    [cyan]📁 Helm 차트 복사: {source_chart_path_in_chartsdir} → {app_final_build_path}[/cyan]")
                shutil.copytree(source_chart_path_in_chartsdir, app_final_build_path, dirs_exist_ok=True)

                if spec_obj.overrides:
                    console.print(f"    [yellow]🔩 Overrides 적용 중...[/yellow]")
                    for override_file_rel_path in spec_obj.overrides:
                        override_src_path = OVERRIDES_DIR / app_build_dest_name / override_file_rel_path
                        override_dst_path = app_final_build_path / override_file_rel_path

                        if override_src_path.exists() and override_src_path.is_file():
                            override_dst_path.parent.mkdir(parents=True, exist_ok=True)
                            shutil.copy2(override_src_path, override_dst_path)
                            console.print(f"        [green]✓ Override 적용: {override_src_path} → {override_dst_path}[/green]")
                        else:
                            console.print(f"        [yellow]⚠️  Override 원본 파일 없음 (건너뜀): {override_src_path}[/yellow]")
                
                if spec_obj.removes:
                    console.print(f"    [yellow]🗑️  Removes 적용 중...[/yellow]")
                    for remove_file_rel_path in spec_obj.removes:
                        file_to_remove = app_final_build_path / remove_file_rel_path
                        if file_to_remove.exists():
                            if file_to_remove.is_file():
                                file_to_remove.unlink()
                                console.print(f"        [green]✓ 파일 삭제: {file_to_remove}[/green]")
                            elif file_to_remove.is_dir():
                                shutil.rmtree(file_to_remove)
                                console.print(f"        [green]✓ 디렉토리 삭제: {file_to_remove}[/green]")
                        else:
                            console.print(f"        [yellow]⚠️  삭제할 파일/디렉토리 없음 (건너뜀): {file_to_remove}[/yellow]")

            elif app_type == "pull-git":
                prepared_git_repo_path = REPOS_DIR / spec_obj.repo
                if not prepared_git_repo_path.exists() or not prepared_git_repo_path.is_dir():
                    console.print(f"[red]❌ 앱 '{app_name}': `prepare` 단계에서 준비된 Git 저장소 소스를 찾을 수 없습니다: {prepared_git_repo_path}[/red]")
                    console.print(f"    [yellow]L 'sbkube prepare' 명령을 먼저 실행했는지 확인하세요.[/yellow]")
                    raise FileNotFoundError(f"Prepared Git repo not found: {prepared_git_repo_path}")
                
                app_final_build_path.mkdir(parents=True, exist_ok=True)
                for copy_pair in spec_obj.paths:
                    source_path_in_repo = prepared_git_repo_path / copy_pair.src
                    dest_path_in_build = app_final_build_path / copy_pair.dest 

                    if not source_path_in_repo.exists():
                        console.print(f"    [red]❌ Git 소스 경로 없음: {source_path_in_repo} (건너뜀)[/red]")
                        continue
                    
                    console.print(f"    [cyan]📂 Git 콘텐츠 복사: {source_path_in_repo} → {dest_path_in_build}[/cyan]")
                    if dest_path_in_build.exists():
                        if dest_path_in_build.is_dir(): shutil.rmtree(dest_path_in_build)
                        else: dest_path_in_build.unlink()
                    
                    dest_path_in_build.parent.mkdir(parents=True, exist_ok=True)
                    if source_path_in_repo.is_dir():
                        shutil.copytree(source_path_in_repo, dest_path_in_build, dirs_exist_ok=True)
                    elif source_path_in_repo.is_file():
                        shutil.copy2(source_path_in_repo, dest_path_in_build)
                    else:
                        console.print(f"    [yellow]⚠️  Git 소스 경로가 파일이나 디렉토리가 아님: {source_path_in_repo} (건너뜀)[/yellow]")
                        continue
            
            elif app_type == "copy-app":
                app_final_build_path.mkdir(parents=True, exist_ok=True)
                for copy_pair in spec_obj.paths:
                    source_local_path_str = copy_pair.src
                    source_local_path = Path(source_local_path_str)
                    if not source_local_path.is_absolute():
                        source_local_path = BASE_DIR / source_local_path_str
                    
                    dest_path_in_build = app_final_build_path / copy_pair.dest

                    if not source_local_path.exists():
                        console.print(f"    [red]❌ 로컬 소스 경로 없음: {source_local_path} (원본: '{source_local_path_str}') (건너뜀)[/red]")
                        continue

                    console.print(f"    [cyan]📂 로컬 콘텐츠 복사: {source_local_path} → {dest_path_in_build}[/cyan]")
                    if dest_path_in_build.exists():
                        if dest_path_in_build.is_dir(): shutil.rmtree(dest_path_in_build)
                        else: dest_path_in_build.unlink()

                    dest_path_in_build.parent.mkdir(parents=True, exist_ok=True)
                    if source_local_path.is_dir():
                        shutil.copytree(source_local_path, dest_path_in_build, dirs_exist_ok=True)
                    elif source_local_path.is_file():
                        shutil.copy2(source_local_path, dest_path_in_build)
                    else:
                        console.print(f"    [yellow]⚠️  로컬 소스 경로가 파일이나 디렉토리가 아님: {source_local_path} (건너뜀)[/yellow]")
                        continue
            
            build_success_apps += 1
            console.print(f"[green]✅ 앱 '{app_name}' 빌드 완료: {app_final_build_path}[/green]")

        except FileNotFoundError as e:
            console.print(f"    [red]L 이 앱 '{app_name}'의 빌드를 중단합니다. (상세: {e})[/red]")
        except Exception as e:
            console.print(f"[red]❌ 앱 '{app_name}' (타입: {app_type}) 빌드 중 예상치 못한 오류 발생: {e}[/red]")
            import traceback
            console.print(f"[grey]{traceback.format_exc()}[/grey]")
        finally:
            console.print("")

    if build_total_apps > 0:
        console.print(f"[bold green]✅ `build` 작업 요약: 총 {build_total_apps}개 앱 중 {build_success_apps}개 성공.[/bold green]")
    else:
        pass 
        
    console.print(f"[bold blue]✨ `build` 작업 완료 (결과물 위치: {BUILD_DIR}) ✨[/bold blue]")
