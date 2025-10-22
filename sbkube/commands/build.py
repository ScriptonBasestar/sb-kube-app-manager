"""
SBKube v0.3.0 build 명령어.

빌드 디렉토리 준비 + 커스터마이징:
- Remote chart: charts/ → build/ 복사
- Local chart: app_dir 기준 경로 → build/ 복사
- Overrides 적용: overrides/<app-name>/* → build/<app-name>/*
- Removes 적용: build/<app-name>/<remove-pattern> 삭제
"""

import shutil
from pathlib import Path

import click
from rich.console import Console

from sbkube.models.config_model import HelmApp, HttpApp, SBKubeConfig
from sbkube.utils.file_loader import load_config_file

console = Console()


def build_helm_app(
    app_name: str,
    app: HelmApp,
    base_dir: Path,
    charts_dir: Path,
    build_dir: Path,
    app_config_dir: Path,
) -> bool:
    """
    Helm 앱 빌드 + 커스터마이징.

    Args:
        app_name: 앱 이름
        app: HelmApp 설정
        base_dir: 프로젝트 루트
        charts_dir: charts 디렉토리
        build_dir: build 디렉토리
        app_config_dir: 앱 설정 디렉토리

    Returns:
        성공 여부
    """
    console.print(f"[cyan]🔨 Building Helm app: {app_name}[/cyan]")

    # 1. 소스 차트 경로 결정
    if app.is_remote_chart():
        # Remote chart: charts/<chart-name>/<chart-name>/
        chart_name = app.get_chart_name()
        source_path = charts_dir / chart_name / chart_name

        if not source_path.exists():
            console.print(f"[red]❌ Remote chart not found: {source_path}[/red]")
            console.print(f"[yellow]💡 Run 'sbkube prepare' first[/yellow]")
            return False
    else:
        # Local chart: app_config_dir 기준
        if app.chart.startswith("./"):
            source_path = app_config_dir / app.chart[2:]
        elif app.chart.startswith("/"):
            source_path = Path(app.chart)
        else:
            source_path = app_config_dir / app.chart

        if not source_path.exists():
            console.print(f"[red]❌ Local chart not found: {source_path}[/red]")
            return False

    # 2. 빌드 디렉토리로 복사
    dest_path = build_dir / app_name

    # 기존 디렉토리 삭제
    if dest_path.exists():
        console.print(f"  Removing existing build directory: {dest_path}")
        shutil.rmtree(dest_path)

    console.print(f"  Copying chart: {source_path} → {dest_path}")
    shutil.copytree(source_path, dest_path)

    # 3. Overrides 적용
    if app.overrides:
        console.print(f"  Applying {len(app.overrides)} overrides...")
        overrides_base = app_config_dir / "overrides" / app_name

        if not overrides_base.exists():
            console.print(f"[yellow]⚠️ Overrides directory not found: {overrides_base}[/yellow]")
        else:
            for override_rel_path in app.overrides:
                src_file = overrides_base / override_rel_path
                dst_file = dest_path / override_rel_path

                if src_file.exists() and src_file.is_file():
                    # 대상 디렉토리 생성
                    dst_file.parent.mkdir(parents=True, exist_ok=True)
                    shutil.copy2(src_file, dst_file)
                    console.print(f"    ✓ Override: {override_rel_path}")
                else:
                    console.print(f"[yellow]    ⚠️ Override file not found: {src_file}[/yellow]")

    # 4. Removes 적용
    if app.removes:
        console.print(f"  Removing {len(app.removes)} patterns...")
        for remove_pattern in app.removes:
            remove_target = dest_path / remove_pattern

            if remove_target.exists():
                if remove_target.is_dir():
                    shutil.rmtree(remove_target)
                    console.print(f"    ✓ Removed directory: {remove_pattern}")
                elif remove_target.is_file():
                    remove_target.unlink()
                    console.print(f"    ✓ Removed file: {remove_pattern}")
            else:
                console.print(f"[yellow]    ⚠️ Remove target not found: {remove_pattern}[/yellow]")

    console.print(f"[green]✅ Helm app built: {app_name}[/green]")
    return True


