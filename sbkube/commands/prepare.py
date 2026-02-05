"""SBKube prepare 명령어.

새로운 기능:
- helm 타입: 자동으로 chart pull (repo/chart 형식 파싱)
- git 타입: 리포지토리 clone
"""

import shutil
import uuid
from pathlib import Path

import click

from sbkube.models.config_model import GitApp, HelmApp, HookApp, HttpApp, SBKubeConfig
from sbkube.models.sources_model import SourceScheme
from sbkube.utils.app_dir_resolver import resolve_app_dirs
from sbkube.utils.cli_check import check_helm_installed_or_exit
from sbkube.utils.workspace_resolver import SbkubeDirectories
from sbkube.utils.cluster_config import (
    ClusterConfigError,
    apply_cluster_config_to_command,
    resolve_cluster_config,
)
from sbkube.utils.common import find_sources_file, run_command
from sbkube.utils.file_loader import load_config_file
from sbkube.utils.hook_executor import HookExecutor
from sbkube.utils.output_manager import OutputManager


def parse_helm_chart(chart: str) -> tuple[str, str]:
    """'repo/chart' 형식을 파싱.

    Args:
        chart: "grafana/grafana" 형식의 문자열

    Returns:
        (repo_name, chart_name) 튜플

    """
    parts = chart.split("/")
    if len(parts) != 2:
        msg = f"Invalid chart format: {chart}. Expected 'repo/chart'"
        raise ValueError(msg)
    return parts[0], parts[1]


def prepare_oci_chart(
    app_name: str,
    app: HelmApp,
    charts_dir: Path,
    oci_sources: dict,
    repo_name: str,
    chart_name: str,
    output: OutputManager,
    kubeconfig: str | None = None,
    context: str | None = None,
    force: bool = False,
    dry_run: bool = False,
) -> bool:
    """OCI 레지스트리에서 Helm 차트를 Pull합니다.

    OCI 레지스트리는 helm repo add/update가 필요없이
    helm pull oci://registry/chart 형식으로 직접 다운로드합니다.

    Args:
        app_name: 앱 이름
        app: HelmApp 설정
        charts_dir: charts 디렉토리
        oci_sources: sources.yaml의 oci_registries 섹션
        repo_name: 레지스트리 이름 (sources.yaml 키)
        chart_name: 차트 이름
        output: OutputManager 인스턴스
        kubeconfig: kubeconfig 경로
        context: kubectl context
        force: 기존 차트 덮어쓰기
        dry_run: dry-run 모드

    Returns:
        성공 여부

    """
    output.print(f"[cyan]📦 Preparing OCI chart: {app_name}[/cyan]")

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
        output.print_error(f"Missing 'registry' for OCI registry: {repo_name}")
        return False

    # OCI URL 구성
    # registry_url 형식: "oci://tccr.io/truecharts" 또는 "tccr.io/truecharts"
    if not registry_url.startswith("oci://"):
        registry_url = f"oci://{registry_url}"

    oci_chart_url = f"{registry_url}/{chart_name}"

    # 인증이 필요한 경우 (추후 구현)
    if username and password:
        output.print_warning("OCI registry authentication is not yet supported")
        output.print("   Using public registry access")

    # Chart pull (repo/chart-version 구조)
    chart_dir = app.get_chart_path(charts_dir)
    chart_yaml = chart_dir / "Chart.yaml"

    # Check if chart already exists (skip if not --force)
    if chart_yaml.exists() and not force:
        output.print_warning(f"Chart already exists, skipping: {chart_dir.name}")
        output.print("    Use --force to re-download")
        return True

    if dry_run:
        output.print(
            f"[yellow]🔍 [DRY-RUN] Would pull OCI chart: {oci_chart_url} → {chart_dir}[/yellow]"
        )
        if app.version:
            output.print(f"[yellow]🔍 [DRY-RUN] Chart version: {app.version}[/yellow]")
        if force:
            output.print(
                "[yellow]🔍 [DRY-RUN] Would remove existing chart (--force)[/yellow]"
            )
    else:
        # If force flag is set, remove existing chart directory
        if force and chart_dir.exists():
            output.print_warning(f"Removing existing chart (--force): {chart_dir}")
            shutil.rmtree(chart_dir)

        chart_dir.parent.mkdir(parents=True, exist_ok=True)

        output.print(f"  Pulling OCI chart: {oci_chart_url} → {chart_dir}")

        # Helm pull with temporary extraction, then move to versioned directory
        # Use UUID suffix to prevent concurrent execution conflicts
        temp_extract_dir = (
            chart_dir.parent / f"_temp_{chart_name}_{uuid.uuid4().hex[:8]}"
        )
        cmd = [
            "helm",
            "pull",
            oci_chart_url,
            "--untar",
            "--untardir",
            str(temp_extract_dir),
        ]

        if app.version:
            cmd.extend(["--version", app.version])

        cmd = apply_cluster_config_to_command(cmd, kubeconfig, context)
        return_code, _stdout, stderr = run_command(cmd)

        if return_code != 0:
            output.print_error(f"Failed to pull OCI chart: {stderr}")
            output.print("[yellow]💡 Possible reasons:[/yellow]")
            output.print(f"   1. OCI registry URL might be incorrect: {registry_url}")
            output.print(f"   2. Chart '{chart_name}' does not exist in the registry")
            output.print(
                "   3. Authentication might be required (check username/password in sources.yaml)"
            )
            output.print("   4. Registry might not support OCI format")
            output.print("[yellow]💡 Verify OCI registry:[/yellow]")
            output.print(
                f"   • Test pull manually: [cyan]helm pull {oci_chart_url}[/cyan]"
            )
            output.print("   • Check registry documentation for correct OCI path")
            # Cleanup temp directory on failure
            if temp_extract_dir.exists():
                shutil.rmtree(temp_extract_dir)
            return False

        # Move extracted chart to versioned directory
        extracted_chart_path = temp_extract_dir / chart_name
        if not extracted_chart_path.exists():
            output.print_error(
                f"Chart extraction failed: expected {extracted_chart_path}"
            )
            if temp_extract_dir.exists():
                shutil.rmtree(temp_extract_dir)
            return False

        # Move to final destination
        extracted_chart_path.rename(chart_dir)

        # Cleanup temp directory
        if temp_extract_dir.exists():
            shutil.rmtree(temp_extract_dir)

    output.print_success(f"OCI chart prepared: {app_name}")
    return True


