"""Check for available Helm chart updates.

This command checks if newer versions of Helm charts are available
for deployed applications. It compares the currently deployed version
with the latest available version in configured Helm repositories.
"""

from __future__ import annotations

import re
from dataclasses import dataclass
from pathlib import Path

import click
from packaging.version import InvalidVersion
from rich.table import Table

from sbkube.models.config_manager import ConfigManager
from sbkube.utils.helm_util import (
    get_all_helm_releases,
    get_latest_chart_version,
    search_helm_chart,
)
from sbkube.utils.output_manager import OutputManager
from sbkube.utils.version_compare import (
    VersionComparison,
    compare_versions,
    get_version_diff,
)


@dataclass
class ChartUpdate:
    """Information about a chart update."""

    name: str
    namespace: str
    current_version: str
    latest_version: str
    comparison: VersionComparison
    is_major: bool
    is_minor: bool
    is_patch: bool
    repo_name: str
    chart_name: str


@click.command(name="check-updates")
@click.option(
    "--base-dir",
    type=click.Path(exists=True, file_okay=False, dir_okay=True, resolve_path=True),
    default=".",
    help="Base directory containing sources.yaml",
)
@click.option(
    "--all",
    "check_all",
    is_flag=True,
    help="Check all Helm releases in cluster (not just sbkube-managed apps)",
)
@click.option(
    "--update-config",
    is_flag=True,
    help="Update config.yaml with latest versions (prompts for confirmation)",
)
@click.pass_context
def cmd(
    ctx,
    base_dir: str,
    check_all: bool,
    update_config: bool,
) -> None:
    """Check for available Helm chart updates.

    By default, checks only sbkube-managed applications defined in config.yaml.
    Use --all to check all Helm releases in the cluster.

    Examples:
        sbkube check-updates
        sbkube check-updates --all
        sbkube check-updates --update-config
    """
    output_format = ctx.obj.get("format", "human")
    kubeconfig = ctx.obj.get("kubeconfig")
    context = ctx.obj.get("context")

    output = OutputManager(format_type=output_format)

    try:
        base_path = Path(base_dir)
        config_manager = ConfigManager(base_path=base_path)

        # Load sources.yaml
        sources = config_manager.load_sources()
        if not sources:
            output.print_error("sources.yaml not found or empty")
            output.finalize(
                status="error", summary={"error": "sources.yaml not found"}
            )
            return

        # Get Helm repositories
        helm_repos = sources.helm_repos or {}

        if check_all:
            output.print_section("Checking All Cluster Helm Releases")
            updates = _check_all_releases(
                helm_repos, kubeconfig, context, output, output_format
            )
        else:
            output.print_section("Checking SBKube-Managed Applications")
            config = config_manager.load_config()
            if not config or not config.apps:
                output.print_error("No applications defined in config.yaml")
                output.finalize(status="error", summary={"error": "No apps defined"})
                return

            updates = _check_sbkube_apps(
                config.apps, helm_repos, kubeconfig, context, output, output_format
            )

        # Display results
        _display_updates(updates, output, output_format)

        # Handle config update if requested
        if update_config and updates:
            _handle_config_update(base_path, updates, output)

        # Finalize output
        summary = {
            "total_checked": len(updates) + sum(
                1 for u in updates if u.comparison == VersionComparison.SAME
            ),
            "updates_available": len([u for u in updates if u.comparison == VersionComparison.OUTDATED]),
            "up_to_date": len([u for u in updates if u.comparison == VersionComparison.SAME]),
        }
        output.finalize(status="success", summary=summary)

    except Exception as e:
        output.print_error(f"Error checking updates: {e}")
        output.finalize(status="error", summary={"error": str(e)})


