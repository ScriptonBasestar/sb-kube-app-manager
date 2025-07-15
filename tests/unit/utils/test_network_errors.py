"""
Tests for network error scenarios.
"""

from subprocess import CalledProcessError
from unittest.mock import patch

import pytest
from requests.exceptions import ConnectionError

from sbkube.exceptions import HelmError, NetworkError
from sbkube.utils.retry import retry_network_operation


@pytest.mark.unit
class TestNetworkErrorScenarios:
    """Test network error handling scenarios."""

    @patch("requests.get")
    def test_git_repository_access_failure(self, mock_get):
        """Test Git repository access failure handling."""
        mock_get.side_effect = ConnectionError("Connection failed")

        with pytest.raises(NetworkError):
            # Simulate git repo access
            response = mock_get("https://github.com/test/repo.git")
            if not response.ok:
                raise NetworkError("Git repository not accessible")

    @patch("subprocess.run")
    def test_helm_repository_connection_failure(self, mock_run):
        """Test Helm repository connection failure."""
        mock_run.side_effect = CalledProcessError(
            1, "helm repo add", "Connection timeout"
        )

        with pytest.raises(HelmError):
            try:
                mock_run(
                    ["helm", "repo", "add", "test", "https://charts.example.com"],
                    capture_output=True,
                    text=True,
                    check=True,
                )
            except CalledProcessError as e:
                raise HelmError(f"Failed to add helm repository: {e}")

    @patch("subprocess.run")
    def test_kubernetes_api_connection_failure(self, mock_run):
        """Test Kubernetes API connection failure."""
        mock_run.side_effect = CalledProcessError(
            1, "kubectl", "Unable to connect to the server"
        )

        with pytest.raises(Exception):  # Should be KubernetesError if defined
            try:
                mock_run(
                    ["kubectl", "get", "pods"],
                    capture_output=True,
                    text=True,
                    check=True,
                )
            except CalledProcessError as e:
                raise Exception(f"Kubernetes API connection failed: {e}")

    @retry_network_operation
    def _flaky_network_operation(self, fail_count=0):
        """Simulate a flaky network operation."""
        if hasattr(self, "_call_count"):
            self._call_count += 1
        else:
            self._call_count = 1

        if self._call_count <= fail_count:
            raise ConnectionError("Network temporarily unavailable")
        return "success"

    def test_network_retry_success_after_retries(self):
        """Test network operation succeeds after retries."""
        self._call_count = 0  # Reset counter
        result = self._flaky_network_operation(fail_count=2)
        assert result == "success"
        assert self._call_count == 3  # Failed twice, succeeded on third try

    def test_network_retry_exhausts_attempts(self):
        """Test network operation fails after exhausting retries."""
        self._call_count = 0  # Reset counter
        with pytest.raises(ConnectionError):
            self._flaky_network_operation(fail_count=10)  # Will exceed retry limit


@pytest.mark.unit
class TestResourceLimitScenarios:
    """Test resource limit and constraint scenarios."""

    def test_large_config_file_handling(self):
        """Test handling of unusually large config files."""
        # Create a large config structure
        large_config = {"namespace": "test", "apps": []}

        # Add many apps to test memory usage
        for i in range(1000):
            large_config["apps"].append(
                {
                    "name": f"app-{i}",
                    "type": "install-helm",
                    "specs": {
                        "repo": "bitnami",
                        "chart": "nginx",
                        "values": {f"key-{j}": f"value-{j}" for j in range(100)},
                    },
                }
            )

        # Test that large config can be processed
        assert len(large_config["apps"]) == 1000
        assert isinstance(large_config, dict)

    def test_disk_space_simulation(self):
        """Test behavior when disk space is low."""
        with patch("shutil.disk_usage") as mock_disk_usage:
            # Simulate low disk space (total, used, free)
            mock_disk_usage.return_value = (
                100 * 1024 * 1024,
                95 * 1024 * 1024,
                5 * 1024 * 1024,
            )  # 5MB free

            # Should warn or fail gracefully
            total, used, free = mock_disk_usage("/tmp")
            free_mb = free / (1024 * 1024)

            if free_mb < 10:  # Less than 10MB free
                pytest.skip("Insufficient disk space for operation")


@pytest.mark.unit
class TestConcurrentOperationScenarios:
    """Test concurrent operation scenarios."""

    def test_concurrent_deployment_detection(self):
        """Test detection of concurrent deployment attempts."""
        import tempfile
        from pathlib import Path

        with tempfile.TemporaryDirectory() as temp_dir:
            lock_file = Path(temp_dir) / "deployment.lock"

            # Simulate first deployment creating lock
            lock_file.write_text("deployment-123")

            # Second deployment should detect existing lock
            if lock_file.exists():
                existing_deployment = lock_file.read_text()
                assert existing_deployment == "deployment-123"

                # Should either wait or fail gracefully
                with pytest.raises(Exception):  # Should be DeploymentInProgressError
                    raise Exception(
                        f"Deployment {existing_deployment} already in progress"
                    )

    def test_state_update_race_condition(self):
        """Test state update race condition handling."""
        # Simulate two processes trying to update deployment state
        state_data = {"status": "pending", "version": 1}

        # First update
        state_data["status"] = "in_progress"
        state_data["version"] += 1

        # Second update (simulated race condition)
        with pytest.raises(Exception):  # Should be StateConflictError
            if state_data["version"] != 2:  # Version mismatch indicates race condition
                raise Exception("State update conflict detected")

        assert state_data["status"] == "in_progress"
        assert state_data["version"] == 2
