"""
SBKube template 명령어.

빌드된 Helm 차트를 YAML로 렌더링:
- build/ 디렉토리의 차트를 helm template으로 렌더링
- 렌더링된 YAML을 rendered/ 디렉토리에 저장
- 배포 전 미리보기 및 CI/CD 검증용
"""

import shutil
from pathlib import Path

import click
from rich.console import Console

from sbkube.models.config_model import (HelmApp, HookApp, HttpApp,
                                        SBKubeConfig, YamlApp)
from sbkube.utils.app_dir_resolver import resolve_app_dirs
from sbkube.utils.common import run_command
from sbkube.utils.file_loader import load_config_file
from sbkube.utils.hook_executor import HookExecutor

console = Console()


def template_helm_app(
    app_name: str,
    app: HelmApp,
    base_dir: Path,
    charts_dir: Path,
    build_dir: Path,
    app_config_dir: Path,
    rendered_dir: Path,
) -> bool:
    """
    Helm 앱을 YAML로 렌더링 (helm template).

    Args:
        app_name: 앱 이름
        app: HelmApp 설정
        base_dir: 프로젝트 루트
        charts_dir: charts 디렉토리
        build_dir: build 디렉토리
        app_config_dir: 앱 설정 디렉토리
        rendered_dir: 렌더링 결과 디렉토리

    Returns:
        성공 여부
    """
    console.print(f"[cyan]📄 Rendering Helm app: {app_name}[/cyan]")

    # 1. 차트 경로 결정 (build/ 우선, 없으면 charts/ 또는 로컬)
    chart_path = None

    # build/ 디렉토리 확인
    build_path = build_dir / app_name
    if build_path.exists() and build_path.is_dir():
        chart_path = build_path
        console.print(f"  Using built chart: {chart_path}")
    else:
        # build 없으면 원본 차트 사용
        if app.is_remote_chart():
            chart_name = app.get_chart_name()
            source_path = charts_dir / chart_name / chart_name
            if source_path.exists():
                chart_path = source_path
                console.print(f"  Using remote chart: {chart_path}")
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
                console.print(f"  Using local chart: {chart_path}")

    if not chart_path or not chart_path.exists():
        console.print(f"[red]❌ Chart not found for app: {app_name}[/red]")
        console.print(
            "[yellow]💡 Run 'sbkube prepare' and 'sbkube build' first[/yellow]"
        )
        return False

    # 2. helm template 명령어 구성
    release_name = app.release_name or app_name
    helm_cmd = ["helm", "template", release_name, str(chart_path)]

    # 네임스페이스 추가
    if app.namespace:
        helm_cmd.extend(["--namespace", app.namespace])

    # values 파일 추가
    if app.values:
        console.print(f"  Applying {len(app.values)} values files...")
        for values_file in app.values:
            values_path = app_config_dir / values_file
            if values_path.exists():
                helm_cmd.extend(["--values", str(values_path)])
                console.print(f"    ✓ {values_file}")
            else:
                console.print(
                    f"[yellow]    ⚠️ Values file not found: {values_file}[/yellow]"
                )

    # --set 옵션 추가
    if app.set_values:
        console.print(f"  Applying {len(app.set_values)} set values...")
        for key, value in app.set_values.items():
            helm_cmd.extend(["--set", f"{key}={value}"])
            console.print(f"    ✓ {key}={value}")

    # 3. helm template 실행
    console.print(f"  $ {' '.join(helm_cmd)}")
    try:
        return_code, stdout, stderr = run_command(helm_cmd, check=False, timeout=60)

        if return_code != 0:
            console.print(
                f"[red]❌ helm template failed (exit code: {return_code})[/red]"
            )
            if stdout:
                console.print(f"  [blue]STDOUT:[/blue] {stdout.strip()}")
            if stderr:
                console.print(f"  [red]STDERR:[/red] {stderr.strip()}")
            return False

        # 4. 렌더링된 YAML 저장
        output_file = rendered_dir / f"{app_name}.yaml"
        output_file.write_text(stdout, encoding="utf-8")
        console.print(f"[green]✅ Rendered YAML saved: {output_file}[/green]")
        return True

    except Exception as e:
        console.print(f"[red]❌ Template rendering failed: {e}[/red]")
        import traceback

        console.print(f"[grey]{traceback.format_exc()}[/grey]")
        return False


