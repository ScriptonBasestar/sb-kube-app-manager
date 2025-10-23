"""
State management commands for deployment tracking and rollback.

This module provides CLI commands for managing deployment states,
viewing deployment history, and performing rollbacks.
"""

from datetime import datetime
from pathlib import Path

import click

from sbkube.exceptions import RollbackError
from sbkube.models.deployment_state import RollbackRequest
from sbkube.state.database import DeploymentDatabase
from sbkube.state.rollback import RollbackManager
from sbkube.utils.logger import logger


@click.group()
def state():
    """Deployment state management commands."""
    pass


@state.command()
@click.option("--cluster", help="Filter by cluster name")
@click.option("--namespace", "-n", help="Filter by namespace")
@click.option("--limit", default=20, help="Maximum number of deployments to show")
@click.option(
    "--format",
    type=click.Choice(["table", "json", "yaml"]),
    default="table",
    help="Output format",
)
def list(cluster: str | None, namespace: str | None, limit: int, format: str):
    """List deployment history."""
    try:
        db = DeploymentDatabase()
        deployments = db.list_deployments(
            cluster=cluster,
            namespace=namespace,
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
        logger.error(f"Failed to list deployments: {e}")
        raise click.Abort()


@state.command()
@click.argument("deployment_id")
@click.option(
    "--format",
    type=click.Choice(["detailed", "summary", "json", "yaml"]),
    default="detailed",
    help="Output format",
)
def show(deployment_id: str, format: str):
    """Show detailed deployment information."""
    try:
        db = DeploymentDatabase()
        deployment = db.get_deployment(deployment_id)

        if not deployment:
            logger.error(f"Deployment not found: {deployment_id}")
            raise click.Abort()

        if format == "detailed":
            _print_deployment_detail(deployment)
        elif format == "summary":
            _print_deployment_summary(deployment)
        elif format == "json":
            import json

            click.echo(json.dumps(deployment.model_dump(), indent=2, default=str))
        elif format == "yaml":
            import yaml

            click.echo(yaml.dump(deployment.model_dump(), default_flow_style=False))

    except Exception as e:
        logger.error(f"Failed to show deployment: {e}")
        raise click.Abort()


@state.command()
@click.argument("deployment_id")
@click.option("--target-deployment", help="Specific deployment ID to rollback to")
@click.option(
    "--app",
    "-a",
    multiple=True,
    help="Specific app(s) to rollback (can be specified multiple times)",
)
@click.option(
    "--dry-run",
    is_flag=True,
    help="Simulate rollback without making changes",
)
@click.option("--force", is_flag=True, help="Force rollback even with warnings")
def rollback(
    deployment_id: str,
    target_deployment: str | None,
    app: tuple,
    dry_run: bool,
    force: bool,
):
    """Rollback a deployment to previous state."""
    try:
        rollback_manager = RollbackManager()

        # Create rollback request
        request = RollbackRequest(
            deployment_id=deployment_id,
            target_deployment_id=target_deployment,
            app_names=list(app) if app else None,
            dry_run=dry_run,
            force=force,
        )

        logger.info(
            f"{'DRY RUN: ' if dry_run else ''}Rolling back deployment: {deployment_id}",
        )

        # Perform rollback
        result = rollback_manager.rollback_deployment(request)

        # Display results
        if dry_run:
            _print_rollback_simulation(result)
        else:
            _print_rollback_result(result)

    except RollbackError as e:
        logger.error(f"Rollback failed: {e}")
        raise click.Abort()
    except Exception as e:
        logger.error(f"Unexpected error during rollback: {e}")
        raise click.Abort()


@state.command()
@click.option("--base-dir", "-b", default=".", help="Base directory")
@click.option("--app-dir", "-a", default=".", help="App configuration directory")
@click.option("--cluster", required=True, help="Cluster name")
@click.option("--namespace", "-n", required=True, help="Namespace")
@click.option("--limit", default=10, help="Maximum number of rollback points to show")
def rollback_points(
    base_dir: str,
    app_dir: str,
    cluster: str,
    namespace: str,
    limit: int,
):
    """List available rollback points for a configuration."""
    try:
        rollback_manager = RollbackManager()
        app_config_dir = str(Path(base_dir).resolve() / app_dir)

        points = rollback_manager.list_rollback_points(
            cluster=cluster,
            namespace=namespace,
            app_config_dir=app_config_dir,
            limit=limit,
        )

        if not points:
            logger.info("No rollback points found")
            return

        logger.heading(f"Rollback points for {app_config_dir}")

        for point in points:
            status_icon = "✅" if point["can_rollback"] else "❌"
            timestamp = datetime.fromisoformat(point["timestamp"])

            click.echo(
                f"{status_icon} {point['deployment_id']} - "
                f"{timestamp.strftime('%Y-%m-%d %H:%M:%S')} - "
                f"{point['apps']} apps - "
                f"Status: {point['status']}",
            )

    except Exception as e:
        logger.error(f"Failed to list rollback points: {e}")
        raise click.Abort()


@state.command()
@click.option("--days", default=30, help="Delete deployments older than this many days")
@click.option(
    "--keep-per-app",
    default=10,
    help="Maximum deployments to keep per application",
)
@click.option(
    "--dry-run",
    is_flag=True,
    help="Show what would be deleted without actually deleting",
)
def cleanup(days: int, keep_per_app: int, dry_run: bool):
    """Clean up old deployment records."""
    try:
        db = DeploymentDatabase()

        if dry_run:
            logger.info(f"DRY RUN: Would delete deployments older than {days} days")
            # Dry run: Show what would be deleted without actually deleting
            from datetime import datetime, timedelta

            cutoff_date = datetime.now() - timedelta(days=days)
            deployments_to_delete = db.session.query(db.DeploymentRecord).filter(
                db.DeploymentRecord.timestamp < cutoff_date
            ).order_by(db.DeploymentRecord.timestamp.desc()).all()

            if deployments_to_delete:
                logger.info(f"Would delete {len(deployments_to_delete)} deployment(s):")
                for dep in deployments_to_delete[:10]:  # Show max 10
                    logger.info(f"  - {dep.app_name} ({dep.timestamp})")
                if len(deployments_to_delete) > 10:
                    logger.info(f"  ... and {len(deployments_to_delete) - 10} more")
            else:
                logger.info("No deployments would be deleted")
        else:
            deleted = db.cleanup_old_deployments(
                days_to_keep=days,
                max_deployments_per_app=keep_per_app,
            )
            logger.success(f"Deleted {deleted} old deployment records")

    except Exception as e:
        logger.error(f"Failed to cleanup deployments: {e}")
        raise click.Abort()


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
                f"(rev: {release.revision}, status: {release.status})",
            )


