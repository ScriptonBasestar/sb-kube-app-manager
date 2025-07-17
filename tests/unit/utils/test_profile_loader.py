import os
import tempfile
from pathlib import Path
from unittest.mock import patch

import pytest
import yaml

from sbkube.utils.profile_loader import ProfileLoader


class TestProfileLoader:
    def test_load_with_cli_overrides(self):
        """CLI 오버라이드 적용 테스트"""
        with tempfile.TemporaryDirectory() as tmpdir:
            self._create_test_profile(tmpdir)

            loader = ProfileLoader(tmpdir)
            config = loader.load_with_overrides(
                profile_name="development", cli_overrides={"namespace": "override-ns"}
            )

            assert config["namespace"] == "override-ns"

    def test_load_with_env_overrides(self):
        """환경변수 오버라이드 적용 테스트"""
        with tempfile.TemporaryDirectory() as tmpdir:
            self._create_test_profile(tmpdir)

            loader = ProfileLoader(tmpdir)
            config = loader.load_with_overrides(
                profile_name="development", env_overrides={"namespace": "env-namespace"}
            )

            assert config["namespace"] == "env-namespace"

    def test_env_override_collection(self):
        """환경변수 오버라이드 수집 테스트"""
        loader = ProfileLoader(".")

        # 환경변수 설정
        os.environ["SBKUBE_NAMESPACE"] = "env-namespace"
        os.environ["SBKUBE_DEBUG"] = "true"
        os.environ["SBKUBE_REPLICAS"] = "3"

        try:
            overrides = loader._collect_env_overrides()
            assert overrides["namespace"] == "env-namespace"
            assert overrides["debug"] is True
            assert overrides["replicas"] == 3

        finally:
            # 환경변수 정리
            os.environ.pop("SBKUBE_NAMESPACE", None)
            os.environ.pop("SBKUBE_DEBUG", None)
            os.environ.pop("SBKUBE_REPLICAS", None)

    def test_nested_env_override_collection(self):
        """중첩된 환경변수 오버라이드 수집 테스트"""
        loader = ProfileLoader(".")

        # 중첩된 환경변수 설정
        os.environ["SBKUBE_APPS_WEB_REPLICAS"] = "5"
        os.environ["SBKUBE_GLOBAL_IMAGE_TAG"] = "v1.2.3"

        try:
            overrides = loader._collect_env_overrides()
            assert overrides["apps"]["web"]["replicas"] == 5
            assert overrides["global"]["image"]["tag"] == "v1.2.3"

        finally:
            # 환경변수 정리
            os.environ.pop("SBKUBE_APPS_WEB_REPLICAS", None)
            os.environ.pop("SBKUBE_GLOBAL_IMAGE_TAG", None)

    def test_parse_env_value_types(self):
        """환경변수 값 타입 파싱 테스트"""
        loader = ProfileLoader(".")

        # 불린 값
        assert loader._parse_env_value("true") is True
        assert loader._parse_env_value("false") is False
        assert loader._parse_env_value("TRUE") is True
        assert loader._parse_env_value("False") is False

        # 숫자 값
        assert loader._parse_env_value("42") == 42
        assert loader._parse_env_value("3.14") == 3.14

        # 리스트 값
        assert loader._parse_env_value("a,b,c") == ["a", "b", "c"]
        assert loader._parse_env_value("  x , y , z  ") == ["x", "y", "z"]

        # 문자열 값
        assert loader._parse_env_value("hello") == "hello"
        assert loader._parse_env_value("") == ""

    def test_validate_and_load_valid_profile(self):
        """유효한 프로파일 검증 및 로드 테스트"""
        with tempfile.TemporaryDirectory() as tmpdir:
            self._create_test_profile(tmpdir)

            loader = ProfileLoader(tmpdir)
            config = loader.validate_and_load("development")

            assert config["namespace"] == "dev"
            assert config["apps"][0]["name"] == "test-app"

    def test_validate_and_load_invalid_profile(self):
        """잘못된 프로파일 검증 테스트"""
        with tempfile.TemporaryDirectory() as tmpdir:
            config_dir = Path(tmpdir) / "config"
            config_dir.mkdir()

            # 잘못된 설정 파일 (namespace 없음)
            invalid_config = {
                "apps": [
                    {
                        "name": "test-app",
                        "type": "install-helm",
                        # specs.path 없음
                    }
                ]
            }

            with open(config_dir / "config.yaml", "w") as f:
                yaml.dump(invalid_config, f)

            with open(config_dir / "config-invalid.yaml", "w") as f:
                yaml.dump({}, f)

            loader = ProfileLoader(tmpdir)

            with pytest.raises(ValueError, match="Invalid profile"):
                loader.validate_and_load("invalid")

    def test_validate_and_load_with_warnings(self):
        """경고가 있는 프로파일 검증 테스트"""
        with tempfile.TemporaryDirectory() as tmpdir:
            config_dir = Path(tmpdir) / "config"
            config_dir.mkdir()

            # 경고가 있는 설정 (앱이 없음)
            config_with_warnings = {
                "namespace": "test",
                "apps": [],  # 앱이 없어서 경고 발생
            }

            with open(config_dir / "config.yaml", "w") as f:
                yaml.dump(config_with_warnings, f)

            with open(config_dir / "config-warning.yaml", "w") as f:
                yaml.dump({}, f)

            loader = ProfileLoader(tmpdir)

            with patch("sbkube.utils.logger.logger") as mock_logger:
                config = loader.validate_and_load("warning")

                # 경고 메시지가 출력되었는지 확인
                mock_logger.warning.assert_called()
                assert config["namespace"] == "test"

    def test_list_available_profiles(self):
        """사용 가능한 프로파일 목록 테스트"""
        with tempfile.TemporaryDirectory() as tmpdir:
            self._create_test_profile(tmpdir)

            loader = ProfileLoader(tmpdir)
            profiles = loader.list_available_profiles()

            assert len(profiles) == 1
            assert profiles[0]["name"] == "development"
            assert profiles[0]["namespace"] == "dev"
            assert profiles[0]["valid"]

    def test_get_profile_from_env(self):
        """환경변수에서 프로파일 이름 가져오기 테스트"""
        loader = ProfileLoader(".")

        # 환경변수 설정
        os.environ["SBKUBE_PROFILE"] = "production"

        try:
            profile = loader.get_profile_from_env()
            assert profile == "production"

        finally:
            os.environ.pop("SBKUBE_PROFILE", None)

    def test_get_profile_from_env_not_set(self):
        """환경변수에 프로파일이 설정되지 않은 경우 테스트"""
        loader = ProfileLoader(".")

        # 환경변수가 설정되지 않은 상태에서 테스트
        os.environ.pop("SBKUBE_PROFILE", None)

        profile = loader.get_profile_from_env()
        assert profile is None

    def test_get_cli_defaults(self):
        """환경변수에서 CLI 기본값 가져오기 테스트"""
        loader = ProfileLoader(".")

        # 환경변수 설정
        os.environ["SBKUBE_PROFILE"] = "development"
        os.environ["SBKUBE_NAMESPACE"] = "default-ns"
        os.environ["SBKUBE_DEBUG"] = "true"
        os.environ["SBKUBE_VERBOSE"] = "false"

        try:
            defaults = loader.get_cli_defaults()

            assert defaults["profile"] == "development"
            assert defaults["namespace"] == "default-ns"
            assert defaults["debug"] is True
            assert defaults["verbose"] is False

        finally:
            # 환경변수 정리
            for var in [
                "SBKUBE_PROFILE",
                "SBKUBE_NAMESPACE",
                "SBKUBE_DEBUG",
                "SBKUBE_VERBOSE",
            ]:
                os.environ.pop(var, None)

    def test_load_with_priority_order(self):
        """우선순위 순서 테스트 (CLI > ENV > Profile > Base)"""
        with tempfile.TemporaryDirectory() as tmpdir:
            self._create_test_profile(tmpdir)

            loader = ProfileLoader(tmpdir)

            # 모든 레벨에서 namespace 설정
            config = loader.load_with_overrides(
                profile_name="development",  # namespace: dev
                env_overrides={"namespace": "env-namespace"},
                cli_overrides={"namespace": "cli-namespace"},
            )

            # CLI 오버라이드가 최고 우선순위
            assert config["namespace"] == "cli-namespace"

    def test_load_without_overrides(self):
        """오버라이드 없이 로드 테스트"""
        with tempfile.TemporaryDirectory() as tmpdir:
            self._create_test_profile(tmpdir)

            loader = ProfileLoader(tmpdir)
            config = loader.load_with_overrides(profile_name="development")

            # 프로파일 설정이 그대로 적용됨
            assert config["namespace"] == "dev"
            assert config["apps"][0]["name"] == "test-app"

    def _create_test_profile(self, tmpdir):
        """테스트용 프로파일 생성"""
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
