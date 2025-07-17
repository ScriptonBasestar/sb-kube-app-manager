---
phase: 2
order: 10
source_plan: /tasks/plan/phase2-advanced-features.md
priority: medium
tags: [progress-tracking, rich-ui, real-time-display]
estimated_days: 3
depends_on: [009-smart-restart-history-management]
---

# 📌 작업: 실시간 진행률 표시 시스템 구현

## 🎯 목표
Rich Progress Bar를 활용하여 단계별 진행률을 실시간으로 표시하고, 예상 완료 시간을 제공하는 시스템을 구현합니다.

## 📋 작업 내용

### 1. 진행률 관리자 구현
```python
# sbkube/utils/progress_manager.py
from typing import Dict, Any, Optional, List, Callable
from datetime import datetime, timedelta
from dataclasses import dataclass, field
from enum import Enum
import time
import threading
from contextlib import contextmanager

from rich.console import Console
from rich.progress import (
    Progress, BarColumn, TextColumn, TimeElapsedColumn, 
    TimeRemainingColumn, MofNCompleteColumn, SpinnerColumn
)
from rich.live import Live
from rich.panel import Panel
from rich.layout import Layout
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
    started_at: Optional[datetime] = None
    estimated_duration: Optional[float] = None
    actual_duration: Optional[float] = None
    sub_tasks: List[str] = field(default_factory=list)
    current_task: Optional[str] = None
    
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
    
    def __init__(self, console: Console = None):
        self.console = console or Console()
        self.steps: Dict[str, StepProgress] = {}
        self.step_order: List[str] = []
        self.overall_progress = Progress(
            TextColumn("[bold blue]{task.description}"),
            BarColumn(bar_width=40),
            MofNCompleteColumn(),
            TextColumn("•"),
            TimeElapsedColumn(),
            TextColumn("•"),
            TimeRemainingColumn(),
            console=self.console,
            transient=False
        )
        self.step_progress = Progress(
            SpinnerColumn(),
            TextColumn("[bold green]{task.description}"),
            BarColumn(bar_width=30),
            TextColumn("{task.percentage:>3.0f}%"),
            TextColumn("•"),
            TextColumn("[cyan]{task.fields[current_task]}"),
            console=self.console,
            transient=True
        )
        
        self.layout = Layout()
        self.live: Optional[Live] = None
        self.update_thread: Optional[threading.Thread] = None
        self.stop_event = threading.Event()
        
        # 통계 정보
        self.start_time: Optional[datetime] = None
        self.estimated_total_duration: Optional[float] = None
        self.historical_durations: Dict[str, List[float]] = {}
    
    def add_step(self, 
                step_name: str, 
                display_name: str, 
                estimated_duration: float = None,
                sub_tasks: List[str] = None) -> StepProgress:
        """단계 추가"""
        step = StepProgress(
            name=step_name,
            display_name=display_name,
            estimated_duration=estimated_duration,
            sub_tasks=sub_tasks or []
        )
        
        self.steps[step_name] = step
        if step_name not in self.step_order:
            self.step_order.append(step_name)
        
        return step
    
    def start_overall_progress(self, profile: str = None, namespace: str = None):
        """전체 진행률 표시 시작"""
        self.start_time = datetime.now()
        self._estimate_total_duration()
        
        # 레이아웃 구성
        self._setup_layout(profile, namespace)
        
        # Live 디스플레이 시작
        self.live = Live(
            self.layout,
            console=self.console,
            refresh_per_second=4,
            transient=False
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
        
        # Rich Progress에 태스크 추가
        overall_task = self.overall_progress.add_task(
            f"{step.display_name} 단계",
            total=100
        )
        
        step_task = self.step_progress.add_task(
            step.display_name,
            total=100,
            current_task="시작 중..."
        )
        
        try:
            yield StepProgressTracker(self, step, overall_task, step_task)
            step.complete()
            self.overall_progress.update(overall_task, completed=100)
            
        except Exception as e:
            step.fail()
            self.overall_progress.update(overall_task, description=f"❌ {step.display_name}")
            raise
        
        finally:
            self.overall_progress.remove_task(overall_task)
            self.step_progress.remove_task(step_task)
    
    def get_overall_progress(self) -> Dict[str, Any]:
        """전체 진행률 정보 반환"""
        if not self.start_time:
            return {}
        
        completed_steps = len([s for s in self.steps.values() if s.state == ProgressState.COMPLETED])
        total_steps = len(self.steps)
        overall_percentage = (completed_steps / total_steps * 100) if total_steps > 0 else 0
        
        elapsed_time = (datetime.now() - self.start_time).total_seconds()
        
        # 예상 완료 시간 계산
        estimated_remaining = None
        if overall_percentage > 0 and self.estimated_total_duration:
            estimated_remaining = max(0, self.estimated_total_duration - elapsed_time)
        
        return {
            'overall_percentage': overall_percentage,
            'completed_steps': completed_steps,
            'total_steps': total_steps,
            'elapsed_time': elapsed_time,
            'estimated_remaining': estimated_remaining,
            'current_step': self._get_current_step()
        }
    
    def _setup_layout(self, profile: str = None, namespace: str = None):
        """레이아웃 구성"""
        # 헤더 정보
        header_text = "🚀 SBKube 배포 진행 중"
        if profile:
            header_text += f" ({profile})"
        if namespace:
            header_text += f" → {namespace}"
        
        header = Panel(
            Text(header_text, style="bold cyan"),
            style="blue"
        )
        
        # 전체 레이아웃
        self.layout.split_column(
            Layout(header, name="header", size=3),
            Layout(self.overall_progress, name="overall"),
            Layout(self.step_progress, name="current")
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
                        'prepare': 30,   # 30초
                        'build': 120,    # 2분
                        'template': 60,  # 1분
                        'deploy': 180    # 3분
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
        if progress_info['overall_percentage'] > 5:  # 5% 이상 진행시
            estimated_total = elapsed / (progress_info['overall_percentage'] / 100)
            remaining = max(0, estimated_total - elapsed)
            
            # 메인 프로그레스 바의 시간 정보 업데이트는 Rich가 자동으로 처리
    
    def _get_current_step(self) -> Optional[str]:
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
    """단계별 진행률 추적기"""
    
    def __init__(self, manager: ProgressManager, step: StepProgress, 
                 overall_task_id, step_task_id):
        self.manager = manager
        self.step = step
        self.overall_task_id = overall_task_id
        self.step_task_id = step_task_id
    
    def update(self, percentage: float, current_task: str = "처리 중..."):
        """진행률 업데이트"""
        percentage = max(0, min(100, percentage))
        
        self.step.update_progress(int(percentage), current_task)
        
        # Rich Progress 업데이트
        self.manager.overall_progress.update(
            self.overall_task_id, 
            completed=percentage
        )
        
        self.manager.step_progress.update(
            self.step_task_id,
            completed=percentage,
            current_task=current_task
        )
    
    def set_sub_task(self, task_name: str):
        """현재 하위 작업 설정"""
        self.step.current_task = task_name
        self.manager.step_progress.update(
            self.step_task_id,
            current_task=task_name
        )
```

