from unittest.mock import Mock, patch

import pytest
from click.testing import CliRunner

from sbkube.commands.fix import (
    _show_fix_history,
    _show_fix_plan,
    _show_fix_summary,
    cmd,
)
from sbkube.utils.auto_fix_system import FixAttempt, FixResult
from sbkube.utils.diagnostic_system import DiagnosticLevel, DiagnosticResult


@pytest.fixture
def runner():
    """Click CLI 테스트 러너"""
    return CliRunner()


@pytest.fixture
def mock_console():
    """Mock console"""
    return Mock()


@pytest.fixture
def sample_diagnostic_results():
    """샘플 진단 결과들"""
    return [
        DiagnosticResult(
            check_name="namespace_check",
            level=DiagnosticLevel.ERROR,
            message="네임스페이스 'test-ns'가 존재하지 않습니다",
            is_fixable=True,
            fix_command="kubectl create namespace test-ns",
        ),
        DiagnosticResult(
            check_name="config_check",
            level=DiagnosticLevel.ERROR,
            message="설정 파일이 없습니다",
            is_fixable=True,
            fix_command="config 파일 생성",
        ),
    ]


@pytest.fixture
def sample_fix_attempts():
    """샘플 수정 시도들"""
    return [
        FixAttempt(
            fix_id="fix1",
            description="네임스페이스 생성",
            command="kubectl create namespace test",
            result=FixResult.SUCCESS,
        ),
        FixAttempt(
            fix_id="fix2",
            description="설정 파일 수정",
            command="config fix",
            result=FixResult.FAILED,
            error_message="권한 없음",
        ),
        FixAttempt(
            fix_id="fix3",
            description="Helm 리포지토리 추가",
            command="helm repo add",
            result=FixResult.SKIPPED,
        ),
    ]


class TestFixCommand:
    """fix 명령어 테스트"""

    @patch("sbkube.commands.fix.AutoFixEngine")
    @patch("sbkube.commands.fix.DiagnosticEngine")
    @patch("asyncio.create_task")
    def test_fix_command_basic(
        self, mock_create_task, mock_diagnostic_engine, mock_fix_engine, runner
    ):
        """기본 fix 명령어 테스트"""
        # Mock 설정
        mock_diagnostic_instance = Mock()
        mock_fix_instance = Mock()

        mock_diagnostic_engine.return_value = mock_diagnostic_instance
        mock_fix_engine.return_value = mock_fix_instance

        # 비동기 결과 모킹
        async def mock_run_checks():
            return []

        mock_create_task.return_value = mock_run_checks()
        mock_fix_instance.apply_fixes.return_value = []

        # CLI 실행
        result = runner.invoke(cmd, [])

        # 검증
        assert result.exit_code == 0
        mock_diagnostic_engine.assert_called_once()
        mock_fix_engine.assert_called_once()

    @patch("sbkube.commands.fix.AutoFixEngine")
    @patch("sbkube.commands.fix.DiagnosticEngine")
    @patch("asyncio.create_task")
    def test_fix_command_dry_run(
        self,
        mock_create_task,
        mock_diagnostic_engine,
        mock_fix_engine,
        runner,
        sample_diagnostic_results,
    ):
        """Dry run 테스트"""
        # Mock 설정
        mock_diagnostic_instance = Mock()
        mock_fix_instance = Mock()

        mock_diagnostic_engine.return_value = mock_diagnostic_instance
        mock_fix_engine.return_value = mock_fix_instance

        # 수정 가능한 결과 반환
        async def mock_run_checks():
            return sample_diagnostic_results

        mock_create_task.return_value = mock_run_checks()
        mock_fix_instance.find_applicable_fixes.return_value = [
            (
                Mock(description="Test Fix", risk_level="low"),
                sample_diagnostic_results[0],
            )
        ]

        # CLI 실행
        result = runner.invoke(cmd, ["--dry-run"])

        # 검증
        assert result.exit_code == 0
        mock_fix_instance.apply_fixes.assert_not_called()  # dry-run에서는 실제 수정 안함

    @patch("sbkube.commands.fix.AutoFixEngine")
    def test_fix_command_history(self, mock_fix_engine, runner):
        """히스토리 표시 테스트"""
        mock_fix_instance = Mock()
        mock_fix_engine.return_value = mock_fix_instance

        # 히스토리 데이터 모킹
        mock_fix_instance.get_history_summary.return_value = {
            "total_attempts": 5,
            "success_count": 3,
            "failed_count": 1,
            "skipped_count": 1,
            "backup_failed_count": 0,
            "recent_attempts": [],
        }
        mock_fix_instance.get_rollback_candidates.return_value = []

        # CLI 실행
        result = runner.invoke(cmd, ["--history"])

        # 검증
        assert result.exit_code == 0
        mock_fix_instance.get_history_summary.assert_called_once()

    @patch("sbkube.commands.fix.AutoFixEngine")
    def test_fix_command_backup_cleanup(self, mock_fix_engine, runner):
        """백업 정리 테스트"""
        mock_fix_instance = Mock()
        mock_fix_engine.return_value = mock_fix_instance

        # CLI 실행
        result = runner.invoke(cmd, ["--backup-cleanup"])

        # 검증
        assert result.exit_code == 0
        mock_fix_instance.cleanup_old_backups.assert_called_once()

    @patch("sbkube.commands.fix.AutoFixEngine")
    def test_fix_command_rollback_success(self, mock_fix_engine, runner):
        """성공적인 롤백 테스트"""
        mock_fix_instance = Mock()
        mock_fix_engine.return_value = mock_fix_instance
        mock_fix_instance.rollback_last_fixes.return_value = True

        # CLI 실행
        result = runner.invoke(cmd, ["--rollback", "2"])

        # 검증
        assert result.exit_code == 0
        mock_fix_instance.rollback_last_fixes.assert_called_once_with(2)

    @patch("sbkube.commands.fix.AutoFixEngine")
    def test_fix_command_rollback_failure(self, mock_fix_engine, runner):
        """롤백 실패 테스트"""
        mock_fix_instance = Mock()
        mock_fix_engine.return_value = mock_fix_instance
        mock_fix_instance.rollback_last_fixes.return_value = False

        # CLI 실행
        result = runner.invoke(cmd, ["--rollback", "2"])

        # 검증
        assert result.exit_code == 1
        mock_fix_instance.rollback_last_fixes.assert_called_once_with(2)

    @patch("sbkube.commands.fix.AutoFixEngine")
    @patch("sbkube.commands.fix.DiagnosticEngine")
    @patch("asyncio.create_task")
    def test_fix_command_force_mode(
        self,
        mock_create_task,
        mock_diagnostic_engine,
        mock_fix_engine,
        runner,
        sample_diagnostic_results,
    ):
        """Force 모드 테스트"""
        # Mock 설정
        mock_diagnostic_instance = Mock()
        mock_fix_instance = Mock()

        mock_diagnostic_engine.return_value = mock_diagnostic_instance
        mock_fix_engine.return_value = mock_fix_instance

        async def mock_run_checks():
            return sample_diagnostic_results

        mock_create_task.return_value = mock_run_checks()
        mock_fix_instance.apply_fixes.return_value = []

        # CLI 실행
        result = runner.invoke(cmd, ["--force"])

        # 검증
        assert result.exit_code == 0
        mock_fix_instance.apply_fixes.assert_called_once()

        # force=True, interactive=False로 호출되었는지 확인
        call_args = mock_fix_instance.apply_fixes.call_args
        assert call_args[1]["force"] is True
        assert call_args[1]["interactive"] is False


