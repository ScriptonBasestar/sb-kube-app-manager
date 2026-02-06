"""SBKube apply 명령어.

통합 명령어: prepare → deploy를 자동으로 실행.
의존성을 고려하여 올바른 순서로 배포합니다.

Supports unified sbkube.yaml format only.
"""

from pathlib import Path
from typing import TYPE_CHECKING

import click

from sbkube.models.config_model import SBKubeConfig
from sbkube.utils.app_dir_resolver import resolve_app_dirs
from sbkube.utils.deployment_checker import DeploymentChecker
from sbkube.utils.error_formatter import format_deployment_error
from sbkube.utils.file_loader import (
    ConfigType,
    detect_config_file,
    load_config_file,
)
from sbkube.utils.hook_executor import HookExecutor
from sbkube.utils.output_manager import OutputManager
from sbkube.utils.perf import perf_timer
from sbkube.utils.progress_tracker import ProgressTracker

if TYPE_CHECKING:
    pass


class ApplyCommand:
    """Programmatic interface for apply command.

    Used by workspace.py to deploy apps from a unified config file.
    """

    def __init__(
        self,
        config_file: str | None = None,
        base_dir: str = ".",
        app_config_dir: str | None = None,
        source: str = "sbkube.yaml",
        dry_run: bool = False,
        force: bool = False,
        parallel: bool = False,
        skip_prepare: bool = False,
        skip_build: bool = False,
        inherited_settings: dict | None = None,
    ) -> None:
        """Initialize ApplyCommand.

        Args:
            config_file: Path to unified config file (sbkube.yaml)
            base_dir: Base directory for legacy mode
            app_config_dir: App config directory for legacy mode
            source: Source file name (sbkube.yaml or sources.yaml)
            dry_run: Dry run mode
            force: Force deployment
            parallel: Parallel deployment
            skip_prepare: Skip prepare step
            skip_build: Skip build step
            inherited_settings: Settings inherited from parent workspace/phase
                (helm_repos, oci_registries, git_repos)

        """
        self.config_file = config_file
        self.base_dir = base_dir
        self.app_config_dir = app_config_dir
        self.source = source
        self.dry_run = dry_run
        self.force = force
        self.parallel = parallel
        self.skip_prepare = skip_prepare
        self.skip_build = skip_build
        self.inherited_settings = inherited_settings or {}

    def execute(self) -> bool:
        """Execute apply command.

        Returns:
            bool: True if successful

        """
        from rich.console import Console

        from sbkube.models.unified_config_model import UnifiedConfig

        console = Console()
        output = OutputManager(format_type="human")

        # Determine which config file to use
        if self.config_file:
            config_path = Path(self.config_file)
        else:
            # Legacy mode - look for sbkube.yaml in base_dir/app_config_dir
            if self.app_config_dir:
                config_path = Path(self.base_dir) / self.app_config_dir / self.source
            else:
                config_path = Path(self.base_dir) / self.source

        if not config_path.exists():
            console.print(f"[red]❌ Config file not found: {config_path}[/red]")
            return False

        # Load config
        try:
            data = load_config_file(str(config_path))
            if data is None:
                console.print(f"[red]❌ Empty config file: {config_path}[/red]")
                return False

            # Try unified config first
            if "apiVersion" in data and data.get("apiVersion", "").startswith("sbkube/"):
                unified_config = UnifiedConfig(**data)

                # Get namespace from settings (required for SBKubeConfig)
                namespace = unified_config.settings.namespace or "default"

                # Convert to SBKubeConfig for deployment
                config = SBKubeConfig(
                    namespace=namespace,
                    apps=unified_config.apps,
                    deps=unified_config.deps,
                    hooks=unified_config.hooks,
                )

                # Get settings from unified config
                settings = unified_config.settings

            else:
                # Legacy format - try SBKubeConfig directly
                config = SBKubeConfig(**data)
                settings = None

        except Exception as e:
            console.print(f"[red]❌ Failed to parse config: {e}[/red]")
            return False

        # Get enabled apps
        enabled_apps = config.get_enabled_apps()
        if not enabled_apps:
            console.print("[yellow]⚠️  No enabled apps found[/yellow]")
            return True

        if self.dry_run:
            console.print(
                f"[yellow]🔍 [DRY-RUN] Would deploy {len(enabled_apps)} app(s)[/yellow]"
            )
            return True

        # Execute deployment
        # For unified config, the base_dir is the parent of config file's directory
        # and app_config_dir is the directory containing sbkube.yaml
        app_config_dir = config_path.parent
        base_dir = str(app_config_dir.parent)  # Parent of app config dir
        current_app_dir = app_config_dir.name  # Just the directory name

        # Create a dummy click context for command invocation
        import click

        # Merge inherited settings with local settings (local takes precedence)
        merged_helm_repos = {**self.inherited_settings.get("helm_repos", {})}
        merged_oci_registries = {**self.inherited_settings.get("oci_registries", {})}
        merged_git_repos = {**self.inherited_settings.get("git_repos", {})}

        # Kubeconfig: local settings take precedence over inherited
        merged_kubeconfig = self.inherited_settings.get("kubeconfig")
        merged_kubeconfig_context = self.inherited_settings.get("kubeconfig_context")

        if settings:
            if settings.helm_repos:
                merged_helm_repos.update(settings.helm_repos)
            if settings.oci_registries:
                merged_oci_registries.update(settings.oci_registries)
            if settings.git_repos:
                merged_git_repos.update(settings.git_repos)
            if settings.kubeconfig:
                merged_kubeconfig = settings.kubeconfig
            if settings.kubeconfig_context:
                merged_kubeconfig_context = settings.kubeconfig_context

        ctx = click.Context(click.Command("apply"))
        ctx.obj = {
            "format": "human",
            "kubeconfig": merged_kubeconfig,
            "context": merged_kubeconfig_context,
            "inherited_settings": {
                "helm_repos": merged_helm_repos,
                "oci_registries": merged_oci_registries,
                "git_repos": merged_git_repos,
                "kubeconfig": merged_kubeconfig,
                "kubeconfig_context": merged_kubeconfig_context,
            },
        }

        try:
            success = _execute_apps_deployment(
                ctx=ctx,
                config=config,
                base_dir=base_dir,
                app_config_dir=app_config_dir,
                current_app_dir=current_app_dir,
                config_file_name=config_path.name,
                sources_file_name=config_path.name,  # Use same file for sources
                app_name=None,
                dry_run=self.dry_run,
                skip_prepare=self.skip_prepare,
                skip_build=self.skip_build,
                skip_deps_check=self.force,
                strict_deps=False,
                no_progress=False,
                output=output,
            )
            return success
        except Exception as e:
            console.print(f"[red]❌ Deployment failed: {e}[/red]")
            return False


