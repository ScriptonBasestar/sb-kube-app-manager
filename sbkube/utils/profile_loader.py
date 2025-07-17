import os
from typing import Any

from sbkube.utils.logger import logger
from sbkube.utils.profile_manager import ConfigPriority, ProfileManager


class ProfileLoader:
    """프로파일 로딩과 CLI 통합을 위한 헬퍼 클래스"""

    def __init__(self, base_dir: str = None):
        self.base_dir = base_dir or os.getcwd()
        self.profile_manager = ProfileManager(self.base_dir, "config")

    def load_with_overrides(
        self,
        profile_name: str = None,
        cli_overrides: dict[str, Any] = None,
        env_overrides: dict[str, Any] = None,
    ) -> dict[str, Any]:
        """프로파일과 오버라이드를 적용한 최종 설정 로드"""

        # 기본 설정 로드
        base_config = self.profile_manager.load_profile(profile_name)

        # 환경변수 오버라이드 수집
        if env_overrides is None:
            env_overrides = self._collect_env_overrides()

        # 우선순위 적용
        final_config = ConfigPriority.apply_overrides(
            base_config=base_config,
            env_overrides=env_overrides,
            cli_overrides=cli_overrides or {},
        )

        logger.verbose(f"프로파일 '{profile_name or 'default'}' 로드 완료")
        return final_config

    def _collect_env_overrides(self) -> dict[str, Any]:
        """환경변수에서 설정 오버라이드 수집"""
        overrides = {}

        # SBKUBE_ 접두사를 가진 환경변수 수집
        for key, value in os.environ.items():
            if key.startswith("SBKUBE_"):
                config_key = key[7:].lower()  # SBKUBE_ 제거 후 소문자 변환

                # 점으로 구분된 경로를 중첩 딕셔너리로 변환
                keys = config_key.split("_")
                current = overrides

                for k in keys[:-1]:
                    if k not in current:
                        current[k] = {}
                    current = current[k]

                # 값 타입 추론
                current[keys[-1]] = self._parse_env_value(value)

        return overrides

    def _parse_env_value(self, value: str) -> Any:
        """환경변수 값의 타입 파싱"""
        # 불린 값
        if value.lower() in ("true", "false"):
            return value.lower() == "true"

        # 숫자 값
        try:
            if "." in value:
                return float(value)
            return int(value)
        except ValueError:
            pass

        # 리스트 값 (쉼표로 구분)
        if "," in value:
            return [item.strip() for item in value.split(",")]

        # 문자열 값
        return value

    def validate_and_load(self, profile_name: str = None) -> dict[str, Any]:
        """프로파일 검증 후 로드"""
        if profile_name:
            validation = self.profile_manager.validate_profile(profile_name)
            if not validation["valid"]:
                logger.error(f"프로파일 '{profile_name}' 검증 실패:")
                for error in validation["errors"]:
                    logger.error(f"  - {error}")
                raise ValueError(f"Invalid profile: {profile_name}")

            if validation["warnings"]:
                for warning in validation["warnings"]:
                    logger.warning(f"  ⚠️  {warning}")

        return self.load_with_overrides(profile_name)

    def list_available_profiles(self) -> list[dict[str, Any]]:
        """사용 가능한 프로파일 목록 반환"""
        return self.profile_manager.list_profiles()

    def get_profile_from_env(self) -> str | None:
        """환경변수에서 기본 프로파일 가져오기"""
        return os.environ.get("SBKUBE_PROFILE")

    def get_cli_defaults(self) -> dict[str, Any]:
        """환경변수에서 CLI 기본값 가져오기"""
        env_defaults = {
            "SBKUBE_PROFILE": "profile",
            "SBKUBE_NAMESPACE": "namespace",
            "SBKUBE_DEBUG": "debug",
            "SBKUBE_VERBOSE": "verbose",
            "SBKUBE_CONFIG_DIR": "config_dir",
        }

        defaults = {}
        for env_var, config_key in env_defaults.items():
            value = os.environ.get(env_var)
            if value:
                defaults[config_key] = self._parse_env_value(value)

        return defaults
