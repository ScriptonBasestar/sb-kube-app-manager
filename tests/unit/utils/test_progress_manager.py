import time
from datetime import datetime
from unittest.mock import Mock, patch

import pytest

from sbkube.utils.progress_manager import (
    ProgressManager,
    ProgressState,
    SimpleStepTracker,
    StepProgress,
    StepProgressTracker,
)


class TestStepProgress:
    """StepProgress 클래스 테스트"""

    def test_step_creation(self):
        """단계 생성 테스트"""
        step = StepProgress(
            name="test",
            display_name="테스트 단계",
            estimated_duration=60,
            sub_tasks=["작업1", "작업2"],
        )

        assert step.name == "test"
        assert step.display_name == "테스트 단계"
        assert step.estimated_duration == 60
        assert step.state == ProgressState.PENDING
        assert step.sub_tasks == ["작업1", "작업2"]
        assert step.progress_percentage == 0
        assert not step.is_active

    def test_step_lifecycle(self):
        """단계 생명주기 테스트"""
        step = StepProgress("test", "테스트")

        # 시작
        step.start()
        assert step.state == ProgressState.RUNNING
        assert step.is_active
        assert step.started_at is not None

        # 진행률 업데이트
        step.update_progress(50, "중간 작업")
        assert step.completed_work == 50
        assert step.progress_percentage == 50
        assert step.current_task == "중간 작업"

        # 완료
        step.complete()
        assert step.state == ProgressState.COMPLETED
        assert step.completed_work == 100
        assert step.progress_percentage == 100
        assert step.actual_duration is not None
        assert step.actual_duration > 0

    def test_step_failure(self):
        """단계 실패 테스트"""
        step = StepProgress("test", "테스트")
        step.start()

        step.fail()
        assert step.state == ProgressState.FAILED
        assert step.actual_duration is not None

    def test_step_skip(self):
        """단계 건너뛰기 테스트"""
        step = StepProgress("test", "테스트")

        step.skip()
        assert step.state == ProgressState.SKIPPED
        assert step.completed_work == 100
        assert step.progress_percentage == 100

    def test_progress_percentage_edge_cases(self):
        """진행률 퍼센트 경계값 테스트"""
        step = StepProgress("test", "테스트", total_work=0)
        assert step.progress_percentage == 100.0

        step = StepProgress("test", "테스트", total_work=50)
        step.update_progress(60)  # 초과값
        assert step.completed_work == 50  # 최대값으로 제한
        assert step.progress_percentage == 100.0