### 2. BaseCommand에 진행률 통합
```python
# sbkube/utils/base_command.py 수정
from sbkube.utils.progress_manager import ProgressManager

class BaseCommand:
    def __init__(self, base_dir: str, profile: str = None, 
                 show_progress: bool = True, **kwargs):
        self.base_dir = base_dir
        self.profile = profile
        self.show_progress = show_progress
        self.progress_manager = ProgressManager() if show_progress else None
        self.config = None
    
    def setup_progress_tracking(self, steps: List[str]):
        """진행률 추적 설정"""
        if not self.progress_manager:
            return
        
        step_configs = {
            'prepare': {
                'display_name': '준비',
                'estimated_duration': 30,
                'sub_tasks': ['설정 검증', '의존성 확인', '소스 다운로드']
            },
            'build': {
                'display_name': '빌드',
                'estimated_duration': 120,
                'sub_tasks': ['Helm 차트 빌드', 'YAML 처리', '이미지 준비']
            },
            'template': {
                'display_name': '템플릿',
                'estimated_duration': 60,
                'sub_tasks': ['템플릿 렌더링', '값 적용', '매니페스트 생성']
            },
            'deploy': {
                'display_name': '배포',
                'estimated_duration': 180,
                'sub_tasks': ['네임스페이스 생성', '리소스 적용', '상태 확인']
            }
        }
        
        for step_name in steps:
            if step_name in step_configs:
                config = step_configs[step_name]
                self.progress_manager.add_step(
                    step_name,
                    config['display_name'],
                    config['estimated_duration'],
                    config['sub_tasks']
                )
    
    def start_progress_display(self):
        """진행률 표시 시작"""
        if self.progress_manager:
            config = self.load_config()
            self.progress_manager.start_overall_progress(
                profile=self.profile,
                namespace=config.get('namespace')
            )
    
    def stop_progress_display(self):
        """진행률 표시 종료"""
        if self.progress_manager:
            self.progress_manager.save_historical_data()
            self.progress_manager.stop_overall_progress()
```

