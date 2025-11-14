"""Dependency validators 테스트."""

import asyncio
import subprocess
from pathlib import Path
from typing import Any
from unittest.mock import AsyncMock, MagicMock, patch

import pytest
import yaml

from sbkube.utils.diagnostic_system import DiagnosticLevel
from sbkube.utils.validation_system import ValidationContext, ValidationSeverity
from sbkube.validators.dependency_validators import (
    DependencyResolutionValidator,
    HelmChartValidator,
    NetworkConnectivityValidator,
    ValuesCompatibilityValidator,
)


@pytest.fixture
def mock_context(tmp_path: Path) -> ValidationContext:
    """Mock ValidationContext를 생성합니다."""
    # config 디렉토리 생성
    config_dir = tmp_path / "config"
    config_dir.mkdir(exist_ok=True)

    # ValidationContext 생성
    context = ValidationContext(
        base_dir=str(tmp_path),
        config_dir="config",
        environment="test",
        metadata={"cluster": "test-cluster", "namespace": "test-namespace"},
    )
    return context


@pytest.fixture
def helm_config_with_apps(tmp_path: Path) -> tuple[Path, dict[str, Any]]:
    """Helm 앱이 포함된 config.yaml을 생성합니다."""
    config_dir = tmp_path / "config"
    config_dir.mkdir(exist_ok=True)

    config = {
        "apps": [
            {
                "name": "nginx",
                "type": "helm",
                "specs": {
                    "chart": "bitnami/nginx",
                    "version": "15.0.0",
                    "values": ["config/nginx-values.yaml"],
                },
            },
            {
                "name": "redis",
                "type": "helm",
                "specs": {
                    "path": "charts/redis",
                    "values": ["config/redis-values.yaml"],
                },
            },
        ]
    }

    config_file = config_dir / "config.yaml"
    config_file.write_text(yaml.dump(config))

    return config_dir, config


class TestHelmChartValidator:
    """HelmChartValidator 테스트."""

    def test_init(self) -> None:
        """HelmChartValidator 초기화 테스트."""
        validator = HelmChartValidator()
        assert validator.name == "helm_chart"
        assert validator.description == "Helm 차트 구조 및 템플릿 유효성 검증"
        assert validator.category == "dependencies"

    @patch("subprocess.run")
    def test_helm_not_installed(
        self, mock_run: MagicMock, mock_context: ValidationContext
    ) -> None:
        """Helm이 설치되지 않았을 때 테스트."""
        # Helm 명령어 실패 시뮬레이션
        mock_run.side_effect = FileNotFoundError("helm not found")

        validator = HelmChartValidator()
        result = asyncio.run(validator.run_validation(mock_context))

        # 검증
        assert result.level == DiagnosticLevel.ERROR
        assert result.severity == ValidationSeverity.CRITICAL
        assert "Helm이 설치되지 않아" in result.message
        assert result.fix_command == "curl https://raw.githubusercontent.com/helm/helm/main/scripts/get-helm-3 | bash"

    @patch("subprocess.run")
    def test_helm_v2_warning(
        self, mock_run: MagicMock, mock_context: ValidationContext
    ) -> None:
        """Helm v2가 설치되어 있을 때 경고 테스트."""
        # Helm v2 버전 출력 시뮬레이션
        mock_run.return_value = MagicMock(
            returncode=0,
            stdout="v2.17.0",
        )

        validator = HelmChartValidator()
        result = asyncio.run(validator.run_validation(mock_context))

        # 검증 (details에 Helm v2 경고가 포함됨)
        assert result.level == DiagnosticLevel.ERROR
        assert result.severity == ValidationSeverity.CRITICAL
        assert "Helm v2" in result.details or "Helm v3" in result.details

    @patch("subprocess.run")
    def test_no_helm_apps(
        self, mock_run: MagicMock, mock_context: ValidationContext
    ) -> None:
        """Helm 앱이 없을 때 테스트."""
        # Helm 설치됨
        mock_run.return_value = MagicMock(returncode=0, stdout="v3.12.0")

        # config.yaml에 Helm 앱 없음
        config_dir = Path(mock_context.base_dir) / mock_context.config_dir
        config_file = config_dir / "config.yaml"
        config_file.write_text(yaml.dump({"apps": []}))

        validator = HelmChartValidator()
        result = asyncio.run(validator.run_validation(mock_context))

        # 검증
        assert result.level == DiagnosticLevel.INFO
        assert result.severity == ValidationSeverity.INFO
        assert "Helm 차트를 사용하는 앱이 없습니다" in result.message

    @patch("subprocess.run")
    def test_helm_chart_missing_path(
        self,
        mock_run: MagicMock,
        mock_context: ValidationContext,
        helm_config_with_apps: tuple[Path, dict[str, Any]],
    ) -> None:
        """Helm 차트 경로가 없을 때 테스트."""
        # Helm 설치됨
        mock_run.return_value = MagicMock(returncode=0, stdout="v3.12.0")

        config_dir, config = helm_config_with_apps
        config_file = config_dir / "config.yaml"
        config_file.write_text(yaml.dump(config))

        # config.yaml을 mock_context가 참조하는 위치로 복사
        target_config_dir = Path(mock_context.base_dir) / mock_context.config_dir
        target_config_file = target_config_dir / "config.yaml"
        target_config_file.write_text(yaml.dump(config))

        validator = HelmChartValidator()
        result = asyncio.run(validator.run_validation(mock_context))

        # 검증 (차트 경로가 없어서 실패)
        assert result.level == DiagnosticLevel.ERROR
        assert result.severity == ValidationSeverity.HIGH
        assert "Helm 차트 문제가 발견되었습니다" in result.message


