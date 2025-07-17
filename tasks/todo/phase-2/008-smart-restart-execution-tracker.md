---
phase: 2
order: 8
source_plan: /tasks/plan/phase2-advanced-features.md
priority: high
tags: [smart-restart, execution-tracker, state-management]
estimated_days: 3
depends_on: [007-profile-loader-implementation]
---

# 📌 작업: 스마트 재시작 실행 상태 추적 시스템

## 🎯 목표
실행 단계별 상태를 추적하고 저장하여 실패 시 해당 지점부터 재시작할 수 있는 시스템을 구현합니다.

## 📋 작업 내용

### 1. 실행 상태 모델 정의
```python
# sbkube/models/execution_state.py
from dataclasses import dataclass, field
from typing import Dict, Any, Optional, List
from datetime import datetime
from enum import Enum
import uuid
import json

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
    started_at: Optional[datetime] = None
    completed_at: Optional[datetime] = None
    duration: Optional[float] = None
    error: Optional[str] = None
    output: Optional[str] = None
    metadata: Dict[str, Any] = field(default_factory=dict)
    
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
        self.metadata['skip_reason'] = reason
    
    def to_dict(self) -> Dict[str, Any]:
        """딕셔너리로 변환"""
        return {
            'name': self.name,
            'status': self.status.value,
            'started_at': self.started_at.isoformat() if self.started_at else None,
            'completed_at': self.completed_at.isoformat() if self.completed_at else None,
            'duration': self.duration,
            'error': self.error,
            'output': self.output,
            'metadata': self.metadata
        }
    
    @classmethod
    def from_dict(cls, data: Dict[str, Any]) -> 'StepExecution':
        """딕셔너리에서 생성"""
        step = cls(name=data['name'])
        step.status = StepStatus(data['status'])
        step.started_at = datetime.fromisoformat(data['started_at']) if data['started_at'] else None
        step.completed_at = datetime.fromisoformat(data['completed_at']) if data['completed_at'] else None
        step.duration = data.get('duration')
        step.error = data.get('error')
        step.output = data.get('output')
        step.metadata = data.get('metadata', {})
        return step

@dataclass
class ExecutionState:
    """전체 실행 상태"""
    run_id: str = field(default_factory=lambda: str(uuid.uuid4()))
    profile: Optional[str] = None
    namespace: Optional[str] = None
    started_at: datetime = field(default_factory=datetime.utcnow)
    completed_at: Optional[datetime] = None
    status: StepStatus = StepStatus.IN_PROGRESS
    steps: Dict[str, StepExecution] = field(default_factory=dict)
    config_hash: Optional[str] = None
    metadata: Dict[str, Any] = field(default_factory=dict)
    
    def add_step(self, step_name: str) -> StepExecution:
        """단계 추가"""
        step = StepExecution(name=step_name)
        self.steps[step_name] = step
        return step
    
    def get_step(self, step_name: str) -> Optional[StepExecution]:
        """단계 조회"""
        return self.steps.get(step_name)
    
    def get_failed_step(self) -> Optional[StepExecution]:
        """실패한 단계 조회"""
        for step in self.steps.values():
            if step.status == StepStatus.FAILED:
                return step
        return None
    
    def get_last_completed_step(self) -> Optional[str]:
        """마지막 완료된 단계명 반환"""
        completed_steps = [
            step.name for step in self.steps.values()
            if step.status == StepStatus.COMPLETED
        ]
        return completed_steps[-1] if completed_steps else None
    
    def get_next_step(self, step_order: List[str]) -> Optional[str]:
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
    
    def to_dict(self) -> Dict[str, Any]:
        """딕셔너리로 변환"""
        return {
            'run_id': self.run_id,
            'profile': self.profile,
            'namespace': self.namespace,
            'started_at': self.started_at.isoformat(),
            'completed_at': self.completed_at.isoformat() if self.completed_at else None,
            'status': self.status.value,
            'steps': {name: step.to_dict() for name, step in self.steps.items()},
            'config_hash': self.config_hash,
            'metadata': self.metadata
        }
    
    @classmethod
    def from_dict(cls, data: Dict[str, Any]) -> 'ExecutionState':
        """딕셔너리에서 생성"""
        state = cls()
        state.run_id = data['run_id']
        state.profile = data.get('profile')
        state.namespace = data.get('namespace')
        state.started_at = datetime.fromisoformat(data['started_at'])
        state.completed_at = datetime.fromisoformat(data['completed_at']) if data['completed_at'] else None
        state.status = StepStatus(data['status'])
        state.config_hash = data.get('config_hash')
        state.metadata = data.get('metadata', {})
        
        # 단계 복원
        for step_name, step_data in data.get('steps', {}).items():
            state.steps[step_name] = StepExecution.from_dict(step_data)
        
        return state
```