def prepare_helm_app(
    app_name: str,
    app: HelmApp,
    base_dir: Path,
    charts_dir: Path,
    sources_file: Path,
    output: OutputManager,
    kubeconfig: str | None = None,
    context: str | None = None,
    force: bool = False,
    dry_run: bool = False,
    helm_repos: dict | None = None,
    oci_registries: dict | None = None,
) -> bool:
    """Helm 앱 준비 (chart pull).

    로컬 차트는 prepare 단계를 건너뜁니다.
    OCI 레지스트리와 일반 Helm 레지스트리를 모두 지원합니다.

    Args:
        app_name: 앱 이름
        app: HelmApp 설정
        base_dir: 프로젝트 루트
        charts_dir: charts 디렉토리
        sources_file: sources.yaml 파일 경로
        output: OutputManager 인스턴스
        force: 기존 차트를 덮어쓰기
        dry_run: dry-run 모드 (실제 다운로드하지 않음)

    Returns:
        성공 여부

    """
    output.print(f"[cyan]📦 Preparing Helm app: {app_name}[/cyan]")

    # 로컬 차트는 prepare 불필요
    if not app.is_remote_chart():
        output.print_warning(f"Local chart detected, skipping prepare: {app.chart}")
        return True

    # Remote chart: pull 수행
    repo_name = app.get_repo_name()
    chart_name = app.get_chart_name()

    # sources.yaml에서 repo URL 찾기 (passed parameters take precedence)
    if helm_repos is not None:
        helm_sources = helm_repos
    elif not sources_file.exists():
        output.print_error(f"sources.yaml not found: {sources_file}")
        return False
    else:
        sources = load_config_file(sources_file)
        helm_sources = sources.get("helm_repos", {})

    if oci_registries is not None:
        oci_sources = oci_registries
    elif sources_file.exists():
        if 'sources' not in locals():
            sources = load_config_file(sources_file)
        oci_sources = sources.get("oci_registries", {})
    else:
        oci_sources = {}

    # OCI 레지스트리 체크 (우선순위)
    if repo_name in oci_sources:
        return prepare_oci_chart(
            app_name=app_name,
            app=app,
            charts_dir=charts_dir,
            oci_sources=oci_sources,
            repo_name=repo_name,
            chart_name=chart_name,
            output=output,
            kubeconfig=kubeconfig,
            context=context,
            force=force,
            dry_run=dry_run,
        )

    # 일반 Helm 레지스트리 체크
    if repo_name not in helm_sources:
        output.print_error(f"Helm repo '{repo_name}' not found in sources.yaml")
        output.print("[yellow]💡 Solutions:[/yellow]")
        output.print(
            f"   1. Check for typos in sources.yaml (e.g., '{repo_name}' → similar name?)"
        )
        output.print(
            f"   2. Search for '{chart_name}' chart: https://artifacthub.io/packages/search?ts_query_web={chart_name}"
        )
        output.print("   3. Add repository to sources.yaml:")
        output.print("      [cyan]helm_repos:[/cyan]")
        output.print(
            f"      [cyan]  {repo_name}: https://example.com/helm-charts[/cyan]"
        )
        output.print("   4. Or check if it's an OCI registry:")
        output.print("      [cyan]oci_registries:[/cyan]")
        output.print(
            f"      [cyan]  {repo_name}: oci://registry.example.com/charts[/cyan]"
        )
        return False

    # helm_repos는 dict 형태: {url: ..., username: ..., password: ...} 또는 단순 URL string
    repo_config = helm_sources[repo_name]
    if isinstance(repo_config, dict):
        repo_url = repo_config.get("url")
        if not repo_url:
            output.print_error(f"Missing 'url' for Helm repo: {repo_name}")
            return False
    else:
        # 구버전 호환: 단순 URL string
        repo_url = repo_config

    if dry_run:
        output.print(
            f"[yellow]🔍 [DRY-RUN] Would add Helm repo: {repo_name} ({repo_url})[/yellow]"
        )
        output.print(
            f"[yellow]🔍 [DRY-RUN] Would update Helm repo: {repo_name}[/yellow]"
        )
    else:
        # Helm repo 추가
        output.print(f"  Adding Helm repo: {repo_name} ({repo_url})")
        cmd = ["helm", "repo", "add", repo_name, repo_url]
        cmd = apply_cluster_config_to_command(cmd, kubeconfig, context)
        return_code, stdout, stderr = run_command(cmd)

        if return_code != 0:
            output.print_warning(f"Failed to add repo (might already exist): {stderr}")

        # Helm repo 업데이트
        output.print(f"  Updating Helm repo: {repo_name}")
        cmd = ["helm", "repo", "update", repo_name]
        cmd = apply_cluster_config_to_command(cmd, kubeconfig, context)
        return_code, stdout, stderr = run_command(cmd)

        if return_code != 0:
            output.print_error(f"Failed to update repo: {stderr}")
            return False

    # Chart pull (repo/chart-version 구조)
    chart_dir = app.get_chart_path(charts_dir)
    chart_yaml = chart_dir / "Chart.yaml"

    # Check if chart already exists (skip if not --force)
    if chart_yaml.exists() and not force:
        output.print_warning(f"Chart already exists, skipping: {chart_dir.name}")
        output.print("    Use --force to re-download")
        return True

    if dry_run:
        output.print(
            f"[yellow]🔍 [DRY-RUN] Would pull chart: {app.chart} → {chart_dir}[/yellow]"
        )
        if app.version:
            output.print(f"[yellow]🔍 [DRY-RUN] Chart version: {app.version}[/yellow]")
        if force:
            output.print(
                "[yellow]🔍 [DRY-RUN] Would remove existing chart (--force)[/yellow]"
            )
    else:
        # If force flag is set, remove existing chart directory
        if force and chart_dir.exists():
            output.print_warning(f"Removing existing chart (--force): {chart_dir}")
            shutil.rmtree(chart_dir)

        chart_dir.parent.mkdir(parents=True, exist_ok=True)

        output.print(f"  Pulling chart: {app.chart} → {chart_dir}")

        # Helm pull with temporary extraction, then move to versioned directory
        # Use UUID suffix to prevent concurrent execution conflicts
        temp_extract_dir = (
            chart_dir.parent / f"_temp_{chart_name}_{uuid.uuid4().hex[:8]}"
        )
        cmd = [
            "helm",
            "pull",
            f"{repo_name}/{chart_name}",
            "--untar",
            "--untardir",
            str(temp_extract_dir),
        ]

        if app.version:
            cmd.extend(["--version", app.version])

        cmd = apply_cluster_config_to_command(cmd, kubeconfig, context)
        return_code, _stdout, stderr = run_command(cmd)

        if return_code != 0:
            output.print_error(f"Failed to pull chart: {stderr}")
            output.print("[yellow]💡 Possible reasons:[/yellow]")
            output.print(
                f"   1. Chart '{chart_name}' does not exist in '{repo_name}' repository"
            )
            output.print("   2. Repository might be deprecated or moved")
            output.print("   3. Chart name might be different (check exact name)")
            output.print("[yellow]💡 Search for the chart:[/yellow]")
            output.print(
                f"   • Artifact Hub: https://artifacthub.io/packages/search?ts_query_web={chart_name}"
            )
            output.print(
                f"   • List charts in repo: [cyan]helm search repo {repo_name}/[/cyan]"
            )
            # Cleanup temp directory on failure
            if temp_extract_dir.exists():
                shutil.rmtree(temp_extract_dir)
            return False

        # Move extracted chart to versioned directory
        extracted_chart_path = temp_extract_dir / chart_name
        if not extracted_chart_path.exists():
            output.print_error(
                f"Chart extraction failed: expected {extracted_chart_path}"
            )
            if temp_extract_dir.exists():
                shutil.rmtree(temp_extract_dir)
            return False

        # Move to final destination
        extracted_chart_path.rename(chart_dir)

        # Cleanup temp directory
        if temp_extract_dir.exists():
            shutil.rmtree(temp_extract_dir)

    output.print_success(f"Helm app prepared: {app_name}")
    return True


