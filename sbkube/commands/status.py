"""Application and cluster status management.

This command provides a unified view of deployed applications, combining
cluster status with deployment tracking information.

Replaces: sbkube cluster status (simplified)
"""

import sys
from pathlib import Path

import click
from rich.console import Console
from rich.table import Table
from rich.tree import Tree

from sbkube.models.config_manager import ConfigManager
from sbkube.state.database import DeploymentDatabase
from sbkube.utils.cluster_cache import ClusterCache
from sbkube.utils.cluster_grouping import (filter_by_app_group,
                                           get_app_group_summary,
                                           group_releases_by_app_group)
from sbkube.utils.cluster_status import ClusterStatusCollector

console = Console()

DEFAULT_CACHE_TTL_SECONDS = 300


@click.command(name="status")
@click.option(
    "--base-dir",
    type=click.Path(exists=True, file_okay=False, dir_okay=True, resolve_path=True),
    default=".",
    help="Base directory containing sources.yaml",
)
@click.option(
    "--by-group",
    is_flag=True,
    help="Group applications by app-group (Feature: app-group classification)",
)
@click.option(
    "--managed",
    is_flag=True,
    help="Show only sbkube-managed applications",
)
@click.option(
    "--all",
    "show_all",
    is_flag=True,
    help="Show all cluster resources including unmanaged ones (default)",
)
@click.option(
    "--unhealthy",
    is_flag=True,
    help="Show only unhealthy resources",
)
@click.option(
    "--refresh",
    is_flag=True,
    help="Force refresh cache by collecting live cluster status",
)
@click.option(
    "--watch",
    is_flag=True,
    help="Auto-refresh status every 10 seconds (Ctrl+C to stop)",
)
@click.option(
    "--deps",
    is_flag=True,
    help="Show dependency tree (Phase 6)",
)
@click.option(
    "--health-check",
    is_flag=True,
    help="Show detailed health check status (Phase 7)",
)
@click.argument("app_group", required=False)
@click.pass_context
def cmd(
    ctx,
    base_dir: str,
    by_group: bool,
    managed: bool,
    show_all: bool,
    unhealthy: bool,
    refresh: bool,
    watch: bool,
    deps: bool,
    health_check: bool,
    app_group: str | None,
):
    """Display application and cluster status.

    This command shows the current state of deployed applications and cluster
    resources. Data is cached locally with a 5-minute TTL for faster queries.

    \b
    Examples:
        # Show overall summary
        sbkube status

        # Group by app-group
        sbkube status --by-group

        # Show specific app-group
        sbkube status app_000_infra_network

        # Show only sbkube-managed apps
        sbkube status --managed

        # Show dependency tree (Phase 6)
        sbkube status --deps

        # Show dependency tree for specific app-group
        sbkube status app_000_infra_network --deps

        # Show health check details (Phase 7)
        sbkube status --health-check

        # Combine options
        sbkube status --by-group --health-check

        # Force refresh cache
        sbkube status --refresh

        # Watch mode (auto-refresh every 10s)
        sbkube status --watch
    """
    base_path = Path(base_dir)
    sources_file = base_path / "sources.yaml"

    # Load sources.yaml
    if not sources_file.exists():
        console.print(f"[red]Error: sources.yaml not found in {base_dir}[/red]")
        console.print(
            "\n[yellow]Hint: Run 'sbkube init' to create a sources.yaml file[/yellow]"
        )
        sys.exit(1)

    try:
        config_manager = ConfigManager(base_path)
        sources = config_manager.load_sources()
    except Exception as e:
        console.print(f"[red]Error: Failed to load sources.yaml: {e}[/red]")
        sys.exit(1)

    # Validate required fields
    if not sources.kubeconfig:
        console.print(
            "[red]Error: 'kubeconfig' field is required in sources.yaml[/red]"
        )
        sys.exit(1)

    if not sources.kubeconfig_context:
        console.print(
            "[red]Error: 'kubeconfig_context' field is required in sources.yaml[/red]"
        )
        sys.exit(1)

    # Initialize cache and collector
    cache_dir = base_path / ".sbkube" / "cluster_status"
    cache = ClusterCache(
        cache_dir=cache_dir,
        context=sources.kubeconfig_context,
        cluster=sources.cluster or "unknown",
    )
    collector = ClusterStatusCollector(
        kubeconfig=sources.kubeconfig,
        context=sources.kubeconfig_context,
    )

    # Phase 6: Handle --deps mode
    if deps:
        _display_dependency_tree(base_path, app_group)
        return

    # Handle watch mode
    if watch:
        import time

        console.print("[cyan]Watching status (updates every 10 seconds)[/cyan]")
        console.print("[dim]Press Ctrl+C to stop[/dim]\n")
        try:
            while True:
                _collect_and_cache(collector, cache, force_refresh=True)
                _display_status(
                    cache,
                    by_group=by_group,
                    managed=managed,
                    show_all=show_all,
                    unhealthy=unhealthy,
                    app_group=app_group,
                    show_cache_info=False,
                    health_check=health_check,
                )
                console.print("\n[dim]Next update in 10 seconds...[/dim]")
                time.sleep(10)
        except KeyboardInterrupt:
            console.print("\n[yellow]Stopped watching.[/yellow]")
            sys.exit(0)

    # Normal mode: check cache or refresh
    if refresh or not cache.is_valid():
        _collect_and_cache(collector, cache, force_refresh=refresh)
    else:
        console.print(
            f"[dim]Using cached data (collected {_format_age(cache.get_age_seconds())} ago)[/dim]\n"
        )

    _display_status(
        cache,
        by_group=by_group,
        managed=managed,
        show_all=show_all,
        unhealthy=unhealthy,
        app_group=app_group,
        show_cache_info=True,
        health_check=health_check,
    )