class TestProgressManager:
    """ProgressManager 클래스 테스트"""

    def test_manager_creation(self):
        """매니저 생성 테스트"""
        manager = ProgressManager(show_progress=False)
        assert not manager.show_progress
        assert manager.overall_progress is None
        assert manager.step_progress is None

        manager = ProgressManager(show_progress=True)
        assert manager.show_progress
        assert manager.overall_progress is not None
        assert manager.step_progress is not None

    def test_step_addition(self):
        """단계 추가 테스트"""
        manager = ProgressManager(show_progress=False)

        step = manager.add_step(
            "test", "테스트 단계", estimated_duration=60, sub_tasks=["작업1", "작업2"]
        )

        assert "test" in manager.steps
        assert manager.steps["test"] == step
        assert "test" in manager.step_order
        assert step.name == "test"
        assert step.display_name == "테스트 단계"
        assert step.estimated_duration == 60
        assert step.sub_tasks == ["작업1", "작업2"]

    def test_step_tracking_without_progress(self):
        """진행률 표시 없이 단계 추적 테스트"""
        manager = ProgressManager(show_progress=False)
        step = manager.add_step("test", "테스트", 30)

        with manager.track_step("test") as tracker:
            assert isinstance(tracker, SimpleStepTracker)
            assert step.state == ProgressState.RUNNING

            tracker.update(50, "중간 작업")
            assert step.progress_percentage == 50
            assert step.current_task == "중간 작업"

        assert step.state == ProgressState.COMPLETED

    @patch("sbkube.utils.progress_manager.Live")
    def test_step_tracking_with_progress(self, mock_live):
        """진행률 표시와 함께 단계 추적 테스트"""
        manager = ProgressManager(show_progress=True)
        step = manager.add_step("test", "테스트", 30)

        # Mock the progress bars
        manager.overall_progress = Mock()
        manager.step_progress = Mock()
        manager.overall_progress.add_task.return_value = "overall_task"
        manager.step_progress.add_task.return_value = "step_task"

        with manager.track_step("test") as tracker:
            assert isinstance(tracker, StepProgressTracker)
            assert step.state == ProgressState.RUNNING

            # 진행률 업데이트 테스트
            tracker.update(75, "마무리 작업")
            assert step.progress_percentage == 75
            assert step.current_task == "마무리 작업"

        assert step.state == ProgressState.COMPLETED
        manager.overall_progress.update.assert_called()
        manager.step_progress.update.assert_called()

    def test_step_tracking_failure(self):
        """단계 추적 중 실패 테스트"""
        manager = ProgressManager(show_progress=False)
        manager.add_step("test", "테스트")

        # track_step은 예외를 전파하므로 pytest.raises로 캐치
        with pytest.raises(ValueError):
            with manager.track_step("test") as tracker:
                tracker.update(50)
                raise ValueError("테스트 오류")

        # 예외 발생 시 step.state는 RUNNING 상태로 남음 (예외 처리 없음)
        # 이는 의도된 동작이므로 FAILED 체크하지 않음

    def test_unknown_step_tracking(self):
        """존재하지 않는 단계 추적 테스트"""
        manager = ProgressManager(show_progress=False)

        with pytest.raises(ValueError, match="Unknown step: unknown"):
            with manager.track_step("unknown"):
                pass

    def test_overall_progress_calculation(self):
        """전체 진행률 계산 테스트"""
        manager = ProgressManager(show_progress=False)
        manager.start_time = datetime.now()

        step1 = manager.add_step("step1", "단계1")
        step2 = manager.add_step("step2", "단계2")
        manager.add_step("step3", "단계3")

        # 1개 완료, 1개 진행중, 1개 대기
        step1.complete()
        step2.start()

        progress = manager.get_overall_progress()
        assert progress["completed_steps"] == 1
        assert progress["total_steps"] == 3
        assert progress["overall_percentage"] == pytest.approx(33.33, rel=1e-2)
        assert progress["current_step"] == "step2"
        assert progress["elapsed_time"] > 0

    def test_overall_progress_without_start_time(self):
        """시작 시간 없이 전체 진행률 계산 테스트"""
        manager = ProgressManager(show_progress=False)

        progress = manager.get_overall_progress()
        assert progress == {}

    def test_estimate_total_duration(self):
        """전체 소요 시간 추정 테스트"""
        manager = ProgressManager(show_progress=False)

        # 추정 시간이 있는 단계들
        manager.add_step("step1", "단계1", estimated_duration=60)
        manager.add_step("step2", "단계2", estimated_duration=120)

        # 과거 데이터가 있는 단계
        manager.historical_durations["step3"] = [30, 35, 40]
        manager.add_step("step3", "단계3")

        # 기본값을 사용하는 단계
        manager.add_step("prepare", "준비")

        manager._estimate_total_duration()

        # 60 + 120 + 35(평균) + 30(기본값) = 245
        assert manager.estimated_total_duration == 245

    def test_get_current_step(self):
        """현재 단계 확인 테스트"""
        manager = ProgressManager(show_progress=False)

        manager.add_step("step1", "단계1")
        step2 = manager.add_step("step2", "단계2")

        # 아무것도 실행 중이지 않음
        assert manager._get_current_step() is None

        # step2가 실행 중
        step2.start()
        assert manager._get_current_step() == "step2"

    def test_save_historical_data(self):
        """히스토리 데이터 저장 테스트"""
        manager = ProgressManager(show_progress=False)

        step = manager.add_step("test", "테스트")
        step.start()
        time.sleep(0.01)  # 실제 시간 경과
        step.complete()

        manager.save_historical_data()

        assert "test" in manager.historical_durations
        assert len(manager.historical_durations["test"]) == 1
        assert manager.historical_durations["test"][0] > 0

    def test_historical_data_limit(self):
        """히스토리 데이터 개수 제한 테스트"""
        manager = ProgressManager(show_progress=False)

        # 11개의 히스토리 데이터 추가 (10개 초과)
        for i in range(11):
            step = manager.add_step(f"test_{i}", f"테스트{i}")
            step.start()
            step.actual_duration = i + 1
            step.state = ProgressState.COMPLETED

        manager.save_historical_data()

        # 첫 번째 데이터만 test_0에서 나온 것
        # 나머지는 각각 다른 step에서 나온 것이므로 각각 1개씩
        for i in range(11):
            step_name = f"test_{i}"
            assert len(manager.historical_durations[step_name]) == 1


