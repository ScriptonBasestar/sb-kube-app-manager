"""Deployment history management.

This command displays the history of deployments tracked by sbkube,
allowing users to review past deployments and their outcomes.

Replaces: sbkube state list, sbkube state show
"""

import click

from sbkube.state.database import DeploymentDatabase
from sbkube.utils.logger import logger


@click.command(name="history")
@click.option("--cluster", help="Filter by cluster name")
@click.option("--namespace", "-n", help="Filter by namespace")
@click.option("--limit", default=20, help="Maximum number of deployments to show")
@click.option(
    "--format",
    type=click.Choice(["table", "json", "yaml"]),
    default="table",
    help="Output format",
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
def cmd(
    cluster: str | None,
    namespace: str | None,
    limit: int,
    format: str,
    deployment_id: str | None,
    diff_ids: str | None,
    values_diff_ids: str | None,
    app_group: str | None,
):
    """Display deployment history.

    Shows the history of deployments managed by sbkube, including deployment
    status, apps deployed, and timestamps.

    \b
    Examples:
        # Show recent deployments
        sbkube history

        # Show deployments for a specific cluster
        sbkube history --cluster production

        # Show deployments for a namespace
        sbkube history --namespace kube-system

        # Show detailed info for a deployment
        sbkube history --show dep_20250131_143022

        # Show history for a specific app-group
        sbkube history app_000_infra_network

        # Compare two deployments (Phase 5)
        sbkube history --diff dep_20250131_143022,dep_20250131_150000

        # Compare Helm values between deployments (Phase 5)
        sbkube history --values-diff dep_20250131_143022,dep_20250131_150000

        # Export history as JSON
        sbkube history --format json
    """
    try:
        db = DeploymentDatabase()

        # Phase 5: Compare Helm values
        if values_diff_ids:
            _show_values_diff(db, values_diff_ids, format)
            return

        # Phase 5: Compare two deployments
        if diff_ids:
            _show_deployment_diff(db, diff_ids, format)
            return

        # Show specific deployment details
        if deployment_id:
            _show_deployment_detail(db, deployment_id, format)
            return

        # Phase 5: Filter by app-group (완성)
        if app_group:
            logger.info(f"Filtering by app-group: {app_group}")

        # List deployments
        deployments = db.list_deployments(
            cluster=cluster,
            namespace=namespace,
            app_group=app_group,
            limit=limit,
        )

        if format == "table":
            _print_deployments_table(deployments)
        elif format == "json":
            import json

            data = [d.model_dump() for d in deployments]
            click.echo(json.dumps(data, indent=2, default=str))
        elif format == "yaml":
            import yaml

            data = [d.model_dump() for d in deployments]
            click.echo(yaml.dump(data, default_flow_style=False))

    except Exception as e:
        logger.error(f"Failed to retrieve deployment history: {e}")
        raise click.Abort()


def _show_deployment_detail(
    db: DeploymentDatabase, deployment_id: str, format: str
) -> None:
    """Show detailed information for a specific deployment."""
    deployment = db.get_deployment(deployment_id)

    if not deployment:
        logger.error(f"Deployment not found: {deployment_id}")
        raise click.Abort()

    if format == "json":
        import json

        click.echo(json.dumps(deployment.model_dump(), indent=2, default=str))
    elif format == "yaml":
        import yaml

        click.echo(yaml.dump(deployment.model_dump(), default_flow_style=False))
    else:
        # Detailed text output
        _print_deployment_detail(deployment)


def _print_deployments_table(deployments):
    """Print deployments in table format."""
    if not deployments:
        logger.info("No deployments found")
        return

    logger.heading("Deployment History")

    # Header
    header = f"{'ID':<30} {'Timestamp':<20} {'Cluster':<15} {'Namespace':<15} {'Status':<12} {'Apps':<10}"
    click.echo(header)
    click.echo("-" * len(header))

    # Rows
    for dep in deployments:
        timestamp = dep.timestamp.strftime("%Y-%m-%d %H:%M:%S")
        status_icon = {
            "success": "✅",
            "failed": "❌",
            "in_progress": "🔄",
            "rolled_back": "↩️",
            "partially_failed": "⚠️",
        }.get(dep.status.value, "❓")

        row = (
            f"{dep.deployment_id:<30} "
            f"{timestamp:<20} "
            f"{dep.cluster:<15} "
            f"{dep.namespace:<15} "
            f"{status_icon} {dep.status.value:<10} "
            f"{dep.success_count}/{dep.app_count:<8}"
        )
        click.echo(row)


def _print_deployment_detail(deployment):
    """Print detailed deployment information."""
    logger.heading(f"Deployment: {deployment.deployment_id}")

    click.echo(f"Timestamp: {deployment.timestamp}")
    click.echo(f"Cluster: {deployment.cluster}")
    click.echo(f"Namespace: {deployment.namespace}")
    click.echo(f"Config Dir: {deployment.app_config_dir}")
    click.echo(f"Status: {deployment.status.value}")

    if deployment.error_message:
        click.echo(f"Error: {deployment.error_message}")

    # Apps
    click.echo("\nApplications:")
    for app in deployment.apps:
        status_icon = "✅" if app["status"] == "success" else "❌"
        click.echo(f"  {status_icon} {app['name']} ({app['type']})")
        if app.get("error_message"):
            click.echo(f"     Error: {app['error_message']}")

    # Resources
    if deployment.resources:
        click.echo("\nResources:")
        for resource in deployment.resources:
            action_icon = {"create": "➕", "update": "📝", "delete": "➖"}.get(
                resource.action.value,
                "❓",
            )

            ns_str = f" -n {resource.namespace}" if resource.namespace else ""
            click.echo(f"  {action_icon} {resource.kind}/{resource.name}{ns_str}")

    # Helm releases
    if deployment.helm_releases:
        click.echo("\nHelm Releases:")
        for release in deployment.helm_releases:
            click.echo(
                f"  📦 {release.release_name} "
                f"(rev: {release.revision}, status: {release.status})"
            )


def _show_deployment_diff(
    db: DeploymentDatabase, diff_ids: str, format: str
) -> None:
    """Compare and show differences between two deployments."""
    try:
        id1, id2 = diff_ids.split(",")
        id1, id2 = id1.strip(), id2.strip()
    except ValueError:
        logger.error("Invalid --diff format. Use: --diff ID1,ID2")
        raise click.Abort()

    diff_result = db.get_deployment_diff(id1, id2)

    if not diff_result:
        logger.error(f"One or both deployments not found: {id1}, {id2}")
        raise click.Abort()

    if format == "json":
        import json

        click.echo(json.dumps(diff_result, indent=2, default=str))
    elif format == "yaml":
        import yaml

        click.echo(yaml.dump(diff_result, default_flow_style=False))
    else:
        # Detailed text output
        _print_deployment_diff(diff_result)


def _print_deployment_diff(diff_result: dict) -> None:
    """Print deployment comparison in readable format."""
    import difflib

    dep1 = diff_result["deployment1"]
    dep2 = diff_result["deployment2"]
    apps_diff = diff_result["apps_diff"]

    logger.heading("Deployment Comparison")

    # Basic info comparison
    click.echo(f"\n{'Field':<20} {'Deployment 1':<30} {'Deployment 2':<30}")
    click.echo("-" * 80)
    click.echo(f"{'ID':<20} {dep1['id']:<30} {dep2['id']:<30}")
    click.echo(f"{'Timestamp':<20} {str(dep1['timestamp']):<30} {str(dep2['timestamp']):<30}")
    click.echo(f"{'Cluster':<20} {dep1['cluster']:<30} {dep2['cluster']:<30}")
    click.echo(f"{'Namespace':<20} {dep1['namespace']:<30} {dep2['namespace']:<30}")
    click.echo(f"{'Status':<20} {dep1['status']:<30} {dep2['status']:<30}")
    click.echo(f"{'App Count':<20} {dep1['app_count']:<30} {dep2['app_count']:<30}")

    # Apps changes
    click.echo("\n📦 Application Changes:")
    if apps_diff["added"]:
        click.echo(f"  ➕ Added ({len(apps_diff['added'])}):")
        for app in apps_diff["added"]:
            click.echo(f"     • {app}")

    if apps_diff["removed"]:
        click.echo(f"  ➖ Removed ({len(apps_diff['removed'])}):")
        for app in apps_diff["removed"]:
            click.echo(f"     • {app}")

    if apps_diff["modified"]:
        click.echo(f"  📝 Modified ({len(apps_diff['modified'])}):")
        for app in apps_diff["modified"]:
            click.echo(f"     • {app}")

    # Config snapshot diff
    if dep1.get("config_snapshot") and dep2.get("config_snapshot"):
        click.echo("\n📄 Configuration Changes:")

        import yaml

        config1_str = yaml.dump(dep1["config_snapshot"], default_flow_style=False)
        config2_str = yaml.dump(dep2["config_snapshot"], default_flow_style=False)

        diff = difflib.unified_diff(
            config1_str.splitlines(keepends=True),
            config2_str.splitlines(keepends=True),
            fromfile=f"{dep1['id']} config",
            tofile=f"{dep2['id']} config",
            lineterm="",
        )

        diff_lines = list(diff)
        if diff_lines:
            for line in diff_lines[:50]:  # Limit to 50 lines
                if line.startswith("+"):
                    click.echo(click.style(line.rstrip(), fg="green"))
                elif line.startswith("-"):
                    click.echo(click.style(line.rstrip(), fg="red"))
                elif line.startswith("@@"):
                    click.echo(click.style(line.rstrip(), fg="cyan"))
                else:
                    click.echo(line.rstrip())

            if len(diff_lines) > 50:
                click.echo(f"\n... ({len(diff_lines) - 50} more lines)")
        else:
            click.echo("  No configuration changes detected")
    else:
        click.echo("\n📄 Configuration: Not available for comparison")


def _show_values_diff(
    db: DeploymentDatabase, values_diff_ids: str, format: str
) -> None:
    """Compare and show Helm values differences between two deployments."""
    try:
        id1, id2 = values_diff_ids.split(",")
        id1, id2 = id1.strip(), id2.strip()
    except ValueError:
        logger.error("Invalid --values-diff format. Use: --values-diff ID1,ID2")
        raise click.Abort()

    diff_result = db.get_deployment_values_diff(id1, id2)

    if not diff_result:
        logger.error(f"One or both deployments not found: {id1}, {id2}")
        raise click.Abort()

    if format == "json":
        import json

        click.echo(json.dumps(diff_result, indent=2, default=str))
    elif format == "yaml":
        import yaml

        click.echo(yaml.dump(diff_result, default_flow_style=False))
    else:
        # Detailed text output
        _print_values_diff(diff_result)


def _print_values_diff(diff_result: dict) -> None:
    """Print Helm values comparison in readable format."""
    import difflib

    dep1 = diff_result["deployment1"]
    dep2 = diff_result["deployment2"]
    values_diff = diff_result["values_diff"]

    logger.heading("Helm Values Comparison")

    click.echo(f"\nDeployment 1: {dep1['id']} ({dep1['timestamp']})")
    click.echo(f"Deployment 2: {dep2['id']} ({dep2['timestamp']})")

    if not values_diff:
        click.echo("\n⚠️  No Helm releases found in either deployment")
        return

    # Summary
    added_count = sum(1 for v in values_diff.values() if v["status"] == "added")
    removed_count = sum(1 for v in values_diff.values() if v["status"] == "removed")
    modified_count = sum(1 for v in values_diff.values() if v["status"] == "modified")
    unchanged_count = sum(1 for v in values_diff.values() if v["status"] == "unchanged")

    click.echo("\n📊 Summary:")
    click.echo(f"  ➕ Added: {added_count}")
    click.echo(f"  ➖ Removed: {removed_count}")
    click.echo(f"  📝 Modified: {modified_count}")
    click.echo(f"  ✅ Unchanged: {unchanged_count}")

    # Detailed changes
    for release_name, diff in values_diff.items():
        status = diff["status"]

        if status == "added":
            click.echo(f"\n➕ {release_name} (ADDED)")
            if diff.get("values"):
                import yaml
                values_str = yaml.dump(diff["values"], default_flow_style=False)
                for line in values_str.splitlines()[:20]:
                    click.echo(click.style(f"  + {line}", fg="green"))

        elif status == "removed":
            click.echo(f"\n➖ {release_name} (REMOVED)")
            if diff.get("values"):
                import yaml
                values_str = yaml.dump(diff["values"], default_flow_style=False)
                for line in values_str.splitlines()[:20]:
                    click.echo(click.style(f"  - {line}", fg="red"))

        elif status == "modified":
            click.echo(f"\n📝 {release_name} (MODIFIED)")

            import yaml

            values1_str = yaml.dump(diff["values_before"], default_flow_style=False) if diff.get("values_before") else ""
            values2_str = yaml.dump(diff["values_after"], default_flow_style=False) if diff.get("values_after") else ""

            diff_lines = difflib.unified_diff(
                values1_str.splitlines(keepends=True),
                values2_str.splitlines(keepends=True),
                fromfile=f"{dep1['id']}",
                tofile=f"{dep2['id']}",
                lineterm="",
            )

            diff_list = list(diff_lines)
            if diff_list:
                for line in diff_list[:30]:  # Limit to 30 lines per release
                    if line.startswith("+"):
                        click.echo(click.style(f"  {line.rstrip()}", fg="green"))
                    elif line.startswith("-"):
                        click.echo(click.style(f"  {line.rstrip()}", fg="red"))
                    elif line.startswith("@@"):
                        click.echo(click.style(f"  {line.rstrip()}", fg="cyan"))
                    else:
                        click.echo(f"  {line.rstrip()}")

                if len(diff_list) > 30:
                    click.echo(f"  ... ({len(diff_list) - 30} more lines)")