def _collect_and_cache(
    collector: ClusterStatusCollector, cache: ClusterCache, force_refresh: bool = False
) -> None:
    """Collect cluster status and save to cache."""
    import subprocess

    action = "Refreshing" if force_refresh else "Collecting"
    console.print(f"[cyan]{action} cluster status...[/cyan]")

    try:
        status_data = collector.collect_all()
        cache.save(status_data)
        console.print("[green]✓ Status collected successfully[/green]\n")
    except subprocess.TimeoutExpired:
        console.print("[yellow]⏱️ Command timeout - kubectl/helm took too long[/yellow]")
        if cache.exists():
            console.print(
                "[yellow]Using existing cache file (may be outdated)[/yellow]\n"
            )
        else:
            console.print("[red]No cache available to fall back on[/red]")
            sys.exit(1)
    except subprocess.CalledProcessError as e:
        console.print(f"[red]kubectl/helm error: {e.stderr if e.stderr else e}[/red]")
        if cache.exists():
            console.print(
                "[yellow]Using existing cache file (may be outdated)[/yellow]\n"
            )
        else:
            console.print("[red]No cache available to fall back on[/red]")
            sys.exit(1)
    except Exception as e:
        console.print(f"[red]Unexpected error: {e}[/red]")
        if cache.exists():
            console.print(
                "[yellow]Using existing cache file (may be outdated)[/yellow]\n"
            )
        else:
            console.print("[red]No cache available to fall back on[/red]")
            sys.exit(1)


def _display_status(
    cache: ClusterCache,
    by_group: bool = False,
    managed: bool = False,
    show_all: bool = False,
    unhealthy: bool = False,
    app_group: str | None = None,
    show_cache_info: bool = True,
    health_check: bool = False,
) -> None:
    """Display cluster status from cache."""
    data = cache.load()
    if not data:
        console.print("[red]Error: No cached data available[/red]")
        sys.exit(1)

    # Header
    cluster_name = data.get("cluster_name", "unknown")
    context = data.get("context", "unknown")
    console.print(
        f"[bold cyan]Status: {cluster_name}[/bold cyan] (context: {context})\n"
    )

    # Get Helm releases
    helm_releases = data.get("helm_releases", [])

    # Phase 4: Implement app-group grouping
    if by_group or app_group or managed:
        _display_grouped_status(
            data=data,
            helm_releases=helm_releases,
            by_group=by_group,
            managed=managed,
            app_group=app_group,
            unhealthy=unhealthy,
            health_check=health_check,
        )
    else:
        # Standard summary view
        _display_summary_status(data, helm_releases, unhealthy, health_check)

    # Show cache metadata at the end
    _display_cache_info(cache, show_cache_info)


