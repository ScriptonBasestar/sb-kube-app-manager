"""Deployment history management with LLM-friendly output."""

from __future__ import annotations

import difflib
import hashlib
import json
from collections import Counter
from typing import Any, Iterable, Tuple

import click
from rich.table import Table

from sbkube.models.deployment_state import (
    DeploymentDetail,
    DeploymentSummary,
    DeploymentStatus,
)
from sbkube.state.database import DeploymentDatabase
from sbkube.utils.output_manager import OutputManager

try:
    import yaml
except ImportError:  # pragma: no cover - optional dependency
    yaml = None


STATUS_ICONS = {
    "success": "✅",
    "failed": "❌",
    "in_progress": "🔄",
    "pending": "⏳",
    "rolled_back": "↩️",
    "partially_failed": "⚠️",
}


@click.command(name="history")
@click.option("--cluster", help="Filter by cluster name")
@click.option("--namespace", "-n", help="Filter by namespace")
@click.option("--limit", default=20, show_default=True, help="Maximum number of deployments to show")
@click.option(
    "--format",
    "format_override",
    type=click.Choice(["table", "human", "llm", "json", "yaml"], case_sensitive=False),
    default=None,
    help="Override output format (deprecated: prefer `sbkube --format`).",
)
@click.option(
    "--show",
    "deployment_id",
    help="Show detailed information for a specific deployment ID",
)
@click.option(
    "--diff",
    "diff_ids",
    help="Compare two deployments (format: ID1,ID2)",
)
@click.option(
    "--values-diff",
    "values_diff_ids",
    help="Compare Helm values between two deployments (format: ID1,ID2)",
)
@click.argument("app_group", required=False)
@click.pass_context
def cmd(
    ctx: click.Context,
    cluster: str | None,
    namespace: str | None,
    limit: int,
    format_override: str | None,
    deployment_id: str | None,
    diff_ids: str | None,
    values_diff_ids: str | None,
    app_group: str | None,
) -> None:
    """Display deployment history with LLM-friendly output."""

    output_format = _resolve_output_format(ctx, format_override)
    output = OutputManager(format_type=output_format)

    if format_override and format_override.lower() == "table" and output.format_type == "human":
        output.print_warning(
            "Option '--format table' is deprecated; use `sbkube --format human` or SBKUBE_OUTPUT_FORMAT=human.",
            deprecated_option="--format table",
        )

    try:
        db = DeploymentDatabase()
    except Exception as exc:  # pragma: no cover - initialization errors
        output.print_error("Failed to initialize deployment database", error=str(exc))
        _finalize_history_failure(output, [str(exc)])
        raise click.Abort()

    try:
        if values_diff_ids:
            _handle_values_diff(output, db, values_diff_ids)
            return

        if diff_ids:
            _handle_diff(output, db, diff_ids)
            return

        if deployment_id:
            _handle_detail(output, db, deployment_id)
            return

        _handle_list(
            output,
            db,
            cluster=cluster,
            namespace=namespace,
            app_group=app_group,
            limit=limit,
        )
    except click.Abort:
        raise
    except Exception as exc:
        output.print_error("Failed to retrieve deployment history", error=str(exc))
        _finalize_history_failure(output, [str(exc)])
        raise click.Abort()


def _handle_list(
    output: OutputManager,
    db: DeploymentDatabase,
    cluster: str | None,
    namespace: str | None,
    app_group: str | None,
    limit: int,
) -> None:
    """Render deployment history list view."""
    deployments = db.list_deployments(
        cluster=cluster,
        namespace=namespace,
        app_group=app_group,
        limit=limit,
    )

    entries = [_serialize_summary(dep) for dep in deployments]
    status_counts = Counter(entry["status"] for entry in entries)

    if output.format_type == "human":
        if not entries:
            output.print_warning("No deployments found", reason="empty_history")
        else:
            _print_history_table(output, entries)
    elif not entries:
        output.print_warning("No deployments found", reason="empty_history")

    summary = {
        "view": "list",
        "total": len(entries),
        "returned": len(entries),
        "limit": limit,
        "filters": {
            "cluster": cluster or "any",
            "namespace": namespace or "any",
            "app_group": app_group or "any",
        },
        "status_counts": dict(status_counts),
    }

    next_steps = []
    if entries:
        next_steps.append(f"sbkube history --show {entries[0]['deployment_id']}")

    overall_status = _derive_overall_status(status_counts)
    output.finalize_history(
        status=overall_status,
        summary=summary,
        history=entries,
        next_steps=next_steps,
    )


