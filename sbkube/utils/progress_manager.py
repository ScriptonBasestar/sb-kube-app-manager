import threading
from contextlib import contextmanager
from dataclasses import dataclass, field
from datetime import datetime
from enum import Enum
from typing import Any

from rich.console import Console
from rich.layout import Layout
from rich.live import Live
from rich.panel import Panel
from rich.progress import (
    BarColumn,
    MofNCompleteColumn,
    Progress,
    SpinnerColumn,
    TextColumn,
    TimeElapsedColumn,
    TimeRemainingColumn,
)
from rich.text import Text

from sbkube.utils.logger import logger


class ProgressState(Enum):
    PENDING = "pending"
    RUNNING = "running"
    COMPLETED = "completed"
    FAILED = "failed"
    SKIPPED = "skipped"


@dataclass
class StepProgress:
    """단계별 진행률 정보"""

    name: str
    display_name: str
    total_work: int = 100
    completed_work: int = 0
    state: ProgressState = ProgressState.PENDING
    started_at: datetime | None = None
    estimated_duration: float | None = None
    actual_duration: float | None = None
    sub_tasks: list[str] = field(default_factory=list)
    current_task: str | None = None

    @property
    def progress_percentage(self) -> float:
        """진행률 퍼센트 (0-100)"""
        if self.total_work == 0:
            return 100.0
        return min((self.completed_work / self.total_work) * 100, 100.0)

    @property
    def is_active(self) -> bool:
        """현재 활성 상태인지 확인"""
        return self.state == ProgressState.RUNNING

    def start(self):
        """단계 시작"""
        self.state = ProgressState.RUNNING
        self.started_at = datetime.now()

    def update_progress(self, completed: int, current_task: str = None):
        """진행률 업데이트"""
        self.completed_work = min(completed, self.total_work)
        if current_task:
            self.current_task = current_task

    def complete(self):
        """단계 완료"""
        self.state = ProgressState.COMPLETED
        self.completed_work = self.total_work
        if self.started_at:
            self.actual_duration = (datetime.now() - self.started_at).total_seconds()

    def fail(self):
        """단계 실패"""
        self.state = ProgressState.FAILED
        if self.started_at:
            self.actual_duration = (datetime.now() - self.started_at).total_seconds()

    def skip(self):
        """단계 건너뛰기"""
        self.state = ProgressState.SKIPPED
        self.completed_work = self.total_work