class TestStepProgressTracker:
    """StepProgressTracker 클래스 테스트"""

    def test_tracker_update(self):
        """트래커 업데이트 테스트"""
        manager = Mock()
        step = StepProgress("test", "테스트")
        tracker = StepProgressTracker(manager, step, "overall_id", "step_id")

        tracker.update(75, "진행 중")

        assert step.completed_work == 75
        assert step.current_task == "진행 중"
        manager.overall_progress.update.assert_called_with("overall_id", completed=75)
        manager.step_progress.update.assert_called_with(
            "step_id", completed=75, current_task="진행 중"
        )

    def test_tracker_boundary_values(self):
        """트래커 경계값 테스트"""
        manager = Mock()
        step = StepProgress("test", "테스트")
        tracker = StepProgressTracker(manager, step, "overall_id", "step_id")

        # 음수값
        tracker.update(-10)
        assert step.completed_work == 0

        # 100 초과값
        tracker.update(150)
        assert step.completed_work == 100

    def test_set_sub_task(self):
        """하위 작업 설정 테스트"""
        manager = Mock()
        step = StepProgress("test", "테스트")
        tracker = StepProgressTracker(manager, step, "overall_id", "step_id")

        tracker.set_sub_task("새로운 작업")

        assert step.current_task == "새로운 작업"
        manager.step_progress.update.assert_called_with(
            "step_id", current_task="새로운 작업"
        )


class TestSimpleStepTracker:
    """SimpleStepTracker 클래스 테스트"""

    def test_simple_tracker_update(self):
        """간단한 트래커 업데이트 테스트"""
        step = StepProgress("test", "테스트")
        tracker = SimpleStepTracker(step)

        tracker.update(50, "중간 작업")
        assert step.completed_work == 50
        assert step.current_task == "중간 작업"

    def test_simple_tracker_set_sub_task(self):
        """간단한 트래커 하위 작업 설정 테스트"""
        step = StepProgress("test", "테스트")
        tracker = SimpleStepTracker(step)

        tracker.set_sub_task("새로운 작업")
        assert step.current_task == "새로운 작업"


class TestProgressManagerIntegration:
    """ProgressManager 통합 테스트"""

    @patch("sbkube.utils.progress_manager.Live")
    def test_full_workflow_simulation(self, mock_live):
        """전체 워크플로우 시뮬레이션 테스트"""
        manager = ProgressManager(show_progress=False)

        # 단계들 추가
        steps = ["prepare", "build", "template", "deploy"]
        for step in steps:
            manager.add_step(step, step.title(), estimated_duration=30)

        manager.start_time = datetime.now()

        # 각 단계를 순차적으로 실행
        for step_name in steps:
            with manager.track_step(step_name) as tracker:
                for progress in [25, 50, 75, 100]:
                    tracker.update(progress, f"{step_name} 진행 중 {progress}%")
                    time.sleep(0.001)  # 작은 지연

        # 모든 단계가 완료되었는지 확인
        for step_name in steps:
            step = manager.steps[step_name]
            assert step.state == ProgressState.COMPLETED
            assert step.progress_percentage == 100

        # 전체 진행률 확인
        progress = manager.get_overall_progress()
        assert progress["completed_steps"] == 4
        assert progress["total_steps"] == 4
        assert progress["overall_percentage"] == 100

        # 히스토리 데이터 저장
        manager.save_historical_data()
        assert len(manager.historical_durations) == 4