def _handle_detail(
    output: OutputManager, db: DeploymentDatabase, deployment_id: str
) -> None:
    """Render detailed deployment view."""
    deployment = db.get_deployment(deployment_id)
    if not deployment:
        message = f"Deployment not found: {deployment_id}"
        output.print_error(message, deployment_id=deployment_id)
        _finalize_history_failure(output, [message])
        raise click.Abort()

    detail = _serialize_detail(deployment)

    if output.format_type == "human":
        _print_deployment_detail(output, detail)

    summary = {
        "view": "detail",
        "deployment_id": detail["deployment_id"],
        "status": detail["status"],
        "timestamp": detail["timestamp"],
        "cluster": detail["cluster"],
        "namespace": detail["namespace"],
    }

    next_steps = [f"sbkube history --diff {detail['deployment_id']},<other-id>"]

    output.finalize_history(
        status=detail["status"],
        summary=summary,
        history=[detail],
        next_steps=next_steps,
        errors=[detail["error_message"]] if detail.get("error_message") else None,
    )


def _handle_diff(
    output: OutputManager,
    db: DeploymentDatabase,
    diff_ids: str,
) -> None:
    """Render deployment comparison view."""
    try:
        id1, id2 = _parse_pair(diff_ids, option_name="--diff")
    except ValueError as err:
        output.print_error(str(err))
        _finalize_history_failure(output, [str(err)])
        raise click.Abort()

    diff_result = db.get_deployment_diff(id1, id2)
    if not diff_result:
        message = f"One or both deployments not found: {id1}, {id2}"
        output.print_error(message)
        _finalize_history_failure(output, [message])
        raise click.Abort()

    diff_payload = _serialize_diff(diff_result)

    if output.format_type == "human":
        _print_deployment_diff(output, diff_result)

    summary = {
        "view": "diff",
        "source": id1,
        "target": id2,
        "status": diff_payload["deployment2"]["status"],
    }

    next_steps = [f"sbkube history --values-diff {id1},{id2}"]

    output.finalize_history(
        status="success",
        summary=summary,
        history=[diff_payload],
        next_steps=next_steps,
    )


def _handle_values_diff(
    output: OutputManager,
    db: DeploymentDatabase,
    diff_ids: str,
) -> None:
    """Render Helm values comparison view."""
    try:
        id1, id2 = _parse_pair(diff_ids, option_name="--values-diff")
    except ValueError as err:
        output.print_error(str(err))
        _finalize_history_failure(output, [str(err)])
        raise click.Abort()

    diff_result = db.get_deployment_values_diff(id1, id2)
    if not diff_result:
        message = f"One or both deployments not found: {id1}, {id2}"
        output.print_error(message)
        _finalize_history_failure(output, [message])
        raise click.Abort()

    values_payload = _serialize_values_diff(diff_result)

    if output.format_type == "human":
        _print_values_diff(output, diff_result)

    summary = {
        "view": "values-diff",
        "deployment1": id1,
        "deployment2": id2,
    }

    output.finalize_history(
        status="success",
        summary=summary,
        history=[values_payload],
    )


# --------------------------------------------------------------------------- #
# Serialization helpers
# --------------------------------------------------------------------------- #


def _serialize_summary(dep: DeploymentSummary) -> dict[str, Any]:
    status = dep.status.value if isinstance(dep.status, DeploymentStatus) else dep.status
    return {
        "deployment_id": dep.deployment_id,
        "timestamp": dep.timestamp.isoformat(),
        "cluster": dep.cluster,
        "namespace": dep.namespace,
        "status": status,
        "status_icon": STATUS_ICONS.get(status, "•"),
        "apps": {
            "success": dep.success_count,
            "total": dep.app_count,
            "failed": dep.failed_count,
        },
        "error_message": dep.error_message,
    }