def _display_summary_status(
    data: dict,
    helm_releases: list[dict],
    unhealthy: bool = False,
    health_check: bool = False,
) -> None:
    """Display standard summary status table."""
    table = Table(show_header=True, header_style="bold magenta", border_style="dim")
    table.add_column("Resource", style="cyan", width=20)
    table.add_column("Status", style="white", width=50)

    # Cluster info
    cluster_info = data.get("cluster_info", {})
    if api_server := cluster_info.get("api_server"):
        table.add_row("API Server", api_server)
    if version := cluster_info.get("version"):
        table.add_row("Kubernetes", version)

    # Nodes
    nodes = data.get("nodes", [])
    if nodes:
        ready_count = sum(1 for node in nodes if node.get("status") == "Ready")
        total_count = len(nodes)
        status_color = "green" if ready_count == total_count else "yellow"
        table.add_row(
            "Nodes",
            f"[{status_color}]{ready_count} Ready[/{status_color}] / {total_count} Total",
        )
    else:
        table.add_row("Nodes", "[dim]No nodes found[/dim]")

    # Namespaces
    namespaces = data.get("namespaces", [])
    table.add_row("Namespaces", str(len(namespaces)))

    # Helm releases
    if helm_releases:
        # Filter unhealthy if requested
        if unhealthy:
            helm_releases = [
                r
                for r in helm_releases
                if r.get("status") not in ["deployed", "superseded"]
            ]

        status_count: dict[str, int] = {}
        for release in helm_releases:
            status = release.get("status", "unknown")
            status_count[status] = status_count.get(status, 0) + 1

        status_summary = ", ".join(
            f"{count} {status}" for status, count in sorted(status_count.items())
        )
        table.add_row("Helm Releases", f"{len(helm_releases)} ({status_summary})")
    else:
        table.add_row("Helm Releases", "[dim]No releases found[/dim]")

    console.print(table)
    console.print()

    # Phase 7: Health check details
    if health_check:
        _display_health_check_details(data)


def _display_grouped_status(
    data: dict,
    helm_releases: list[dict],
    by_group: bool = False,
    managed: bool = False,
    app_group: str | None = None,
    unhealthy: bool = False,
    health_check: bool = False,
) -> None:
    """Display app-group grouped status."""
    try:
        # Initialize State DB
        db = DeploymentDatabase()
    except Exception:
        db = None
        console.print(
            "[yellow]⚠️ Could not connect to State DB, grouping may be incomplete[/yellow]\n"
        )

    # Group releases
    grouped_data = group_releases_by_app_group(helm_releases, db)

    # Filter by specific app-group
    if app_group:
        group_data = filter_by_app_group(grouped_data, app_group)
        if not group_data:
            console.print(f"[red]App-group not found: {app_group}[/red]")
            console.print("\n[dim]Available app-groups:[/dim]")
            for ag in grouped_data.get("managed_app_groups", {}).keys():
                console.print(f"  - {ag}")
            return

        _display_single_app_group(app_group, group_data)
        return

    # Display all app-groups
    managed_groups = grouped_data.get("managed_app_groups", {})
    unmanaged = grouped_data.get("unmanaged_releases", [])
    summary = get_app_group_summary(grouped_data)

    # Filter managed only
    if managed:
        unmanaged = []

    # Filter unhealthy if requested
    if unhealthy:
        managed_groups = {
            ag: gdata
            for ag, gdata in managed_groups.items()
            if gdata["summary"]["failed"] > 0
        }

    # Display summary
    console.print(f"[bold]App Groups:[/bold] {summary['total_app_groups']}")
    console.print(f"[bold]Managed Releases:[/bold] {summary['total_managed_releases']}")
    if not managed:
        console.print(
            f"[bold]Unmanaged Releases:[/bold] {summary['total_unmanaged_releases']}"
        )
    console.print(
        f"[bold]Overall Health:[/bold] {_format_health(summary['overall_health'])}\n"
    )

    # Display each app-group
    for ag_name in sorted(managed_groups.keys()):
        group_data = managed_groups[ag_name]
        _display_app_group_summary(ag_name, group_data)

    # Display unmanaged releases
    if unmanaged and not managed:
        console.print("\n[bold yellow]Unmanaged Releases:[/bold yellow]")
        table = Table(show_header=True, border_style="dim")
        table.add_column("Name", style="cyan")
        table.add_column("Namespace", style="white")
        table.add_column("Status", style="white")

        for rel in unmanaged:
            table.add_row(
                rel["name"],
                rel["namespace"],
                _format_release_status(rel["status"]),
            )
        console.print(table)
        console.print()


