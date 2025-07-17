from unittest.mock import Mock, patch

import pytest

from sbkube.commands.run import RunCommand


class TestRunCommand:
    def test_init(self):
        """RunCommand 초기화 테스트"""
        cmd = RunCommand(".", "config")
        assert str(cmd.base_dir) == "."
        assert str(cmd.app_config_dir) == "config"

    def test_init_with_optional_params(self):
        """RunCommand 초기화 시 선택적 매개변수 테스트"""
        cmd = RunCommand(".", "config", "test-app", "config.yaml")
        assert str(cmd.base_dir) == "."
        assert str(cmd.app_config_dir) == "config"
        assert cmd.target_app_name == "test-app"
        assert cmd.config_file_name == "config.yaml"

    def test_execute_step_validation(self):
        """단계 이름 검증 테스트"""
        cmd = RunCommand(".", "config")

        with pytest.raises(ValueError, match="Unknown step: invalid_step"):
            cmd._execute_step("invalid_step")

    @patch("sbkube.commands.run.prepare.PrepareCommand")
    def test_execute_step_prepare(self, mock_prepare):
        """prepare 단계 실행 테스트"""
        cmd = RunCommand(".", "config", "test-app", "config.yaml")
        mock_instance = Mock()
        mock_prepare.return_value = mock_instance

        cmd._execute_step("prepare")

        mock_prepare.assert_called_once_with(".", "config", "test-app", "config.yaml")
        mock_instance.execute.assert_called_once()

    @patch("sbkube.commands.run.build.BuildCommand")
    def test_execute_step_build(self, mock_build):
        """build 단계 실행 테스트"""
        cmd = RunCommand(".", "config", "test-app", "config.yaml")
        mock_instance = Mock()
        mock_build.return_value = mock_instance

        cmd._execute_step("build")

        mock_build.assert_called_once_with(".", "config", "test-app", "config.yaml")
        mock_instance.execute.assert_called_once()

    @patch("sbkube.commands.run.template.TemplateCommand")
    def test_execute_step_template(self, mock_template):
        """template 단계 실행 테스트"""
        cmd = RunCommand(".", "config", "test-app", "config.yaml")
        mock_instance = Mock()
        mock_template.return_value = mock_instance

        cmd._execute_step("template")

        mock_template.assert_called_once_with(".", "config", "test-app", "config.yaml")
        mock_instance.execute.assert_called_once()

    @patch("sbkube.commands.run.deploy.DeployCommand")
    def test_execute_step_deploy(self, mock_deploy):
        """deploy 단계 실행 테스트"""
        cmd = RunCommand(".", "config", "test-app", "config.yaml")
        mock_instance = Mock()
        mock_deploy.return_value = mock_instance

        cmd._execute_step("deploy")

        mock_deploy.assert_called_once_with(".", "config", "test-app", "config.yaml")
        mock_instance.execute.assert_called_once()

    @patch("sbkube.commands.run.deploy.DeployCommand")
    @patch("sbkube.commands.run.template.TemplateCommand")
    @patch("sbkube.commands.run.build.BuildCommand")
    @patch("sbkube.commands.run.prepare.PrepareCommand")
    @patch.object(RunCommand, "execute_pre_hook")
    def test_execute_full_workflow(
        self, mock_pre_hook, mock_prepare, mock_build, mock_template, mock_deploy
    ):
        """전체 워크플로우 실행 테스트"""
        cmd = RunCommand(".", "config")

        # Mock instances
        for mock_class in [mock_prepare, mock_build, mock_template, mock_deploy]:
            mock_instance = Mock()
            mock_class.return_value = mock_instance

        cmd.execute()

        # 사전 작업이 실행되는지 확인
        mock_pre_hook.assert_called_once()

        # 모든 단계가 순서대로 실행되는지 확인
        mock_prepare.assert_called_once()
        mock_build.assert_called_once()
        mock_template.assert_called_once()
        mock_deploy.assert_called_once()

    @patch("sbkube.commands.run.prepare.PrepareCommand")
    @patch.object(RunCommand, "execute_pre_hook")
    def test_execute_step_failure(self, mock_pre_hook, mock_prepare):
        """단계 실행 실패 시 예외 처리 테스트"""
        cmd = RunCommand(".", "config")

        # prepare 단계에서 예외 발생 시뮬레이션
        mock_instance = Mock()
        mock_instance.execute.side_effect = Exception("Test error")
        mock_prepare.return_value = mock_instance

        with pytest.raises(Exception, match="Test error"):
            cmd.execute()

        # 사전 작업은 실행되었지만, prepare에서 실패했는지 확인
        mock_pre_hook.assert_called_once()
        mock_prepare.assert_called_once()