class ProgressManager:
    """진행률 관리자"""

    def __init__(self, console: Console = None, show_progress: bool = True):
        self.console = console or Console()
        self.show_progress = show_progress
        self.steps: dict[str, StepProgress] = {}
        self.step_order: list[str] = []

        if show_progress:
            self.overall_progress = Progress(
                TextColumn("[bold blue]{task.description}"),
                BarColumn(bar_width=40),
                MofNCompleteColumn(),
                TextColumn("•"),
                TimeElapsedColumn(),
                TextColumn("•"),
                TimeRemainingColumn(),
                console=self.console,
                transient=False,
            )
            self.step_progress = Progress(
                SpinnerColumn(),
                TextColumn("[bold green]{task.description}"),
                BarColumn(bar_width=30),
                TextColumn("{task.percentage:>3.0f}%"),
                TextColumn("•"),
                TextColumn("[cyan]{task.fields[current_task]}"),
                console=self.console,
                transient=True,
            )
        else:
            self.overall_progress = None
            self.step_progress = None

        self.layout = Layout() if show_progress else None
        self.live: Live | None = None
        self.update_thread: threading.Thread | None = None
        self.stop_event = threading.Event()

        # 통계 정보
        self.start_time: datetime | None = None
        self.estimated_total_duration: float | None = None
        self.historical_durations: dict[str, list[float]] = {}

    def add_step(
        self,
        step_name: str,
        display_name: str,
        estimated_duration: float = None,
        sub_tasks: list[str] = None,
    ) -> StepProgress:
        """단계 추가"""
        step = StepProgress(
            name=step_name,
            display_name=display_name,
            estimated_duration=estimated_duration,
            sub_tasks=sub_tasks or [],
        )

        self.steps[step_name] = step
        if step_name not in self.step_order:
            self.step_order.append(step_name)

        return step

    def start_overall_progress(self, profile: str = None, namespace: str = None):
        """전체 진행률 표시 시작"""
        if not self.show_progress:
            return

        self.start_time = datetime.now()
        self._estimate_total_duration()

        # 레이아웃 구성
        self._setup_layout(profile, namespace)

        # Live 디스플레이 시작
        self.live = Live(
            self.layout, console=self.console, refresh_per_second=4, transient=False
        )
        self.live.start()

        # 백그라운드 업데이트 시작
        self.stop_event.clear()
        self.update_thread = threading.Thread(target=self._background_update)
        self.update_thread.daemon = True
        self.update_thread.start()

        logger.info("🚀 SBKube 배포 진행 중...")

    def stop_overall_progress(self):
        """전체 진행률 표시 종료"""
        if not self.show_progress:
            return

        if self.update_thread:
            self.stop_event.set()
            self.update_thread.join(timeout=1.0)

        if self.live:
            self.live.stop()
            self.live = None

    @contextmanager
    def track_step(self, step_name: str):
        """단계 진행률 추적 컨텍스트"""
        step = self.steps.get(step_name)
        if not step:
            raise ValueError(f"Unknown step: {step_name}")

        step.start()

        # 진행률 표시가 비활성화된 경우 간단한 트래커 반환
        if not self.show_progress:
            yield SimpleStepTracker(step)
            step.complete()
            return

        # Rich Progress에 태스크 추가
        overall_task = self.overall_progress.add_task(
            f"{step.display_name} 단계", total=100
        )

        step_task = self.step_progress.add_task(
            step.display_name, total=100, current_task="시작 중..."
        )

        try:
            yield StepProgressTracker(self, step, overall_task, step_task)
            step.complete()
            self.overall_progress.update(overall_task, completed=100)

        except Exception:
            step.fail()
            self.overall_progress.update(
                overall_task, description=f"❌ {step.display_name}"
            )
            raise

        finally:
            self.overall_progress.remove_task(overall_task)
            self.step_progress.remove_task(step_task)

    def get_overall_progress(self) -> dict[str, Any]:
        """전체 진행률 정보 반환"""
        if not self.start_time:
            return {}

        completed_steps = len(
            [s for s in self.steps.values() if s.state == ProgressState.COMPLETED]
        )
        total_steps = len(self.steps)
        overall_percentage = (
            (completed_steps / total_steps * 100) if total_steps > 0 else 0
        )

        elapsed_time = (datetime.now() - self.start_time).total_seconds()

        # 예상 완료 시간 계산
        estimated_remaining = None
        if overall_percentage > 0 and self.estimated_total_duration:
            estimated_remaining = max(0, self.estimated_total_duration - elapsed_time)

        return {
            "overall_percentage": overall_percentage,
            "completed_steps": completed_steps,
            "total_steps": total_steps,
            "elapsed_time": elapsed_time,
            "estimated_remaining": estimated_remaining,
            "current_step": self._get_current_step(),
        }

    def _setup_layout(self, profile: str = None, namespace: str = None):
        """레이아웃 구성"""
        if not self.show_progress:
            return

        # 헤더 정보
        header_text = "🚀 SBKube 배포 진행 중"
        if profile:
            header_text += f" ({profile})"
        if namespace:
            header_text += f" → {namespace}"

        header = Panel(Text(header_text, style="bold cyan"), style="blue")

        # 전체 레이아웃
        self.layout.split_column(
            Layout(header, name="header", size=3),
            Layout(self.overall_progress, name="overall"),
            Layout(self.step_progress, name="current"),
        )

    def _background_update(self):
        """백그라운드 업데이트"""
        while not self.stop_event.wait(0.25):  # 250ms마다 업데이트
            try:
                self._update_time_estimates()
            except Exception as e:
                logger.warning(f"진행률 업데이트 오류: {e}")

    def _estimate_total_duration(self):
        """전체 소요 시간 추정"""
        total_estimate = 0

        for step in self.steps.values():
            if step.estimated_duration:
                total_estimate += step.estimated_duration
            else:
                # 과거 데이터 기반 추정
                historical = self.historical_durations.get(step.name, [])
                if historical:
                    total_estimate += sum(historical) / len(historical)
                else:
                    # 기본 추정값 (단계별로 다르게)
                    default_estimates = {
                        "prepare": 30,  # 30초
                        "build": 120,  # 2분
                        "template": 60,  # 1분
                        "deploy": 180,  # 3분
                    }
                    total_estimate += default_estimates.get(step.name, 60)

        self.estimated_total_duration = total_estimate

    def _update_time_estimates(self):
        """시간 추정값 업데이트"""
        if not self.start_time:
            return

        elapsed = (datetime.now() - self.start_time).total_seconds()

        # 전체 진행률 기반 예상 완료 시간 업데이트
        progress_info = self.get_overall_progress()
        if progress_info["overall_percentage"] > 5:  # 5% 이상 진행시
            estimated_total = elapsed / (progress_info["overall_percentage"] / 100)
            max(0, estimated_total - elapsed)

            # 메인 프로그레스 바의 시간 정보 업데이트는 Rich가 자동으로 처리

    def _get_current_step(self) -> str | None:
        """현재 실행 중인 단계 반환"""
        for step in self.steps.values():
            if step.state == ProgressState.RUNNING:
                return step.name
        return None

    def save_historical_data(self):
        """완료된 단계들의 실행 시간을 히스토리에 저장"""
        for step in self.steps.values():
            if step.state == ProgressState.COMPLETED and step.actual_duration:
                if step.name not in self.historical_durations:
                    self.historical_durations[step.name] = []

                # 최근 10개만 유지
                self.historical_durations[step.name].append(step.actual_duration)
                if len(self.historical_durations[step.name]) > 10:
                    self.historical_durations[step.name].pop(0)


