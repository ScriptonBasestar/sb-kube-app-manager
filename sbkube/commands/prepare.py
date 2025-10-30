"""
SBKube prepare 명령어.

새로운 기능:
- helm 타입: 자동으로 chart pull (repo/chart 형식 파싱)
- git 타입: 리포지토리 clone
"""

import shutil
from pathlib import Path

import click
from rich.console import Console

from sbkube.models.config_model import GitApp, HelmApp, HttpApp, SBKubeConfig
from sbkube.models.sources_model import SourceScheme
from sbkube.utils.cli_check import check_helm_installed_or_exit
from sbkube.utils.cluster_config import (
    ClusterConfigError,
    apply_cluster_config_to_command,
    resolve_cluster_config,
)
from sbkube.utils.common import find_sources_file, run_command
from sbkube.utils.file_loader import load_config_file

console = Console()


def parse_helm_chart(chart: str) -> tuple[str, str]:
    """
    'repo/chart' 형식을 파싱.

    Args:
        chart: "bitnami/redis" 형식의 문자열

    Returns:
        (repo_name, chart_name) 튜플
    """
    parts = chart.split("/")
    if len(parts) != 2:
        raise ValueError(f"Invalid chart format: {chart}. Expected 'repo/chart'")
    return parts[0], parts[1]


def prepare_helm_app(
    app_name: str,
    app: HelmApp,
    base_dir: Path,
    charts_dir: Path,
    sources_file: Path,
    kubeconfig: str | None = None,
    context: str | None = None,
    force: bool = False,
    dry_run: bool = False,
) -> bool:
    """
    Helm 앱 준비 (chart pull).

    로컬 차트는 prepare 단계를 건너뜁니다.

    Args:
        app_name: 앱 이름
        app: HelmApp 설정
        base_dir: 프로젝트 루트
        charts_dir: charts 디렉토리
        sources_file: sources.yaml 파일 경로
        force: 기존 차트를 덮어쓰기
        dry_run: dry-run 모드 (실제 다운로드하지 않음)

    Returns:
        성공 여부
    """
    console.print(f"[cyan]📦 Preparing Helm app: {app_name}[/cyan]")

    # 로컬 차트는 prepare 불필요
    if not app.is_remote_chart():
        console.print(
            f"[yellow]⏭️  Local chart detected, skipping prepare: {app.chart}[/yellow]"
        )
        return True

    # Remote chart: pull 수행
    repo_name = app.get_repo_name()
    chart_name = app.get_chart_name()

    # sources.yaml에서 repo URL 찾기
    if not sources_file.exists():
        console.print(f"[red]❌ sources.yaml not found: {sources_file}[/red]")
        return False

    sources = load_config_file(sources_file)
    helm_sources = sources.get("helm_repos", {})

    if repo_name not in helm_sources:
        console.print(
            f"[red]❌ Helm repo '{repo_name}' not found in sources.yaml[/red]"
        )
        return False

    # helm_repos는 dict 형태: {url: ..., username: ..., password: ...} 또는 단순 URL string
    repo_config = helm_sources[repo_name]
    if isinstance(repo_config, dict):
        repo_url = repo_config.get("url")
        if not repo_url:
            console.print(f"[red]❌ Missing 'url' for Helm repo: {repo_name}[/red]")
            return False
    else:
        # 구버전 호환: 단순 URL string
        repo_url = repo_config

    if dry_run:
        console.print(
            f"[yellow]🔍 [DRY-RUN] Would add Helm repo: {repo_name} ({repo_url})[/yellow]"
        )
        console.print(
            f"[yellow]🔍 [DRY-RUN] Would update Helm repo: {repo_name}[/yellow]"
        )
    else:
        # Helm repo 추가
        console.print(f"  Adding Helm repo: {repo_name} ({repo_url})")
        cmd = ["helm", "repo", "add", repo_name, repo_url]
        cmd = apply_cluster_config_to_command(cmd, kubeconfig, context)
        return_code, stdout, stderr = run_command(cmd)

        if return_code != 0:
            console.print(
                f"[yellow]⚠️ Failed to add repo (might already exist): {stderr}[/yellow]"
            )

        # Helm repo 업데이트
        console.print(f"  Updating Helm repo: {repo_name}")
        cmd = ["helm", "repo", "update", repo_name]
        cmd = apply_cluster_config_to_command(cmd, kubeconfig, context)
        return_code, stdout, stderr = run_command(cmd)

        if return_code != 0:
            console.print(f"[red]❌ Failed to update repo: {stderr}[/red]")
            return False

    # Chart pull
    dest_dir = charts_dir / chart_name
    chart_yaml = dest_dir / chart_name / "Chart.yaml"

    # Check if chart already exists (skip if not --force)
    if chart_yaml.exists() and not force:
        console.print(
            f"[yellow]⏭️  Chart already exists, skipping: {chart_name}[/yellow]"
        )
        console.print("    Use --force to re-download")
        return True

    if dry_run:
        console.print(
            f"[yellow]🔍 [DRY-RUN] Would pull chart: {app.chart} → {dest_dir}[/yellow]"
        )
        if app.version:
            console.print(f"[yellow]🔍 [DRY-RUN] Chart version: {app.version}[/yellow]")
        if force:
            console.print(
                "[yellow]🔍 [DRY-RUN] Would remove existing chart (--force)[/yellow]"
            )
    else:
        # If force flag is set, remove existing chart directory
        if force and dest_dir.exists():
            console.print(
                f"[yellow]⚠️  Removing existing chart (--force): {dest_dir}[/yellow]"
            )
            shutil.rmtree(dest_dir)

        dest_dir.mkdir(parents=True, exist_ok=True)

        console.print(f"  Pulling chart: {app.chart} → {dest_dir}")
        cmd = [
            "helm",
            "pull",
            f"{repo_name}/{chart_name}",
            "--untar",
            "--untardir",
            str(dest_dir),
        ]

        if app.version:
            cmd.extend(["--version", app.version])

        cmd = apply_cluster_config_to_command(cmd, kubeconfig, context)
        return_code, stdout, stderr = run_command(cmd)

        if return_code != 0:
            console.print(f"[red]❌ Failed to pull chart: {stderr}[/red]")
            return False

    console.print(f"[green]✅ Helm app prepared: {app_name}[/green]")
    return True


