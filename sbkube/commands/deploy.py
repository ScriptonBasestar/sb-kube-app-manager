"""
SBKube deploy 명령어.

새로운 기능:
- helm 타입: Helm install/upgrade
- yaml 타입: kubectl apply
- action 타입: 커스텀 액션 (apply/create/delete)
- exec 타입: 커스텀 명령어 실행
- kustomize 타입: kubectl apply -k
"""

from pathlib import Path

import click
from rich.console import Console

from sbkube.models.config_model import (
    ActionApp,
    ExecApp,
    HelmApp,
    KustomizeApp,
    SBKubeConfig,
    YamlApp,
)
from sbkube.utils.cli_check import check_helm_installed_or_exit, check_kubectl_installed_or_exit
from sbkube.utils.common import run_command
from sbkube.utils.file_loader import load_config_file

console = Console()


def deploy_helm_app(
    app_name: str,
    app: HelmApp,
    base_dir: Path,
    charts_dir: Path,
    build_dir: Path,
    app_config_dir: Path,
    dry_run: bool = False,
) -> bool:
    """
    Helm 앱 배포 (install/upgrade).

    Args:
        app_name: 앱 이름
        app: HelmApp 설정
        base_dir: 프로젝트 루트
        charts_dir: charts 디렉토리
        build_dir: build 디렉토리
        app_config_dir: 앱 설정 디렉토리
        dry_run: dry-run 모드

    Returns:
        성공 여부
    """
    console.print(f"[cyan]🚀 Deploying Helm app: {app_name}[/cyan]")

    release_name = app.release_name or app_name
    namespace = app.namespace

    # Chart 경로 결정 (build/ 우선, 없으면 charts/ 또는 로컬)
    chart_path = None

    # 1. build/ 디렉토리 확인 (overrides/removes 적용된 차트)
    build_path = build_dir / app_name
    if build_path.exists() and build_path.is_dir():
        chart_path = build_path
        console.print(f"  Using built chart: {chart_path}")
    else:
        # 2. build 없으면 원본 차트 사용
        if app.is_remote_chart():
            # Remote chart: charts/ 디렉토리에서 찾기
            chart_name = app.get_chart_name()
            source_path = charts_dir / chart_name / chart_name  # charts/redis/redis

            if not source_path.exists():
                console.print(f"[red]❌ Chart not found: {source_path}[/red]")
                console.print(f"[yellow]💡 Run 'sbkube prepare' first[/yellow]")
                return False
            chart_path = source_path
        else:
            # Local chart: 상대 경로 또는 절대 경로
            if app.chart.startswith("./"):
                # 상대 경로: app_config_dir 기준
                source_path = app_config_dir / app.chart[2:]  # "./" 제거
            elif app.chart.startswith("/"):
                # 절대 경로
                source_path = Path(app.chart)
            else:
                # 그냥 chart 이름만 있는 경우: app_config_dir 기준
                source_path = app_config_dir / app.chart

            if not source_path.exists():
                console.print(f"[red]❌ Local chart not found: {source_path}[/red]")
                return False

            chart_path = source_path
            console.print(f"  Using local chart: {chart_path}")

    # Helm install/upgrade 명령어
    cmd = ["helm", "upgrade", release_name, str(chart_path), "--install"]

    if namespace:
        cmd.extend(["--namespace", namespace])

    if app.create_namespace:
        cmd.append("--create-namespace")

    if app.wait:
        cmd.append("--wait")

    if app.timeout:
        cmd.extend(["--timeout", app.timeout])

    if app.atomic:
        cmd.append("--atomic")

    # Values 파일
    for values_file in app.values:
        values_path = app_config_dir / values_file
        if not values_path.exists():
            console.print(f"[yellow]⚠️ Values file not found: {values_path}[/yellow]")
        else:
            cmd.extend(["--values", str(values_path)])

    # --set 옵션
    for key, value in app.set_values.items():
        cmd.extend(["--set", f"{key}={value}"])

    if dry_run:
        cmd.append("--dry-run")
        console.print(f"[yellow]🔍 Dry-run mode enabled[/yellow]")

    # 명령어 출력
    console.print(f"  Command: {' '.join(cmd)}")

    # 실행
    return_code, stdout, stderr = run_command(cmd, timeout=300)

    if return_code != 0:
        console.print(f"[red]❌ Failed to deploy: {stderr}[/red]")
        return False

    console.print(f"[green]✅ Helm app deployed: {app_name} (release: {release_name})[/green]")
    return True


