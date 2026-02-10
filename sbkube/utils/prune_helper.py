"""Prune helper for removing disabled apps from the cluster.

When an app is set to enabled: false in config, and it was previously
deployed to the cluster, prune logic detects and removes it.
"""

from __future__ import annotations

from pathlib import Path
from typing import TYPE_CHECKING

from sbkube.utils.common import run_command

if TYPE_CHECKING:
    from sbkube.models.config_model import AppConfig, SBKubeConfig
    from sbkube.utils.output_manager import OutputManager

# App types that can be pruned (have cluster-side resources)
PRUNABLE_TYPES = frozenset({"helm", "yaml", "action"})


def find_disabled_apps_to_prune(
    config: SBKubeConfig,
) -> list[tuple[str, AppConfig]]:
    """Find disabled apps that are candidates for pruning.

    Only returns apps with prunable types (helm, yaml, action).
    exec, noop, git, http, kustomize, hook types are excluded.

    Args:
        config: SBKubeConfig with all apps

    Returns:
        List of (app_name, app_config) tuples for disabled prunable apps

    """
    return [
        (name, app)
        for name, app in config.apps.items()
        if not app.enabled and app.type in PRUNABLE_TYPES
    ]


def prune_disabled_apps(
    apps_to_prune: list[tuple[str, AppConfig]],
    kubeconfig: str | None,
    context: str | None,
    app_config_dir: Path,
    output: OutputManager,
    dry_run: bool = False,
) -> bool:
    """Prune disabled apps from the cluster.

    For each disabled app, checks if it exists in the cluster and removes it.
    Skips apps that are not currently installed.

    Args:
        apps_to_prune: List of (app_name, app_config) from find_disabled_apps_to_prune
        kubeconfig: Path to kubeconfig file
        context: Kubernetes context name
        app_config_dir: App config directory (for resolving manifest paths)
        output: OutputManager for logging
        dry_run: If True, only show what would be deleted

    Returns:
        True if all prune operations succeeded (or were skipped)

    """
    all_success = True

    for app_name, app_config in apps_to_prune:
        app_type = app_config.type

        if app_type == "helm":
            success = _prune_helm_app(
                app_name, app_config, kubeconfig, context, output, dry_run
            )
        elif app_type == "yaml":
            success = _prune_yaml_app(
                app_name, app_config, kubeconfig, context, app_config_dir, output, dry_run
            )
        elif app_type == "action":
            success = _prune_action_app(
                app_name, app_config, app_config_dir, output, dry_run
            )
        else:
            continue

        if not success:
            all_success = False

    return all_success


def _prune_helm_app(
    app_name: str,
    app_config: AppConfig,
    kubeconfig: str | None,
    context: str | None,
    output: OutputManager,
    dry_run: bool,
) -> bool:
    """Prune a disabled Helm app by running helm uninstall."""
    from sbkube.utils.helm_util import get_installed_charts

    release_name = getattr(app_config, "release_name", None) or app_name
    namespace = getattr(app_config, "namespace", None) or "default"

    # App-level context takes precedence
    app_context = getattr(app_config, "context", None)
    effective_context = app_context or context
    effective_kubeconfig = kubeconfig if not app_context else None

    # Check if helm release is installed
    try:
        installed = get_installed_charts(
            namespace, context=effective_context, kubeconfig=effective_kubeconfig
        )
    except Exception as e:
        output.print(
            f"[yellow]  {app_name}: Helm 설치 상태 확인 실패 ({e}), skip[/yellow]",
            level="warning",
        )
        return True  # Non-fatal: skip this app

    if release_name not in installed:
        output.print(
            f"[dim]  {app_name}: 미설치 상태, skip[/dim]",
            level="info",
        )
        return True

    if dry_run:
        output.print(
            f"[yellow]  [DRY-RUN] {app_name}: helm uninstall {release_name} -n {namespace}[/yellow]",
            level="info",
        )
        return True

    # Build and execute helm uninstall
    helm_cmd = ["helm", "uninstall", release_name, "--namespace", namespace]
    if effective_kubeconfig:
        helm_cmd.extend(["--kubeconfig", effective_kubeconfig])
    if effective_context:
        helm_cmd.extend(["--kube-context", effective_context])

    return_code, stdout, stderr = run_command(helm_cmd, check=False, timeout=300)
    if return_code == 0:
        output.print(
            f"[green]  {app_name}: Helm release '{release_name}' 삭제 완료[/green]",
            level="success",
        )
        return True

    output.print(
        f"[red]  {app_name}: Helm uninstall 실패[/red]",
        level="error",
    )
    if stderr:
        output.print(f"    STDERR: {stderr.strip()}", level="error")
    return False


