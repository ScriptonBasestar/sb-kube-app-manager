import uuid
from dataclasses import dataclass, field
from datetime import datetime
from enum import Enum
from typing import Any


class StepStatus(Enum):
    PENDING = "pending"
    IN_PROGRESS = "in_progress"
    COMPLETED = "completed"
    FAILED = "failed"
    SKIPPED = "skipped"


@dataclass
class StepExecution:
    """단계별 실행 정보"""

    name: str
    status: StepStatus = StepStatus.PENDING
    started_at: datetime | None = None
    completed_at: datetime | None = None
    duration: float | None = None
    error: str | None = None
    output: str | None = None
    metadata: dict[str, Any] = field(default_factory=dict)

    def start(self):
        """단계 시작"""
        self.status = StepStatus.IN_PROGRESS
        self.started_at = datetime.utcnow()

    def complete(self, output: str = None):
        """단계 완료"""
        self.status = StepStatus.COMPLETED
        self.completed_at = datetime.utcnow()
        if self.started_at:
            self.duration = (self.completed_at - self.started_at).total_seconds()
        if output:
            self.output = output

    def fail(self, error: str):
        """단계 실패"""
        self.status = StepStatus.FAILED
        self.completed_at = datetime.utcnow()
        if self.started_at:
            self.duration = (self.completed_at - self.started_at).total_seconds()
        self.error = error

    def skip(self, reason: str):
        """단계 건너뛰기"""
        self.status = StepStatus.SKIPPED
        self.metadata["skip_reason"] = reason

    def to_dict(self) -> dict[str, Any]:
        """딕셔너리로 변환"""
        return {
            "name": self.name,
            "status": self.status.value,
            "started_at": self.started_at.isoformat() if self.started_at else None,
            "completed_at": (
                self.completed_at.isoformat() if self.completed_at else None
            ),
            "duration": self.duration,
            "error": self.error,
            "output": self.output,
            "metadata": self.metadata,
        }

    @classmethod
    def from_dict(cls, data: dict[str, Any]) -> "StepExecution":
        """딕셔너리에서 생성"""
        step = cls(name=data["name"])
        step.status = StepStatus(data["status"])
        step.started_at = (
            datetime.fromisoformat(data["started_at"]) if data["started_at"] else None
        )
        step.completed_at = (
            datetime.fromisoformat(data["completed_at"])
            if data["completed_at"]
            else None
        )
        step.duration = data.get("duration")
        step.error = data.get("error")
        step.output = data.get("output")
        step.metadata = data.get("metadata", {})
        return step


@dataclass
class ExecutionState:
    """전체 실행 상태"""

    run_id: str = field(default_factory=lambda: str(uuid.uuid4()))
    profile: str | None = None
    namespace: str | None = None
    started_at: datetime = field(default_factory=datetime.utcnow)
    completed_at: datetime | None = None
    status: StepStatus = StepStatus.IN_PROGRESS
    steps: dict[str, StepExecution] = field(default_factory=dict)
    config_hash: str | None = None
    metadata: dict[str, Any] = field(default_factory=dict)

    def add_step(self, step_name: str) -> StepExecution:
        """단계 추가"""
        step = StepExecution(name=step_name)
        self.steps[step_name] = step
        return step

    def get_step(self, step_name: str) -> StepExecution | None:
        """단계 조회"""
        return self.steps.get(step_name)

    def get_failed_step(self) -> StepExecution | None:
        """실패한 단계 조회"""
        for step in self.steps.values():
            if step.status == StepStatus.FAILED:
                return step
        return None

    def get_last_completed_step(self) -> str | None:
        """마지막 완료된 단계명 반환"""
        completed_steps = [
            step.name
            for step in self.steps.values()
            if step.status == StepStatus.COMPLETED
        ]
        return completed_steps[-1] if completed_steps else None

    def get_next_step(self, step_order: list[str]) -> str | None:
        """다음 실행해야 할 단계 반환"""
        for step_name in step_order:
            step = self.steps.get(step_name)
            if not step or step.status in [StepStatus.PENDING, StepStatus.FAILED]:
                return step_name
        return None

    def complete(self):
        """전체 실행 완료"""
        self.status = StepStatus.COMPLETED
        self.completed_at = datetime.utcnow()

    def fail(self):
        """전체 실행 실패"""
        self.status = StepStatus.FAILED
        self.completed_at = datetime.utcnow()

    def to_dict(self) -> dict[str, Any]:
        """딕셔너리로 변환"""
        return {
            "run_id": self.run_id,
            "profile": self.profile,
            "namespace": self.namespace,
            "started_at": self.started_at.isoformat(),
            "completed_at": (
                self.completed_at.isoformat() if self.completed_at else None
            ),
            "status": self.status.value,
            "steps": {name: step.to_dict() for name, step in self.steps.items()},
            "config_hash": self.config_hash,
            "metadata": self.metadata,
        }

    @classmethod
    def from_dict(cls, data: dict[str, Any]) -> "ExecutionState":
        """딕셔너리에서 생성"""
        state = cls()
        state.run_id = data["run_id"]
        state.profile = data.get("profile")
        state.namespace = data.get("namespace")
        state.started_at = datetime.fromisoformat(data["started_at"])
        state.completed_at = (
            datetime.fromisoformat(data["completed_at"])
            if data["completed_at"]
            else None
        )
        state.status = StepStatus(data["status"])
        state.config_hash = data.get("config_hash")
        state.metadata = data.get("metadata", {})

        # 단계 복원
        for step_name, step_data in data.get("steps", {}).items():
            state.steps[step_name] = StepExecution.from_dict(step_data)

        return state