def prepare_http_app(
    app_name: str,
    app: HttpApp,
    base_dir: Path,
    app_config_dir: Path,
    output: OutputManager,
    dry_run: bool = False,
) -> bool:
    """HTTP 앱 준비 (파일 다운로드).

    Args:
        app_name: 앱 이름
        app: HttpApp 설정
        base_dir: 프로젝트 루트
        app_config_dir: 앱 설정 디렉토리
        output: OutputManager 인스턴스
        dry_run: dry-run 모드 (실제 다운로드하지 않음)

    Returns:
        성공 여부

    """
    output.print(f"[cyan]📦 Preparing HTTP app: {app_name}[/cyan]")

    # 다운로드 대상 경로
    dest_path = app_config_dir / app.dest

    # 이미 존재하면 건너뛰기
    if dest_path.exists():
        output.print_warning(f"File already exists, skipping download: {dest_path}")
        return True

    if dry_run:
        output.print(
            f"[yellow]🔍 [DRY-RUN] Would download: {app.url} → {dest_path}[/yellow]"
        )
        if app.headers:
            output.print(f"[yellow]🔍 [DRY-RUN] Headers: {app.headers}[/yellow]")
    else:
        # 디렉토리 생성
        dest_path.parent.mkdir(parents=True, exist_ok=True)

        # HTTP 다운로드 (curl 사용)
        output.print(f"  Downloading: {app.url} → {dest_path}")
        cmd = ["curl", "-L", "-o", str(dest_path), app.url]

        # Headers 추가
        for key, value in app.headers.items():
            cmd.extend(["-H", f"{key}: {value}"])

        return_code, _stdout, stderr = run_command(cmd, timeout=300)

        if return_code != 0:
            output.print_error(f"Failed to download: {stderr}")
            # 실패 시 파일 삭제
            if dest_path.exists():
                dest_path.unlink()
            return False

    output.print_success(f"HTTP app prepared: {app_name}")
    return True