### 2. 실행 추적기 구현
```python
# sbkube/utils/execution_tracker.py
import os
import json
import hashlib
from pathlib import Path
from typing import Dict, Any, Optional, List, Callable
from contextlib import contextmanager

from sbkube.models.execution_state import ExecutionState, StepExecution, StepStatus
from sbkube.utils.logger import logger

class ExecutionTracker:
    """실행 상태 추적기"""
    
    def __init__(self, base_dir: str, profile: str = None):
        self.base_dir = Path(base_dir)
        self.profile = profile
        self.state_dir = self.base_dir / ".sbkube" / "runs"
        self.state_dir.mkdir(parents=True, exist_ok=True)
        
        self.current_state: Optional[ExecutionState] = None
        self.step_order = ["prepare", "build", "template", "deploy"]
    
    def start_execution(self, config: Dict[str, Any], force_new: bool = False) -> ExecutionState:
        """새 실행 시작 또는 기존 실행 복원"""
        config_hash = self._compute_config_hash(config)
        
        if not force_new:
            # 기존 실행 상태 확인
            existing_state = self._load_latest_state()
            if (existing_state and 
                existing_state.config_hash == config_hash and
                existing_state.status == StepStatus.IN_PROGRESS and
                existing_state.profile == self.profile):
                
                logger.info(f"🔄 기존 실행 상태 복원 (Run ID: {existing_state.run_id[:8]})")
                self.current_state = existing_state
                return existing_state
        
        # 새 실행 상태 생성
        self.current_state = ExecutionState(
            profile=self.profile,
            namespace=config.get('namespace'),
            config_hash=config_hash
        )
        
        # 단계 초기화
        for step_name in self.step_order:
            self.current_state.add_step(step_name)
        
        self._save_state()
        logger.info(f"🚀 새 실행 시작 (Run ID: {self.current_state.run_id[:8]})")
        return self.current_state
    
    @contextmanager
    def track_step(self, step_name: str):
        """단계 실행 추적 컨텍스트"""
        if not self.current_state:
            raise RuntimeError("실행 상태가 초기화되지 않았습니다")
        
        step = self.current_state.get_step(step_name)
        if not step:
            step = self.current_state.add_step(step_name)
        
        step.start()
        self._save_state()
        logger.info(f"🔄 {step_name} 단계 시작...")
        
        try:
            yield step
            step.complete()
            logger.success(f"✅ {step_name} 단계 완료")
            
        except Exception as e:
            step.fail(str(e))
            self.current_state.fail()
            logger.error(f"❌ {step_name} 단계 실패: {e}")
            raise
        
        finally:
            self._save_state()
    
    def complete_execution(self):
        """실행 완료 처리"""
        if self.current_state:
            self.current_state.complete()
            self._save_state()
            logger.success("🎉 전체 실행 완료!")
    
    def get_restart_point(self) -> Optional[str]:
        """재시작 지점 결정"""
        if not self.current_state:
            return None
        
        # 실패한 단계가 있으면 해당 단계부터
        failed_step = self.current_state.get_failed_step()
        if failed_step:
            return failed_step.name
        
        # 다음 실행할 단계 반환
        return self.current_state.get_next_step(self.step_order)
    
    def can_resume(self) -> bool:
        """재시작 가능 여부 확인"""
        if not self.current_state:
            return False
        
        return (self.current_state.status == StepStatus.IN_PROGRESS and
                any(step.status == StepStatus.COMPLETED for step in self.current_state.steps.values()))
    
    def get_execution_summary(self) -> Dict[str, Any]:
        """실행 요약 정보 반환"""
        if not self.current_state:
            return {}
        
        total_steps = len(self.current_state.steps)
        completed_steps = sum(1 for step in self.current_state.steps.values() 
                            if step.status == StepStatus.COMPLETED)
        failed_steps = sum(1 for step in self.current_state.steps.values() 
                         if step.status == StepStatus.FAILED)
        
        total_duration = 0
        if self.current_state.started_at and self.current_state.completed_at:
            total_duration = (self.current_state.completed_at - self.current_state.started_at).total_seconds()
        
        return {
            'run_id': self.current_state.run_id,
            'profile': self.current_state.profile,
            'status': self.current_state.status.value,
            'progress': f"{completed_steps}/{total_steps}",
            'completed_steps': completed_steps,
            'failed_steps': failed_steps,
            'total_duration': total_duration,
            'can_resume': self.can_resume(),
            'restart_point': self.get_restart_point()
        }
    
    def _compute_config_hash(self, config: Dict[str, Any]) -> str:
        """설정 해시 계산"""
        # 실행에 영향을 주는 주요 설정만 해시 계산
        relevant_config = {
            'namespace': config.get('namespace'),
            'apps': config.get('apps', []),
            'profile': self.profile
        }
        
        config_str = json.dumps(relevant_config, sort_keys=True, ensure_ascii=False)
        return hashlib.md5(config_str.encode()).hexdigest()
    
    def _save_state(self):
        """현재 상태 저장"""
        if not self.current_state:
            return
        
        state_file = self.state_dir / f"{self.current_state.run_id}.json"
        latest_file = self.state_dir / "latest.json"
        
        state_data = self.current_state.to_dict()
        
        # 개별 상태 파일 저장
        with open(state_file, 'w', encoding='utf-8') as f:
            json.dump(state_data, f, indent=2, ensure_ascii=False)
        
        # 최신 상태 링크 업데이트
        with open(latest_file, 'w', encoding='utf-8') as f:
            json.dump(state_data, f, indent=2, ensure_ascii=False)
    
    def _load_latest_state(self) -> Optional[ExecutionState]:
        """최신 상태 로드"""
        latest_file = self.state_dir / "latest.json"
        
        if not latest_file.exists():
            return None
        
        try:
            with open(latest_file, 'r', encoding='utf-8') as f:
                state_data = json.load(f)
            
            return ExecutionState.from_dict(state_data)
            
        except Exception as e:
            logger.warning(f"상태 파일 로드 실패: {e}")
            return None
    
    def load_execution_history(self, limit: int = 10) -> List[Dict[str, Any]]:
        """실행 히스토리 로드"""
        history = []
        
        for state_file in sorted(self.state_dir.glob("*.json"), reverse=True):
            if state_file.name == "latest.json":
                continue
            
            try:
                with open(state_file, 'r', encoding='utf-8') as f:
                    state_data = json.load(f)
                
                history.append({
                    'run_id': state_data['run_id'],
                    'profile': state_data.get('profile'),
                    'status': state_data['status'],
                    'started_at': state_data['started_at'],
                    'completed_at': state_data.get('completed_at'),
                    'file': str(state_file)
                })
                
                if len(history) >= limit:
                    break
                    
            except Exception as e:
                logger.warning(f"히스토리 파일 로드 실패 ({state_file}): {e}")
        
        return history
    
    def cleanup_old_states(self, keep_days: int = 30):
        """오래된 상태 파일 정리"""
        import time
        from datetime import datetime, timedelta
        
        cutoff_time = datetime.now() - timedelta(days=keep_days)
        cutoff_timestamp = cutoff_time.timestamp()
        
        cleaned_count = 0
        for state_file in self.state_dir.glob("*.json"):
            if state_file.name == "latest.json":
                continue
            
            if state_file.stat().st_mtime < cutoff_timestamp:
                try:
                    state_file.unlink()
                    cleaned_count += 1
                except Exception as e:
                    logger.warning(f"상태 파일 삭제 실패 ({state_file}): {e}")
        
        if cleaned_count > 0:
            logger.info(f"🧹 {cleaned_count}개의 오래된 상태 파일을 정리했습니다")
```

