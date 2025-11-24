"""SBKube template 명령어.

빌드된 Helm 차트를 YAML로 렌더링:
- build/ 디렉토리의 차트를 helm template으로 렌더링
- 렌더링된 YAML을 rendered/ 디렉토리에 저장
- 배포 전 미리보기 및 CI/CD 검증용
"""

import shutil
from pathlib import Path

import click

from sbkube.models.config_model import HelmApp, HookApp, HttpApp, SBKubeConfig, YamlApp
from sbkube.utils.app_dir_resolver import resolve_app_dirs
from sbkube.utils.common import run_command
from sbkube.utils.file_loader import load_config_file
from sbkube.utils.hook_executor import HookExecutor
from sbkube.utils.manifest_cleaner import clean_manifest_metadata
from sbkube.utils.output_manager import OutputManager


def template_helm_app(
    app_name: str,
    app: HelmApp,
    base_dir: Path,
    charts_dir: Path,
    build_dir: Path,
    app_config_dir: Path,
    rendered_dir: Path,
    output: OutputManager,
    cluster_global_values: dict | None = None,
    cleanup_metadata: bool = True,
) -> bool:
    """Helm 앱을 YAML로 렌더링 (helm template).

    Args:
        app_name: 앱 이름
        app: HelmApp 설정
        base_dir: 프로젝트 루트
        charts_dir: charts 디렉토리
        build_dir: build 디렉토리
        app_config_dir: 앱 설정 디렉토리
        rendered_dir: 렌더링 결과 디렉토리
        output: OutputManager instance
        cluster_global_values: 클러스터 전역 values (선택, v0.7.0+)
        cleanup_metadata: 서버 관리 메타데이터 자동 제거 여부 (기본: True, v0.7.0+)

    Returns:
        성공 여부

    """
    output.print(f"[cyan]📄 Rendering Helm app: {app_name}[/cyan]", level="info")

    # 1. 차트 경로 결정 (build/ 우선, 없으면 charts/ 또는 로컬)
    chart_path = None

    # build/ 디렉토리 확인
    build_path = build_dir / app_name
    if build_path.exists() and build_path.is_dir():
        chart_path = build_path
        output.print(f"  Using built chart: {chart_path}", level="info")
    # build 없으면 원본 차트 사용 (v0.8.0+ path structure)
    elif app.is_remote_chart():
        source_path = app.get_chart_path(charts_dir)
        if source_path and source_path.exists():
            chart_path = source_path
            output.print(f"  Using remote chart: {chart_path}", level="info")
    else:
        # 로컬 차트
        if app.chart.startswith("./"):
            source_path = app_config_dir / app.chart[2:]
        elif app.chart.startswith("/"):
            source_path = Path(app.chart)
        else:
            source_path = app_config_dir / app.chart

        if source_path.exists():
            chart_path = source_path
            output.print(f"  Using local chart: {chart_path}", level="info")

    if not chart_path or not chart_path.exists():
        output.print_error(
            f"Chart not found for app: {app_name}",
            app_name=app_name,
        )
        output.print_warning("Run 'sbkube prepare' and 'sbkube build' first")
        return False

    # 2. helm template 명령어 구성
    release_name = app.release_name or app_name
    helm_cmd = ["helm", "template", release_name, str(chart_path)]

    # 네임스페이스 추가
    if app.namespace:
        helm_cmd.extend(["--namespace", app.namespace])

    # 클러스터 전역 values 추가 (v0.7.0+, 최하위 우선순위)
    import tempfile

    temp_cluster_values_file = None
    if cluster_global_values:
        import yaml

        output.print("  Applying cluster global values...", level="info")
        # 임시 파일에 cluster global values 저장
        temp_cluster_values_file = tempfile.NamedTemporaryFile(
            mode="w", suffix=".yaml", delete=False, encoding="utf-8"
        )
        yaml.dump(
            cluster_global_values, temp_cluster_values_file, default_flow_style=False
        )
        temp_cluster_values_file.close()
        helm_cmd.extend(["--values", temp_cluster_values_file.name])
        output.print(
            f"    ✓ cluster global values ({len(cluster_global_values)} keys)",
            level="info",
        )

    # values 파일 추가
    if app.values:
        output.print(f"  Applying {len(app.values)} values files...", level="info")
        for values_file in app.values:
            values_path = app_config_dir / values_file
            if values_path.exists():
                helm_cmd.extend(["--values", str(values_path)])
                output.print(f"    ✓ {values_file}", level="info")
            else:
                output.print_warning(f"Values file not found: {values_file}")

    # --set 옵션 추가
    if app.set_values:
        output.print(f"  Applying {len(app.set_values)} set values...", level="info")
        for key, value in app.set_values.items():
            helm_cmd.extend(["--set", f"{key}={value}"])
            output.print(f"    ✓ {key}={value}", level="info")

    # 3. helm template 실행
    output.print(f"  $ {' '.join(helm_cmd)}", level="info")
    try:
        return_code, stdout, stderr = run_command(helm_cmd, check=False, timeout=60)

        if return_code != 0:
            output.print_error(
                f"helm template failed (exit code: {return_code})",
                exit_code=return_code,
            )
            if stdout:
                output.print(f"  [blue]STDOUT:[/blue] {stdout.strip()}", level="error")
            if stderr:
                output.print(f"  [red]STDERR:[/red] {stderr.strip()}", level="error")
            return False

        # 4. 렌더링된 YAML 정리 (managedFields 등 제거)
        if cleanup_metadata:
            cleaned_yaml = clean_manifest_metadata(stdout)
            output.print("  🧹 Cleaned server-managed metadata fields", level="info")
        else:
            cleaned_yaml = stdout
            output.print("  ⏭️  Skipped metadata cleanup (disabled)", level="info")

        # 5. 렌더링된 YAML 저장
        output_file = rendered_dir / f"{app_name}.yaml"
        output_file.write_text(cleaned_yaml, encoding="utf-8")
        output.print_success(f"Rendered YAML saved: {output_file}")
        return True

    except Exception as e:
        output.print_error(f"Template rendering failed: {e}", error=str(e))
        import traceback

        output.print(f"[grey]{traceback.format_exc()}[/grey]", level="error")
        return False
    finally:
        # 임시 파일 정리
        if temp_cluster_values_file:
            import os

            try:
                os.unlink(temp_cluster_values_file.name)
            except Exception:
                pass  # 정리 실패해도 무시


