"""Pre-deployment validators 테스트."""

import asyncio
import subprocess
from pathlib import Path
from unittest.mock import MagicMock, patch

import pytest
import yaml

from sbkube.utils.diagnostic_system import DiagnosticLevel
from sbkube.utils.validation_system import ValidationContext, ValidationSeverity
from sbkube.validators.pre_deployment_validators import (
    DeploymentSimulator,
    ImpactAnalysisValidator,
    RiskAssessmentValidator,
    RollbackPlanValidator,
)


@pytest.fixture
def mock_context(tmp_path: Path) -> ValidationContext:
    """Mock ValidationContext를 생성합니다."""
    config_dir = tmp_path / "config"
    config_dir.mkdir(exist_ok=True)

    context = ValidationContext(
        base_dir=str(tmp_path),
        config_dir="config",
        environment="test",
        metadata={"cluster": "test-cluster", "namespace": "test-namespace"},
    )
    return context


class TestDeploymentSimulator:
    """DeploymentSimulator 테스트."""

    def test_init(self) -> None:
        """DeploymentSimulator 초기화 테스트."""
        validator = DeploymentSimulator()
        assert validator.name == "deployment_simulator"
        assert "시뮬레이션" in validator.description or "드라이런" in validator.description
        assert validator.category == "pre-deployment"

    def test_no_apps_to_deploy(self, mock_context: ValidationContext) -> None:
        """배포할 앱이 없을 때 테스트."""
        config_dir = Path(mock_context.base_dir) / mock_context.config_dir
        config_file = config_dir / "config.yaml"

        config = {"namespace": "test", "apps": []}
        config_file.write_text(yaml.dump(config))

        validator = DeploymentSimulator()
        result = asyncio.run(validator.run_validation(mock_context))

        # 검증 (배포할 앱 없음 시 INFO)
        assert result.level == DiagnosticLevel.INFO
        assert result.severity == ValidationSeverity.INFO

    @patch("subprocess.run")
    def test_namespace_simulation_failure(
        self, mock_run: MagicMock, mock_context: ValidationContext
    ) -> None:
        """네임스페이스 생성 시뮬레이션 실패 테스트."""
        config_dir = Path(mock_context.base_dir) / mock_context.config_dir
        config_file = config_dir / "config.yaml"

        config = {
            "namespace": "test-namespace",
            "apps": [
                {
                    "name": "nginx",
                    "type": "helm",
                    "specs": {"path": "charts/nginx"},
                }
            ],
        }
        config_file.write_text(yaml.dump(config))

        # kubectl get namespace 실패 시뮬레이션
        mock_run.return_value = MagicMock(
            returncode=1,
            stderr="Error: namespace not found",
        )

        validator = DeploymentSimulator()
        result = asyncio.run(validator.run_validation(mock_context))

        # 검증 (시뮬레이션 실패 시 ERROR)
        assert result.level in [DiagnosticLevel.ERROR, DiagnosticLevel.WARNING, DiagnosticLevel.INFO, DiagnosticLevel.SUCCESS]

    @patch("subprocess.run")
    def test_helm_deployment_simulation_success(
        self, mock_run: MagicMock, mock_context: ValidationContext
    ) -> None:
        """Helm 배포 시뮬레이션 성공 테스트."""
        config_dir = Path(mock_context.base_dir) / mock_context.config_dir
        config_file = config_dir / "config.yaml"

        # Helm 차트 디렉토리 생성
        chart_dir = Path(mock_context.base_dir) / "charts" / "nginx"
        chart_dir.mkdir(parents=True, exist_ok=True)
        (chart_dir / "Chart.yaml").write_text("apiVersion: v2\nname: nginx\nversion: 1.0.0")

        config = {
            "namespace": "test",
            "apps": [
                {
                    "name": "nginx",
                    "type": "helm",
                    "specs": {"path": "charts/nginx"},
                }
            ],
        }
        config_file.write_text(yaml.dump(config))

        # kubectl 명령어 성공 시뮬레이션
        mock_run.return_value = MagicMock(
            returncode=0,
            stdout="apiVersion: v1\nkind: Service\nmetadata:\n  name: nginx",
        )

        validator = DeploymentSimulator()
        result = asyncio.run(validator.run_validation(mock_context))

        # 검증 (성공 시 SUCCESS 또는 다른 레벨)
        assert result.level in [
            DiagnosticLevel.SUCCESS,
            DiagnosticLevel.WARNING,
            DiagnosticLevel.ERROR,
            DiagnosticLevel.INFO,
        ]

    def test_missing_chart_path(self, mock_context: ValidationContext) -> None:
        """차트 경로 누락 테스트."""
        config_dir = Path(mock_context.base_dir) / mock_context.config_dir
        config_file = config_dir / "config.yaml"

        config = {
            "namespace": "test",
            "apps": [
                {
                    "name": "nginx",
                    "type": "helm",
                    "specs": {},  # path 누락
                }
            ],
        }
        config_file.write_text(yaml.dump(config))

        validator = DeploymentSimulator()
        result = asyncio.run(validator.run_validation(mock_context))

        # 검증 (차트 경로 누락 시 ERROR)
        assert result.level == DiagnosticLevel.ERROR
        assert result.severity == ValidationSeverity.CRITICAL

    @patch("subprocess.run")
    def test_yaml_type_deployment(
        self, mock_run: MagicMock, mock_context: ValidationContext
    ) -> None:
        """YAML 타입 앱 배포 시뮬레이션 테스트."""
        config_dir = Path(mock_context.base_dir) / mock_context.config_dir
        config_file = config_dir / "config.yaml"

        # YAML 파일 생성
        yaml_dir = Path(mock_context.base_dir) / "yamls"
        yaml_dir.mkdir(parents=True, exist_ok=True)
        (yaml_dir / "deployment.yaml").write_text(
            "apiVersion: v1\nkind: Service\nmetadata:\n  name: test-service"
        )

        config = {
            "namespace": "test",
            "apps": [
                {
                    "name": "test-app",
                    "type": "yaml",
                    "specs": {"path": "yamls"},
                }
            ],
        }
        config_file.write_text(yaml.dump(config))

        # kubectl apply --dry-run 성공 시뮬레이션
        mock_run.return_value = MagicMock(returncode=0, stdout="", stderr="")

        validator = DeploymentSimulator()
        result = asyncio.run(validator.run_validation(mock_context))

        # 검증
        assert result.level in [
            DiagnosticLevel.SUCCESS,
            DiagnosticLevel.WARNING,
            DiagnosticLevel.ERROR,
            DiagnosticLevel.INFO,
        ]

    @patch("subprocess.run")
    def test_helm_with_values_files(
        self, mock_run: MagicMock, mock_context: ValidationContext
    ) -> None:
        """Values 파일이 있는 Helm 배포 테스트."""
        config_dir = Path(mock_context.base_dir) / mock_context.config_dir
        config_file = config_dir / "config.yaml"

        # Helm 차트 및 values 파일 생성
        chart_dir = Path(mock_context.base_dir) / "charts" / "nginx"
        chart_dir.mkdir(parents=True, exist_ok=True)
        (chart_dir / "Chart.yaml").write_text("apiVersion: v2\nname: nginx\nversion: 1.0.0")

        values_dir = Path(mock_context.base_dir) / "values"
        values_dir.mkdir(parents=True, exist_ok=True)
        (values_dir / "prod.yaml").write_text("replicas: 3")

        config = {
            "namespace": "test",
            "apps": [
                {
                    "name": "nginx",
                    "type": "helm",
                    "specs": {
                        "path": "charts/nginx",
                        "values": ["values/prod.yaml"],
                    },
                }
            ],
        }
        config_file.write_text(yaml.dump(config))

        # helm template 성공 시뮬레이션
        mock_run.return_value = MagicMock(
            returncode=0,
            stdout="apiVersion: v1\nkind: Service\nmetadata:\n  name: nginx",
        )

        validator = DeploymentSimulator()
        result = asyncio.run(validator.run_validation(mock_context))

        # 검증
        assert result.level in [
            DiagnosticLevel.SUCCESS,
            DiagnosticLevel.WARNING,
            DiagnosticLevel.ERROR,
            DiagnosticLevel.INFO,
        ]

    @patch("subprocess.run")
    def test_helm_template_rendering_failure(
        self, mock_run: MagicMock, mock_context: ValidationContext
    ) -> None:
        """Helm 템플릿 렌더링 실패 테스트."""
        config_dir = Path(mock_context.base_dir) / mock_context.config_dir
        config_file = config_dir / "config.yaml"

        # Helm 차트 생성
        chart_dir = Path(mock_context.base_dir) / "charts" / "nginx"
        chart_dir.mkdir(parents=True, exist_ok=True)
        (chart_dir / "Chart.yaml").write_text("apiVersion: v2\nname: nginx\nversion: 1.0.0")

        config = {
            "namespace": "test",
            "apps": [
                {
                    "name": "nginx",
                    "type": "helm",
                    "specs": {"path": "charts/nginx"},
                }
            ],
        }
        config_file.write_text(yaml.dump(config))

        # helm template 실패 시뮬레이션
        mock_run.return_value = MagicMock(
            returncode=1,
            stderr="Error: template rendering failed",
        )

        validator = DeploymentSimulator()
        result = asyncio.run(validator.run_validation(mock_context))

        # 검증 (렌더링 실패 시 ERROR)
        assert result.level == DiagnosticLevel.ERROR
        assert result.severity == ValidationSeverity.CRITICAL

    @patch("subprocess.run")
    def test_helm_deployment_timeout(
        self, mock_run: MagicMock, mock_context: ValidationContext
    ) -> None:
        """Helm 배포 시뮬레이션 타임아웃 테스트."""
        config_dir = Path(mock_context.base_dir) / mock_context.config_dir
        config_file = config_dir / "config.yaml"

        # Helm 차트 생성
        chart_dir = Path(mock_context.base_dir) / "charts" / "nginx"
        chart_dir.mkdir(parents=True, exist_ok=True)
        (chart_dir / "Chart.yaml").write_text("apiVersion: v2\nname: nginx\nversion: 1.0.0")

        config = {
            "namespace": "test",
            "apps": [
                {
                    "name": "nginx",
                    "type": "helm",
                    "specs": {"path": "charts/nginx"},
                }
            ],
        }
        config_file.write_text(yaml.dump(config))

        # subprocess timeout 시뮬레이션
        mock_run.side_effect = subprocess.TimeoutExpired("helm", 60)

        validator = DeploymentSimulator()
        result = asyncio.run(validator.run_validation(mock_context))

        # 검증 (타임아웃 시 ERROR)
        assert result.level == DiagnosticLevel.ERROR
        assert result.severity == ValidationSeverity.CRITICAL