### 3. RunCommand에 진행률 통합
```python
# sbkube/commands/run.py 수정
class RunCommand(BaseCommand):
    def execute(self):
        """실행 (진행률 표시 포함)"""
        config = self.load_config()
        
        # 실행할 단계 결정
        steps = self._determine_steps()
        
        # 진행률 추적 설정
        self.setup_progress_tracking(steps)
        
        try:
            # 진행률 표시 시작
            self.start_progress_display()
            
            # 단계별 실행
            for step in steps:
                if self.progress_manager:
                    with self.progress_manager.track_step(step) as tracker:
                        self._execute_step_with_progress(step, config, tracker)
                else:
                    self._execute_step(step, config)
            
            logger.success("🎉 모든 단계가 성공적으로 완료되었습니다!")
            
        finally:
            # 진행률 표시 종료
            self.stop_progress_display()
    
    def _execute_step_with_progress(self, step: str, config: dict, tracker):
        """진행률 추적과 함께 단계 실행"""
        if step == "prepare":
            self._execute_prepare_with_progress(config, tracker)
        elif step == "build":
            self._execute_build_with_progress(config, tracker)
        elif step == "template":
            self._execute_template_with_progress(config, tracker)
        elif step == "deploy":
            self._execute_deploy_with_progress(config, tracker)
    
    def _execute_prepare_with_progress(self, config: dict, tracker):
        """준비 단계 (진행률 포함)"""
        tracker.update(10, "설정 파일 검증 중...")
        time.sleep(0.5)  # 시뮬레이션
        
        tracker.update(30, "의존성 확인 중...")
        # 실제 의존성 확인 로직
        time.sleep(1.0)
        
        tracker.update(60, "소스 다운로드 중...")
        # 실제 소스 다운로드 로직
        time.sleep(1.5)
        
        tracker.update(100, "준비 완료")
    
    def _execute_build_with_progress(self, config: dict, tracker):
        """빌드 단계 (진행률 포함)"""
        apps = config.get('apps', [])
        total_apps = len(apps)
        
        if total_apps == 0:
            tracker.update(100, "빌드할 앱이 없음")
            return
        
        for i, app in enumerate(apps):
            progress = ((i + 1) / total_apps) * 100
            tracker.update(progress, f"{app['name']} 빌드 중...")
            
            # 실제 빌드 로직
            time.sleep(2.0)
        
        tracker.update(100, "모든 앱 빌드 완료")
    
    def _execute_template_with_progress(self, config: dict, tracker):
        """템플릿 단계 (진행률 포함)"""
        tracker.update(20, "템플릿 엔진 초기화...")
        time.sleep(0.5)
        
        tracker.update(50, "값 적용 중...")
        time.sleep(1.0)
        
        tracker.update(80, "매니페스트 생성 중...")
        time.sleep(1.0)
        
        tracker.update(100, "템플릿 처리 완료")
    
    def _execute_deploy_with_progress(self, config: dict, tracker):
        """배포 단계 (진행률 포함)"""
        tracker.update(10, "네임스페이스 확인...")
        time.sleep(0.5)
        
        tracker.update(30, "리소스 적용 중...")
        time.sleep(2.0)
        
        tracker.update(70, "Pod 시작 대기 중...")
        time.sleep(2.0)
        
        tracker.update(90, "상태 확인 중...")
        time.sleep(1.0)
        
        tracker.update(100, "배포 완료")
```

