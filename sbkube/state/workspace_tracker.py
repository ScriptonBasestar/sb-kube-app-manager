"""Workspace deployment state tracker.

This module provides state tracking for workspace multi-phase deployments.
"""

import hashlib
import os
from datetime import datetime

from sqlalchemy.orm import Session

from sbkube.models.workspace_state import (
    PhaseDeployment,
    PhaseDeploymentCreate,
    PhaseDeploymentInfo,
    PhaseDeploymentStatus,
    WorkspaceDeployment,
    WorkspaceDeploymentCreate,
    WorkspaceDeploymentDetail,
    WorkspaceDeploymentStatus,
    WorkspaceDeploymentSummary,
)
from sbkube.utils.logger import get_logger

logger = get_logger()


def generate_workspace_deployment_id(
    workspace_name: str,
    workspace_file: str,
    timestamp: datetime,
) -> str:
    """Generate unique workspace deployment ID.

    Args:
        workspace_name: Name of the workspace
        workspace_file: Path to workspace.yaml
        timestamp: Deployment timestamp

    Returns:
        Unique deployment ID (SHA256 hash prefix)

    """
    data = f"{workspace_name}:{workspace_file}:{timestamp.isoformat()}"
    return hashlib.sha256(data.encode()).hexdigest()[:16]


def generate_phase_deployment_id(
    workspace_deployment_id: str,
    phase_name: str,
    execution_order: int,
) -> str:
    """Generate unique phase deployment ID.

    Args:
        workspace_deployment_id: Parent workspace deployment ID
        phase_name: Name of the phase
        execution_order: Execution order of the phase

    Returns:
        Unique phase deployment ID (SHA256 hash prefix)

    """
    data = f"{workspace_deployment_id}:{phase_name}:{execution_order}"
    return hashlib.sha256(data.encode()).hexdigest()[:16]


