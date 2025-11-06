from pathlib import Path

import click
from pydantic import ValidationError as PydanticValidationError
from rich.console import Console

from sbkube.models.config_model import ActionApp, SBKubeConfig, YamlApp
from sbkube.utils.cli_check import (
    check_helm_installed_or_exit,
    check_kubectl_installed_or_exit,
)
from sbkube.utils.cluster_config import resolve_cluster_config
from sbkube.utils.common import find_sources_file, run_command
from sbkube.utils.file_loader import load_config_file
from sbkube.utils.helm_util import get_installed_charts

console = Console()


@click.command(name="delete")
@click.option(
    "--app-dir",
    "app_config_dir_name",
    default=".",
    help="앱 설정 파일이 위치한 디렉토리 이름 (base-dir 기준)",
)
@click.option(
    "--base-dir",
    default=".",
    type=click.Path(exists=True, file_okay=False, dir_okay=True),
    help="프로젝트 루트 디렉토리",
)
@click.option(
    "--app",
    "target_app_name",
    default=None,
    help="특정 앱만 삭제 (지정하지 않으면 모든 앱 대상)",
)
@click.option(
    "--skip-not-found",
    is_flag=True,
    help="삭제 대상 리소스가 없을 경우 오류 대신 건너뜁니다.",
)
@click.option(
    "--dry-run",
    is_flag=True,
    help="실제로 삭제하지 않고 삭제될 리소스를 미리 확인합니다.",
)
@click.option(
    "--config-file",
    "config_file_name",
    default=None,
    help="사용할 설정 파일 이름 (app-dir 내부, 기본값: config.yaml 자동 탐색)",
)
@click.pass_context
def cmd(
    ctx,
    app_config_dir_name: str,
    base_dir: str,
    target_app_name: str | None,
    skip_not_found: bool,
    dry_run: bool,
    config_file_name: str | None,
) -> None:
    """config.yaml/toml에 정의된 애플리케이션을 삭제합니다 (Helm 릴리스, Kubectl 리소스 등)."""
    if dry_run:
        console.print(
            "[bold yellow]🔍 `delete` 작업 시작 (DRY-RUN 모드) - 실제 삭제는 수행되지 않습니다 ✨[/bold yellow]",
        )
    else:
        console.print(
            f"[bold blue]✨ `delete` 작업 시작 (앱 설정: '{app_config_dir_name}', 기준 경로: '{base_dir}') ✨[/bold blue]",
        )

    cli_namespace = ctx.obj.get("namespace")

    BASE_DIR = Path(base_dir).resolve()
    APP_CONFIG_DIR = BASE_DIR / app_config_dir_name

    if not APP_CONFIG_DIR.is_dir():
        console.print(
            f"[red]❌ 앱 설정 디렉토리가 존재하지 않습니다: {APP_CONFIG_DIR}[/red]",
        )
        raise click.Abort

    # Load sources.yaml and resolve cluster configuration
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
            raise click.Abort

    # Resolve cluster configuration (kubeconfig + context)
    kubeconfig = None
    context = None
    if sources:
        try:
            kubeconfig, context = resolve_cluster_config(
                cli_kubeconfig=ctx.obj.get("kubeconfig"),
                cli_context=ctx.obj.get("context"),
                sources=sources,
            )
        except Exception as e:
            console.print(f"[red]❌ Cluster configuration error: {e}[/red]")
            raise click.Abort

    config_file_path = None
    if config_file_name:
        config_file_path = APP_CONFIG_DIR / config_file_name
        if not config_file_path.exists() or not config_file_path.is_file():
            console.print(
                f"[red]❌ 지정된 설정 파일을 찾을 수 없습니다: {config_file_path}[/red]",
            )
            raise click.Abort
    else:
        # 1차 시도: APP_CONFIG_DIR에서 찾기
        for ext in [".yaml", ".yml", ".toml"]:
            candidate = APP_CONFIG_DIR / f"config{ext}"
            if candidate.exists() and candidate.is_file():
                config_file_path = candidate
                break

        # 2차 시도 (fallback): BASE_DIR에서 찾기
        if not config_file_path:
            for ext in [".yaml", ".yml", ".toml"]:
                candidate = BASE_DIR / f"config{ext}"
                if candidate.exists() and candidate.is_file():
                    config_file_path = candidate
                    break

        if not config_file_path:
            console.print(
                f"[red]❌ 앱 목록 설정 파일을 찾을 수 없습니다: {APP_CONFIG_DIR}/config.[yaml|yml|toml] 또는 {BASE_DIR}/config.[yaml|yml|toml][/red]",
            )
            raise click.Abort
    console.print(f"[green]ℹ️ 앱 목록 설정 파일 사용: {config_file_path}[/green]")

    # SBKubeConfig 모델로 로드
    try:
        config_data = load_config_file(str(config_file_path))
        config = SBKubeConfig(**config_data)
    except PydanticValidationError as e:
        console.print("[red]❌ 설정 파일 검증 실패:[/red]")
        for error in e.errors():
            console.print(f"  - {error['loc']}: {error['msg']}")
        raise click.Abort
    except Exception as e:
        console.print(f"[red]❌ 설정 파일 로드 실패: {e}[/red]")
        raise click.Abort

    global_namespace_from_config = config.namespace

    delete_total_apps = 0
    delete_success_apps = 0
    delete_skipped_apps = 0

    # apps는 dict (key=name, value=AppConfig)
    apps_to_process = []
    if target_app_name:
        if target_app_name not in config.apps:
            console.print(
                f"[red]❌ 삭제 대상 앱 '{target_app_name}'을(를) 설정 파일에서 찾을 수 없습니다.[/red]",
            )
            raise click.Abort
        apps_to_process.append((target_app_name, config.apps[target_app_name]))
    else:
        apps_to_process = list(config.apps.items())

    if not apps_to_process:
        console.print(
            "[yellow]⚠️ 설정 파일에 삭제할 앱이 정의되어 있지 않습니다.[/yellow]",
        )
        console.print(
            "[bold blue]✨ `delete` 작업 완료 (처리할 앱 없음) ✨[/bold blue]",
        )
        return

    # (app_name, app_config) 튜플
    for app_name, app_config in apps_to_process:
        # 타입은 'helm', 'yaml', 'action' 등으로 단순화됨
        # Legacy 'install-helm' → 'helm'
        # Legacy 'install-yaml' → 'yaml'
        # Legacy 'install-action' → 'action'

        if app_config.type not in ["helm", "yaml", "action"]:
            continue

        delete_total_apps += 1
        app_type = app_config.type
        app_release_name = getattr(app_config, "release_name", None) or app_name

        console.print(
            f"[magenta]➡️  앱 '{app_name}' (타입: {app_type}, 릴리스명: '{app_release_name}') 삭제 시도...[/magenta]",
        )

        # Namespace 우선순위: CLI > App > Global
        current_namespace = None
        app_namespace = getattr(app_config, "namespace", None)
        if app_namespace and app_namespace not in ["!ignore", "!none", "!false", ""]:
            current_namespace = app_namespace
        elif cli_namespace:
            current_namespace = cli_namespace
        elif global_namespace_from_config:
            current_namespace = global_namespace_from_config
        elif app_type == "helm":
            current_namespace = "default"

        if current_namespace:
            console.print(f"    [grey]ℹ️ 네임스페이스 사용: {current_namespace}[/grey]")
        else:
            console.print(
                "    [grey]ℹ️ 네임스페이스 미지정 (현재 컨텍스트의 기본값 사용 또는 리소스에 따라 다름)[/grey]",
            )

        delete_command_executed = False
        delete_successful_for_app = False

        if app_type == "helm":
            check_helm_installed_or_exit()

            # Context Priority Resolution:
            # 1. app.context (app-level): Highest priority - specified in config.yaml per app
            # 2. sources.yaml context: Middle priority - project-level default
            # 3. Current kubectl context: Lowest priority - system default
            #
            # Note: When using app.context, we don't use sources.yaml's kubeconfig
            # because app.context might refer to a context in the default kubeconfig (~/.kube/config)
            # or another kubeconfig file that the user has already configured in their environment.
            app_context = getattr(app_config, "context", None)
            effective_context = app_context or context
            effective_kubeconfig = kubeconfig if not app_context else None

            installed_charts = get_installed_charts(
                current_namespace,
                context=effective_context,
                kubeconfig=effective_kubeconfig,
            )
            if app_release_name not in installed_charts:
                console.print(
                    f"[yellow]⚠️ Helm 릴리스 '{app_release_name}'(네임스페이스: {current_namespace or '-'})가 설치되어 있지 않습니다.[/yellow]",
                )
                if skip_not_found:
                    console.print(
                        "    [grey]L `--skip-not-found` 옵션으로 건너뜁니다.[/grey]",
                    )
                    delete_skipped_apps += 1
                    console.print("")
                    continue
                delete_skipped_apps += 1
                console.print("")
                continue

            helm_cmd = ["helm", "uninstall", app_release_name]
            if current_namespace:
                helm_cmd.extend(["--namespace", current_namespace])
            if effective_kubeconfig:
                helm_cmd.extend(["--kubeconfig", effective_kubeconfig])
            if effective_context:
                helm_cmd.extend(["--kube-context", effective_context])
            if dry_run:
                helm_cmd.append("--dry-run")

            console.print(f"    [cyan]$ {' '.join(helm_cmd)}[/cyan]")
            return_code, stdout, stderr = run_command(
                helm_cmd,
                check=False,
                timeout=300,
            )
            if return_code == 0:
                if dry_run:
                    console.print(
                        f"[yellow]🔍 [DRY-RUN] Helm 릴리스 '{app_release_name}' 삭제 예정.[/yellow]",
                    )
                else:
                    console.print(
                        f"[green]✅ Helm 릴리스 '{app_release_name}' 삭제 완료.[/green]",
                    )
                if stdout:
                    console.print(f"    [grey]Helm STDOUT: {stdout.strip()}[/grey]")
                delete_successful_for_app = True
                delete_command_executed = True
            else:
                console.print(
                    f"[red]❌ Helm 릴리스 '{app_release_name}' 삭제 실패:[/red]",
                )
                if stdout:
                    console.print(f"    [blue]STDOUT:[/blue] {stdout.strip()}")
                if stderr:
                    console.print(f"    [red]STDERR:[/red] {stderr.strip()}")

        elif app_type == "yaml":
            check_kubectl_installed_or_exit()

            # YamlApp은 files 리스트를 직접 가짐
            if not isinstance(app_config, YamlApp):
                console.print(
                    f"[red]❌ 앱 '{app_name}': 타입이 'yaml'이나 YamlApp 모델이 아님[/red]",
                )
                delete_skipped_apps += 1
                console.print("")
                continue

            # Context Priority Resolution (same as helm):
            # 1. app.context > 2. sources.yaml context > 3. current kubectl context
            app_context = getattr(app_config, "context", None)
            effective_context = app_context or context
            effective_kubeconfig = kubeconfig if not app_context else None

            if not app_config.manifests:
                console.print(
                    f"[yellow]⚠️ 앱 '{app_name}': 삭제할 YAML 파일이 지정되지 않았습니다. 건너뜁니다.[/yellow]",
                )
                delete_skipped_apps += 1
                console.print("")
                continue

            yaml_delete_successful_files = 0
            yaml_delete_failed_files = 0

            # manifests를 역순으로 삭제
            for file_rel_path in reversed(app_config.manifests):
                file_path = Path(file_rel_path)
                abs_yaml_path = file_path
                if not abs_yaml_path.is_absolute():
                    abs_yaml_path = APP_CONFIG_DIR / file_path

                if not abs_yaml_path.exists() or not abs_yaml_path.is_file():
                    console.print(
                        f"    [yellow]⚠️ YAML 삭제 대상 파일을 찾을 수 없음 (건너뜀): {abs_yaml_path}[/yellow]",
                    )
                    yaml_delete_failed_files += 1
                    continue

                kubectl_cmd = ["kubectl", "delete", "-f", str(abs_yaml_path)]
                if current_namespace:
                    kubectl_cmd.extend(["--namespace", current_namespace])
                if effective_kubeconfig:
                    kubectl_cmd.extend(["--kubeconfig", effective_kubeconfig])
                if effective_context:
                    kubectl_cmd.extend(["--context", effective_context])
                if skip_not_found:
                    kubectl_cmd.append("--ignore-not-found=true")
                if dry_run:
                    kubectl_cmd.append("--dry-run=client")

                console.print(f"    [cyan]$ {' '.join(kubectl_cmd)}[/cyan]")
                return_code, stdout, stderr = run_command(
                    kubectl_cmd,
                    check=False,
                    timeout=120,
                )
                if return_code == 0:
                    if dry_run:
                        console.print(
                            f"[yellow]    🔍 [DRY-RUN] YAML '{abs_yaml_path.name}' 삭제 예정.[/yellow]",
                        )
                    else:
                        console.print(
                            f"[green]    ✅ YAML '{abs_yaml_path.name}' 삭제 요청 성공.[/green]",
                        )
                    if stdout:
                        console.print(
                            f"        [grey]Kubectl STDOUT: {stdout.strip()}[/grey]",
                        )
                    yaml_delete_successful_files += 1
                    delete_command_executed = True
                else:
                    console.print(
                        f"[red]    ❌ YAML '{abs_yaml_path.name}' 삭제 실패:[/red]",
                    )
                    if stdout:
                        console.print(f"        [blue]STDOUT:[/blue] {stdout.strip()}")
                    if stderr:
                        console.print(f"        [red]STDERR:[/red] {stderr.strip()}")
                    yaml_delete_failed_files += 1

            if yaml_delete_failed_files == 0 and yaml_delete_successful_files > 0:
                delete_successful_for_app = True
            elif (
                yaml_delete_failed_files == 0
                and yaml_delete_successful_files == 0
                and not delete_command_executed
            ):
                if skip_not_found:
                    delete_successful_for_app = True
                    console.print(
                        f"    [yellow]ℹ️ 앱 '{app_name}': 모든 YAML 리소스가 이미 삭제되었거나 대상이 없었습니다 (skip-not-found).[/yellow]",
                    )

            console.print(
                f"    [grey]YAML 삭제 요약 (파일 기준): 성공 {yaml_delete_successful_files}, 실패 {yaml_delete_failed_files}[/grey]",
            )

        elif app_type == "action":
            # ActionApp
            if not isinstance(app_config, ActionApp):
                console.print(
                    f"[red]❌ 앱 '{app_name}': 타입이 'action'이나 ActionApp 모델이 아님[/red]",
                )
                delete_skipped_apps += 1
                console.print("")
                continue

            if not app_config.uninstall or not app_config.uninstall.script:
                console.print(
                    f"[yellow]⚠️ 앱 '{app_name}' (타입: {app_type}): `uninstall.script`가 정의되지 않아 자동으로 삭제할 수 없습니다. 건너뜁니다.[/yellow]",
                )
                delete_skipped_apps += 1
                console.print("")
                continue

            if dry_run:
                console.print(
                    f"[yellow]⚠️ [DRY-RUN] 앱 '{app_name}' (타입: action): uninstall 스크립트는 dry-run에서 실행되지 않습니다.[/yellow]",
                )
                console.print(
                    f"    [grey]스크립트 내용: {app_config.uninstall.script}[/grey]",
                )
                delete_successful_for_app = True
                delete_command_executed = True
            else:
                for raw_cmd_str in app_config.uninstall.script:
                    console.print(f"    [cyan]$ {raw_cmd_str}[/cyan]")
                    return_code, stdout, stderr = run_command(
                        raw_cmd_str,
                        check=False,
                        cwd=BASE_DIR,
                    )
                    if return_code != 0:
                        console.print(
                            f"[red]❌ 앱 '{app_name}': uninstall 스크립트 실행 실패 ('{raw_cmd_str}'):[/red]",
                        )
                        if stdout:
                            console.print(f"    [blue]STDOUT:[/blue] {stdout.strip()}")
                        if stderr:
                            console.print(f"    [red]STDERR:[/red] {stderr.strip()}")
                        delete_successful_for_app = False
                        break
                    if stdout:
                        console.print(f"    [grey]STDOUT:[/grey] {stdout.strip()}")
                    console.print(
                        f"[green]✅ 앱 '{app_name}': uninstall 스크립트 실행 완료 ('{raw_cmd_str}')[/green]",
                    )
                    delete_successful_for_app = True
                delete_command_executed = True

        else:
            console.print(
                f"[yellow]⚠️ 앱 '{app_name}' (타입: {app_type}): 이 타입에 대한 자동 삭제 로직이 아직 정의되지 않았습니다. 건너뜁니다.[/yellow]",
            )
            delete_skipped_apps += 1
            console.print("")
            continue

        if delete_successful_for_app or (not delete_command_executed and skip_not_found):
            delete_success_apps += 1

        console.print("")

    console.print("[bold blue]✨ `delete` 작업 요약 ✨[/bold blue]")
    if delete_total_apps > 0:
        console.print(
            f"[green]    총 {delete_total_apps}개 앱 대상 중 {delete_success_apps}개 삭제 성공 (또는 이미 삭제됨).[/green]",
        )
        if delete_skipped_apps > 0:
            console.print(
                f"[yellow]    {delete_skipped_apps}개 앱 건너뜀 (지원되지 않는 타입, 설정 오류, 리소스 없음 등).[/yellow]",
            )
        if (delete_total_apps - delete_success_apps - delete_skipped_apps) > 0:
            console.print(
                f"[red]    {delete_total_apps - delete_success_apps - delete_skipped_apps}개 앱 삭제 실패.[/red]",
            )
    elif target_app_name and not apps_to_process:
        pass
    else:
        console.print("[yellow]    삭제할 대상으로 지정된 앱이 없었습니다.[/yellow]")
    console.print("[bold blue]✨ `delete` 작업 완료 ✨[/bold blue]")
