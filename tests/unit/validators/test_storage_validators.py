"""Tests for storage validators."""

import json
from unittest.mock import MagicMock, patch

from sbkube.models.config_model import HelmApp, SBKubeConfig
from sbkube.validators.storage_validators import (
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
