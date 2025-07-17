import pytest
import json
import tempfile
import shutil
from pathlib import Path
from datetime import datetime
from unittest.mock import Mock, patch, MagicMock

from sbkube.utils.auto_fix_system import (
    AutoFix, AutoFixEngine, FixAttempt, FixResult
)
from sbkube.utils.diagnostic_system import DiagnosticResult, DiagnosticLevel


class MockAutoFix(AutoFix):
    """테스트용 Mock AutoFix"""
    
    def __init__(self, fix_id="test_fix", description="Test Fix", risk_level="low"):
        super().__init__(fix_id, description, risk_level)
        self.can_fix_result = True
        self.create_backup_result = None
        self.apply_fix_result = True
        self.rollback_result = True
        self.validate_fix_result = True
    
    def can_fix(self, diagnostic_result):
        return self.can_fix_result
    
    def create_backup(self):
        return self.create_backup_result
    
    def apply_fix(self, diagnostic_result):
        return self.apply_fix_result
    
    def rollback(self, backup_path):
        return self.rollback_result
    
    def validate_fix(self, diagnostic_result):
        return self.validate_fix_result


@pytest.fixture
def temp_dir():
    """임시 디렉토리 생성"""
    temp_path = tempfile.mkdtemp()
    yield temp_path
    shutil.rmtree(temp_path)


@pytest.fixture
def mock_console():
    """Mock console"""
    return Mock()


@pytest.fixture
def sample_diagnostic_result():
    """샘플 진단 결과"""
    return DiagnosticResult(
        check_name="test_check",
        level=DiagnosticLevel.ERROR,
        message="Test error message",
        is_fixable=True,
        fix_command="test fix command"
    )


@pytest.fixture
def fix_engine(temp_dir, mock_console):
    """AutoFixEngine 인스턴스"""
    return AutoFixEngine(base_dir=temp_dir, console=mock_console)


class TestFixAttempt:
    """FixAttempt 테스트"""
    
    def test_to_dict(self):
        """딕셔너리 변환 테스트"""
        attempt = FixAttempt(
            fix_id="test_fix",
            description="Test fix",
            command="test command",
            result=FixResult.SUCCESS
        )
        
        data = attempt.to_dict()
        
        assert data['fix_id'] == "test_fix"
        assert data['description'] == "Test fix"
        assert data['command'] == "test command"
        assert data['result'] == "success"
        assert 'timestamp' in data
        assert 'execution_time' in data
    
    def test_from_dict(self):
        """딕셔너리에서 생성 테스트"""
        data = {
            'fix_id': 'test_fix',
            'description': 'Test fix',
            'command': 'test command',
            'result': 'success',
            'timestamp': '2024-01-01T12:00:00',
            'backup_path': '/test/backup',
            'error_message': None,
            'execution_time': 1.5
        }
        
        attempt = FixAttempt.from_dict(data)
        
        assert attempt.fix_id == "test_fix"
        assert attempt.description == "Test fix"
        assert attempt.command == "test command"
        assert attempt.result == FixResult.SUCCESS
        assert attempt.backup_path == "/test/backup"
        assert attempt.execution_time == 1.5