class TestRunCommandStepControl:
    def test_determine_steps_full_workflow(self):
        """전체 워크플로우 단계 결정"""
        cmd = RunCommand(".", "config")
        steps = cmd._determine_steps()
        assert steps == ["prepare", "build", "template", "deploy"]

    def test_determine_steps_from_step(self):
        """--from-step 옵션 테스트"""
        cmd = RunCommand(".", "config", from_step="build")
        steps = cmd._determine_steps()
        assert steps == ["build", "template", "deploy"]

    def test_determine_steps_to_step(self):
        """--to-step 옵션 테스트"""
        cmd = RunCommand(".", "config", to_step="template")
        steps = cmd._determine_steps()
        assert steps == ["prepare", "build", "template"]

    def test_determine_steps_from_to_step(self):
        """--from-step과 --to-step 조합 테스트"""
        cmd = RunCommand(".", "config", from_step="build", to_step="template")
        steps = cmd._determine_steps()
        assert steps == ["build", "template"]

    def test_determine_steps_only_step(self):
        """--only 옵션 테스트"""
        cmd = RunCommand(".", "config", only_step="template")
        steps = cmd._determine_steps()
        assert steps == ["template"]

    def test_invalid_from_step_name(self):
        """잘못된 from_step 이름 처리"""
        cmd = RunCommand(".", "config", from_step="invalid")
        with pytest.raises(ValueError, match="Invalid from-step: invalid"):
            cmd._determine_steps()

    def test_invalid_to_step_name(self):
        """잘못된 to_step 이름 처리"""
        cmd = RunCommand(".", "config", to_step="invalid")
        with pytest.raises(ValueError, match="Invalid to-step: invalid"):
            cmd._determine_steps()

    def test_invalid_only_step_name(self):
        """잘못된 only_step 이름 처리"""
        cmd = RunCommand(".", "config", only_step="invalid")
        with pytest.raises(ValueError, match="Invalid step: invalid"):
            cmd._determine_steps()

    def test_invalid_step_order(self):
        """잘못된 단계 순서 처리"""
        cmd = RunCommand(".", "config", from_step="deploy", to_step="prepare")
        with pytest.raises(ValueError, match="from-step must come before to-step"):
            cmd._determine_steps()

    def test_validate_step_dependencies(self):
        """단계 의존성 검증 테스트"""
        cmd = RunCommand(".", "config")

        # template 단계만 실행 시 의존성 경고가 출력되어야 함
        # (실제 로깅 출력은 테스트하지 않고, 메서드가 예외 없이 실행되는지만 확인)
        cmd._validate_step_dependencies(["template"])

        # 전체 워크플로우 실행 시 의존성 문제 없음
        cmd._validate_step_dependencies(["prepare", "build", "template", "deploy"])

    def test_is_step_completed_default(self):
        """단계 완료 여부 기본값 테스트"""
        cmd = RunCommand(".", "config")
        assert cmd._is_step_completed("prepare") is False
        assert cmd._is_step_completed("build") is False


class TestRunCommandDryRun:
    def test_dry_run_initialization(self):
        """dry-run 초기화 테스트"""
        cmd = RunCommand(".", "config", dry_run=True)
        assert cmd.dry_run is True

        cmd_default = RunCommand(".", "config")
        assert cmd_default.dry_run is False

    @patch("sbkube.commands.run.RunCommand._show_execution_plan")
    def test_dry_run_execution(self, mock_show_plan):
        """dry-run 실행 테스트"""
        cmd = RunCommand(".", "config", dry_run=True)

        cmd.execute()

        # _show_execution_plan이 호출되었는지 확인
        mock_show_plan.assert_called_once()

        # 실제 단계 실행은 되지 않았는지 확인 (호출된 인자로 검증)
        args, kwargs = mock_show_plan.call_args
        steps = args[0]
        assert steps == ["prepare", "build", "template", "deploy"]

    @patch("sbkube.commands.run.RunCommand._show_execution_plan")
    def test_dry_run_with_step_control(self, mock_show_plan):
        """단계 제어와 함께 dry-run 테스트"""
        # --from-step 테스트
        cmd = RunCommand(".", "config", from_step="build", dry_run=True)
        cmd.execute()

        args, kwargs = mock_show_plan.call_args
        steps = args[0]
        assert steps == ["build", "template", "deploy"]

        mock_show_plan.reset_mock()

        # --only 테스트
        cmd = RunCommand(".", "config", only_step="template", dry_run=True)
        cmd.execute()

        args, kwargs = mock_show_plan.call_args
        steps = args[0]
        assert steps == ["template"]

    @patch("sbkube.commands.run.RunCommand._show_execution_plan")
    @patch.object(RunCommand, "execute_pre_hook")
    def test_dry_run_skips_pre_hook(self, mock_pre_hook, mock_show_plan):
        """dry-run이 사전 작업을 건너뛰는지 테스트"""
        cmd = RunCommand(".", "config", dry_run=True)
        cmd.execute()

        # dry-run에서는 사전 작업이 실행되지 않아야 함
        mock_pre_hook.assert_not_called()
        mock_show_plan.assert_called_once()

    @patch("rich.console.Console.print")
    def test_show_execution_plan_output(self, mock_print):
        """실행 계획 표시 테스트"""
        cmd = RunCommand(".", "config")
        steps = ["prepare", "build", "template", "deploy"]

        cmd._show_execution_plan(steps)

        # rich.console.Console.print가 호출되었는지 확인
        assert mock_print.call_count >= 1

        # 호출된 인자들 확인
        call_args_list = mock_print.call_args_list
        output_content = str(call_args_list)

        # 기본적인 내용이 포함되어 있는지 확인
        assert "실행 계획" in output_content or "Dry Run" in output_content

    def test_dry_run_with_all_parameters(self):
        """모든 매개변수와 함께 dry-run 테스트"""
        cmd = RunCommand(
            base_dir="/test/base",
            app_config_dir="test-config",
            target_app_name="test-app",
            config_file_name="test.yaml",
            from_step="build",
            to_step="template",
            only_step=None,
            dry_run=True,
        )

        assert cmd.dry_run is True
        assert cmd.from_step == "build"
        assert cmd.to_step == "template"
        assert cmd.only_step is None

        steps = cmd._determine_steps()
        assert steps == ["build", "template"]