def _display_single_app_group(app_group: str, group_data: dict) -> None:
    """Display detailed information for a single app-group."""
    console.print(f"[bold cyan]App Group: {app_group}[/bold cyan]")
    console.print(f"Namespace: {group_data.get('namespace', 'N/A')}")

    summary = group_data.get("summary", {})
    console.print(f"Total Apps: {summary.get('total_apps', 0)}")
    console.print(f"Healthy: [green]{summary.get('healthy', 0)}[/green]")
    console.print(f"Failed: [red]{summary.get('failed', 0)}[/red]\n")

    # Display apps table
    apps = group_data.get("apps", {})
    if apps:
        table = Table(show_header=True, border_style="dim")
        table.add_column("App", style="cyan", width=30)
        table.add_column("Chart", style="white", width=40)
        table.add_column("Status", style="white", width=15)

        for app_name, app_info in sorted(apps.items()):
            table.add_row(
                app_name,
                app_info.get("chart", "unknown"),
                _format_release_status(app_info.get("status", "unknown")),
            )
        console.print(table)
        console.print()


def _display_app_group_summary(app_group: str, group_data: dict) -> None:
    """Display summary for an app-group."""
    summary = group_data.get("summary", {})
    total = summary.get("total_apps", 0)
    healthy = summary.get("healthy", 0)
    failed = summary.get("failed", 0)

    # Status icon
    if failed == 0:
        icon = "✅"
        color = "green"
    elif failed < healthy:
        icon = "⚠️"
        color = "yellow"
    else:
        icon = "❌"
        color = "red"

    console.print(
        f"{icon} [{color}]{app_group}[/{color}] "
        f"({healthy}/{total} healthy, {failed} failed)"
    )


def _format_health(health: str) -> str:
    """Format health status with color."""
    if health == "healthy":
        return "[green]✅ Healthy[/green]"
    elif health == "degraded":
        return "[yellow]⚠️ Degraded[/yellow]"
    else:
        return "[red]❌ Unhealthy[/red]"


def _format_release_status(status: str) -> str:
    """Format Helm release status with color."""
    status_map = {
        "deployed": "[green]deployed[/green]",
        "superseded": "[dim]superseded[/dim]",
        "failed": "[red]failed[/red]",
        "pending-install": "[yellow]pending-install[/yellow]",
        "pending-upgrade": "[yellow]pending-upgrade[/yellow]",
        "uninstalled": "[dim]uninstalled[/dim]",
    }
    return status_map.get(status, status)


def _display_cache_info(cache: ClusterCache, show: bool) -> None:
    """Display cache metadata."""
    if not show:
        return

    console.print(f"\n[dim]Cache file: {cache.cache_file}[/dim]")
    if age_seconds := cache.get_age_seconds():
        console.print(f"[dim]Last updated: {_format_age(age_seconds)} ago[/dim]")
    if remaining_ttl := cache.get_remaining_ttl():
        console.print(f"[dim]Cache expires in: {_format_duration(remaining_ttl)}[/dim]")


def _format_age(seconds: float | None) -> str:
    """Format age in seconds to human-readable string."""
    if seconds is None:
        return "unknown"

    if seconds < 60:
        return f"{int(seconds)}s"
    elif seconds < 3600:
        minutes = int(seconds / 60)
        remaining_seconds = int(seconds % 60)
        return f"{minutes}m {remaining_seconds}s"
    else:
        hours = int(seconds / 3600)
        minutes = int((seconds % 3600) / 60)
        return f"{hours}h {minutes}m"


def _format_duration(seconds: float) -> str:
    """Format duration in seconds to human-readable string."""
    return _format_age(seconds)


