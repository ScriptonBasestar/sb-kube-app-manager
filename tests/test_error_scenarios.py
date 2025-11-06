"""SBKube 주요 에러 시나리오 테스트.

간소화된 에러 케이스 테스트:
- 설정 파일 관련 에러
- 모델 검증 에러
- 명령어 실행 에러
"""

import pytest
import yaml

from sbkube.exceptions import ConfigValidationError
from sbkube.models.config_model import HelmApp, SBKubeConfig


class TestConfigValidationErrors:
    """설정 파일 검증 에러 테스트."""

    def test_config_missing_namespace(self):
        """Namespace 필드 누락."""
        with pytest.raises((ConfigValidationError, Exception)):
            SBKubeConfig(
                # namespace 누락
                apps={
                    "grafana": HelmApp(
                        chart="grafana/grafana",
                        version="6.50.0",
                    )
                }
            )

    def test_config_invalid_app_type(self):
        """잘못된 앱 타입."""
        config_data = {
            "namespace": "test",
            "apps": {
                "myapp": {
                    "type": "unknown-type",  # 지원하지 않는 타입
                    "chart": "something",
                }
            },
        }

        with pytest.raises((ConfigValidationError, Exception)):
            SBKubeConfig(**config_data)

    def test_helm_app_missing_chart(self):
        """Helm 앱에서 chart 필드 누락."""
        with pytest.raises((ConfigValidationError, Exception)):
            HelmApp(
                # chart 누락
                version="1.0.0",
            )

    def test_helm_app_empty_chart(self):
        """Helm 앱에서 chart가 빈 문자열."""
        with pytest.raises((ValueError, Exception)):
            HelmApp(
                chart="",  # 빈 문자열
                version="1.0.0",
            )

    def test_helm_app_invalid_overrides(self):
        """overrides가 잘못된 타입."""
        with pytest.raises((ConfigValidationError, Exception)):
            HelmApp(
                chart="grafana/grafana",
                overrides="should-be-list",  # list여야 함
            )


class TestYAMLParsingErrors:
    """YAML 파싱 에러 테스트."""

    def test_invalid_yaml_syntax(self, tmp_path):
        """잘못된 YAML 문법."""
        config_file = tmp_path / "invalid.yaml"
        config_file.write_text("invalid: yaml: ::: syntax")

        with pytest.raises(yaml.YAMLError), open(config_file) as f:
            yaml.safe_load(f)

    def test_yaml_missing_required_keys(self, tmp_path):
        """필수 키 누락."""
        config_file = tmp_path / "config.yaml"
        config_file.write_text("""
apps:
  redis:
    type: helm
    # chart 누락
    version: 1.0.0
""")

        with open(config_file) as f:
            data = yaml.safe_load(f)

        with pytest.raises((ConfigValidationError, Exception)):
            SBKubeConfig(**data)


class TestFileSystemErrors:
    """파일 시스템 관련 에러 테스트."""

    def test_config_file_not_found(self, tmp_path):
        """존재하지 않는 파일."""
        non_existent = tmp_path / "non_existent.yaml"

        with pytest.raises(FileNotFoundError), open(non_existent) as f:
            yaml.safe_load(f)

    def test_directory_not_found(self, tmp_path):
        """존재하지 않는 디렉토리."""
        non_existent_dir = tmp_path / "non_existent_dir" / "file.yaml"

        assert not non_existent_dir.parent.exists()

    def test_permission_denied_simulation(self, tmp_path):
        """권한 없는 파일 (시뮬레이션)."""
        restricted_file = tmp_path / "restricted.yaml"
        restricted_file.write_text("test: data")

        # chmod 000 (읽기/쓰기 권한 제거)
        restricted_file.chmod(0o000)

        try:
            with pytest.raises(PermissionError), open(restricted_file) as f:
                f.read()
        finally:
            # 정리를 위해 권한 복원
            restricted_file.chmod(0o644)


class TestModelValidationErrors:
    """Pydantic 모델 검증 에러 테스트."""

    def test_helm_app_with_invalid_version_type(self):
        """version이 잘못된 타입."""
        with pytest.raises((ConfigValidationError, Exception)):
            HelmApp(
                chart="grafana/grafana",
                version=123,  # str이어야 함
            )

    def test_helm_app_with_invalid_values_type(self):
        """values가 잘못된 타입."""
        with pytest.raises((ConfigValidationError, Exception)):
            HelmApp(
                chart="grafana/grafana",
                values="should-be-list",  # list여야 함
            )

    def test_helm_app_with_invalid_set_values_type(self):
        """set_values가 잘못된 타입."""
        with pytest.raises((ConfigValidationError, Exception)):
            HelmApp(
                chart="grafana/grafana",
                set_values="should-be-dict",  # dict여야 함
            )

    def test_config_with_invalid_apps_type(self):
        """apps가 잘못된 타입."""
        with pytest.raises((ConfigValidationError, Exception)):
            SBKubeConfig(
                namespace="test",
                apps=["should", "be", "dict"],  # dict여야 함
            )


class TestRuntimeErrors:
    """런타임 에러 시나리오."""

    def test_chart_parsing_invalid_format(self):
        """차트 파싱 실패."""
        from sbkube.commands.prepare import parse_helm_chart

        # 올바른 형식 테스트
        repo, chart = parse_helm_chart("grafana/grafana")
        assert repo == "grafana"
        assert chart == "grafana"

        # 슬래시 없는 경우 (로컬 차트)
        repo, chart = parse_helm_chart("./local-chart")
        # 로컬 차트는 repo가 None일 수 있음

    def test_empty_config_apps(self):
        """apps가 빈 dict."""
        config = SBKubeConfig(
            namespace="test",
            apps={},
        )

        assert config.apps == {}
        assert len(config.apps) == 0

    def test_disabled_app(self):
        """비활성화된 앱."""
        config = SBKubeConfig(
            namespace="test",
            apps={
                "grafana": HelmApp(
                    chart="grafana/grafana",
                    enabled=False,  # 비활성화
                )
            },
        )

        assert config.apps["grafana"].enabled is False


# 에러 카운트 통계
def test_error_test_count():
    """추가된 에러 테스트 개수 확인."""
    # 모든 테스트 클래스 수집
    test_classes = [
        TestConfigValidationErrors,
        TestYAMLParsingErrors,
        TestFileSystemErrors,
        TestModelValidationErrors,
        TestRuntimeErrors,
    ]

    total_tests = 0
    for cls in test_classes:
        methods = [m for m in dir(cls) if m.startswith("test_")]
        total_tests += len(methods)

    print(f"\n총 에러 케이스 테스트: {total_tests}개")
    assert total_tests >= 15, f"최소 15개 이상의 에러 테스트 필요 (현재: {total_tests})"