def template_yaml_app(
    app_name: str,
    app: YamlApp,
    base_dir: Path,
    build_dir: Path,
    app_config_dir: Path,
    rendered_dir: Path,
    output: OutputManager,
    cleanup_metadata: bool = True,
) -> bool:
    """YAML 앱 렌더링 (빌드 디렉토리에서 복사).

    Args:
        app_name: 앱 이름
        app: YamlApp 설정
        base_dir: 프로젝트 루트
        build_dir: build 디렉토리
        app_config_dir: 앱 설정 디렉토리
        rendered_dir: 렌더링 결과 디렉토리
        output: OutputManager instance
        cleanup_metadata: 서버 관리 메타데이터 자동 제거 여부 (기본: True, v0.7.0+)

    Returns:
        성공 여부

    """
    output.print(f"[cyan]📄 Rendering YAML app: {app_name}[/cyan]", level="info")

    # build/ 디렉토리에서 YAML 파일 찾기
    build_path = build_dir / app_name

    if not build_path.exists():
        output.print_warning("Build directory not found, using original files")
        # build 없으면 원본 파일 사용
        combined_content = ""
        for file_rel_path in app.manifests:
            file_path = app_config_dir / file_rel_path
            if file_path.exists():
                content = file_path.read_text(encoding="utf-8")
                if combined_content:
                    combined_content += "\n---\n"
                combined_content += content
                output.print(f"  ✓ {file_rel_path}", level="info")
            else:
                output.print_warning(f"File not found: {file_rel_path}")
    else:
        # build 디렉토리의 모든 YAML 파일 결합
        yaml_files = list(build_path.glob("*.yaml")) + list(build_path.glob("*.yml"))
        if not yaml_files:
            output.print_error(
                f"No YAML files found in: {build_path}",
                build_path=str(build_path),
            )
            return False

        combined_content = ""
        for yaml_file in yaml_files:
            content = yaml_file.read_text(encoding="utf-8")
            if combined_content:
                combined_content += "\n---\n"
            combined_content += content
            output.print(f"  ✓ {yaml_file.name}", level="info")

    if combined_content:
        # Clean server-managed metadata fields
        if cleanup_metadata:
            cleaned_content = clean_manifest_metadata(combined_content)
            output.print("  🧹 Cleaned server-managed metadata fields", level="info")
        else:
            cleaned_content = combined_content
            output.print("  ⏭️  Skipped metadata cleanup (disabled)", level="info")

        output_file = rendered_dir / f"{app_name}.yaml"
        output_file.write_text(cleaned_content, encoding="utf-8")
        output.print_success(f"Rendered YAML saved: {output_file}")
        return True

    output.print_error("No content to render")
    return False