def prepare_http_app(
    app_name: str,
    app: HttpApp,
    base_dir: Path,
    app_config_dir: Path,
    dry_run: bool = False,
) -> bool:
    """
    HTTP 앱 준비 (파일 다운로드).

    Args:
        app_name: 앱 이름
        app: HttpApp 설정
        base_dir: 프로젝트 루트
        app_config_dir: 앱 설정 디렉토리
        dry_run: dry-run 모드 (실제 다운로드하지 않음)

    Returns:
        성공 여부
    """
    console.print(f"[cyan]📦 Preparing HTTP app: {app_name}[/cyan]")

    # 다운로드 대상 경로
    dest_path = app_config_dir / app.dest

    # 이미 존재하면 건너뛰기
    if dest_path.exists():
        console.print(
            f"[yellow]⏭️  File already exists, skipping download: {dest_path}[/yellow]"
        )
        return True

    if dry_run:
        console.print(
            f"[yellow]🔍 [DRY-RUN] Would download: {app.url} → {dest_path}[/yellow]"
        )
        if app.headers:
            console.print(f"[yellow]🔍 [DRY-RUN] Headers: {app.headers}[/yellow]")
    else:
        # 디렉토리 생성
        dest_path.parent.mkdir(parents=True, exist_ok=True)

        # HTTP 다운로드 (curl 사용)
        console.print(f"  Downloading: {app.url} → {dest_path}")
        cmd = ["curl", "-L", "-o", str(dest_path), app.url]

        # Headers 추가
        for key, value in app.headers.items():
            cmd.extend(["-H", f"{key}: {value}"])

        return_code, stdout, stderr = run_command(cmd, timeout=300)

        if return_code != 0:
            console.print(f"[red]❌ Failed to download: {stderr}[/red]")
            # 실패 시 파일 삭제
            if dest_path.exists():
                dest_path.unlink()
            return False

    console.print(f"[green]✅ HTTP app prepared: {app_name}[/green]")
    return True


