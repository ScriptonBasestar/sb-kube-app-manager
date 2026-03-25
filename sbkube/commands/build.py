"""SBKube build 명령어.

빌드 디렉토리 준비 + 커스터마이징:
- Remote chart: charts/ → build/ 복사
- Local chart: app_dir 기준 경로 → build/ 복사
- Overrides 적용: overrides/<app-name>/* → build/<app-name>/*
- Removes 적용: build/<app-name>/<remove-pattern> 삭제
"""

import shutil
from pathlib import Path

import click

from sbkube.models.config_model import HelmApp, HookApp, HttpApp, SBKubeConfig
from sbkube.utils.app_dir_resolver import resolve_app_dirs
from sbkube.utils.chart_path_resolver import (
    resolve_local_chart_path,
    resolve_remote_chart_path,
)
from sbkube.utils.common_options import resolve_command_paths, target_options
from sbkube.utils.file_loader import load_config_file
from sbkube.utils.global_options import global_options
from sbkube.utils.hook_helpers import (
    create_hook_executor,
    execute_app_post_hook,
    execute_app_pre_hook,
    execute_global_post_hook,
    execute_global_pre_hook,
)
from sbkube.utils.output_manager import OutputManager
from sbkube.utils.workspace_resolver import resolve_sbkube_directories


