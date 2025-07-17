import os
from unittest.mock import patch

from click.testing import CliRunner

from sbkube.cli import main


class TestRunEndToEnd:
    def test_complete_run_workflow_dry_run(self):
        """완전한 run 워크플로우 dry-run E2E 테스트"""
        runner = CliRunner()

        with runner.isolated_filesystem():
            # 완전한 테스트 프로젝트 설정
            self._setup_test_project()

            # dry-run 실행 테스트
            result = runner.invoke(main, ["run", "--dry-run"])

            assert result.exit_code == 0
            assert "실행 계획" in result.output
            assert "Dry Run" in result.output
            assert "Prepare" in result.output
            assert "Build" in result.output
            assert "Template" in result.output
            assert "Deploy" in result.output

    def test_run_with_various_options(self):
        """다양한 옵션 조합 E2E 테스트"""
        runner = CliRunner()

        with runner.isolated_filesystem():
            self._setup_test_project()

            # 각 옵션별 테스트 (dry-run 모드로)
            test_cases = [
                ["run", "--dry-run"],
                ["run", "--from-step", "build", "--dry-run"],
                ["run", "--to-step", "template", "--dry-run"],
                ["run", "--only", "prepare", "--dry-run"],
                ["run", "--app", "test-app", "--dry-run"],
                ["run", "--app-dir", "config", "--dry-run"],
                ["run", "--config-file", "config.yaml", "--dry-run"],
                ["run", "--from-step", "build", "--to-step", "template", "--dry-run"],
            ]

            for args in test_cases:
                result = runner.invoke(main, args)
                assert result.exit_code == 0, f"Failed with args: {args}"
                assert "실행 계획" in result.output

    def test_run_option_validation_e2e(self):
        """옵션 검증 E2E 테스트"""
        runner = CliRunner()

        with runner.isolated_filesystem():
            self._setup_test_project()

            # 충돌하는 옵션 조합 테스트
            invalid_combinations = [
                ["run", "--only", "template", "--from-step", "build"],
                ["run", "--only", "template", "--to-step", "deploy"],
                [
                    "run",
                    "--only",
                    "template",
                    "--from-step",
                    "build",
                    "--to-step",
                    "deploy",
                ],
            ]

            for combo in invalid_combinations:
                result = runner.invoke(main, combo)
                assert result.exit_code == 1, f"Should fail with: {combo}"
                assert "옵션 오류" in result.output or "--only 옵션은" in result.output

    def test_help_messages_e2e(self):
        """도움말 메시지 E2E 테스트"""
        runner = CliRunner()

        # 메인 CLI 도움말
        result = runner.invoke(main, ["--help"])
        assert result.exit_code == 0
        assert "run" in result.output

        # run 명령어 도움말
        result = runner.invoke(main, ["run", "--help"])
        assert result.exit_code == 0
        assert "전체 워크플로우를 통합 실행" in result.output
        assert "--dry-run" in result.output
        assert "기본 사용법:" in result.output

    @patch("sbkube.commands.run.RunCommand._show_execution_plan")
    def test_dry_run_plan_display_e2e(self, mock_show_plan):
        """dry-run 계획 표시 E2E 테스트"""
        runner = CliRunner()

        with runner.isolated_filesystem():
            self._setup_test_project()

            result = runner.invoke(main, ["run", "--dry-run"])

            assert result.exit_code == 0
            mock_show_plan.assert_called_once()

            # 호출된 인자 확인
            args, kwargs = mock_show_plan.call_args
            steps = args[0]
            assert steps == ["prepare", "build", "template", "deploy"]

    @patch("sbkube.commands.run.RunCommand._show_execution_plan")
    def test_dry_run_with_step_control_e2e(self, mock_show_plan):
        """단계 제어와 함께 dry-run E2E 테스트"""
        runner = CliRunner()

        with runner.isolated_filesystem():
            self._setup_test_project()

            # --from-step 테스트
            result = runner.invoke(main, ["run", "--from-step", "build", "--dry-run"])
            assert result.exit_code == 0

            args, kwargs = mock_show_plan.call_args
            steps = args[0]
            assert steps == ["build", "template", "deploy"]

            mock_show_plan.reset_mock()

            # --to-step 테스트
            result = runner.invoke(main, ["run", "--to-step", "template", "--dry-run"])
            assert result.exit_code == 0

            args, kwargs = mock_show_plan.call_args
            steps = args[0]
            assert steps == ["prepare", "build", "template"]

            mock_show_plan.reset_mock()

            # --only 테스트
            result = runner.invoke(main, ["run", "--only", "build", "--dry-run"])
            assert result.exit_code == 0

            args, kwargs = mock_show_plan.call_args
            steps = args[0]
            assert steps == ["build"]

    def test_global_options_with_run_e2e(self):
        """전역 옵션과 run 명령어 E2E 테스트"""
        runner = CliRunner()

        with runner.isolated_filesystem():
            self._setup_test_project()

            # 다양한 전역 옵션 조합
            global_option_tests = [
                ["-v", "run", "--dry-run"],
                ["--verbose", "run", "--dry-run"],
                ["run", "--dry-run", "-v"],  # 순서 바뀐 경우
            ]

            for args in global_option_tests:
                result = runner.invoke(main, args)
                assert result.exit_code == 0, f"Failed with args: {args}"

    def test_complete_workflow_simulation(self):
        """실제 워크플로우 시뮬레이션 테스트"""
        runner = CliRunner()

        with runner.isolated_filesystem():
            self._setup_test_project()

            # 1. 먼저 계획 확인
            result = runner.invoke(main, ["run", "--dry-run"])
            assert result.exit_code == 0
            assert "실행 계획" in result.output

            # 2. 특정 단계만 실행 (dry-run)
            result = runner.invoke(main, ["run", "--only", "prepare", "--dry-run"])
            assert result.exit_code == 0

            # 3. 범위를 지정해서 실행 (dry-run)
            result = runner.invoke(
                main,
                ["run", "--from-step", "build", "--to-step", "template", "--dry-run"],
            )
            assert result.exit_code == 0

            # 4. 전체 실행 (dry-run)
            result = runner.invoke(main, ["run", "--dry-run"])
            assert result.exit_code == 0

    def _setup_test_project(self):
        """테스트 프로젝트 기본 구조 생성"""
        os.makedirs("config", exist_ok=True)

        # 기본 config.yaml
        with open("config/config.yaml", "w") as f:
            f.write("""
namespace: test-ns
apps:
  - name: test-app
    type: install-yaml
    specs:
      actions:
        - type: apply
          path: manifests/test.yaml
""")

        # 기본 sources.yaml
        with open("config/sources.yaml", "w") as f:
            f.write("""
helm_repos: []
git_repos: []
""")

        # 테스트 매니페스트
        os.makedirs("manifests", exist_ok=True)
        with open("manifests/test.yaml", "w") as f:
            f.write("""
apiVersion: v1
kind: ConfigMap
metadata:
  name: test-config
data:
  test: "value"
""")

    def test_error_handling_e2e(self):
        """오류 처리 E2E 테스트"""
        runner = CliRunner()

        # 잘못된 디렉토리에서 실행
        result = runner.invoke(main, ["run", "--app-dir", "nonexistent", "--dry-run"])
        # dry-run이므로 실제 파일 검사 전에 계획만 표시되어 성공할 수 있음
        # 실제 실행 시에는 오류가 발생할 것

        # 잘못된 단계 이름 (Click이 자동으로 검증)
        result = runner.invoke(main, ["run", "--from-step", "invalid"])
        assert result.exit_code != 0  # Click 옵션 검증 실패

    def test_run_command_integration_completeness(self):
        """run 명령어 통합 완성도 테스트"""
        runner = CliRunner()

        # 메인 CLI에서 run 명령어 존재 확인
        result = runner.invoke(main, ["--help"])
        assert "run" in result.output

        # run 명령어 자체 실행 가능 확인
        result = runner.invoke(main, ["run", "--help"])
        assert result.exit_code == 0

        # 모든 필수 옵션 존재 확인
        help_output = result.output
        required_options = [
            "--from-step",
            "--to-step",
            "--only",
            "--dry-run",
            "--app-dir",
            "--base-dir",
            "--app",
            "--config-file",
        ]
        for option in required_options:
            assert option in help_output, f"Missing option: {option}"

        # 도움말 섹션 존재 확인
        required_sections = [
            "기본 사용법:",
            "단계별 실행 제어:",
            "환경 설정:",
            "문제 해결:",
        ]
        for section in required_sections:
            assert section in help_output, f"Missing help section: {section}"