def prepare_git_app(
    app_name: str,
    app: GitApp,
    base_dir: Path,
    repos_dir: Path,
    sources_file: Path,
    force: bool = False,
    dry_run: bool = False,
) -> bool:
    """
    Git 앱 준비 (repo clone).

    Args:
        app_name: 앱 이름
        app: GitApp 설정
        base_dir: 프로젝트 루트
        repos_dir: repos 디렉토리
        sources_file: sources.yaml 파일 경로
        force: 기존 리포지토리를 덮어쓰기
        dry_run: dry-run 모드 (실제 클론하지 않음)

    Returns:
        성공 여부
    """
    console.print(f"[cyan]📦 Preparing Git app: {app_name}[/cyan]")

    # sources.yaml에서 repo URL 찾기
    if not sources_file.exists():
        console.print(f"[red]❌ sources.yaml not found: {sources_file}[/red]")
        return False

    sources = load_config_file(sources_file)
    git_sources = sources.get("git_repos", {})

    # app.repo가 alias인지 URL인지 판단
    if (
        app.repo.startswith("http://")
        or app.repo.startswith("https://")
        or app.repo.startswith("git@")
    ):
        repo_url = app.repo
        repo_alias = app_name
        branch = app.branch or app.ref or "main"
    else:
        # sources.yaml에서 찾기
        if app.repo not in git_sources:
            console.print(
                f"[red]❌ Git repo '{app.repo}' not found in sources.yaml[/red]"
            )
            return False
        repo_config = git_sources[app.repo]
        # repo_config는 dict 형태: {url: ..., branch: ...}
        if isinstance(repo_config, dict):
            repo_url = repo_config.get("url")
            if not repo_url:
                console.print(f"[red]❌ Missing 'url' for Git repo: {app.repo}[/red]")
                return False
            branch = app.branch or app.ref or repo_config.get("branch", "main")
        else:
            # 구버전 호환: 단순 URL string
            repo_url = repo_config
            branch = app.branch or app.ref or "main"
        repo_alias = app.repo

    dest_dir = repos_dir / repo_alias
    git_dir = dest_dir / ".git"

    # Check if repository already exists (skip if not --force)
    if git_dir.exists() and not force:
        console.print(
            f"[yellow]⏭️  Repository already exists, skipping: {repo_alias}[/yellow]"
        )
        console.print("    Use --force to re-clone")
        return True

    if dry_run:
        console.print(
            f"[yellow]🔍 [DRY-RUN] Would clone: {repo_url} (branch: {branch}) → {dest_dir}[/yellow]"
        )
        if force and dest_dir.exists():
            console.print(
                "[yellow]🔍 [DRY-RUN] Would remove existing repository (--force)[/yellow]"
            )
    else:
        # If force flag is set, remove existing repository
        if force and dest_dir.exists():
            console.print(
                f"[yellow]⚠️  Removing existing repository (--force): {dest_dir}[/yellow]"
            )
            shutil.rmtree(dest_dir)

        dest_dir.mkdir(parents=True, exist_ok=True)

        # Git clone
        console.print(f"  Cloning: {repo_url} (branch: {branch}) → {dest_dir}")
        cmd = ["git", "clone", repo_url, str(dest_dir)]

        if branch:
            cmd.extend(["--branch", branch])

        return_code, stdout, stderr = run_command(cmd)

        if return_code != 0:
            console.print(f"[red]❌ Failed to clone repository: {stderr}[/red]")
            return False

    console.print(f"[green]✅ Git app prepared: {app_name}[/green]")
    return True