def build_helm_app(
    app_name: str,
    app: HelmApp,
    base_dir: Path,
    charts_dir: Path,
    build_dir: Path,
    app_config_dir: Path,
    output: OutputManager,
    dry_run: bool = False,
) -> bool:
    """Helm 앱 빌드 + 커스터마이징.

    Args:
        app_name: 앱 이름
        app: HelmApp 설정
        base_dir: 프로젝트 루트
        charts_dir: charts 디렉토리
        build_dir: build 디렉토리
        app_config_dir: 앱 설정 디렉토리
        output: OutputManager instance
        dry_run: dry-run 모드 (실제 파일 복사/수정하지 않음)

    Returns:
        성공 여부

    """
    output.print(f"[cyan]🔨 Building Helm app: {app_name}[/cyan]", level="info")

    # 1. 소스 차트 경로 결정 (Phase 2 refactoring: chart_path_resolver 사용)
    if app.is_remote_chart():
        # Remote chart: resolve using centralized utility
        chart_result = resolve_remote_chart_path(app, charts_dir, output)
        if not chart_result.found:
            return False
        source_path = chart_result.chart_path
    else:
        # Local chart: resolve using centralized utility
        chart_result = resolve_local_chart_path(app, app_config_dir, output)
        if not chart_result.found:
            return False
        source_path = chart_result.chart_path

    # 2. 빌드 디렉토리로 복사
    dest_path = build_dir / app_name

    if dry_run:
        output.print(
            f"[yellow]🔍 [DRY-RUN] Would copy chart: {source_path} → {dest_path}[/yellow]",
            level="info",
        )
        if dest_path.exists():
            output.print(
                "[yellow]🔍 [DRY-RUN] Would remove existing build directory[/yellow]",
                level="info",
            )
    else:
        # 기존 디렉토리 삭제
        if dest_path.exists():
            output.print(
                f"  Removing existing build directory: {dest_path}", level="info"
            )
            shutil.rmtree(dest_path)

        output.print(f"  Copying chart: {source_path} → {dest_path}", level="info")
        shutil.copytree(source_path, dest_path)

    # 3. Check for override directory and warn if not configured
    overrides_base = app_config_dir / "overrides" / app_name

    # 3.1. Warn if override directory exists but not configured
    if overrides_base.exists() and overrides_base.is_dir() and not app.overrides:
        output.print("", level="warning")
        output.print_warning(f"Override directory found but not configured: {app_name}")

        try:
            rel_path = overrides_base.relative_to(Path.cwd())
        except ValueError:
            rel_path = overrides_base

        output.print(f"[yellow]    Location: {rel_path}[/yellow]", level="warning")
        output.print("[yellow]    Files:[/yellow]", level="warning")

        # Show first few files
        override_files = [f for f in overrides_base.rglob("*") if f.is_file()]
        for f in override_files[:5]:
            rel_file_path = f.relative_to(overrides_base)
            output.print(f"[yellow]      - {rel_file_path}[/yellow]", level="warning")

        if len(override_files) > 5:
            output.print(
                f"[yellow]      ... and {len(override_files) - 5} more files[/yellow]",
                level="warning",
            )

        output.print(
            "[yellow]    💡 To apply these overrides, add to config.yaml:[/yellow]",
            level="warning",
        )
        output.print(f"[yellow]       {app_name}:[/yellow]", level="warning")
        output.print("[yellow]         overrides:[/yellow]", level="warning")
        if override_files:
            # Show up to 3 files with full path mapping explanation
            for i, f in enumerate(override_files[:3]):
                rel_file_path = f.relative_to(overrides_base)
                output.print(
                    f"[yellow]           - {rel_file_path}[/yellow]", level="warning"
                )
                if i == 0:
                    output.print(
                        f"[dim yellow]             # → build/{app_name}/{rel_file_path}[/dim yellow]",
                        level="warning",
                    )
            if len(override_files) > 3:
                output.print(
                    f"[yellow]           # ... and {len(override_files) - 3} more[/yellow]",
                    level="warning",
                )
        output.print("", level="warning")

    # 3.2. Apply overrides if configured
    if app.overrides:
        output.print(
            f"  Processing {len(app.overrides)} override patterns...", level="info"
        )

        if not overrides_base.exists():
            output.print_warning(f"Overrides directory not found: {overrides_base}")
        else:
            total_files_copied = 0

            for override_pattern in app.overrides:
                # Check if pattern contains glob wildcards
                if "*" in override_pattern or "?" in override_pattern:
                    # Glob pattern - match multiple files
                    matched_files = list(overrides_base.glob(override_pattern))

                    if not matched_files:
                        output.print_warning(
                            f"    No files matched pattern: {override_pattern}"
                        )
                        continue

                    output.print(
                        f"    Pattern '{override_pattern}' matched {len(matched_files)} files",
                        level="info",
                    )

                    for src_file in matched_files:
                        if src_file.is_file():
                            # Calculate relative path from overrides_base
                            override_rel_path = src_file.relative_to(overrides_base)
                            dst_file = dest_path / override_rel_path

                            # Create destination directory
                            if dry_run:
                                output.print(
                                    f"[yellow]      🔍 [DRY-RUN] Would override: {override_rel_path}[/yellow]",
                                    level="info",
                                )
                            else:
                                dst_file.parent.mkdir(parents=True, exist_ok=True)
                                shutil.copy2(src_file, dst_file)
                                output.print(
                                    f"      ✓ {override_rel_path}", level="info"
                                )
                                total_files_copied += 1
                else:
                    # Exact file path - existing behavior
                    src_file = overrides_base / override_pattern
                    dst_file = dest_path / override_pattern

                    if src_file.exists() and src_file.is_file():
                        if dry_run:
                            output.print(
                                f"[yellow]    🔍 [DRY-RUN] Would override: {override_pattern}[/yellow]",
                                level="info",
                            )
                        else:
                            # 대상 디렉토리 생성
                            dst_file.parent.mkdir(parents=True, exist_ok=True)
                            shutil.copy2(src_file, dst_file)
                            output.print(
                                f"    ✓ Override: {override_pattern}", level="info"
                            )
                            total_files_copied += 1
                    else:
                        output.print_warning(f"    Override file not found: {src_file}")

            if total_files_copied > 0:
                output.print(
                    f"  Total files copied: {total_files_copied}", level="info"
                )

    # 4. Removes 적용
    if app.removes:
        output.print(f"  Removing {len(app.removes)} patterns...", level="info")
        for remove_pattern in app.removes:
            remove_target = dest_path / remove_pattern

            if dry_run:
                if remove_target.exists():
                    if remove_target.is_dir():
                        output.print(
                            f"[yellow]    🔍 [DRY-RUN] Would remove directory: {remove_pattern}[/yellow]",
                            level="info",
                        )
                    elif remove_target.is_file():
                        output.print(
                            f"[yellow]    🔍 [DRY-RUN] Would remove file: {remove_pattern}[/yellow]",
                            level="info",
                        )
                else:
                    output.print_warning(
                        f"    Remove target not found: {remove_pattern}"
                    )
            elif remove_target.exists():
                if remove_target.is_dir():
                    shutil.rmtree(remove_target)
                    output.print(
                        f"    ✓ Removed directory: {remove_pattern}", level="info"
                    )
                elif remove_target.is_file():
                    remove_target.unlink()
                    output.print(f"    ✓ Removed file: {remove_pattern}", level="info")
            else:
                output.print_warning(f"    Remove target not found: {remove_pattern}")

    output.print_success(f"Helm app built: {app_name}")
    return True


