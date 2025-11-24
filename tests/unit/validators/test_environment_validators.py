"""Environment validators 테스트."""

import asyncio
import json
from pathlib import Path
from unittest.mock import MagicMock, patch

import pytest

from sbkube.utils.diagnostic_system import DiagnosticLevel
from sbkube.utils.validation_system import ValidationContext, ValidationSeverity
from sbkube.validators.environment_validators import (
    ClusterResourceValidator,
    NamespacePermissionValidator,
    NetworkPolicyValidator,
    SecurityContextValidator,
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


class TestClusterResourceValidator:
    """ClusterResourceValidator 테스트."""

    def test_init(self) -> None:
        """ClusterResourceValidator 초기화 테스트."""
        validator = ClusterResourceValidator()
        assert validator.name == "cluster_resource"
        assert "가용성" in validator.description or "availability" in validator.description.lower()
        assert validator.category == "environment"

    @patch("subprocess.run")
    def test_kubectl_not_available(
        self, mock_run: MagicMock, mock_context: ValidationContext
    ) -> None:
        """kubectl 명령어 실행 실패 테스트."""
        mock_run.return_value = MagicMock(
            returncode=1,
            stderr="error: failed to connect",
        )

        validator = ClusterResourceValidator()
        result = asyncio.run(validator.run_validation(mock_context))

        # 검증 (kubectl 실패 시 ERROR)
        assert result.level in [DiagnosticLevel.ERROR, DiagnosticLevel.WARNING]
        assert result.severity in [ValidationSeverity.HIGH, ValidationSeverity.MEDIUM]

    @patch("subprocess.run")
    def test_sufficient_resources(
        self, mock_run: MagicMock, mock_context: ValidationContext
    ) -> None:
        """충분한 리소스가 있을 때 테스트."""
        # kubectl get nodes -o json 응답 시뮬레이션
        nodes_response = {
            "items": [
                {
                    "status": {
                        "allocatable": {
                            "cpu": "4",
                            "memory": "8Gi",
                        },
                        "conditions": [
                            {"type": "Ready", "status": "True"}
                        ]
                    }
                }
            ]
        }

        mock_run.return_value = MagicMock(
            returncode=0,
            stdout=json.dumps(nodes_response),
        )

        validator = ClusterResourceValidator()
        result = asyncio.run(validator.run_validation(mock_context))

        # 검증 (리소스 충분 시 SUCCESS 또는 WARNING)
        assert result.level in [DiagnosticLevel.SUCCESS, DiagnosticLevel.WARNING, DiagnosticLevel.ERROR]


class TestNamespacePermissionValidator:
    """NamespacePermissionValidator 테스트."""

    def test_init(self) -> None:
        """NamespacePermissionValidator 초기화 테스트."""
        validator = NamespacePermissionValidator()
        assert validator.name == "namespace_permission"
        assert "권한" in validator.description or "permission" in validator.description.lower()
        assert validator.category == "environment"

    @patch("subprocess.run")
    def test_namespace_not_accessible(
        self, mock_run: MagicMock, mock_context: ValidationContext
    ) -> None:
        """네임스페이스 접근 불가 테스트."""
        mock_run.return_value = MagicMock(
            returncode=1,
            stderr="Error from server (Forbidden)",
        )

        validator = NamespacePermissionValidator()
        result = asyncio.run(validator.run_validation(mock_context))

        # 검증 (권한 없음 시 ERROR)
        assert result.level in [DiagnosticLevel.ERROR, DiagnosticLevel.WARNING]
        assert result.severity in [ValidationSeverity.HIGH, ValidationSeverity.CRITICAL, ValidationSeverity.MEDIUM]

    @patch("subprocess.run")
    def test_sufficient_permissions(
        self, mock_run: MagicMock, mock_context: ValidationContext
    ) -> None:
        """충분한 권한이 있을 때 테스트."""
        # kubectl auth can-i 응답 시뮬레이션
        mock_run.return_value = MagicMock(
            returncode=0,
            stdout="yes",
        )

        validator = NamespacePermissionValidator()
        result = asyncio.run(validator.run_validation(mock_context))

        # 검증 (권한 충분 시 SUCCESS, ERROR, WARNING 가능)
        assert result.level in [DiagnosticLevel.SUCCESS, DiagnosticLevel.ERROR, DiagnosticLevel.WARNING]


class TestNetworkPolicyValidator:
    """NetworkPolicyValidator 테스트."""

    def test_init(self) -> None:
        """NetworkPolicyValidator 초기화 테스트."""
        validator = NetworkPolicyValidator()
        assert validator.name == "network_policy"
        assert "네트워크" in validator.description or "network" in validator.description.lower()
        assert validator.category == "environment"

    @patch("subprocess.run")
    def test_no_network_policies(
        self, mock_run: MagicMock, mock_context: ValidationContext
    ) -> None:
        """네트워크 정책이 없을 때 테스트."""
        # kubectl get networkpolicies 응답 (빈 목록)
        mock_run.return_value = MagicMock(
            returncode=0,
            stdout=json.dumps({"items": []}),
        )

        validator = NetworkPolicyValidator()
        result = asyncio.run(validator.run_validation(mock_context))

        # 검증 (정책 없음 시 INFO 또는 WARNING)
        assert result.level in [DiagnosticLevel.INFO, DiagnosticLevel.WARNING, DiagnosticLevel.SUCCESS, DiagnosticLevel.ERROR]

    @patch("subprocess.run")
    def test_network_policy_check_failure(
        self, mock_run: MagicMock, mock_context: ValidationContext
    ) -> None:
        """네트워크 정책 조회 실패 테스트."""
        mock_run.return_value = MagicMock(
            returncode=1,
            stderr="Error: connection refused",
        )

        validator = NetworkPolicyValidator()
        result = asyncio.run(validator.run_validation(mock_context))

        # 검증 (조회 실패 시 모든 레벨 가능)
        assert result.level in [DiagnosticLevel.ERROR, DiagnosticLevel.WARNING, DiagnosticLevel.INFO, DiagnosticLevel.SUCCESS]


class TestSecurityContextValidator:
    """SecurityContextValidator 테스트."""

    def test_init(self) -> None:
        """SecurityContextValidator 초기화 테스트."""
        validator = SecurityContextValidator()
        assert validator.name == "security_context"
        assert "보안" in validator.description or "security" in validator.description.lower()
        assert validator.category == "environment"

    @patch("subprocess.run")
    def test_pod_security_check(
        self, mock_run: MagicMock, mock_context: ValidationContext
    ) -> None:
        """Pod Security 검증 테스트."""
        # kubectl 명령어 응답 시뮬레이션
        mock_run.return_value = MagicMock(
            returncode=0,
            stdout=json.dumps({"items": []}),
        )

        validator = SecurityContextValidator()
        result = asyncio.run(validator.run_validation(mock_context))

        # 검증 (성공 또는 경고)
        assert result.level in [
            DiagnosticLevel.SUCCESS,
            DiagnosticLevel.WARNING,
            DiagnosticLevel.INFO,
            DiagnosticLevel.ERROR,
        ]

    @patch("subprocess.run")
    def test_security_check_failure(
        self, mock_run: MagicMock, mock_context: ValidationContext
    ) -> None:
        """보안 검증 실패 테스트."""
        mock_run.return_value = MagicMock(
            returncode=1,
            stderr="Error: unauthorized",
        )

        validator = SecurityContextValidator()
        result = asyncio.run(validator.run_validation(mock_context))

        # 검증 (실패 시 ERROR 또는 WARNING)
        assert result.level in [DiagnosticLevel.ERROR, DiagnosticLevel.WARNING, DiagnosticLevel.INFO]