### 4. 진행률 설정 및 커스터마이징
```python
# sbkube/utils/progress_config.py
from typing import Dict, Any
from dataclasses import dataclass

@dataclass
class ProgressConfig:
    """진행률 표시 설정"""
    show_progress: bool = True
    show_spinner: bool = True
    show_time_remaining: bool = True
    update_frequency: float = 0.25  # seconds
    bar_width: int = 40
    
    # 색상 설정
    primary_color: str = "blue"
    success_color: str = "green"
    error_color: str = "red"
    warning_color: str = "yellow"
    
    # 디스플레이 설정
    show_overall_progress: bool = True
    show_step_progress: bool = True
    show_sub_tasks: bool = True
    
    @classmethod
    def from_dict(cls, data: Dict[str, Any]) -> 'ProgressConfig':
        """딕셔너리에서 생성"""
        return cls(**{k: v for k, v in data.items() if hasattr(cls, k)})
    
    def to_dict(self) -> Dict[str, Any]:
        """딕셔너리로 변환"""
        return {
            'show_progress': self.show_progress,
            'show_spinner': self.show_spinner,
            'show_time_remaining': self.show_time_remaining,
            'update_frequency': self.update_frequency,
            'bar_width': self.bar_width,
            'primary_color': self.primary_color,
            'success_color': self.success_color,
            'error_color': self.error_color,
            'warning_color': self.warning_color,
            'show_overall_progress': self.show_overall_progress,
            'show_step_progress': self.show_step_progress,
            'show_sub_tasks': self.show_sub_tasks
        }

# 진행률 설정을 .sbkuberc에서 로드
def load_progress_config(base_dir: str) -> ProgressConfig:
    """진행률 설정 로드"""
    config_file = Path(base_dir) / ".sbkuberc"
    
    if config_file.exists():
        try:
            import yaml
            with open(config_file, 'r', encoding='utf-8') as f:
                data = yaml.safe_load(f) or {}
            
            progress_data = data.get('progress', {})
            return ProgressConfig.from_dict(progress_data)
            
        except Exception as e:
            logger.warning(f"진행률 설정 로드 실패: {e}")
    
    return ProgressConfig()
```

## 🧪 테스트 구현

### 단위 테스트
```python
# tests/unit/utils/test_progress_manager.py
import pytest
import time
from sbkube.utils.progress_manager import ProgressManager, StepProgress, ProgressState

class TestProgressManager:
    def test_step_creation(self):
        """단계 생성 테스트"""
        manager = ProgressManager()
        step = manager.add_step("test", "테스트 단계", 60)
        
        assert step.name == "test"
        assert step.display_name == "테스트 단계"
        assert step.estimated_duration == 60
        assert step.state == ProgressState.PENDING
    
    def test_step_progress_tracking(self):
        """단계 진행률 추적 테스트"""
        manager = ProgressManager()
        step = manager.add_step("test", "테스트", 30)
        
        # Mock console to avoid actual display
        manager.console = None
        
        with manager.track_step("test") as tracker:
            tracker.update(50, "중간 작업")
            assert step.progress_percentage == 50
            assert step.current_task == "중간 작업"
            
            tracker.update(100, "완료")
            assert step.progress_percentage == 100
        
        assert step.state == ProgressState.COMPLETED
    
    def test_overall_progress_calculation(self):
        """전체 진행률 계산 테스트"""
        manager = ProgressManager()
        manager.start_time = datetime.now()
        
        step1 = manager.add_step("step1", "단계1")
        step2 = manager.add_step("step2", "단계2")
        
        step1.complete()
        # step2는 아직 진행 중
        
        progress = manager.get_overall_progress()
        assert progress['completed_steps'] == 1
        assert progress['total_steps'] == 2
        assert progress['overall_percentage'] == 50
```

## ✅ 완료 기준

- [ ] ProgressManager 클래스 구현
- [ ] Rich Progress Bar 통합
- [ ] 단계별 진행률 추적 시스템
- [ ] 실시간 시간 추정 기능
- [ ] BaseCommand 및 RunCommand 통합
- [ ] 진행률 설정 시스템
- [ ] 히스토리 기반 시간 추정
- [ ] 단위 테스트 작성 및 통과

## 🔍 검증 명령어

```bash
# 진행률 표시와 함께 실행
sbkube run

# 진행률 없이 실행 (기존 방식)
sbkube run --no-progress

# 특정 단계만 실행하여 진행률 확인
sbkube run --only build

# 테스트 실행
pytest tests/unit/utils/test_progress_manager.py -v
```

## 📝 예상 결과

```
🚀 SBKube 배포 진행 중 (production) → prod-namespace
━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
├── [✓] 준비    ━━━━━━━━━━━━━━━━ 100% (1m 30s)
├── [✓] 빌드    ━━━━━━━━━━━━━━━━ 100% (2m 15s)  
├── [▶] 템플릿  ━━━━━━━━━━━━━░░░  75% (45s) 
└── [ ] 배포    ━━━━━━━━━━━━━░░░   0% (대기중)

⚡ 템플릿 ━━━━━━━━━━━━━━━━━━━━━━━ 75% • 매니페스트 생성 중...

전체 진행률: 68% • 경과 시간: 4분 30초 • 예상 완료: 약 1분 30초 후
```

## 🔄 다음 단계

이 작업 완료 후 다음 작업으로 진행:
- `011-enhanced-logging-system.md` - 향상된 로깅 시스템 구현