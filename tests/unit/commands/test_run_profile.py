import tempfile
from pathlib import Path
from unittest.mock import patch

import pytest
import yaml

from sbkube.commands.run import RunCommand, RunExecutionError


class TestRunProfile:
    def test_run_with_profile(self):
        """프로파일을 사용한 run 명령어 테스트"""
        with tempfile.TemporaryDirectory() as tmpdir:
            self._create_test_configs(tmpdir)

            # ProfileManager의 메서드들을 모킹
            with patch("sbkube.commands.run.ProfileManager") as mock_pm_class:
                mock_pm = mock_pm_class.return_value
                mock_pm.available_profiles = ["development", "production"]
                mock_pm.validate_profile.return_value = {
                    "valid": True,
                    "errors": [],
                    "warnings": [],
                }
                mock_pm.load_profile.return_value = {
                    "namespace": "dev",
                    "apps": [{"name": "test-app"}],
                }

                # 실제 단계 실행을 모킹
                with patch.object(RunCommand, "_execute_step"):
                    cmd = RunCommand(
                        base_dir=tmpdir,
                        app_config_dir="config",
                        profile="development",
                        dry_run=True,  # dry_run으로 실제 실행 방지
                    )

                    cmd.execute()

                    # ProfileManager가 올바르게 호출되었는지 확인
                    mock_pm_class.assert_called_once_with(
                        Path(tmpdir), Path(tmpdir) / "config"
                    )
                    mock_pm.validate_profile.assert_called_once_with("development")
                    mock_pm.load_profile.assert_called_once_with("development")

    def test_run_with_invalid_profile(self):
        """존재하지 않는 프로파일로 run 실행 테스트"""
        with tempfile.TemporaryDirectory() as tmpdir:
            self._create_test_configs(tmpdir)

            with patch("sbkube.commands.run.ProfileManager") as mock_pm_class:
                mock_pm = mock_pm_class.return_value
                mock_pm.available_profiles = ["development", "production"]

                cmd = RunCommand(
                    base_dir=tmpdir, app_config_dir="config", profile="nonexistent"
                )

                with pytest.raises(RunExecutionError, match="프로파일 로딩 실패"):
                    cmd.execute()

    def test_run_with_invalid_profile_config(self):
        """잘못된 프로파일 설정으로 run 실행 테스트"""
        with tempfile.TemporaryDirectory() as tmpdir:
            self._create_test_configs(tmpdir)

            with patch("sbkube.commands.run.ProfileManager") as mock_pm_class:
                mock_pm = mock_pm_class.return_value
                mock_pm.available_profiles = ["development"]
                mock_pm.validate_profile.return_value = {
                    "valid": False,
                    "errors": ["namespace is required"],
                    "warnings": [],
                }

                cmd = RunCommand(
                    base_dir=tmpdir, app_config_dir="config", profile="development"
                )

                with pytest.raises(RunExecutionError, match="프로파일 검증 실패"):
                    cmd.execute()

    def test_run_with_profile_warnings(self):
        """프로파일 경고가 있는 경우 테스트"""
        with tempfile.TemporaryDirectory() as tmpdir:
            self._create_test_configs(tmpdir)

            with patch("sbkube.commands.run.ProfileManager") as mock_pm_class:
                mock_pm = mock_pm_class.return_value
                mock_pm.available_profiles = ["development"]
                mock_pm.validate_profile.return_value = {
                    "valid": True,
                    "errors": [],
                    "warnings": ["no apps defined"],
                }
                mock_pm.load_profile.return_value = {"namespace": "dev", "apps": []}

                with patch("sbkube.utils.logger.logger") as mock_logger:
                    cmd = RunCommand(
                        base_dir=tmpdir,
                        app_config_dir="config",
                        profile="development",
                        dry_run=True,
                    )

                    cmd.execute()

                    # 경고 메시지가 출력되었는지 확인
                    mock_logger.warning.assert_called_with(
                        "⚠️  프로파일 경고: no apps defined"
                    )

    def test_run_without_profile(self):
        """프로파일 없이 run 실행 테스트"""
        with tempfile.TemporaryDirectory() as tmpdir:
            self._create_test_configs(tmpdir)

            with patch.object(RunCommand, "_execute_step"):
                cmd = RunCommand(base_dir=tmpdir, app_config_dir="config", dry_run=True)

                cmd.execute()

                # _load_profile이 호출되지 않았는지 확인
                assert cmd.profile is None

    def test_profile_config_file_override(self):
        """프로파일 사용 시 config 파일 경로 오버라이드 테스트"""
        with tempfile.TemporaryDirectory() as tmpdir:
            self._create_test_configs(tmpdir)

            with patch("sbkube.commands.run.ProfileManager") as mock_pm_class:
                mock_pm = mock_pm_class.return_value
                mock_pm.available_profiles = ["development"]
                mock_pm.validate_profile.return_value = {
                    "valid": True,
                    "errors": [],
                    "warnings": [],
                }
                mock_pm.load_profile.return_value = {
                    "namespace": "dev",
                    "apps": [{"name": "test-app"}],
                }

                cmd = RunCommand(
                    base_dir=tmpdir,
                    app_config_dir="config",
                    profile="development",
                    dry_run=True,
                )

                cmd.execute()

                # config_file_name이 프로파일에 맞게 설정되었는지 확인
                assert cmd.config_file_name == "config-development.yaml"

    def test_profile_with_explicit_config_file(self):
        """프로파일과 명시적 config 파일이 함께 지정된 경우 테스트"""
        with tempfile.TemporaryDirectory() as tmpdir:
            self._create_test_configs(tmpdir)

            with patch("sbkube.commands.run.ProfileManager") as mock_pm_class:
                mock_pm = mock_pm_class.return_value
                mock_pm.available_profiles = ["development"]
                mock_pm.validate_profile.return_value = {
                    "valid": True,
                    "errors": [],
                    "warnings": [],
                }
                mock_pm.load_profile.return_value = {
                    "namespace": "dev",
                    "apps": [{"name": "test-app"}],
                }

                cmd = RunCommand(
                    base_dir=tmpdir,
                    app_config_dir="config",
                    config_file_name="custom-config.yaml",
                    profile="development",
                    dry_run=True,
                )

                cmd.execute()

                # 명시적으로 지정된 config 파일이 유지되는지 확인
                assert cmd.config_file_name == "custom-config.yaml"

    def _create_test_configs(self, tmpdir):
        """테스트용 설정 파일 생성"""
        config_dir = Path(tmpdir) / "config"
        config_dir.mkdir()

        base_config = {
            "namespace": "default",
            "apps": [
                {
                    "name": "test-app",
                    "type": "install-helm",
                    "specs": {"path": "test-chart"},
                }
            ],
        }

        dev_config = {
            "namespace": "dev",
            "apps": [{"name": "test-app", "specs": {"replicas": 1}}],
        }

        with open(config_dir / "config.yaml", "w") as f:
            yaml.dump(base_config, f)

        with open(config_dir / "config-development.yaml", "w") as f:
            yaml.dump(dev_config, f)