class TestAutoFixEngine:
    """AutoFixEngine 테스트"""
    
    def test_init(self, temp_dir, mock_console):
        """초기화 테스트"""
        engine = AutoFixEngine(base_dir=temp_dir, console=mock_console)
        
        assert engine.base_dir == Path(temp_dir)
        assert engine.console == mock_console
        assert len(engine.fixes) == 0
        assert len(engine.fix_history) == 0
        
        # 디렉토리 생성 확인
        assert engine.backup_dir.exists()
        assert engine.history_dir.exists()
    
    def test_register_fix(self, fix_engine):
        """자동 수정 등록 테스트"""
        mock_fix = MockAutoFix()
        
        fix_engine.register_fix(mock_fix)
        
        assert len(fix_engine.fixes) == 1
        assert fix_engine.fixes[0] == mock_fix
    
    def test_find_applicable_fixes(self, fix_engine, sample_diagnostic_result):
        """적용 가능한 수정 찾기 테스트"""
        # 수정 가능한 fix
        applicable_fix = MockAutoFix("applicable_fix")
        applicable_fix.can_fix_result = True
        
        # 수정 불가능한 fix
        non_applicable_fix = MockAutoFix("non_applicable_fix")
        non_applicable_fix.can_fix_result = False
        
        fix_engine.register_fix(applicable_fix)
        fix_engine.register_fix(non_applicable_fix)
        
        # 수정 불가능한 결과
        non_fixable_result = DiagnosticResult(
            check_name="non_fixable",
            level=DiagnosticLevel.WARNING,
            message="Non fixable",
            is_fixable=False
        )
        
        results = [sample_diagnostic_result, non_fixable_result]
        applicable = fix_engine.find_applicable_fixes(results)
        
        assert len(applicable) == 1
        assert applicable[0][0] == applicable_fix
        assert applicable[0][1] == sample_diagnostic_result
    
    def test_apply_fixes_success(self, fix_engine, sample_diagnostic_result):
        """성공적인 수정 적용 테스트"""
        mock_fix = MockAutoFix()
        mock_fix.create_backup_result = "/test/backup"
        mock_fix.apply_fix_result = True
        mock_fix.validate_fix_result = True
        
        fix_engine.register_fix(mock_fix)
        
        with patch('sbkube.utils.auto_fix_system.Path.exists', return_value=True):
            attempts = fix_engine.apply_fixes([sample_diagnostic_result], interactive=False)
        
        assert len(attempts) == 1
        assert attempts[0].result == FixResult.SUCCESS
        assert attempts[0].fix_id == mock_fix.fix_id
        assert len(fix_engine.fix_history) == 1
    
    def test_apply_fixes_backup_failed(self, fix_engine, sample_diagnostic_result):
        """백업 실패 테스트"""
        mock_fix = MockAutoFix()
        mock_fix.create_backup_result = "/nonexistent/backup"
        
        fix_engine.register_fix(mock_fix)
        
        with patch('sbkube.utils.auto_fix_system.Path.exists', return_value=False):
            attempts = fix_engine.apply_fixes([sample_diagnostic_result], interactive=False)
        
        assert len(attempts) == 1
        assert attempts[0].result == FixResult.BACKUP_FAILED
    
    def test_apply_fixes_validation_failed(self, fix_engine, sample_diagnostic_result):
        """검증 실패 테스트"""
        mock_fix = MockAutoFix()
        mock_fix.apply_fix_result = True
        mock_fix.validate_fix_result = False
        
        fix_engine.register_fix(mock_fix)
        
        attempts = fix_engine.apply_fixes([sample_diagnostic_result], interactive=False)
        
        assert len(attempts) == 1
        assert attempts[0].result == FixResult.FAILED
        assert "검증 실패" in attempts[0].error_message
    
    def test_apply_fixes_exception(self, fix_engine, sample_diagnostic_result):
        """예외 발생 테스트"""
        mock_fix = MockAutoFix()
        
        def raise_exception(*args):
            raise Exception("Test exception")
        
        mock_fix.apply_fix = raise_exception
        fix_engine.register_fix(mock_fix)
        
        attempts = fix_engine.apply_fixes([sample_diagnostic_result], interactive=False)
        
        assert len(attempts) == 1
        assert attempts[0].result == FixResult.FAILED
        assert "Test exception" in attempts[0].error_message
    
    def test_rollback_last_fixes(self, fix_engine):
        """최근 수정 롤백 테스트"""
        # 성공한 수정 추가
        successful_attempt = FixAttempt(
            fix_id="test_fix",
            description="Test fix",
            command="test command",
            result=FixResult.SUCCESS,
            backup_path="/test/backup"
        )
        fix_engine.fix_history.append(successful_attempt)
        
        # 해당 fix 등록
        mock_fix = MockAutoFix("test_fix")
        mock_fix.rollback_result = True
        fix_engine.register_fix(mock_fix)
        
        result = fix_engine.rollback_last_fixes(1)
        
        assert result is True
    
    def test_rollback_no_candidates(self, fix_engine):
        """롤백 대상 없음 테스트"""
        result = fix_engine.rollback_last_fixes(1)
        assert result is False
    
    def test_save_and_load_history(self, fix_engine, temp_dir):
        """히스토리 저장/로드 테스트"""
        # 히스토리 추가
        attempt = FixAttempt(
            fix_id="test_fix",
            description="Test fix",
            command="test command",
            result=FixResult.SUCCESS
        )
        fix_engine.fix_history.append(attempt)
        
        # 저장
        fix_engine._save_fix_history()
        
        # 새 엔진으로 로드
        new_engine = AutoFixEngine(base_dir=temp_dir)
        
        assert len(new_engine.fix_history) == 1
        assert new_engine.fix_history[0].fix_id == "test_fix"
        assert new_engine.fix_history[0].result == FixResult.SUCCESS
    
    def test_cleanup_old_backups(self, fix_engine):
        """오래된 백업 정리 테스트"""
        # 테스트 백업 파일 생성
        backup_dir = fix_engine.backup_dir
        old_backup = backup_dir / "old_backup.txt"
        recent_backup = backup_dir / "recent_backup.txt"
        
        old_backup.write_text("old")
        recent_backup.write_text("recent")
        
        # 파일 수정 시간 조작
        old_time = datetime.now().timestamp() - (10 * 24 * 3600)  # 10일 전
        import os
        os.utime(old_backup, (old_time, old_time))
        
        fix_engine.cleanup_old_backups(keep_days=7)
        
        assert not old_backup.exists()
        assert recent_backup.exists()
    
    def test_get_history_summary(self, fix_engine):
        """히스토리 요약 테스트"""
        # 다양한 결과의 히스토리 추가
        attempts = [
            FixAttempt("fix1", "Fix 1", "cmd1", FixResult.SUCCESS),
            FixAttempt("fix2", "Fix 2", "cmd2", FixResult.FAILED),
            FixAttempt("fix3", "Fix 3", "cmd3", FixResult.SUCCESS),
            FixAttempt("fix4", "Fix 4", "cmd4", FixResult.SKIPPED)
        ]
        
        fix_engine.fix_history.extend(attempts)
        
        summary = fix_engine.get_history_summary()
        
        assert summary['total_attempts'] == 4
        assert summary['success_count'] == 2
        assert summary['failed_count'] == 1
        assert summary['skipped_count'] == 1
        assert summary['backup_failed_count'] == 0
        assert len(summary['recent_attempts']) == 4
    
    def test_get_rollback_candidates(self, fix_engine):
        """롤백 후보 테스트"""
        # 롤백 가능한 수정들 추가
        candidates = [
            FixAttempt("fix1", "Fix 1", "cmd1", FixResult.SUCCESS, backup_path="/backup1"),
            FixAttempt("fix2", "Fix 2", "cmd2", FixResult.FAILED),  # 실패한 것은 제외
            FixAttempt("fix3", "Fix 3", "cmd3", FixResult.SUCCESS, backup_path="/backup3"),
            FixAttempt("fix4", "Fix 4", "cmd4", FixResult.SUCCESS)  # 백업 없는 것은 제외
        ]
        
        fix_engine.fix_history.extend(candidates)
        
        rollback_candidates = fix_engine.get_rollback_candidates(limit=2)
        
        assert len(rollback_candidates) == 2
        assert rollback_candidates[0].fix_id == "fix3"  # 최근 것부터
        assert rollback_candidates[1].fix_id == "fix1"
        assert all(c.result == FixResult.SUCCESS for c in rollback_candidates)
        assert all(c.backup_path for c in rollback_candidates)


