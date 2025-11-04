"""
SBKube apply 명령어.

통합 명령어: prepare → deploy를 자동으로 실행.
의존성을 고려하여 올바른 순서로 배포합니다.
"""

from pathlib import Path

import click
from rich.console import Console

from sbkube.models.config_model import SBKubeConfig
from sbkube.utils.app_dir_resolver import resolve_app_dirs
from sbkube.utils.deployment_checker import DeploymentChecker
from sbkube.utils.error_formatter import format_deployment_error
from sbkube.utils.file_loader import load_config_file
from sbkube.utils.hook_executor import HookExecutor
from sbkube.utils.progress_tracker import ProgressTracker

console = Console()


@click.command(name="apply")
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
    "--no-progress",
    is_flag=True,
    default=False,
    help="진행 상황 표시 비활성화",
)
@click.pass_context
def cmd(
    ctx: click.Context,
    app_config_dir_name: str | None,
    base_dir: str,
    config_file_name: str,
    sources_file_name: str,
    app_name: str | None,
    dry_run: bool,
    skip_prepare: bool,
    skip_build: bool,
    skip_deps_check: bool,
    no_progress: bool,
):
    """
    SBKube apply 명령어.

    전체 워크플로우를 한 번에 실행합니다:
    1. prepare: 외부 리소스 준비 (Helm chart pull, Git clone, HTTP download 등)
    2. build: 차트 커스터마이징 (overrides, removes 적용)
    3. deploy: Kubernetes 클러스터에 배포

    의존성(depends_on)을 자동으로 해결하여 올바른 순서로 배포합니다.
    """
    console.print("[bold blue]✨ SBKube `apply` 시작 ✨[/bold blue]")

    if dry_run:
        console.print("[yellow]🔍 Dry-run mode enabled[/yellow]")

    # 경로 설정
    BASE_DIR = Path(base_dir).resolve()

    # 앱 그룹 디렉토리 결정 (공통 유틸리티 사용)
    try:
        app_config_dirs = resolve_app_dirs(
            BASE_DIR, app_config_dir_name, config_file_name, sources_file_name
        )
    except ValueError:
        raise click.Abort()

    # 각 앱 그룹 처리
    overall_success = True
    for APP_CONFIG_DIR in app_config_dirs:
        console.print(
            f"\n[bold cyan]━━━ Processing app group: {APP_CONFIG_DIR.name} ━━━[/bold cyan]"
        )

        # app_config_dir_name을 현재 앱 그룹 이름으로 설정
        current_app_dir = str(APP_CONFIG_DIR.relative_to(BASE_DIR))
        config_file_path = APP_CONFIG_DIR / config_file_name

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

        # deps (app-group dependencies) 배포 상태 검증
        if config.deps and not skip_deps_check:
            console.print("[cyan]🔍 Checking app-group dependencies...[/cyan]")
            deployment_checker = DeploymentChecker(
                base_dir=BASE_DIR,
                namespace=None,  # Auto-detect from deployment history
            )

            dep_check_result = deployment_checker.check_dependencies(
                deps=config.deps,
                namespace=None,  # Auto-detect namespace for each dependency
            )

            if not dep_check_result["all_deployed"]:
                console.print(
                    f"[red]❌ Error: {len(dep_check_result['missing'])} dependencies not deployed:[/red]"
                )
                for dep in dep_check_result["missing"]:
                    _, status_msg = dep_check_result["details"][dep]
                    console.print(f"  - {dep} ({status_msg})")

                console.print(
                    "\n[yellow]💡 Deploy missing dependencies first:[/yellow]"
                )
                for dep in dep_check_result["missing"]:
                    console.print(f"  sbkube apply --app-dir {dep}")

                console.print(
                    "\n[dim]Tip: Use --skip-deps-check to override this check[/dim]"
                )

                overall_success = False
                continue

            # All deps are deployed
            console.print(
                f"[green]✅ All {len(config.deps)} dependencies are deployed:[/green]"
            )
            for dep, (deployed, msg) in dep_check_result["details"].items():
                console.print(f"  - {dep}: {msg}")
        elif config.deps and skip_deps_check:
            console.print(
                f"[yellow]⚠️  Skipping dependency check ({len(config.deps)} deps declared)[/yellow]"
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
            console.print("[cyan]🪝 Executing global pre-apply hooks...[/cyan]")
            if not hook_executor.execute_command_hooks(apply_hooks, "pre", "apply"):
                console.print("[red]❌ Pre-apply hook failed[/red]")
                overall_success = False
                continue

        # 배포 순서 출력
        deployment_order = config.get_deployment_order()
        console.print("\n[cyan]📋 Deployment order (based on dependencies):[/cyan]")
        for idx, app in enumerate(deployment_order, 1):
            app_config = config.apps[app]
            deps = getattr(app_config, "depends_on", [])
            deps_str = f" [depends on: {', '.join(deps)}]" if deps else ""
            console.print(f"  {idx}. {app} ({app_config.type}){deps_str}")

        # 적용할 앱 필터링
        if app_name:
            if app_name not in config.apps:
                console.print(f"[red]❌ App not found: {app_name}[/red]")
                overall_success = False
                continue

            # 의존성 체크: 해당 앱이 의존하는 앱들도 함께 배포해야 함
            apps_to_apply = []
            visited = set()

            def collect_dependencies(name: str):
                if name in visited:  # noqa: B023
                    return
                visited.add(name)  # noqa: B023

                app_cfg = config.apps[name]  # noqa: B023
                if hasattr(app_cfg, "depends_on"):
                    for dep in app_cfg.depends_on:
                        collect_dependencies(dep)

                apps_to_apply.append(name)  # noqa: B023

            collect_dependencies(app_name)
            console.print(
                f"\n[yellow]ℹ️  Including dependencies: {', '.join(apps_to_apply)}[/yellow]"
            )
        else:
            apps_to_apply = deployment_order

        # Import commands
        from sbkube.commands.build import cmd as build_cmd
        from sbkube.commands.deploy import cmd as deploy_cmd
        from sbkube.commands.prepare import cmd as prepare_cmd

        # Process each app in dependency order
        failed = False

        # Progress tracking setup
        progress_tracker = ProgressTracker(console=console, disable=(dry_run or no_progress))

        try:
            for app_name_iter in apps_to_apply:
                app_config = config.apps[app_name_iter]

                if not app_config.enabled:
                    console.print(
                        f"[yellow]⏭️  Skipping disabled app: {app_name_iter}[/yellow]"
                    )
                    continue

                if not no_progress:
                    # Progress 모드: 앱 헤더를 간단하게
                    console.print(f"\n[bold cyan]━━━ {app_name_iter} ({app_config.type}) ━━━[/bold cyan]")
                else:
                    # 일반 모드: 기존 동작 유지
                    console.print(
                        f"\n[bold cyan]━━━ Processing app: {app_name_iter} ({app_config.type}) ━━━[/bold cyan]"
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
                            progress_tracker.update(task_id, description=f"📦 Prepare {app_name_iter}")
                        else:
                            console.print(f"[cyan]📦 Step 1: Prepare {app_name_iter}[/cyan]")

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
                            progress_tracker.update(task_id, description=f"🔨 Build {app_name_iter}")
                        else:
                            console.print(
                                f"[cyan]🔨 Step {step_number}: Build {app_name_iter}[/cyan]"
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
                        progress_tracker.update(task_id, description=f"🚀 Deploy {app_name_iter}")
                    else:
                        console.print(
                            f"[cyan]🚀 Step {step_number}: Deploy {app_name_iter}[/cyan]"
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
                console.print("[cyan]🪝 Executing global post-apply hooks...[/cyan]")
                if not hook_executor.execute_command_hooks(
                    apply_hooks, "post", "apply"
                ):
                    console.print("[red]❌ Post-apply hook failed[/red]")
                    failed = True

        except Exception as e:
            failed = True
            # 글로벌 on_failure 훅 실행
            if config.hooks and "apply" in config.hooks:
                apply_hooks = config.hooks["apply"].model_dump()
                console.print(
                    "[yellow]🪝 Executing global on-failure hooks...[/yellow]"
                )
                hook_executor.execute_command_hooks(apply_hooks, "on_failure", "apply")
            overall_success = False
            # Note: Detailed error already printed by format_deployment_error in inner try-except
            # Just print summary here
            console.print(
                f"\n[red]━━━ App group '{APP_CONFIG_DIR.name}' 처리 실패 ━━━[/red]"
            )
            continue

        # 실패 시 on_failure 훅 실행
        if failed:
            if config.hooks and "apply" in config.hooks:
                apply_hooks = config.hooks["apply"].model_dump()
                console.print(
                    "[yellow]🪝 Executing global on-failure hooks...[/yellow]"
                )
                hook_executor.execute_command_hooks(apply_hooks, "on_failure", "apply")
            overall_success = False
            console.print(f"[red]❌ App group '{APP_CONFIG_DIR.name}' failed[/red]")
        else:
            console.print(
                f"[bold green]✅ App group '{APP_CONFIG_DIR.name}' applied successfully![/bold green]"
            )

    # 전체 결과
    if not overall_success:
        console.print("\n[bold red]❌ Some app groups failed to apply[/bold red]")
        raise click.Abort()
    else:
        console.print(
            "\n[bold green]🎉 All app groups applied successfully![/bold green]"
        )