def template_yaml_app(
    app_name: str,
    app: YamlApp,
    base_dir: Path,
    build_dir: Path,
    app_config_dir: Path,
    rendered_dir: Path,
) -> bool:
    """
    YAML 앱 렌더링 (빌드 디렉토리에서 복사).

    Args:
        app_name: 앱 이름
        app: YamlApp 설정
        base_dir: 프로젝트 루트
        build_dir: build 디렉토리
        app_config_dir: 앱 설정 디렉토리
        rendered_dir: 렌더링 결과 디렉토리

    Returns:
        성공 여부
    """
    console.print(f"[cyan]📄 Rendering YAML app: {app_name}[/cyan]")

    # build/ 디렉토리에서 YAML 파일 찾기
    build_path = build_dir / app_name

    if not build_path.exists():
        console.print(
            "[yellow]⚠️ Build directory not found, using original files[/yellow]"
        )
        # build 없으면 원본 파일 사용
        combined_content = ""
        for file_rel_path in app.files:
            file_path = app_config_dir / file_rel_path
            if file_path.exists():
                content = file_path.read_text(encoding="utf-8")
                if combined_content:
                    combined_content += "\n---\n"
                combined_content += content
                console.print(f"  ✓ {file_rel_path}")
            else:
                console.print(f"[yellow]  ⚠️ File not found: {file_rel_path}[/yellow]")
    else:
        # build 디렉토리의 모든 YAML 파일 결합
        yaml_files = list(build_path.glob("*.yaml")) + list(build_path.glob("*.yml"))
        if not yaml_files:
            console.print(f"[red]❌ No YAML files found in: {build_path}[/red]")
            return False

        combined_content = ""
        for yaml_file in yaml_files:
            content = yaml_file.read_text(encoding="utf-8")
            if combined_content:
                combined_content += "\n---\n"
            combined_content += content
            console.print(f"  ✓ {yaml_file.name}")

    if combined_content:
        output_file = rendered_dir / f"{app_name}.yaml"
        output_file.write_text(combined_content, encoding="utf-8")
        console.print(f"[green]✅ Rendered YAML saved: {output_file}[/green]")
        return True

    console.print("[red]❌ No content to render[/red]")
    return False