def _prune_yaml_app(
    app_name: str,
    app_config: AppConfig,
    kubeconfig: str | None,
    context: str | None,
    app_config_dir: Path,
    output: OutputManager,
    dry_run: bool,
) -> bool:
    """Prune a disabled YAML app by running kubectl delete."""
    manifests = getattr(app_config, "manifests", [])
    if not manifests:
        output.print(
            f"[dim]  {app_name}: manifest 없음, skip[/dim]",
            level="info",
        )
        return True

    namespace = getattr(app_config, "namespace", None)
    app_context = getattr(app_config, "context", None)
    effective_context = app_context or context
    effective_kubeconfig = kubeconfig if not app_context else None

    all_ok = True
    # Delete in reverse order (same as delete.py)
    for file_rel_path in reversed(manifests):
        abs_path = Path(file_rel_path)
        if not abs_path.is_absolute():
            abs_path = app_config_dir / file_rel_path

        if not abs_path.exists():
            output.print(
                f"[dim]  {app_name}: {file_rel_path} 파일 없음, skip[/dim]",
                level="info",
            )
            continue

        if dry_run:
            output.print(
                f"[yellow]  [DRY-RUN] {app_name}: kubectl delete -f {abs_path.name}[/yellow]",
                level="info",
            )
            continue

        kubectl_cmd = ["kubectl", "delete", "-f", str(abs_path), "--ignore-not-found=true"]
        if namespace:
            kubectl_cmd.extend(["--namespace", namespace])
        if effective_kubeconfig:
            kubectl_cmd.extend(["--kubeconfig", effective_kubeconfig])
        if effective_context:
            kubectl_cmd.extend(["--context", effective_context])

        return_code, stdout, stderr = run_command(kubectl_cmd, check=False, timeout=120)
        if return_code == 0:
            output.print(
                f"[green]  {app_name}: '{abs_path.name}' 삭제 완료[/green]",
                level="success",
            )
        else:
            output.print(
                f"[red]  {app_name}: '{abs_path.name}' 삭제 실패[/red]",
                level="error",
            )
            if stderr:
                output.print(f"    STDERR: {stderr.strip()}", level="error")
            all_ok = False

    return all_ok


def _prune_action_app(
    app_name: str,
    app_config: AppConfig,
    app_config_dir: Path,
    output: OutputManager,
    dry_run: bool,
) -> bool:
    """Prune a disabled action app by running its uninstall script."""
    uninstall = getattr(app_config, "uninstall", None)
    if not uninstall or not getattr(uninstall, "script", None):
        output.print(
            f"[dim]  {app_name}: uninstall.script 없음, skip[/dim]",
            level="info",
        )
        return True

    if dry_run:
        output.print(
            f"[yellow]  [DRY-RUN] {app_name}: uninstall script 실행 예정[/yellow]",
            level="info",
        )
        return True

    for cmd_str in uninstall.script:
        return_code, stdout, stderr = run_command(
            cmd_str, check=False, cwd=str(app_config_dir)
        )
        if return_code != 0:
            output.print(
                f"[red]  {app_name}: uninstall 스크립트 실패 ('{cmd_str}')[/red]",
                level="error",
            )
            if stderr:
                output.print(f"    STDERR: {stderr.strip()}", level="error")
            return False

    output.print(
        f"[green]  {app_name}: uninstall 스크립트 실행 완료[/green]",
        level="success",
    )
    return True
