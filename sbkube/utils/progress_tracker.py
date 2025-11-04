"""Progress tracking utilities for SBKube commands.

Rich Progress 바를 활용하여 사용자에게 세밀한 진행 상황을 표시합니다.
"""

from contextlib import contextmanager
from typing import Any

from rich.console import Console
from rich.progress import (
    BarColumn,
    MofNCompleteColumn,
    Progress,
    SpinnerColumn,
    TaskID,
    TextColumn,
    TimeElapsedColumn,
)


class ProgressTracker:
    """진행 상황 추적 및 표시 클래스."""

    def __init__(self, console: Console | None = None, disable: bool = False):
        """ProgressTracker 초기화.

        Args:
            console: Rich Console 인스턴스
            disable: True면 진행 표시 비활성화 (dry-run, --no-progress 등)
        """
        self.console = console or Console()
        self.disable = disable
        self.progress: Progress | None = None
        self.current_task: TaskID | None = None

    def create_progress(self) -> Progress:
        """Rich Progress 객체 생성.

        Returns:
            설정된 Progress 인스턴스
        """
        return Progress(
            SpinnerColumn(),
            TextColumn("[bold blue]{task.description}"),
            BarColumn(),
            MofNCompleteColumn(),
            TextColumn("•"),
            TimeElapsedColumn(),
            console=self.console,
            disable=self.disable,
        )

    @contextmanager
    def track_task(self, description: str, total: int = 100):
        """태스크 진행 상황을 추적하는 컨텍스트 매니저.

        Args:
            description: 태스크 설명
            total: 전체 작업량 (기본값: 100)

        Yields:
            TaskID: 업데이트할 수 있는 task ID

        Example:
            ```python
            tracker = ProgressTracker()
            with tracker.track_task("Downloading charts", total=5) as task_id:
                for i in range(5):
                    # 작업 수행
                    tracker.update(task_id, advance=1)
            ```
        """
        if self.disable:
            yield None
            return

        progress = self.create_progress()
        with progress:
            task_id = progress.add_task(description, total=total)
            self.progress = progress
            self.current_task = task_id
            yield task_id
            self.progress = None
            self.current_task = None

    def update(
        self,
        task_id: TaskID | None,
        advance: float | None = None,
        completed: float | None = None,
        description: str | None = None,
        **kwargs: Any,
    ) -> None:
        """진행 상황 업데이트.

        Args:
            task_id: 업데이트할 task ID
            advance: 진행량 증가분
            completed: 완료된 작업량 (절대값)
            description: 새로운 설명
            **kwargs: Progress.update()의 추가 인자
        """
        if self.disable or not self.progress or task_id is None:
            return

        update_kwargs: dict[str, Any] = {}
        if advance is not None:
            update_kwargs["advance"] = advance
        if completed is not None:
            update_kwargs["completed"] = completed
        if description is not None:
            update_kwargs["description"] = description
        update_kwargs.update(kwargs)

        self.progress.update(task_id, **update_kwargs)

    def console_print(self, *args: Any, **kwargs: Any) -> None:
        """Progress 외부에서 console.print() 호출.

        Progress가 활성화되어 있으면 progress.console.print() 사용,
        그렇지 않으면 일반 console.print() 사용.

        Args:
            *args: print()의 위치 인자
            **kwargs: print()의 키워드 인자
        """
        if self.progress:
            self.progress.console.print(*args, **kwargs)
        else:
            self.console.print(*args, **kwargs)


class DeploymentProgressTracker(ProgressTracker):
    """배포 작업 전용 진행 추적기."""

    def __init__(self, console: Console | None = None, disable: bool = False):
        """DeploymentProgressTracker 초기화.

        Args:
            console: Rich Console 인스턴스
            disable: 진행 표시 비활성화 여부
        """
        super().__init__(console, disable)
        self.steps: dict[str, tuple[str, int]] = {
            "prepare": ("📦 Preparing sources", 0),
            "build": ("🔨 Building application", 0),
            "deploy": ("🚀 Deploying to cluster", 0),
        }

    def set_step_total(self, step: str, total: int) -> None:
        """특정 단계의 전체 작업량 설정.

        Args:
            step: 단계 이름 (prepare, build, deploy)
            total: 전체 작업량
        """
        if step in self.steps:
            desc, _ = self.steps[step]
            self.steps[step] = (desc, total)

    def get_step_description(self, step: str) -> str:
        """단계 설명 가져오기.

        Args:
            step: 단계 이름

        Returns:
            단계 설명 문자열
        """
        return self.steps.get(step, (f"{step}", 0))[0]

    def get_step_total(self, step: str) -> int:
        """단계의 전체 작업량 가져오기.

        Args:
            step: 단계 이름

        Returns:
            전체 작업량
        """
        return self.steps.get(step, ("", 0))[1]


# 전역 인스턴스 (필요시 사용)
_global_tracker: ProgressTracker | None = None


def get_global_tracker() -> ProgressTracker:
    """전역 ProgressTracker 인스턴스 가져오기.

    Returns:
        ProgressTracker 싱글톤 인스턴스
    """
    global _global_tracker
    if _global_tracker is None:
        _global_tracker = ProgressTracker()
    return _global_tracker


def reset_global_tracker() -> None:
    """전역 ProgressTracker 리셋."""
    global _global_tracker
    _global_tracker = None