def deploy_yaml_app(
    app_name: str,
    app: YamlApp,
    base_dir: Path,
    app_config_dir: Path,
    dry_run: bool = False,
) -> bool:
    """
    YAML 앱 배포 (kubectl apply).

    Args:
        app_name: 앱 이름
        app: YamlApp 설정
        base_dir: 프로젝트 루트
        app_config_dir: 앱 설정 디렉토리
        dry_run: dry-run 모드

    Returns:
        성공 여부
    """
    console.print(f"[cyan]🚀 Deploying YAML app: {app_name}[/cyan]")

    namespace = app.namespace

    for yaml_file in app.files:
        yaml_path = app_config_dir / yaml_file

        if not yaml_path.exists():
            console.print(f"[red]❌ YAML file not found: {yaml_path}[/red]")
            return False

        cmd = ["kubectl", "apply", "-f", str(yaml_path)]

        if namespace:
            cmd.extend(["--namespace", namespace])

        if dry_run:
            cmd.append("--dry-run=client")

        console.print(f"  Applying: {yaml_file}")
        return_code, stdout, stderr = run_command(cmd)

        if return_code != 0:
            console.print(f"[red]❌ Failed to apply: {stderr}[/red]")
            return False

    console.print(f"[green]✅ YAML app deployed: {app_name}[/green]")
    return True


def deploy_action_app(
    app_name: str,
    app: ActionApp,
    base_dir: Path,
    app_config_dir: Path,
    dry_run: bool = False,
) -> bool:
    """
    Action 앱 배포 (커스텀 액션).

    Args:
        app_name: 앱 이름
        app: ActionApp 설정
        base_dir: 프로젝트 루트
        app_config_dir: 앱 설정 디렉토리
        dry_run: dry-run 모드

    Returns:
        성공 여부
    """
    console.print(f"[cyan]🚀 Deploying Action app: {app_name}[/cyan]")

    namespace = app.namespace

    for action in app.actions:
        action_type = action.get("type", "apply")
        action_path = action.get("path")
        action_namespace = action.get("namespace", namespace)

        if not action_path:
            console.print(f"[red]❌ Action path not specified[/red]")
            return False

        # 경로 해석 (URL 또는 로컬 파일)
        if action_path.startswith("http://") or action_path.startswith("https://"):
            file_path = action_path
        else:
            file_path = str(app_config_dir / action_path)

        cmd = ["kubectl", action_type, "-f", file_path]

        if action_namespace:
            cmd.extend(["--namespace", action_namespace])

        if dry_run:
            cmd.append("--dry-run=client")

        console.print(f"  {action_type.capitalize()}: {action_path}")
        return_code, stdout, stderr = run_command(cmd)

        if return_code != 0:
            console.print(f"[red]❌ Failed to {action_type}: {stderr}[/red]")
            return False

    console.print(f"[green]✅ Action app deployed: {app_name}[/green]")
    return True


def deploy_exec_app(
    app_name: str,
    app: ExecApp,
    base_dir: Path,
    dry_run: bool = False,
) -> bool:
    """
    Exec 앱 실행 (커스텀 명령어).

    Args:
        app_name: 앱 이름
        app: ExecApp 설정
        base_dir: 프로젝트 루트
        dry_run: dry-run 모드

    Returns:
        성공 여부
    """
    console.print(f"[cyan]🚀 Executing commands: {app_name}[/cyan]")

    for command in app.commands:
        if dry_run:
            console.print(f"  [DRY-RUN] {command}")
            continue

        console.print(f"  Running: {command}")
        return_code, stdout, stderr = run_command(command, shell=True, timeout=60)

        if return_code != 0:
            console.print(f"[red]❌ Command failed: {stderr}[/red]")
            return False

        if stdout:
            console.print(f"  Output: {stdout.strip()}")

    console.print(f"[green]✅ Commands executed: {app_name}[/green]")
    return True