def _check_all_releases(
    helm_repos: dict,
    kubeconfig: str | None,
    context: str | None,
    output: OutputManager,
    output_format: str,
) -> list[ChartUpdate]:
    """Check all Helm releases in the cluster."""
    updates: list[ChartUpdate] = []

    try:
        releases = get_all_helm_releases(context=context, kubeconfig=kubeconfig)
    except Exception as e:
        output.print_error(f"Failed to get Helm releases: {e}")
        return updates

    output.print(f"Found {len(releases)} Helm releases")

    for release in releases:
        name = release.get("name", "")
        namespace = release.get("namespace", "")
        chart = release.get("chart", "")

        # Parse chart string (format: "chart-name-version")
        chart_info = _parse_chart_string(chart)
        if not chart_info:
            continue

        chart_name, current_version = chart_info

        # Try to find chart in known repositories
        repo_name = _find_chart_repo(chart_name, helm_repos)
        if not repo_name:
            if output_format == "human":
                output.print(
                    f"  [dim]⊘ {name}: Repository not found for {chart_name}[/dim]"
                )
            continue

        # Check for updates
        update_info = _check_chart_update(
            name, namespace, repo_name, chart_name, current_version
        )
        if update_info:
            updates.append(update_info)
            if output_format == "human":
                _print_update_info(update_info, output)

    return updates


def _check_sbkube_apps(
    apps: dict,
    helm_repos: dict,
    kubeconfig: str | None,
    context: str | None,
    output: OutputManager,
    output_format: str,
) -> list[ChartUpdate]:
    """Check sbkube-managed applications."""
    updates: list[ChartUpdate] = []

    # Get deployed releases for comparison
    try:
        all_releases = get_all_helm_releases(context=context, kubeconfig=kubeconfig)
        release_map = {
            f"{r.get('namespace', '')}/{r.get('name', '')}": r for r in all_releases
        }
    except Exception as e:
        output.print_error(f"Failed to get Helm releases: {e}")
        release_map = {}

    output.print(f"Checking {len(apps)} configured applications")

    for app_name, app_config in apps.items():
        # Only check Helm apps
        if app_config.type != "helm":
            continue

        # Parse chart specification
        chart = app_config.chart
        if not chart or "/" not in chart:
            continue

        repo_name, chart_name = chart.split("/", 1)

        # Get current version from deployment or config
        namespace = app_config.namespace or "default"
        release_key = f"{namespace}/{app_name}"
        release = release_map.get(release_key)

        if release:
            # Get version from deployed release
            chart_str = release.get("chart", "")
            chart_info = _parse_chart_string(chart_str)
            current_version = chart_info[1] if chart_info else app_config.version
        else:
            # Use config version
            current_version = app_config.version

        if not current_version:
            if output_format == "human":
                output.print(f"  [dim]⊘ {app_name}: No version specified[/dim]")
            continue

        # Check for updates
        update_info = _check_chart_update(
            app_name, namespace, repo_name, chart_name, current_version
        )
        if update_info:
            updates.append(update_info)
            if output_format == "human":
                _print_update_info(update_info, output)

    return updates


def _parse_chart_string(chart: str) -> tuple[str, str] | None:
    """Parse chart string like 'nginx-1.0.0' into ('nginx', '1.0.0')."""
    # Pattern: chart-name-version (version is semantic version)
    pattern = r"^(.+)-(\d+\.\d+\.\d+.*)$"
    match = re.match(pattern, chart)
    if match:
        return match.group(1), match.group(2)
    return None


def _find_chart_repo(chart_name: str, helm_repos: dict) -> str | None:
    """Find repository name for a chart by searching."""
    for repo_name in helm_repos.keys():
        try:
            results = search_helm_chart(repo_name, chart_name)
            if results:
                return repo_name
        except Exception:
            continue
    return None


def _check_chart_update(
    name: str,
    namespace: str,
    repo_name: str,
    chart_name: str,
    current_version: str,
) -> ChartUpdate | None:
    """Check if an update is available for a chart."""
    try:
        latest_version = get_latest_chart_version(repo_name, chart_name)
        if not latest_version:
            return None

        version_diff = get_version_diff(current_version, latest_version)

        return ChartUpdate(
            name=name,
            namespace=namespace,
            current_version=current_version,
            latest_version=latest_version,
            comparison=version_diff.comparison,
            is_major=version_diff.is_major_update,
            is_minor=version_diff.is_minor_update,
            is_patch=version_diff.is_patch_update,
            repo_name=repo_name,
            chart_name=chart_name,
        )
    except (InvalidVersion, Exception):
        return None


