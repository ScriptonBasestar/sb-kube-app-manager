"""Tests for storage validators."""

import asyncio
import json
from pathlib import Path
from unittest.mock import MagicMock, patch

import pytest

from sbkube.models.config_model import HelmApp, SBKubeConfig
from sbkube.utils.diagnostic_system import DiagnosticLevel
from sbkube.utils.validation_system import ValidationContext, ValidationSeverity
from sbkube.validators.storage_validators import (
    StorageValidator,
    StorageValidatorLegacy,
)


class TestStorageValidator:
    """Test StorageValidator class."""

    def test_no_storage_required(self):
        """Test validation when no apps require manual PV.

        NOTE: v0.8.0 limitation - cannot detect PV requirements from HelmApp
        because values is list[str] (file paths), not inline dict.
        This test validates the current behavior.
        """
        config = SBKubeConfig(
            namespace="default",
            apps={
                "nginx": HelmApp(
                    type="helm",
                    chart="grafana/nginx",
                    version="15.0.0",
                )
            },
        )

        validator = StorageValidatorLegacy()
        result = validator.check_required_pvs(config)

        # v0.8.0: Always returns all_exist=True for HelmApps
        # because we can't parse values files
        assert result["all_exist"] is True
        assert result["missing"] == []
        assert result["existing"] == []

    @patch("subprocess.run")
    def test_no_provisioner_storage_class(self, mock_subprocess):
        """Test detection of no-provisioner StorageClass."""
        # Mock kubectl get storageclass
        sc_json = {
            "provisioner": "kubernetes.io/no-provisioner",
            "volumeBindingMode": "WaitForFirstConsumer",
        }
        mock_subprocess.return_value = MagicMock(
            returncode=0,
            stdout=json.dumps(sc_json),
            stderr="",
        )

        validator_legacy = StorageValidatorLegacy()
        validator = validator_legacy._validator

        # Check if no-provisioner detection works
        is_no_prov = validator._is_no_provisioner("postgresql-hostpath")
        assert is_no_prov is True

    def test_size_parsing(self):
        """Test storage size parsing."""
        validator_legacy = StorageValidatorLegacy()
        validator = validator_legacy._validator

        # Test parse_size
        value, unit = validator._parse_size("8Gi")
        assert value == 8.0
        assert unit == "Gi"

        value, unit = validator._parse_size("10G")
        assert value == 10.0
        assert unit == "G"

        value, unit = validator._parse_size("100Mi")
        assert value == 100.0
        assert unit == "Mi"

    def test_size_comparison(self):
        """Test storage size comparison."""
        validator_legacy = StorageValidatorLegacy()
        validator = validator_legacy._validator

        # Same unit
        assert validator._size_sufficient("8Gi", "8Gi") is True
        assert validator._size_sufficient("10Gi", "8Gi") is True
        assert validator._size_sufficient("5Gi", "8Gi") is False

        # Different units (Gi vs G)
        assert validator._size_sufficient("8Gi", "8G") is True  # 8Gi > 8G
        assert validator._size_sufficient("1Gi", "1G") is True  # 1Gi > 1G

    @patch("subprocess.run")
    def test_kubectl_failure(self, mock_subprocess):
        """Test handling of kubectl command failure."""
        # Mock kubectl failure
        mock_subprocess.side_effect = Exception("kubectl not found")

        config = SBKubeConfig(
            namespace="database",
            apps={
                "postgresql": HelmApp(
                    type="helm",
                    chart="prometheus-community/kube-state-metrics",
                    version="13.0.0",
                )
            },
        )

        validator = StorageValidatorLegacy()
        # Should return all_exist=True when kubectl fails (skip validation)
        result = validator.check_required_pvs(config)

        assert result["all_exist"] is True
        assert result["missing"] == []


@pytest.fixture
def mock_context(tmp_path: Path) -> ValidationContext:
    """Create mock ValidationContext."""
    return ValidationContext(
        base_dir=str(tmp_path),
        config_dir="config",
        environment="test",
        metadata={"cluster": "test-cluster"},
    )