class WorkspaceStateTracker:
    """Tracks workspace deployment state.

    Provides methods for recording and querying workspace deployment history.
    """

    def __init__(self, session: Session) -> None:
        """Initialize workspace state tracker.

        Args:
            session: SQLAlchemy database session

        """
        self.session = session

    def start_workspace_deployment(
        self,
        create_data: WorkspaceDeploymentCreate,
        sbkube_version: str | None = None,
    ) -> WorkspaceDeployment:
        """Start a new workspace deployment.

        Args:
            create_data: Workspace deployment creation data
            sbkube_version: SBKube version

        Returns:
            Created WorkspaceDeployment record

        """
        timestamp = datetime.utcnow()
        deployment_id = generate_workspace_deployment_id(
            create_data.workspace_name,
            create_data.workspace_file,
            timestamp,
        )

        deployment = WorkspaceDeployment(
            workspace_deployment_id=deployment_id,
            timestamp=timestamp,
            workspace_name=create_data.workspace_name,
            workspace_file=create_data.workspace_file,
            environment=create_data.environment,
            dry_run=create_data.dry_run,
            force=create_data.force,
            target_phase=create_data.target_phase,
            status=WorkspaceDeploymentStatus.IN_PROGRESS.value,
            workspace_config=create_data.workspace_config,
            sbkube_version=sbkube_version,
            operator=os.environ.get("USER", os.environ.get("USERNAME", "unknown")),
        )

        self.session.add(deployment)
        self.session.commit()

        logger.verbose(f"Started workspace deployment: {deployment_id}")
        return deployment

    def add_phase_deployment(
        self,
        workspace_deployment: WorkspaceDeployment,
        phase_data: PhaseDeploymentCreate,
    ) -> PhaseDeployment:
        """Add a phase deployment record.

        Args:
            workspace_deployment: Parent workspace deployment
            phase_data: Phase deployment creation data

        Returns:
            Created PhaseDeployment record

        """
        phase_id = generate_phase_deployment_id(
            workspace_deployment.workspace_deployment_id,
            phase_data.phase_name,
            phase_data.execution_order,
        )

        phase = PhaseDeployment(
            phase_deployment_id=phase_id,
            workspace_deployment_id=workspace_deployment.id,
            phase_name=phase_data.phase_name,
            phase_description=phase_data.phase_description,
            source_path=phase_data.source_path,
            execution_order=phase_data.execution_order,
            depends_on=phase_data.depends_on,
            app_groups=phase_data.app_groups,
            total_app_groups=len(phase_data.app_groups),
            on_failure_action=phase_data.on_failure_action,
            status=PhaseDeploymentStatus.PENDING.value,
        )

        self.session.add(phase)
        workspace_deployment.total_phases += 1
        self.session.commit()

        return phase

    def start_phase(self, phase: PhaseDeployment) -> None:
        """Mark phase as started.

        Args:
            phase: Phase deployment to start

        """
        phase.status = PhaseDeploymentStatus.IN_PROGRESS.value
        phase.started_at = datetime.utcnow()
        self.session.commit()

        logger.verbose(f"Started phase: {phase.phase_name}")

    def complete_phase(
        self,
        phase: PhaseDeployment,
        success: bool,
        error_message: str | None = None,
        completed_app_groups: int = 0,
    ) -> None:
        """Mark phase as completed.

        Args:
            phase: Phase deployment to complete
            success: Whether the phase succeeded
            error_message: Error message if failed
            completed_app_groups: Number of completed app groups

        """
        phase.completed_at = datetime.utcnow()
        phase.completed_app_groups = completed_app_groups

        if phase.started_at:
            duration = (phase.completed_at - phase.started_at).total_seconds()
            phase.duration_seconds = int(duration)

        if success:
            phase.status = PhaseDeploymentStatus.SUCCESS.value
        else:
            phase.status = PhaseDeploymentStatus.FAILED.value
            phase.error_message = error_message

        # Update parent deployment counters
        workspace = phase.workspace_deployment
        if success:
            workspace.completed_phases += 1
        else:
            workspace.failed_phases += 1

        self.session.commit()

        logger.verbose(
            f"Completed phase: {phase.phase_name} "
            f"(status={phase.status}, duration={phase.duration_seconds}s)"
        )

    def skip_phase(self, phase: PhaseDeployment, reason: str | None = None) -> None:
        """Mark phase as skipped.

        Args:
            phase: Phase deployment to skip
            reason: Reason for skipping

        """
        phase.status = PhaseDeploymentStatus.SKIPPED.value
        phase.error_message = reason
        phase.workspace_deployment.skipped_phases += 1
        self.session.commit()

        logger.verbose(f"Skipped phase: {phase.phase_name}")

    def complete_workspace_deployment(
        self,
        deployment: WorkspaceDeployment,
        success: bool,
        error_message: str | None = None,
    ) -> None:
        """Mark workspace deployment as completed.

        Args:
            deployment: Workspace deployment to complete
            success: Whether the deployment succeeded
            error_message: Error message if failed

        """
        deployment.completed_at = datetime.utcnow()

        if success:
            deployment.status = WorkspaceDeploymentStatus.SUCCESS.value
        elif deployment.completed_phases > 0 and deployment.failed_phases > 0:
            deployment.status = WorkspaceDeploymentStatus.PARTIALLY_FAILED.value
            deployment.error_message = error_message
        else:
            deployment.status = WorkspaceDeploymentStatus.FAILED.value
            deployment.error_message = error_message

        self.session.commit()

        logger.verbose(
            f"Completed workspace deployment: {deployment.workspace_deployment_id} "
            f"(status={deployment.status})"
        )

    def get_workspace_deployment(
        self, deployment_id: str
    ) -> WorkspaceDeployment | None:
        """Get workspace deployment by ID.

        Args:
            deployment_id: Workspace deployment ID

        Returns:
            WorkspaceDeployment or None if not found

        """
        return (
            self.session.query(WorkspaceDeployment)
            .filter(WorkspaceDeployment.workspace_deployment_id == deployment_id)
            .first()
        )

    def list_workspace_deployments(
        self,
        workspace_name: str | None = None,
        limit: int = 20,
        offset: int = 0,
    ) -> list[WorkspaceDeploymentSummary]:
        """List workspace deployments.

        Args:
            workspace_name: Filter by workspace name
            limit: Maximum number of results
            offset: Result offset

        Returns:
            List of workspace deployment summaries

        """
        query = self.session.query(WorkspaceDeployment)

        if workspace_name:
            query = query.filter(WorkspaceDeployment.workspace_name == workspace_name)

        query = query.order_by(WorkspaceDeployment.timestamp.desc())
        query = query.offset(offset).limit(limit)

        deployments = query.all()

        return [
            WorkspaceDeploymentSummary(
                workspace_deployment_id=d.workspace_deployment_id,
                workspace_name=d.workspace_name,
                environment=d.environment,
                timestamp=d.timestamp,
                completed_at=d.completed_at,
                status=d.status,
                dry_run=d.dry_run,
                total_phases=d.total_phases,
                completed_phases=d.completed_phases,
                failed_phases=d.failed_phases,
                skipped_phases=d.skipped_phases,
            )
            for d in deployments
        ]

    def get_workspace_deployment_detail(
        self, deployment_id: str
    ) -> WorkspaceDeploymentDetail | None:
        """Get detailed workspace deployment information.

        Args:
            deployment_id: Workspace deployment ID

        Returns:
            Detailed deployment info or None if not found

        """
        deployment = self.get_workspace_deployment(deployment_id)
        if not deployment:
            return None

        phases = [
            PhaseDeploymentInfo(
                phase_deployment_id=p.phase_deployment_id,
                phase_name=p.phase_name,
                phase_description=p.phase_description,
                execution_order=p.execution_order,
                status=p.status,
                started_at=p.started_at,
                completed_at=p.completed_at,
                duration_seconds=p.duration_seconds,
                app_groups=p.app_groups or [],
                total_app_groups=p.total_app_groups,
                completed_app_groups=p.completed_app_groups,
                error_message=p.error_message,
            )
            for p in deployment.phase_deployments
        ]

        return WorkspaceDeploymentDetail(
            workspace_deployment_id=deployment.workspace_deployment_id,
            workspace_name=deployment.workspace_name,
            workspace_file=deployment.workspace_file,
            environment=deployment.environment,
            timestamp=deployment.timestamp,
            completed_at=deployment.completed_at,
            status=deployment.status,
            dry_run=deployment.dry_run,
            force=deployment.force,
            target_phase=deployment.target_phase,
            total_phases=deployment.total_phases,
            completed_phases=deployment.completed_phases,
            failed_phases=deployment.failed_phases,
            skipped_phases=deployment.skipped_phases,
            error_message=deployment.error_message,
            sbkube_version=deployment.sbkube_version,
            operator=deployment.operator,
            phases=phases,
        )

    def get_latest_workspace_deployment(
        self, workspace_name: str
    ) -> WorkspaceDeployment | None:
        """Get the latest deployment for a workspace.

        Args:
            workspace_name: Name of the workspace

        Returns:
            Latest WorkspaceDeployment or None

        """
        return (
            self.session.query(WorkspaceDeployment)
            .filter(WorkspaceDeployment.workspace_name == workspace_name)
            .order_by(WorkspaceDeployment.timestamp.desc())
            .first()
        )
