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
            logger.info(f"✅ {step_name} 단계 완료")
            
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
            logger.info("🎉 전체 실행 완료!")
    
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