def build_http_app(
    app_name: str,
    app: HttpApp,
    base_dir: Path,
    build_dir: Path,
    app_config_dir: Path,
    output: OutputManager,
    dry_run: bool = False,
) -> bool:
    """HTTP 앱 빌드 (다운로드된 파일을 build/로 복사).

    Args:
        app_name: 앱 이름
        app: HttpApp 설정
        base_dir: 프로젝트 루트
        build_dir: build 디렉토리
        app_config_dir: 앱 설정 디렉토리
        output: OutputManager instance
        dry_run: dry-run 모드 (실제 파일 복사하지 않음)

    Returns:
        성공 여부

    """
    output.print(f"[cyan]🔨 Building HTTP app: {app_name}[/cyan]", level="info")

    # 다운로드된 파일 위치 (prepare 단계에서 생성됨)
    source_file = app_config_dir / app.dest

    if not source_file.exists():
        output.print_error(
            f"Downloaded file not found: {source_file}",
            file=str(source_file),
        )
        output.print_warning("Run 'sbkube prepare' first")
        return False

    # build/ 디렉토리로 복사
    dest_file = build_dir / app_name / source_file.name

    if dry_run:
        output.print(
            f"[yellow]🔍 [DRY-RUN] Would copy: {source_file} → {dest_file}[/yellow]",
            level="info",
        )
    else:
        dest_file.parent.mkdir(parents=True, exist_ok=True)
        output.print(f"  Copying: {source_file} → {dest_file}", level="info")
        shutil.copy2(source_file, dest_file)

    output.print_success(f"HTTP app built: {app_name}")
    return True


