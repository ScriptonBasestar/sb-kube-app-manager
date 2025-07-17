from unittest.mock import patch

import pytest

from sbkube.commands.run import RunCommand, RunExecutionError


class TestRunErrorHandling:
    def test_step_failure_handling(self):
        """단계 실패 처리 테스트"""
        cmd = RunCommand(".", "config")

        mock_error = Exception("Test error")

        # _handle_step_failure 메서드가 예외 없이 실행되는지 확인
        cmd._handle_step_failure("build", mock_error, 2, 4)

        # 메서드가 정상적으로 완료되면 테스트 통과
        assert True

    def test_error_message_enhancement(self):
        """오류 메시지 강화 테스트"""
        cmd = RunCommand(".", "config")

        error = Exception("Original error")
        enhanced = cmd._enhance_error_message("prepare", error)
        assert "소스 준비 중 오류 발생" in enhanced
        assert "Original error" in enhanced

        enhanced = cmd._enhance_error_message("build", error)
        assert "앱 빌드 중 오류 발생" in enhanced

        enhanced = cmd._enhance_error_message("template", error)
        assert "템플릿 렌더링 중 오류 발생" in enhanced

        enhanced = cmd._enhance_error_message("deploy", error)
        assert "배포 중 오류 발생" in enhanced

        enhanced = cmd._enhance_error_message("unknown", error)
        assert enhanced == "Original error"

    def test_failure_suggestions_prepare(self):
        """prepare 단계 실패 제안 테스트"""
        cmd = RunCommand(".", "config")

        error = Exception("Repository not found")
        suggestions = cmd._get_failure_suggestions("prepare", error)

        assert any("sources.yaml" in s for s in suggestions)
        assert any("저장소 URL" in s for s in suggestions)
        assert any("네트워크 연결" in s for s in suggestions)
        assert any("--from-step prepare" in s for s in suggestions)

        # permission 오류 테스트
        permission_error = Exception("Permission denied")
        suggestions = cmd._get_failure_suggestions("prepare", permission_error)
        assert any("권한" in s for s in suggestions)

    def test_failure_suggestions_build(self):
        """build 단계 실패 제안 테스트"""
        cmd = RunCommand(".", "config")

        error = Exception("file not found")
        suggestions = cmd._get_failure_suggestions("build", error)

        assert any("config.yaml" in s for s in suggestions)
        assert any("prepare 단계가 정상적으로" in s for s in suggestions)
        assert any("--from-step build" in s for s in suggestions)

    def test_failure_suggestions_template(self):
        """template 단계 실패 제안 테스트"""
        cmd = RunCommand(".", "config")

        error = Exception("yaml syntax error")
        suggestions = cmd._get_failure_suggestions("template", error)

        assert any("Helm 차트" in s for s in suggestions)
        assert any("YAML 파일 문법" in s for s in suggestions)
        assert any("--from-step template" in s for s in suggestions)

    def test_failure_suggestions_deploy(self):
        """deploy 단계 실패 제안 테스트"""
        cmd = RunCommand(".", "config")

        error = Exception("namespace not found")
        suggestions = cmd._get_failure_suggestions("deploy", error)

        assert any("네임스페이스" in s for s in suggestions)
        assert any("kubectl create namespace" in s for s in suggestions)
        assert any("--from-step deploy" in s for s in suggestions)

        # permission 오류 테스트
        permission_error = Exception("permission denied to deploy")
        suggestions = cmd._get_failure_suggestions("deploy", permission_error)
        assert any("kubectl 권한" in s for s in suggestions)

    def test_common_suggestions_always_included(self):
        """공통 제안사항이 항상 포함되는지 테스트"""
        cmd = RunCommand(".", "config")

        for step in ["prepare", "build", "template", "deploy"]:
            error = Exception("Test error")
            suggestions = cmd._get_failure_suggestions(step, error)

            assert any(f"--from-step {step}" in s for s in suggestions)
            assert any("sbkube validate" in s for s in suggestions)
            assert any("-v 옵션" in s for s in suggestions)

    def test_save_failure_state(self):
        """실패 상태 저장 테스트"""
        cmd = RunCommand(".", "config")

        error = Exception("Test error")

        # 현재는 디버그 로그만 기록하므로 예외 없이 실행되는지 확인
        cmd._save_failure_state("prepare", error)
        assert True

    @patch("sbkube.commands.prepare.PrepareCommand.execute")
    @patch.object(RunCommand, "execute_pre_hook")
    def test_run_execution_error_propagation(self, mock_pre_hook, mock_prepare):
        """RunExecutionError 전파 테스트"""
        mock_prepare.side_effect = Exception("Prepare failed")

        cmd = RunCommand(".", "config")

        with pytest.raises(RunExecutionError) as exc_info:
            cmd.execute()

        assert exc_info.value.step == "prepare"
        assert "Prepare failed" in str(exc_info.value)
        assert len(exc_info.value.suggestions) > 0

        # 제안사항에 prepare 관련 내용이 포함되어 있는지 확인
        suggestions_text = " ".join(exc_info.value.suggestions)
        assert "sources.yaml" in suggestions_text

    @patch("sbkube.commands.build.BuildCommand.execute")
    @patch("sbkube.commands.prepare.PrepareCommand.execute")
    @patch.object(RunCommand, "execute_pre_hook")
    def test_run_execution_error_on_second_step(
        self, mock_pre_hook, mock_prepare, mock_build
    ):
        """두 번째 단계에서 실패 시 테스트"""
        mock_build.side_effect = Exception("Build failed")

        cmd = RunCommand(".", "config")

        with pytest.raises(RunExecutionError) as exc_info:
            cmd.execute()

        assert exc_info.value.step == "build"
        assert "Build failed" in str(exc_info.value)

        # prepare는 성공했어야 함
        mock_prepare.assert_called_once()
        mock_build.assert_called_once()

    def test_run_execution_error_attributes(self):
        """RunExecutionError 속성 테스트"""
        suggestions = ["suggestion 1", "suggestion 2"]
        error = RunExecutionError("test_step", "test message", suggestions)

        assert error.step == "test_step"
        assert error.suggestions == suggestions
        assert "test_step 단계 실패: test message" in str(error)

        # 제안사항이 없는 경우
        error_no_suggestions = RunExecutionError("test_step", "test message")
        assert error_no_suggestions.suggestions == []
