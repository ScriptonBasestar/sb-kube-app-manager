"""
Database manager for deployment state tracking.

This module provides the database connection and session management
for the deployment state tracking system.
"""

import hashlib
import json
from contextlib import contextmanager
from pathlib import Path
from typing import Any, Dict, List, Optional, Union

from sqlalchemy import create_engine, event, text
from sqlalchemy.orm import Session, sessionmaker
from sqlalchemy.pool import StaticPool

from sbkube.models.deployment_state import (AppDeployment, AppDeploymentCreate,
                                            Base, DeployedResource, Deployment,
                                            DeploymentCreate, DeploymentDetail,
                                            DeploymentStatus,
                                            DeploymentSummary, HelmRelease,
                                            HelmReleaseInfo, ResourceAction,
                                            ResourceInfo)
from sbkube.utils.logger import get_logger

logger = get_logger()


class DeploymentDatabase:
    """
    Manager for deployment state database.

    Handles database initialization, connections, and provides
    high-level methods for deployment state management.
    """

    def __init__(self, db_path: Optional[Union[str, Path]] = None):
        """
        Initialize deployment database.

        Args:
            db_path: Path to SQLite database file. If None, uses default location.
        """
        if db_path is None:
            # Default to ~/.sbkube/deployments.db
            default_dir = Path.home() / ".sbkube"
            default_dir.mkdir(exist_ok=True)
            db_path = default_dir / "deployments.db"

        self.db_path = Path(db_path)
        self.db_path.parent.mkdir(parents=True, exist_ok=True)

        # Create engine with connection pooling suitable for SQLite
        self.engine = create_engine(
            f"sqlite:///{self.db_path}",
            connect_args={"check_same_thread": False},
            poolclass=StaticPool,
            echo=False,
        )

        # Enable foreign keys for SQLite
        @event.listens_for(self.engine, "connect")
        def set_sqlite_pragma(dbapi_connection, connection_record):
            cursor = dbapi_connection.cursor()
            cursor.execute("PRAGMA foreign_keys=ON")
            cursor.close()

        # Create session factory
        self.SessionLocal = sessionmaker(
            autocommit=False, autoflush=False, bind=self.engine
        )

        # Initialize database
        self._init_database()

    def _init_database(self):
        """Initialize database schema."""
        try:
            Base.metadata.create_all(bind=self.engine)
            logger.verbose(f"Database initialized at: {self.db_path}")
        except Exception as e:
            logger.error(f"Failed to initialize database: {e}")
            raise

    @contextmanager
    def get_session(self) -> Session:
        """
        Get a database session with automatic cleanup.

        Yields:
            SQLAlchemy session
        """
        session = self.SessionLocal()
        try:
            yield session
            session.commit()
        except Exception:
            session.rollback()
            raise
        finally:
            session.close()

    def create_deployment(self, deployment_data: DeploymentCreate) -> Deployment:
        """
        Create a new deployment record.

        Args:
            deployment_data: Deployment creation data

        Returns:
            Created deployment object
        """
        with self.get_session() as session:
            deployment = Deployment(
                deployment_id=deployment_data.deployment_id,
                cluster=deployment_data.cluster,
                namespace=deployment_data.namespace,
                app_config_dir=deployment_data.app_config_dir,
                config_file_path=deployment_data.config_file_path,
                command=deployment_data.command,
                command_args=deployment_data.command_args,
                dry_run=deployment_data.dry_run,
                config_snapshot=deployment_data.config_snapshot,
                sources_snapshot=deployment_data.sources_snapshot,
                sbkube_version=deployment_data.sbkube_version,
                operator=deployment_data.operator,
            )
            session.add(deployment)
            session.flush()
            session.refresh(deployment)

            # Detach the object from session to prevent DetachedInstanceError
            session.expunge(deployment)

            return deployment

    def add_app_deployment(
        self, deployment_id: int, app_data: AppDeploymentCreate
    ) -> AppDeployment:
        """
        Add an app deployment to a deployment.

        Args:
            deployment_id: Parent deployment ID
            app_data: App deployment data

        Returns:
            Created app deployment object
        """
        with self.get_session() as session:
            app_deployment = AppDeployment(
                deployment_id=deployment_id,
                app_name=app_data.app_name,
                app_type=app_data.app_type,
                namespace=app_data.namespace,
                app_config=app_data.app_config,
                deployment_metadata=app_data.deployment_metadata,
            )
            session.add(app_deployment)
            session.flush()
            session.refresh(app_deployment)

            # Pre-load all necessary attributes before session closes
            _ = app_deployment.id
            _ = app_deployment.app_name
            _ = app_deployment.app_type
            _ = app_deployment.namespace
            _ = app_deployment.status

            # Detach the object from session to prevent DetachedInstanceError
            session.expunge(app_deployment)

            return app_deployment

    def add_deployed_resource(
        self, app_deployment_id: int, resource_info: ResourceInfo
    ) -> DeployedResource:
        """
        Add a deployed resource record.

        Args:
            app_deployment_id: Parent app deployment ID
            resource_info: Resource information

        Returns:
            Created resource object
        """
        with self.get_session() as session:
            resource = DeployedResource(
                app_deployment_id=app_deployment_id,
                api_version=resource_info.api_version,
                kind=resource_info.kind,
                name=resource_info.name,
                namespace=resource_info.namespace,
                action=resource_info.action.value,
                previous_state=resource_info.previous_state,
                current_state=resource_info.current_state,
                checksum=resource_info.checksum,
                source_file=resource_info.source_file,
            )
            session.add(resource)
            session.flush()
            session.refresh(resource)

            # Pre-load all necessary attributes before session closes
            _ = resource.id
            _ = resource.api_version
            _ = resource.kind
            _ = resource.name
            _ = resource.namespace
            _ = resource.action

            # Detach the object from session to prevent DetachedInstanceError
            session.expunge(resource)

            return resource

    def add_helm_release(
        self, app_deployment_id: int, release_info: HelmReleaseInfo
    ) -> HelmRelease:
        """
        Add a Helm release record.

        Args:
            app_deployment_id: Parent app deployment ID
            release_info: Helm release information

        Returns:
            Created Helm release object
        """
        with self.get_session() as session:
            release = HelmRelease(
                app_deployment_id=app_deployment_id,
                release_name=release_info.release_name,
                namespace=release_info.namespace,
                chart=release_info.chart,
                chart_version=release_info.chart_version,
                app_version=release_info.app_version,
                revision=release_info.revision,
                values=release_info.values,
                status=release_info.status,
            )
            session.add(release)
            session.flush()
            session.refresh(release)

            # Pre-load all necessary attributes before session closes
            _ = release.id
            _ = release.release_name
            _ = release.namespace
            _ = release.chart
            _ = release.status

            # Detach the object from session to prevent DetachedInstanceError
            session.expunge(release)

            return release

    def update_deployment_status(
        self,
        deployment_id: str,
        status: DeploymentStatus,
        error_message: Optional[str] = None,
    ):
        """
        Update deployment status.

        Args:
            deployment_id: Deployment ID
            status: New status
            error_message: Optional error message
        """
        with self.get_session() as session:
            deployment = (
                session.query(Deployment).filter_by(deployment_id=deployment_id).first()
            )

            if deployment:
                deployment.status = status.value
                if error_message:
                    deployment.error_message = error_message

    def update_app_deployment_status(
        self,
        app_deployment_id: int,
        status: DeploymentStatus,
        error_message: Optional[str] = None,
        rollback_info: Optional[Dict[str, Any]] = None,
    ):
        """
        Update app deployment status.

        Args:
            app_deployment_id: App deployment ID
            status: New status
            error_message: Optional error message
            rollback_info: Optional rollback information
        """
        with self.get_session() as session:
            app_deployment = session.query(AppDeployment).get(app_deployment_id)

            if app_deployment:
                app_deployment.status = status.value
                if error_message:
                    app_deployment.error_message = error_message
                if rollback_info:
                    app_deployment.rollback_info = rollback_info

    def get_deployment(self, deployment_id: str) -> Optional[DeploymentDetail]:
        """
        Get detailed deployment information.

        Args:
            deployment_id: Deployment ID

        Returns:
            Deployment details or None if not found
        """
        with self.get_session() as session:
            deployment = (
                session.query(Deployment).filter_by(deployment_id=deployment_id).first()
            )

            if not deployment:
                return None

            # Build deployment detail
            detail = DeploymentDetail(
                deployment_id=deployment.deployment_id,
                timestamp=deployment.timestamp,
                cluster=deployment.cluster,
                namespace=deployment.namespace,
                app_config_dir=deployment.app_config_dir,
                status=DeploymentStatus(deployment.status),
                error_message=deployment.error_message,
                config_snapshot=deployment.config_snapshot,
                apps=[],
                resources=[],
                helm_releases=[],
            )

            # Add app deployments and their resources
            for app_dep in deployment.app_deployments:
                app_info = {
                    "id": app_dep.id,
                    "name": app_dep.app_name,
                    "type": app_dep.app_type,
                    "namespace": app_dep.namespace,
                    "status": app_dep.status,
                    "error_message": app_dep.error_message,
                    "config": app_dep.app_config,
                    "deployment_metadata": app_dep.deployment_metadata,
                    "rollback_info": app_dep.rollback_info,
                }
                detail.apps.append(app_info)

                # Add resources
                for resource in app_dep.resources:
                    detail.resources.append(
                        ResourceInfo(
                            api_version=resource.api_version,
                            kind=resource.kind,
                            name=resource.name,
                            namespace=resource.namespace,
                            action=ResourceAction(resource.action),
                            previous_state=resource.previous_state,
                            current_state=resource.current_state,
                            checksum=resource.checksum,
                            source_file=resource.source_file,
                        )
                    )

                # Add Helm releases
                helm_releases = (
                    session.query(HelmRelease)
                    .filter_by(app_deployment_id=app_dep.id)
                    .all()
                )

                for release in helm_releases:
                    detail.helm_releases.append(
                        HelmReleaseInfo(
                            release_name=release.release_name,
                            namespace=release.namespace,
                            chart=release.chart,
                            chart_version=release.chart_version,
                            app_version=release.app_version,
                            revision=release.revision,
                            values=release.values,
                            status=release.status,
                        )
                    )

            return detail

    def list_deployments(
        self,
        cluster: Optional[str] = None,
        namespace: Optional[str] = None,
        limit: int = 50,
        offset: int = 0,
    ) -> List[DeploymentSummary]:
        """
        List deployments with optional filtering.

        Args:
            cluster: Filter by cluster
            namespace: Filter by namespace
            limit: Maximum number of results
            offset: Result offset for pagination

        Returns:
            List of deployment summaries
        """
        with self.get_session() as session:
            query = session.query(Deployment)

            if cluster:
                query = query.filter_by(cluster=cluster)
            if namespace:
                query = query.filter_by(namespace=namespace)

            query = query.order_by(Deployment.timestamp.desc())
            query = query.limit(limit).offset(offset)

            summaries = []
            for deployment in query:
                # Count app statuses
                total_apps = len(deployment.app_deployments)
                success_apps = sum(
                    1
                    for app in deployment.app_deployments
                    if app.status == DeploymentStatus.SUCCESS.value
                )
                failed_apps = sum(
                    1
                    for app in deployment.app_deployments
                    if app.status
                    in [
                        DeploymentStatus.FAILED.value,
                        DeploymentStatus.PARTIALLY_FAILED.value,
                    ]
                )

                summaries.append(
                    DeploymentSummary(
                        deployment_id=deployment.deployment_id,
                        timestamp=deployment.timestamp,
                        cluster=deployment.cluster,
                        namespace=deployment.namespace,
                        status=DeploymentStatus(deployment.status),
                        app_count=total_apps,
                        success_count=success_apps,
                        failed_count=failed_apps,
                        error_message=deployment.error_message,
                    )
                )

            return summaries

    def get_latest_deployment(
        self, cluster: str, namespace: str, app_config_dir: str
    ) -> Optional[DeploymentDetail]:
        """
        Get the latest deployment for a specific configuration.

        Args:
            cluster: Cluster name
            namespace: Namespace
            app_config_dir: Application configuration directory

        Returns:
            Latest deployment details or None
        """
        with self.get_session() as session:
            deployment = (
                session.query(Deployment)
                .filter_by(
                    cluster=cluster, namespace=namespace, app_config_dir=app_config_dir
                )
                .order_by(Deployment.timestamp.desc())
                .first()
            )

            if deployment:
                return self.get_deployment(deployment.deployment_id)

            return None

    def cleanup_old_deployments(
        self, days_to_keep: int = 30, max_deployments_per_app: int = 10
    ) -> int:
        """
        Clean up old deployment records.

        Args:
            days_to_keep: Number of days to keep deployments
            max_deployments_per_app: Maximum deployments to keep per app

        Returns:
            Number of deployments deleted
        """
        with self.get_session() as session:
            # Delete deployments older than specified days
            cutoff_date = text(f"datetime('now', '-{days_to_keep} days')")

            old_deployments = (
                session.query(Deployment)
                .filter(Deployment.timestamp < cutoff_date)
                .all()
            )

            deleted_count = len(old_deployments)

            for deployment in old_deployments:
                session.delete(deployment)

            # TODO: Implement max_deployments_per_app cleanup

            return deleted_count

    @staticmethod
    def compute_resource_checksum(resource_data: Dict[str, Any]) -> str:
        """
        Compute checksum for a resource.

        Args:
            resource_data: Resource data dictionary

        Returns:
            SHA256 checksum hex string
        """
        # Remove volatile fields before computing checksum
        data_copy = resource_data.copy()
        volatile_fields = [
            "metadata.resourceVersion",
            "metadata.uid",
            "metadata.generation",
            "metadata.creationTimestamp",
            "status",
        ]

        for field_path in volatile_fields:
            parts = field_path.split(".")
            current = data_copy
            for part in parts[:-1]:
                if part in current:
                    current = current[part]
                else:
                    break
            else:
                if parts[-1] in current:
                    del current[parts[-1]]

        # Compute checksum
        json_str = json.dumps(data_copy, sort_keys=True)
        return hashlib.sha256(json_str.encode()).hexdigest()