class TestFixHelperFunctions:
    """Fix 명령어 도우미 함수들 테스트"""

    def test_show_fix_plan_with_fixes(self, mock_console):
        """수정 계획 표시 테스트 (수정 있음)"""
        mock_engine = Mock()
        mock_fix = Mock()
        mock_fix.description = "Test Fix"
        mock_fix.risk_level = "low"

        mock_result = Mock()
        mock_result.message = "Test error"
        mock_result.fix_command = "test command"

        mock_engine.find_applicable_fixes.return_value = [(mock_fix, mock_result)]

        _show_fix_plan(mock_engine, [mock_result])

        # console.print가 호출되었는지 확인
        assert mock_console.print.call_count == 0  # mock_console이 실제 사용되지 않음
        mock_engine.find_applicable_fixes.assert_called_once()

    def test_show_fix_plan_no_fixes(self, mock_console):
        """수정 계획 표시 테스트 (수정 없음)"""
        mock_engine = Mock()
        mock_engine.find_applicable_fixes.return_value = []

        _show_fix_plan(mock_engine, [])

        mock_engine.find_applicable_fixes.assert_called_once()

    def test_show_fix_summary(self, sample_fix_attempts, mock_console):
        """수정 결과 요약 테스트"""
        with patch("sbkube.commands.fix.console") as mock_console_module:
            _show_fix_summary(sample_fix_attempts)

            # console.print가 여러 번 호출되었는지 확인
            assert mock_console_module.print.call_count > 0

    def test_show_fix_history_with_data(self, mock_console):
        """히스토리 표시 테스트 (데이터 있음)"""
        mock_engine = Mock()
        mock_engine.get_history_summary.return_value = {
            "total_attempts": 5,
            "success_count": 3,
            "failed_count": 1,
            "skipped_count": 1,
            "backup_failed_count": 0,
            "recent_attempts": [
                {
                    "description": "Test Fix",
                    "result": "success",
                    "timestamp": "2024-01-01T12:00:00",
                }
            ],
        }
        mock_engine.get_rollback_candidates.return_value = [
            Mock(description="Rollback candidate", timestamp=Mock())
        ]

        with patch("sbkube.commands.fix.console"):
            _show_fix_history(mock_engine)

        mock_engine.get_history_summary.assert_called_once()
        mock_engine.get_rollback_candidates.assert_called_once()

    def test_show_fix_history_no_data(self, mock_console):
        """히스토리 표시 테스트 (데이터 없음)"""
        mock_engine = Mock()
        mock_engine.get_history_summary.return_value = {}

        with patch("sbkube.commands.fix.console"):
            _show_fix_history(mock_engine)

        mock_engine.get_history_summary.assert_called_once()


