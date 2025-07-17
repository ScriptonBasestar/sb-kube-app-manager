import tempfile
from pathlib import Path

import yaml
from click.testing import CliRunner

from sbkube.cli import main
from sbkube.utils.profile_manager import ProfileManager


class TestProfileIntegration:
    def test_profile_manager_with_init_generated_files(self):
        """init으로 생성된 파일들과 ProfileManager 통합 테스트"""
        runner = CliRunner()

        with runner.isolated_filesystem():
            # 프로젝트 초기화
            result = runner.invoke(
                main, ["init", "--name", "profile-test", "--non-interactive"]
            )
            assert result.exit_code == 0

            # ProfileManager로 프로파일 목록 확인
            pm = ProfileManager(".", "config")
            profiles = pm.list_profiles()

            # init으로 생성된 환경별 프로파일 확인
            profile_names = [p["name"] for p in profiles]
            assert "development" in profile_names
            assert "staging" in profile_names
            assert "production" in profile_names

            # 각 프로파일이 유효한지 확인
            for profile in profiles:
                assert profile["valid"]
                assert profile["namespace"].startswith("profile-test")
                assert profile["apps_count"] == 1

    def test_run_with_profile_end_to_end(self):
        """run 명령어와 프로파일 E2E 테스트"""
        runner = CliRunner()

        with runner.isolated_filesystem():
            # 프로젝트 초기화
            init_result = runner.invoke(
                main, ["init", "--name", "e2e-test", "--non-interactive"]
            )
            assert init_result.exit_code == 0

            # 프로파일을 사용한 dry-run 실행
            run_result = runner.invoke(
                main, ["run", "--profile", "development", "--dry-run"]
            )
            assert run_result.exit_code == 0
            assert "프로파일 'development' 로딩 중" in run_result.output
            assert "프로파일 'development' 로딩 완료" in run_result.output
            assert "실행 계획" in run_result.output

    def test_run_with_invalid_profile_cli(self):
        """존재하지 않는 프로파일로 CLI 실행 테스트"""
        runner = CliRunner()

        with runner.isolated_filesystem():
            # 프로젝트 초기화
            init_result = runner.invoke(
                main, ["init", "--name", "invalid-test", "--non-interactive"]
            )
            assert init_result.exit_code == 0

            # 존재하지 않는 프로파일로 실행
            run_result = runner.invoke(
                main, ["run", "--profile", "nonexistent", "--dry-run"]
            )
            assert run_result.exit_code == 1
            assert "프로파일 로딩 실패" in run_result.output

    def test_profile_values_path_resolution(self):
        """프로파일별 values 파일 경로 해결 테스트"""
        with tempfile.TemporaryDirectory() as tmpdir:
            # 디렉토리 구조 생성
            config_dir = Path(tmpdir) / "config"
            values_dir = Path(tmpdir) / "values"
            dev_values_dir = values_dir / "development"
            prod_values_dir = values_dir / "production"
            common_values_dir = values_dir / "common"

            config_dir.mkdir()
            values_dir.mkdir()
            dev_values_dir.mkdir()
            prod_values_dir.mkdir()
            common_values_dir.mkdir()

            # Values 파일 생성
            (dev_values_dir / "app-values.yaml").write_text("replicas: 1")
            (prod_values_dir / "app-values.yaml").write_text("replicas: 3")
            (common_values_dir / "common-values.yaml").write_text("debug: false")
            (values_dir / "base-values.yaml").write_text("timeout: 30")

            # 설정 파일 생성
            base_config = {
                "namespace": "default",
                "apps": [
                    {
                        "name": "test-app",
                        "type": "install-helm",
                        "specs": {
                            "path": "test-chart",
                            "values": [
                                "app-values.yaml",
                                "common-values.yaml",
                                "base-values.yaml",
                            ],
                        },
                    }
                ],
            }

            dev_config = {"namespace": "development"}
            prod_config = {"namespace": "production"}

            with open(config_dir / "config.yaml", "w") as f:
                yaml.dump(base_config, f)

            with open(config_dir / "config-development.yaml", "w") as f:
                yaml.dump(dev_config, f)

            with open(config_dir / "config-production.yaml", "w") as f:
                yaml.dump(prod_config, f)

            # ProfileManager로 프로파일 로드
            pm = ProfileManager(tmpdir, "config")

            # Development 프로파일 테스트
            dev_config_loaded = pm.load_profile("development")
            dev_values = dev_config_loaded["apps"][0]["specs"]["values"]

            assert "values/development/app-values.yaml" in dev_values
            assert "values/common/common-values.yaml" in dev_values
            assert "values/base-values.yaml" in dev_values

            # Production 프로파일 테스트
            prod_config_loaded = pm.load_profile("production")
            prod_values = prod_config_loaded["apps"][0]["specs"]["values"]

            assert "values/production/app-values.yaml" in prod_values
            assert "values/common/common-values.yaml" in prod_values
            assert "values/base-values.yaml" in prod_values

    def test_profile_config_deep_merge(self):
        """프로파일 설정 딥 머지 테스트"""
        with tempfile.TemporaryDirectory() as tmpdir:
            config_dir = Path(tmpdir) / "config"
            config_dir.mkdir()

            # 복잡한 설정 구조
            base_config = {
                "namespace": "default",
                "apps": [
                    {
                        "name": "web-app",
                        "type": "install-helm",
                        "specs": {
                            "path": "web-chart",
                            "values": ["web-values.yaml"],
                            "helm": {"timeout": "5m", "wait": True},
                        },
                    },
                    {
                        "name": "api-app",
                        "type": "install-helm",
                        "specs": {"path": "api-chart", "values": ["api-values.yaml"]},
                    },
                ],
                "global": {
                    "image": {"registry": "docker.io", "tag": "latest"},
                    "resources": {"limits": {"memory": "512Mi"}},
                },
            }

            # Production 오버라이드
            prod_config = {
                "namespace": "production",
                "apps": [{"name": "web-app", "specs": {"helm": {"timeout": "10m"}}}],
                "global": {
                    "image": {"tag": "v1.2.3"},
                    "resources": {
                        "limits": {"cpu": "1000m"},
                        "requests": {"memory": "256Mi"},
                    },
                },
            }

            with open(config_dir / "config.yaml", "w") as f:
                yaml.dump(base_config, f)

            with open(config_dir / "config-production.yaml", "w") as f:
                yaml.dump(prod_config, f)

            # ProfileManager로 프로파일 로드
            pm = ProfileManager(tmpdir, "config")
            merged_config = pm.load_profile("production")

            # 병합 결과 검증
            assert merged_config["namespace"] == "production"

            # apps 배열 병합 확인
            web_app = merged_config["apps"][0]
            assert web_app["name"] == "web-app"
            assert web_app["specs"]["helm"]["timeout"] == "10m"  # 오버라이드됨
            assert web_app["specs"]["helm"]["wait"]  # 유지됨
            assert web_app["specs"]["values"] == ["web-values.yaml"]  # 유지됨

            api_app = merged_config["apps"][1]
            assert api_app["name"] == "api-app"  # 두 번째 앱 유지됨

            # global 설정 딥 머지 확인
            global_config = merged_config["global"]
            assert global_config["image"]["registry"] == "docker.io"  # 유지됨
            assert global_config["image"]["tag"] == "v1.2.3"  # 오버라이드됨
            assert global_config["resources"]["limits"]["memory"] == "512Mi"  # 유지됨
            assert global_config["resources"]["limits"]["cpu"] == "1000m"  # 추가됨
            assert global_config["resources"]["requests"]["memory"] == "256Mi"  # 추가됨

    def test_profile_list_command_integration(self):
        """프로파일 목록 조회 통합 테스트"""
        runner = CliRunner()

        with runner.isolated_filesystem():
            # 프로젝트 초기화
            init_result = runner.invoke(
                main, ["init", "--name", "list-test", "--non-interactive"]
            )
            assert init_result.exit_code == 0

            # ProfileManager로 프로파일 목록 확인
            pm = ProfileManager(".", "config")
            profiles = pm.list_profiles()

            # 프로파일이 올바르게 생성되었는지 확인
            assert len(profiles) == 3  # development, staging, production

            for profile in profiles:
                assert profile["valid"]
                assert profile["errors"] == 0
                assert profile["apps_count"] == 1
                assert "list-test" in profile["namespace"]
