"""Rollback functionality for deployment states.

This module provides the rollback mechanism to restore previous
deployment states using tracked deployment information.
"""

import json
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
from sbkube.state.rollback_compare import (
    AppComparison,
    AppSnapshot,
    RollbackComparison,
    RollbackConfirmationRequired,
    compare_snapshots,
)
from sbkube.utils.common import run_command
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

    def rollback_deployment(
        self,
        rollback_request: RollbackRequest,
        confirmed_digest: str | None = None,
    ) -> dict[str, Any]:
        """Rollback a deployment to a previous state.

        A rollback whose target differs from the current deployment in chart
        version, values digest or source commit (or cannot be compared) runs
        only when confirmed_digest equals the comparison digest. force does
        not skip this check; dry runs only report the comparison.

        Args:
            rollback_request: Rollback request details
            confirmed_digest: Difference digest typed or passed by the operator

        Returns:
            Rollback result summary, with the comparison under "comparison"

        Raises:
            RollbackError: If rollback fails
            RollbackConfirmationRequired: If code changes and the digest does not match

        """
        current_deployment, target_deployment = self._load_deployments(rollback_request)

        # Validate rollback is possible
        self._validate_rollback(current_deployment, target_deployment, rollback_request)

        comparison = self._compare(
            current_deployment, target_deployment, rollback_request
        )

        # Perform rollback
        if rollback_request.dry_run:
            logger.info("DRY RUN: Rollback would be performed")
            result = self._simulate_rollback(
                current_deployment,
                target_deployment,
                rollback_request,
            )
            result["comparison"] = comparison
            return result

        if comparison.requires_confirmation and confirmed_digest != comparison.digest:
            msg = (
                "Rollback changes code (chart, chart version, values or source commit) "
                "and was not confirmed with the difference digest"
            )
            raise RollbackConfirmationRequired(msg)

        result = self._execute_rollback(
            current_deployment,
            target_deployment,
            rollback_request,
        )
        result["comparison"] = comparison
        return result

    def compare_rollback(self, rollback_request: RollbackRequest) -> RollbackComparison:
        """Compare the rollback target with the current deployment without acting.

        Raises:
            RollbackError: If the rollback itself is invalid (see _validate_rollback)

        """
        current_deployment, target_deployment = self._load_deployments(rollback_request)
        self._validate_rollback(current_deployment, target_deployment, rollback_request)
        return self._compare(current_deployment, target_deployment, rollback_request)

    def _load_deployments(
        self,
        rollback_request: RollbackRequest,
    ) -> tuple[DeploymentDetail, DeploymentDetail | None]:
        """Load the current and optional target deployment records."""
        current_deployment = self.db.get_deployment(rollback_request.deployment_id)
        if not current_deployment:
            msg = f"Deployment not found: {rollback_request.deployment_id}"
            raise RollbackError(
                msg,
            )

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
        return current_deployment, target_deployment

    def _compare(
        self,
        current_deployment: DeploymentDetail,
        target_deployment: DeploymentDetail | None,
        request: RollbackRequest,
    ) -> RollbackComparison:
        """Compare every app the rollback would touch."""
        apps: list[AppComparison] = []
        for app in current_deployment.apps:
            # Same selection as _simulate_rollback/_execute_rollback
            if request.app_names and app["name"] not in request.app_names:
                continue

            rollback_info = app.get("rollback_info") or {}
            if app["type"] != "helm" or rollback_info.get("type") != "helm":
                apps.append(
                    AppComparison(
                        app_name=app["name"],
                        current=None,
                        target=None,
                        uncomparable_reason=(
                            f"no recorded chart/values snapshot for app type '{app['type']}'"
                        ),
                    )
                )
                continue

            apps.append(
                self._compare_helm_app(
                    app["name"], rollback_info, current_deployment, target_deployment
                )
            )

        return RollbackComparison(
            current_deployment_id=current_deployment.deployment_id,
            apps=apps,
        )

    def _compare_helm_app(
        self,
        app_name: str,
        rollback_info: dict[str, Any],
        current_deployment: DeploymentDetail,
        target_deployment: DeploymentDetail | None,
    ) -> AppComparison:
        """Compare one Helm app with the state its rollback restores.

        The target state is the record of the same release and namespace at
        the Helm revision the rollback restores (current revision - 1): the
        --target deployment's record when given, else the newest earlier one.
        The current record must also be the live state: the newest record of
        the release, at the revision `helm status` reports.
        """
        release_name = rollback_info.get("release_name")
        namespace = rollback_info.get("namespace")
        current = AppSnapshot.from_record(
            current_deployment.deployment_id,
            rollback_info,
            current_deployment.source_commit,
        )
        restore_revision = (
            max(1, current.revision - 1) if current.revision is not None else None
        )

        target_record = target_deployment
        if target_record is None and restore_revision is not None:
            target_record = self.db.get_previous_app_deployment(
                current_deployment.cluster,
                release_name,
                namespace,
                restore_revision,
                current_deployment.deployment_id,
            )
        target_info = (
            _find_release_info(target_record, release_name, namespace)
            if target_record is not None
            else None
        )
        target = (
            AppSnapshot.from_record(
                target_record.deployment_id, target_info, target_record.source_commit
            )
            if target_record is not None and target_info is not None
            else None
        )

        comparison = compare_snapshots(app_name, current, target, restore_revision)
        live_reason = self._current_state_reason(
            current_deployment, release_name, namespace, current.revision
        )
        if live_reason is not None:
            comparison.uncomparable_reason = live_reason
        elif target_deployment is not None and target_info is None:
            comparison.uncomparable_reason = (
                f"--target {target_deployment.deployment_id} has no record of "
                f"release {release_name} in namespace {namespace}"
            )
        return comparison

    def _current_state_reason(
        self,
        current_deployment: DeploymentDetail,
        release_name: str | None,
        namespace: str | None,
        recorded_revision: int | None,
    ) -> str | None:
        """Why the current record may not be the live release state, else None."""
        if not release_name or not namespace:
            return "release name or namespace was not recorded"
        latest = self.db.get_latest_helm_release_deployment_id(
            current_deployment.cluster, release_name, namespace
        )
        if latest != current_deployment.deployment_id:
            return (
                f"{current_deployment.deployment_id} is not the newest record of "
                f"release {release_name} in {namespace} (newest: {latest})"
            )
        live_revision = self._live_helm_revision(release_name, namespace)
        if live_revision is None:
            return (
                f"live Helm revision of {release_name} in {namespace} could not be read"
            )
        if live_revision != recorded_revision:
            return (
                f"live Helm revision {live_revision} of {release_name} differs from "
                f"recorded revision {recorded_revision}"
            )
        return None

    def _live_helm_revision(self, release_name: str, namespace: str) -> int | None:
        """Revision `helm status` reports, None when helm fails or is unparsable.

        The reason text stays free of helm output so that the difference
        digest is stable between the comparison and the confirmed rollback.
        """
        cmd = ["helm", "status", release_name, "-n", namespace, "-o", "json"]
        return_code, stdout, stderr = run_command(cmd)
        if return_code != 0:
            logger.warning(f"helm status {release_name} failed: {stderr.strip()}")
            return None
        try:
            revision = json.loads(stdout).get("version")
        except (ValueError, AttributeError):
            logger.warning(f"helm status {release_name} returned unparsable output")
            return None
        if isinstance(revision, bool) or not isinstance(revision, int):
            logger.warning(f"helm status {release_name} has no revision number")
            return None
        return revision

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

            # helm rollback always restores current revision - 1; --target only
            # names the record that state is compared with.
            for app in current_deployment.apps:
                if request.app_names and app["name"] not in request.app_names:
                    continue
                info = app.get("rollback_info") or {}
                if info.get("type") != "helm" or info.get("revision") is None:
                    continue
                target_info = _find_release_info(
                    target_deployment, info.get("release_name"), info.get("namespace")
                )
                if target_info is None:
                    continue
                restore_revision = max(1, info["revision"] - 1)
                if target_info.get("revision") != restore_revision:
                    msg = (
                        f"--target {target_deployment.deployment_id} recorded "
                        f"{info.get('release_name')} at revision "
                        f"{target_info.get('revision')}, but rollback restores "
                        f"revision {restore_revision} (current revision - 1)"
                    )
                    raise RollbackError(msg)

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

    def get_phase_apps(
        self,
        deployment_id: str,
        phase_name: str | None,
    ) -> list[str]:
        """Get apps deployed in a specific phase.

        Args:
            deployment_id: Deployment ID to look up
            phase_name: Phase name to filter apps by

        Returns:
            List of app names belonging to the phase

        """
        if not phase_name:
            return []

        deployment = self.db.get_deployment(deployment_id)
        if not deployment:
            logger.warning(f"Deployment not found: {deployment_id}")
            return []

        # Filter apps by app_group (which stores phase info)
        phase_apps = []
        for app in deployment.apps:
            app_group = app.get("app_group") or app.get("phase")
            if app_group == phase_name:
                phase_apps.append(app["name"])

        return phase_apps

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


def _find_release_info(
    deployment: DeploymentDetail,
    release_name: str | None,
    namespace: str | None,
) -> dict[str, Any] | None:
    """Helm rollback_info of release_name/namespace in deployment, if recorded."""
    for app in deployment.apps:
        info = app.get("rollback_info") or {}
        if (
            info.get("type") == "helm"
            and info.get("release_name") == release_name
            and info.get("namespace") == namespace
        ):
            return info
    return None