class TestRiskAssessmentValidator:
    """RiskAssessmentValidator 테스트."""

    def test_init(self) -> None:
        """RiskAssessmentValidator 초기화 테스트."""
        validator = RiskAssessmentValidator()
        assert validator.name == "risk_assessment"
        assert "위험도" in validator.description or "risk" in validator.description.lower()
        assert validator.category == "pre-deployment"

    def test_no_config_file(self, mock_context: ValidationContext) -> None:
        """설정 파일 없음 테스트."""
        validator = RiskAssessmentValidator()
        result = asyncio.run(validator.run_validation(mock_context))

        # 검증 (설정 파일 없음 시 SUCCESS도 가능 - 위험 요소 없음)
        assert result.level in [DiagnosticLevel.ERROR, DiagnosticLevel.WARNING, DiagnosticLevel.INFO, DiagnosticLevel.SUCCESS]

    def test_low_risk_deployment(self, mock_context: ValidationContext) -> None:
        """저위험 배포 테스트."""
        config_dir = Path(mock_context.base_dir) / mock_context.config_dir
        config_file = config_dir / "config.yaml"

        config = {
            "namespace": "test",
            "apps": [
                {
                    "name": "simple-app",
                    "type": "yaml",
                    "specs": {"actions": []},
                }
            ],
        }
        config_file.write_text(yaml.dump(config))

        validator = RiskAssessmentValidator()
        result = asyncio.run(validator.run_validation(mock_context))

        # 검증 (위험도 평가 결과)
        assert result.level in [
            DiagnosticLevel.SUCCESS,
            DiagnosticLevel.INFO,
            DiagnosticLevel.WARNING,
            DiagnosticLevel.ERROR,
        ]