### 3. RunCommand 클래스 수정 (상태 추적 통합)
```python
# sbkube/commands/run.py 수정
from sbkube.utils.execution_tracker import ExecutionTracker

class RunCommand(BaseCommand):
    def __init__(self, base_dir: str, profile: str = None, 
                 only: str = None, skip: str = None, 
                 continue_from: str = None, retry_failed: bool = False,
                 resume: bool = False):
        super().__init__(base_dir, profile)
        self.only = only
        self.skip = skip
        self.continue_from = continue_from
        self.retry_failed = retry_failed
        self.resume = resume
        self.tracker = ExecutionTracker(base_dir, profile)
    
    def execute(self):
        """실행 (상태 추적 포함)"""
        config = self.load_config()
        
        # 실행 상태 초기화
        force_new = not (self.resume or self.retry_failed or self.continue_from)
        execution_state = self.tracker.start_execution(config, force_new)
        
        # 시작 지점 결정
        start_step = self._determine_start_step(execution_state)
        
        # 단계별 실행
        steps = ["prepare", "build", "template", "deploy"]
        
        if self.only:
            steps = [self.only]
            start_step = self.only
        elif start_step:
            # 시작 지점부터 실행
            start_index = steps.index(start_step) if start_step in steps else 0
            steps = steps[start_index:]
        
        try:
            for step in steps:
                if self.skip and step == self.skip:
                    step_obj = execution_state.get_step(step)
                    if step_obj:
                        step_obj.skip(f"사용자 요청으로 건너뜀")
                    continue
                
                with self.tracker.track_step(step):
                    self._execute_step(step, config)
            
            self.tracker.complete_execution()
            
        except Exception as e:
            logger.error(f"실행 실패: {e}")
            self._show_restart_options()
            raise
    
    def _determine_start_step(self, execution_state) -> Optional[str]:
        """시작 단계 결정"""
        if self.continue_from:
            return self.continue_from
        
        if self.retry_failed:
            restart_point = self.tracker.get_restart_point()
            if restart_point:
                logger.info(f"🔄 실패한 단계부터 재시작: {restart_point}")
                return restart_point
        
        if self.resume:
            if self.tracker.can_resume():
                restart_point = self.tracker.get_restart_point()
                if restart_point:
                    logger.info(f"🔄 중단된 지점부터 재시작: {restart_point}")
                    return restart_point
            else:
                logger.info("재시작할 수 있는 실행이 없습니다. 새로 시작합니다.")
        
        return None
    
    def _show_restart_options(self):
        """재시작 옵션 안내"""
        if self.tracker.can_resume():
            restart_point = self.tracker.get_restart_point()
            logger.info(f"\n💡 재시작 옵션:")
            logger.info(f"   sbkube run --retry-failed  # 실패한 단계부터 재시작")
            logger.info(f"   sbkube run --continue-from {restart_point}  # {restart_point} 단계부터 재시작")
            logger.info(f"   sbkube run --resume  # 자동으로 재시작 지점 탐지")
```

