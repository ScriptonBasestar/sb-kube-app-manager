"""State DB records for the deploy gate (``sbkube/utils/deploy_gate.py``)."""

from sqlalchemy import Column, DateTime, Index, Integer, String, Text

from sbkube.models.deployment_state import Base
from sbkube.utils.datetime_utils import utc_now


class DeployGateSkip(Base):
    """A human ``--skip-deploy-gate=<reason>`` use."""

    __tablename__ = "deploy_gate_skips"

    id = Column(Integer, primary_key=True)
    timestamp = Column(DateTime, default=utc_now, nullable=False)
    operation = Column(String(50), nullable=False)
    target_dir = Column(String(1024), nullable=False)
    gate_file = Column(String(1024), nullable=True)
    reason = Column(Text, nullable=False)
    operator = Column(String(255), nullable=True)

    __table_args__ = (Index("idx_deploy_gate_skip_timestamp", "timestamp"),)


class DeployGateGrant(Base):
    """A human ``sbkube gate grant`` for one agent session.

    The session is a process (``pid`` plus its ``pid_started`` time, so a
    reused PID does not inherit the grant); the gate passes only for
    commands that descend from it. ``expires_at`` is ``None`` for
    ``ttl: unlimited``, which then ends when that process ends.
    """

    __tablename__ = "deploy_gate_grants"

    id = Column(Integer, primary_key=True)
    granted_at = Column(DateTime, default=utc_now, nullable=False)
    expires_at = Column(DateTime, nullable=True)
    gate_dir = Column(String(1024), nullable=False)
    pid = Column(Integer, nullable=False)
    pid_started = Column(String(64), nullable=False)
    reason = Column(Text, nullable=False)
    operator = Column(String(255), nullable=True)

    __table_args__ = (Index("idx_deploy_gate_grant_gate_dir", "gate_dir"),)