def _execute_apps_deployment(
    ctx: click.Context,
    config: SBKubeConfig,
    base_dir: str,
    app_config_dir: Path,
    current_app_dir: str,
    config_file_name: str,
    sources_file_name: str,
    app_name: str | None,
    dry_run: bool,
    skip_prepare: bool,
    skip_build: bool,
    skip_deps_check: bool,
    strict_deps: bool,
    no_progress: bool,
    output: OutputManager,
) -> bool:
    """Execute app deployment for unified config without phases.

    Args:
        ctx: Click context
        config: SBKubeConfig with apps
        base_dir: Base directory
        app_config_dir: App config directory
        current_app_dir: Current app directory relative to base
        config_file_name: Config file name
        sources_file_name: Sources file name
        app_name: Specific app to deploy (None for all)
        dry_run: Dry run mode
        skip_prepare: Skip prepare step
        skip_build: Skip build step
        skip_deps_check: Skip dependency check
        strict_deps: Strict dependency mode
        no_progress: Disable progress tracking
        output: Output manager

    Returns:
        bool: True if deployment succeeded

    """
    from sbkube.commands.build import cmd as build_cmd
    from sbkube.commands.deploy import cmd as deploy_cmd
    from sbkube.commands.prepare import cmd as prepare_cmd

    BASE_DIR = Path(base_dir).resolve()
    APP_CONFIG_DIR = app_config_dir
    overall_success = True

    # deps (app-group dependencies) 배포 상태 검증
    if config.deps and not skip_deps_check:
        output.print(
            "[cyan]🔍 Checking app-group dependencies...[/cyan]", level="info"
        )
        deployment_checker = DeploymentChecker(
            base_dir=BASE_DIR,
            namespace=None,
        )

        dep_check_result = deployment_checker.check_dependencies(
            deps=config.deps,
            namespace=None,
        )

        if not dep_check_result["all_deployed"]:
            output.print_warning(
                f"⚠️  {len(dep_check_result['missing'])} dependencies not deployed:",
                missing_count=len(dep_check_result["missing"]),
            )
            for dep in dep_check_result["missing"]:
                _, status_msg = dep_check_result["details"][dep]
                output.print(f"  - {dep} ({status_msg})", level="warning")

            if strict_deps:
                output.print_error(
                    "Deployment aborted due to missing dependencies (--strict-deps mode)",
                )
                return False
            output.print(
                "\n[yellow]⚠️  Continuing deployment despite missing dependencies (non-blocking mode)[/yellow]",
                level="warning",
            )
        else:
            output.print_success(
                f"All {len(config.deps)} dependencies are deployed:",
                deps_count=len(config.deps),
            )
    elif config.deps and skip_deps_check:
        output.print_warning(
            f"Skipping dependency check ({len(config.deps)} deps declared)",
            deps_count=len(config.deps),
        )

    # Hook executor 초기화
    hook_executor = HookExecutor(
        base_dir=BASE_DIR,
        work_dir=APP_CONFIG_DIR,
        dry_run=dry_run,
    )

    # 글로벌 pre-apply 훅 실행
    if config.hooks and "apply" in config.hooks:
        apply_hooks = config.hooks["apply"].model_dump()
        output.print(
            "[cyan]🪝 Executing global pre-apply hooks...[/cyan]", level="info"
        )
        if not hook_executor.execute_command_hooks(apply_hooks, "pre", "apply"):
            output.print_error("Pre-apply hook failed")
            return False

    # 배포 순서 출력
    deployment_order = config.get_deployment_order()
    output.print(
        "\n[cyan]📋 Deployment order (based on dependencies):[/cyan]", level="info"
    )
    for idx, app in enumerate(deployment_order, 1):
        app_config = config.apps[app]
        deps = getattr(app_config, "depends_on", [])
        deps_str = f" [depends on: {', '.join(deps)}]" if deps else ""
        output.print(f"  {idx}. {app} ({app_config.type}){deps_str}", level="info")

    # 적용할 앱 필터링
    if app_name:
        if app_name not in config.apps:
            output.print_error(f"App not found: {app_name}", app_name=app_name)
            return False

        apps_to_apply = []
        visited: set[str] = set()

        def collect_dependencies(name: str) -> None:
            if name in visited:
                return
            visited.add(name)
            app_cfg = config.apps[name]
            if hasattr(app_cfg, "depends_on"):
                for dep in app_cfg.depends_on:
                    collect_dependencies(dep)
            apps_to_apply.append(name)

        collect_dependencies(app_name)
        output.print(
            f"\n[yellow]ℹ️  Including dependencies: {', '.join(apps_to_apply)}[/yellow]",
            level="info",
        )
    else:
        apps_to_apply = deployment_order

    # Progress tracking setup
    console = output.get_console()
    progress_tracker = ProgressTracker(
        console=console, disable=(dry_run or no_progress)
    )

    failed = False
    try:
        for app_name_iter in apps_to_apply:
            app_config = config.apps[app_name_iter]

            if not app_config.enabled:
                output.print(
                    f"[yellow]⏭️  Skipping disabled app: {app_name_iter}[/yellow]",
                    level="info",
                )
                output.add_deployment(
                    name=app_name_iter,
                    namespace=getattr(app_config, "namespace", "default"),
                    status="skipped",
                )
                continue

            output.print_section(f"{app_name_iter} ({app_config.type})")

            total_steps = 3
            if skip_prepare:
                total_steps -= 1
            if skip_build:
                total_steps -= 1

            use_progress = not no_progress and not dry_run

            with progress_tracker.track_task(
                f"Deploying {app_name_iter}", total=total_steps
            ) as task_id:
                # Step 1: Prepare
                if not skip_prepare:
                    if use_progress:
                        progress_tracker.update(
                            task_id, description=f"📦 Prepare {app_name_iter}"
                        )
                    else:
                        output.print(
                            f"[cyan]📦 Step 1: Prepare {app_name_iter}[/cyan]",
                            level="info",
                        )

                    prepare_ctx = click.Context(prepare_cmd, parent=ctx)
                    prepare_ctx.obj = ctx.obj
                    with perf_timer("stage.prepare", app=app_name_iter):
                        prepare_ctx.invoke(
                            prepare_cmd,
                            app_config_dir_name=current_app_dir,
                            base_dir=base_dir,
                            config_file_name=config_file_name,
                            sources_file_name=sources_file_name,
                            app_name=app_name_iter,
                            force=False,
                            dry_run=dry_run,
                        )
                    if use_progress:
                        progress_tracker.update(task_id, advance=1)

                # Step 2: Build
                if not skip_build:
                    step_number = 2 if not skip_prepare else 1
                    if use_progress:
                        progress_tracker.update(
                            task_id, description=f"🔨 Build {app_name_iter}"
                        )
                    else:
                        output.print(
                            f"[cyan]🔨 Step {step_number}: Build {app_name_iter}[/cyan]",
                            level="info",
                        )

                    build_ctx = click.Context(build_cmd, parent=ctx)
                    build_ctx.obj = ctx.obj
                    with perf_timer("stage.build", app=app_name_iter):
                        build_ctx.invoke(
                            build_cmd,
                            app_config_dir_name=current_app_dir,
                            base_dir=base_dir,
                            config_file_name=config_file_name,
                            sources_file_name=sources_file_name,
                            app_name=app_name_iter,
                            dry_run=dry_run,
                        )
                    if use_progress:
                        progress_tracker.update(task_id, advance=1)

                # Step 3: Deploy
                step_number = 3
                if skip_prepare:
                    step_number -= 1
                if skip_build:
                    step_number -= 1

                if use_progress:
                    progress_tracker.update(
                        task_id, description=f"🚀 Deploy {app_name_iter}"
                    )
                else:
                    output.print(
                        f"[cyan]🚀 Step {step_number}: Deploy {app_name_iter}[/cyan]",
                        level="info",
                    )

                deploy_ctx = click.Context(deploy_cmd, parent=ctx)
                deploy_ctx.obj = ctx.obj
                with perf_timer("stage.deploy", app=app_name_iter):
                    deploy_ctx.invoke(
                        deploy_cmd,
                        app_config_dir_name=current_app_dir,
                        base_dir=base_dir,
                        config_file_name=config_file_name,
                        sources_file_name=sources_file_name,
                        app_name=app_name_iter,
                        dry_run=dry_run,
                    )
                if use_progress:
                    progress_tracker.update(task_id, advance=1)
                    progress_tracker.console_print(
                        f"[green]✅ {app_name_iter} deployed successfully[/green]"
                    )
                output.add_deployment(
                    name=app_name_iter,
                    namespace=getattr(app_config, "namespace", "default"),
                    status="deployed",
                    version=getattr(app_config, "version", None),
                )

        # 글로벌 post-apply 훅 실행
        if config.hooks and "apply" in config.hooks:
            apply_hooks = config.hooks["apply"].model_dump()
            output.print(
                "[cyan]🪝 Executing global post-apply hooks...[/cyan]", level="info"
            )
            if not hook_executor.execute_command_hooks(
                apply_hooks, "post", "apply"
            ):
                output.print_error("Post-apply hook failed")
                failed = True

    except KeyboardInterrupt:
        output.print(
            "\n[yellow]⚠️  Operation interrupted by user[/yellow]", level="warning"
        )
        raise
    except Exception as e:
        failed = True
        output.print_error(f"Deployment failed: {e}")
        if config.hooks and "apply" in config.hooks:
            apply_hooks = config.hooks["apply"].model_dump()
            output.print(
                "[yellow]🪝 Executing global on-failure hooks...[/yellow]",
                level="warning",
            )
            hook_executor.execute_command_hooks(apply_hooks, "on_failure", "apply")

    if failed:
        overall_success = False
    else:
        output.print_success(
            "App group applied successfully!",
        )

    return overall_success