def _serialize_detail(deployment: DeploymentDetail) -> dict[str, Any]:
    status = (
        deployment.status.value
        if isinstance(deployment.status, DeploymentStatus)
        else deployment.status
    )

    apps = []
    for app in deployment.apps:
        app_status = app.get("status", "unknown")
        apps.append(
            {
                "name": app.get("name"),
                "type": app.get("type"),
                "namespace": app.get("namespace"),
                "status": app_status,
                "status_icon": STATUS_ICONS.get(app_status, "•"),
                "error_message": app.get("error_message"),
            }
        )

    resources = []
    for resource in deployment.resources:
        resources.append(
            {
                "kind": resource.kind,
                "name": resource.name,
                "namespace": resource.namespace,
                "action": resource.action.value if hasattr(resource.action, "value") else resource.action,
            }
        )

    helm_releases = []
    for release in deployment.helm_releases:
        helm_releases.append(
            {
                "release_name": release.release_name,
                "namespace": release.namespace,
                "chart": release.chart,
                "chart_version": release.chart_version,
                "app_version": release.app_version,
                "revision": release.revision,
                "status": release.status,
            }
        )

    return {
        "deployment_id": deployment.deployment_id,
        "timestamp": deployment.timestamp.isoformat(),
        "cluster": deployment.cluster,
        "namespace": deployment.namespace,
        "config_dir": deployment.app_config_dir,
        "status": status,
        "status_icon": STATUS_ICONS.get(status, "•"),
        "error_message": deployment.error_message,
        "apps": apps,
        "resources": resources,
        "helm_releases": helm_releases,
        "config_snapshot": deployment.config_snapshot,
        "sources_snapshot": deployment.sources_snapshot if hasattr(deployment, "sources_snapshot") else None,
    }


def _serialize_diff(diff_result: dict[str, Any]) -> dict[str, Any]:
    dep1 = diff_result["deployment1"]
    dep2 = diff_result["deployment2"]
    apps_diff = diff_result.get("apps_diff", {})

    config_changes = _summarize_config_changes(
        dep1.get("config_snapshot"),
        dep2.get("config_snapshot"),
    )

    return {
        "deployment1": _serialize_diff_side(dep1),
        "deployment2": _serialize_diff_side(dep2),
        "apps_diff": apps_diff,
        "config_changes": config_changes,
        "config_checksums": {
            "deployment1": _hash_config(dep1.get("config_snapshot")),
            "deployment2": _hash_config(dep2.get("config_snapshot")),
        },
    }


def _serialize_diff_side(data: dict[str, Any]) -> dict[str, Any]:
    return {
        "id": data.get("id"),
        "timestamp": _to_iso(data.get("timestamp")),
        "cluster": data.get("cluster"),
        "namespace": data.get("namespace"),
        "status": data.get("status"),
        "app_count": data.get("app_count"),
    }


def _serialize_values_diff(diff_result: dict[str, Any]) -> dict[str, Any]:
    values_diff = diff_result.get("values_diff", {})

    summary_counts = Counter(info.get("status", "unknown") for info in values_diff.values())

    releases = [
        {"name": name, "status": info.get("status")}
        for name, info in values_diff.items()
    ]

    return {
        "deployment1_id": diff_result["deployment1"]["id"],
        "deployment2_id": diff_result["deployment2"]["id"],
        "summary": dict(summary_counts),
        "releases": releases,
        "values_diff": values_diff,
    }


# --------------------------------------------------------------------------- #
# Human rendering helpers
# --------------------------------------------------------------------------- #


def _print_history_table(output: OutputManager, entries: list[dict[str, Any]]) -> None:
    console = output.get_console()
    table = Table(title="Deployment History", expand=True)
    table.add_column("ID", style="cyan", overflow="fold")
    table.add_column("Timestamp", style="green")
    table.add_column("Cluster", style="magenta")
    table.add_column("Namespace", style="magenta")
    table.add_column("Status", style="yellow")
    table.add_column("Apps", justify="right")

    for entry in entries:
        apps = entry["apps"]
        table.add_row(
            entry["deployment_id"],
            entry["timestamp"],
            entry["cluster"],
            entry["namespace"],
            f"{entry['status_icon']} {entry['status']}",
            f"{apps['success']}/{apps['total']}",
        )

    console.print(table)


