import pytest
import tempfile
import json
from pathlib import Path
from sbkube.utils.execution_tracker import ExecutionTracker
from sbkube.models.execution_state import StepStatus


class TestExecutionTracker:
    def test_start_new_execution(self):
        """새 실행 시작 테스트"""
        with tempfile.TemporaryDirectory() as tmpdir:
            tracker = ExecutionTracker(tmpdir, "test-profile")
            config = {"namespace": "test", "apps": []}
            
            state = tracker.start_execution(config)
            
            assert state.profile == "test-profile"
            assert state.namespace == "test"
            assert len(state.steps) == 4  # prepare, build, template, deploy
            assert state.status == StepStatus.IN_PROGRESS
    
    def test_step_tracking(self):
        """단계 추적 테스트"""
        with tempfile.TemporaryDirectory() as tmpdir:
            tracker = ExecutionTracker(tmpdir)
            config = {"namespace": "test", "apps": []}
            
            state = tracker.start_execution(config)
            
            # 정상 단계 실행
            with tracker.track_step("prepare"):
                pass  # 단계 로직 시뮬레이션
            
            step = state.get_step("prepare")
            assert step.status == StepStatus.COMPLETED
            assert step.started_at is not None
            assert step.completed_at is not None
            assert step.duration is not None
    
    def test_step_failure_tracking(self):
        """단계 실패 추적 테스트"""
        with tempfile.TemporaryDirectory() as tmpdir:
            tracker = ExecutionTracker(tmpdir)
            config = {"namespace": "test", "apps": []}
            
            state = tracker.start_execution(config)
            
            # 실패 단계 실행
            try:
                with tracker.track_step("build"):
                    raise Exception("빌드 실패")
            except Exception:
                pass
            
            step = state.get_step("build")
            assert step.status == StepStatus.FAILED
            assert step.error == "빌드 실패"
            assert state.status == StepStatus.FAILED
            
            # 재시작 지점 확인
            restart_point = tracker.get_restart_point()
            assert restart_point == "build"
    
    def test_state_persistence(self):
        """상태 저장/로드 테스트"""
        with tempfile.TemporaryDirectory() as tmpdir:
            # 첫 번째 실행
            tracker1 = ExecutionTracker(tmpdir, "test")
            config = {"namespace": "test", "apps": []}
            
            state1 = tracker1.start_execution(config)
            run_id = state1.run_id
            
            with tracker1.track_step("prepare"):
                pass
            
            # 두 번째 실행 (같은 설정)
            tracker2 = ExecutionTracker(tmpdir, "test")
            state2 = tracker2.start_execution(config)
            
            # 같은 실행 상태가 복원되어야 함
            assert state2.run_id == run_id
            assert state2.get_step("prepare").status == StepStatus.COMPLETED
    
    def test_config_hash_changes(self):
        """설정 변경 시 새 실행 시작 테스트"""
        with tempfile.TemporaryDirectory() as tmpdir:
            tracker = ExecutionTracker(tmpdir, "test")
            
            # 첫 번째 설정
            config1 = {"namespace": "test1", "apps": []}
            state1 = tracker.start_execution(config1)
            run_id1 = state1.run_id
            
            # 다른 설정으로 실행
            config2 = {"namespace": "test2", "apps": []}
            state2 = tracker.start_execution(config2)
            run_id2 = state2.run_id
            
            # 다른 실행이어야 함
            assert run_id1 != run_id2
    
    def test_can_resume(self):
        """재시작 가능 여부 테스트"""
        with tempfile.TemporaryDirectory() as tmpdir:
            tracker = ExecutionTracker(tmpdir)
            config = {"namespace": "test", "apps": []}
            
            state = tracker.start_execution(config)
            
            # 아직 단계 실행 전이므로 재시작 불가
            assert not tracker.can_resume()
            
            # 한 단계 완료 후 재시작 가능
            with tracker.track_step("prepare"):
                pass
            
            assert tracker.can_resume()
    
    def test_execution_summary(self):
        """실행 요약 정보 테스트"""
        with tempfile.TemporaryDirectory() as tmpdir:
            tracker = ExecutionTracker(tmpdir, "test-profile")
            config = {"namespace": "test", "apps": []}
            
            state = tracker.start_execution(config)
            
            # 한 단계 완료
            with tracker.track_step("prepare"):
                pass
            
            summary = tracker.get_execution_summary()
            
            assert summary['profile'] == "test-profile"
            assert summary['status'] == StepStatus.IN_PROGRESS.value
            assert summary['progress'] == "1/4"
            assert summary['completed_steps'] == 1
            assert summary['failed_steps'] == 0
            assert summary['can_resume'] is True
    
    def test_complete_execution(self):
        """전체 실행 완료 테스트"""
        with tempfile.TemporaryDirectory() as tmpdir:
            tracker = ExecutionTracker(tmpdir)
            config = {"namespace": "test", "apps": []}
            
            state = tracker.start_execution(config)
            
            # 모든 단계 완료
            for step_name in ["prepare", "build", "template", "deploy"]:
                with tracker.track_step(step_name):
                    pass
            
            tracker.complete_execution()
            
            assert state.status == StepStatus.COMPLETED
            assert state.completed_at is not None
    
    def test_execution_history(self):
        """실행 히스토리 테스트"""
        with tempfile.TemporaryDirectory() as tmpdir:
            tracker = ExecutionTracker(tmpdir)
            
            # 여러 실행 생성
            for i in range(3):
                config = {"namespace": f"test{i}", "apps": []}
                state = tracker.start_execution(config, force_new=True)
                tracker.complete_execution()
            
            # 히스토리 조회
            history = tracker.load_execution_history(limit=2)
            
            assert len(history) == 2
            assert all('run_id' in entry for entry in history)
            assert all('status' in entry for entry in history)
    
    def test_cleanup_old_states(self):
        """오래된 상태 파일 정리 테스트"""
        with tempfile.TemporaryDirectory() as tmpdir:
            tracker = ExecutionTracker(tmpdir)
            
            # 테스트용 상태 파일 생성
            state_dir = Path(tmpdir) / ".sbkube" / "runs"
            state_dir.mkdir(parents=True, exist_ok=True)
            
            test_file = state_dir / "test-old-state.json"
            test_file.write_text(json.dumps({"test": "data"}))
            
            # 파일 수정 시간을 오래전으로 설정
            import time
            old_time = time.time() - (31 * 24 * 60 * 60)  # 31일 전
            test_file.touch(times=(old_time, old_time))
            
            # 정리 실행
            tracker.cleanup_old_states(keep_days=30)
            
            # 파일이 삭제되었는지 확인
            assert not test_file.exists()
    
    def test_get_next_step(self):
        """다음 단계 결정 테스트"""
        with tempfile.TemporaryDirectory() as tmpdir:
            tracker = ExecutionTracker(tmpdir)
            config = {"namespace": "test", "apps": []}
            
            state = tracker.start_execution(config)
            
            # 첫 번째 단계가 다음 단계여야 함
            next_step = tracker.get_restart_point()
            assert next_step == "prepare"
            
            # prepare 완료 후 build가 다음 단계
            with tracker.track_step("prepare"):
                pass
            
            next_step = tracker.get_restart_point()
            assert next_step == "build"
    
    def test_skip_step(self):
        """단계 건너뛰기 테스트"""
        with tempfile.TemporaryDirectory() as tmpdir:
            tracker = ExecutionTracker(tmpdir)
            config = {"namespace": "test", "apps": []}
            
            state = tracker.start_execution(config)
            
            # 단계 건너뛰기
            step = state.get_step("build")
            step.skip("사용자 요청")
            
            assert step.status == StepStatus.SKIPPED
            assert step.metadata['skip_reason'] == "사용자 요청"