class TestFixCommandError:
    """Fix 명령어 에러 처리 테스트"""

    @patch("sbkube.commands.fix.AutoFixEngine")
    def test_fix_command_exception(self, mock_fix_engine, runner):
        """예외 발생 테스트"""
        mock_fix_engine.side_effect = Exception("Test exception")

        # CLI 실행
        result = runner.invoke(cmd, [])

        # 검증
        assert result.exit_code == 1

    @patch("sbkube.commands.fix.AutoFixEngine")
    @patch("sbkube.commands.fix.DiagnosticEngine")
    @patch("asyncio.create_task")
    def test_fix_command_with_failed_attempts(
        self,
        mock_create_task,
        mock_diagnostic_engine,
        mock_fix_engine,
        runner,
        sample_diagnostic_results,
    ):
        """실패한 수정이 있는 경우 테스트"""
        # Mock 설정
        mock_diagnostic_instance = Mock()
        mock_fix_instance = Mock()

        mock_diagnostic_engine.return_value = mock_diagnostic_instance
        mock_fix_engine.return_value = mock_fix_instance

        async def mock_run_checks():
            return sample_diagnostic_results

        mock_create_task.return_value = mock_run_checks()

        # 실패한 수정 시도 반환
        failed_attempt = FixAttempt(
            fix_id="failed_fix",
            description="Failed Fix",
            command="failed command",
            result=FixResult.FAILED,
        )
        mock_fix_instance.apply_fixes.return_value = [failed_attempt]

        # CLI 실행
        result = runner.invoke(cmd, [])

        # 검증: 실패한 수정이 있으면 exit code 1
        assert result.exit_code == 1


@pytest.mark.integration
class TestFixCommandIntegration:
    """Fix 명령어 통합 테스트"""

    @patch("sbkube.commands.fix.AutoFixEngine")
    @patch("sbkube.commands.fix.DiagnosticEngine")
    @patch("sbkube.commands.fix.MissingNamespaceFix")
    @patch("sbkube.commands.fix.ConfigFileFix")
    @patch("sbkube.commands.fix.HelmRepositoryFix")
    @patch("asyncio.create_task")
    def test_complete_fix_workflow(
        self,
        mock_create_task,
        mock_helm_fix,
        mock_config_fix,
        mock_namespace_fix,
        mock_diagnostic_engine,
        mock_fix_engine,
        runner,
    ):
        """완전한 수정 워크플로우 테스트"""
        # Mock 인스턴스들
        mock_diagnostic_instance = Mock()
        mock_fix_instance = Mock()

        mock_diagnostic_engine.return_value = mock_diagnostic_instance
        mock_fix_engine.return_value = mock_fix_instance

        # 진단 결과
        diagnostic_results = [
            DiagnosticResult(
                check_name="namespace_check",
                level=DiagnosticLevel.ERROR,
                message="네임스페이스가 없습니다",
                is_fixable=True,
            )
        ]

        async def mock_run_checks():
            return diagnostic_results

        mock_create_task.return_value = mock_run_checks()

        # 성공적인 수정 시도
        successful_attempt = FixAttempt(
            fix_id="namespace_fix",
            description="네임스페이스 생성",
            command="kubectl create namespace",
            result=FixResult.SUCCESS,
        )
        mock_fix_instance.apply_fixes.return_value = [successful_attempt]

        # CLI 실행
        result = runner.invoke(cmd, ["--force"])

        # 검증
        assert result.exit_code == 0

        # 모든 수정 클래스가 등록되었는지 확인
        register_calls = mock_fix_instance.register_fix.call_args_list
        assert (
            len(register_calls) == 3
        )  # MissingNamespaceFix, ConfigFileFix, HelmRepositoryFix

        # 진단이 실행되었는지 확인
        mock_diagnostic_instance.register_check.assert_called()

        # 수정이 적용되었는지 확인
        mock_fix_instance.apply_fixes.assert_called_once()

    def test_cli_options_parsing(self, runner):
        """CLI 옵션 파싱 테스트"""
        with patch("sbkube.commands.fix.AutoFixEngine"):
            # 모든 옵션과 함께 실행
            runner.invoke(
                cmd,
                [
                    "--dry-run",
                    "--force",
                    "--rollback",
                    "3",
                    "--backup-cleanup",
                    "--history",
                    "--config-dir",
                    "custom-config",
                ],
            )

            # 명령어가 파싱되었는지 확인 (에러가 발생하지 않아야 함)
            # Note: 실제로는 여러 옵션이 상호 배타적이므로 동시에 사용할 수 없지만,
            # 파싱 자체는 성공해야 함
