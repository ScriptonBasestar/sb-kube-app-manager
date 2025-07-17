from unittest.mock import patch

from click.testing import CliRunner

from sbkube.commands.run import cmd


class TestRunCLIErrorHandling:
    @patch("sbkube.commands.prepare.PrepareCommand.execute")
    @patch("sbkube.commands.run.RunCommand.execute_pre_hook")
    def test_step_failure_cli_output(self, mock_pre_hook, mock_prepare):
        """CLI 단계 실패 출력 테스트"""
        mock_prepare.side_effect = Exception("Mock prepare error")

        runner = CliRunner()
        result = runner.invoke(cmd)

        assert result.exit_code == 1
        assert "prepare 단계 실패" in result.output
        assert "💡 다음 해결 방법을 시도해보세요" in result.output
        assert "sbkube run --from-step prepare" in result.output
        assert "sources.yaml" in result.output

    def test_option_validation_error(self):
        """옵션 검증 오류 테스트"""
        runner = CliRunner()
        result = runner.invoke(cmd, ["--only", "template", "--from-step", "build"])

        assert result.exit_code == 1
        assert "옵션 오류" in result.output
        assert "--help" in result.output

    @patch("sbkube.commands.run.RunCommand.execute")
    def test_keyboard_interrupt_handling(self, mock_execute):
        """키보드 인터럽트 처리 테스트"""
        mock_execute.side_effect = KeyboardInterrupt()

        runner = CliRunner()
        result = runner.invoke(cmd)

        assert result.exit_code == 130
        assert "사용자에 의해 중단" in result.output

    @patch("sbkube.commands.run.RunCommand.execute")
    def test_unexpected_error_handling(self, mock_execute):
        """예상치 못한 오류 처리 테스트"""
        mock_execute.side_effect = RuntimeError("Unexpected error")

        runner = CliRunner()
        result = runner.invoke(cmd)

        assert result.exit_code == 1
        assert "예상치 못한 오류" in result.output
        assert "-v 옵션" in result.output
        assert "GitHub Issues" in result.output
        assert "sbkube validate" in result.output

    @patch("sbkube.commands.run.RunCommand.execute")
    def test_successful_execution_output(self, mock_execute):
        """성공적인 실행 출력 테스트"""
        runner = CliRunner()
        result = runner.invoke(cmd)

        assert result.exit_code == 0
        assert "🎉 모든 단계가 성공적으로 완료되었습니다!" in result.output

    @patch("sbkube.commands.build.BuildCommand.execute")
    @patch("sbkube.commands.prepare.PrepareCommand.execute")
    @patch("sbkube.commands.run.RunCommand.execute_pre_hook")
    def test_build_step_failure_output(self, mock_pre_hook, mock_prepare, mock_build):
        """build 단계 실패 출력 테스트"""
        mock_build.side_effect = Exception("Build error with file not found")

        runner = CliRunner()
        result = runner.invoke(cmd)

        assert result.exit_code == 1
        assert "build 단계 실패" in result.output
        assert "config.yaml" in result.output
        assert "prepare 단계가 정상적으로" in result.output
        assert "sbkube run --from-step build" in result.output

    @patch("sbkube.commands.template.TemplateCommand.execute")
    @patch("sbkube.commands.build.BuildCommand.execute")
    @patch("sbkube.commands.prepare.PrepareCommand.execute")
    @patch("sbkube.commands.run.RunCommand.execute_pre_hook")
    def test_template_step_failure_output(
        self, mock_pre_hook, mock_prepare, mock_build, mock_template
    ):
        """template 단계 실패 출력 테스트"""
        mock_template.side_effect = Exception("yaml syntax error")

        runner = CliRunner()
        result = runner.invoke(cmd)

        assert result.exit_code == 1
        assert "template 단계 실패" in result.output
        assert "Helm 차트" in result.output
        assert "YAML 파일 문법" in result.output
        assert "sbkube run --from-step template" in result.output

    @patch("sbkube.commands.deploy.DeployCommand.execute")
    @patch("sbkube.commands.template.TemplateCommand.execute")
    @patch("sbkube.commands.build.BuildCommand.execute")
    @patch("sbkube.commands.prepare.PrepareCommand.execute")
    @patch("sbkube.commands.run.RunCommand.execute_pre_hook")
    def test_deploy_step_failure_output(
        self, mock_pre_hook, mock_prepare, mock_build, mock_template, mock_deploy
    ):
        """deploy 단계 실패 출력 테스트"""
        mock_deploy.side_effect = Exception("namespace not found")

        runner = CliRunner()
        result = runner.invoke(cmd)

        assert result.exit_code == 1
        assert "deploy 단계 실패" in result.output
        assert "네임스페이스" in result.output
        assert "kubectl create namespace" in result.output
        assert "sbkube run --from-step deploy" in result.output

    @patch("sbkube.commands.template.TemplateCommand.execute")
    @patch("sbkube.commands.build.BuildCommand.execute")
    @patch("sbkube.commands.prepare.PrepareCommand.execute")
    @patch("sbkube.commands.run.RunCommand.execute_pre_hook")
    def test_step_failure_with_only_option(
        self, mock_pre_hook, mock_prepare, mock_build, mock_template
    ):
        """--only 옵션 사용 시 단계 실패 테스트"""
        mock_template.side_effect = Exception("Template error")

        runner = CliRunner()
        result = runner.invoke(cmd, ["--only", "template"])

        assert result.exit_code == 1
        assert "template 단계 실패" in result.output
        assert "sbkube run --from-step template" in result.output

        # prepare와 build는 실행되지 않았어야 함
        mock_prepare.assert_not_called()
        mock_build.assert_not_called()

    def test_error_output_format_consistency(self):
        """오류 출력 형식 일관성 테스트"""
        runner = CliRunner()

        # 옵션 오류
        result = runner.invoke(cmd, ["--invalid-option"])
        assert "❌" in result.output

        # 옵션 충돌 오류
        result = runner.invoke(cmd, ["--only", "template", "--from-step", "build"])
        assert "❌ 옵션 오류" in result.output
        assert "💡" in result.output

    @patch("sbkube.commands.prepare.PrepareCommand.execute")
    @patch("sbkube.commands.run.RunCommand.execute_pre_hook")
    def test_suggestions_numbering(self, mock_pre_hook, mock_prepare):
        """제안사항 번호 매기기 테스트"""
        mock_prepare.side_effect = Exception("Permission denied")

        runner = CliRunner()
        result = runner.invoke(cmd)

        assert result.exit_code == 1
        assert "1." in result.output
        assert "2." in result.output
        assert "3." in result.output

        # 여러 제안사항이 번호와 함께 나열되는지 확인
        lines = result.output.split("\n")
        numbered_lines = [
            line
            for line in lines
            if line.strip().startswith(("1.", "2.", "3.", "4.", "5."))
        ]
        assert len(numbered_lines) >= 3