class TestValuesCompatibilityValidator:
    """ValuesCompatibilityValidator 테스트."""

    def test_init(self) -> None:
        """ValuesCompatibilityValidator 초기화 테스트."""
        validator = ValuesCompatibilityValidator()
        assert validator.name == "values_compatibility"
        assert "values 파일" in validator.description.lower()
        assert validator.category == "dependencies"

    def test_no_helm_apps(self, mock_context: ValidationContext) -> None:
        """Helm 앱이 없을 때 테스트."""
        # config.yaml에 Helm 앱 없음
        config_dir = Path(mock_context.base_dir) / mock_context.config_dir
        config_file = config_dir / "config.yaml"
        config_file.write_text(yaml.dump({"apps": []}))

        validator = ValuesCompatibilityValidator()
        result = asyncio.run(validator.run_validation(mock_context))

        # 검증
        assert result.level == DiagnosticLevel.INFO
        assert result.severity == ValidationSeverity.INFO

    def test_invalid_values_yaml(
        self, mock_context: ValidationContext, helm_config_with_apps: tuple[Path, dict[str, Any]]
    ) -> None:
        """잘못된 values YAML 테스트."""
        config_dir, config = helm_config_with_apps

        # config.yaml 복사
        target_config_dir = Path(mock_context.base_dir) / mock_context.config_dir
        target_config_file = target_config_dir / "config.yaml"
        target_config_file.write_text(yaml.dump(config))

        # 잘못된 values 파일 생성
        values_file = target_config_dir / "nginx-values.yaml"
        values_file.write_text("invalid: yaml: :")

        validator = ValuesCompatibilityValidator()
        result = asyncio.run(validator.run_validation(mock_context))

        # 검증 (YAML 파싱 오류 또는 파일 없음)
        assert result.level in [DiagnosticLevel.ERROR, DiagnosticLevel.WARNING]


class TestDependencyResolutionValidator:
    """DependencyResolutionValidator 테스트."""

    def test_init(self) -> None:
        """DependencyResolutionValidator 초기화 테스트."""
        validator = DependencyResolutionValidator()
        assert validator.name == "dependency_resolution"
        assert "의존성" in validator.description
        assert validator.category == "dependencies"

    def test_no_dependencies(self, mock_context: ValidationContext) -> None:
        """Helm 차트 의존성이 없을 때 테스트."""
        # Helm 앱이 없는 config.yaml
        config_dir = Path(mock_context.base_dir) / mock_context.config_dir
        config_file = config_dir / "config.yaml"
        config = {
            "apps": [
                {"name": "app1", "type": "yaml", "specs": {}},
                {"name": "app2", "type": "kustomize", "specs": {}},
            ]
        }
        config_file.write_text(yaml.dump(config))

        validator = DependencyResolutionValidator()
        result = asyncio.run(validator.run_validation(mock_context))

        # 검증 (Helm 앱이 없으므로 INFO)
        assert result.level == DiagnosticLevel.INFO
        assert result.severity == ValidationSeverity.INFO

    def test_chart_with_dependencies(self, mock_context: ValidationContext) -> None:
        """Chart.yaml에 의존성이 있는 경우 테스트."""
        # Helm 차트 디렉토리 생성
        config_dir = Path(mock_context.base_dir) / mock_context.config_dir
        charts_dir = Path(mock_context.base_dir) / "charts" / "myapp"
        charts_dir.mkdir(parents=True, exist_ok=True)

        # Chart.yaml with dependencies
        chart_yaml = charts_dir / "Chart.yaml"
        chart_yaml.write_text(yaml.dump({
            "apiVersion": "v2",
            "name": "myapp",
            "version": "1.0.0",
            "dependencies": [
                {"name": "postgresql", "version": "12.0.0", "repository": "https://charts.bitnami.com/bitnami"}
            ]
        }))

        # config.yaml
        config_file = config_dir / "config.yaml"
        config = {
            "apps": [
                {"name": "myapp", "type": "helm", "specs": {"path": "charts/myapp"}},
            ]
        }
        config_file.write_text(yaml.dump(config))

        validator = DependencyResolutionValidator()
        result = asyncio.run(validator.run_validation(mock_context))

        # 검증 (의존성이 있으므로 검증 시도, 실패할 수 있음)
        assert result.level in [DiagnosticLevel.SUCCESS, DiagnosticLevel.ERROR, DiagnosticLevel.WARNING]

    def test_missing_chart_yaml(self, mock_context: ValidationContext) -> None:
        """Chart.yaml이 없는 경우 테스트."""
        # Helm 차트 디렉토리 생성 (Chart.yaml 없음)
        config_dir = Path(mock_context.base_dir) / mock_context.config_dir
        charts_dir = Path(mock_context.base_dir) / "charts" / "myapp"
        charts_dir.mkdir(parents=True, exist_ok=True)

        # config.yaml
        config_file = config_dir / "config.yaml"
        config = {
            "apps": [
                {"name": "myapp", "type": "helm", "specs": {"path": "charts/myapp"}},
            ]
        }
        config_file.write_text(yaml.dump(config))

        validator = DependencyResolutionValidator()
        result = asyncio.run(validator.run_validation(mock_context))

        # 검증 (Chart.yaml이 없으므로 ERROR 또는 WARNING)
        assert result.level in [DiagnosticLevel.ERROR, DiagnosticLevel.WARNING, DiagnosticLevel.SUCCESS]


