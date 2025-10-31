"""
Deployment state tracker for integration with deployment commands.

This module provides the DeploymentTracker class that tracks deployment
operations and enables rollback functionality.
"""

import json
import os
import subprocess
import uuid
from contextlib import contextmanager
from datetime import datetime
from pathlib import Path
from typing import Any

import yaml

from sbkube.models.deployment_state import (AppDeploymentCreate,
                                            DeploymentCreate, DeploymentStatus,
                                            HelmReleaseInfo, ResourceAction,
                                            ResourceInfo)
from sbkube.state.database import DeploymentDatabase
from sbkube.utils.logger import get_logger

logger = get_logger()


class DeploymentTracker:
    """
    Tracks deployment operations and provides rollback functionality.

    This class integrates with deployment commands to capture state
    before and after operations, enabling rollback capabilities.
    """

    def __init__(self, db_path: str | Path | None = None):
        """
        Initialize deployment tracker.

        Args:
            db_path: Optional path to database file
        """
        self.db = DeploymentDatabase(db_path)
        self.current_deployment_id: str | None = None
        self.current_deployment_record_id: int | None = None
        self.current_app_deployment_id: int | None = None
        self._tracking_enabled = True

    @property
    def tracking_enabled(self) -> bool:
        """Check if tracking is enabled."""
        return self._tracking_enabled

    @tracking_enabled.setter
    def tracking_enabled(self, value: bool):
        """Enable or disable tracking."""
        self._tracking_enabled = value
        if not value:
            logger.verbose("Deployment tracking disabled")

    @contextmanager
    def track_deployment(
        self,
        cluster: str,
        namespace: str,
        app_config_dir: str,
        config_file_path: str,
        config_data: dict[str, Any],
        sources_data: dict[str, Any] | None = None,
        command: str = "deploy",
        command_args: dict[str, Any] | None = None,
        dry_run: bool = False,
    ):
        """
        Context manager to track a deployment operation.

        Args:
            cluster: Target cluster
            namespace: Target namespace
            app_config_dir: App configuration directory
            config_file_path: Configuration file path
            config_data: Configuration data
            sources_data: Optional sources configuration
            command: Command being executed
            command_args: Command arguments
            dry_run: Whether this is a dry run

        Yields:
            Deployment ID for tracking
        """
        if not self._tracking_enabled or dry_run:
            yield None
            return

        # Generate deployment ID
        self.current_deployment_id = self._generate_deployment_id()

        # Get sbkube version
        sbkube_version = self._get_sbkube_version()

        # Get operator info
        operator = os.environ.get("USER", "unknown")

        try:
            # Create deployment record
            deployment_data = DeploymentCreate(
                deployment_id=self.current_deployment_id,
                cluster=cluster,
                namespace=namespace,
                app_config_dir=app_config_dir,
                config_file_path=config_file_path,
                command=command,
                command_args=command_args,
                dry_run=dry_run,
                config_snapshot=config_data,
                sources_snapshot=sources_data,
                sbkube_version=sbkube_version,
                operator=operator,
            )

            deployment = self.db.create_deployment(deployment_data)
            self.current_deployment_record_id = deployment.id

            logger.info(f"Tracking deployment: {self.current_deployment_id}")

            yield self.current_deployment_id

            # If we get here without exception, mark as success
            self.db.update_deployment_status(
                self.current_deployment_id,
                DeploymentStatus.SUCCESS,
            )

        except Exception as e:
            # Mark deployment as failed
            if self.current_deployment_id:
                self.db.update_deployment_status(
                    self.current_deployment_id,
                    DeploymentStatus.FAILED,
                    error_message=str(e),
                )
            raise
        finally:
            # Reset current deployment
            self.current_deployment_id = None
            self.current_deployment_record_id = None

    @contextmanager
    def track_app_deployment(
        self,
        app_name: str,
        app_type: str,
        app_namespace: str | None,
        app_config: dict[str, Any],
    ):
        """
        Context manager to track an individual app deployment.

        Args:
            app_name: Application name
            app_type: Application type
            app_namespace: Application namespace
            app_config: Application configuration

        Yields:
            App deployment ID
        """
        if not self._tracking_enabled or not self.current_deployment_record_id:
            yield None
            return

        try:
            # Create app deployment record
            app_data = AppDeploymentCreate(
                app_name=app_name,
                app_type=app_type,
                namespace=app_namespace,
                app_config=app_config,
            )

            app_deployment = self.db.add_app_deployment(
                self.current_deployment_record_id,
                app_data,
            )
            self.current_app_deployment_id = app_deployment.id

            yield self.current_app_deployment_id

            # Mark as success if no exception
            self.db.update_app_deployment_status(
                self.current_app_deployment_id,
                DeploymentStatus.SUCCESS,
            )

        except Exception as e:
            # Mark app deployment as failed
            if self.current_app_deployment_id:
                self.db.update_app_deployment_status(
                    self.current_app_deployment_id,
                    DeploymentStatus.FAILED,
                    error_message=str(e),
                )
            raise
        finally:
            self.current_app_deployment_id = None

    def track_helm_release(
        self,
        release_name: str,
        namespace: str,
        chart: str,
        chart_version: str | None = None,
        values: dict[str, Any] | None = None,
    ):
        """
        Track a Helm release deployment.

        Args:
            release_name: Helm release name
            namespace: Release namespace
            chart: Chart name/path
            chart_version: Chart version
            values: Values used for deployment
        """
        if not self._tracking_enabled or not self.current_app_deployment_id:
            return

        try:
            # Get Helm release info
            revision = self._get_helm_revision(release_name, namespace)
            status = self._get_helm_status(release_name, namespace)

            # Create Helm release record
            release_info = HelmReleaseInfo(
                release_name=release_name,
                namespace=namespace,
                chart=chart,
                chart_version=chart_version,
                revision=revision,
                values=values,
                status=status,
            )

            self.db.add_helm_release(self.current_app_deployment_id, release_info)

            # Store rollback info
            rollback_info = {
                "type": "helm",
                "release_name": release_name,
                "namespace": namespace,
                "revision": revision,
            }

            self.db.update_app_deployment_status(
                self.current_app_deployment_id,
                DeploymentStatus.SUCCESS,
                rollback_info=rollback_info,
            )

        except Exception as e:
            logger.warning(f"Failed to track Helm release: {e}")

    def track_resource(
        self,
        manifest: dict[str, Any],
        action: ResourceAction,
        source_file: str | None = None,
        previous_state: dict[str, Any] | None = None,
    ):
        """
        Track a Kubernetes resource deployment.

        Args:
            manifest: Resource manifest
            action: Action taken (create, update, delete)
            source_file: Source YAML file
            previous_state: Previous state for updates
        """
        if not self._tracking_enabled or not self.current_app_deployment_id:
            return

        try:
            # Extract resource info
            api_version = manifest.get("apiVersion", "")
            kind = manifest.get("kind", "")
            metadata = manifest.get("metadata", {})
            name = metadata.get("name", "")
            namespace = metadata.get("namespace")

            # Compute checksum
            checksum = DeploymentDatabase.compute_resource_checksum(manifest)

            # Create resource record
            resource_info = ResourceInfo(
                api_version=api_version,
                kind=kind,
                name=name,
                namespace=namespace,
                action=action,
                previous_state=previous_state,
                current_state=manifest if action != ResourceAction.DELETE else None,
                checksum=checksum,
                source_file=source_file,
            )

            self.db.add_deployed_resource(self.current_app_deployment_id, resource_info)

        except Exception as e:
            logger.warning(f"Failed to track resource: {e}")

    def get_resource_state(
        self,
        api_version: str,
        kind: str,
        name: str,
        namespace: str | None = None,
    ) -> dict[str, Any] | None:
        """
        Get current state of a Kubernetes resource.

        Args:
            api_version: API version
            kind: Resource kind
            name: Resource name
            namespace: Resource namespace

        Returns:
            Current resource state or None
        """
        try:
            # Build kubectl command
            cmd = ["kubectl", "get", f"{kind}.{api_version}", name, "-o", "yaml"]

            if namespace:
                cmd.extend(["-n", namespace])

            # Execute command
            result = subprocess.run(cmd, capture_output=True, text=True, check=True)

            # Parse YAML
            return yaml.safe_load(result.stdout)

        except subprocess.CalledProcessError:
            return None
        except Exception as e:
            logger.warning(f"Failed to get resource state: {e}")
            return None

    def _generate_deployment_id(self) -> str:
        """Generate unique deployment ID."""
        timestamp = datetime.utcnow().strftime("%Y%m%d%H%M%S")
        unique_id = str(uuid.uuid4())[:8]
        return f"dep-{timestamp}-{unique_id}"

    def _get_sbkube_version(self) -> str:
        """Get sbkube version."""
        try:
            from sbkube import __version__

            return __version__
        except Exception:
            return "unknown"

    def _get_helm_revision(self, release_name: str, namespace: str) -> int:
        """Get Helm release revision."""
        try:
            cmd = [
                "helm",
                "list",
                "-n",
                namespace,
                "--filter",
                f"^{release_name}$",
                "-o",
                "json",
            ]

            result = subprocess.run(cmd, capture_output=True, text=True, check=True)

            releases = json.loads(result.stdout)
            if releases:
                return releases[0].get("revision", 1)

            return 1

        except Exception:
            return 1

    def _get_helm_status(self, release_name: str, namespace: str) -> str:
        """Get Helm release status."""
        try:
            cmd = ["helm", "status", release_name, "-n", namespace, "-o", "json"]

            result = subprocess.run(cmd, capture_output=True, text=True, check=True)

            status_data = json.loads(result.stdout)
            return status_data.get("info", {}).get("status", "unknown")

        except Exception:
            return "unknown"
