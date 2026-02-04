"""Deployment rollback management.

This command performs rollback operations on deployments, restoring
applications to previous states.

Replaces: sbkube state rollback, sbkube state rollback_points

Scope options (v0.11.0+):
- app: Rollback single app (default, existing behavior)
- phase: Rollback all apps deployed in a specific phase
- all: Rollback entire deployment (all apps)
"""

from datetime import datetime
from pathlib import Path
from typing import Literal

import click

from sbkube.exceptions import RollbackError
from sbkube.models.deployment_state import RollbackRequest
from sbkube.state.rollback import RollbackManager
from sbkube.utils.logger import logger


# Type alias for rollback scope
RollbackScope = Literal["app", "phase", "all"]


@click.command(name="rollback")
@click.argument("deployment_id", required=False)
@click.option("--target", help="Specific deployment ID to rollback to")
@click.option(
    "--app",
    "-a",
    multiple=True,
    help="Specific app(s) to rollback (can be specified multiple times)",
)
@click.option(
    "--scope",
    type=click.Choice(["app", "phase", "all"]),
    default="app",
    help="Rollback scope: app (single), phase (all apps in phase), all (entire deployment)",
)
@click.option(
    "--phase",
    "-p",
    help="Phase name to rollback (requires --scope=phase)",
)
@click.option(
    "--dry-run",
    is_flag=True,
    help="Simulate rollback without making changes",
)
@click.option("--force", is_flag=True, help="Force rollback even with warnings")
@click.option(
    "--list",
    "list_points",
    is_flag=True,
    help="List available rollback points",
)
@click.option("--base-dir", "-b", default=".", help="Base directory")
@click.option("--app-dir", "-ad", default=".", help="App configuration directory")
@click.option("--cluster", help="Cluster name (for --list)")
@click.option("--namespace", "-n", help="Namespace (for --list)")
@click.option(
    "--limit", default=10, help="Maximum rollback points to show (for --list)"
)
def cmd(
    deployment_id: str | None,
    target: str | None,
    app: tuple,
    scope: RollbackScope,
    phase: str | None,
    dry_run: bool,
    force: bool,
    list_points: bool,
    base_dir: str,
    app_dir: str,
    cluster: str | None,
    namespace: str | None,
    limit: int,
) -> None:
    r"""Rollback a deployment to a previous state.

    This command allows you to roll back applications to a previous deployment
    state, either completely or for specific apps only.

    \b
    Scope options (v0.11.0+):
        app   - Rollback specific app(s) only (default)
        phase - Rollback all apps deployed in a specific phase
        all   - Rollback entire deployment (all apps)

    \b
    Examples:
        # Rollback a specific deployment
        sbkube rollback dep_20250131_143022

        # Dry-run rollback (simulate)
        sbkube rollback dep_20250131_143022 --dry-run

        # Rollback to a specific target
        sbkube rollback dep_20250131_143022 --target dep_20250130_095510

        # Rollback specific apps only (scope=app, default)
        sbkube rollback dep_20250131_143022 --app traefik --app coredns

        # Rollback entire phase (scope=phase)
        sbkube rollback dep_20250131_143022 --scope phase --phase p1-infra

        # Rollback entire deployment (scope=all)
        sbkube rollback dep_20250131_143022 --scope all

        # List available rollback points
        sbkube rollback --list --cluster production --namespace kube-system

        # Force rollback (ignore warnings)
        sbkube rollback dep_20250131_143022 --force
    """
    try:
        rollback_manager = RollbackManager()

        # List rollback points
        if list_points:
            _list_rollback_points(
                rollback_manager, base_dir, app_dir, cluster, namespace, limit
            )
            return

        # Rollback operation requires deployment_id
        if not deployment_id:
            logger.error("deployment_id is required for rollback operation")
            logger.info("Use --list to see available rollback points")
            raise click.Abort

        # Validate scope-specific options
        if scope == "phase" and not phase:
            logger.error("--phase is required when using --scope=phase")
            raise click.Abort

        if scope == "app" and not app:
            logger.warning(
                "No apps specified with --scope=app. "
                "Use --app or --scope=all to rollback all apps."
            )

        # Resolve apps based on scope
        app_names = _resolve_apps_for_scope(
            scope=scope,
            apps=list(app) if app else None,
            phase_name=phase,
            deployment_id=deployment_id,
            rollback_manager=rollback_manager,
        )

        # Create rollback request
        request = RollbackRequest(
            deployment_id=deployment_id,
            target_deployment_id=target,
            app_names=app_names,
            dry_run=dry_run,
            force=force,
        )

        scope_desc = {
            "app": f"apps: {app_names}" if app_names else "all apps",
            "phase": f"phase '{phase}'",
            "all": "entire deployment",
        }
        logger.info(
            f"{'DRY RUN: ' if dry_run else ''}"
            f"Rolling back {scope_desc[scope]} from deployment: {deployment_id}"
        )

        # Perform rollback
        result = rollback_manager.rollback_deployment(request)

        # Display results
        if dry_run:
            _print_rollback_simulation(result, scope)
        else:
            _print_rollback_result(result, scope)

    except RollbackError as e:
        logger.error(f"Rollback failed: {e}")
        raise click.Abort
    except Exception as e:
        logger.error(f"Unexpected error during rollback: {e}")
        raise click.Abort