def template_http_app(
    app_name: str,
    app: HttpApp,
    base_dir: Path,
    build_dir: Path,
    app_config_dir: Path,
    rendered_dir: Path,
) -> bool:
    """
    HTTP 앱 렌더링 (다운로드된 파일 복사).

    Args:
        app_name: 앱 이름
        app: HttpApp 설정
        base_dir: 프로젝트 루트
        build_dir: build 디렉토리
        app_config_dir: 앱 설정 디렉토리
        rendered_dir: 렌더링 결과 디렉토리

    Returns:
        성공 여부
    """
    console.print(f"[cyan]📄 Rendering HTTP app: {app_name}[/cyan]")

    # build/ 디렉토리에서 파일 찾기
    build_path = build_dir / app_name

    if build_path.exists() and build_path.is_dir():
        # build 디렉토리의 파일 복사
        source_files = list(build_path.glob("*"))
        if not source_files:
            console.print(f"[red]❌ No files found in: {build_path}[/red]")
            return False

        for source_file in source_files:
            if source_file.is_file():
                dest_file = rendered_dir / f"{app_name}-{source_file.name}"
                shutil.copy2(source_file, dest_file)
                console.print(f"  ✓ {source_file.name} → {dest_file.name}")

        console.print("[green]✅ HTTP app files copied[/green]")
        return True
    else:
        # build 없으면 원본 다운로드 파일 사용
        source_file = app_config_dir / app.dest

        if not source_file.exists():
            console.print(f"[red]❌ Downloaded file not found: {source_file}[/red]")
            console.print("[yellow]💡 Run 'sbkube prepare' first[/yellow]")
            return False

        dest_file = rendered_dir / f"{app_name}-{source_file.name}"
        shutil.copy2(source_file, dest_file)
        console.print(f"[green]✅ HTTP app file copied: {dest_file}[/green]")
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
def cmd(
    app_config_dir_name: str | None,
    base_dir: str,
    config_file_name: str,
    output_dir_name: str,
    app_name: str | None,
    dry_run: bool,
):
    """
    SBKube template 명령어.

    빌드된 차트를 YAML로 렌더링:
    - .sbkube/build/ 디렉토리의 차트를 helm template으로 렌더링
    - 렌더링된 YAML을 .sbkube/rendered/ 디렉토리에 저장
    - 배포 전 미리보기 및 CI/CD 검증용
    """
    console.print("[bold blue]✨ SBKube `template` 시작 ✨[/bold blue]")

    if dry_run:
        console.print("[yellow]🔍 Dry-run mode enabled[/yellow]")

    # 경로 설정
    BASE_DIR = Path(base_dir).resolve()

    SBKUBE_WORK_DIR = BASE_DIR / ".sbkube"
    CHARTS_DIR = SBKUBE_WORK_DIR / "charts"
    BUILD_DIR = SBKUBE_WORK_DIR / "build"

    # 앱 그룹 디렉토리 결정 (공통 유틸리티 사용)
    try:
        app_config_dirs = resolve_app_dirs(
            BASE_DIR, app_config_dir_name, config_file_name
        )
    except ValueError:
        raise click.Abort()

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
    console.print(f"[cyan]📁 Output directory: {RENDERED_DIR}[/cyan]")

    # 각 앱 그룹 처리
    overall_success = True
    for APP_CONFIG_DIR in app_config_dirs:
        console.print(
            f"\n[bold cyan]━━━ Processing app group: {APP_CONFIG_DIR.name} ━━━[/bold cyan]"
        )

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

        # Hook executor 초기화
        hook_executor = HookExecutor(
            base_dir=BASE_DIR,
            work_dir=APP_CONFIG_DIR,  # 훅은 APP_CONFIG_DIR에서 실행
            dry_run=dry_run,
        )

        # 글로벌 pre-template 훅 실행
        if config.hooks and "template" in config.hooks:
            template_hooks = config.hooks["template"].model_dump()
            console.print("[cyan]🪝 Executing global pre-template hooks...[/cyan]")
            if not hook_executor.execute_command_hooks(
                template_hooks, "pre", "template"
            ):
                console.print("[red]❌ Pre-template hook failed[/red]")
                overall_success = False
                continue

        # 배포 순서 얻기 (의존성 고려)
        deployment_order = config.get_deployment_order()

        if app_name:
            # 특정 앱만 렌더링
            if app_name not in config.apps:
                console.print(f"[red]❌ App not found: {app_name}[/red]")
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
                    console.print(
                        f"[yellow]⏭️  Skipping disabled app: {app_name_iter}[/yellow]"
                    )
                    continue

                # 앱별 pre-template 훅 실행
                if hasattr(app, "hooks") and app.hooks:
                    console.print(
                        f"[cyan]🪝 Executing pre-template hook for {app_name_iter}...[/cyan]"
                    )
                    if not hook_executor.execute_app_hook(
                        app_name_iter,
                        app.hooks.model_dump() if app.hooks else None,
                        "pre_template",
                        context={"namespace": config.namespace},
                    ):
                        console.print(
                            f"[red]❌ Pre-template hook failed for {app_name_iter}[/red]"
                        )
                        failed = True
                        break

                success = False

                if isinstance(app, HookApp):
                    # HookApp은 template 단계 불필요 (deploy 시에만 실행)
                    console.print(
                        f"[yellow]⏭️  HookApp does not support template: {app_name_iter}[/yellow]"
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
                    )
                elif isinstance(app, YamlApp):
                    success = template_yaml_app(
                        app_name_iter,
                        app,
                        BASE_DIR,
                        BUILD_DIR,
                        APP_CONFIG_DIR,
                        RENDERED_DIR,
                    )
                elif isinstance(app, HttpApp):
                    success = template_http_app(
                        app_name_iter,
                        app,
                        BASE_DIR,
                        BUILD_DIR,
                        APP_CONFIG_DIR,
                        RENDERED_DIR,
                    )
                else:
                    console.print(
                        f"[yellow]⏭️  App type '{app.type}' does not support template: {app_name_iter}[/yellow]"
                    )
                    success = True  # 건너뛰어도 성공으로 간주

                if not success:
                    failed = True
                    # 앱별 on_template_failure 훅 실행
                    if hasattr(app, "hooks") and app.hooks:
                        console.print(
                            f"[yellow]🪝 Executing on-failure hook for {app_name_iter}...[/yellow]"
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
                    console.print(
                        f"[cyan]🪝 Executing post-template hook for {app_name_iter}...[/cyan]"
                    )
                    if not hook_executor.execute_app_hook(
                        app_name_iter,
                        app.hooks.model_dump() if app.hooks else None,
                        "post_template",
                        context={"namespace": config.namespace},
                    ):
                        console.print(
                            f"[red]❌ Post-template hook failed for {app_name_iter}[/red]"
                        )
                        failed = True
                        break

                if success:
                    success_count += 1

            # 글로벌 post-template 훅 실행 (성공 시에만)
            if not failed and config.hooks and "template" in config.hooks:
                template_hooks = config.hooks["template"].model_dump()
                console.print("[cyan]🪝 Executing global post-template hooks...[/cyan]")
                if not hook_executor.execute_command_hooks(
                    template_hooks, "post", "template"
                ):
                    console.print("[red]❌ Post-template hook failed[/red]")
                    failed = True

        except Exception:
            # 글로벌 on_failure 훅 실행
            if config.hooks and "template" in config.hooks:
                template_hooks = config.hooks["template"].model_dump()
                console.print(
                    "[yellow]🪝 Executing global on-failure hooks...[/yellow]"
                )
                hook_executor.execute_command_hooks(
                    template_hooks, "on_failure", "template"
                )
            failed = True

        # 실패 시 on_failure 훅 실행
        if failed:
            if config.hooks and "template" in config.hooks:
                template_hooks = config.hooks["template"].model_dump()
                console.print(
                    "[yellow]🪝 Executing global on-failure hooks...[/yellow]"
                )
                hook_executor.execute_command_hooks(
                    template_hooks, "on_failure", "template"
                )

        # 이 앱 그룹 결과 출력
        console.print(
            f"[bold green]✅ App group '{APP_CONFIG_DIR.name}' templated: {success_count}/{total_count} apps[/bold green]"
        )
        console.print(f"[cyan]📁 Rendered files saved to: {RENDERED_DIR}[/cyan]")

        if success_count < total_count or failed:
            overall_success = False

    # 전체 결과
    if not overall_success:
        console.print("\n[bold red]❌ Some app groups failed to template[/bold red]")
        raise click.Abort()
    else:
        console.print(
            "\n[bold green]🎉 All app groups templated successfully![/bold green]"
        )