def prepare_git_app(
    app_name: str,
    app: GitApp,
    base_dir: Path,
    repos_dir: Path,
    sources_file: Path,
    output: OutputManager,
    force: bool = False,
    dry_run: bool = False,
    git_repos: dict | None = None,
) -> bool:
    """Git 앱 준비 (repo clone).

    Args:
        app_name: 앱 이름
        app: GitApp 설정
        base_dir: 프로젝트 루트
        repos_dir: repos 디렉토리
        sources_file: sources.yaml 파일 경로
        output: OutputManager 인스턴스
        force: 기존 리포지토리를 덮어쓰기
        dry_run: dry-run 모드 (실제 클론하지 않음)

    Returns:
        성공 여부

    """
    output.print(f"[cyan]📦 Preparing Git app: {app_name}[/cyan]")

    # sources.yaml에서 repo URL 찾기 (passed parameters take precedence)
    if git_repos is not None:
        git_sources = git_repos
    elif not sources_file.exists():
        output.print_error(f"sources.yaml not found: {sources_file}")
        return False
    else:
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
            output.print_error(f"Git repo '{app.repo}' not found in sources.yaml")
            return False
        repo_config = git_sources[app.repo]
        # repo_config는 dict 형태: {url: ..., branch: ...}
        if isinstance(repo_config, dict):
            repo_url = repo_config.get("url")
            if not repo_url:
                output.print_error(f"Missing 'url' for Git repo: {app.repo}")
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
        output.print_warning(f"Repository already exists, skipping: {repo_alias}")
        output.print("    Use --force to re-clone")
        return True

    if dry_run:
        output.print(
            f"[yellow]🔍 [DRY-RUN] Would clone: {repo_url} (branch: {branch}) → {dest_dir}[/yellow]"
        )
        if force and dest_dir.exists():
            output.print(
                "[yellow]🔍 [DRY-RUN] Would remove existing repository (--force)[/yellow]"
            )
    else:
        # If force flag is set, remove existing repository
        if force and dest_dir.exists():
            output.print_warning(f"Removing existing repository (--force): {dest_dir}")
            shutil.rmtree(dest_dir)

        dest_dir.mkdir(parents=True, exist_ok=True)

        # Git clone
        output.print(f"  Cloning: {repo_url} (branch: {branch}) → {dest_dir}")
        cmd = ["git", "clone", repo_url, str(dest_dir)]

        if branch:
            cmd.extend(["--branch", branch])

        return_code, _stdout, stderr = run_command(cmd)

        if return_code != 0:
            output.print_error(f"Failed to clone repository: {stderr}")
            return False

    output.print_success(f"Git app prepared: {app_name}")
    return True