def template_http_app(
    app_name: str,
    app: HttpApp,
    base_dir: Path,
    build_dir: Path,
    app_config_dir: Path,
    rendered_dir: Path,
    output: OutputManager,
    cleanup_metadata: bool = True,
) -> bool:
    """HTTP 앱 렌더링 (다운로드된 파일 복사).

    Args:
        app_name: 앱 이름
        app: HttpApp 설정
        base_dir: 프로젝트 루트
        build_dir: build 디렉토리
        app_config_dir: 앱 설정 디렉토리
        rendered_dir: 렌더링 결과 디렉토리
        output: OutputManager instance
        cleanup_metadata: 서버 관리 메타데이터 자동 제거 여부 (기본: True, v0.7.0+)

    Returns:
        성공 여부

    """
    output.print(f"[cyan]📄 Rendering HTTP app: {app_name}[/cyan]", level="info")

    # build/ 디렉토리에서 파일 찾기
    build_path = build_dir / app_name

    if build_path.exists() and build_path.is_dir():
        # build 디렉토리의 파일 복사
        source_files = list(build_path.glob("*"))
        if not source_files:
            output.print_error(
                f"No files found in: {build_path}",
                build_path=str(build_path),
            )
            return False

        for source_file in source_files:
            if source_file.is_file():
                dest_file = rendered_dir / f"{app_name}-{source_file.name}"

                # Clean YAML files before copying
                if source_file.suffix in [".yaml", ".yml"]:
                    content = source_file.read_text(encoding="utf-8")
                    if cleanup_metadata:
                        cleaned_content = clean_manifest_metadata(content)
                        dest_file.write_text(cleaned_content, encoding="utf-8")
                        output.print(
                            f"  ✓ {source_file.name} → {dest_file.name} (cleaned)",
                            level="info",
                        )
                    else:
                        dest_file.write_text(content, encoding="utf-8")
                        output.print(
                            f"  ✓ {source_file.name} → {dest_file.name}",
                            level="info",
                        )
                else:
                    shutil.copy2(source_file, dest_file)
                    output.print(f"  ✓ {source_file.name} → {dest_file.name}", level="info")

        if cleanup_metadata:
            output.print("  🧹 Cleaned YAML manifests", level="info")
        else:
            output.print("  ⏭️  Skipped metadata cleanup (disabled)", level="info")
        output.print_success("HTTP app files copied")
        return True
    # build 없으면 원본 다운로드 파일 사용
    source_file = app_config_dir / app.dest

    if not source_file.exists():
        output.print_error(
            f"Downloaded file not found: {source_file}",
            file=str(source_file),
        )
        output.print_warning("Run 'sbkube prepare' first")
        return False

    dest_file = rendered_dir / f"{app_name}-{source_file.name}"

    # Clean YAML files before copying
    if source_file.suffix in [".yaml", ".yml"]:
        content = source_file.read_text(encoding="utf-8")
        if cleanup_metadata:
            cleaned_content = clean_manifest_metadata(content)
            dest_file.write_text(cleaned_content, encoding="utf-8")
            output.print("  🧹 Cleaned server-managed metadata fields", level="info")
            output.print_success(f"HTTP app file copied (cleaned): {dest_file}")
        else:
            dest_file.write_text(content, encoding="utf-8")
            output.print("  ⏭️  Skipped metadata cleanup (disabled)", level="info")
            output.print_success(f"HTTP app file copied: {dest_file}")
    else:
        shutil.copy2(source_file, dest_file)
        output.print_success(f"HTTP app file copied: {dest_file}")

    return True


