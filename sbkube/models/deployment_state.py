"""
Deployment state tracking models for rollback functionality.

This module provides SQLAlchemy models and Pydantic schemas for tracking
deployment states and enabling rollback operations.
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
    UniqueConstraint,
)
from sqlalchemy.orm import declarative_base, relationship

Base = declarative_base()


class DeploymentStatus(str, Enum):
    """Deployment status enumeration."""

    PENDING = "pending"
    IN_PROGRESS = "in_progress"
    SUCCESS = "success"
    FAILED = "failed"
    ROLLED_BACK = "rolled_back"
    PARTIALLY_FAILED = "partially_failed"


class ResourceAction(str, Enum):
    """Resource action types."""

    CREATE = "create"
    UPDATE = "update"
    DELETE = "delete"
    APPLY = "apply"
    ROLLBACK = "rollback"


# SQLAlchemy Models


class Deployment(Base):
    """Main deployment record."""

    __tablename__ = "deployments"

    id = Column(Integer, primary_key=True)
    deployment_id = Column(String(64), unique=True, nullable=False, index=True)
    timestamp = Column(DateTime, default=datetime.utcnow, nullable=False)

    # Deployment context
    cluster = Column(String(255), nullable=False)
    namespace = Column(String(255), nullable=False)
    app_config_dir = Column(String(1024), nullable=False)
    config_file_path = Column(String(1024), nullable=False)

    # Command context
    command = Column(String(50), nullable=False)  # deploy, rollback, etc.
    command_args = Column(JSON, nullable=True)  # CLI arguments
    dry_run = Column(Boolean, default=False)

    # State
    status = Column(String(20), default=DeploymentStatus.PENDING.value)
    error_message = Column(Text, nullable=True)

    # Configuration snapshot
    config_snapshot = Column(JSON, nullable=False)  # Complete config.yaml content
    sources_snapshot = Column(JSON, nullable=True)  # sources.yaml if available

    # Metadata
    sbkube_version = Column(String(20), nullable=True)
    operator = Column(String(255), nullable=True)  # User who ran the command

    # Relationships
    app_deployments = relationship(
        "AppDeployment",
        back_populates="deployment",
        cascade="all, delete-orphan",
    )

    __table_args__ = (
        Index("idx_deployment_timestamp", "timestamp"),
        Index("idx_deployment_cluster_namespace", "cluster", "namespace"),
    )


class AppDeployment(Base):
    """Individual app deployment within a deployment."""

    __tablename__ = "app_deployments"

    id = Column(Integer, primary_key=True)
    deployment_id = Column(Integer, ForeignKey("deployments.id"), nullable=False)

    # App info
    app_name = Column(String(255), nullable=False)
    app_type = Column(String(50), nullable=False)
    app_group = Column(String(255), nullable=True)  # Phase 2: app-group tracking
    namespace = Column(String(255), nullable=True)

    # State
    status = Column(String(20), default=DeploymentStatus.PENDING.value)
    error_message = Column(Text, nullable=True)

    # App configuration
    app_config = Column(JSON, nullable=False)  # App specs from config

    # Type-specific metadata
    deployment_metadata = Column(JSON, nullable=True)  # Type-specific deployment info

    # Rollback information
    rollback_info = Column(JSON, nullable=True)  # Info needed for rollback

    # Relationships
    deployment = relationship("Deployment", back_populates="app_deployments")
    resources = relationship(
        "DeployedResource",
        back_populates="app_deployment",
        cascade="all, delete-orphan",
    )

    __table_args__ = (
        Index("idx_app_deployment_name", "app_name"),
        Index("idx_app_deployment_type", "app_type"),
        Index("idx_app_deployment_group", "app_group"),  # Phase 2: app-group index
    )


class DeployedResource(Base):
    """Individual Kubernetes resource deployed."""

    __tablename__ = "deployed_resources"

    id = Column(Integer, primary_key=True)
    app_deployment_id = Column(
        Integer,
        ForeignKey("app_deployments.id"),
        nullable=False,
    )

    # Resource identification
    api_version = Column(String(100), nullable=False)
    kind = Column(String(100), nullable=False)
    name = Column(String(255), nullable=False)
    namespace = Column(String(255), nullable=True)

    # Action taken
    action = Column(String(20), nullable=False)  # create, update, delete

    # State snapshots
    previous_state = Column(
        JSON,
        nullable=True,
    )  # Previous resource state (for rollback)
    current_state = Column(JSON, nullable=True)  # Current resource state

    # Metadata
    checksum = Column(String(64), nullable=True)  # SHA256 of resource
    source_file = Column(String(1024), nullable=True)  # Source YAML file

    # Relationships
    app_deployment = relationship("AppDeployment", back_populates="resources")

    __table_args__ = (
        UniqueConstraint(
            "app_deployment_id",
            "api_version",
            "kind",
            "name",
            "namespace",
            name="uq_resource_identity",
        ),
        Index("idx_resource_kind_name", "kind", "name"),
    )


class HelmRelease(Base):
    """Helm release tracking."""

    __tablename__ = "helm_releases"

    id = Column(Integer, primary_key=True)
    app_deployment_id = Column(
        Integer,
        ForeignKey("app_deployments.id"),
        nullable=False,
    )

    # Helm release info
    release_name = Column(String(255), nullable=False)
    namespace = Column(String(255), nullable=False)
    chart = Column(String(255), nullable=False)
    chart_version = Column(String(50), nullable=True)
    app_version = Column(String(50), nullable=True)

    # Helm state
    revision = Column(Integer, nullable=False)
    values = Column(JSON, nullable=True)  # Values used for deployment

    # Status
    status = Column(String(50), nullable=False)  # deployed, failed, etc.

    __table_args__ = (
        UniqueConstraint("release_name", "namespace", name="uq_helm_release"),
        Index("idx_helm_release_name", "release_name"),
    )


# Pydantic Schemas for API/CLI interaction


class DeploymentCreate(BaseModel):
    """Schema for creating a deployment record."""

    deployment_id: str
    cluster: str
    namespace: str
    app_config_dir: str
    config_file_path: str
    command: str
    command_args: dict[str, Any] | None = None
    dry_run: bool = False
    config_snapshot: dict[str, Any]
    sources_snapshot: dict[str, Any] | None = None
    sbkube_version: str | None = None
    operator: str | None = None


class AppDeploymentCreate(BaseModel):
    """Schema for creating an app deployment record."""

    app_name: str
    app_type: str
    app_group: str | None = None  # Phase 2: app-group tracking
    namespace: str | None = None
    app_config: dict[str, Any]
    deployment_metadata: dict[str, Any] | None = None


class ResourceInfo(BaseModel):
    """Schema for resource information."""

    api_version: str
    kind: str
    name: str
    namespace: str | None = None
    action: ResourceAction
    previous_state: dict[str, Any] | None = None
    current_state: dict[str, Any] | None = None
    checksum: str | None = None
    source_file: str | None = None


class HelmReleaseInfo(BaseModel):
    """Schema for Helm release information."""

    release_name: str
    namespace: str
    chart: str
    chart_version: str | None = None
    app_version: str | None = None
    revision: int
    values: dict[str, Any] | None = None
    status: str


class DeploymentSummary(BaseModel):
    """Schema for deployment summary."""

    model_config = ConfigDict(from_attributes=True)

    deployment_id: str
    timestamp: datetime
    cluster: str
    namespace: str
    status: DeploymentStatus
    app_count: int
    success_count: int
    failed_count: int
    error_message: str | None = None


class DeploymentDetail(BaseModel):
    """Schema for detailed deployment information."""

    model_config = ConfigDict(from_attributes=True)

    deployment_id: str
    timestamp: datetime
    cluster: str
    namespace: str
    app_config_dir: str
    status: DeploymentStatus
    error_message: str | None = None
    config_snapshot: dict[str, Any]
    apps: list[dict[str, Any]] = []
    resources: list[ResourceInfo] = []
    helm_releases: list[HelmReleaseInfo] = []


class RollbackRequest(BaseModel):
    """Schema for rollback request."""

    deployment_id: str
    target_deployment_id: str | None = None  # Roll back to specific deployment
    app_names: list[str] | None = None  # Selective rollback
    dry_run: bool = False
    force: bool = False  # Force rollback even with warnings