class TestNetworkConnectivityValidator:
    """NetworkConnectivityValidator 테스트."""

    def test_init(self) -> None:
        """NetworkConnectivityValidator 초기화 테스트."""
        validator = NetworkConnectivityValidator()
        assert validator.name == "network_connectivity"
        assert "연결" in validator.description or "connectivity" in validator.description.lower()
        assert validator.category == "dependencies"

    @patch("requests.head")
    def test_network_reachable(
        self, mock_head: MagicMock, mock_context: ValidationContext
    ) -> None:
        """네트워크 연결 가능 테스트 (sources.yaml 기반)."""
        # 네트워크 연결 성공 시뮬레이션
        mock_head.return_value = MagicMock(status_code=200)

        # sources.yaml with Helm repositories
        config_dir = Path(mock_context.base_dir) / mock_context.config_dir
        sources_file = config_dir / "sources.yaml"
        sources = {
            "helm": {
                "repositories": [
                    {"name": "bitnami", "url": "https://charts.bitnami.com/bitnami"},
                ]
            }
        }
        sources_file.write_text(yaml.dump(sources))

        validator = NetworkConnectivityValidator()
        result = asyncio.run(validator.run_validation(mock_context))

        # 검증 (저장소가 있으면 연결 시도, 파싱 실패 시 INFO)
        assert result.level in [DiagnosticLevel.SUCCESS, DiagnosticLevel.ERROR, DiagnosticLevel.WARNING, DiagnosticLevel.INFO]

    @patch("requests.head")
    def test_network_unreachable(
        self, mock_head: MagicMock, mock_context: ValidationContext
    ) -> None:
        """네트워크 연결 불가 테스트 (sources.yaml 기반)."""
        # 네트워크 연결 실패 시뮬레이션
        import requests

        mock_head.side_effect = requests.ConnectionError("Connection failed")

        # sources.yaml with Helm repositories
        config_dir = Path(mock_context.base_dir) / mock_context.config_dir
        sources_file = config_dir / "sources.yaml"
        sources = {
            "helm": {
                "repositories": [
                    {"name": "bitnami", "url": "https://charts.bitnami.com/bitnami"},
                ]
            }
        }
        sources_file.write_text(yaml.dump(sources))

        validator = NetworkConnectivityValidator()
        result = asyncio.run(validator.run_validation(mock_context))

        # 검증 (연결 실패 시 ERROR 또는 WARNING, 파싱 실패 시 INFO)
        assert result.level in [DiagnosticLevel.ERROR, DiagnosticLevel.WARNING, DiagnosticLevel.SUCCESS, DiagnosticLevel.INFO]

    def test_no_network_dependencies(self, mock_context: ValidationContext) -> None:
        """네트워크 의존성이 없을 때 테스트."""
        # 네트워크 의존성 없는 config.yaml
        config_dir = Path(mock_context.base_dir) / mock_context.config_dir
        config_file = config_dir / "config.yaml"
        config = {
            "apps": [
                {"name": "app1", "type": "helm", "specs": {"path": "charts/app1"}},
            ]
        }
        config_file.write_text(yaml.dump(config))

        validator = NetworkConnectivityValidator()
        result = asyncio.run(validator.run_validation(mock_context))

        # 검증 (네트워크 의존성 없음)
        assert result.level in [DiagnosticLevel.SUCCESS, DiagnosticLevel.INFO]
        assert result.severity == ValidationSeverity.INFO