def _display_dependency_tree(base_path: Path, app_group: str | None) -> None:
    """Display dependency tree for applications (Phase 6)."""
    console.print("\n[bold cyan]🔗 Dependency Tree[/bold cyan]\n")

    try:
        config_manager = ConfigManager(base_path)
        config = config_manager.load_config()
    except Exception as e:
        console.print(f"[red]Error loading config: {e}[/red]")
        sys.exit(1)

    if not config.apps:
        console.print("[yellow]No applications found in config.yaml[/yellow]")
        return

    # Build dependency map
    dep_map = _build_dependency_map(config.apps)

    # Detect circular dependencies
    circular = _detect_circular_dependencies(dep_map)
    if circular:
        console.print("[red]⚠️  Circular dependencies detected:[/red]")
        for cycle in circular:
            console.print(f"  [red]• {' → '.join(cycle)}[/red]")
        console.print()

    # Filter by app_group if specified
    apps_to_show = config.apps
    if app_group:
        apps_to_show = [app for app in config.apps if app.name.startswith(app_group)]
        if not apps_to_show:
            console.print(f"[yellow]No apps found for app-group: {app_group}[/yellow]")
            return

    # Find root apps (apps with no dependencies or all deps satisfied)
    root_apps = _find_root_apps(apps_to_show, dep_map)

    if not root_apps:
        console.print("[yellow]No root applications found[/yellow]")
        return

    # Build and display tree
    tree = Tree("📦 Applications")
    visited = set()

    for root_app in root_apps:
        _add_tree_node(tree, root_app, dep_map, visited, circular)

    console.print(tree)
    console.print()

    # Statistics
    total_apps = len(apps_to_show)
    apps_with_deps = sum(1 for app in apps_to_show if dep_map.get(app.name))
    console.print(
        f"[dim]Total: {total_apps} apps, {apps_with_deps} with dependencies[/dim]"
    )


def _build_dependency_map(apps: list) -> dict[str, list[str]]:
    """Build a reverse dependency map (dependent -> dependencies)."""
    dep_map = {}
    for app in apps:
        deps = getattr(app, "deps", None) or []
        if deps:
            dep_map[app.name] = deps
    return dep_map


def _detect_circular_dependencies(dep_map: dict[str, list[str]]) -> list[list[str]]:
    """Detect circular dependencies using DFS."""
    circular = []
    visited = set()
    rec_stack = set()

    def dfs(node: str, path: list[str]) -> None:
        if node in rec_stack:
            # Found a cycle
            cycle_start = path.index(node)
            cycle = path[cycle_start:] + [node]
            circular.append(cycle)
            return

        if node in visited:
            return

        visited.add(node)
        rec_stack.add(node)
        path.append(node)

        for dep in dep_map.get(node, []):
            dfs(dep, path[:])

        path.pop()
        rec_stack.remove(node)

    for app_name in dep_map.keys():
        if app_name not in visited:
            dfs(app_name, [])

    return circular


def _find_root_apps(apps: list, dep_map: dict[str, list[str]]) -> list:
    """Find root applications (no dependencies or not depended upon)."""
    all_deps = set()
    for deps in dep_map.values():
        all_deps.update(deps)

    # Apps that are not dependencies of others, or have no deps themselves
    roots = []
    for app in apps:
        if not dep_map.get(app.name):  # No dependencies
            roots.append(app)
        elif app.name not in all_deps:  # Not a dependency of others
            roots.append(app)

    # If no clear roots, return all apps without deps
    if not roots:
        roots = [app for app in apps if not dep_map.get(app.name)]

    return roots


def _add_tree_node(
    parent, app, dep_map: dict[str, list[str]], visited: set, circular: list
) -> None:
    """Recursively add tree nodes for dependencies."""
    if app.name in visited:
        parent.add(f"[dim]{app.name} (already shown)[/dim]")
        return

    visited.add(app.name)

    # Check if app is in a circular dependency
    is_circular = any(app.name in cycle for cycle in circular)
    color = "red" if is_circular else "green"

    deps = dep_map.get(app.name, [])
    if deps:
        node = parent.add(
            f"[{color}]{app.name}[/{color}] [dim]→ {len(deps)} deps[/dim]"
        )
        for dep_name in deps:
            # Find the dep app object
            dep_app = type("App", (), {"name": dep_name})()  # Mock app object
            _add_tree_node(node, dep_app, dep_map, visited, circular)
    else:
        parent.add(f"[{color}]{app.name}[/{color}] [dim](no deps)[/dim]")


