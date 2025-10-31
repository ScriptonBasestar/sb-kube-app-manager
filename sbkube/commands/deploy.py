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

from sbkube.exceptions import KubernetesConnectionError
from sbkube.models.config_model import (
    ActionApp,
    ExecApp,
    HelmApp,
    KustomizeApp,
    NoopApp,
    SBKubeConfig,
    YamlApp,
)
from sbkube.utils.app_labels import (
    build_helm_set_annotations,
    build_helm_set_labels,
    build_sbkube_annotations,
    build_sbkube_labels,
    extract_app_group_from_name,
)
from sbkube.utils.cli_check import (
    check_cluster_connectivity_or_exit,
    check_helm_installed_or_exit,
    check_kubectl_installed_or_exit,
)
from sbkube.utils.cluster_config import (
    ClusterConfigError,
    apply_cluster_config_to_command,
    resolve_cluster_config,
)
from sbkube.utils.common import find_all_app_dirs, find_sources_file, run_command
from sbkube.utils.hook_executor import HookExecutor

console = Console()


_CONNECTION_ERROR_KEYWORDS: tuple[str, ...] = (
    "connection refused",
    "kubernetes cluster unreachable",
    "unable to connect to the server",
    "the connection to the server",
    "context deadline exceeded",
    "i/o timeout",
    "no such host",
    "name or service not known",
    "connection timed out",
    "timeout expired",
)


def _get_connection_error_reason(stdout: str, stderr: str) -> str | None:
    """
    Detects common Kubernetes connection error patterns in command output.

    Args:
        stdout: 표준 출력
        stderr: 표준 에러

    Returns:
        감지된 경우 오류 메시지, 없으면 None
    """
    combined = f"{stdout}\n{stderr}".lower()
    for keyword in _CONNECTION_ERROR_KEYWORDS:
        if keyword in combined:
            message = stderr.strip() or stdout.strip()
            return message or keyword
    return None