class TestStorageValidatorAsync:
    """Test StorageValidator async methods."""

    def test_init(self) -> None:
        """Test StorageValidator initialization."""
        validator = StorageValidator()
        assert validator.name == "storage_validation"
        assert "PV/PVC" in validator.description or "스토리지" in validator.description
        assert validator.category == "infrastructure"

    def test_init_with_kubeconfig(self) -> None:
        """Test StorageValidator with kubeconfig parameter."""
        validator = StorageValidator(kubeconfig="/path/to/kubeconfig")
        assert validator.kubeconfig == "/path/to/kubeconfig"

    def test_no_config_in_context(self, mock_context: ValidationContext) -> None:
        """Test validation when context has no config."""
        validator = StorageValidator()
        result = asyncio.run(validator.run_validation(mock_context))

        # Should return WARNING when no config
        assert result.level == DiagnosticLevel.WARNING
        assert result.severity == ValidationSeverity.LOW

    def test_no_required_pvs(self, mock_context: ValidationContext) -> None:
        """Test validation when no PVs are required."""
        # Create config with no PV requirements
        config = SBKubeConfig(
            namespace="default",
            apps={
                "nginx": HelmApp(
                    type="helm",
                    chart="nginx/nginx",
                    version="1.0.0",
                )
            },
        )
        mock_context.config = config

        validator = StorageValidator()
        result = asyncio.run(validator.run_validation(mock_context))

        # Should return SUCCESS when no PVs needed
        assert result.level == DiagnosticLevel.SUCCESS
        assert result.severity == ValidationSeverity.INFO

    @patch("subprocess.run")
    def test_kubectl_failure(
        self, mock_subprocess: MagicMock, mock_context: ValidationContext
    ) -> None:
        """Test handling when kubectl fails."""
        # Create config (doesn't matter what's in it)
        config = SBKubeConfig(
            namespace="default",
            apps={
                "app1": HelmApp(
                    type="helm",
                    chart="test/test",
                    version="1.0.0",
                )
            },
        )
        mock_context.config = config

        # Mock subprocess to fail
        mock_subprocess.side_effect = Exception("kubectl not found")

        validator = StorageValidator()
        result = asyncio.run(validator.run_validation(mock_context))

        # Should return WARNING or SUCCESS (skips validation)
        assert result.level in [
            DiagnosticLevel.WARNING,
            DiagnosticLevel.SUCCESS,
        ]

    @patch("sbkube.validators.storage_validators.StorageValidator._get_cluster_pvs")
    @patch("sbkube.validators.storage_validators.StorageValidator._extract_required_pvs")
    def test_all_pvs_exist(
        self,
        mock_extract: MagicMock,
        mock_get_pvs: MagicMock,
        mock_context: ValidationContext,
    ) -> None:
        """Test validation when all required PVs exist."""
        config = SBKubeConfig(
            namespace="default",
            apps={
                "app1": HelmApp(
                    type="helm",
                    chart="test/test",
                    version="1.0.0",
                )
            },
        )
        mock_context.config = config

        # Mock required PVs
        mock_extract.return_value = [
            {
                "app": "app1",
                "storage_class": "local-path",
                "size": "8Gi",
            }
        ]

        # Mock cluster PVs (PV exists) - Kubernetes structure
        mock_get_pvs.return_value = [
            {
                "metadata": {"name": "pv-001"},
                "spec": {
                    "storageClassName": "local-path",
                    "capacity": {"storage": "10Gi"},
                },
                "status": {"phase": "Available"},
            }
        ]

        validator = StorageValidator()
        result = asyncio.run(validator.run_validation(mock_context))

        # Should return SUCCESS
        assert result.level == DiagnosticLevel.SUCCESS
        assert result.severity == ValidationSeverity.INFO

    @patch("sbkube.validators.storage_validators.StorageValidator._get_cluster_pvs")
    @patch("sbkube.validators.storage_validators.StorageValidator._extract_required_pvs")
    def test_missing_pvs(
        self,
        mock_extract: MagicMock,
        mock_get_pvs: MagicMock,
        mock_context: ValidationContext,
    ) -> None:
        """Test validation when required PVs are missing."""
        config = SBKubeConfig(
            namespace="default",
            apps={
                "app1": HelmApp(
                    type="helm",
                    chart="test/test",
                    version="1.0.0",
                )
            },
        )
        mock_context.config = config

        # Mock required PVs
        mock_extract.return_value = [
            {
                "app": "app1",
                "storage_class": "local-path",
                "size": "8Gi",
            }
        ]

        # Mock cluster PVs (empty - no PVs exist)
        mock_get_pvs.return_value = []

        validator = StorageValidator()
        result = asyncio.run(validator.run_validation(mock_context))

        # Should return ERROR
        assert result.level == DiagnosticLevel.ERROR
        assert result.severity == ValidationSeverity.HIGH

    @patch("sbkube.validators.storage_validators.StorageValidator._get_cluster_pvs")
    @patch("sbkube.validators.storage_validators.StorageValidator._extract_required_pvs")
    def test_cluster_access_failure(
        self,
        mock_extract: MagicMock,
        mock_get_pvs: MagicMock,
        mock_context: ValidationContext,
    ) -> None:
        """Test handling when cluster access fails."""
        config = SBKubeConfig(
            namespace="default",
            apps={
                "app1": HelmApp(
                    type="helm",
                    chart="test/test",
                    version="1.0.0",
                )
            },
        )
        mock_context.config = config

        # Mock required PVs
        mock_extract.return_value = [
            {
                "app": "app1",
                "storage_class": "local-path",
                "size": "8Gi",
            }
        ]

        # Mock cluster PVs to return None (cluster access failed)
        mock_get_pvs.return_value = None

        validator = StorageValidator()
        result = asyncio.run(validator.run_validation(mock_context))

        # Should return WARNING
        assert result.level == DiagnosticLevel.WARNING
        assert result.severity == ValidationSeverity.MEDIUM
