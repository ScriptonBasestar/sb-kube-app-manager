"""Workspace deployment state tracking models.

This module provides SQLAlchemy models and Pydantic schemas for tracking
workspace multi-phase deployment states.
"""

from datetime import datetime
from enum import Enum
from typing import Any

from pydantic import BaseModel, ConfigDict
from sqlalchemy import (
    JSON,
    Boolean,
    Column,
    DateTime,
    ForeignKey,
    Index,
    Integer,
    String,
    Text,
)
from sqlalchemy.orm import relationship

from sbkube.models.deployment_state import Base
from sbkube.utils.datetime_utils import utc_now


class WorkspaceDeploymentStatus(str, Enum):
    """Workspace deployment status enumeration."""

    PENDING = "pending"
    IN_PROGRESS = "in_progress"
    SUCCESS = "success"
    FAILED = "failed"
    PARTIALLY_FAILED = "partially_failed"
    CANCELLED = "cancelled"


class PhaseDeploymentStatus(str, Enum):
    """Phase deployment status enumeration."""

    PENDING = "pending"
    IN_PROGRESS = "in_progress"
    SUCCESS = "success"
    FAILED = "failed"
    SKIPPED = "skipped"
    ROLLED_BACK = "rolled_back"


# SQLAlchemy Models


class WorkspaceDeployment(Base):
    """Main workspace deployment record."""

    __tablename__ = "workspace_deployments"

    id = Column(Integer, primary_key=True)
    workspace_deployment_id = Column(
        String(64), unique=True, nullable=False, index=True
    )
    timestamp = Column(DateTime, default=utc_now, nullable=False)
    completed_at = Column(DateTime, nullable=True)

    # Workspace context
    workspace_name = Column(String(255), nullable=False)
    workspace_file = Column(String(1024), nullable=False)
    environment = Column(String(50), nullable=True)

    # Execution context
    dry_run = Column(Boolean, default=False)
    force = Column(Boolean, default=False)
    target_phase = Column(String(255), nullable=True)  # If specific phase requested

    # State
    status = Column(String(20), default=WorkspaceDeploymentStatus.PENDING.value)
    error_message = Column(Text, nullable=True)

    # Statistics
    total_phases = Column(Integer, default=0)
    completed_phases = Column(Integer, default=0)
    failed_phases = Column(Integer, default=0)
    skipped_phases = Column(Integer, default=0)

    # Configuration snapshot
    workspace_config = Column(JSON, nullable=False)  # Complete workspace.yaml content

    # Metadata
    sbkube_version = Column(String(20), nullable=True)
    operator = Column(String(255), nullable=True)

    # Relationships
    phase_deployments = relationship(
        "PhaseDeployment",
        back_populates="workspace_deployment",
        cascade="all, delete-orphan",
        order_by="PhaseDeployment.execution_order",
    )

    __table_args__ = (
        Index("idx_workspace_deployment_timestamp", "timestamp"),
        Index("idx_workspace_deployment_name", "workspace_name"),
    )


class PhaseDeployment(Base):
    """Individual phase deployment within a workspace deployment."""

    __tablename__ = "phase_deployments"

    id = Column(Integer, primary_key=True)
    phase_deployment_id = Column(String(64), unique=True, nullable=False, index=True)

    # Parent relationship
    workspace_deployment_id = Column(
        Integer,
        ForeignKey("workspace_deployments.id", ondelete="CASCADE"),
        nullable=False,
    )

    # Phase context
    phase_name = Column(String(255), nullable=False)
    phase_description = Column(Text, nullable=True)
    source_path = Column(String(1024), nullable=False)
    execution_order = Column(Integer, nullable=False)

    # Dependencies
    depends_on = Column(JSON, nullable=True)  # List of phase names

    # App groups
    app_groups = Column(JSON, nullable=False)  # List of app group names
    total_app_groups = Column(Integer, default=0)
    completed_app_groups = Column(Integer, default=0)

    # Timing
    started_at = Column(DateTime, nullable=True)
    completed_at = Column(DateTime, nullable=True)
    duration_seconds = Column(Integer, nullable=True)

    # State
    status = Column(String(20), default=PhaseDeploymentStatus.PENDING.value)
    error_message = Column(Text, nullable=True)
    on_failure_action = Column(String(20), nullable=True)  # stop, continue, rollback

    # Relationships
    workspace_deployment = relationship(
        "WorkspaceDeployment", back_populates="phase_deployments"
    )

    __table_args__ = (
        Index("idx_phase_deployment_phase_name", "phase_name"),
        Index(
            "idx_phase_deployment_workspace", "workspace_deployment_id", "execution_order"
        ),
    )


# Pydantic Schemas for API


class PhaseDeploymentCreate(BaseModel):
    """Schema for creating a phase deployment record."""

    phase_name: str
    phase_description: str | None = None
    source_path: str
    execution_order: int
    depends_on: list[str] = []
    app_groups: list[str]
    on_failure_action: str | None = None

    model_config = ConfigDict(from_attributes=True)


class PhaseDeploymentInfo(BaseModel):
    """Schema for phase deployment information."""

    phase_deployment_id: str
    phase_name: str
    phase_description: str | None
    execution_order: int
    status: str
    started_at: datetime | None
    completed_at: datetime | None
    duration_seconds: int | None
    app_groups: list[str]
    total_app_groups: int
    completed_app_groups: int
    error_message: str | None

    model_config = ConfigDict(from_attributes=True)


class WorkspaceDeploymentCreate(BaseModel):
    """Schema for creating a workspace deployment record."""

    workspace_name: str
    workspace_file: str
    environment: str | None = None
    dry_run: bool = False
    force: bool = False
    target_phase: str | None = None
    workspace_config: dict[str, Any]

    model_config = ConfigDict(from_attributes=True)


class WorkspaceDeploymentSummary(BaseModel):
    """Summary of a workspace deployment."""

    workspace_deployment_id: str
    workspace_name: str
    environment: str | None
    timestamp: datetime
    completed_at: datetime | None
    status: str
    dry_run: bool
    total_phases: int
    completed_phases: int
    failed_phases: int
    skipped_phases: int

    model_config = ConfigDict(from_attributes=True)


class WorkspaceDeploymentDetail(BaseModel):
    """Detailed workspace deployment information."""

    workspace_deployment_id: str
    workspace_name: str
    workspace_file: str
    environment: str | None
    timestamp: datetime
    completed_at: datetime | None
    status: str
    dry_run: bool
    force: bool
    target_phase: str | None
    total_phases: int
    completed_phases: int
    failed_phases: int
    skipped_phases: int
    error_message: str | None
    sbkube_version: str | None
    operator: str | None
    phases: list[PhaseDeploymentInfo]

    model_config = ConfigDict(from_attributes=True)