def deploy_helm_app(
    app_name: str,
    app: HelmApp,
    base_dir: Path,
    charts_dir: Path,
    build_dir: Path,
    app_config_dir: Path,
    kubeconfig: str | None = None,
    context: str | None = None,
    dry_run: bool = False,
    deployment_id: str | None = None,
    operator: str | None = None,
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
        kubeconfig: kubeconfig 파일 경로
        context: kubectl context 이름
        dry_run: dry-run 모드
        deployment_id: 배포 ID (Phase 2)
        operator: 배포자 이름 (Phase 2)

    Returns:
        성공 여부
    """
    console.print(f"[cyan]🚀 Deploying Helm app: {app_name}[/cyan]")

    release_name = app.release_name or app_name
    namespace = app.namespace

    # Chart 경로 결정 (.sbkube/build/ 우선, 없으면 .sbkube/charts/ 또는 로컬)
    chart_path = None

    # 1. .sbkube/build/ 디렉토리 확인 (overrides/removes 적용된 차트)
    build_path = build_dir / app_name
    if build_path.exists() and build_path.is_dir():
        chart_path = build_path
        console.print(f"  Using built chart: {chart_path}")
    else:
        # 2. build 없으면 원본 차트 사용
        if app.is_remote_chart():
            # Remote chart: .sbkube/charts/ 디렉토리에서 찾기
            chart_name = app.get_chart_name()
            source_path = charts_dir / chart_name / chart_name  # .sbkube/charts/redis/redis

            if not source_path.exists():
                console.print(f"[red]❌ Chart not found: {source_path}[/red]")
                console.print("[yellow]💡 Run 'sbkube prepare' first[/yellow]")
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
        # Ensure namespace exists unless helm will create it
        namespace_missing = False
        check_cmd = ["kubectl", "get", "namespace", namespace]
        check_cmd = apply_cluster_config_to_command(check_cmd, kubeconfig, context)
        check_return_code, _, _ = run_command(check_cmd)

        if check_return_code != 0:
            namespace_missing = True

        if namespace_missing and not app.create_namespace:
            if dry_run:
                console.print(
                    f"[yellow]⚠️ Namespace '{namespace}' is missing (dry-run: skipping creation)[/yellow]"
                )
            else:
                console.print(
                    f"[yellow]ℹ️  Namespace '{namespace}' not found. Creating...[/yellow]"
                )
                create_cmd = ["kubectl", "create", "namespace", namespace]
                create_cmd = apply_cluster_config_to_command(
                    create_cmd, kubeconfig, context
                )
                create_return_code, _, create_stderr = run_command(create_cmd)
                if create_return_code != 0:
                    console.print(
                        f"[red]❌ Failed to create namespace '{namespace}': {create_stderr}[/red]"
                    )
                    return False

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

    # Phase 2: Inject sbkube labels and annotations
    # Extract app-group from app_config_dir path
    app_group = extract_app_group_from_name(app_config_dir.name)
    if not app_group:
        # Try parent directory (for nested apps)
        app_group = extract_app_group_from_name(app_config_dir.parent.name)

    if app_group:
        # Build labels
        labels = build_sbkube_labels(
            app_name=app_name,
            app_group=app_group,
            deployment_id=deployment_id,
        )
        label_args = build_helm_set_labels(labels)
        cmd.extend(label_args)
        console.print(f"  [dim]Injecting labels: app-group={app_group}[/dim]")

        # Build annotations
        annotations = build_sbkube_annotations(
            deployment_id=deployment_id,
            operator=operator,
        )
        annotation_args = build_helm_set_annotations(annotations)
        cmd.extend(annotation_args)
    else:
        console.print(
            f"  [yellow]⚠️ Could not detect app-group from path: {app_config_dir}[/yellow]"
        )
        console.print(
            "  [dim]Labels will not be injected (use app_XXX_category naming)[/dim]"
        )

    if dry_run:
        cmd.append("--dry-run")
        console.print("[yellow]🔍 Dry-run mode enabled[/yellow]")

    # Apply cluster configuration
    cmd = apply_cluster_config_to_command(cmd, kubeconfig, context)

    # 명령어 출력
    console.print(f"  Command: {' '.join(cmd)}")

    # 실행
    return_code, stdout, stderr = run_command(cmd, timeout=300)

    if return_code != 0:
        reason = _get_connection_error_reason(stdout, stderr)
        if reason:
            raise KubernetesConnectionError(reason=reason)
        console.print(f"[red]❌ Failed to deploy: {stderr}[/red]")
        return False

    console.print(
        f"[green]✅ Helm app deployed: {app_name} (release: {release_name})[/green]"
    )
    return True


def deploy_yaml_app(
    app_name: str,
    app: YamlApp,
    base_dir: Path,
    app_config_dir: Path,
    kubeconfig: str | None = None,
    context: str | None = None,
    dry_run: bool = False,
) -> bool:
    """
    YAML 앱 배포 (kubectl apply).

    Args:
        app_name: 앱 이름
        app: YamlApp 설정
        base_dir: 프로젝트 루트
        app_config_dir: 앱 설정 디렉토리
        kubeconfig: kubeconfig 파일 경로
        context: kubectl context 이름
        dry_run: dry-run 모드

    Returns:
        성공 여부
    """
    console.print(f"[cyan]🚀 Deploying YAML app: {app_name}[/cyan]")

    namespace = app.namespace

    for yaml_file in app.manifests:
        yaml_path = app_config_dir / yaml_file

        if not yaml_path.exists():
            console.print(f"[red]❌ YAML file not found: {yaml_path}[/red]")
            return False

        cmd = ["kubectl", "apply", "-f", str(yaml_path)]

        if namespace:
            cmd.extend(["--namespace", namespace])

        if dry_run:
            cmd.append("--dry-run=client")
            cmd.append("--validate=false")

        # Apply cluster configuration
        cmd = apply_cluster_config_to_command(cmd, kubeconfig, context)

        console.print(f"  Applying: {yaml_file}")
        return_code, stdout, stderr = run_command(cmd)

        if return_code != 0:
            reason = _get_connection_error_reason(stdout, stderr)
            if reason:
                raise KubernetesConnectionError(reason=reason)
            console.print(f"[red]❌ Failed to apply: {stderr}[/red]")
            return False

    console.print(f"[green]✅ YAML app deployed: {app_name}[/green]")
    return True


def deploy_action_app(
    app_name: str,
    app: ActionApp,
    base_dir: Path,
    app_config_dir: Path,
    kubeconfig: str | None = None,
    context: str | None = None,
    dry_run: bool = False,
) -> bool:
    """
    Action 앱 배포 (커스텀 액션).

    Args:
        app_name: 앱 이름
        app: ActionApp 설정
        base_dir: 프로젝트 루트
        app_config_dir: 앱 설정 디렉토리
        kubeconfig: kubeconfig 파일 경로
        context: kubectl context 이름
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
            console.print("[red]❌ Action path not specified[/red]")
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
            cmd.append("--validate=false")

        # Apply cluster configuration
        cmd = apply_cluster_config_to_command(cmd, kubeconfig, context)

        console.print(f"  {action_type.capitalize()}: {action_path}")
        return_code, stdout, stderr = run_command(cmd)

        if return_code != 0:
            reason = _get_connection_error_reason(stdout, stderr)
            if reason:
                raise KubernetesConnectionError(reason=reason)
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
        return_code, stdout, stderr = run_command(command, timeout=60)

        if return_code != 0:
            reason = _get_connection_error_reason(stdout, stderr)
            if reason:
                raise KubernetesConnectionError(reason=reason)
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
    kubeconfig: str | None = None,
    context: str | None = None,
    dry_run: bool = False,
) -> bool:
    """
    Kustomize 앱 배포 (kubectl apply -k).

    Args:
        app_name: 앱 이름
        app: KustomizeApp 설정
        base_dir: 프로젝트 루트
        app_config_dir: 앱 설정 디렉토리
        kubeconfig: kubeconfig 파일 경로
        context: kubectl context 이름
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
        cmd.append("--validate=false")

    # Apply cluster configuration
    cmd = apply_cluster_config_to_command(cmd, kubeconfig, context)

    console.print(f"  Applying: {kustomize_path}")
    return_code, stdout, stderr = run_command(cmd)

    if return_code != 0:
        reason = _get_connection_error_reason(stdout, stderr)
        if reason:
            raise KubernetesConnectionError(reason=reason)
        console.print(f"[red]❌ Failed to apply: {stderr}[/red]")
        return False

    console.print(f"[green]✅ Kustomize app deployed: {app_name}[/green]")
    return True


def deploy_noop_app(
    app_name: str,
    app: NoopApp,
    base_dir: Path,
    app_config_dir: Path,
    dry_run: bool = False,
) -> bool:
    """
    Noop 앱 배포 (실제로는 아무것도 하지 않음).

    Args:
        app_name: 앱 이름
        app: NoopApp 설정
        base_dir: 프로젝트 루트
        app_config_dir: 앱 설정 디렉토리
        dry_run: dry-run 모드

    Returns:
        항상 True (성공)
    """
    console.print(f"[cyan]🚀 Processing Noop app: {app_name}[/cyan]")

    if app.description:
        console.print(f"  Description: {app.description}")

    if dry_run:
        console.print("  [yellow]Dry-run mode: No actual deployment[/yellow]")

    console.print(f"[green]✅ Noop app processed: {app_name} (no-op)[/green]")
    return True


@click.command(name="deploy")
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
@click.pass_context
def cmd(
    ctx: click.Context,
    app_config_dir_name: str | None,
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
    check_cluster_connectivity_or_exit()

    # 경로 설정
    BASE_DIR = Path(base_dir).resolve()

    SBKUBE_WORK_DIR = BASE_DIR / ".sbkube"
    CHARTS_DIR = SBKUBE_WORK_DIR / "charts"
    BUILD_DIR = SBKUBE_WORK_DIR / "build"

    # sources.yaml 로드 (app_dirs 확인용)
    sources_file_path = BASE_DIR / "sources.yaml"
    sources_config = None
    if sources_file_path.exists():
        from sbkube.models.sources_model import SourceScheme
        from sbkube.utils.file_loader import load_config_file
        try:
            sources_data = load_config_file(sources_file_path)
            sources_config = SourceScheme(**sources_data)
        except Exception as e:
            console.print(f"[yellow]⚠️  Warning: Could not load sources.yaml: {e}[/yellow]")

    # 앱 그룹 디렉토리 결정
    if app_config_dir_name:
        # 특정 디렉토리 지정 (--app-dir 옵션)
        app_config_dirs = [BASE_DIR / app_config_dir_name]
    elif sources_config and sources_config.app_dirs is not None:
        # sources.yaml에 명시적 app_dirs 목록이 있는 경우
        try:
            app_config_dirs = sources_config.get_app_dirs(BASE_DIR, config_file_name)
            console.print(f"[cyan]📂 Using app_dirs from sources.yaml ({len(app_config_dirs)} group(s)):[/cyan]")
            for app_dir in app_config_dirs:
                console.print(f"  - {app_dir.name}/")
        except ValueError as e:
            console.print(f"[red]❌ {e}[/red]")
            raise click.Abort()
    else:
        # 자동 탐색 (기존 동작)
        app_config_dirs = find_all_app_dirs(BASE_DIR, config_file_name)
        if not app_config_dirs:
            console.print(f"[red]❌ No app directories found in: {BASE_DIR}[/red]")
            console.print("[yellow]💡 Tip: Create directories with config.yaml or use --app-dir[/yellow]")
            raise click.Abort()

        console.print(f"[cyan]📂 Found {len(app_config_dirs)} app group(s) (auto-discovery):[/cyan]")
        for app_dir in app_config_dirs:
            console.print(f"  - {app_dir.name}/")

    # 각 앱 그룹 처리
    overall_success = True
    for APP_CONFIG_DIR in app_config_dirs:
        console.print(f"\n[bold cyan]━━━ Processing app group: {APP_CONFIG_DIR.name} ━━━[/bold cyan]")

        config_file_path = APP_CONFIG_DIR / config_file_name

        # Load sources and resolve cluster configuration
        sources_file_name = ctx.obj.get("sources_file", "sources.yaml")
        sources_file_path = find_sources_file(BASE_DIR, APP_CONFIG_DIR, sources_file_name)

        sources = None
        if sources_file_path and sources_file_path.exists():
            console.print(f"[cyan]📄 Loading sources: {sources_file_path}[/cyan]")
            try:
                from sbkube.models.sources_model import SourceScheme

                sources_data = load_config_file(sources_file_path)
                sources = SourceScheme(**sources_data)
            except Exception as e:
                console.print(f"[red]❌ Invalid sources file: {e}[/red]")
                overall_success = False
                continue

        # Resolve cluster configuration
        try:
            kubeconfig, context = resolve_cluster_config(
                cli_kubeconfig=ctx.obj.get("kubeconfig"),
                cli_context=ctx.obj.get("context"),
                sources=sources,
            )
        except ClusterConfigError as e:
            console.print(f"[red]{e}[/red]")
            overall_success = False
            continue

        # 설정 파일 로드
        if not config_file_path.exists():
            console.print(f"[red]❌ Config file not found: {config_file_path}[/red]")
            overall_success = False
            continue

        console.print(f"[cyan]📄 Loading config: {config_file_path}[/cyan]")
        config_data = load_config_file(config_file_path)

        try:
            config = SBKubeConfig(**config_data)
        except Exception as e:
            console.print(f"[red]❌ Invalid config file: {e}[/red]")
            overall_success = False
            continue

        # 배포 순서 얻기 (의존성 고려)
        deployment_order = config.get_deployment_order()

        if app_name:
            # 특정 앱만 배포
            if app_name not in config.apps:
                console.print(f"[red]❌ App not found: {app_name}[/red]")
                overall_success = False
                continue
            apps_to_deploy = [app_name]
        else:
            # 모든 앱 배포 (의존성 순서대로)
            apps_to_deploy = deployment_order

        # Hook executor 초기화
        hook_executor = HookExecutor(
            base_dir=BASE_DIR,
            work_dir=APP_CONFIG_DIR,  # 훅은 APP_CONFIG_DIR에서 실행
            dry_run=dry_run,
        )

        # ========== 전역 pre-deploy 훅 실행 ==========
        if config.hooks and "deploy" in config.hooks:
            deploy_hooks = config.hooks["deploy"].model_dump()
            if not hook_executor.execute_command_hooks(
                hook_config=deploy_hooks,
                hook_phase="pre",
                command_name="deploy",
            ):
                console.print("[red]❌ Pre-deploy hook failed[/red]")
                overall_success = False
                continue

        # 앱 배포
        success_count = 0
        total_count = len(apps_to_deploy)
        deployment_failed = False

        for app_name_iter in apps_to_deploy:
            app = config.apps[app_name_iter]

            if not app.enabled:
                console.print(f"[yellow]⏭️  Skipping disabled app: {app_name_iter}[/yellow]")
                continue

            # ========== 앱별 pre-deploy 훅 실행 ==========
            if hasattr(app, "hooks") and app.hooks:
                app_hooks = app.hooks.model_dump()
                hook_context = {
                    "namespace": app.namespace if hasattr(app, "namespace") else config.namespace,
                    "release_name": getattr(app, "release_name", None) or app_name_iter,
                }
                if not hook_executor.execute_app_hook(
                    app_name=app_name_iter,
                    app_hooks=app_hooks,
                    hook_type="pre_deploy",
                    context=hook_context,
                ):
                    console.print(f"[red]❌ Pre-deploy hook failed for app: {app_name_iter}[/red]")
                    deployment_failed = True
                    continue

            success = False

            try:
                if isinstance(app, HelmApp):
                    check_helm_installed_or_exit()
                    success = deploy_helm_app(
                        app_name_iter,
                        app,
                        BASE_DIR,
                        CHARTS_DIR,
                        BUILD_DIR,
                        APP_CONFIG_DIR,
                        kubeconfig,
                        context,
                        dry_run,
                    )
                elif isinstance(app, YamlApp):
                    success = deploy_yaml_app(
                        app_name_iter,
                        app,
                        BASE_DIR,
                        APP_CONFIG_DIR,
                        kubeconfig,
                        context,
                        dry_run,
                    )
                elif isinstance(app, ActionApp):
                    success = deploy_action_app(
                        app_name_iter,
                        app,
                        BASE_DIR,
                        APP_CONFIG_DIR,
                        kubeconfig,
                        context,
                        dry_run,
                    )
                elif isinstance(app, ExecApp):
                    success = deploy_exec_app(app_name_iter, app, BASE_DIR, dry_run)
                elif isinstance(app, KustomizeApp):
                    success = deploy_kustomize_app(
                        app_name_iter,
                        app,
                        BASE_DIR,
                        APP_CONFIG_DIR,
                        kubeconfig,
                        context,
                        dry_run,
                    )
                elif isinstance(app, NoopApp):
                    success = deploy_noop_app(
                        app_name_iter, app, BASE_DIR, APP_CONFIG_DIR, dry_run
                    )
                else:
                    console.print(
                        f"[yellow]⏭️  Unsupported app type '{app.type}': {app_name_iter}[/yellow]"
                    )
                    continue
            except KubernetesConnectionError as exc:
                console.print(
                    f"[red]❌ Kubernetes cluster connection error detected while processing app: {app_name_iter}[/red]"
                )
                if exc.reason:
                    console.print(f"[red]   {exc.reason}[/red]")
                console.print(
                    "[yellow]💡 Check your cluster connectivity and try again.[/yellow]"
                )
                deployment_failed = True
                overall_success = False
                break

            # ========== 앱별 post-deploy 또는 on_deploy_failure 훅 실행 ==========
            if hasattr(app, "hooks") and app.hooks:
                app_hooks = app.hooks.model_dump()
                hook_context = {
                    "namespace": app.namespace if hasattr(app, "namespace") else config.namespace,
                    "release_name": getattr(app, "release_name", None) or app_name_iter,
                }

                if success:
                    # 배포 성공 시 post_deploy 훅 실행
                    hook_executor.execute_app_hook(
                        app_name=app_name_iter,
                        app_hooks=app_hooks,
                        hook_type="post_deploy",
                        context=hook_context,
                    )
                else:
                    # 배포 실패 시 on_deploy_failure 훅 실행
                    hook_executor.execute_app_hook(
                        app_name=app_name_iter,
                        app_hooks=app_hooks,
                        hook_type="on_deploy_failure",
                        context=hook_context,
                    )
                    deployment_failed = True

            if success:
                success_count += 1
            else:
                deployment_failed = True

        # ========== 전역 post-deploy 또는 on_failure 훅 실행 ==========
        if config.hooks and "deploy" in config.hooks:
            deploy_hooks = config.hooks["deploy"].model_dump()

            if deployment_failed:
                # 배포 실패 시 on_failure 훅 실행
                hook_executor.execute_command_hooks(
                    hook_config=deploy_hooks,
                    hook_phase="on_failure",
                    command_name="deploy",
                )
            else:
                # 모든 배포 성공 시 post 훅 실행
                hook_executor.execute_command_hooks(
                    hook_config=deploy_hooks,
                    hook_phase="post",
                    command_name="deploy",
                )

        # 이 앱 그룹 결과 출력
        console.print(
            f"[bold green]✅ App group '{APP_CONFIG_DIR.name}' deployed: {success_count}/{total_count} apps[/bold green]"
        )

        if success_count < total_count:
            overall_success = False

    # 전체 결과
    if not overall_success:
        console.print("\n[bold red]❌ Some app groups failed to deploy[/bold red]")
        raise click.Abort()
    else:
        console.print("\n[bold green]🎉 All app groups deployed successfully![/bold green]")
