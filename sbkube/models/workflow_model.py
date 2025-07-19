from dataclasses import dataclass, field
from enum import Enum
from typing import Any

import yaml


class StepType(Enum):
    BUILTIN = "builtin"  # sbkube 내장 명령어
    SCRIPT = "script"  # 사용자 스크립트
    PARALLEL = "parallel"  # 병렬 실행 그룹


class StepStatus(Enum):
    PENDING = "pending"
    RUNNING = "running"
    COMPLETED = "completed"
    FAILED = "failed"
    SKIPPED = "skipped"


@dataclass
class WorkflowStep:
    """워크플로우 단계"""

    name: str
    type: StepType = StepType.BUILTIN
    command: str | None = None
    script: str | None = None
    condition: str | None = None
    parallel: bool = False
    apps: list[str] | None = None
    timeout: int = 300  # 5분 기본 타임아웃
    retry_count: int = 0
    on_failure: str | None = None  # continue, stop, retry
    metadata: dict[str, Any] = field(default_factory=dict)

    # 실행 상태
    status: StepStatus = StepStatus.PENDING
    started_at: str | None = None
    completed_at: str | None = None
    output: str | None = None
    error: str | None = None

    def to_dict(self) -> dict[str, Any]:
        """딕셔너리로 변환"""
        return {
            "name": self.name,
            "type": self.type.value,
            "command": self.command,
            "script": self.script,
            "condition": self.condition,
            "parallel": self.parallel,
            "apps": self.apps,
            "timeout": self.timeout,
            "retry_count": self.retry_count,
            "on_failure": self.on_failure,
            "metadata": self.metadata,
            "status": self.status.value,
            "started_at": self.started_at,
            "completed_at": self.completed_at,
            "output": self.output,
            "error": self.error,
        }

    @classmethod
    def from_dict(cls, data: dict[str, Any]) -> "WorkflowStep":
        """딕셔너리에서 생성"""
        step = cls(
            name=data["name"],
            type=StepType(data.get("type", "builtin")),
            command=data.get("command"),
            script=data.get("script"),
            condition=data.get("condition"),
            parallel=data.get("parallel", False),
            apps=data.get("apps"),
            timeout=data.get("timeout", 300),
            retry_count=data.get("retry_count", 0),
            on_failure=data.get("on_failure"),
            metadata=data.get("metadata", {}),
        )

        # 실행 상태 복원
        if "status" in data:
            step.status = StepStatus(data["status"])
        step.started_at = data.get("started_at")
        step.completed_at = data.get("completed_at")
        step.output = data.get("output")
        step.error = data.get("error")

        return step


@dataclass
class Workflow:
    """워크플로우 정의"""

    name: str
    description: str = ""
    version: str = "1.0"
    variables: dict[str, Any] = field(default_factory=dict)
    steps: list[WorkflowStep] = field(default_factory=list)

    # 실행 상태
    status: StepStatus = StepStatus.PENDING
    started_at: str | None = None
    completed_at: str | None = None

    def to_dict(self) -> dict[str, Any]:
        """딕셔너리로 변환"""
        return {
            "name": self.name,
            "description": self.description,
            "version": self.version,
            "variables": self.variables,
            "steps": [step.to_dict() for step in self.steps],
            "status": self.status.value,
            "started_at": self.started_at,
            "completed_at": self.completed_at,
        }

    @classmethod
    def from_dict(cls, data: dict[str, Any]) -> "Workflow":
        """딕셔너리에서 생성"""
        workflow = cls(
            name=data["name"],
            description=data.get("description", ""),
            version=data.get("version", "1.0"),
            variables=data.get("variables", {}),
            steps=[
                WorkflowStep.from_dict(step_data) for step_data in data.get("steps", [])
            ],
        )

        # 실행 상태 복원
        if "status" in data:
            workflow.status = StepStatus(data["status"])
        workflow.started_at = data.get("started_at")
        workflow.completed_at = data.get("completed_at")

        return workflow

    @classmethod
    def from_yaml_file(cls, file_path: str) -> "Workflow":
        """YAML 파일에서 로드"""
        with open(file_path, encoding="utf-8") as f:
            data = yaml.safe_load(f)

        return cls.from_dict(data)

    def save_to_yaml(self, file_path: str):
        """YAML 파일로 저장"""
        with open(file_path, "w", encoding="utf-8") as f:
            yaml.dump(self.to_dict(), f, default_flow_style=False, allow_unicode=True)

    def get_step(self, name: str) -> WorkflowStep | None:
        """단계 이름으로 조회"""
        return next((step for step in self.steps if step.name == name), None)

    def get_pending_steps(self) -> list[WorkflowStep]:
        """대기 중인 단계들"""
        return [step for step in self.steps if step.status == StepStatus.PENDING]

    def get_failed_steps(self) -> list[WorkflowStep]:
        """실패한 단계들"""
        return [step for step in self.steps if step.status == StepStatus.FAILED]