class TestMockAutoFix:
    """MockAutoFix 기본 동작 테스트"""
    
    def test_mock_auto_fix_basic(self, sample_diagnostic_result):
        """MockAutoFix 기본 동작 테스트"""
        fix = MockAutoFix()
        
        assert fix.can_fix(sample_diagnostic_result) is True
        assert fix.create_backup() is None
        assert fix.apply_fix(sample_diagnostic_result) is True
        assert fix.rollback("/test/backup") is True
        assert fix.validate_fix(sample_diagnostic_result) is True
    
    def test_mock_auto_fix_customized(self, sample_diagnostic_result):
        """MockAutoFix 커스터마이징 테스트"""
        fix = MockAutoFix(fix_id="custom_fix", description="Custom Fix", risk_level="high")
        fix.can_fix_result = False
        fix.apply_fix_result = False
        
        assert fix.fix_id == "custom_fix"
        assert fix.description == "Custom Fix"
        assert fix.risk_level == "high"
        assert fix.can_fix(sample_diagnostic_result) is False
        assert fix.apply_fix(sample_diagnostic_result) is False


@pytest.mark.integration
class TestAutoFixEngineIntegration:
    """AutoFixEngine 통합 테스트"""
    
    def test_complete_fix_workflow(self, temp_dir):
        """완전한 수정 워크플로우 테스트"""
        from rich.console import Console
        
        console = Console()
        engine = AutoFixEngine(base_dir=temp_dir, console=console)
        
        # Mock fix 등록
        mock_fix = MockAutoFix()
        mock_fix.create_backup_result = str(Path(temp_dir) / "backup.txt")
        
        # 백업 파일 생성
        Path(mock_fix.create_backup_result).write_text("backup content")
        
        engine.register_fix(mock_fix)
        
        # 진단 결과
        diagnostic_result = DiagnosticResult(
            check_name="integration_test",
            level=DiagnosticLevel.ERROR,
            message="Integration test error",
            is_fixable=True,
            fix_command="integration fix"
        )
        
        # 수정 적용
        attempts = engine.apply_fixes([diagnostic_result], interactive=False)
        
        # 검증
        assert len(attempts) == 1
        assert attempts[0].result == FixResult.SUCCESS
        assert len(engine.fix_history) == 1
        
        # 히스토리 요약 확인
        summary = engine.get_history_summary()
        assert summary['total_attempts'] == 1
        assert summary['success_count'] == 1
        
        # 롤백 테스트
        rollback_result = engine.rollback_last_fixes(1)
        assert rollback_result is True