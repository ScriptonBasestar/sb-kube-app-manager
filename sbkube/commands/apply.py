"""
SBKube apply 명령어.

통합 명령어: prepare → deploy를 자동으로 실행.
의존성을 고려하여 올바른 순서로 배포합니다.
"""

from pathlib import Path

import click
from rich.console import Console

from sbkube.models.config_model import SBKubeConfig
from sbkube.utils.file_loader import load_config_file

console = Console()


@click.command(name="apply")
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
@click.pass_context
def cmd(
    ctx: click.Context,
    app_config_dir_name: str,
    base_dir: str,
    config_file_name: str,
    sources_file_name: str,
    app_name: str | None,
    dry_run: bool,
    skip_prepare: bool,
    skip_build: bool,
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

    # 경로 설정
    BASE_DIR = Path(base_dir).resolve()
    APP_CONFIG_DIR = BASE_DIR / app_config_dir_name
    config_file_path = APP_CONFIG_DIR / config_file_name

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
            raise click.Abort()

        # 의존성 체크: 해당 앱이 의존하는 앱들도 함께 배포해야 함
        apps_to_apply = []
        visited = set()

        def collect_dependencies(name: str):
            if name in visited:
                return
            visited.add(name)

            app_cfg = config.apps[name]
            if hasattr(app_cfg, "depends_on"):
                for dep in app_cfg.depends_on:
                    collect_dependencies(dep)

            apps_to_apply.append(name)

        collect_dependencies(app_name)
        console.print(f"\n[yellow]ℹ️  Including dependencies: {', '.join(apps_to_apply)}[/yellow]")
    else:
        apps_to_apply = deployment_order

    # Step 1: Prepare
    if not skip_prepare:
        console.print("\n[bold cyan]📦 Step 1: Prepare[/bold cyan]")

        from sbkube.commands.prepare import cmd as prepare_cmd

        # Create new context with parent's obj for kubeconfig/context/sources_file
        prepare_ctx = click.Context(prepare_cmd, parent=ctx)
        prepare_ctx.obj = ctx.obj  # Pass parent context object
        prepare_ctx.invoke(
            prepare_cmd,
            app_config_dir_name=app_config_dir_name,
            base_dir=base_dir,
            config_file_name=config_file_name,
            sources_file_name=sources_file_name,
            app_name=None,  # prepare all (의존성 때문에)
            force=False,
            dry_run=dry_run,
        )
    else:
        console.print("\n[yellow]⏭️  Skipping prepare step[/yellow]")

    # Step 2: Build
    if not skip_build:
        console.print("\n[bold cyan]🔨 Step 2: Build[/bold cyan]")

        from sbkube.commands.build import cmd as build_cmd

        # Create new context with parent's obj
        build_ctx = click.Context(build_cmd, parent=ctx)
        build_ctx.obj = ctx.obj  # Pass parent context object
        build_ctx.invoke(
            build_cmd,
            app_config_dir_name=app_config_dir_name,
            base_dir=base_dir,
            config_file_name=config_file_name,
            app_name=None,  # build all
            dry_run=dry_run,
        )
    else:
        console.print("\n[yellow]⏭️  Skipping build step[/yellow]")

    # Step 3: Deploy
    console.print("\n[bold cyan]🚀 Step 3: Deploy[/bold cyan]")

    from sbkube.commands.deploy import cmd as deploy_cmd

    # Create new context with parent's obj for kubeconfig/context/sources_file
    deploy_ctx = click.Context(deploy_cmd, parent=ctx)
    deploy_ctx.obj = ctx.obj  # Pass parent context object
    deploy_ctx.invoke(
        deploy_cmd,
        app_config_dir_name=app_config_dir_name,
        base_dir=base_dir,
        config_file_name=config_file_name,
        app_name=None if not app_name else app_name,  # 지정한 앱만
        dry_run=dry_run,
    )

    # 완료
    console.print("\n[bold green]🎉 Apply completed successfully![/bold green]")