@click.command(name="apply")
@click.option(
    "-f",
    "--file",
    "config_file",
    default=None,
    type=click.Path(exists=True, file_okay=True, dir_okay=False),
    help="Unified config file (sbkube.yaml) - recommended for new projects",
)
@click.option(
    "--app-dir",
    "app_config_dir_name",
    default=None,
    help="[DEPRECATED] 앱 설정 디렉토리 (지정하지 않으면 모든 하위 디렉토리 자동 탐색)",
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
    help="[DEPRECATED] 설정 파일 이름 (app-dir 내부) - use -f instead",
)
@click.option(
    "--source",
    "sources_file_name",
    default="sources.yaml",
    help="[DEPRECATED] 소스 설정 파일 (base-dir 기준) - use -f instead",
)
@click.option(
    "--app",
    "app_name",
    default=None,
    help="적용할 특정 앱 이름 (지정하지 않으면 모든 앱 적용)",
)
@click.option(
    "--dry-run",
    is_flag=True,
    default=False,
    help="Dry-run 모드 (실제 배포하지 않음)",
)
@click.option(
    "--skip-prepare",
    is_flag=True,
    default=False,
    help="prepare 단계 건너뛰기 (이미 준비된 경우)",
)
@click.option(
    "--skip-build",
    is_flag=True,
    default=False,
    help="build 단계 건너뛰기 (overrides/removes가 없는 경우)",
)
@click.option(
    "--skip-deps-check",
    is_flag=True,
    default=False,
    help="앱 그룹 의존성 검증 건너뛰기 (강제 배포 시)",
)
@click.option(
    "--strict-deps",
    is_flag=True,
    default=False,
    help="의존성 검증 실패 시 배포 중단 (기본: 경고만 출력하고 계속 진행)",
)
@click.option(
    "--no-progress",
    is_flag=True,
    default=False,
    help="진행 상황 표시 비활성화",
)
@click.pass_context
def cmd(
    ctx: click.Context,
    config_file: str | None,
    app_config_dir_name: str | None,
    base_dir: str,
    config_file_name: str,
    sources_file_name: str,
    app_name: str | None,
    dry_run: bool,
    skip_prepare: bool,
    skip_build: bool,
    skip_deps_check: bool,
    strict_deps: bool,
    no_progress: bool,
) -> None:
    """SBKube apply 명령어.

    전체 워크플로우를 한 번에 실행합니다:
    1. prepare: 외부 리소스 준비 (Helm chart pull, Git clone, HTTP download 등)
    2. build: 차트 커스터마이징 (overrides, removes 적용)
    3. deploy: Kubernetes 클러스터에 배포

    의존성(depends_on)을 자동으로 해결하여 올바른 순서로 배포합니다.

    \b
    Usage with unified config (recommended):
        sbkube apply -f sbkube.yaml
        sbkube apply -f sbkube.yaml --dry-run

    \b
    Usage with legacy config (deprecated):
        sbkube apply --base-dir ./project --source sources.yaml
    """
    # Initialize OutputManager
    output_format = ctx.obj.get("format", "human")
    output = OutputManager(format_type=output_format)

    output.print("[bold blue]✨ SBKube `apply` 시작 ✨[/bold blue]", level="info")

    if dry_run:
        output.print("[yellow]🔍 Dry-run mode enabled[/yellow]", level="info")

    # Detect config format and emit deprecation warnings
    BASE_DIR = Path(base_dir).resolve()
    detected = detect_config_file(BASE_DIR, config_file)

    if detected.config_type == ConfigType.UNIFIED:
        output.print(
            f"[green]📄 Using unified config: {detected.primary_file}[/green]",
            level="info",
        )
        # Load config to check if it has phases (workspace mode)
        config_data = load_config_file(str(detected.primary_file))
        if "phases" in config_data and config_data["phases"]:
            # Workspace mode: delegate to WorkspaceDeployCommand
            output.print(
                "[cyan]🔄 Detected multi-phase workspace configuration[/cyan]",
                level="info",
            )
            from sbkube.commands.workspace import WorkspaceDeployCommand

            workspace_cmd = WorkspaceDeployCommand(
                workspace_file=str(detected.primary_file),
                phase=None,  # Deploy all phases
                dry_run=dry_run,
                force=False,
                skip_validation=False,
                parallel=None,
                parallel_apps=None,
                max_workers=4,
            )
            success = workspace_cmd.execute()
            if not success:
                raise click.Abort
            return

        # Single app group mode with unified config - process apps directly
        output.print(
            "[cyan]📦 Single app group mode (no phases)[/cyan]",
            level="info",
        )
        # Load apps from unified config and deploy directly
        from sbkube.models.unified_config_model import UnifiedConfig

        try:
            unified_config = UnifiedConfig(**config_data)
        except Exception as e:
            output.print_error(f"Invalid unified config: {e}", error=str(e))
            raise click.Abort

        # Convert UnifiedConfig apps to SBKubeConfig format for compatibility
        config = SBKubeConfig(
            namespace=unified_config.settings.namespace,
            apps=unified_config.apps,
            deps=unified_config.deps,
            hooks=config_data.get("hooks", {}),
        )

        # Process apps using the existing flow (skip directory scanning)
        # Set up paths for the unified config location
        APP_CONFIG_DIR = detected.primary_file.parent
        current_app_dir = APP_CONFIG_DIR.name

        overall_success = _execute_apps_deployment(
            ctx=ctx,
            config=config,
            base_dir=str(APP_CONFIG_DIR.parent),
            app_config_dir=APP_CONFIG_DIR,
            current_app_dir=current_app_dir,
            config_file_name="sbkube.yaml",
            sources_file_name="sbkube.yaml",
            app_name=app_name,
            dry_run=dry_run,
            skip_prepare=skip_prepare,
            skip_build=skip_build,
            skip_deps_check=skip_deps_check,
            strict_deps=strict_deps,
            no_progress=no_progress,
            output=output,
        )

        if not overall_success:
            output.print(
                "\n[bold red]❌ Deployment failed[/bold red]", level="error"
            )
            output.finalize(status="failed", summary={"status": "failed"})
            raise click.Abort

        output.print(
            "\n[bold green]🎉 All apps applied successfully![/bold green]",
            level="success",
        )
        output.finalize(
            status="success",
            summary={"status": "success"},
            next_steps=["Verify deployment with: kubectl get pods"],
        )
        return

    elif detected.config_type == ConfigType.UNKNOWN:
        output.print_error(
            f"No sbkube.yaml found in {BASE_DIR}. "
            "Create one with 'sbkube init' or specify with -f flag.",
            config_path=str(BASE_DIR),
        )
        raise click.Abort

    # 경로 설정
    BASE_DIR = Path(base_dir).resolve()

    # 앱 그룹 디렉토리 결정 (공통 유틸리티 사용)
    try:
        app_config_dirs = resolve_app_dirs(
            BASE_DIR, app_config_dir_name, config_file_name, sources_file_name
        )
    except ValueError:
        raise click.Abort

    # 각 앱 그룹 처리
    overall_success = True
    for APP_CONFIG_DIR in app_config_dirs:
        output.print_section(f"Processing app group: {APP_CONFIG_DIR.name}")

        # app_config_dir_name을 현재 앱 그룹 이름으로 설정
        current_app_dir = str(APP_CONFIG_DIR.relative_to(BASE_DIR))
        config_file_path = APP_CONFIG_DIR / config_file_name

        # 설정 파일 로드
        if not config_file_path.exists():
            output.print_error(
                f"Config file not found: {config_file_path}",
                config_path=str(config_file_path),
            )
            overall_success = False
            continue

        output.print(
            f"[cyan]📄 Loading config: {config_file_path}[/cyan]", level="info"
        )
        config_data = load_config_file(config_file_path)

        try:
            config = SBKubeConfig(**config_data)
        except Exception as e:
            output.print_error(f"Invalid config file: {e}", error=str(e))
            overall_success = False
            continue

        # deps (app-group dependencies) 배포 상태 검증
        if config.deps and not skip_deps_check:
            output.print(
                "[cyan]🔍 Checking app-group dependencies...[/cyan]", level="info"
            )
            deployment_checker = DeploymentChecker(
                base_dir=BASE_DIR,
                namespace=None,  # Auto-detect from deployment history
            )

            dep_check_result = deployment_checker.check_dependencies(
                deps=config.deps,
                namespace=None,  # Auto-detect namespace for each dependency
            )

            if not dep_check_result["all_deployed"]:
                # 의존성 누락 정보 출력
                output.print_warning(
                    f"⚠️  {len(dep_check_result['missing'])} dependencies not deployed:",
                    missing_count=len(dep_check_result["missing"]),
                )
                missing_deps = []
                for dep in dep_check_result["missing"]:
                    _, status_msg = dep_check_result["details"][dep]
                    missing_deps.append(f"{dep} ({status_msg})")
                    output.print(f"  - {dep} ({status_msg})", level="warning")

                output.print(
                    "\n[yellow]💡 Recommended deployment order:[/yellow]",
                    level="warning",
                )
                for dep in dep_check_result["missing"]:
                    output.print(f"  sbkube apply --app-dir {dep}", level="info")

                # strict_deps 모드일 때만 중단
                if strict_deps:
                    output.print_error(
                        "Deployment aborted due to missing dependencies (--strict-deps mode)",
                    )
                    output.print(
                        "\n[dim]Tip: Use --skip-deps-check to override this check, or remove --strict-deps to allow deployment with warnings[/dim]",
                        level="info",
                    )
                    overall_success = False
                    continue
                # 경고만 출력하고 계속 진행
                output.print(
                    "\n[yellow]⚠️  Continuing deployment despite missing dependencies (non-blocking mode)[/yellow]",
                    level="warning",
                )
                output.print(
                    "[dim]Tip: Use --strict-deps to enforce dependency validation[/dim]",
                    level="info",
                )
            else:
                # All deps are deployed
                output.print_success(
                    f"All {len(config.deps)} dependencies are deployed:",
                    deps_count=len(config.deps),
                )
                for dep, (deployed, msg) in dep_check_result["details"].items():
                    output.print(f"  - {dep}: {msg}", level="success")
        elif config.deps and skip_deps_check:
            output.print_warning(
                f"Skipping dependency check ({len(config.deps)} deps declared)",
                deps_count=len(config.deps),
            )

        # Hook executor 초기화
        hook_executor = HookExecutor(
            base_dir=BASE_DIR,
            work_dir=APP_CONFIG_DIR,  # 훅은 APP_CONFIG_DIR에서 실행
            dry_run=dry_run,
        )

        # 글로벌 pre-apply 훅 실행
        if config.hooks and "apply" in config.hooks:
            apply_hooks = config.hooks["apply"].model_dump()
            output.print(
                "[cyan]🪝 Executing global pre-apply hooks...[/cyan]", level="info"
            )
            if not hook_executor.execute_command_hooks(apply_hooks, "pre", "apply"):
                output.print_error("Pre-apply hook failed")
                overall_success = False
                continue

        # 배포 순서 출력
        deployment_order = config.get_deployment_order()
        output.print(
            "\n[cyan]📋 Deployment order (based on dependencies):[/cyan]", level="info"
        )
        deployment_list = []
        for idx, app in enumerate(deployment_order, 1):
            app_config = config.apps[app]
            deps = getattr(app_config, "depends_on", [])
            deps_str = f" [depends on: {', '.join(deps)}]" if deps else ""
            deployment_list.append(f"{idx}. {app} ({app_config.type}){deps_str}")
            output.print(f"  {idx}. {app} ({app_config.type}){deps_str}", level="info")

        # 적용할 앱 필터링
        if app_name:
            if app_name not in config.apps:
                output.print_error(f"App not found: {app_name}", app_name=app_name)
                overall_success = False
                continue

            # 의존성 체크: 해당 앱이 의존하는 앱들도 함께 배포해야 함
            apps_to_apply = []
            visited = set()

            def collect_dependencies(name: str) -> None:
                if name in visited:  # noqa: B023
                    return
                visited.add(name)  # noqa: B023

                app_cfg = config.apps[name]  # noqa: B023
                if hasattr(app_cfg, "depends_on"):
                    for dep in app_cfg.depends_on:
                        collect_dependencies(dep)

                apps_to_apply.append(name)  # noqa: B023

            collect_dependencies(app_name)
            output.print(
                f"\n[yellow]ℹ️  Including dependencies: {', '.join(apps_to_apply)}[/yellow]",
                level="info",
            )
        else:
            apps_to_apply = deployment_order

        # Import commands
        from sbkube.commands.build import cmd as build_cmd
        from sbkube.commands.deploy import cmd as deploy_cmd
        from sbkube.commands.prepare import cmd as prepare_cmd

        # Process each app in dependency order
        failed = False

        # Progress tracking setup (get console from OutputManager)
        console = output.get_console()
        progress_tracker = ProgressTracker(
            console=console, disable=(dry_run or no_progress)
        )

        try:
            for app_name_iter in apps_to_apply:
                app_config = config.apps[app_name_iter]

                if not app_config.enabled:
                    output.print(
                        f"[yellow]⏭️  Skipping disabled app: {app_name_iter}[/yellow]",
                        level="info",
                    )
                    # Record skipped deployment
                    output.add_deployment(
                        name=app_name_iter,
                        namespace=getattr(app_config, "namespace", "default"),
                        status="skipped",
                    )
                    continue

                if not no_progress:
                    # Progress 모드: 앱 헤더를 간단하게
                    output.print_section(f"{app_name_iter} ({app_config.type})")
                else:
                    # 일반 모드: 기존 동작 유지
                    output.print_section(
                        f"Processing app: {app_name_iter} ({app_config.type})"
                    )

                # Determine total steps (considering skip flags)
                total_steps = 3
                if skip_prepare:
                    total_steps -= 1
                if skip_build:
                    total_steps -= 1

                # Use progress tracker if enabled
                use_progress = not no_progress and not dry_run

                # Execute steps with progress tracking
                with progress_tracker.track_task(
                    f"Deploying {app_name_iter}", total=total_steps
                ) as task_id:
                    # Step 1: Prepare this app
                    if not skip_prepare:
                        if use_progress:
                            progress_tracker.update(
                                task_id, description=f"📦 Prepare {app_name_iter}"
                            )
                        else:
                            output.print(
                                f"[cyan]📦 Step 1: Prepare {app_name_iter}[/cyan]",
                                level="info",
                            )

                        try:
                            # Create new context with parent's obj for kubeconfig/context/sources_file
                            prepare_ctx = click.Context(prepare_cmd, parent=ctx)
                            prepare_ctx.obj = ctx.obj  # Pass parent context object
                            prepare_ctx.invoke(
                                prepare_cmd,
                                app_config_dir_name=current_app_dir,
                                base_dir=base_dir,
                                config_file_name=config_file_name,
                                sources_file_name=sources_file_name,
                                app_name=app_name_iter,  # 현재 처리 중인 앱
                                force=False,
                                dry_run=dry_run,
                            )
                            if use_progress:
                                progress_tracker.update(task_id, advance=1)
                        except Exception as prepare_error:
                            format_deployment_error(
                                error=prepare_error,
                                app_name=app_name_iter,
                                step="prepare",
                                step_number=1,
                                total_steps=total_steps,
                                console=console,
                            )
                            raise  # Re-raise to trigger outer exception handler

                    # Step 2: Build this app
                    if not skip_build:
                        step_number = 2 if not skip_prepare else 1
                        if use_progress:
                            progress_tracker.update(
                                task_id, description=f"🔨 Build {app_name_iter}"
                            )
                        else:
                            output.print(
                                f"[cyan]🔨 Step {step_number}: Build {app_name_iter}[/cyan]",
                                level="info",
                            )

                        try:
                            # Create new context with parent's obj
                            build_ctx = click.Context(build_cmd, parent=ctx)
                            build_ctx.obj = ctx.obj  # Pass parent context object
                            build_ctx.invoke(
                                build_cmd,
                                app_config_dir_name=current_app_dir,
                                base_dir=base_dir,
                                config_file_name=config_file_name,
                                app_name=app_name_iter,  # 현재 처리 중인 앱
                                dry_run=dry_run,
                            )
                            if use_progress:
                                progress_tracker.update(task_id, advance=1)
                        except Exception as build_error:
                            format_deployment_error(
                                error=build_error,
                                app_name=app_name_iter,
                                step="build",
                                step_number=step_number,
                                total_steps=total_steps,
                                console=console,
                            )
                            raise  # Re-raise to trigger outer exception handler

                    # Step 3: Deploy this app
                    step_number = 3
                    if skip_prepare:
                        step_number -= 1
                    if skip_build:
                        step_number -= 1

                    if use_progress:
                        progress_tracker.update(
                            task_id, description=f"🚀 Deploy {app_name_iter}"
                        )
                    else:
                        output.print(
                            f"[cyan]🚀 Step {step_number}: Deploy {app_name_iter}[/cyan]",
                            level="info",
                        )

                    try:
                        # Create new context with parent's obj for kubeconfig/context/sources_file
                        deploy_ctx = click.Context(deploy_cmd, parent=ctx)
                        deploy_ctx.obj = ctx.obj  # Pass parent context object
                        deploy_ctx.invoke(
                            deploy_cmd,
                            app_config_dir_name=current_app_dir,
                            base_dir=base_dir,
                            config_file_name=config_file_name,
                            app_name=app_name_iter,  # 현재 처리 중인 앱
                            dry_run=dry_run,
                        )
                        if use_progress:
                            progress_tracker.update(task_id, advance=1)
                            progress_tracker.console_print(
                                f"[green]✅ {app_name_iter} deployed successfully[/green]"
                            )
                        # Record successful deployment
                        output.add_deployment(
                            name=app_name_iter,
                            namespace=getattr(app_config, "namespace", "default"),
                            status="deployed",
                            version=getattr(app_config, "version", None),
                        )
                    except Exception as deploy_error:
                        format_deployment_error(
                            error=deploy_error,
                            app_name=app_name_iter,
                            step="deploy",
                            step_number=step_number,
                            total_steps=total_steps,
                            console=console,
                        )
                        raise  # Re-raise to trigger outer exception handler

            # 글로벌 post-apply 훅 실행
            if config.hooks and "apply" in config.hooks:
                apply_hooks = config.hooks["apply"].model_dump()
                output.print(
                    "[cyan]🪝 Executing global post-apply hooks...[/cyan]", level="info"
                )
                if not hook_executor.execute_command_hooks(
                    apply_hooks, "post", "apply"
                ):
                    output.print_error("Post-apply hook failed")
                    failed = True

        except KeyboardInterrupt:
            # User interrupted (Ctrl+C) - exit immediately
            output.print(
                "\n[yellow]⚠️  Operation interrupted by user[/yellow]", level="warning"
            )
            if "app_name_iter" in locals():
                output.print_error(f"App '{app_name_iter}' deployment was interrupted")
            raise  # Re-raise to exit the entire command
        except Exception:
            failed = True
            # Record failed deployment (if app_name_iter is available)
            if "app_name_iter" in locals():
                output.add_deployment(
                    name=app_name_iter,
                    namespace=getattr(app_config, "namespace", "default"),
                    status="failed",
                )
            # 글로벌 on_failure 훅 실행
            if config.hooks and "apply" in config.hooks:
                apply_hooks = config.hooks["apply"].model_dump()
                output.print(
                    "[yellow]🪝 Executing global on-failure hooks...[/yellow]",
                    level="warning",
                )
                hook_executor.execute_command_hooks(apply_hooks, "on_failure", "apply")
            overall_success = False
            # Note: Detailed error already printed by format_deployment_error in inner try-except
            # Just print summary here
            output.print_error(f"App group '{APP_CONFIG_DIR.name}' 처리 실패")
            continue

        # 실패 시 on_failure 훅 실행
        if failed:
            if config.hooks and "apply" in config.hooks:
                apply_hooks = config.hooks["apply"].model_dump()
                output.print(
                    "[yellow]🪝 Executing global on-failure hooks...[/yellow]",
                    level="warning",
                )
                hook_executor.execute_command_hooks(apply_hooks, "on_failure", "apply")
            overall_success = False
            output.print_error(f"App group '{APP_CONFIG_DIR.name}' failed")
        else:
            output.print_success(
                f"App group '{APP_CONFIG_DIR.name}' applied successfully!",
                app_group=APP_CONFIG_DIR.name,
            )

    # 전체 결과
    if not overall_success:
        output.print(
            "\n[bold red]❌ Some app groups failed to apply[/bold red]", level="error"
        )
        output.finalize(
            status="failed",
            summary={
                "app_groups_processed": len(app_config_dirs),
                "status": "failed",
            },
            next_steps=["Check error messages above", "Fix issues and retry"],
            # errors는 OutputManager가 자동으로 수집한 것을 사용
        )
        raise click.Abort
    output.print(
        "\n[bold green]🎉 All app groups applied successfully![/bold green]",
        level="success",
    )
    output.finalize(
        status="success",
        summary={
            "app_groups_processed": len(app_config_dirs),
            "status": "success",
        },
        next_steps=["Verify deployment with: kubectl get pods"],
    )