def deploy_kustomize_app(
    app_name: str,
    app: KustomizeApp,
    base_dir: Path,
    app_config_dir: Path,
    dry_run: bool = False,
) -> bool:
    """
    Kustomize 앱 배포 (kubectl apply -k).

    Args:
        app_name: 앱 이름
        app: KustomizeApp 설정
        base_dir: 프로젝트 루트
        app_config_dir: 앱 설정 디렉토리
        dry_run: dry-run 모드

    Returns:
        성공 여부
    """
    console.print(f"[cyan]🚀 Deploying Kustomize app: {app_name}[/cyan]")

    kustomize_path = app_config_dir / app.path
    namespace = app.namespace

    if not kustomize_path.exists():
        console.print(f"[red]❌ Kustomize path not found: {kustomize_path}[/red]")
        return False

    cmd = ["kubectl", "apply", "-k", str(kustomize_path)]

    if namespace:
        cmd.extend(["--namespace", namespace])

    if dry_run:
        cmd.append("--dry-run=client")

    console.print(f"  Applying: {kustomize_path}")
    return_code, stdout, stderr = run_command(cmd)

    if return_code != 0:
        console.print(f"[red]❌ Failed to apply: {stderr}[/red]")
        return False

    console.print(f"[green]✅ Kustomize app deployed: {app_name}[/green]")
    return True


@click.command(name="deploy")
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
    help="배포할 특정 앱 이름 (지정하지 않으면 모든 앱 배포)",
)
@click.option(
    "--dry-run",
    is_flag=True,
    default=False,
    help="Dry-run 모드 (실제 배포하지 않음)",
)
def cmd(
    app_config_dir_name: str,
    base_dir: str,
    config_file_name: str,
    app_name: str | None,
    dry_run: bool,
):
    """
    SBKube deploy 명령어.

    애플리케이션을 Kubernetes 클러스터에 배포합니다:
    - helm 타입: Helm install/upgrade
    - yaml 타입: kubectl apply
    - action 타입: 커스텀 액션
    - exec 타입: 커스텀 명령어
    - kustomize 타입: kubectl apply -k
    """
    console.print("[bold blue]✨ SBKube `deploy` 시작 ✨[/bold blue]")

    # kubectl 설치 확인
    check_kubectl_installed_or_exit()

    # 경로 설정
    BASE_DIR = Path(base_dir).resolve()
    APP_CONFIG_DIR = BASE_DIR / app_config_dir_name
    config_file_path = APP_CONFIG_DIR / config_file_name

    CHARTS_DIR = BASE_DIR / "charts"
    BUILD_DIR = BASE_DIR / "build"

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
        # 특정 앱만 배포
        if app_name not in config.apps:
            console.print(f"[red]❌ App not found: {app_name}[/red]")
            raise click.Abort()
        apps_to_deploy = [app_name]
    else:
        # 모든 앱 배포 (의존성 순서대로)
        apps_to_deploy = deployment_order

    # 앱 배포
    success_count = 0
    total_count = len(apps_to_deploy)

    for app_name in apps_to_deploy:
        app = config.apps[app_name]

        if not app.enabled:
            console.print(f"[yellow]⏭️  Skipping disabled app: {app_name}[/yellow]")
            continue

        success = False

        if isinstance(app, HelmApp):
            check_helm_installed_or_exit()
            success = deploy_helm_app(app_name, app, BASE_DIR, CHARTS_DIR, BUILD_DIR, APP_CONFIG_DIR, dry_run)
        elif isinstance(app, YamlApp):
            success = deploy_yaml_app(app_name, app, BASE_DIR, APP_CONFIG_DIR, dry_run)
        elif isinstance(app, ActionApp):
            success = deploy_action_app(app_name, app, BASE_DIR, APP_CONFIG_DIR, dry_run)
        elif isinstance(app, ExecApp):
            success = deploy_exec_app(app_name, app, BASE_DIR, dry_run)
        elif isinstance(app, KustomizeApp):
            success = deploy_kustomize_app(app_name, app, BASE_DIR, APP_CONFIG_DIR, dry_run)
        else:
            console.print(f"[yellow]⏭️  Unsupported app type '{app.type}': {app_name}[/yellow]")
            continue

        if success:
            success_count += 1

    # 결과 출력
    console.print(f"\n[bold green]✅ Deploy completed: {success_count}/{total_count} apps[/bold green]")

    if success_count < total_count:
        raise click.Abort()
