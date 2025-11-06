"""Rollback functionality for deployment states.

This module provides the rollback mechanism to restore previous
deployment states using tracked deployment information.
"""

import subprocess
from pathlib import Path
from typing import Any

import yaml

from sbkube.exceptions import RollbackError
from sbkube.models.deployment_state import (
    DeploymentDetail,
    DeploymentStatus,
    ResourceAction,
    RollbackRequest,
)
from sbkube.state.database import DeploymentDatabase
from sbkube.utils.logger import get_logger

logger = get_logger()


class RollbackManager:
    """Manages rollback operations for deployments.

    Provides functionality to rollback deployments to previous states
    using tracked deployment information.
    """

    def __init__(self, db_path: Path | None = None) -> None:
        """Initialize rollback manager.

        Args:
            db_path: Optional path to database file

        """
        self.db = DeploymentDatabase(db_path)

    def rollback_deployment(self, rollback_request: RollbackRequest) -> dict[str, Any]:
        """Rollback a deployment to a previous state.

        Args:
            rollback_request: Rollback request details

        Returns:
            Rollback result summary

        Raises:
            RollbackError: If rollback fails

        """
        # Get current deployment details
        current_deployment = self.db.get_deployment(rollback_request.deployment_id)
        if not current_deployment:
            msg = f"Deployment not found: {rollback_request.deployment_id}"
            raise RollbackError(
                msg,
            )

        # Get target deployment if specified
        target_deployment = None
        if rollback_request.target_deployment_id:
            target_deployment = self.db.get_deployment(
                rollback_request.target_deployment_id,
            )
            if not target_deployment:
                msg = f"Target deployment not found: {rollback_request.target_deployment_id}"
                raise RollbackError(
                    msg,
                )

        # Validate rollback is possible
        self._validate_rollback(current_deployment, target_deployment, rollback_request)

        # Perform rollback
        if rollback_request.dry_run:
            logger.info("DRY RUN: Rollback would be performed")
            return self._simulate_rollback(
                current_deployment,
                target_deployment,
                rollback_request,
            )
        return self._execute_rollback(
            current_deployment,
            target_deployment,
            rollback_request,
        )

    def _validate_rollback(
        self,
        current_deployment: DeploymentDetail,
        target_deployment: DeploymentDetail | None,
        request: RollbackRequest,
    ) -> None:
        """Validate that rollback can be performed.

        Args:
            current_deployment: Current deployment state
            target_deployment: Target deployment state
            request: Rollback request

        Raises:
            RollbackError: If validation fails

        """
        # Check deployment status
        if (
            current_deployment.status
            not in [
                DeploymentStatus.SUCCESS,
                DeploymentStatus.PARTIALLY_FAILED,
            ]
            and not request.force
        ):
            msg = (
                f"Cannot rollback deployment with status: {current_deployment.status}. "
                "Use --force to override."
            )
            raise RollbackError(
                msg,
            )

        # Check if target deployment exists and is valid
        if target_deployment:
            if target_deployment.cluster != current_deployment.cluster:
                msg = "Cannot rollback to deployment from different cluster"
                raise RollbackError(
                    msg,
                )

            if target_deployment.timestamp >= current_deployment.timestamp:
                msg = "Target deployment is newer than current deployment"
                raise RollbackError(
                    msg,
                )

    def _simulate_rollback(
        self,
        current_deployment: DeploymentDetail,
        target_deployment: DeploymentDetail | None,
        request: RollbackRequest,
    ) -> dict[str, Any]:
        """Simulate rollback without making changes.

        Args:
            current_deployment: Current deployment state
            target_deployment: Target deployment state
            request: Rollback request

        Returns:
            Simulation results

        """
        results = {
            "dry_run": True,
            "current_deployment": current_deployment.deployment_id,
            "target_deployment": (
                target_deployment.deployment_id if target_deployment else "previous"
            ),
            "actions": [],
        }

        # Simulate app rollbacks
        for app in current_deployment.apps:
            if request.app_names and app["name"] not in request.app_names:
                continue

            app_type = app["type"]
            rollback_info = app.get("rollback_info", {})

            if app_type == "helm" and rollback_info.get("type") == "helm":
                action = {
                    "app": app["name"],
                    "type": "helm_rollback",
                    "details": {
                        "release": rollback_info["release_name"],
                        "namespace": rollback_info["namespace"],
                        "from_revision": rollback_info["revision"],
                        "to_revision": rollback_info["revision"] - 1,
                    },
                }
                results["actions"].append(action)

            elif app_type in ["yaml", "action"]:
                # Find resources for this app
                app_resources = [
                    r
                    for r in current_deployment.resources
                    if any(a["id"] == app["id"] for a in current_deployment.apps)
                ]

                for resource in app_resources:
                    if resource.action == ResourceAction.CREATE:
                        action = {
                            "app": app["name"],
                            "type": "resource_delete",
                            "details": {
                                "kind": resource.kind,
                                "name": resource.name,
                                "namespace": resource.namespace,
                            },
                        }
                    elif (
                        resource.action == ResourceAction.UPDATE
                        and resource.previous_state
                    ):
                        action = {
                            "app": app["name"],
                            "type": "resource_restore",
                            "details": {
                                "kind": resource.kind,
                                "name": resource.name,
                                "namespace": resource.namespace,
                                "has_previous_state": True,
                            },
                        }
                    else:
                        continue

                    results["actions"].append(action)

        return results

    def _execute_rollback(
        self,
        current_deployment: DeploymentDetail,
        target_deployment: DeploymentDetail | None,
        request: RollbackRequest,
    ) -> dict[str, Any]:
        """Execute the rollback operation.

        Args:
            current_deployment: Current deployment state
            target_deployment: Target deployment state
            request: Rollback request

        Returns:
            Rollback results

        """
        results = {
            "dry_run": False,
            "current_deployment": current_deployment.deployment_id,
            "target_deployment": (
                target_deployment.deployment_id if target_deployment else "previous"
            ),
            "success": True,
            "rollbacks": [],
            "errors": [],
        }

        # Process each app
        for app in current_deployment.apps:
            if request.app_names and app["name"] not in request.app_names:
                continue

            try:
                app_result = self._rollback_app(app, current_deployment)
                results["rollbacks"].append(app_result)
            except Exception as e:
                error_info = {"app": app["name"], "error": str(e)}
                results["errors"].append(error_info)
                results["success"] = False

                if not request.force:
                    msg = f"Rollback failed for app {app['name']}: {e}"
                    raise RollbackError(msg)

        return results

    def _rollback_app(
        self,
        app: dict[str, Any],
        deployment: DeploymentDetail,
    ) -> dict[str, Any]:
        """Rollback a single application.

        Args:
            app: Application deployment info
            deployment: Full deployment details

        Returns:
            Rollback result for the app

        """
        app_type = app["type"]
        rollback_info = app.get("rollback_info", {})

        result = {"app": app["name"], "type": app_type, "success": True, "actions": []}

        if app_type == "helm" and rollback_info.get("type") == "helm":
            # Rollback Helm release
            self._rollback_helm_release(
                rollback_info["release_name"],
                rollback_info["namespace"],
                rollback_info["revision"],
            )

            result["actions"].append(
                {
                    "type": "helm_rollback",
                    "release": rollback_info["release_name"],
                    "revision": rollback_info["revision"] - 1,
                },
            )

        elif app_type in ["yaml", "action"]:
            # Rollback Kubernetes resources
            app_resources = [
                r
                for r in deployment.resources
                if r.source_file and app["name"] in r.source_file
            ]

            for resource in app_resources:
                try:
                    if resource.action == ResourceAction.CREATE:
                        # Delete created resources
                        self._delete_resource(
                            resource.api_version,
                            resource.kind,
                            resource.name,
                            resource.namespace,
                        )

                        result["actions"].append(
                            {
                                "type": "delete",
                                "resource": f"{resource.kind}/{resource.name}",
                            },
                        )

                    elif (
                        resource.action == ResourceAction.UPDATE
                        and resource.previous_state
                    ):
                        # Restore previous state
                        self._restore_resource(resource.previous_state)

                        result["actions"].append(
                            {
                                "type": "restore",
                                "resource": f"{resource.kind}/{resource.name}",
                            },
                        )

                    elif (
                        resource.action == ResourceAction.DELETE
                        and resource.previous_state
                    ):
                        # Recreate deleted resources
                        self._restore_resource(resource.previous_state)

                        result["actions"].append(
                            {
                                "type": "recreate",
                                "resource": f"{resource.kind}/{resource.name}",
                            },
                        )

                except Exception as e:
                    logger.exception(
                        f"Failed to rollback resource {resource.kind}/{resource.name}: {e}",
                    )
                    result["success"] = False
                    result["actions"].append(
                        {
                            "type": "error",
                            "resource": f"{resource.kind}/{resource.name}",
                            "error": str(e),
                        },
                    )

        else:
            logger.warning(f"Rollback not supported for app type: {app_type}")
            result["success"] = False
            result["message"] = "Rollback not supported for this app type"

        return result

    def _rollback_helm_release(
        self,
        release_name: str,
        namespace: str,
        current_revision: int,
    ) -> None:
        """Rollback a Helm release to previous revision.

        Args:
            release_name: Helm release name
            namespace: Release namespace
            current_revision: Current revision number

        """
        target_revision = max(1, current_revision - 1)

        cmd = ["helm", "rollback", release_name, str(target_revision), "-n", namespace]

        logger.info(
            f"Rolling back Helm release: {release_name} to revision {target_revision}",
        )

        try:
            subprocess.run(cmd, check=True, capture_output=True, text=True)
            logger.success(f"Helm release rolled back: {release_name}")
        except subprocess.CalledProcessError as e:
            msg = f"Helm rollback failed: {e.stderr}"
            raise RollbackError(msg)

    def _delete_resource(
        self,
        api_version: str,
        kind: str,
        name: str,
        namespace: str | None = None,
    ) -> None:
        """Delete a Kubernetes resource.

        Args:
            api_version: API version
            kind: Resource kind
            name: Resource name
            namespace: Resource namespace

        """
        cmd = ["kubectl", "delete", f"{kind}.{api_version}", name]

        if namespace:
            cmd.extend(["-n", namespace])

        logger.info(f"Deleting resource: {kind}/{name}")

        try:
            subprocess.run(cmd, check=True, capture_output=True, text=True)
            logger.success(f"Resource deleted: {kind}/{name}")
        except subprocess.CalledProcessError as e:
            if "NotFound" in e.stderr:
                logger.warning(f"Resource not found: {kind}/{name}")
            else:
                msg = f"Failed to delete resource: {e.stderr}"
                raise RollbackError(msg)

    def _restore_resource(self, resource_state: dict[str, Any]) -> None:
        """Restore a resource to its previous state.

        Args:
            resource_state: Previous resource state

        """
        # Write resource to temporary file
        import tempfile

        with tempfile.NamedTemporaryFile(mode="w", suffix=".yaml", delete=False) as f:
            yaml.dump(resource_state, f)
            temp_file = f.name

        try:
            # Apply the resource
            cmd = ["kubectl", "apply", "-f", temp_file]

            metadata = resource_state.get("metadata", {})
            kind = resource_state.get("kind", "Resource")
            name = metadata.get("name", "unknown")

            logger.info(f"Restoring resource: {kind}/{name}")

            subprocess.run(cmd, check=True, capture_output=True, text=True)
            logger.success(f"Resource restored: {kind}/{name}")

        except subprocess.CalledProcessError as e:
            msg = f"Failed to restore resource: {e.stderr}"
            raise RollbackError(msg)
        finally:
            # Clean up temporary file
            Path(temp_file).unlink(missing_ok=True)

    def list_rollback_points(
        self,
        cluster: str,
        namespace: str,
        app_config_dir: str,
        limit: int = 10,
    ) -> list[dict[str, Any]]:
        """List available rollback points for a configuration.

        Args:
            cluster: Cluster name
            namespace: Namespace
            app_config_dir: App configuration directory
            limit: Maximum number of results

        Returns:
            List of rollback points

        """
        deployments = self.db.list_deployments(
            cluster=cluster,
            namespace=namespace,
            limit=limit,
        )

        # Filter by app_config_dir
        rollback_points = []
        for deployment in deployments:
            detail = self.db.get_deployment(deployment.deployment_id)
            if detail and detail.app_config_dir == app_config_dir:
                rollback_points.append(
                    {
                        "deployment_id": deployment.deployment_id,
                        "timestamp": deployment.timestamp.isoformat(),
                        "status": deployment.status.value,
                        "apps": len(deployment.app_count),
                        "can_rollback": deployment.status
                        in [
                            DeploymentStatus.SUCCESS,
                            DeploymentStatus.PARTIALLY_FAILED,
                        ],
                    },
                )

        return rollback_points