@click.command(name="template")
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
    "--output-dir",
    "output_dir_name",
    default=None,
    help="렌더링된 YAML을 저장할 디렉토리 경로 (기본값: BASE_DIR/.sbkube/rendered)",
)
@click.option(
    "--app",
    "app_name",
    default=None,
    help="렌더링할 특정 앱 이름 (지정하지 않으면 모든 앱 렌더링)",
)
@click.option(
    "--dry-run",
    is_flag=True,
    default=False,
    help="Dry-run 모드 (훅 실행 시뮬레이션)",
)
@click.pass_context
def cmd(
    ctx: click.Context,
    app_config_dir_name: str | None,
    base_dir: str,
    config_file_name: str,
    sources_file_name: str,
    output_dir_name: str,
    app_name: str | None,
    dry_run: bool,
) -> None:
    """SBKube template 명령어.

    빌드된 차트를 YAML로 렌더링:
    - .sbkube/build/ 디렉토리의 차트를 helm template으로 렌더링
    - 렌더링된 YAML을 .sbkube/rendered/ 디렉토리에 저장
    - 배포 전 미리보기 및 CI/CD 검증용
    """
    # Initialize OutputManager
    output_format = ctx.obj.get("format", "human")
    output = OutputManager(format_type=output_format)

    output.print("[bold blue]✨ SBKube `template` 시작 ✨[/bold blue]", level="info")

    if dry_run:
        output.print("[yellow]🔍 Dry-run mode enabled[/yellow]", level="info")

    # 경로 설정
    BASE_DIR = Path(base_dir).resolve()

    # 앱 그룹 디렉토리 결정 (공통 유틸리티 사용)
    try:
        app_config_dirs = resolve_app_dirs(
            BASE_DIR, app_config_dir_name, config_file_name, sources_file_name
        )
    except ValueError:
        raise click.Abort

    # Find sources.yaml to determine .sbkube location
    # (준비 단계와 동일한 로직: sources.yaml 위치 기준)
    sources_file_path = None
    if app_config_dirs:
        # Start from first app config dir and search upwards
        search_dir = app_config_dirs[0]
        while search_dir != search_dir.parent:
            candidate = search_dir / sources_file_name
            if candidate.exists():
                sources_file_path = candidate
                break
            search_dir = search_dir.parent

    # .sbkube 작업 디렉토리는 sources.yaml이 있는 위치 기준
    # (prepare, build 명령어와 동일한 로직)
    if sources_file_path:
        SOURCES_BASE_DIR = sources_file_path.parent
        SBKUBE_WORK_DIR = SOURCES_BASE_DIR / ".sbkube"
    else:
        # Fallback to BASE_DIR if sources.yaml not found
        SBKUBE_WORK_DIR = BASE_DIR / ".sbkube"

    CHARTS_DIR = SBKUBE_WORK_DIR / "charts"
    BUILD_DIR = SBKUBE_WORK_DIR / "build"

    # rendered 디렉토리 결정
    if output_dir_name:
        # 사용자가 명시적으로 지정한 경우
        output_path = Path(output_dir_name)
        if output_path.is_absolute():
            RENDERED_DIR = output_path
        else:
            RENDERED_DIR = BASE_DIR / output_path
    else:
        # 기본값: .sbkube/rendered/
        RENDERED_DIR = SBKUBE_WORK_DIR / "rendered"

    # rendered 디렉토리 생성
    RENDERED_DIR.mkdir(parents=True, exist_ok=True)
    output.print(f"[cyan]📁 Output directory: {RENDERED_DIR}[/cyan]", level="info")

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
        config_data = load_config_file(config_file_path)

        try:
            config = SBKubeConfig(**config_data)
        except Exception as e:
            output.print_error(f"Invalid config file: {e}", error=str(e))
            overall_success = False
            continue

        # sources.yaml 로드 (cluster global values + cleanup_metadata용, v0.7.0+)
        cluster_global_values = None
        cleanup_metadata = True  # Default value
        sources_file_path = APP_CONFIG_DIR / "sources.yaml"
        if sources_file_path.exists():
            try:
                from sbkube.models.sources_model import SourceScheme

                sources_data = load_config_file(sources_file_path)
                sources = SourceScheme(**sources_data)
                cluster_global_values = sources.get_merged_global_values(
                    sources_dir=APP_CONFIG_DIR
                )
                cleanup_metadata = sources.cleanup_metadata  # Get cleanup_metadata setting
                if cluster_global_values:
                    output.print(
                        "[cyan]🌐 Loaded cluster global values from sources.yaml[/cyan]",
                        level="info",
                    )
                if not cleanup_metadata:
                    output.print(
                        "[yellow]⚠️  Manifest metadata cleanup is disabled[/yellow]",
                        level="warning",
                    )
            except Exception as e:
                output.print_warning(f"Failed to load cluster global values: {e}")

        # Hook executor 초기화
        hook_executor = HookExecutor(
            base_dir=BASE_DIR,
            work_dir=APP_CONFIG_DIR,  # 훅은 APP_CONFIG_DIR에서 실행
            dry_run=dry_run,
        )

        # 글로벌 pre-template 훅 실행
        if config.hooks and "template" in config.hooks:
            template_hooks = config.hooks["template"].model_dump()
            output.print(
                "[cyan]🪝 Executing global pre-template hooks...[/cyan]", level="info"
            )
            if not hook_executor.execute_command_hooks(
                template_hooks, "pre", "template"
            ):
                output.print_error("Pre-template hook failed")
                overall_success = False
                continue

        # 배포 순서 얻기 (의존성 고려)
        deployment_order = config.get_deployment_order()

        if app_name:
            # 특정 앱만 렌더링
            if app_name not in config.apps:
                output.print_error(f"App not found: {app_name}", app_name=app_name)
                overall_success = False
                continue
            apps_to_template = [app_name]
        else:
            # 모든 앱 렌더링 (의존성 순서대로)
            apps_to_template = deployment_order

        # 앱 렌더링
        success_count = 0
        total_count = len(apps_to_template)
        failed = False

        try:
            for app_name_iter in apps_to_template:
                app = config.apps[app_name_iter]

                if not app.enabled:
                    output.print(
                        f"[yellow]⏭️  Skipping disabled app: {app_name_iter}[/yellow]",
                        level="info",
                    )
                    continue

                # 앱별 pre-template 훅 실행
                if hasattr(app, "hooks") and app.hooks:
                    output.print(
                        f"[cyan]🪝 Executing pre-template hook for {app_name_iter}...[/cyan]",
                        level="info",
                    )
                    if not hook_executor.execute_app_hook(
                        app_name_iter,
                        app.hooks.model_dump() if app.hooks else None,
                        "pre_template",
                        context={"namespace": config.namespace},
                    ):
                        output.print_error(
                            f"Pre-template hook failed for {app_name_iter}",
                            app_name=app_name_iter,
                        )
                        failed = True
                        break

                success = False

                if isinstance(app, HookApp):
                    # HookApp은 template 단계 불필요 (deploy 시에만 실행)
                    output.print(
                        f"[yellow]⏭️  HookApp does not support template: {app_name_iter}[/yellow]",
                        level="info",
                    )
                    success = True
                elif isinstance(app, HelmApp):
                    success = template_helm_app(
                        app_name_iter,
                        app,
                        BASE_DIR,
                        CHARTS_DIR,
                        BUILD_DIR,
                        APP_CONFIG_DIR,
                        RENDERED_DIR,
                        output,
                        cluster_global_values=cluster_global_values,
                        cleanup_metadata=cleanup_metadata,
                    )
                elif isinstance(app, YamlApp):
                    success = template_yaml_app(
                        app_name_iter,
                        app,
                        BASE_DIR,
                        BUILD_DIR,
                        APP_CONFIG_DIR,
                        RENDERED_DIR,
                        output,
                        cleanup_metadata=cleanup_metadata,
                    )
                elif isinstance(app, HttpApp):
                    success = template_http_app(
                        app_name_iter,
                        app,
                        BASE_DIR,
                        BUILD_DIR,
                        APP_CONFIG_DIR,
                        RENDERED_DIR,
                        output,
                        cleanup_metadata=cleanup_metadata,
                    )
                else:
                    output.print(
                        f"[yellow]⏭️  App type '{app.type}' does not support template: {app_name_iter}[/yellow]",
                        level="info",
                    )
                    success = True  # 건너뛰어도 성공으로 간주

                if not success:
                    failed = True
                    # 앱별 on_template_failure 훅 실행
                    if hasattr(app, "hooks") and app.hooks:
                        output.print(
                            f"[yellow]🪝 Executing on-failure hook for {app_name_iter}...[/yellow]",
                            level="warning",
                        )
                        hook_executor.execute_app_hook(
                            app_name_iter,
                            app.hooks.model_dump() if app.hooks else None,
                            "on_template_failure",
                            context={"namespace": config.namespace},
                        )
                    break

                # 앱별 post-template 훅 실행
                if hasattr(app, "hooks") and app.hooks:
                    output.print(
                        f"[cyan]🪝 Executing post-template hook for {app_name_iter}...[/cyan]",
                        level="info",
                    )
                    if not hook_executor.execute_app_hook(
                        app_name_iter,
                        app.hooks.model_dump() if app.hooks else None,
                        "post_template",
                        context={"namespace": config.namespace},
                    ):
                        output.print_error(
                            f"Post-template hook failed for {app_name_iter}",
                            app_name=app_name_iter,
                        )
                        failed = True
                        break

                if success:
                    success_count += 1

            # 글로벌 post-template 훅 실행 (성공 시에만)
            if not failed and config.hooks and "template" in config.hooks:
                template_hooks = config.hooks["template"].model_dump()
                output.print(
                    "[cyan]🪝 Executing global post-template hooks...[/cyan]",
                    level="info",
                )
                if not hook_executor.execute_command_hooks(
                    template_hooks, "post", "template"
                ):
                    output.print_error("Post-template hook failed")
                    failed = True

        except Exception:
            # 글로벌 on_failure 훅 실행
            if config.hooks and "template" in config.hooks:
                template_hooks = config.hooks["template"].model_dump()
                output.print(
                    "[yellow]🪝 Executing global on-failure hooks...[/yellow]",
                    level="warning",
                )
                hook_executor.execute_command_hooks(
                    template_hooks, "on_failure", "template"
                )
            failed = True

        # 실패 시 on_failure 훅 실행
        if failed and config.hooks and "template" in config.hooks:
            template_hooks = config.hooks["template"].model_dump()
            output.print(
                "[yellow]🪝 Executing global on-failure hooks...[/yellow]",
                level="warning",
            )
            hook_executor.execute_command_hooks(
                template_hooks, "on_failure", "template"
            )

        # 이 앱 그룹 결과 출력
        output.print_success(
            f"App group '{APP_CONFIG_DIR.name}' templated: {success_count}/{total_count} apps",
            app_group=APP_CONFIG_DIR.name,
            success_count=success_count,
            total_count=total_count,
        )
        output.print(
            f"[cyan]📁 Rendered files saved to: {RENDERED_DIR}[/cyan]", level="info"
        )

        if success_count < total_count or failed:
            overall_success = False

    # 전체 결과
    if not overall_success:
        output.print(
            "\n[bold red]❌ Some app groups failed to template[/bold red]",
            level="error",
        )
        output.finalize(
            status="failed",
            summary={
                "app_groups_processed": len(app_config_dirs),
                "status": "failed",
            },
            next_steps=[
                "Check error messages and fix configuration",
                "Verify chart paths and values files",
            ],
            errors=["Some app groups failed to template"],
        )
        raise click.Abort
    output.print(
        "\n[bold green]🎉 All app groups templated successfully![/bold green]",
        level="success",
    )
    output.finalize(
        status="success",
        summary={
            "app_groups_processed": len(app_config_dirs),
            "rendered_files": str(RENDERED_DIR),
            "status": "success",
        },
        next_steps=[
            f"Review rendered files: ls {RENDERED_DIR}",
            f"Deploy with: sbkube deploy --app-dir {app_config_dirs[0].name}",
        ],
    )