def _print_deployment_detail(output: OutputManager, detail: dict[str, Any]) -> None:
    console = output.get_console()
    console.print(f"[bold cyan]Deployment:[/bold cyan] {detail['deployment_id']}")
    console.print(f"Timestamp: {detail['timestamp']}")
    console.print(f"Cluster: {detail['cluster']}  Namespace: {detail['namespace']}")
    console.print(f"Config Dir: {detail.get('config_dir', '-')}")
    console.print(f"Status: {detail['status_icon']} {detail['status']}")

    if detail.get("error_message"):
        console.print(f"[red]Error:[/red] {detail['error_message']}")

    if detail["apps"]:
        console.print("\n[bold]Applications[/bold]")
        for app in detail["apps"]:
            namespace = f" ({app['namespace']})" if app.get("namespace") else ""
            console.print(
                f"  {app['status_icon']} {app['name']} [{app['type']}]"
                f"{namespace} - {app['status']}"
            )
            if app.get("error_message"):
                console.print(f"      [red]Error:[/red] {app['error_message']}")

    if detail["resources"]:
        console.print("\n[bold]Resources[/bold]")
        for resource in detail["resources"]:
            ns = f"/{resource['namespace']}" if resource.get("namespace") else ""
            console.print(
                f"  {resource['action'].upper():<8} {resource['kind']}{ns}/{resource['name']}"
            )

    if detail["helm_releases"]:
        console.print("\n[bold]Helm Releases[/bold]")
        for release in detail["helm_releases"]:
            console.print(
                "  📦 {name} (rev {rev}) status={status}".format(
                    name=release["release_name"],
                    rev=release["revision"],
                    status=release["status"],
                )
            )


def _print_deployment_diff(output: OutputManager, diff_result: dict[str, Any]) -> None:
    console = output.get_console()
    console.print("[bold cyan]Deployment Comparison[/bold cyan]")

    dep1 = diff_result["deployment1"]
    dep2 = diff_result["deployment2"]

    table = Table(show_header=True, header_style="bold")
    table.add_column("Field")
    table.add_column("Deployment 1")
    table.add_column("Deployment 2")

    table.add_row("ID", str(dep1["id"]), str(dep2["id"]))
    table.add_row(
        "Timestamp",
        str(dep1["timestamp"]),
        str(dep2["timestamp"]),
    )
    table.add_row("Cluster", dep1["cluster"], dep2["cluster"])
    table.add_row("Namespace", dep1["namespace"], dep2["namespace"])
    table.add_row("Status", dep1["status"], dep2["status"])
    table.add_row("App Count", str(dep1["app_count"]), str(dep2["app_count"]))

    console.print(table)

    apps_diff = diff_result.get("apps_diff", {})
    console.print("\n[bold]Application Changes[/bold]")
    for label in ("added", "removed", "modified"):
        items = apps_diff.get(label) or []
        if items:
            console.print(f"  {label.capitalize()} ({len(items)}):")
            for item in items:
                console.print(f"    • {item}")

    config1 = dep1.get("config_snapshot")
    config2 = dep2.get("config_snapshot")
    if config1 and config2 and yaml:
        console.print("\n[bold]Configuration Changes[/bold]")
        config1_str = yaml.dump(config1, default_flow_style=False)
        config2_str = yaml.dump(config2, default_flow_style=False)
        diff_lines = list(
            difflib.unified_diff(
                config1_str.splitlines(),
                config2_str.splitlines(),
                fromfile=f"{dep1['id']} config",
                tofile=f"{dep2['id']} config",
                lineterm="",
            )
        )
        for line in diff_lines[:50]:
            if line.startswith("+"):
                console.print(f"[green]{line}[/green]")
            elif line.startswith("-"):
                console.print(f"[red]{line}[/red]")
            elif line.startswith("@@"):
                console.print(f"[cyan]{line}[/cyan]")
            else:
                console.print(line)
        if len(diff_lines) > 50:
            console.print(f"... ({len(diff_lines) - 50} more lines)")


