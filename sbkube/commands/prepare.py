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
from sbkube.utils.hook_executor import HookExecutor

console = Console()


def parse_helm_chart(chart: str) -> tuple[str, str]:
    """
    'repo/chart' 형식을 파싱.

    Args:
        chart: "grafana/grafana" 형식의 문자열

    Returns:
        (repo_name, chart_name) 튜플
    """
    parts = chart.split("/")
    if len(parts) != 2:
        raise ValueError(f"Invalid chart format: {chart}. Expected 'repo/chart'")
    return parts[0], parts[1]


def prepare_oci_chart(
    app_name: str,
    app: HelmApp,
    charts_dir: Path,
    oci_sources: dict,
    repo_name: str,
    chart_name: str,
    kubeconfig: str | None = None,
    context: str | None = None,
    force: bool = False,
    dry_run: bool = False,
) -> bool:
    """
    OCI 레지스트리에서 Helm 차트를 Pull합니다.

    OCI 레지스트리는 helm repo add/update가 필요없이
    helm pull oci://registry/chart 형식으로 직접 다운로드합니다.

    Args:
        app_name: 앱 이름
        app: HelmApp 설정
        charts_dir: charts 디렉토리
        oci_sources: sources.yaml의 oci_registries 섹션
        repo_name: 레지스트리 이름 (sources.yaml 키)
        chart_name: 차트 이름
        kubeconfig: kubeconfig 경로
        context: kubectl context
        force: 기존 차트 덮어쓰기
        dry_run: dry-run 모드

    Returns:
        성공 여부
    """
    console.print(f"[cyan]📦 Preparing OCI chart: {app_name}[/cyan]")

    # OCI 레지스트리 설정 가져오기
    oci_config = oci_sources[repo_name]
    if isinstance(oci_config, dict):
        registry_url = oci_config.get("registry")
        username = oci_config.get("username")
        password = oci_config.get("password")
    else:
        # 구버전 호환: 단순 URL string
        registry_url = oci_config
        username = None
        password = None

    if not registry_url:
        console.print(f"[red]❌ Missing 'registry' for OCI registry: {repo_name}[/red]")
        return False

    # OCI URL 구성
    # registry_url 형식: "oci://tccr.io/truecharts" 또는 "tccr.io/truecharts"
    if not registry_url.startswith("oci://"):
        registry_url = f"oci://{registry_url}"

    oci_chart_url = f"{registry_url}/{chart_name}"

    # 인증이 필요한 경우 (추후 구현)
    if username and password:
        console.print("[yellow]⚠️ OCI registry authentication is not yet supported[/yellow]")
        console.print("[yellow]   Using public registry access[/yellow]")

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
            f"[yellow]🔍 [DRY-RUN] Would pull OCI chart: {oci_chart_url} → {dest_dir}[/yellow]"
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

        console.print(f"  Pulling OCI chart: {oci_chart_url} → {dest_dir}")
        cmd = [
            "helm",
            "pull",
            oci_chart_url,
            "--untar",
            "--untardir",
            str(dest_dir),
        ]

        if app.version:
            cmd.extend(["--version", app.version])

        cmd = apply_cluster_config_to_command(cmd, kubeconfig, context)
        return_code, stdout, stderr = run_command(cmd)

        if return_code != 0:
            console.print(f"[red]❌ Failed to pull OCI chart: {stderr}[/red]")
            console.print(f"[yellow]💡 Possible reasons:[/yellow]")
            console.print(f"   1. OCI registry URL might be incorrect: {registry_url}")
            console.print(f"   2. Chart '{chart_name}' does not exist in the registry")
            console.print(f"   3. Authentication might be required (check username/password in sources.yaml)")
            console.print(f"   4. Registry might not support OCI format")
            console.print(f"[yellow]💡 Verify OCI registry:[/yellow]")
            console.print(f"   • Test pull manually: [cyan]helm pull {oci_chart_url}[/cyan]")
            console.print(f"   • Check registry documentation for correct OCI path")
            return False

    console.print(f"[green]✅ OCI chart prepared: {app_name}[/green]")
    return True


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
    OCI 레지스트리와 일반 Helm 레지스트리를 모두 지원합니다.

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
    oci_sources = sources.get("oci_registries", {})

    # OCI 레지스트리 체크 (우선순위)
    if repo_name in oci_sources:
        return prepare_oci_chart(
            app_name=app_name,
            app=app,
            charts_dir=charts_dir,
            oci_sources=oci_sources,
            repo_name=repo_name,
            chart_name=chart_name,
            kubeconfig=kubeconfig,
            context=context,
            force=force,
            dry_run=dry_run,
        )

    # 일반 Helm 레지스트리 체크
    if repo_name not in helm_sources:
        console.print(f"[red]❌ Helm repo '{repo_name}' not found in sources.yaml[/red]")
        console.print(f"[yellow]💡 Solutions:[/yellow]")
        console.print(f"   1. Check for typos in sources.yaml (e.g., '{repo_name}' → similar name?)")
        console.print(f"   2. Search for '{chart_name}' chart: https://artifacthub.io/packages/search?ts_query_web={chart_name}")
        console.print(f"   3. Add repository to sources.yaml:")
        console.print(f"      [cyan]helm_repos:[/cyan]")
        console.print(f"      [cyan]  {repo_name}: https://example.com/helm-charts[/cyan]")
        console.print(f"   4. Or check if it's an OCI registry:")
        console.print(f"      [cyan]oci_registries:[/cyan]")
        console.print(f"      [cyan]  {repo_name}: oci://registry.example.com/charts[/cyan]")
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
            console.print(f"[yellow]💡 Possible reasons:[/yellow]")
            console.print(f"   1. Chart '{chart_name}' does not exist in '{repo_name}' repository")
            console.print(f"   2. Repository might be deprecated or moved")
            console.print(f"   3. Chart name might be different (check exact name)")
            console.print(f"[yellow]💡 Search for the chart:[/yellow]")
            console.print(f"   • Artifact Hub: https://artifacthub.io/packages/search?ts_query_web={chart_name}")
            console.print(f"   • List charts in repo: [cyan]helm search repo {repo_name}/[/cyan]")
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
    "--source",
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

    # sources.yaml 찾기 (CLI --source 옵션 또는 --profile 우선)
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

    # Hook executor 초기화
    hook_executor = HookExecutor(
        base_dir=BASE_DIR,
        work_dir=APP_CONFIG_DIR,  # 훅은 APP_CONFIG_DIR에서 실행
        dry_run=dry_run,
    )

    # ========== 전역 pre-prepare 훅 실행 ==========
    if config.hooks and "prepare" in config.hooks:
        prepare_hooks = config.hooks["prepare"].model_dump()
        if not hook_executor.execute_command_hooks(
            hook_config=prepare_hooks,
            hook_phase="pre",
            command_name="prepare",
        ):
            console.print("[red]❌ Pre-prepare hook failed[/red]")
            raise click.Abort()

    # 앱 준비
    success_count = 0
    total_count = len(apps_to_prepare)
    preparation_failed = False

    for app_name in apps_to_prepare:
        app = config.apps[app_name]

        if not app.enabled:
            console.print(f"[yellow]⏭️  Skipping disabled app: {app_name}[/yellow]")
            continue

        # ========== 앱별 pre-prepare 훅 실행 ==========
        if hasattr(app, "hooks") and app.hooks:
            app_hooks = app.hooks.model_dump()
            if not hook_executor.execute_app_hook(
                app_name=app_name,
                app_hooks=app_hooks,
                hook_type="pre_prepare",
                context={},
            ):
                console.print(f"[red]❌ Pre-prepare hook failed for app: {app_name}[/red]")
                preparation_failed = True
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

        # ========== 앱별 post-prepare 훅 실행 ==========
        if hasattr(app, "hooks") and app.hooks:
            app_hooks = app.hooks.model_dump()
            if success:
                # 준비 성공 시 post_prepare 훅 실행
                hook_executor.execute_app_hook(
                    app_name=app_name,
                    app_hooks=app_hooks,
                    hook_type="post_prepare",
                    context={},
                )
            else:
                preparation_failed = True

        if success:
            success_count += 1
        else:
            preparation_failed = True

    # ========== 전역 post-prepare 훅 실행 ==========
    if config.hooks and "prepare" in config.hooks:
        prepare_hooks = config.hooks["prepare"].model_dump()

        if preparation_failed:
            # 준비 실패 시 on_failure 훅 실행
            hook_executor.execute_command_hooks(
                hook_config=prepare_hooks,
                hook_phase="on_failure",
                command_name="prepare",
            )
        else:
            # 모든 준비 성공 시 post 훅 실행
            hook_executor.execute_command_hooks(
                hook_config=prepare_hooks,
                hook_phase="post",
                command_name="prepare",
            )

    # 결과 출력
    console.print(
        f"\n[bold green]✅ Prepare completed: {success_count}/{total_count} apps[/bold green]"
    )

    if success_count < total_count:
        raise click.Abort()