@click.command(name="prepare")
@click.option(
    "--app-dir",
    "app_config_dir_name",
    default=None,
    help="앱 설정 디렉토리 (지정하지 않으면 모든 하위 디렉토리 자동 탐색)",
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
    app_config_dir_name: str | None,
    base_dir: str,
    config_file_name: str,
    sources_file_name: str,
    app_name: str | None,
    force: bool,
    dry_run: bool,
) -> None:
    """SBKube prepare 명령어.

    외부 리소스를 준비합니다:
    - helm 타입: Helm chart pull
    - git 타입: Git repository clone
    """
    # Initialize OutputManager
    output_format = ctx.obj.get("format", "human")
    output = OutputManager(format_type=output_format)

    output.print_section("SBKube `prepare` 시작")

    # Helm 설치 확인
    check_helm_installed_or_exit()

    # 경로 설정
    BASE_DIR = Path(base_dir).resolve()

    # 앱 그룹 디렉토리 결정 (공통 유틸리티 사용)
    try:
        app_config_dirs = resolve_app_dirs(
            BASE_DIR, app_config_dir_name, config_file_name
        )
    except ValueError:
        raise click.Abort

    # 각 앱 그룹 처리
    overall_success = True
    for APP_CONFIG_DIR in app_config_dirs:
        output.print(
            f"\n[bold cyan]━━━ Processing app group: {APP_CONFIG_DIR.name} ━━━[/bold cyan]"
        )

        config_file_path = APP_CONFIG_DIR / config_file_name

        # sources.yaml 찾기 (CLI --source 옵션 또는 --profile 우선)
        sources_file_name_resolved = ctx.obj.get("sources_file", sources_file_name)
        sources_file_path = find_sources_file(
            BASE_DIR, APP_CONFIG_DIR, sources_file_name_resolved
        )

        if not sources_file_path:
            output.print_error("sources.yaml not found in:")
            output.print(f"  - {APP_CONFIG_DIR / sources_file_name_resolved}")
            output.print(f"  - {APP_CONFIG_DIR.parent / sources_file_name_resolved}")
            output.print(f"  - {BASE_DIR / sources_file_name_resolved}")
            overall_success = False
            continue

        output.print(f"[cyan]📄 Using sources file: {sources_file_path}[/cyan]")

        # sources.yaml 로드 및 클러스터 설정 해석
        sources_data = load_config_file(sources_file_path)

        # 통합 sbkube.yaml 포맷 감지 (apiVersion이 sbkube/로 시작)
        api_version = sources_data.get("apiVersion", "")
        if api_version.startswith("sbkube/"):
            # 통합 포맷: settings 섹션에서 SourceScheme 필드만 추출
            full_settings = sources_data.get("settings", {})
            output.print(f"[cyan]📄 Unified format detected (apiVersion: {api_version})[/cyan]")

            # SourceScheme에서 허용하는 필드만 추출
            source_scheme_fields = {
                "cluster", "kubeconfig", "kubeconfig_context",
                "app_dirs", "cluster_values_file", "global_values",
                "cleanup_metadata", "incompatible_charts", "force_label_injection",
                "helm_repos", "oci_registries", "git_repos",
                "http_proxy", "https_proxy", "no_proxy",
            }

            # Get inherited settings from context (passed from parent workspace/phase)
            # No parent scanning - settings must be explicitly passed or defined locally
            inherited_settings = ctx.obj.get("inherited_settings", {})

            # Start with inherited settings
            merged_settings: dict = {}

            # Apply inherited helm_repos, oci_registries, git_repos
            if inherited_settings.get("helm_repos"):
                merged_settings["helm_repos"] = dict(inherited_settings["helm_repos"])
            if inherited_settings.get("oci_registries"):
                merged_settings["oci_registries"] = dict(inherited_settings["oci_registries"])
            if inherited_settings.get("git_repos"):
                merged_settings["git_repos"] = dict(inherited_settings["git_repos"])

            # Override with local settings (local takes precedence)
            for k, v in full_settings.items():
                if k in source_scheme_fields:
                    if k in ("helm_repos", "oci_registries", "git_repos") and k in merged_settings:
                        # Merge dict fields: inherited + local (local wins on conflict)
                        merged_settings[k].update(v)
                    else:
                        merged_settings[k] = v

            settings_data = merged_settings
        else:
            # 레거시 포맷: 전체 데이터가 SourceScheme
            settings_data = sources_data

        try:
            sources = SourceScheme(**settings_data)
        except Exception as e:
            output.print_error(f"Invalid sources file: {e}")
            overall_success = False
            continue

        # 클러스터 설정 해석
        try:
            kubeconfig, context = resolve_cluster_config(
                cli_kubeconfig=ctx.obj.get("kubeconfig"),
                cli_context=ctx.obj.get("context"),
                sources=sources,
            )
        except ClusterConfigError as e:
            output.print_error(str(e))
            overall_success = False
            continue

        # .sbkube 작업 디렉토리는 sources.yaml이 있는 위치 기준
        # (Phase 2 refactoring: SbkubeDirectories 사용)
        SOURCES_BASE_DIR = sources_file_path.parent
        sbkube_dirs = SbkubeDirectories(
            base_dir=BASE_DIR,
            sources_file=sources_file_path,
            sources_base_dir=SOURCES_BASE_DIR,
            sbkube_work_dir=SOURCES_BASE_DIR / ".sbkube",
            charts_dir=SOURCES_BASE_DIR / ".sbkube" / "charts",
            repos_dir=SOURCES_BASE_DIR / ".sbkube" / "repos",
            build_dir=SOURCES_BASE_DIR / ".sbkube" / "build",
            rendered_dir=SOURCES_BASE_DIR / ".sbkube" / "rendered",
        )
        CHARTS_DIR = sbkube_dirs.charts_dir
        REPOS_DIR = sbkube_dirs.repos_dir

        # 디렉토리 생성
        sbkube_dirs.ensure_directories()

        # 설정 파일 로드
        # 통합 포맷인 경우, 동일 파일에서 apps 로드
        if api_version.startswith("sbkube/"):
            apps_data = sources_data.get("apps", {})
            if not apps_data:
                output.print_warning(f"No apps found in: {sources_file_path}")
                continue

            # namespace 상속 처리 (parent → current)
            merged_namespace = "default"
            current_dir = sources_file_path.parent
            parent_configs = []
            for _ in range(5):
                parent_dir = current_dir.parent
                if parent_dir == current_dir:
                    break
                parent_config = parent_dir / "sbkube.yaml"
                if parent_config.exists():
                    parent_configs.append(parent_config)
                current_dir = parent_dir

            for parent_config in reversed(parent_configs):
                try:
                    parent_data = load_config_file(parent_config)
                    if parent_data.get("apiVersion", "").startswith("sbkube/"):
                        parent_ns = parent_data.get("settings", {}).get("namespace")
                        if parent_ns:
                            merged_namespace = parent_ns
                except Exception:
                    pass

            # 현재 config의 namespace로 오버라이드
            current_namespace = sources_data.get("settings", {}).get("namespace")
            if current_namespace:
                merged_namespace = current_namespace

            config_data = {"apps": apps_data, "namespace": merged_namespace}
            output.print(f"[cyan]📄 Loading apps from unified config: {sources_file_path}[/cyan]")
        else:
            # 레거시 포맷: 별도 config.yaml 로드
            if not config_file_path.exists():
                output.print_error(f"Config file not found: {config_file_path}")
                overall_success = False
                continue

            output.print(f"[cyan]📄 Loading config: {config_file_path}[/cyan]")
            config_data = load_config_file(config_file_path)

        try:
            config = SBKubeConfig(**config_data)
        except Exception as e:
            output.print_error(f"Invalid config file: {e}")
            overall_success = False
            continue

        # 배포 순서 얻기 (의존성 고려)
        deployment_order = config.get_deployment_order()

        if app_name:
            # 특정 앱만 준비
            if app_name not in config.apps:
                output.print_error(f"App not found: {app_name}")
                overall_success = False
                continue
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
                output.print_error("Pre-prepare hook failed")
                overall_success = False
                continue

        # 앱 준비
        success_count = 0
        total_count = len(apps_to_prepare)
        preparation_failed = False

        for app_name_iter in apps_to_prepare:
            app = config.apps[app_name_iter]

            if not app.enabled:
                output.print_warning(f"Skipping disabled app: {app_name_iter}")
                continue

            # ========== 앱별 pre-prepare 훅 실행 ==========
            if hasattr(app, "hooks") and app.hooks:
                app_hooks = app.hooks.model_dump()
                if not hook_executor.execute_app_hook(
                    app_name=app_name_iter,
                    app_hooks=app_hooks,
                    hook_type="pre_prepare",
                    context={},
                ):
                    output.print_error(
                        f"Pre-prepare hook failed for app: {app_name_iter}"
                    )
                    preparation_failed = True
                    continue

            success = False

            if isinstance(app, HookApp):
                # HookApp은 prepare 단계 불필요 (deploy 시에만 실행)
                output.print_warning(
                    f"HookApp does not require prepare: {app_name_iter}"
                )
                success = True
            elif isinstance(app, HelmApp):
                success = prepare_helm_app(
                    app_name_iter,
                    app,
                    BASE_DIR,
                    CHARTS_DIR,
                    sources_file_path,
                    output,
                    kubeconfig,
                    context,
                    force,
                    dry_run,
                    helm_repos=sources.helm_repos,
                    oci_registries=sources.oci_registries,
                )
            elif isinstance(app, GitApp):
                success = prepare_git_app(
                    app_name_iter,
                    app,
                    BASE_DIR,
                    REPOS_DIR,
                    sources_file_path,
                    output,
                    force,
                    dry_run,
                    git_repos=sources.git_repos,
                )
            elif isinstance(app, HttpApp):
                success = prepare_http_app(
                    app_name_iter, app, BASE_DIR, APP_CONFIG_DIR, output, dry_run
                )
            else:
                output.print_warning(
                    f"App type '{app.type}' does not require prepare: {app_name_iter}"
                )
                success = True  # 건너뛰어도 성공으로 간주

            # ========== 앱별 post-prepare 훅 실행 ==========
            if hasattr(app, "hooks") and app.hooks:
                app_hooks = app.hooks.model_dump()
                if success:
                    # 준비 성공 시 post_prepare 훅 실행
                    hook_executor.execute_app_hook(
                        app_name=app_name_iter,
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

        # 이 앱 그룹 결과 출력
        output.print_success(
            f"App group '{APP_CONFIG_DIR.name}' prepared: {success_count}/{total_count} apps"
        )

        if success_count < total_count:
            overall_success = False

    # 전체 결과
    if not overall_success:
        output.print_error("Some app groups failed to prepare")
        output.finalize()
        raise click.Abort
    output.print_success("All app groups prepared successfully!")
    output.finalize()