def _print_values_diff(output: OutputManager, diff_result: dict[str, Any]) -> None:
    console = output.get_console()
    console.print("[bold cyan]Helm Values Comparison[/bold cyan]")

    dep1 = diff_result["deployment1"]
    dep2 = diff_result["deployment2"]
    console.print(
        f"Deployment 1: {dep1['id']} ({dep1['timestamp']})\n"
        f"Deployment 2: {dep2['id']} ({dep2['timestamp']})"
    )

    values_diff = diff_result.get("values_diff", {})
    status_counter = Counter(info.get("status", "unknown") for info in values_diff.values())
    console.print("\n[bold]Summary[/bold]")
    for key in ("added", "removed", "modified", "unchanged"):
        console.print(f"  {key.capitalize():<9}: {status_counter.get(key, 0)}")

    if not values_diff:
        console.print("\n[italic]No Helm releases found in either deployment[/italic]")
        return

    for release_name, info in values_diff.items():
        status = info.get("status")
        console.print(f"\n[bold]{release_name}[/bold] ({status.upper()})")

        if status in {"added", "removed"} and info.get("values") and yaml:
            values_str = yaml.dump(info["values"], default_flow_style=False)
            for line in values_str.splitlines()[:20]:
                prefix = "+" if status == "added" else "-"
                color = "green" if status == "added" else "red"
                console.print(f"[{color}]{prefix} {line}[/{color}]")
        elif status == "modified" and yaml:
            before = yaml.dump(info.get("values_before"), default_flow_style=False) if info.get("values_before") else ""
            after = yaml.dump(info.get("values_after"), default_flow_style=False) if info.get("values_after") else ""
            diff_lines = list(
                difflib.unified_diff(
                    before.splitlines(),
                    after.splitlines(),
                    fromfile=dep1["id"],
                    tofile=dep2["id"],
                    lineterm="",
                )
            )
            for line in diff_lines[:30]:
                if line.startswith("+"):
                    console.print(f"[green]{line}[/green]")
                elif line.startswith("-"):
                    console.print(f"[red]{line}[/red]")
                elif line.startswith("@@"):
                    console.print(f"[cyan]{line}[/cyan]")
                else:
                    console.print(line)
            if len(diff_lines) > 30:
                console.print(f"... ({len(diff_lines) - 30} more lines)")


# --------------------------------------------------------------------------- #
# Utility helpers
# --------------------------------------------------------------------------- #


def _resolve_output_format(ctx: click.Context, override: str | None) -> str:
    base_format = ctx.obj.get("format", "human") if ctx.obj else "human"
    if not override:
        return base_format

    override_normalized = override.lower()
    if override_normalized == "table":
        return "human"

    return override_normalized


def _derive_overall_status(status_counts: Counter) -> str:
    if status_counts.get("failed") or status_counts.get("partially_failed"):
        return "warning"
    if status_counts.get("rolled_back"):
        return "warning"
    return "success"


def _parse_pair(value: str, option_name: str) -> Tuple[str, str]:
    try:
        first, second = value.split(",", 1)
        return first.strip(), second.strip()
    except ValueError as err:
        raise ValueError(f"Invalid {option_name} format. Use: {option_name} ID1,ID2") from err


def _hash_config(config: Any) -> str | None:
    if config is None:
        return None
    try:
        payload = json.dumps(config, sort_keys=True, default=str).encode()
        return hashlib.sha256(payload).hexdigest()
    except Exception:  # pragma: no cover - hashing failures are unlikely
        return None


def _summarize_config_changes(
    config1: Any,
    config2: Any,
    max_lines: int = 20,
) -> list[str]:
    if not yaml or not config1 or not config2:
        return []

    config1_str = yaml.dump(config1, default_flow_style=False)
    config2_str = yaml.dump(config2, default_flow_style=False)
    diff_lines = list(
        difflib.unified_diff(
            config1_str.splitlines(),
            config2_str.splitlines(),
            lineterm="",
        )
    )
    return diff_lines[:max_lines]


def _to_iso(value: Any) -> str | None:
    if hasattr(value, "isoformat"):
        return value.isoformat()
    return str(value) if value is not None else None


def _finalize_history_failure(output: OutputManager, errors: Iterable[str]) -> None:
    if output.format_type == "human":
        return

    output.finalize_history(
        status="failed",
        summary={"view": "error"},
        history=[],
        next_steps=[],
        errors=list(errors),
    )