def _resolve_apps_for_scope(
    scope: RollbackScope,
    apps: list[str] | None,
    phase_name: str | None,
    deployment_id: str,
    rollback_manager: RollbackManager,
) -> list[str] | None:
    """Resolve app names based on rollback scope.

    Args:
        scope: Rollback scope (app, phase, all)
        apps: Explicitly specified apps (for scope=app)
        phase_name: Phase name (for scope=phase)
        deployment_id: Deployment ID to look up
        rollback_manager: Rollback manager instance

    Returns:
        List of app names to rollback, or None for all apps

    """
    if scope == "app":
        return apps if apps else None

    if scope == "all":
        return None  # None means all apps

    if scope == "phase":
        # Get apps deployed in the specified phase
        # This requires looking up phase metadata from deployment history
        phase_apps = rollback_manager.get_phase_apps(deployment_id, phase_name)
        if not phase_apps:
            logger.warning(
                f"No apps found for phase '{phase_name}' in deployment {deployment_id}"
            )
            return []
        logger.info(f"Phase '{phase_name}' contains {len(phase_apps)} apps: {phase_apps}")
        return phase_apps

    return None


def _list_rollback_points(
    rollback_manager: RollbackManager,
    base_dir: str,
    app_dir: str,
    cluster: str | None,
    namespace: str | None,
    limit: int,
) -> None:
    """List available rollback points."""
    if not cluster or not namespace:
        logger.error("--cluster and --namespace are required for --list")
        raise click.Abort

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
            f"Status: {point['status']}"
        )


def _print_rollback_simulation(result, scope: RollbackScope = "app") -> None:
    """Print rollback simulation results.

    Args:
        result: Rollback simulation result
        scope: Rollback scope for display

    """
    scope_labels = {
        "app": "App-level",
        "phase": "Phase-level",
        "all": "Full deployment",
    }
    logger.heading(f"Rollback Simulation ({scope_labels.get(scope, scope)})")

    click.echo(f"Current: {result['current_deployment']}")
    click.echo(f"Target: {result['target_deployment']}")
    click.echo(f"Scope: {scope}")
    click.echo(f"\nPlanned Actions ({len(result['actions'])} total):")

    for action in result["actions"]:
        if action["type"] == "helm_rollback":
            click.echo(
                f"  📦 Rollback Helm release '{action['details']['release']}' "
                f"from revision {action['details']['from_revision']} "
                f"to {action['details']['to_revision']}"
            )
        elif action["type"] == "resource_delete":
            click.echo(
                f"  ➖ Delete {action['details']['kind']}/{action['details']['name']}"
            )
        elif action["type"] == "resource_restore":
            click.echo(
                f"  📝 Restore {action['details']['kind']}/{action['details']['name']}"
            )


def _print_rollback_result(result, scope: RollbackScope = "app") -> None:
    """Print rollback execution results.

    Args:
        result: Rollback execution result
        scope: Rollback scope for display

    """
    scope_labels = {
        "app": "App-level",
        "phase": "Phase-level",
        "all": "Full deployment",
    }

    if result["success"]:
        logger.success(f"Rollback completed successfully ({scope_labels.get(scope, scope)})")
    else:
        logger.error(f"Rollback completed with errors ({scope_labels.get(scope, scope)})")

    click.echo(f"\nRollback Summary (scope={scope}):")
    click.echo(f"  Successful: {len(result['rollbacks'])}")
    click.echo(f"  Failed: {len(result['errors'])}")

    if result["rollbacks"]:
        click.echo("\nSuccessful Rollbacks:")
        for rollback in result["rollbacks"]:
            click.echo(f"  ✅ {rollback['app']} ({rollback['type']})")
            for action in rollback.get("actions", []):
                click.echo(
                    f"     - {action['type']}: {action.get('resource', action.get('release', ''))}"
                )

    if result["errors"]:
        click.echo("\nFailed Rollbacks:")
        for error in result["errors"]:
            click.echo(f"  ❌ {error['app']}: {error['error']}")