def build_http_app(
    app_name: str,
    app: HttpApp,
    base_dir: Path,
    build_dir: Path,
    app_config_dir: Path,
) -> bool:
    """
    HTTP 앱 빌드 (다운로드된 파일을 build/로 복사).

    Args:
        app_name: 앱 이름
        app: HttpApp 설정
        base_dir: 프로젝트 루트
        build_dir: build 디렉토리
        app_config_dir: 앱 설정 디렉토리

    Returns:
        성공 여부
    """
    console.print(f"[cyan]🔨 Building HTTP app: {app_name}[/cyan]")

    # 다운로드된 파일 위치 (prepare 단계에서 생성됨)
    source_file = app_config_dir / app.dest

    if not source_file.exists():
        console.print(f"[red]❌ Downloaded file not found: {source_file}[/red]")
        console.print(f"[yellow]💡 Run 'sbkube prepare' first[/yellow]")
        return False

    # build/ 디렉토리로 복사
    dest_file = build_dir / app_name / source_file.name
    dest_file.parent.mkdir(parents=True, exist_ok=True)

    console.print(f"  Copying: {source_file} → {dest_file}")
    shutil.copy2(source_file, dest_file)

    console.print(f"[green]✅ HTTP app built: {app_name}[/green]")
    return True


@click.command(name="build")
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
    "--app",
    "app_name",
    default=None,
    help="빌드할 특정 앱 이름 (지정하지 않으면 모든 앱 빌드)",
)
def cmd(
    app_config_dir_name: str,
    base_dir: str,
    config_file_name: str,
    app_name: str | None,
):
    """
    SBKube v0.3.0 build 명령어.

    빌드 디렉토리 준비 및 커스터마이징:
    - Remote chart를 charts/에서 build/로 복사
    - Overrides 적용 (overrides/<app-name>/* → build/<app-name>/*)
    - Removes 적용 (불필요한 파일/디렉토리 삭제)
    """
    console.print("[bold blue]✨ SBKube v0.3.0 `build` 시작 ✨[/bold blue]")

    # 경로 설정
    BASE_DIR = Path(base_dir).resolve()
    APP_CONFIG_DIR = BASE_DIR / app_config_dir_name
    config_file_path = APP_CONFIG_DIR / config_file_name

    CHARTS_DIR = BASE_DIR / "charts"
    BUILD_DIR = BASE_DIR / "build"

    # build 디렉토리 생성
    BUILD_DIR.mkdir(parents=True, exist_ok=True)

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
        # 특정 앱만 빌드
        if app_name not in config.apps:
            console.print(f"[red]❌ App not found: {app_name}[/red]")
            raise click.Abort()
        apps_to_build = [app_name]
    else:
        # 모든 앱 빌드 (의존성 순서대로)
        apps_to_build = deployment_order

    # 앱 빌드
    success_count = 0
    total_count = len(apps_to_build)

    for app_name in apps_to_build:
        app = config.apps[app_name]

        if not app.enabled:
            console.print(f"[yellow]⏭️  Skipping disabled app: {app_name}[/yellow]")
            continue

        success = False

        if isinstance(app, HelmApp):
            # Helm 앱만 빌드 (커스터마이징 필요)
            if app.overrides or app.removes or app.is_remote_chart():
                success = build_helm_app(app_name, app, BASE_DIR, CHARTS_DIR, BUILD_DIR, APP_CONFIG_DIR)
            else:
                console.print(f"[yellow]⏭️  Skipping Helm app (no customization): {app_name}[/yellow]")
                success = True  # 건너뛰어도 성공으로 간주
        elif isinstance(app, HttpApp):
            success = build_http_app(app_name, app, BASE_DIR, BUILD_DIR, APP_CONFIG_DIR)
        else:
            console.print(f"[yellow]⏭️  App type '{app.type}' does not require build: {app_name}[/yellow]")
            success = True  # 건너뛰어도 성공으로 간주

        if success:
            success_count += 1

    # 결과 출력
    console.print(f"\n[bold green]✅ Build completed: {success_count}/{total_count} apps[/bold green]")

    if success_count < total_count:
        raise click.Abort()