def _display_health_check_details(data: dict) -> None:
    """Display detailed health check information for pods (Phase 7)."""
    console.print("\n[bold cyan]💊 Health Check Details[/bold cyan]\n")

    pods = data.get("pods", [])
    if not pods:
        console.print("[yellow]No pods found[/yellow]")
        return

    # Group pods by namespace
    pods_by_ns: dict[str, list[dict]] = {}
    for pod in pods:
        ns = pod.get("namespace", "default")
        if ns not in pods_by_ns:
            pods_by_ns[ns] = []
        pods_by_ns[ns].append(pod)

    for namespace, ns_pods in sorted(pods_by_ns.items()):
        console.print(f"[bold]Namespace: {namespace}[/bold]")

        table = Table(show_header=True, header_style="bold magenta", border_style="dim")
        table.add_column("Pod", style="cyan", width=30)
        table.add_column("Phase", width=12)
        table.add_column("Ready", width=10)
        table.add_column("Restarts", width=10)
        table.add_column("Health", width=50)

        for pod in ns_pods:
            pod_name = pod.get("name", "unknown")
            phase = pod.get("phase", "Unknown")
            ready = f"{pod.get('ready_containers', 0)}/{pod.get('total_containers', 0)}"
            restarts = str(pod.get("restart_count", 0))

            # Determine health status
            health_status = _get_pod_health_status(pod)
            health_icon = _get_health_icon(health_status)

            # Phase color
            phase_color = {
                "Running": "green",
                "Pending": "yellow",
                "Failed": "red",
                "Succeeded": "blue",
                "Unknown": "dim",
            }.get(phase, "white")

            table.add_row(
                pod_name,
                f"[{phase_color}]{phase}[/{phase_color}]",
                ready,
                restarts,
                f"{health_icon} {health_status}",
            )

        console.print(table)
        console.print()


def _get_pod_health_status(pod: dict) -> str:
    """Analyze pod health based on conditions and container statuses."""
    phase = pod.get("phase", "Unknown")
    ready_containers = pod.get("ready_containers", 0)
    total_containers = pod.get("total_containers", 1)
    restart_count = pod.get("restart_count", 0)
    conditions = pod.get("conditions", [])

    # Check for critical conditions
    issues = []

    if phase == "Failed":
        return "Pod failed"
    elif phase == "Pending":
        # Check for image pull errors or scheduling issues
        for cond in conditions:
            if cond.get("type") == "PodScheduled" and cond.get("status") != "True":
                reason = cond.get("reason", "Unknown")
                issues.append(f"Not scheduled: {reason}")
        if not issues:
            issues.append("Waiting to start")
    elif phase == "Running":
        # Check if all containers are ready
        if ready_containers < total_containers:
            issues.append(
                f"Only {ready_containers}/{total_containers} containers ready"
            )

        # Check for high restart count
        if restart_count > 5:
            issues.append(f"High restart count: {restart_count}")
        elif restart_count > 0:
            issues.append(f"Restarted {restart_count} time(s)")

        # Check Ready condition
        ready_cond = next((c for c in conditions if c.get("type") == "Ready"), None)
        if ready_cond and ready_cond.get("status") != "True":
            reason = ready_cond.get("reason", "NotReady")
            issues.append(f"Not ready: {reason}")

    if issues:
        return ", ".join(issues)
    elif phase == "Running" and ready_containers == total_containers:
        return "Healthy"
    elif phase == "Succeeded":
        return "Completed"
    else:
        return phase


def _get_health_icon(health_status: str) -> str:
    """Get appropriate icon for health status."""
    if "Healthy" in health_status:
        return "✅"
    elif "Completed" in health_status:
        return "🏁"
    elif "failed" in health_status.lower():
        return "❌"
    elif "Not ready" in health_status or "Only" in health_status:
        return "⚠️"
    elif "Waiting" in health_status or "Pending" in health_status:
        return "⏳"
    elif "restart" in health_status.lower():
        return "🔄"
    else:
        return "ℹ️"