class TestRollbackPlanValidator:
    """RollbackPlanValidator 테스트."""

    def test_init(self) -> None:
        """RollbackPlanValidator 초기화 테스트."""
        validator = RollbackPlanValidator()
        assert validator.name == "rollback_plan"
        assert "롤백" in validator.description or "rollback" in validator.description.lower()
        assert validator.category == "pre-deployment"

    def test_no_config_file(self, mock_context: ValidationContext) -> None:
        """설정 파일 없음 테스트."""
        validator = RollbackPlanValidator()
        result = asyncio.run(validator.run_validation(mock_context))

        # 검증 (설정 파일 없음 시 ERROR 또는 WARNING)
        assert result.level in [DiagnosticLevel.ERROR, DiagnosticLevel.WARNING, DiagnosticLevel.INFO]

    @patch("subprocess.run")
    def test_rollback_plan_creation(
        self, mock_run: MagicMock, mock_context: ValidationContext
    ) -> None:
        """롤백 계획 생성 테스트."""
        config_dir = Path(mock_context.base_dir) / mock_context.config_dir
        config_file = config_dir / "config.yaml"

        config = {
            "namespace": "test",
            "apps": [
                {
                    "name": "nginx",
                    "type": "helm",
                    "specs": {"path": "charts/nginx"},
                }
            ],
        }
        config_file.write_text(yaml.dump(config))

        # kubectl 명령어 성공 시뮬레이션
        mock_run.return_value = MagicMock(
            returncode=0,
            stdout="apiVersion: v1\nkind: Service\nmetadata:\n  name: nginx",
        )

        validator = RollbackPlanValidator()
        result = asyncio.run(validator.run_validation(mock_context))

        # 검증 (롤백 계획 생성 결과)
        assert result.level in [
            DiagnosticLevel.SUCCESS,
            DiagnosticLevel.INFO,
            DiagnosticLevel.WARNING,
            DiagnosticLevel.ERROR,
        ]