@click.command(name="build")
@target_options
@click.option(
    "--app",
    "app_name",
    default=None,
    help="빌드할 특정 앱 이름 (지정하지 않으면 모든 앱 빌드)",
)
@click.option(
    "--dry-run",
    is_flag=True,
    default=False,
    help="Dry-run 모드 (실제 파일 복사/수정하지 않음)",
)
@global_options
@click.pass_context
def cmd(
    ctx: click.Context,
    target: str | None,
    config_file: str | None,
    app_name: str | None,
    dry_run: bool,
) -> None:
    """SBKube build 명령어.

    빌드 디렉토리 준비 및 커스터마이징:
    - Remote chart를 charts/에서 build/로 복사
    - Overrides 적용 (overrides/<app-name>/* → build/<app-name>/*)
    - Removes 적용 (불필요한 파일/디렉토리 삭제)
    """
    # Use shared OutputManager from parent command, or create own if standalone
    shared_output = ctx.obj.get("output")
    output_format = ctx.obj.get("format", "human")
    output = shared_output or OutputManager(format_type=output_format)
    _is_standalone = shared_output is None

    output.print("[bold blue]✨ SBKube `build` 시작 ✨[/bold blue]", level="info")

    try:
        resolved_paths = resolve_command_paths(
            target=target,
            config_file=config_file,
            base_dir=".",
            app_config_dir_name=None,
            config_file_name="config.yaml",
            sources_file_name=ctx.obj.get("sources_file", "sources.yaml"),
        )
    except ValueError as e:
        output.print_error(str(e), error=str(e))
        raise click.Abort from e

    BASE_DIR = resolved_paths.base_dir
    app_config_dir_name = resolved_paths.app_config_dir_name
    config_file_name = resolved_paths.config_file_name
    sources_file_name = resolved_paths.sources_file_name

    # 앱 그룹 디렉토리 결정 (공통 유틸리티 사용)
    try:
        app_config_dirs = resolve_app_dirs(
            BASE_DIR, app_config_dir_name, config_file_name, sources_file_name,
            output=output,
        )
    except ValueError:
        raise click.Abort

    # Resolve .sbkube directories using centralized utility (Phase 2 refactoring)
    sbkube_dirs = resolve_sbkube_directories(
        BASE_DIR, app_config_dirs, sources_file_name
    )
    CHARTS_DIR = sbkube_dirs.charts_dir
    BUILD_DIR = sbkube_dirs.build_dir

    # 작업 디렉토리 생성
    sbkube_dirs.ensure_directories()

    # 각 앱 그룹 처리
    overall_success = True
    for APP_CONFIG_DIR in app_config_dirs:
        output.print_section(f"Processing app group: {APP_CONFIG_DIR.name}")

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
        raw_data = load_config_file(config_file_path)

        # 통합 sbkube.yaml 포맷 감지 (apiVersion이 sbkube/로 시작)
        api_version = raw_data.get("apiVersion", "") if raw_data else ""
        if api_version.startswith("sbkube/"):
            # 통합 포맷: apps와 namespace 추출
            apps_data = raw_data.get("apps", {})
            if not apps_data:
                output.print_warning(f"No apps found in: {config_file_path}")
                continue

            # namespace 상속 처리 (parent → current)
            merged_namespace = "default"
            current_dir = config_file_path.parent
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
                    if parent_data and parent_data.get("apiVersion", "").startswith("sbkube/"):
                        parent_ns = parent_data.get("settings", {}).get("namespace")
                        if parent_ns:
                            merged_namespace = parent_ns
                except Exception:
                    pass

            # 현재 config의 namespace로 오버라이드
            current_namespace = raw_data.get("settings", {}).get("namespace")
            if current_namespace:
                merged_namespace = current_namespace

            config_data = {"apps": apps_data, "namespace": merged_namespace}
        else:
            # 레거시 포맷: 전체 데이터가 SBKubeConfig
            config_data = raw_data

        try:
            config = SBKubeConfig(**config_data)
        except Exception as e:
            output.print_error(f"Invalid config file: {e}", error=str(e))
            overall_success = False
            continue

        # 배포 순서 얻기 (의존성 고려)
        deployment_order = config.get_deployment_order()

        if app_name:
            # 특정 앱만 빌드
            if app_name not in config.apps:
                output.print_error(f"App not found: {app_name}", app_name=app_name)
                overall_success = False
                continue
            apps_to_build = [app_name]
        else:
            # 모든 앱 빌드 (의존성 순서대로)
            apps_to_build = deployment_order

        # Hook executor 초기화 (Phase 3 refactoring: hook_helpers 사용)
        hook_executor = create_hook_executor(
            base_dir=BASE_DIR,
            work_dir=APP_CONFIG_DIR,
            dry_run=dry_run,
        )

        # ========== 전역 pre-build 훅 실행 ==========
        if not execute_global_pre_hook(hook_executor, config, "build", output):
            overall_success = False
            continue

        # 앱 빌드
        success_count = 0
        total_count = len(apps_to_build)
        build_failed = False

        for app_name_iter in apps_to_build:
            app = config.apps[app_name_iter]

            if not app.enabled:
                output.print(
                    f"[yellow]⏭️  Skipping disabled app: {app_name_iter}[/yellow]",
                    level="info",
                )
                continue

            # ========== 앱별 pre-build 훅 실행 (Phase 3 refactoring) ==========
            if not execute_app_pre_hook(hook_executor, app_name_iter, app, "build", output):
                build_failed = True
                continue

            success = False

            if isinstance(app, HookApp):
                # HookApp은 build 단계 불필요 (deploy 시에만 실행)
                output.print(
                    f"[yellow]⏭️  HookApp does not require build: {app_name_iter}[/yellow]",
                    level="info",
                )
                success = True
            elif isinstance(app, HelmApp):
                # Helm 앱만 빌드 (커스터마이징 필요)
                if app.overrides or app.removes or app.is_remote_chart():
                    success = build_helm_app(
                        app_name_iter,
                        app,
                        BASE_DIR,
                        CHARTS_DIR,
                        BUILD_DIR,
                        APP_CONFIG_DIR,
                        output,
                        dry_run,
                    )
                else:
                    output.print(
                        f"[yellow]⏭️  Skipping Helm app (no customization): {app_name_iter}[/yellow]",
                        level="info",
                    )
                    success = True  # 건너뛰어도 성공으로 간주
            elif isinstance(app, HttpApp):
                success = build_http_app(
                    app_name_iter,
                    app,
                    BASE_DIR,
                    BUILD_DIR,
                    APP_CONFIG_DIR,
                    output,
                    dry_run,
                )
            else:
                output.print(
                    f"[yellow]⏭️  App type '{app.type}' does not require build: {app_name_iter}[/yellow]",
                    level="info",
                )
                success = True  # 건너뛰어도 성공으로 간주

            # ========== 앱별 post-build 훅 실행 (Phase 3 refactoring) ==========
            if success:
                execute_app_post_hook(hook_executor, app_name_iter, app, "build")
            else:
                build_failed = True

            if success:
                success_count += 1
            else:
                build_failed = True

        # ========== 전역 post-build 훅 실행 (Phase 3 refactoring) ==========
        execute_global_post_hook(hook_executor, config, "build", failed=build_failed)

        # 이 앱 그룹 결과 출력
        output.print_success(
            f"App group '{APP_CONFIG_DIR.name}' built: {success_count}/{total_count} apps",
            app_group=APP_CONFIG_DIR.name,
            success_count=success_count,
            total_count=total_count,
        )

        if success_count < total_count:
            overall_success = False

    # 전체 결과
    if not overall_success:
        output.print(
            "\n[bold red]❌ Some app groups failed to build[/bold red]", level="error"
        )
        if _is_standalone:
            output.finalize(
                status="failed",
                summary={"app_groups_processed": len(app_config_dirs), "status": "failed"},
                next_steps=["Check error messages above and fix configuration"],
                errors=["Some apps failed to build"],
            )
        raise click.Abort
    output.print(
        "\n[bold green]🎉 All app groups built successfully![/bold green]",
        level="success",
    )
    if _is_standalone:
        output.finalize(
            status="success",
            summary={"app_groups_processed": len(app_config_dirs), "status": "success"},
            next_steps=["Run 'sbkube deploy' to deploy to cluster"],
        )