def _print_deployment_summary(deployment):
    """Print deployment summary."""
    total_apps = len(deployment.apps)
    success_apps = sum(1 for app in deployment.apps if app["status"] == "success")

    click.echo(f"Deployment ID: {deployment.deployment_id}")
    click.echo(f"Status: {deployment.status.value}")
    click.echo(f"Apps: {success_apps}/{total_apps} successful")
    click.echo(f"Resources: {len(deployment.resources)} tracked")
    click.echo(f"Helm Releases: {len(deployment.helm_releases)}")


def _print_rollback_simulation(result):
    """Print rollback simulation results."""
    logger.heading("Rollback Simulation")

    click.echo(f"Current: {result['current_deployment']}")
    click.echo(f"Target: {result['target_deployment']}")
    click.echo(f"\nPlanned Actions ({len(result['actions'])} total):")

    for action in result["actions"]:
        if action["type"] == "helm_rollback":
            click.echo(
                f"  📦 Rollback Helm release '{action['details']['release']}' "
                f"from revision {action['details']['from_revision']} "
                f"to {action['details']['to_revision']}",
            )
        elif action["type"] == "resource_delete":
            click.echo(
                f"  ➖ Delete {action['details']['kind']}/{action['details']['name']}",
            )
        elif action["type"] == "resource_restore":
            click.echo(
                f"  📝 Restore {action['details']['kind']}/{action['details']['name']}",
            )


def _print_rollback_result(result):
    """Print rollback execution results."""
    if result["success"]:
        logger.success("Rollback completed successfully")
    else:
        logger.error("Rollback completed with errors")

    click.echo("\nRollback Summary:")
    click.echo(f"  Successful: {len(result['rollbacks'])}")
    click.echo(f"  Failed: {len(result['errors'])}")

    if result["rollbacks"]:
        click.echo("\nSuccessful Rollbacks:")
        for rollback in result["rollbacks"]:
            click.echo(f"  ✅ {rollback['app']} ({rollback['type']})")
            for action in rollback.get("actions", []):
                click.echo(
                    f"     - {action['type']}: {action.get('resource', action.get('release', ''))}",
                )

    if result["errors"]:
        click.echo("\nFailed Rollbacks:")
        for error in result["errors"]:
            click.echo(f"  ❌ {error['app']}: {error['error']}")