class StepProgressTracker:
    """단계별 진행률 추적기 (Rich Progress 지원)"""

    def __init__(
        self,
        manager: ProgressManager,
        step: StepProgress,
        overall_task_id,
        step_task_id,
    ):
        self.manager = manager
        self.step = step
        self.overall_task_id = overall_task_id
        self.step_task_id = step_task_id

    def update(self, percentage: float, current_task: str = "처리 중..."):
        """진행률 업데이트"""
        percentage = max(0, min(100, percentage))

        self.step.update_progress(int(percentage), current_task)

        # Rich Progress 업데이트
        self.manager.overall_progress.update(self.overall_task_id, completed=percentage)

        self.manager.step_progress.update(
            self.step_task_id, completed=percentage, current_task=current_task
        )

    def set_sub_task(self, task_name: str):
        """현재 하위 작업 설정"""
        self.step.current_task = task_name
        self.manager.step_progress.update(self.step_task_id, current_task=task_name)


class SimpleStepTracker:
    """간단한 단계 추적기 (진행률 표시 없음)"""

    def __init__(self, step: StepProgress):
        self.step = step

    def update(self, percentage: float, current_task: str = "처리 중..."):
        """진행률 업데이트 (로그만)"""
        self.step.update_progress(int(percentage), current_task)
        if percentage % 25 == 0:  # 25% 단위로만 로그
            logger.verbose(f"{self.step.display_name}: {percentage}% - {current_task}")

    def set_sub_task(self, task_name: str):
        """현재 하위 작업 설정"""
        self.step.current_task = task_name
        logger.verbose(f"{self.step.display_name}: {task_name}")