def _print_update_info(update: ChartUpdate, output: OutputManager) -> None:
    """Print update information for a single chart."""
    if update.comparison == VersionComparison.OUTDATED:
        update_type = "major" if update.is_major else "minor" if update.is_minor else "patch"
        icon = "🔴" if update.is_major else "🟡" if update.is_minor else "🟢"
        output.print(
            f"  {icon} {update.name}: {update.current_version} → {update.latest_version} ({update_type})"
        )
    elif update.comparison == VersionComparison.SAME:
        output.print(f"  ✓ {update.name}: {update.current_version} (up to date)")


def _display_updates(
    updates: list[ChartUpdate], output: OutputManager, output_format: str
) -> None:
    """Display update results in a table."""
    if output_format != "human":
        return

    outdated = [u for u in updates if u.comparison == VersionComparison.OUTDATED]

    if not outdated:
        output.print("\n[green]✓ All applications are up to date![/green]\n")
        return

    output.print_section(f"\n{len(outdated)} Updates Available")

    console = output.get_console()
    table = Table(show_header=True, header_style="bold magenta", border_style="dim")
    table.add_column("Application", style="cyan")
    table.add_column("Namespace", style="dim")
    table.add_column("Current", style="yellow")
    table.add_column("Latest", style="green")
    table.add_column("Type", style="white")
    table.add_column("Upgrade Command", style="blue")

    for update in outdated:
        update_type = (
            "Major 🔴"
            if update.is_major
            else "Minor 🟡"
            if update.is_minor
            else "Patch 🟢"
        )
        upgrade_cmd = f"sbkube upgrade {update.name} --version {update.latest_version}"

        table.add_row(
            update.name,
            update.namespace,
            update.current_version,
            update.latest_version,
            update_type,
            upgrade_cmd,
        )

    console.print(table)
    output.print("")


def _handle_config_update(
    base_path: Path, updates: list[ChartUpdate], output: OutputManager
) -> None:
    """Handle config.yaml update with user confirmation."""
    outdated = [u for u in updates if u.comparison == VersionComparison.OUTDATED]
    if not outdated:
        output.print("[green]No updates to apply to config.yaml[/green]")
        return

    output.print_section("Config Update")
    output.print(f"Found {len(outdated)} applications with available updates:")
    for update in outdated:
        output.print(
            f"  • {update.name}: {update.current_version} → {update.latest_version}"
        )

    if not click.confirm("\nUpdate config.yaml with latest versions?", default=False):
        output.print("[yellow]Config update cancelled[/yellow]")
        return

    # Load config
    config_manager = ConfigManager(base_path=base_path)
    config_path = base_path / "config.yaml"

    if not config_path.exists():
        output.print_error("config.yaml not found")
        return

    # Read config file
    with config_path.open("r") as f:
        config_content = f.read()

    # Update versions
    updated_content = config_content
    for update in outdated:
        # Pattern: version: "1.0.0" or version: 1.0.0
        old_pattern = f'version: "{update.current_version}"'
        new_pattern = f'version: "{update.latest_version}"'
        updated_content = updated_content.replace(old_pattern, new_pattern)

        old_pattern = f"version: {update.current_version}"
        new_pattern = f'version: "{update.latest_version}"'
        updated_content = updated_content.replace(old_pattern, new_pattern)

    # Write updated config
    if updated_content != config_content:
        with config_path.open("w") as f:
            f.write(updated_content)
        output.print_success(
            f"[green]✓ Updated config.yaml with {len(outdated)} new versions[/green]"
        )
    else:
        output.print_warning("[yellow]No changes made to config.yaml[/yellow]")
