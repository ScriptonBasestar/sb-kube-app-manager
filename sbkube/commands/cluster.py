"""Cluster status management commands.

This module provides commands for managing and displaying Kubernetes cluster
status with caching support.
"""

import subprocess
import sys
import time
from pathlib import Path

import click
from rich.console import Console
from rich.table import Table

from sbkube.models.config_manager import ConfigManager
from sbkube.utils.cluster_cache import ClusterCache
from sbkube.utils.cluster_status import ClusterStatusCollector

# Constants
WATCH_INTERVAL_SECONDS = 10
DEFAULT_CACHE_TTL_SECONDS = 300

console = Console()


@click.group()
def cluster():
    """Cluster status management commands."""
    pass


@cluster.command()
@click.option(
    "--base-dir",
    type=click.Path(exists=True, file_okay=False, dir_okay=True, resolve_path=True),
    default=".",
    help="Base directory containing sources.yaml (default: current directory)",
)
@click.option(
    "--refresh",
    is_flag=True,
    help="Force refresh cache by collecting live cluster status",
)
@click.option(
    "--watch",
    is_flag=True,
    help="Auto-refresh cache every 10 seconds (Ctrl+C to stop)",
)
@click.pass_context
def status(ctx, base_dir: str, refresh: bool, watch: bool):
    """Display cluster-wide status (cached or live).

    This command collects and displays comprehensive Kubernetes cluster information
    including nodes, namespaces, and Helm releases. The data is cached locally
    with a 5-minute TTL (Time To Live) for faster subsequent queries.

    Examples:
        # Show cached status (or collect if cache expired)
        sbkube cluster status

        # Force refresh cache with live data
        sbkube cluster status --refresh

        # Auto-refresh every 10 seconds
        sbkube cluster status --watch

        # Use specific base directory
        sbkube cluster status --base-dir /path/to/config
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

    # Handle watch mode
    if watch:
        console.print(
            f"[cyan]Watching cluster status (updates every {WATCH_INTERVAL_SECONDS} seconds)[/cyan]"
        )
        console.print("[dim]Press Ctrl+C to stop[/dim]\n")
        try:
            while True:
                _collect_and_cache(collector, cache, force_refresh=True)
                _display_status(cache, show_cache_info=False)
                console.print(f"\n[dim]Next update in {WATCH_INTERVAL_SECONDS} seconds...[/dim]")
                time.sleep(WATCH_INTERVAL_SECONDS)
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

    _display_status(cache, show_cache_info=True)


def _collect_and_cache(
    collector: ClusterStatusCollector, cache: ClusterCache, force_refresh: bool = False
) -> None:
    """Collect cluster status and save to cache.

    Args:
        collector: ClusterStatusCollector instance
        cache: ClusterCache instance
        force_refresh: Whether this is a forced refresh (affects messaging)
    """
    action = "Refreshing" if force_refresh else "Collecting"
    console.print(f"[cyan]{action} cluster status...[/cyan]")

    try:
        status_data = collector.collect_all()
        cache.save(status_data)
        console.print("[green]✓ Status collected successfully[/green]\n")
    except subprocess.TimeoutExpired:
        console.print("[yellow]⏱️ Command timeout - kubectl/helm took too long[/yellow]")
        if cache.exists():
            console.print("[yellow]Using existing cache file (may be outdated)[/yellow]\n")
        else:
            console.print("[red]No cache available to fall back on[/red]")
            sys.exit(1)
    except subprocess.CalledProcessError as e:
        console.print(f"[red]kubectl/helm error: {e.stderr if e.stderr else e}[/red]")
        if cache.exists():
            console.print("[yellow]Using existing cache file (may be outdated)[/yellow]\n")
        else:
            console.print("[red]No cache available to fall back on[/red]")
            sys.exit(1)
    except Exception as e:
        console.print(f"[red]Unexpected error: {e}[/red]")
        if cache.exists():
            console.print("[yellow]Using existing cache file (may be outdated)[/yellow]\n")
        else:
            console.print("[red]No cache available to fall back on[/red]")
            sys.exit(1)


def _display_status(cache: ClusterCache, show_cache_info: bool = True) -> None:
    """Display cluster status from cache.

    Args:
        cache: ClusterCache instance
        show_cache_info: Whether to show cache metadata

    Raises:
        SystemExit: If no cached data is available (exit code 1)
    """
    data = cache.load()
    if not data:
        console.print("[red]Error: No cached data available[/red]")
        sys.exit(1)

    # Header
    cluster_name = data.get("cluster_name", "unknown")
    context = data.get("context", "unknown")
    console.print(f"[bold cyan]Cluster Status: {cluster_name}[/bold cyan] (context: {context})")

    # Build summary table
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
    helm_releases = data.get("helm_releases", [])
    if helm_releases:
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

    # Cache metadata (optional)
    if show_cache_info:
        console.print(f"\n[dim]Cache file: {cache.cache_file}[/dim]")
        if age_seconds := cache.get_age_seconds():
            console.print(f"[dim]Last updated: {_format_age(age_seconds)} ago[/dim]")
        if remaining_ttl := cache.get_remaining_ttl():
            console.print(f"[dim]Cache expires in: {_format_duration(remaining_ttl)}[/dim]")


def _format_age(seconds: float | None) -> str:
    """Format age in seconds to human-readable string.

    Args:
        seconds: Age in seconds

    Returns:
        Formatted string (e.g., "2m 34s", "1h 23m")
    """
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
    """Format duration in seconds to human-readable string.

    Args:
        seconds: Duration in seconds

    Returns:
        Formatted string (e.g., "4m 23s")
    """
    return _format_age(seconds)
