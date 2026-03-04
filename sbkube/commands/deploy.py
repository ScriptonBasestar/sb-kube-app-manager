"""SBKube deploy 명령어.

새로운 기능:
- helm 타입: Helm install/upgrade
- yaml 타입: kubectl apply
- action 타입: 커스텀 액션 (apply/create/delete)
- exec 타입: 커스텀 명령어 실행
- kustomize 타입: kubectl apply -k
"""

from pathlib import Path
from typing import Any

import click

from sbkube.exceptions import KubernetesConnectionError
from sbkube.models.config_model import (
    ActionApp,
    ExecApp,
    GitApp,
    HelmApp,
    HookApp,
    KustomizeApp,
    NoopApp,
    SBKubeConfig,
    YamlApp,
)
from sbkube.utils.app_dir_resolver import resolve_app_dirs
from sbkube.utils.app_labels import (
    build_helm_set_annotations,
    build_helm_set_labels,
    build_sbkube_annotations,
    build_sbkube_labels,
    extract_app_group_from_name,
    get_label_injection_recommendation,
    inject_labels_to_yaml,
    is_chart_label_injection_compatible,
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
from sbkube.utils.common import find_sources_file, run_command
from sbkube.utils.common_options import resolve_command_paths, target_options
from sbkube.utils.file_loader import load_config_file
from sbkube.utils.helm_command_builder import (
    HelmCommand,
    HelmCommandBuilder,
)
from sbkube.utils.hook_executor import HookExecutor
from sbkube.utils.logger import LogLevel, logger
from sbkube.utils.output_manager import OutputManager
from sbkube.utils.security import is_exec_allowed
from sbkube.utils.workspace_resolver import resolve_sbkube_directories

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


def _info_print(console, msg, **kwargs) -> None:
    """INFO 레벨 이하일 때만 console.print 출력."""
    if logger._level <= LogLevel.INFO:
        console.print(msg, **kwargs)


def _verbose_print(console, msg, **kwargs) -> None:
    """VERBOSE 레벨 이하일 때만 console.print 출력."""
    if logger._level <= LogLevel.VERBOSE:
        console.print(msg, **kwargs)


def _get_connection_error_reason(stdout: str, stderr: str) -> str | None:
    """Detects common Kubernetes connection error patterns in command output.

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
    output: OutputManager,
    kubeconfig: str | None = None,
    context: str | None = None,
    dry_run: bool = False,
    deployment_id: str | None = None,
    operator: str | None = None,
    progress_tracker: Any = None,
    cluster_global_values: dict | None = None,
    incompatible_charts: list[str] | None = None,
    force_label_injection: list[str] | None = None,
) -> bool:
    """Helm 앱 배포 (install/upgrade).

    Args:
        app_name: 앱 이름
        app: HelmApp 설정
        base_dir: 프로젝트 루트
        charts_dir: charts 디렉토리
        build_dir: build 디렉토리
        app_config_dir: 앱 설정 디렉토리
        output: OutputManager 인스턴스
        kubeconfig: kubeconfig 파일 경로
        context: kubectl context 이름
        dry_run: dry-run 모드
        deployment_id: 배포 ID (Phase 2)
        operator: 배포자 이름 (Phase 2)
        progress_tracker: ProgressTracker 인스턴스 (Phase 2)
        cluster_global_values: 클러스터 전역 values (선택, v0.7.0+)
        incompatible_charts: 추가 비호환 chart 목록 (sources.yaml에서)
        force_label_injection: 강제 호환 chart 목록 (sources.yaml에서)

    Returns:
        성공 여부

    """
    console = output.get_console()
    # Progress tracking setup
    current_step = 0

    def _update_progress(description: str) -> None:
        nonlocal current_step
        current_step += 1
        if progress_tracker:
            progress_tracker.update(
                progress_tracker.current_task,
                completed=current_step,
                description=f"🚀 Deploy {app_name}: {description}",
            )

    if not progress_tracker:
        output.print(f"[cyan]🚀 Deploying Helm app: {app_name}[/cyan]")

    _update_progress("Resolving chart path")

    release_name = app.release_name or app_name
    namespace = app.namespace

    # App-level context overrides CLI/sources.yaml context
    if hasattr(app, "context") and app.context:
        context = app.context
        _verbose_print(console, f"  [yellow]Using app-specific context: {context}[/yellow]")

    # Chart 경로 결정 (.sbkube/build/ 우선, 없으면 .sbkube/charts/ 또는 로컬)
    chart_path = None

    # 1. .sbkube/build/ 디렉토리 확인 (overrides/removes 적용된 차트)
    build_path = build_dir / app_name
    if build_path.exists() and build_path.is_dir():
        chart_path = build_path
        _verbose_print(console, f"  Using built chart: {chart_path}")
    # 2. build 없으면 원본 차트 사용 (v0.8.0+ path structure)
    elif app.is_remote_chart():
        # Remote chart: .sbkube/charts/{repo}/{chart-name}-{version}/
        source_path = app.get_chart_path(charts_dir)

        if not source_path or not source_path.exists():
            # Check for legacy paths (v0.7.1 and earlier)
            chart_name = app.get_chart_name()

            # Legacy v0.7.1: charts/{chart-name}/
            legacy_v071_path = charts_dir / chart_name
            # Legacy v0.7.0: charts/{chart-name}/{chart-name}/
            legacy_v070_path = charts_dir / chart_name / chart_name

            if legacy_v071_path.exists():
                output.print_error(
                    f"Chart found at legacy path (v0.7.1): {legacy_v071_path}"
                )
                output.print_warning(
                    "This chart was downloaded with an older version of SBKube"
                )
                console.print(
                    "[yellow]💡 Migration required (v0.8.0 path structure):[/yellow]"
                )
                console.print(f"   1. Remove old charts: rm -rf {charts_dir}")
                console.print("   2. Re-download charts: sbkube prepare --force")
                console.print(
                    "\n📚 See: docs/05-best-practices/directory-structure.md (v0.8.0 migration)"
                )
            elif legacy_v070_path.exists():
                output.print_error(
                    f"Chart found at legacy path (v0.7.0): {legacy_v070_path}"
                )
                output.print_warning(
                    "This chart was downloaded with a very old version of SBKube"
                )
                console.print("[yellow]💡 Migration required:[/yellow]")
                console.print(f"   1. Remove old charts: rm -rf {charts_dir}")
                console.print("   2. Re-download charts: sbkube prepare --force")
                console.print(
                    "\n📚 See: docs/05-best-practices/directory-structure.md (v0.8.0 migration)"
                )
            else:
                output.print_error(f"Chart not found: {source_path}")
                output.print_warning("Run 'sbkube prepare' first")
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
            output.print_error(f"Local chart not found: {source_path}")
            return False

        chart_path = source_path
        _verbose_print(console, f"  Using local chart: {chart_path}")

    # Helm install/upgrade 명령어 구성 (HelmCommandBuilder 사용)
    helm_builder = (
        HelmCommandBuilder(HelmCommand.UPGRADE)
        .with_release_name(release_name)
        .with_chart_path(chart_path)
        .with_install_flag()
        .with_namespace(namespace)
        .with_create_namespace(app.create_namespace)
        .with_wait(app.wait)
        .with_atomic(app.atomic)
        .with_force_conflicts(app.force_conflicts)
        .with_timeout(app.timeout)
        .with_cluster_global_values(cluster_global_values)
    )

    # Values 파일 추가
    for values_file in app.values:
        values_path = app_config_dir / values_file
        if not values_path.exists():
            console.print(f"[yellow]⚠️ Values file not found: {values_path}[/yellow]")
        else:
            helm_builder.with_values_file(values_path)

    # --set 옵션 추가
    helm_builder.with_set_values(app.set_values)

    # Build the command
    helm_result = helm_builder.build()
    cmd = list(helm_result.command)  # Copy to allow modifications

    _update_progress("Checking namespace")

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
                if not progress_tracker:
                    console.print(
                        f"[yellow]⚠️ Namespace '{namespace}' is missing (dry-run: skipping creation)[/yellow]"
                    )
            else:
                if progress_tracker:
                    progress_tracker.console_print(
                        f"[yellow]  Creating namespace '{namespace}'...[/yellow]"
                    )
                else:
                    _info_print(console,
                        f"[yellow]ℹ️  Namespace '{namespace}' not found. Creating...[/yellow]"
                    )
                create_cmd = ["kubectl", "create", "namespace", namespace]
                create_cmd = apply_cluster_config_to_command(
                    create_cmd, kubeconfig, context
                )
                create_return_code, _, create_stderr = run_command(create_cmd)
                if create_return_code != 0:
                    output.print_error(
                        f"Failed to create namespace '{namespace}'", error=create_stderr
                    )
                    helm_result.cleanup()
                    return False

    if cluster_global_values:
        _verbose_print(console, "  [dim]Applying cluster global values...[/dim]")

    # Phase 2: Inject sbkube labels and annotations
    # Extract app-group from app_config_dir path
    app_group = extract_app_group_from_name(app_config_dir.name)
    if not app_group:
        # Try parent directory (for nested apps)
        app_group = extract_app_group_from_name(app_config_dir.parent.name)

    # Check chart compatibility and determine effective label injection setting
    effective_label_injection = app.helm_label_injection
    chart_name = app.chart

    # Auto-disable for known incompatible charts (unless user explicitly set it or forced)
    if effective_label_injection and chart_name:
        if not is_chart_label_injection_compatible(
            chart_name,
            extra_incompatible=incompatible_charts,
            force_compatible=force_label_injection,
        ):
            recommendation = get_label_injection_recommendation(
                chart_name,
                extra_incompatible=incompatible_charts,
                force_compatible=force_label_injection,
            )
            if recommendation:
                for line in recommendation.split("\n"):
                    _verbose_print(console, f"  [yellow]{line}[/yellow]")
            effective_label_injection = False

    # Check if automatic label injection is enabled
    if effective_label_injection:
        if app_group:
            # Build labels
            labels = build_sbkube_labels(
                app_name=app_name,
                app_group=app_group,
                deployment_id=deployment_id,
            )
            label_args = build_helm_set_labels(labels)
            cmd.extend(label_args)
            _verbose_print(console, f"  [dim]Injecting labels: app-group={app_group}[/dim]")

            # Build annotations
            annotations = build_sbkube_annotations(
                deployment_id=deployment_id,
                operator=operator,
            )
            annotation_args = build_helm_set_annotations(annotations)
            cmd.extend(annotation_args)
        else:
            _verbose_print(console,
                f"  [yellow]⚠️ Could not detect app-group from path: {app_config_dir}[/yellow]"
            )
            _verbose_print(console,
                "  [dim]Labels will not be injected (use app_XXX_category naming)[/dim]"
            )
    else:
        if not chart_name or is_chart_label_injection_compatible(
            chart_name,
            extra_incompatible=incompatible_charts,
            force_compatible=force_label_injection,
        ):
            # User explicitly disabled, not auto-disabled
            _verbose_print(console,
                "  [dim]Label injection disabled (helm_label_injection: false)[/dim]"
            )
        if app_group:
            _verbose_print(console,
                f"  [dim]App tracking will use State DB and name pattern (app-group={app_group})[/dim]"
            )

    if dry_run:
        cmd.append("--dry-run")
        console.print("[yellow]🔍 Dry-run mode enabled[/yellow]")

    # Apply cluster configuration
    cmd = apply_cluster_config_to_command(cmd, kubeconfig, context)

    # 명령어 출력
    if not progress_tracker:
        _verbose_print(console, f"  Command: {' '.join(cmd)}")

    # 실행
    _update_progress("Installing/Upgrading Helm release")

    try:
        return_code, stdout, stderr = run_command(cmd, timeout=300)

        if return_code != 0:
            # Timeout detection
            if return_code == -1 and "Timeout expired" in stderr:
                timeout_msg = (
                    f"Helm deployment timed out after 300 seconds (5 minutes).\n\n"
                    f"Possible causes:\n"
                    f"  - Pod image pull is slow or failing\n"
                    f"  - Pod is failing health checks\n"
                    f"  - Insufficient cluster resources\n\n"
                    f"Troubleshooting:\n"
                    f"  1. Check pod status: kubectl get pods -n {namespace}\n"
                    f"  2. Check pod logs: kubectl logs -n {namespace} <pod-name>\n"
                    f"  3. Describe pod: kubectl describe pod -n {namespace} <pod-name>\n"
                    f"  4. Increase timeout: add 'timeout: 10m' to app config\n"
                )
                output.print_error("Helm deployment timeout", error=timeout_msg)
                return False

            reason = _get_connection_error_reason(stdout, stderr)
            if reason:
                raise KubernetesConnectionError(reason=reason)

            # Check for label injection related errors
            error_lower = stderr.lower()
            is_schema_error = any(
                keyword in error_lower
                for keyword in (
                    "commonlabels",
                    "commonannotations",
                    "values.schema.json",
                    "additional properties",
                    "not allowed",
                )
            )
            if is_schema_error:
                label_hint = (
                    f"\n\n"
                    f"{'─' * 60}\n"
                    f"💡 Schema Validation Error Detected\n"
                    f"{'─' * 60}\n"
                    f"\n"
                    f"원인: Chart '{app.chart}'의 JSON schema가 sbkube 자동 주입 필드를 거부\n"
                    f"\n"
                    f"해결책: config.yaml에 다음 추가\n"
                    f"\n"
                    f"  {app_name}:\n"
                    f"    helm_label_injection: false  # strict schema 호환\n"
                    f"\n"
                    f"알려진 strict schema charts:\n"
                    f"  - traefik/traefik (commonAnnotations 미지원)\n"
                    f"  - jetstack/cert-manager (additionalProperties: false)\n"
                    f"  - authelia/authelia (다른 필드명 사용)\n"
                    f"{'─' * 60}"
                )
                output.print_error("Schema validation failed", error=stderr + label_hint)
            else:
                output.print_error("Failed to deploy", error=stderr)
            return False

        if progress_tracker:
            progress_tracker.console_print(
                f"[green]✅ {app_name} deployed (release: {release_name})[/green]"
            )
        else:
            output.print_success(
                f"Helm app deployed: {app_name} (release: {release_name})"
            )
        return True
    except KeyboardInterrupt:
        console.print("\n[yellow]⚠️  Deployment interrupted by user (Ctrl+C)[/yellow]")
        console.print(
            f"[yellow]ℹ️  App '{app_name}' deployment may be incomplete.[/yellow]"
        )
        console.print(
            f"[dim]Check deployment status: kubectl get pods -n {namespace}[/dim]"
        )
        raise  # Re-raise to allow outer handler to exit properly
    finally:
        # 임시 파일 정리 (HelmCommandBuilder가 생성한 temp 파일)
        helm_result.cleanup()


def deploy_yaml_app(
    app_name: str,
    app: YamlApp,
    base_dir: Path,
    app_config_dir: Path,
    output: OutputManager,
    kubeconfig: str | None = None,
    context: str | None = None,
    dry_run: bool = False,
    apps_config: dict | None = None,
    sbkube_work_dir: Path | None = None,
    config_namespace: str | None = None,
) -> bool:
    """YAML 앱 배포 (kubectl apply).

    Args:
        app_name: 앱 이름
        app: YamlApp 설정
        base_dir: 프로젝트 루트
        app_config_dir: 앱 설정 디렉토리
        output: OutputManager 인스턴스
        kubeconfig: kubeconfig 파일 경로
        context: kubectl context 이름
        dry_run: dry-run 모드
        apps_config: 전체 앱 설정 (변수 확장용)
        sbkube_work_dir: .sbkube 작업 디렉토리 경로
        config_namespace: config.yaml의 전역 namespace (fallback용)

    Returns:
        성공 여부

    """
    # 순환 import 방지를 위해 함수 내부에서 import
    from sbkube.utils.path_resolver import expand_repo_variables

    console = output.get_console()
    output.print(f"[cyan]🚀 Deploying YAML app: {app_name}[/cyan]")

    # 네임스페이스 해석: app.namespace가 명시되면 우선, 없으면 config.namespace 사용
    namespace = app.namespace or config_namespace

    # App-level context overrides CLI/sources.yaml context
    if hasattr(app, "context") and app.context:
        context = app.context
        _verbose_print(console, f"  [yellow]Using app-specific context: {context}[/yellow]")

    # .sbkube 디렉토리 결정 (기본값: base_dir/.sbkube)
    if sbkube_work_dir is None:
        sbkube_work_dir = base_dir / ".sbkube"
    repos_dir = sbkube_work_dir / "repos"

    # Phase 2: Extract app-group for label injection
    app_group = extract_app_group_from_name(app_config_dir.name)
    if not app_group:
        app_group = extract_app_group_from_name(app_config_dir.parent.name)

    # Build sbkube labels and annotations to inject
    labels = None
    annotations = None
    if app_group:
        labels = build_sbkube_labels(app_name, app_group)
        annotations = build_sbkube_annotations()
        _verbose_print(console, f"  [dim]Will inject labels: app-group={app_group}[/dim]")
    else:
        _verbose_print(console,
            f"  [yellow]⚠️ Could not detect app-group from path: {app_config_dir}[/yellow]"
        )
        _verbose_print(console,
            "  [dim]Labels will not be injected (use app_XXX_category naming)[/dim]"
        )

    for yaml_file in app.manifests:
        # ${repos.app-name} 변수 확장
        expanded_file = yaml_file
        if "${repos." in yaml_file:
            if apps_config is None:
                output.print_error(
                    f"Cannot expand variable '{yaml_file}': apps_config not provided"
                )
                return False
            try:
                expanded_file = expand_repo_variables(yaml_file, repos_dir, apps_config)
                # 변수 확장 성공 로그
                if expanded_file != yaml_file:
                    _verbose_print(console,
                        f"  [dim]Variable expanded: {yaml_file} → {expanded_file}[/dim]"
                    )
            except Exception as e:
                output.print_error(
                    f"Failed to expand variable in '{yaml_file}'", error=str(e)
                )
                return False

        # 경로 해석: 절대경로면 그대로, 상대경로면 app_config_dir 기준
        yaml_path = Path(expanded_file)
        if not yaml_path.is_absolute():
            yaml_path = app_config_dir / expanded_file

        if not yaml_path.exists():
            output.print_error(f"YAML file not found: {yaml_path}")
            return False

        # Read and inject labels dynamically
        try:
            with yaml_path.open("r", encoding="utf-8") as f:
                yaml_content = f.read()

            # Inject labels if app-group detected
            if labels and annotations:
                yaml_content = inject_labels_to_yaml(yaml_content, labels, annotations)
        except Exception as e:
            output.print_error(
                f"Failed to process YAML file: {yaml_path}", error=str(e)
            )
            return False

        # Create temporary file with injected labels
        import tempfile

        temp_dir = base_dir / ".sbkube" / "temp"
        temp_dir.mkdir(parents=True, exist_ok=True)

        try:
            with tempfile.NamedTemporaryFile(
                mode="w",
                suffix=".yaml",
                dir=str(temp_dir),
                delete=False,
                encoding="utf-8",
            ) as temp_file:
                temp_file.write(yaml_content)
                temp_yaml_path = Path(temp_file.name)

            cmd = ["kubectl", "apply", "-f", str(temp_yaml_path)]

            if namespace:
                cmd.extend(["--namespace", namespace])

            if dry_run:
                cmd.append("--dry-run=client")
                cmd.append("--validate=false")

            # Apply cluster configuration
            cmd = apply_cluster_config_to_command(cmd, kubeconfig, context)

            _info_print(console, f"  Applying: {yaml_file}")
            return_code, stdout, stderr = run_command(cmd)

            # Clean up temporary file
            try:
                temp_yaml_path.unlink()
            except Exception:
                pass  # Ignore cleanup errors

            if return_code != 0:
                reason = _get_connection_error_reason(stdout, stderr)
                if reason:
                    raise KubernetesConnectionError(reason=reason)
                output.print_error("Failed to apply", error=stderr)
                return False

        except Exception as e:
            output.print_error(f"Failed to deploy YAML: {yaml_file}", error=str(e))
            return False

    output.print_success(f"YAML app deployed: {app_name}")
    return True


def deploy_action_app(
    app_name: str,
    app: ActionApp,
    base_dir: Path,
    app_config_dir: Path,
    output: OutputManager,
    kubeconfig: str | None = None,
    context: str | None = None,
    dry_run: bool = False,
    config_namespace: str | None = None,
) -> bool:
    """Action 앱 배포 (커스텀 액션).

    Args:
        app_name: 앱 이름
        app: ActionApp 설정
        base_dir: 프로젝트 루트
        app_config_dir: 앱 설정 디렉토리
        output: OutputManager 인스턴스
        kubeconfig: kubeconfig 파일 경로
        context: kubectl context 이름
        dry_run: dry-run 모드
        config_namespace: config.yaml의 전역 namespace (fallback용)

    Returns:
        성공 여부

    """
    console = output.get_console()
    output.print(f"[cyan]🚀 Deploying Action app: {app_name}[/cyan]")

    # 네임스페이스 해석: app.namespace가 명시되면 우선, 없으면 config.namespace 사용
    namespace = app.namespace or config_namespace

    # Phase 2: Extract app-group for label injection
    app_group = extract_app_group_from_name(app_config_dir.name)
    if not app_group:
        app_group = extract_app_group_from_name(app_config_dir.parent.name)

    # Build sbkube labels and annotations to inject
    labels = None
    annotations = None
    if app_group:
        labels = build_sbkube_labels(app_name, app_group)
        annotations = build_sbkube_annotations()
        _verbose_print(console, f"  [dim]Will inject labels: app-group={app_group}[/dim]")
    else:
        _verbose_print(console,
            f"  [yellow]⚠️ Could not detect app-group from path: {app_config_dir}[/yellow]"
        )
        _verbose_print(console,
            "  [dim]Labels will not be injected (use app_XXX_category naming)[/dim]"
        )

    for action in app.actions:
        # ActionSpec은 이제 타입이 있는 객체입니다
        action_type = action.type
        action_path = action.path
        action_namespace = action.namespace or namespace

        # 경로 해석 (URL 또는 로컬 파일)
        if action_path.startswith(("http://", "https://")):
            file_path = action_path
        else:
            file_path = str(app_config_dir / action_path)

        # Read and inject labels dynamically for local files
        actual_file_path = file_path
        temp_yaml_path = None
        if not action_path.startswith(("http://", "https://")):
            try:
                with open(file_path, encoding="utf-8") as f:
                    yaml_content = f.read()

                # Inject labels if app-group detected
                if labels and annotations:
                    yaml_content = inject_labels_to_yaml(
                        yaml_content, labels, annotations
                    )

                # Create temporary file with injected labels
                import tempfile

                temp_dir = base_dir / ".sbkube" / "temp"
                temp_dir.mkdir(parents=True, exist_ok=True)

                with tempfile.NamedTemporaryFile(
                    mode="w",
                    suffix=".yaml",
                    dir=str(temp_dir),
                    delete=False,
                    encoding="utf-8",
                ) as temp_file:
                    temp_file.write(yaml_content)
                    temp_yaml_path = Path(temp_file.name)
                    actual_file_path = str(temp_yaml_path)
            except Exception as e:
                output.print_error(
                    f"Failed to process YAML file: {file_path}", error=str(e)
                )
                return False

        cmd = ["kubectl", action_type, "-f", actual_file_path]

        if action_namespace:
            cmd.extend(["--namespace", action_namespace])

        if dry_run:
            cmd.append("--dry-run=client")
            cmd.append("--validate=false")

        # Apply cluster configuration
        cmd = apply_cluster_config_to_command(cmd, kubeconfig, context)

        _info_print(console, f"  {action_type.capitalize()}: {action_path}")
        return_code, stdout, stderr = run_command(cmd)

        # Clean up temporary file if created
        if temp_yaml_path:
            try:
                temp_yaml_path.unlink()
            except Exception:
                pass  # Ignore cleanup errors

        if return_code != 0:
            reason = _get_connection_error_reason(stdout, stderr)
            if reason:
                raise KubernetesConnectionError(reason=reason)
            output.print_error(f"Failed to {action_type}", error=stderr)
            return False

    output.print_success(f"Action app deployed: {app_name}")
    return True


def deploy_exec_app(
    app_name: str,
    app: ExecApp,
    base_dir: Path,
    output: OutputManager,
    dry_run: bool = False,
) -> bool:
    """Exec 앱 실행 (커스텀 명령어).

    Args:
        app_name: 앱 이름
        app: ExecApp 설정
        base_dir: 프로젝트 루트
        output: OutputManager 인스턴스
        dry_run: dry-run 모드

    Returns:
        성공 여부

    """
    console = output.get_console()
    output.print(f"[cyan]🚀 Executing commands: {app_name}[/cyan]")

    if not dry_run and not is_exec_allowed():
        output.print_error(
            "Exec apps are disabled (SBKUBE_ALLOW_EXEC=false). "
            "Enable execution to run exec commands."
        )
        return False

    for command in app.commands:
        if dry_run:
            console.print(f"  [DRY-RUN] {command}")
            continue

        _info_print(console, f"  Running: {command}")
        return_code, stdout, stderr = run_command(command, timeout=60)

        if return_code != 0:
            reason = _get_connection_error_reason(stdout, stderr)
            if reason:
                raise KubernetesConnectionError(reason=reason)
            output.print_error("Command failed", error=stderr)
            return False

        if stdout:
            _verbose_print(console, f"  Output: {stdout.strip()}")

    output.print_success(f"Commands executed: {app_name}")
    return True


def deploy_kustomize_app(
    app_name: str,
    app: KustomizeApp,
    base_dir: Path,
    app_config_dir: Path,
    output: OutputManager,
    kubeconfig: str | None = None,
    context: str | None = None,
    dry_run: bool = False,
    config_namespace: str | None = None,
) -> bool:
    """Kustomize 앱 배포 (kubectl apply -k).

    Args:
        app_name: 앱 이름
        app: KustomizeApp 설정
        base_dir: 프로젝트 루트
        app_config_dir: 앱 설정 디렉토리
        output: OutputManager 인스턴스
        kubeconfig: kubeconfig 파일 경로
        context: kubectl context 이름
        dry_run: dry-run 모드
        config_namespace: config.yaml의 전역 namespace (fallback용)

    Returns:
        성공 여부

    """
    console = output.get_console()
    output.print(f"[cyan]🚀 Deploying Kustomize app: {app_name}[/cyan]")

    kustomize_path = app_config_dir / app.path
    # 네임스페이스 해석: app.namespace가 명시되면 우선, 없으면 config.namespace 사용
    namespace = app.namespace or config_namespace

    if not kustomize_path.exists():
        output.print_error(f"Kustomize path not found: {kustomize_path}")
        return False

    # Phase 2: Extract app-group for label injection
    app_group = extract_app_group_from_name(app_config_dir.name)
    if not app_group:
        app_group = extract_app_group_from_name(app_config_dir.parent.name)

    # Build sbkube labels and annotations to inject
    labels = None
    annotations = None
    if app_group:
        labels = build_sbkube_labels(app_name, app_group)
        annotations = build_sbkube_annotations()
        _verbose_print(console, f"  [dim]Will inject labels: app-group={app_group}[/dim]")
    else:
        _verbose_print(console,
            f"  [yellow]⚠️ Could not detect app-group from path: {app_config_dir}[/yellow]"
        )
        _verbose_print(console,
            "  [dim]Labels will not be injected (use app_XXX_category naming)[/dim]"
        )

    # Build kustomize build command to get YAML output
    build_cmd = ["kustomize", "build", str(kustomize_path)]

    # Apply cluster configuration (for kubeconfig/context if needed in build step)
    build_cmd = apply_cluster_config_to_command(build_cmd, kubeconfig, context)

    _info_print(console, f"  Building Kustomize: {kustomize_path}")
    return_code, stdout, stderr = run_command(build_cmd)

    if return_code != 0:
        output.print_error("Failed to build Kustomize manifest", error=stderr)
        return False

    # Get built YAML content
    yaml_content = stdout

    # Inject labels if app-group detected
    if labels and annotations:
        yaml_content = inject_labels_to_yaml(yaml_content, labels, annotations)

    # Create temporary file with built and injected YAML
    import tempfile

    temp_dir = base_dir / ".sbkube" / "temp"
    temp_dir.mkdir(parents=True, exist_ok=True)

    temp_yaml_path = None
    try:
        with tempfile.NamedTemporaryFile(
            mode="w",
            suffix=".yaml",
            dir=str(temp_dir),
            delete=False,
            encoding="utf-8",
        ) as temp_file:
            temp_file.write(yaml_content)
            temp_yaml_path = Path(temp_file.name)

        # Apply the built YAML
        cmd = ["kubectl", "apply", "-f", str(temp_yaml_path)]

        if namespace:
            cmd.extend(["--namespace", namespace])

        if dry_run:
            cmd.append("--dry-run=client")
            cmd.append("--validate=false")

        # Apply cluster configuration
        cmd = apply_cluster_config_to_command(cmd, kubeconfig, context)

        _info_print(console, f"  Applying: {kustomize_path}")
        return_code, stdout, stderr = run_command(cmd)

        if return_code != 0:
            reason = _get_connection_error_reason(stdout, stderr)
            if reason:
                raise KubernetesConnectionError(reason=reason)
            output.print_error("Failed to apply", error=stderr)
            return False

    finally:
        # Clean up temporary file
        if temp_yaml_path:
            try:
                temp_yaml_path.unlink()
            except Exception:
                pass  # Ignore cleanup errors

    output.print_success(f"Kustomize app deployed: {app_name}")
    return True


def deploy_noop_app(
    app_name: str,
    app: NoopApp,
    base_dir: Path,
    app_config_dir: Path,
    output: OutputManager,
    dry_run: bool = False,
) -> bool:
    """Noop 앱 배포 (실제로는 아무것도 하지 않음).

    Args:
        app_name: 앱 이름
        app: NoopApp 설정
        base_dir: 프로젝트 루트
        app_config_dir: 앱 설정 디렉토리
        output: OutputManager 인스턴스
        dry_run: dry-run 모드

    Returns:
        항상 True (성공)

    """
    console = output.get_console()
    output.print(f"[cyan]🚀 Processing Noop app: {app_name}[/cyan]")

    if app.description:
        _verbose_print(console, f"  Description: {app.description}")

    if dry_run:
        output.print_warning("Dry-run mode: No actual deployment")

    output.print_success(f"Noop app processed: {app_name} (no-op)")
    return True


def deploy_hook_app(
    app_name: str,
    app: HookApp,
    base_dir: Path,
    app_config_dir: Path,
    output: OutputManager,
    kubeconfig: str | None = None,
    context: str | None = None,
    namespace: str | None = None,
    dry_run: bool = False,
) -> bool:
    """Hook 앱 배포 (Phase 4: Hook as First-class App).

    HookApp은 독립적인 리소스 관리 앱으로, Phase 2/3의 HookTask를 재사용합니다.

    Args:
        app_name: 앱 이름
        app: HookApp 설정
        base_dir: 프로젝트 루트
        app_config_dir: 앱 설정 디렉토리
        output: OutputManager 인스턴스
        kubeconfig: kubeconfig 파일 경로
        context: kubectl context
        namespace: 배포 대상 namespace
        dry_run: dry-run 모드

    Returns:
        성공 여부

    """
    console = output.get_console()
    output.print(f"[cyan]🪝 Deploying Hook app: {app_name}[/cyan]")

    # HookApp의 tasks가 비어있으면 경고
    if not app.tasks:
        output.print_warning("No tasks defined in Hook app, skipping")
        return True

    # namespace 결정 (우선순위: 앱 설정 > 명령어 인자)
    target_namespace = app.namespace or namespace

    # HookExecutor 초기화
    hook_executor = HookExecutor(
        base_dir=base_dir,
        work_dir=app_config_dir,
        dry_run=dry_run,
        kubeconfig=kubeconfig,
        context=context,
        namespace=target_namespace,
    )

    # Hook Context 준비
    hook_context = {
        "namespace": target_namespace,
        "app_name": app_name,
        "dry_run": dry_run,
    }

    # Hook Tasks 실행 (Phase 2/3 로직 재사용)
    _info_print(console, f"  Executing {len(app.tasks)} tasks...")
    success = hook_executor.execute_hook_tasks(
        app_name=app_name,
        tasks=app.tasks,
        hook_type="hook_app_deploy",  # HookApp 전용 hook_type
        context=hook_context,
    )

    if success:
        output.print_success(f"Hook app deployed: {app_name}")
    else:
        output.print_error(f"Hook app failed: {app_name}")

    return success


@click.command(name="deploy")
@target_options
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
    target: str | None,
    config_file: str | None,
    app_name: str | None,
    dry_run: bool,
) -> None:
    """SBKube deploy 명령어.

    애플리케이션을 Kubernetes 클러스터에 배포합니다:
    - helm 타입: Helm install/upgrade
    - yaml 타입: kubectl apply
    - action 타입: 커스텀 액션
    - exec 타입: 커스텀 명령어
    - kustomize 타입: kubectl apply -k
    """
    # Initialize OutputManager
    output_format = ctx.obj.get("format", "human")
    output = OutputManager(format_type=output_format)

    output.print("[bold blue]✨ SBKube `deploy` 시작 ✨[/bold blue]")

    # kubectl 설치 확인 (cluster connectivity는 나중에 확인)
    check_kubectl_installed_or_exit()

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
            BASE_DIR, app_config_dir_name, config_file_name, sources_file_name
        )
    except ValueError:
        raise click.Abort

    # Resolve .sbkube directories using centralized utility (Phase 2 refactoring)
    sbkube_dirs = resolve_sbkube_directories(
        BASE_DIR, app_config_dirs, sources_file_name
    )
    SBKUBE_WORK_DIR = sbkube_dirs.sbkube_work_dir
    CHARTS_DIR = sbkube_dirs.charts_dir
    BUILD_DIR = sbkube_dirs.build_dir

    # 각 앱 그룹 처리
    overall_success = True
    for APP_CONFIG_DIR in app_config_dirs:
        output.print_section(f"Processing app group: {APP_CONFIG_DIR.name}")

        config_file_path = APP_CONFIG_DIR / config_file_name

        # Load sources and resolve cluster configuration
        sources_file_name = ctx.obj.get("sources_file", "sources.yaml")
        sources_file_path = find_sources_file(
            BASE_DIR, APP_CONFIG_DIR, sources_file_name
        )

        sources = None
        cluster_global_values = None
        if sources_file_path and sources_file_path.exists():
            output.print(f"[cyan]📄 Loading sources: {sources_file_path}[/cyan]")
            try:
                from sbkube.models.sources_model import SourceScheme

                sources_data = load_config_file(sources_file_path)

                # 통합 sbkube.yaml 포맷 감지 (apiVersion이 sbkube/로 시작)
                api_version = sources_data.get("apiVersion", "") if sources_data else ""
                if api_version.startswith("sbkube/"):
                    # 통합 포맷: settings 섹션에서 SourceScheme 필드만 추출
                    full_settings = sources_data.get("settings", {})

                    # SourceScheme에서 허용하는 필드만 추출
                    source_scheme_fields = {
                        "cluster", "kubeconfig", "kubeconfig_context",
                        "app_dirs", "cluster_values_file", "global_values",
                        "cleanup_metadata", "incompatible_charts", "force_label_injection",
                        "helm_repos", "oci_registries", "git_repos",
                        "http_proxy", "https_proxy", "no_proxy",
                    }

                    # 상위 디렉토리의 sbkube.yaml에서 설정 상속 (cluster settings)
                    merged_settings: dict = {}
                    current_dir = sources_file_path.parent
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
                                parent_settings = parent_data.get("settings", {})
                                for k, v in parent_settings.items():
                                    if k in source_scheme_fields:
                                        merged_settings[k] = v
                        except Exception:
                            pass

                    for k, v in full_settings.items():
                        if k in source_scheme_fields:
                            merged_settings[k] = v

                    settings_data = merged_settings
                else:
                    settings_data = sources_data

                sources = SourceScheme(**settings_data)

                # Load cluster global values (v0.7.0+)
                cluster_global_values = sources.get_merged_global_values(
                    sources_dir=APP_CONFIG_DIR
                )
                if cluster_global_values:
                    output.print(
                        "[cyan]🌐 Loaded cluster global values from sources.yaml[/cyan]"
                    )
            except Exception as e:
                output.print_error(f"Invalid sources file: {e}")
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
            output.print_error(str(e))
            overall_success = False
            continue

        # Check cluster connectivity with resolved kubeconfig and context
        check_cluster_connectivity_or_exit(
            kubeconfig=kubeconfig,
            kubecontext=context,
        )

        # 설정 파일 로드
        if not config_file_path.exists():
            output.print_error(f"Config file not found: {config_file_path}")
            overall_success = False
            continue

        output.print(f"[cyan]📄 Loading config: {config_file_path}[/cyan]")
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
            output.print_error(f"Invalid config file: {e}")
            overall_success = False
            continue

        # 배포 순서 얻기 (의존성 고려)
        deployment_order = config.get_deployment_order()

        if app_name:
            # 특정 앱만 배포
            if app_name not in config.apps:
                output.print_error(f"App not found: {app_name}")
                overall_success = False
                continue
            apps_to_deploy = [app_name]
        else:
            # 모든 앱 배포 (의존성 순서대로)
            apps_to_deploy = deployment_order

        # Hook executor 초기화 (Phase 1: kubeconfig, context, namespace 추가)
        hook_executor = HookExecutor(
            base_dir=BASE_DIR,
            work_dir=APP_CONFIG_DIR,  # 훅은 APP_CONFIG_DIR에서 실행
            dry_run=dry_run,
            kubeconfig=kubeconfig,
            context=context,
            namespace=config.namespace,  # config에서 namespace 가져옴
        )

        # ========== 전역 pre-deploy 훅 실행 ==========
        if config.hooks and "deploy" in config.hooks:
            deploy_hooks = config.hooks["deploy"].model_dump()
            if not hook_executor.execute_command_hooks(
                hook_config=deploy_hooks,
                hook_phase="pre",
                command_name="deploy",
            ):
                output.print_error("Pre-deploy hook failed")
                overall_success = False
                continue

        # 앱 배포
        success_count = 0
        total_count = len(apps_to_deploy)
        deployment_failed = False

        for app_name_iter in apps_to_deploy:
            app = config.apps[app_name_iter]

            if not app.enabled:
                output.print_warning(f"Skipping disabled app: {app_name_iter}")
                continue

            # ========== 앱별 pre-deploy 훅 실행 ==========
            if hasattr(app, "hooks") and app.hooks:
                app_hooks = app.hooks.model_dump()
                hook_context = {
                    "namespace": (
                        app.namespace if hasattr(app, "namespace") else config.namespace
                    ),
                    "release_name": getattr(app, "release_name", None) or app_name_iter,
                }

                # Phase 2: pre_deploy_tasks 우선 실행
                if app_hooks.get("pre_deploy_tasks"):
                    if not hook_executor.execute_hook_tasks(
                        app_name=app_name_iter,
                        tasks=app_hooks["pre_deploy_tasks"],
                        hook_type="pre_deploy",
                        context=hook_context,
                    ):
                        output.print_error(
                            f"Pre-deploy tasks failed for app: {app_name_iter}"
                        )
                        deployment_failed = True
                        continue

                # Phase 1: shell 명령어 + manifests
                if not hook_executor.execute_app_hook_with_manifests(
                    app_name=app_name_iter,
                    app_hooks=app_hooks,
                    hook_type="pre_deploy",
                    context=hook_context,
                ):
                    output.print_error(
                        f"Pre-deploy hook failed for app: {app_name_iter}"
                    )
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
                        output,
                        kubeconfig,
                        context,
                        dry_run,
                        cluster_global_values=cluster_global_values,
                        incompatible_charts=sources.incompatible_charts if sources else None,
                        force_label_injection=sources.force_label_injection if sources else None,
                    )
                elif isinstance(app, YamlApp):
                    # apps_config를 딕셔너리로 변환 (Pydantic 모델 → dict)
                    apps_config_dict = {
                        name: app_obj.model_dump()
                        for name, app_obj in config.apps.items()
                    }
                    success = deploy_yaml_app(
                        app_name_iter,
                        app,
                        BASE_DIR,
                        APP_CONFIG_DIR,
                        output,
                        kubeconfig,
                        context,
                        dry_run,
                        apps_config=apps_config_dict,
                        sbkube_work_dir=SBKUBE_WORK_DIR,
                        config_namespace=config.namespace,
                    )
                elif isinstance(app, ActionApp):
                    success = deploy_action_app(
                        app_name_iter,
                        app,
                        BASE_DIR,
                        APP_CONFIG_DIR,
                        output,
                        kubeconfig,
                        context,
                        dry_run,
                        config_namespace=config.namespace,
                    )
                elif isinstance(app, ExecApp):
                    success = deploy_exec_app(
                        app_name_iter, app, BASE_DIR, output, dry_run
                    )
                elif isinstance(app, KustomizeApp):
                    success = deploy_kustomize_app(
                        app_name_iter,
                        app,
                        BASE_DIR,
                        APP_CONFIG_DIR,
                        output,
                        kubeconfig,
                        context,
                        dry_run,
                        config_namespace=config.namespace,
                    )
                elif isinstance(app, NoopApp):
                    success = deploy_noop_app(
                        app_name_iter, app, BASE_DIR, APP_CONFIG_DIR, output, dry_run
                    )
                elif isinstance(app, HookApp):
                    success = deploy_hook_app(
                        app_name_iter,
                        app,
                        BASE_DIR,
                        APP_CONFIG_DIR,
                        output,
                        kubeconfig,
                        context,
                        config.namespace,  # config에서 namespace 가져옴
                        dry_run,
                    )
                elif isinstance(app, GitApp):
                    # Git apps are handled in prepare phase, skip silently in deploy
                    output.print(
                        f"⏭️  Git app skipped (handled in prepare): {app_name_iter}"
                    )
                    success = True
                else:
                    output.print_warning(
                        f"Unsupported app type '{app.type}': {app_name_iter}"
                    )
                    continue
            except KubernetesConnectionError as exc:
                output.print_error(
                    f"Kubernetes cluster connection error detected while processing app: {app_name_iter}",
                    error=exc.reason if exc.reason else None,
                )
                output.print_warning("Check your cluster connectivity and try again.")
                deployment_failed = True
                overall_success = False
                break

            # ========== 앱별 post-deploy 또는 on_deploy_failure 훅 실행 ==========
            if hasattr(app, "hooks") and app.hooks:
                app_hooks = app.hooks.model_dump()
                hook_context = {
                    "namespace": (
                        app.namespace if hasattr(app, "namespace") else config.namespace
                    ),
                    "release_name": getattr(app, "release_name", None) or app_name_iter,
                }

                if success:
                    # 배포 성공 시 post_deploy 훅 실행
                    # Phase 1: shell 명령어 + manifests
                    hook_executor.execute_app_hook_with_manifests(
                        app_name=app_name_iter,
                        app_hooks=app_hooks,
                        hook_type="post_deploy",
                        context=hook_context,
                    )

                    # Phase 2: tasks (우선순위: tasks > manifests > commands)
                    if app_hooks.get("post_deploy_tasks"):
                        hook_executor.execute_hook_tasks(
                            app_name=app_name_iter,
                            tasks=app_hooks["post_deploy_tasks"],
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
        output.print_success(
            f"App group '{APP_CONFIG_DIR.name}' deployed: {success_count}/{total_count} apps"
        )

        if success_count < total_count:
            overall_success = False

    # 전체 결과
    if not overall_success:
        output.finalize(
            status="failed",
            summary={"app_groups_processed": len(app_config_dirs), "status": "failed"},
            next_steps=["Check error messages above and fix configuration"],
            errors=None,  # OutputManager will use accumulated errors
        )
        raise click.Abort
    output.finalize(
        status="success",
        summary={"app_groups_processed": len(app_config_dirs), "status": "success"},
        next_steps=["Verify deployment with: kubectl get pods"],
        errors=[],
    )
