import json
import shutil
from pathlib import Path
from shutil import which

import click
from rich.console import Console

from sbkube.models.config_model import (
    AppInfoScheme,
    AppPullGitSpec,
    AppPullHelmOciSpec,
    AppPullHelmSpec,
)
from sbkube.utils.cli_check import check_helm_installed_or_exit
from sbkube.utils.common import run_command
from sbkube.utils.file_loader import load_config_file

console = Console()


def check_command_available(command):
    if which(command) is None:
        console.print(
            f"[yellow]⚠️ '{command}' 명령을 찾을 수 없습니다. PATH에 등록되어 있는지 확인하세요.[/yellow]",
        )
        return False
    return_code, _, _ = run_command([command, "--help"], timeout=5)
    return return_code == 0


@click.command(name="prepare")
@click.option(
    "--app-dir",
    "app_config_dir_name",
    default="config",
    help="앱 설정 디렉토리 (config.yaml 등 내부 탐색, base-dir 기준)",
)
@click.option(
    "--sources",
    "sources_file_name",
    default="sources.yaml",
    help="소스 설정 파일 (base-dir 기준)",
)
@click.option(
    "--base-dir",
    default=".",
    type=click.Path(exists=True, file_okay=False, dir_okay=True),
    help="프로젝트 루트 디렉토리",
)
@click.option(
    "--config-file",
    "config_file_name",
    default=None,
    help="사용할 설정 파일 이름 (app-dir 내부, 기본값: config.yaml 자동 탐색)",
)
@click.option(
    "--sources-file",
    "sources_file_override",
    default=None,
    help="소스 설정 파일 경로 (--sources와 동일, 테스트 호환성)",
)
@click.option(
    "--app",
    "app_name",
    default=None,
    help="준비할 특정 앱 이름 (지정하지 않으면 모든 앱 준비)",
)
def cmd(
    app_config_dir_name,
    sources_file_name,
    base_dir,
    config_file_name,
    sources_file_override,
    app_name,
):
    """..."""

    console.print("[bold blue]✨ `prepare` 작업 시작 ✨[/bold blue]")

    if not check_command_available("helm"):
        console.print(
            "[red]❌ `helm` 명령을 사용할 수 없습니다. `prepare` 작업을 진행할 수 없습니다.[/red]",
        )
        raise click.Abort()
    check_helm_installed_or_exit()

    BASE_DIR = Path(base_dir).resolve()
    CHARTS_DIR = BASE_DIR / "charts"
    REPOS_DIR = BASE_DIR / "repos"

    APP_CONFIG_DIR = BASE_DIR / app_config_dir_name

    config_file_path = None
    if config_file_name:
        # 명시적으로 설정 파일이 지정된 경우
        config_file_path = APP_CONFIG_DIR / config_file_name
        if not config_file_path.exists() or not config_file_path.is_file():
            console.print(
                f"[red]❌ 지정된 설정 파일을 찾을 수 없습니다: {config_file_path}[/red]",
            )
            raise click.Abort()
    else:
        # 자동 탐색: 1차 APP_CONFIG_DIR, 2차 BASE_DIR (fallback)
        for ext in [".yaml", ".yml", ".toml"]:
            candidate = APP_CONFIG_DIR / f"config{ext}"
            if candidate.exists() and candidate.is_file():
                config_file_path = candidate
                break

        # Fallback: BASE_DIR에서 찾기 (현재 디렉토리 지원)
        if not config_file_path:
            for ext in [".yaml", ".yml", ".toml"]:
                candidate = BASE_DIR / f"config{ext}"
                if candidate.exists() and candidate.is_file():
                    config_file_path = candidate
                    break

        if not config_file_path:
            console.print(
                f"[red]❌ 앱 설정 파일을 찾을 수 없습니다.[/red]",
            )
            console.print(
                f"[yellow]    탐색 위치: {APP_CONFIG_DIR}/config.[yaml|yml|toml] 또는 {BASE_DIR}/config.[yaml|yml|toml][/yellow]",
            )
            raise click.Abort()
    console.print(f"[green]ℹ️ 앱 설정 파일 사용: {config_file_path}[/green]")

    # sources 파일 탐색
    sources_file_path = None
    if sources_file_override:
        sources_file_path = BASE_DIR / sources_file_override
        if not sources_file_path.exists() or not sources_file_path.is_file():
            console.print(
                f"[red]❌ 지정된 소스 설정 파일을 찾을 수 없습니다: {sources_file_path}[/red]",
            )
            raise click.Abort()
    else:
        # 자동 탐색: 1) 현재 디렉토리 2) 상위 디렉토리
        sources_search_paths = [
            BASE_DIR / sources_file_name,  # 현재 디렉토리
            BASE_DIR.parent / sources_file_name,  # 상위 디렉토리
        ]

        for candidate in sources_search_paths:
            if candidate.exists() and candidate.is_file():
                sources_file_path = candidate
                break

        if not sources_file_path:
            console.print(
                f"[red]❌ 소스 설정 파일을 찾을 수 없습니다: {sources_file_name}[/red]",
            )
            console.print(
                f"[yellow]    탐색 위치: {BASE_DIR}/{sources_file_name} 또는 {BASE_DIR.parent}/{sources_file_name}[/yellow]",
            )
            raise click.Abort()
    console.print(f"[green]ℹ️ 소스 설정 파일 사용: {sources_file_path}[/green]")

    apps_config_dict = load_config_file(str(config_file_path))
    sources_config_dict = load_config_file(str(sources_file_path))

    helm_repos_from_sources = sources_config_dict.get("helm_repos", {})
    oci_repos_from_sources = sources_config_dict.get("oci_repos", {})
    git_repos_from_sources = sources_config_dict.get("git_repos", {})

    app_info_list = []
    for app_dict in apps_config_dict.get("apps", []):
        try:
            app_info = AppInfoScheme(**app_dict)
            if app_info.type in ["pull-helm", "pull-helm-oci", "pull-git"]:
                if app_name is None or app_info.name == app_name:
                    app_info_list.append(app_info)
        except Exception as e:
            app_name_for_error = app_dict.get("name", "알 수 없는 앱")
            console.print(
                f"[red]❌ 앱 정보 '{app_name_for_error}' 처리 중 오류 (AppInfoScheme 변환 실패): {e}[/red]",
            )
            console.print(
                f"    [yellow]L 해당 앱 설정을 건너뜁니다: {app_dict}[/yellow]",
            )
            continue

    if app_name is not None and not app_info_list:
        console.print(
            f"[red]❌ 지정된 앱 '{app_name}'을 찾을 수 없거나 prepare 대상이 아닙니다.[/red]",
        )
        raise click.Abort()

    console.print("[cyan]--- Helm 저장소 준비 시작 ---[/cyan]")
    needed_helm_repo_names = set()
    for app_info in app_info_list:
        if app_info.type in ["pull-helm", "pull-helm-oci"]:
            try:
                if app_info.type == "pull-helm":
                    spec_obj = AppPullHelmSpec(**app_info.specs)
                else:
                    spec_obj = AppPullHelmOciSpec(**app_info.specs)
                needed_helm_repo_names.add(spec_obj.repo)
            except Exception as e:
                console.print(
                    f"[red]❌ 앱 '{app_info.name}' (타입: {app_info.type})의 Spec에서 repo 정보 추출 실패: {e}[/red]",
                )
                continue

    if needed_helm_repo_names:
        return_code, stdout, stderr = run_command(
            ["helm", "repo", "list", "-o", "json"],
            timeout=10,
        )
        if return_code == 0:
            try:
                local_helm_repos_list = json.loads(stdout)
                local_helm_repos_map = {
                    entry["name"]: entry["url"] for entry in local_helm_repos_list
                }
                console.print(
                    f"[green]ℹ️ 현재 로컬 Helm 저장소 목록 확인됨: {list(local_helm_repos_map.keys())}[/green]",
                )
            except json.JSONDecodeError as e:
                console.print(
                    f"[red]❌ 로컬 Helm 저장소 목록을 파싱하는 데 실패했습니다: {e}[/red]",
                )
                local_helm_repos_map = {}
        else:
            console.print(
                f"[red]❌ 로컬 Helm 저장소 목록을 가져오는 데 실패했습니다: {stderr}[/red]",
            )
            local_helm_repos_map = {}

        for repo_name in needed_helm_repo_names:
            is_oci_repo = any(
                app_info.type == "pull-helm-oci"
                and AppPullHelmOciSpec(**app_info.specs).repo == repo_name
                for app_info in app_info_list
                if app_info.type == "pull-helm-oci"
            )

            if is_oci_repo:
                if repo_name not in oci_repos_from_sources:
                    console.print(
                        f"[red]❌ 앱에서 OCI 저장소 '{repo_name}'를 사용하지만, '{sources_file_name}'에 해당 OCI 저장소 URL 정의가 없습니다.[/red]",
                    )
                else:
                    console.print(
                        f"[green]OCI 저장소 '{repo_name}' 확인됨 (URL: {oci_repos_from_sources.get(repo_name, {}).get('<chart_name>', 'URL 정보 없음')})[/green]",
                    )
                continue

            if repo_name not in helm_repos_from_sources:
                console.print(
                    f"[red]❌ 앱에서 Helm 저장소 '{repo_name}'를 사용하지만, '{sources_file_name}'에 해당 저장소 URL 정의가 없습니다.[/red]",
                )
                continue

            repo_url = helm_repos_from_sources[repo_name]
            needs_add = repo_name not in local_helm_repos_map
            needs_update = (
                repo_name in local_helm_repos_map
                and local_helm_repos_map[repo_name] != repo_url
            )

            if needs_add:
                console.print(
                    f"[yellow]➕ Helm 저장소 추가 시도: {repo_name} ({repo_url})[/yellow]",
                )
                return_code, _, stderr = run_command(
                    ["helm", "repo", "add", repo_name, repo_url],
                    check=False,
                    timeout=30,
                )
                if return_code == 0:
                    console.print(
                        f"[green]  ✅ Helm 저장소 '{repo_name}' 추가 완료.[/green]",
                    )
                    local_helm_repos_map[repo_name] = repo_url
                    needs_update = True
                else:
                    console.print(
                        f"[red]  ❌ Helm 저장소 '{repo_name}' 추가 실패: {stderr.strip()}[/red]",
                    )
                    continue

            if needs_update:
                console.print(
                    f"[yellow]🔄 Helm 저장소 업데이트 시도: {repo_name}[/yellow]",
                )
                return_code, _, stderr = run_command(
                    ["helm", "repo", "update", repo_name],
                    check=False,
                    timeout=60,
                )
                if return_code == 0:
                    console.print(
                        f"[green]  ✅ Helm 저장소 '{repo_name}' 업데이트 완료.[/green]",
                    )
                else:
                    console.print(
                        f"[red]  ❌ Helm 저장소 '{repo_name}' 업데이트 실패: {stderr.strip()}[/red]",
                    )
            elif repo_name in local_helm_repos_map:
                console.print(
                    f"[green]  ✅ Helm 저장소 '{repo_name}'는 이미 최신 상태입니다.[/green]",
                )
    else:
        console.print("[yellow]ℹ️ 준비할 Helm 저장소가 없습니다.[/yellow]")
    console.print("[cyan]--- Helm 저장소 준비 완료 ---[/cyan]")

    console.print("[cyan]--- Git 저장소 준비 시작 ---[/cyan]")
    REPOS_DIR.mkdir(parents=True, exist_ok=True)
    git_prepare_total = 0
    git_prepare_success = 0

    needed_git_repo_names = set()
    for app_info in app_info_list:
        if app_info.type == "pull-git":
            try:
                spec_obj = AppPullGitSpec(**app_info.specs)
                needed_git_repo_names.add(spec_obj.repo)
            except Exception as e:
                console.print(
                    f"[red]❌ 앱 '{app_info.name}' (타입: {app_info.type})의 Spec에서 repo 정보 추출 실패: {e}[/red]",
                )
                continue

    if needed_git_repo_names:
        if not check_command_available("git"):
            console.print(
                "[red]❌ `git` 명령을 사용할 수 없습니다. Git 저장소 준비를 건너뜁니다.[/red]",
            )
        else:
            for repo_name in needed_git_repo_names:
                git_prepare_total += 1
                if repo_name not in git_repos_from_sources:
                    console.print(
                        f"[red]❌ 앱에서 Git 저장소 '{repo_name}'를 사용하지만, '{sources_file_name}'에 해당 저장소 정보(URL 등)가 없습니다.[/red]",
                    )
                    continue

                repo_info = git_repos_from_sources[repo_name]
                repo_url = repo_info.get("url")
                repo_branch = repo_info.get("branch")

                if not repo_url:
                    console.print(
                        f"[red]❌ Git 저장소 '{repo_name}'의 URL이 '{sources_file_name}'에 정의되지 않았습니다.[/red]",
                    )
                    continue

                repo_local_path = REPOS_DIR / repo_name
                console.print(
                    f"[magenta]➡️  Git 저장소 처리 중: {repo_name} (경로: {repo_local_path})[/magenta]",
                )
                try:
                    if repo_local_path.exists() and repo_local_path.is_dir():
                        console.print(
                            f"    [yellow]🔄 기존 Git 저장소 업데이트 시도: {repo_name}[/yellow]",
                        )
                        run_command(
                            ["git", "-C", str(repo_local_path), "fetch", "origin"],
                            check=True,
                            timeout=60,
                        )
                        run_command(
                            [
                                "git",
                                "-C",
                                str(repo_local_path),
                                "reset",
                                "--hard",
                                f"origin/{repo_branch or 'HEAD'}",
                            ],
                            check=True,
                            timeout=30,
                        )
                        run_command(
                            ["git", "-C", str(repo_local_path), "clean", "-dfx"],
                            check=True,
                            timeout=30,
                        )
                        console.print(
                            f"    [green]✅ Git 저장소 '{repo_name}' 업데이트 완료.[/green]",
                        )
                    else:
                        console.print(
                            f"    [yellow]➕ Git 저장소 클론 시도: {repo_name} ({repo_url})[/yellow]",
                        )
                        clone_cmd = ["git", "clone", repo_url, str(repo_local_path)]
                        if repo_branch:
                            clone_cmd.extend(["--branch", repo_branch])
                        run_command(clone_cmd, check=True, timeout=300)
                        console.print(
                            f"    [green]✅ Git 저장소 '{repo_name}' 클론 완료.[/green]",
                        )
                    git_prepare_success += 1
                except Exception as e:
                    console.print(
                        f"[red]❌ Git 저장소 '{repo_name}' 작업 실패: {e}[/red]",
                    )
    else:
        console.print("[yellow]ℹ️ 준비할 Git 저장소가 없습니다.[/yellow]")
    console.print(
        f"[cyan]--- Git 저장소 준비 완료 ({git_prepare_success}/{git_prepare_total} 성공) ---[/cyan]",
    )

    console.print("[cyan]--- Helm 차트 풀링 시작 ---[/cyan]")
    CHARTS_DIR.mkdir(parents=True, exist_ok=True)
    chart_pull_total = 0
    chart_pull_success = 0

    for app_info in app_info_list:
        if app_info.type not in ["pull-helm", "pull-helm-oci"]:
            continue

        chart_pull_total += 1
        spec_obj = None
        try:
            if app_info.type == "pull-helm":
                spec_obj = AppPullHelmSpec(**app_info.specs)
            else:
                spec_obj = AppPullHelmOciSpec(**app_info.specs)
        except Exception as e:
            console.print(
                f"[red]❌ 앱 '{app_info.name}' (타입: {app_info.type})의 Spec 데이터 검증/변환 중 오류: {e}[/red]",
            )
            continue

        repo_name = spec_obj.repo
        chart_name = spec_obj.chart
        chart_version = spec_obj.chart_version
        destination_subdir_name = spec_obj.dest or chart_name
        chart_destination_base_path = CHARTS_DIR / destination_subdir_name

        console.print(
            f"[magenta]➡️  Helm 차트 풀링 시도: {repo_name}/{chart_name} (버전: {chart_version or 'latest'}) → {chart_destination_base_path}[/magenta]",
        )

        if chart_destination_base_path.exists():
            console.print(
                f"    [yellow]🗑️  기존 차트 디렉토리 삭제: {chart_destination_base_path}[/yellow]",
            )
            try:
                shutil.rmtree(chart_destination_base_path)
            except OSError as e:
                console.print(
                    f"[red]    ❌ 기존 차트 디렉토리 삭제 실패: {e}. 권한 등을 확인하세요.[/red]",
                )
                continue

        helm_pull_cmd = ["helm", "pull"]
        pull_target = ""

        if app_info.type == "pull-helm":
            if (
                repo_name not in helm_repos_from_sources
                and repo_name not in local_helm_repos_map
            ):
                is_oci_repo_check = any(
                    app_oci.type == "pull-helm-oci"
                    and AppPullHelmOciSpec(**app_oci.specs).repo == repo_name
                    for app_oci in app_info_list
                    if app_oci.type == "pull-helm-oci"
                )
                if not is_oci_repo_check:
                    console.print(
                        f"[red]❌ Helm 저장소 '{repo_name}'가 로컬에 추가되어 있지 않거나 '{sources_file_name}'에 정의되지 않았습니다. '{repo_name}/{chart_name}' 풀링 불가.[/red]",
                    )
                    continue
            pull_target = f"{repo_name}/{chart_name}"
            helm_pull_cmd.append(pull_target)
        else:
            oci_repo_charts = oci_repos_from_sources.get(repo_name, {})
            oci_chart_url = oci_repo_charts.get(chart_name)
            if not oci_chart_url:
                console.print(
                    f"[red]❌ OCI 차트 '{repo_name}/{chart_name}'의 URL을 '{sources_file_name}'의 `oci_repos` 섹션에서 찾을 수 없습니다.[/red]",
                )
                console.print(
                    f"    [yellow]L 확인된 OCI 저장소 정보: {oci_repo_charts}[/yellow]",
                )
                continue
            pull_target = oci_chart_url
            helm_pull_cmd.append(pull_target)

        helm_pull_cmd.extend(["-d", str(CHARTS_DIR), "--untar"])
        if chart_version:
            helm_pull_cmd.extend(["--version", chart_version])

        console.print(f"    [cyan]$ {' '.join(helm_pull_cmd)}[/cyan]")
        return_code, stdout, stderr = run_command(
            helm_pull_cmd,
            check=False,
            timeout=300,
        )

        if return_code == 0:
            pulled_chart_path = CHARTS_DIR / chart_name
            final_chart_path = CHARTS_DIR / destination_subdir_name

            if pulled_chart_path.exists() and pulled_chart_path.is_dir():
                if pulled_chart_path != final_chart_path:
                    if final_chart_path.exists():
                        shutil.rmtree(final_chart_path)
                    shutil.move(str(pulled_chart_path), str(final_chart_path))
                    console.print(
                        f"    [green]  ✅ Helm 차트 '{pull_target}' 풀링 및 이름 변경 완료: {final_chart_path}[/green]",
                    )
                else:
                    console.print(
                        f"    [green]  ✅ Helm 차트 '{pull_target}' 풀링 완료: {final_chart_path}[/green]",
                    )
                chart_pull_success += 1
            else:
                console.print(
                    f"[red]    ❌ Helm 차트 '{pull_target}' 풀링 후 예상된 경로({pulled_chart_path})에서 차트를 찾을 수 없습니다.[/red]",
                )
                if stdout:
                    console.print(f"        [blue]STDOUT:[/blue] {stdout.strip()}")
                if stderr:
                    console.print(f"        [red]STDERR:[/red] {stderr.strip()}")
        else:
            console.print(
                f"[red]❌ Helm 차트 '{pull_target}' 풀링 실패: {stderr.strip()}[/red]",
            )

    console.print(
        f"[cyan]--- Helm 차트 풀링 완료 ({chart_pull_success}/{chart_pull_total} 성공) ---[/cyan]",
    )

    total_prepare_tasks = git_prepare_total + chart_pull_total
    total_prepare_success = git_prepare_success + chart_pull_success

    if total_prepare_tasks > 0:
        console.print(
            f"[bold green]✅ `prepare` 작업 요약: 총 {total_prepare_tasks}개 중 {total_prepare_success}개 성공.[/bold green]",
        )
    else:
        console.print(
            "[bold yellow]✅ `prepare` 작업 대상이 없습니다 (pull-helm, pull-git 등).[/bold yellow]",
        )

    console.print("[bold blue]✨ `prepare` 작업 완료 ✨[/bold blue]")