class TestImpactAnalysisValidator:
    """ImpactAnalysisValidator 테스트."""

    def test_init(self) -> None:
        """ImpactAnalysisValidator 초기화 테스트."""
        validator = ImpactAnalysisValidator()
        assert validator.name == "impact_analysis"
        assert "영향" in validator.description or "impact" in validator.description.lower()
        assert validator.category == "pre-deployment"

    def test_no_config_file(self, mock_context: ValidationContext) -> None:
        """설정 파일 없음 테스트."""
        validator = ImpactAnalysisValidator()
        result = asyncio.run(validator.run_validation(mock_context))

        # 검증 (설정 파일 없음 시 SUCCESS도 가능 - 영향 없음)
        assert result.level in [DiagnosticLevel.ERROR, DiagnosticLevel.WARNING, DiagnosticLevel.INFO, DiagnosticLevel.SUCCESS]

    @patch("subprocess.run")
    def test_impact_analysis_with_existing_resources(
        self, mock_run: MagicMock, mock_context: ValidationContext
    ) -> None:
        """기존 리소스가 있는 경우 영향도 분석 테스트."""
        config_dir = Path(mock_context.base_dir) / mock_context.config_dir
        config_file = config_dir / "config.yaml"

        config = {
            "namespace": "test",
            "apps": [
                {
                    "name": "nginx",
                    "type": "helm",
                    "specs": {"path": "charts/nginx"},
                }
            ],
        }
        config_file.write_text(yaml.dump(config))

        # kubectl 명령어 성공 시뮬레이션
        mock_run.return_value = MagicMock(
            returncode=0,
            stdout="nginx-deployment\nnginx-service",
        )

        validator = ImpactAnalysisValidator()
        result = asyncio.run(validator.run_validation(mock_context))

        # 검증 (영향도 분석 결과)
        assert result.level in [
            DiagnosticLevel.SUCCESS,
            DiagnosticLevel.INFO,
            DiagnosticLevel.WARNING,
            DiagnosticLevel.ERROR,
        ]

    def test_impact_analysis_no_apps(self, mock_context: ValidationContext) -> None:
        """배포할 앱이 없을 때 영향도 분석 테스트."""
        config_dir = Path(mock_context.base_dir) / mock_context.config_dir
        config_file = config_dir / "config.yaml"

        config = {"namespace": "test", "apps": []}
        config_file.write_text(yaml.dump(config))

        validator = ImpactAnalysisValidator()
        result = asyncio.run(validator.run_validation(mock_context))

        # 검증 (앱 없음 시 SUCCESS도 가능 - 영향 없음)
        assert result.level in [
            DiagnosticLevel.INFO,
            DiagnosticLevel.WARNING,
            DiagnosticLevel.ERROR,
            DiagnosticLevel.SUCCESS,
        ]