## 🧪 테스트 구현

### 단위 테스트
```python
# tests/unit/utils/test_execution_tracker.py
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
```

## ✅ 완료 기준

- [ ] ExecutionState 및 StepExecution 모델 구현
- [ ] ExecutionTracker 클래스 구현
- [ ] 상태 저장/로드 기능 구현
- [ ] RunCommand에 상태 추적 통합
- [ ] 재시작 옵션 (--continue-from, --retry-failed, --resume) 구현
- [ ] 실행 히스토리 관리 기능
- [ ] 단위 테스트 작성 및 통과

## 🔍 검증 명령어

```bash
# 정상 실행
sbkube run

# 실행 중단 후 재시작 테스트
sbkube run --only prepare
sbkube run --resume

# 실패 후 재시작 테스트
# (build 단계에서 의도적으로 실패시킨 후)
sbkube run --retry-failed
sbkube run --continue-from template

# 상태 확인
ls -la .sbkube/runs/
cat .sbkube/runs/latest.json

# 테스트 실행
pytest tests/unit/utils/test_execution_tracker.py -v
```

## 📝 예상 결과

```bash
$ sbkube run
🚀 새 실행 시작 (Run ID: a1b2c3d4)
🔄 prepare 단계 시작...
✅ prepare 단계 완료
🔄 build 단계 시작...
❌ build 단계 실패: Helm chart not found

💡 재시작 옵션:
   sbkube run --retry-failed  # 실패한 단계부터 재시작
   sbkube run --continue-from build  # build 단계부터 재시작
   sbkube run --resume  # 자동으로 재시작 지점 탐지

$ sbkube run --retry-failed
🔄 기존 실행 상태 복원 (Run ID: a1b2c3d4)
🔄 실패한 단계부터 재시작: build
🔄 build 단계 시작...
✅ build 단계 완료
🔄 template 단계 시작...
✅ template 단계 완료
🔄 deploy 단계 시작...
✅ deploy 단계 완료
🎉 전체 실행 완료!
```

## 🔄 다음 단계

이 작업 완료 후 다음 작업으로 진행:
- `009-smart-restart-history-management.md` - 실행 히스토리 관리 시스템 구현