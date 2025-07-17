from pathlib import Path
from unittest.mock import patch

from click.testing import CliRunner

from sbkube.cli import main


class TestInitEndToEnd:
    def test_complete_init_workflow_non_interactive(self):
        """완전한 init 워크플로우 E2E 테스트 (비대화형)"""
        runner = CliRunner()

        with runner.isolated_filesystem():
            result = runner.invoke(
                main,
                [
                    "init",
                    "--name",
                    "e2e-test-project",
                    "--template",
                    "basic",
                    "--non-interactive",
                ],
            )

            assert result.exit_code == 0
            assert "새 프로젝트 초기화를 시작합니다" in result.output
            assert "프로젝트 초기화가 완료되었습니다" in result.output

            # 생성된 파일들 확인
            assert Path("config/config.yaml").exists()
            assert Path("config/sources.yaml").exists()
            assert Path("values/e2e-test-project-values.yaml").exists()
            assert Path("README.md").exists()

            # 환경별 설정 파일 확인 (기본적으로 생성됨)
            assert Path("config/config-development.yaml").exists()
            assert Path("config/config-staging.yaml").exists()
            assert Path("config/config-production.yaml").exists()

    def test_init_with_existing_files_force(self):
        """기존 파일이 있을 때 force 옵션 E2E 테스트"""
        runner = CliRunner()

        with runner.isolated_filesystem():
            # 먼저 한 번 초기화
            result1 = runner.invoke(
                main, ["init", "--name", "existing-project", "--non-interactive"]
            )
            assert result1.exit_code == 0

            # 기존 파일 확인
            assert Path("config/config.yaml").exists()

            # force 옵션으로 다시 초기화
            result2 = runner.invoke(
                main,
                [
                    "init",
                    "--name",
                    "overwritten-project",
                    "--non-interactive",
                    "--force",
                ],
            )
            assert result2.exit_code == 0

            # 파일이 덮어써졌는지 확인
            config_content = Path("config/config.yaml").read_text()
            assert "overwritten-project" in config_content

    def test_init_template_rendering_accuracy(self):
        """템플릿 렌더링 정확성 E2E 테스트"""
        runner = CliRunner()

        with runner.isolated_filesystem():
            result = runner.invoke(
                main,
                [
                    "init",
                    "--name",
                    "template-test",
                    "--template",
                    "basic",
                    "--non-interactive",
                ],
            )

            assert result.exit_code == 0

            # config.yaml 내용 검증
            config_content = Path("config/config.yaml").read_text()
            assert "namespace: template-test" in config_content
            assert "name: template-test" in config_content
            assert "type: install-helm" in config_content

            # sources.yaml 내용 검증
            sources_content = Path("config/sources.yaml").read_text()
            assert "bitnami" in sources_content
            assert "https://charts.bitnami.com/bitnami" in sources_content

            # values 파일 내용 검증
            values_content = Path("values/template-test-values.yaml").read_text()
            assert "template-test Helm Values" in values_content
            assert "replicaCount: 1" in values_content
            assert "repository: nginx" in values_content

            # README.md 내용 검증
            readme_content = Path("README.md").read_text()
            assert "# template-test" in readme_content
            assert "sbkube run" in readme_content
            assert "SBKube로 초기화되었습니다" in readme_content

    def test_init_environment_configs_generation(self):
        """환경별 설정 파일 생성 E2E 테스트"""
        runner = CliRunner()

        with runner.isolated_filesystem():
            result = runner.invoke(
                main, ["init", "--name", "env-test", "--non-interactive"]
            )

            assert result.exit_code == 0

            # 각 환경별 설정 파일 확인
            environments = ["development", "staging", "production"]

            for env in environments:
                env_config_file = Path(f"config/config-{env}.yaml")
                assert env_config_file.exists()

                env_content = env_config_file.read_text()
                assert f"namespace: env-test-{env}" in env_content
                assert "name: env-test" in env_content

    def test_init_directory_structure_creation(self):
        """디렉토리 구조 생성 E2E 테스트"""
        runner = CliRunner()

        with runner.isolated_filesystem():
            result = runner.invoke(
                main, ["init", "--name", "structure-test", "--non-interactive"]
            )

            assert result.exit_code == 0

            # 기본 디렉토리 구조 확인
            assert Path("config").is_dir()
            assert Path("values").is_dir()
            assert Path("manifests").is_dir()

            # 환경별 디렉토리 확인
            environments = ["development", "staging", "production"]
            for env in environments:
                assert Path(f"values/{env}").is_dir()
                assert Path(f"config-{env}").is_dir()

    @patch("click.confirm")
    @patch("click.prompt")
    def test_init_interactive_mode_e2e(self, mock_prompt, mock_confirm):
        """대화형 모드 E2E 테스트"""
        mock_prompt.side_effect = [
            "interactive-project",  # 프로젝트 이름
            "custom-namespace",  # 네임스페이스
            "custom-app",  # 앱 이름
            "install-yaml",  # 앱 타입
        ]
        mock_confirm.side_effect = [
            True,  # 환경별 설정 생성
            False,  # Bitnami 저장소 추가 안함
            True,  # Prometheus 모니터링 설정
        ]

        runner = CliRunner()

        with runner.isolated_filesystem():
            result = runner.invoke(main, ["init"])

            assert result.exit_code == 0
            assert "프로젝트 정보를 입력해주세요" in result.output

            # 사용자 입력이 반영되었는지 확인
            config_content = Path("config/config.yaml").read_text()
            assert "namespace: custom-namespace" in config_content
            assert "name: custom-app" in config_content
            assert "type: install-yaml" in config_content

            # sources.yaml에서 Bitnami가 없고 Prometheus가 있는지 확인
            sources_content = Path("config/sources.yaml").read_text()
            assert "bitnami" not in sources_content
            assert "prometheus-community" in sources_content

    def test_init_different_templates(self):
        """다른 템플릿 옵션 E2E 테스트"""
        runner = CliRunner()

        # 현재는 basic 템플릿만 구현되어 있지만, 구조는 확장 가능
        templates = ["basic"]  # 향후 'web-app', 'microservice' 추가 가능

        for template in templates:
            with runner.isolated_filesystem():
                result = runner.invoke(
                    main,
                    [
                        "init",
                        "--template",
                        template,
                        "--name",
                        f"{template}-test",
                        "--non-interactive",
                    ],
                )

                assert result.exit_code == 0, f"Failed with template: {template}"

                # 기본 파일들이 생성되었는지 확인
                assert Path("config/config.yaml").exists()
                assert Path("config/sources.yaml").exists()
                assert Path("README.md").exists()

    def test_init_error_handling_e2e(self):
        """오류 처리 E2E 테스트"""
        runner = CliRunner()

        # 잘못된 템플릿으로 테스트
        result = runner.invoke(
            main, ["init", "--template", "nonexistent-template", "--non-interactive"]
        )

        # Click이 자동으로 잘못된 선택을 거부
        assert result.exit_code != 0

    def test_init_help_accessibility(self):
        """도움말 접근성 E2E 테스트"""
        runner = CliRunner()

        # 메인 CLI에서 init 명령어 확인
        result = runner.invoke(main, ["--help"])
        assert result.exit_code == 0
        assert "init" in result.output

        # init 명령어 자체 도움말
        result = runner.invoke(main, ["init", "--help"])
        assert result.exit_code == 0
        assert "새 프로젝트를 초기화합니다" in result.output
        assert "사용 예시:" in result.output

        # 모든 필수 옵션이 도움말에 표시되는지 확인
        help_content = result.output
        required_options = ["--template", "--name", "--non-interactive", "--force"]
        for option in required_options:
            assert option in help_content

    def test_init_output_consistency(self):
        """출력 일관성 E2E 테스트"""
        runner = CliRunner()

        with runner.isolated_filesystem():
            result = runner.invoke(
                main, ["init", "--name", "consistency-test", "--non-interactive"]
            )

            assert result.exit_code == 0

            # 성공 메시지들이 올바른 순서로 출력되는지 확인
            output_lines = result.output.split("\n")

            # 주요 단계별 메시지 확인
            assert any(
                "새 프로젝트 초기화를 시작합니다" in line for line in output_lines
            )
            assert any("생성됨: config/config.yaml" in line for line in output_lines)
            assert any("생성됨: config/sources.yaml" in line for line in output_lines)
            assert any("README.md 생성됨" in line for line in output_lines)
            assert any(
                "프로젝트 초기화가 완료되었습니다" in line for line in output_lines
            )
            assert any("다음 단계:" in line for line in output_lines)

    def test_init_file_content_validation(self):
        """생성된 파일 내용 검증 E2E 테스트"""
        runner = CliRunner()

        with runner.isolated_filesystem():
            result = runner.invoke(
                main, ["init", "--name", "validation-test", "--non-interactive"]
            )

            assert result.exit_code == 0

            # 생성된 파일들이 유효한 YAML인지 확인
            import yaml

            # config.yaml 검증
            with open("config/config.yaml") as f:
                config_data = yaml.safe_load(f)
                assert config_data["namespace"] == "validation-test"
                assert len(config_data["apps"]) == 1
                assert config_data["apps"][0]["name"] == "validation-test"

            # sources.yaml 검증
            with open("config/sources.yaml") as f:
                sources_data = yaml.safe_load(f)
                assert "helm_repos" in sources_data
                assert "git_repos" in sources_data
                assert isinstance(sources_data["helm_repos"], list)
                assert isinstance(sources_data["git_repos"], list)

            # values 파일 검증
            with open("values/validation-test-values.yaml") as f:
                values_data = yaml.safe_load(f)
                assert "replicaCount" in values_data
                assert "image" in values_data
                assert "service" in values_data
                assert "resources" in values_data

    def test_init_workflow_integration_with_run(self):
        """init 후 run 명령어 연동 E2E 테스트"""
        runner = CliRunner()

        with runner.isolated_filesystem():
            # 프로젝트 초기화
            init_result = runner.invoke(
                main, ["init", "--name", "integration-test", "--non-interactive"]
            )
            assert init_result.exit_code == 0

            # run 명령어로 dry-run 실행해보기
            run_result = runner.invoke(main, ["run", "--dry-run"])
            assert run_result.exit_code == 0
            assert "실행 계획" in run_result.output

            # 초기화된 프로젝트에서 run이 정상 동작하는지 확인