@click.command(name="prepare")
@click.option(
    "--app-dir",
    "app_config_dir_name",
    default=".",
    help="앱 설정 디렉토리 (config.yaml 위치, base-dir 기준)",
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
    default="config.yaml",
    help="설정 파일 이름 (app-dir 내부)",
)
@click.option(
    "--sources",
    "sources_file_name",
    default="sources.yaml",
    help="소스 설정 파일 (base-dir 기준)",
)
@click.option(
    "--app",
    "app_name",
    default=None,
    help="준비할 특정 앱 이름 (지정하지 않으면 모든 앱 준비)",
)
@click.option(
    "--force",
    is_flag=True,
    default=False,
    help="기존 리소스를 덮어쓰기 (Helm chart pull --force)",
)
@click.option(
    "--dry-run",
    is_flag=True,
    default=False,
    help="Dry-run 모드 (실제 리소스를 다운로드하지 않음)",
)
@click.pass_context
def cmd(
    ctx: click.Context,
    app_config_dir_name: str,
    base_dir: str,
    config_file_name: str,
    sources_file_name: str,
    app_name: str | None,
    force: bool,
    dry_run: bool,
):
    """
    SBKube prepare 명령어.

    외부 리소스를 준비합니다:
    - helm 타입: Helm chart pull
    - git 타입: Git repository clone
    """
    console.print("[bold blue]✨ SBKube `prepare` 시작 ✨[/bold blue]")

    # Helm 설치 확인
    check_helm_installed_or_exit()

    # 경로 설정
    BASE_DIR = Path(base_dir).resolve()
    APP_CONFIG_DIR = BASE_DIR / app_config_dir_name
    config_file_path = APP_CONFIG_DIR / config_file_name

    # sources.yaml 찾기 (CLI --sources 옵션 또는 --env 우선)
    sources_file_name = ctx.obj.get("sources_file", sources_file_name)
    sources_file_path = find_sources_file(BASE_DIR, APP_CONFIG_DIR, sources_file_name)

    if not sources_file_path:
        console.print("[red]❌ sources.yaml not found in:[/red]")
        console.print(f"  - {APP_CONFIG_DIR / sources_file_name}")
        console.print(f"  - {APP_CONFIG_DIR.parent / sources_file_name}")
        console.print(f"  - {BASE_DIR / sources_file_name}")
        raise click.Abort()

    console.print(f"[cyan]📄 Using sources file: {sources_file_path}[/cyan]")

    # sources.yaml 로드 및 클러스터 설정 해석
    sources_data = load_config_file(sources_file_path)
    try:
        sources = SourceScheme(**sources_data)
    except Exception as e:
        console.print(f"[red]❌ Invalid sources file: {e}[/red]")
        raise click.Abort()

    # 클러스터 설정 해석
    try:
        kubeconfig, context = resolve_cluster_config(
            cli_kubeconfig=ctx.obj.get("kubeconfig"),
            cli_context=ctx.obj.get("context"),
            sources=sources,
        )
    except ClusterConfigError as e:
        console.print(f"[red]{e}[/red]")
        raise click.Abort()

    # charts/repos 디렉토리는 sources.yaml이 있는 위치 기준
    SOURCES_BASE_DIR = sources_file_path.parent
    CHARTS_DIR = SOURCES_BASE_DIR / "charts"
    REPOS_DIR = SOURCES_BASE_DIR / "repos"

    # 디렉토리 생성
    CHARTS_DIR.mkdir(parents=True, exist_ok=True)
    REPOS_DIR.mkdir(parents=True, exist_ok=True)

    # 설정 파일 로드
    if not config_file_path.exists():
        console.print(f"[red]❌ Config file not found: {config_file_path}[/red]")
        raise click.Abort()

    console.print(f"[cyan]📄 Loading config: {config_file_path}[/cyan]")
    config_data = load_config_file(config_file_path)

    try:
        config = SBKubeConfig(**config_data)
    except Exception as e:
        console.print(f"[red]❌ Invalid config file: {e}[/red]")
        raise click.Abort()

    # 배포 순서 얻기 (의존성 고려)
    deployment_order = config.get_deployment_order()

    if app_name:
        # 특정 앱만 준비
        if app_name not in config.apps:
            console.print(f"[red]❌ App not found: {app_name}[/red]")
            raise click.Abort()
        apps_to_prepare = [app_name]
    else:
        # 모든 앱 준비 (의존성 순서대로)
        apps_to_prepare = deployment_order

    # 앱 준비
    success_count = 0
    total_count = len(apps_to_prepare)

    for app_name in apps_to_prepare:
        app = config.apps[app_name]

        if not app.enabled:
            console.print(f"[yellow]⏭️  Skipping disabled app: {app_name}[/yellow]")
            continue

        success = False

        if isinstance(app, HelmApp):
            success = prepare_helm_app(
                app_name,
                app,
                BASE_DIR,
                CHARTS_DIR,
                sources_file_path,
                kubeconfig,
                context,
                force,
                dry_run,
            )
        elif isinstance(app, GitApp):
            success = prepare_git_app(
                app_name, app, BASE_DIR, REPOS_DIR, sources_file_path, force, dry_run
            )
        elif isinstance(app, HttpApp):
            success = prepare_http_app(app_name, app, BASE_DIR, APP_CONFIG_DIR, dry_run)
        else:
            console.print(
                f"[yellow]⏭️  App type '{app.type}' does not require prepare: {app_name}[/yellow]"
            )
            success = True  # 건너뛰어도 성공으로 간주

        if success:
            success_count += 1

    # 결과 출력
    console.print(
        f"\n[bold green]✅ Prepare completed: {success_count}/{total_count} apps[/bold green]"
    )

    if success_count < total_count:
        raise click.Abort()
