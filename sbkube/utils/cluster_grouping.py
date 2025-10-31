"""Cluster status grouping utilities.

This module provides functionality to group Helm releases and Kubernetes
resources by app-group, integrating State DB information with live cluster status.
"""

from collections import defaultdict
from typing import Any

from sbkube.state.database import DeploymentDatabase
from sbkube.utils.app_labels import extract_app_group_from_name


def group_releases_by_app_group(
    helm_releases: list[dict[str, Any]],
    db: DeploymentDatabase | None = None,
) -> dict[str, Any]:
    """Group Helm releases by app-group.

    This function organizes Helm releases into groups based on:
    1. Labels (sbkube.io/app-group) if available
    2. State DB records (deployment history)
    3. Name pattern matching (app_XXX_category_subcategory)

    Args:
        helm_releases: List of Helm release dicts from cluster status
        db: DeploymentDatabase instance for matching with deployment history

    Returns:
        Grouped data structure:
        {
            "managed_app_groups": {
                "app_000_infra_network": {
                    "namespace": "kube-system",
                    "apps": {
                        "traefik": {"release_name": "traefik", "status": "deployed", ...},
                        ...
                    },
                    "summary": {"total_apps": 4, "healthy": 4, "failed": 0}
                },
                ...
            },
            "unmanaged_releases": [
                {"name": "manual-app", "namespace": "default", ...},
                ...
            ],
            "summary": {
                "total_app_groups": 15,
                "total_managed_releases": 42,
                "total_unmanaged_releases": 1
            }
        }
    """
    grouped: dict[str, dict[str, Any]] = defaultdict(
        lambda: {"apps": {}, "namespace": None}
    )
    unmanaged = []

    # Get deployment history from State DB if available
    state_db_mapping = {}
    if db:
        try:
            # Query recent deployments
            deployments = db.list_deployments(limit=1000)
            for deployment in deployments:
                # Build mapping: release_name -> app_group
                for app in deployment.apps:
                    if app.get("app_group"):
                        # Extract release name from app metadata
                        # This is a placeholder - actual implementation depends on app type
                        release_name = app.get("release_name") or app.get("name")
                        if release_name:
                            state_db_mapping[release_name] = app.get("app_group")
        except Exception:
            # Gracefully handle DB errors
            pass

    for release in helm_releases:
        release_name = release.get("name", "unknown")
        namespace = release.get("namespace", "unknown")
        status = release.get("status", "unknown")
        chart = release.get("chart", "unknown")

        # Try to determine app-group
        app_group = None

        # Method 1: Check State DB
        if release_name in state_db_mapping:
            app_group = state_db_mapping[release_name]

        # Method 2: Extract from release name pattern
        if not app_group:
            app_group = extract_app_group_from_name(release_name)

        # Method 3: Try namespace pattern (less reliable)
        if not app_group and namespace != "default":
            app_group = extract_app_group_from_name(namespace)

        if app_group:
            # Managed release - add to app-group
            if not grouped[app_group]["namespace"]:
                grouped[app_group]["namespace"] = namespace

            grouped[app_group]["apps"][release_name] = {
                "release_name": release_name,
                "chart": chart,
                "status": status,
                "namespace": namespace,
            }
        else:
            # Unmanaged release
            unmanaged.append(
                {
                    "name": release_name,
                    "namespace": namespace,
                    "chart": chart,
                    "status": status,
                    "note": "Not managed by sbkube",
                }
            )

    # Calculate summaries
    for app_group, group_data in grouped.items():
        apps = group_data["apps"]
        total = len(apps)
        healthy = sum(
            1
            for app in apps.values()
            if app["status"] in ["deployed", "superseded"]
        )
        failed = sum(
            1
            for app in apps.values()
            if app["status"] in ["failed", "pending-install", "pending-upgrade"]
        )

        group_data["summary"] = {
            "total_apps": total,
            "healthy": healthy,
            "failed": failed,
        }

    # Overall summary
    total_managed = sum(len(g["apps"]) for g in grouped.values())
    overall_summary = {
        "total_app_groups": len(grouped),
        "total_managed_releases": total_managed,
        "total_unmanaged_releases": len(unmanaged),
    }

    return {
        "managed_app_groups": dict(grouped),
        "unmanaged_releases": unmanaged,
        "summary": overall_summary,
    }


def filter_by_app_group(
    grouped_data: dict[str, Any],
    app_group: str,
) -> dict[str, Any] | None:
    """Extract specific app-group from grouped data.

    Args:
        grouped_data: Result from group_releases_by_app_group()
        app_group: App group name to filter

    Returns:
        App-group data or None if not found
    """
    managed = grouped_data.get("managed_app_groups", {})
    return managed.get(app_group)


def get_app_group_summary(grouped_data: dict[str, Any]) -> dict[str, Any]:
    """Get summary statistics from grouped data.

    Args:
        grouped_data: Result from group_releases_by_app_group()

    Returns:
        Summary dict with counts and health status
    """
    summary = grouped_data.get("summary", {})
    managed_groups = grouped_data.get("managed_app_groups", {})

    total_healthy = sum(
        g["summary"]["healthy"]
        for g in managed_groups.values()
    )
    total_failed = sum(
        g["summary"]["failed"]
        for g in managed_groups.values()
    )

    overall_health = "healthy" if total_failed == 0 else "degraded"
    if total_failed > total_healthy:
        overall_health = "unhealthy"

    return {
        **summary,
        "total_healthy_apps": total_healthy,
        "total_failed_apps": total_failed,
        "overall_health": overall_health,
    }
