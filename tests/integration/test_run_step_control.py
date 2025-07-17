from unittest.mock import patch

from click.testing import CliRunner

from sbkube.commands.run import cmd


class TestRunStepControl:
    @patch("sbkube.commands.run.RunCommand.execute")
    def test_from_step_option(self, mock_execute):
        """--from-step 옵션 테스트"""
        runner = CliRunner()

        with runner.isolated_filesystem():
            result = runner.invoke(cmd, ["--from-step", "template"])

            assert result.exit_code == 0
            mock_execute.assert_called_once()

            # RunCommand가 올바른 매개변수로 생성되었는지 확인
            args, kwargs = mock_execute.call_args
            # execute() 메서드는 인자가 없음, RunCommand 인스턴스에서 확인

    @patch("sbkube.commands.run.RunCommand.execute")
    def test_to_step_option(self, mock_execute):
        """--to-step 옵션 테스트"""
        runner = CliRunner()

        with runner.isolated_filesystem():
            result = runner.invoke(cmd, ["--to-step", "build"])

            assert result.exit_code == 0
            mock_execute.assert_called_once()

    @patch("sbkube.commands.run.RunCommand.execute")
    def test_only_option(self, mock_execute):
        """--only 옵션 테스트"""
        runner = CliRunner()

        with runner.isolated_filesystem():
            result = runner.invoke(cmd, ["--only", "template"])

            assert result.exit_code == 0
            mock_execute.assert_called_once()

    def test_option_conflict(self):
        """옵션 충돌 테스트"""
        runner = CliRunner()

        with runner.isolated_filesystem():
            result = runner.invoke(cmd, ["--only", "template", "--from-step", "build"])

            assert result.exit_code == 1
            assert (
                "--only 옵션은 --from-step, --to-step과 함께 사용할 수 없습니다"
                in result.output
            )

    def test_option_conflict_only_with_to_step(self):
        """--only와 --to-step 옵션 충돌 테스트"""
        runner = CliRunner()

        with runner.isolated_filesystem():
            result = runner.invoke(cmd, ["--only", "template", "--to-step", "deploy"])

            assert result.exit_code == 1
            assert (
                "--only 옵션은 --from-step, --to-step과 함께 사용할 수 없습니다"
                in result.output
            )

    @patch("sbkube.commands.run.RunCommand")
    def test_parameter_passing_from_step(self, mock_run_command):
        """--from-step 매개변수 전달 테스트"""
        runner = CliRunner()
        mock_instance = mock_run_command.return_value

        with runner.isolated_filesystem():
            runner.invoke(
                cmd,
                [
                    "--app-dir",
                    "test-config",
                    "--base-dir",
                    "/test/path",
                    "--app",
                    "my-app",
                    "--config-file",
                    "my-config.yaml",
                    "--from-step",
                    "build",
                ],
            )

            # RunCommand가 올바른 매개변수로 생성되었는지 확인
            mock_run_command.assert_called_once_with(
                base_dir="/test/path",
                app_config_dir="test-config",
                target_app_name="my-app",
                config_file_name="my-config.yaml",
                from_step="build",
                to_step=None,
                only_step=None,
            )

            mock_instance.execute.assert_called_once()

    @patch("sbkube.commands.run.RunCommand")
    def test_parameter_passing_to_step(self, mock_run_command):
        """--to-step 매개변수 전달 테스트"""
        runner = CliRunner()

        with runner.isolated_filesystem():
            runner.invoke(cmd, ["--to-step", "template"])

            # RunCommand가 올바른 매개변수로 생성되었는지 확인
            mock_run_command.assert_called_once_with(
                base_dir=".",
                app_config_dir="config",
                target_app_name=None,
                config_file_name=None,
                from_step=None,
                to_step="template",
                only_step=None,
            )

    @patch("sbkube.commands.run.RunCommand")
    def test_parameter_passing_only_step(self, mock_run_command):
        """--only 매개변수 전달 테스트"""
        runner = CliRunner()

        with runner.isolated_filesystem():
            runner.invoke(cmd, ["--only", "deploy"])

            # RunCommand가 올바른 매개변수로 생성되었는지 확인
            mock_run_command.assert_called_once_with(
                base_dir=".",
                app_config_dir="config",
                target_app_name=None,
                config_file_name=None,
                from_step=None,
                to_step=None,
                only_step="deploy",
            )

    @patch("sbkube.commands.run.RunCommand")
    def test_parameter_passing_from_to_combination(self, mock_run_command):
        """--from-step과 --to-step 조합 매개변수 전달 테스트"""
        runner = CliRunner()

        with runner.isolated_filesystem():
            runner.invoke(
                cmd, ["--from-step", "build", "--to-step", "template"]
            )

            # RunCommand가 올바른 매개변수로 생성되었는지 확인
            mock_run_command.assert_called_once_with(
                base_dir=".",
                app_config_dir="config",
                target_app_name=None,
                config_file_name=None,
                from_step="build",
                to_step="template",
                only_step=None,
            )

    @patch("sbkube.commands.run.RunCommand.execute")
    def test_value_error_handling(self, mock_execute):
        """ValueError 처리 테스트"""
        runner = CliRunner()
        mock_execute.side_effect = ValueError("Test validation error")

        with runner.isolated_filesystem():
            result = runner.invoke(cmd, ["--only", "template"])

            assert result.exit_code == 1
            # ValueError는 옵션 오류로 처리됨
            assert "❌ 옵션 오류: Test validation error" in result.output

    def test_help_message_includes_new_options(self):
        """help 메시지에 새로운 옵션들이 포함되는지 테스트"""
        runner = CliRunner()
        result = runner.invoke(cmd, ["--help"])

        assert result.exit_code == 0
        assert "--from-step" in result.output
        assert "--to-step" in result.output
        assert "--only" in result.output
        assert "시작할 단계 지정" in result.output
        assert "종료할 단계 지정" in result.output
        assert "특정 단계만 실행" in result.output
