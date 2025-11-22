"""Unit tests for doctor.py command.

Tests verify:
- Basic diagnostic execution
- Detailed mode output
- Specific check execution
- Check name validation
- Error handling
- Exit code behavior (0=success, 1=error, 2=warning)
"""

from unittest.mock import AsyncMock, MagicMock, patch

import pytest
from click.testing import CliRunner

from sbkube.commands.doctor import cmd
from sbkube.utils.diagnostic_system import DiagnosticLevel, DiagnosticResult


class TestDoctorBasic:
    """Test basic doctor command functionality."""

    @patch("sbkube.commands.doctor.asyncio.run")
    @patch("sbkube.commands.doctor.DiagnosticEngine")
    def test_doctor_basic_success(self, mock_engine_class, mock_asyncio_run):
        """Test successful basic diagnostic run."""
        # Arrange
        mock_engine = MagicMock()
        mock_engine_class.return_value = mock_engine
        mock_engine.get_summary.return_value = {
            "total": 6,
            "success": 6,
            "warning": 0,
            "error": 0,
        }

        # Act
        runner = CliRunner()
        result = runner.invoke(cmd, [])

        # Assert
        assert result.exit_code == 0
        mock_engine.register_check.assert_called()  # Should register checks
        mock_asyncio_run.assert_called_once()  # Should run async checks
        mock_engine.display_results.assert_called_once_with(detailed=False)

    @patch("sbkube.commands.doctor.asyncio.run")
    @patch("sbkube.commands.doctor.DiagnosticEngine")
    def test_doctor_detailed_mode(self, mock_engine_class, mock_asyncio_run):
        """Test doctor with --detailed flag."""
        # Arrange
        mock_engine = MagicMock()
        mock_engine_class.return_value = mock_engine
        mock_engine.get_summary.return_value = {
            "total": 6,
            "success": 6,
            "warning": 0,
            "error": 0,
        }

        # Act
        runner = CliRunner()
        result = runner.invoke(cmd, ["--detailed"])

        # Assert
        assert result.exit_code == 0
        mock_engine.display_results.assert_called_once_with(detailed=True)

    @patch("sbkube.commands.doctor.asyncio.run")
    @patch("sbkube.commands.doctor.DiagnosticEngine")
    def test_doctor_custom_config_dir(self, mock_engine_class, mock_asyncio_run):
        """Test doctor with custom --config-dir."""
        # Arrange
        mock_engine = MagicMock()
        mock_engine_class.return_value = mock_engine
        mock_engine.get_summary.return_value = {
            "total": 6,
            "success": 6,
            "warning": 0,
            "error": 0,
        }

        # Act
        runner = CliRunner()
        result = runner.invoke(cmd, ["--config-dir", "/custom/path"])

        # Assert
        assert result.exit_code == 0
        # ConfigValidityCheck should be initialized with custom path
        # We can verify through the register_check calls


class TestDoctorSpecificCheck:
    """Test running specific diagnostic checks."""

    @patch("sbkube.commands.doctor.asyncio.run")
    @patch("sbkube.commands.doctor.DiagnosticEngine")
    @patch("sbkube.commands.doctor.KubernetesConnectivityCheck")
    def test_specific_check_k8s_connectivity(
        self, mock_k8s_check_class, mock_engine_class, mock_asyncio_run
    ):
        """Test running only k8s_connectivity check."""
        # Arrange
        mock_check = MagicMock()
        mock_check.name = "k8s_connectivity"
        mock_check.description = "Kubernetes cluster connectivity"
        mock_k8s_check_class.return_value = mock_check

        mock_engine = MagicMock()
        mock_engine_class.return_value = mock_engine
        mock_engine.get_summary.return_value = {
            "total": 1,
            "success": 1,
            "warning": 0,
            "error": 0,
        }

        # Act
        runner = CliRunner()
        result = runner.invoke(cmd, ["--check", "k8s_connectivity"])

        # Assert
        assert result.exit_code == 0
        # Should only register the specific check
        assert mock_engine.register_check.call_count == 1

    @patch("sbkube.commands.doctor.KubernetesConnectivityCheck")
    @patch("sbkube.commands.doctor.HelmInstallationCheck")
    @patch("sbkube.commands.doctor.ConfigValidityCheck")
    @patch("sbkube.commands.doctor.NetworkAccessCheck")
    @patch("sbkube.commands.doctor.PermissionsCheck")
    @patch("sbkube.commands.doctor.ResourceAvailabilityCheck")
    def test_invalid_check_name(
        self,
        mock_resource_check,
        mock_permissions_check,
        mock_network_check,
        mock_config_check,
        mock_helm_check,
        mock_k8s_check,
    ):
        """Test error when providing invalid check name."""
        # Arrange - Mock all checks with names
        for mock_check_class, name, desc in [
            (mock_k8s_check, "k8s_connectivity", "Kubernetes connectivity"),
            (mock_helm_check, "helm_installation", "Helm installation"),
            (mock_config_check, "config_validity", "Config validity"),
            (mock_network_check, "network_access", "Network access"),
            (mock_permissions_check, "permissions", "Permissions"),
            (mock_resource_check, "resource_availability", "Resource availability"),
        ]:
            mock_instance = MagicMock()
            mock_instance.name = name
            mock_instance.description = desc
            mock_check_class.return_value = mock_instance

        # Act
        runner = CliRunner()
        result = runner.invoke(cmd, ["--check", "invalid_check_name"])

        # Assert
        assert result.exit_code == 1
        assert "알 수 없는 검사" in result.output
        assert "사용 가능한 검사" in result.output


class TestDoctorExitCodes:
    """Test exit code behavior based on diagnostic results."""

    @patch("sbkube.commands.doctor.asyncio.run")
    @patch("sbkube.commands.doctor.DiagnosticEngine")
    def test_exit_code_0_all_success(self, mock_engine_class, mock_asyncio_run):
        """Test exit code 0 when all checks pass."""
        # Arrange
        mock_engine = MagicMock()
        mock_engine_class.return_value = mock_engine
        mock_engine.get_summary.return_value = {
            "total": 6,
            "success": 6,
            "warning": 0,
            "error": 0,
        }

        # Act
        runner = CliRunner()
        result = runner.invoke(cmd, [])

        # Assert
        assert result.exit_code == 0

    @patch("sbkube.commands.doctor.asyncio.run")
    @patch("sbkube.commands.doctor.DiagnosticEngine")
    def test_exit_code_1_with_errors(self, mock_engine_class, mock_asyncio_run):
        """Test exit code 1 when there are errors."""
        # Arrange
        mock_engine = MagicMock()
        mock_engine_class.return_value = mock_engine
        mock_engine.get_summary.return_value = {
            "total": 6,
            "success": 4,
            "warning": 1,
            "error": 1,
        }

        # Act
        runner = CliRunner()
        result = runner.invoke(cmd, [])

        # Assert
        assert result.exit_code == 1

    @patch("sbkube.commands.doctor.asyncio.run")
    @patch("sbkube.commands.doctor.DiagnosticEngine")
    def test_exit_code_2_with_warnings_only(
        self, mock_engine_class, mock_asyncio_run
    ):
        """Test exit code 2 when there are only warnings."""
        # Arrange
        mock_engine = MagicMock()
        mock_engine_class.return_value = mock_engine
        mock_engine.get_summary.return_value = {
            "total": 6,
            "success": 5,
            "warning": 1,
            "error": 0,
        }

        # Act
        runner = CliRunner()
        result = runner.invoke(cmd, [])

        # Assert
        assert result.exit_code == 2


class TestDoctorErrorHandling:
    """Test error handling scenarios."""

    @patch("sbkube.commands.doctor.DiagnosticEngine")
    def test_engine_initialization_failure(self, mock_engine_class):
        """Test graceful handling of engine initialization failure."""
        # Arrange
        mock_engine_class.side_effect = Exception("Engine init failed")

        # Act
        runner = CliRunner()
        result = runner.invoke(cmd, [])

        # Assert
        assert result.exit_code == 1
        # Should log error (can't easily verify logger output in tests)

    @patch("sbkube.commands.doctor.asyncio.run")
    @patch("sbkube.commands.doctor.DiagnosticEngine")
    def test_diagnostic_execution_failure(self, mock_engine_class, mock_asyncio_run):
        """Test handling of diagnostic execution failure."""
        # Arrange
        mock_engine = MagicMock()
        mock_engine_class.return_value = mock_engine
        mock_asyncio_run.side_effect = Exception("Async execution failed")

        # Act
        runner = CliRunner()
        result = runner.invoke(cmd, [])

        # Assert
        assert result.exit_code == 1


class TestDoctorCheckRegistration:
    """Test diagnostic check registration."""

    @patch("sbkube.commands.doctor.asyncio.run")
    @patch("sbkube.commands.doctor.DiagnosticEngine")
    @patch("sbkube.commands.doctor.KubernetesConnectivityCheck")
    @patch("sbkube.commands.doctor.HelmInstallationCheck")
    @patch("sbkube.commands.doctor.ConfigValidityCheck")
    @patch("sbkube.commands.doctor.NetworkAccessCheck")
    @patch("sbkube.commands.doctor.PermissionsCheck")
    @patch("sbkube.commands.doctor.ResourceAvailabilityCheck")
    def test_all_checks_registered(
        self,
        mock_resource_check,
        mock_permissions_check,
        mock_network_check,
        mock_config_check,
        mock_helm_check,
        mock_k8s_check,
        mock_engine_class,
        mock_asyncio_run,
    ):
        """Test that all 6 diagnostic checks are registered."""
        # Arrange
        mock_engine = MagicMock()
        mock_engine_class.return_value = mock_engine
        mock_engine.get_summary.return_value = {
            "total": 6,
            "success": 6,
            "warning": 0,
            "error": 0,
        }

        # Create mock check instances
        for mock_check_class, name in [
            (mock_k8s_check, "k8s_connectivity"),
            (mock_helm_check, "helm_installation"),
            (mock_config_check, "config_validity"),
            (mock_network_check, "network_access"),
            (mock_permissions_check, "permissions"),
            (mock_resource_check, "resource_availability"),
        ]:
            mock_instance = MagicMock()
            mock_instance.name = name
            mock_instance.description = f"Description for {name}"
            mock_check_class.return_value = mock_instance

        # Act
        runner = CliRunner()
        result = runner.invoke(cmd, [])

        # Assert
        assert result.exit_code == 0
        # Should register all 6 checks
        assert mock_engine.register_check.call_count == 6

    @patch("sbkube.commands.doctor.asyncio.run")
    @patch("sbkube.commands.doctor.DiagnosticEngine")
    @patch("sbkube.commands.doctor.ConfigValidityCheck")
    def test_config_check_receives_config_dir(
        self, mock_config_check, mock_engine_class, mock_asyncio_run
    ):
        """Test that ConfigValidityCheck receives the config_dir parameter."""
        # Arrange
        mock_instance = MagicMock()
        mock_instance.name = "config_validity"
        mock_config_check.return_value = mock_instance

        mock_engine = MagicMock()
        mock_engine_class.return_value = mock_engine
        mock_engine.get_summary.return_value = {
            "total": 6,
            "success": 6,
            "warning": 0,
            "error": 0,
        }

        # Act
        runner = CliRunner()
        result = runner.invoke(cmd, ["--config-dir", "/custom/config"])

        # Assert
        assert result.exit_code == 0
        # ConfigValidityCheck should be called with config_dir
        mock_config_check.assert_called_once_with("/custom/config")


class TestDoctorIntegration:
    """Integration-level tests for doctor command."""

    @patch("sbkube.commands.doctor.asyncio.run")
    @patch("sbkube.commands.doctor.DiagnosticEngine")
    def test_full_diagnostic_workflow(self, mock_engine_class, mock_asyncio_run):
        """Test complete diagnostic workflow execution."""
        # Arrange
        mock_engine = MagicMock()
        mock_engine_class.return_value = mock_engine
        mock_engine.get_summary.return_value = {
            "total": 6,
            "success": 4,
            "warning": 1,
            "error": 1,
        }

        # Act
        runner = CliRunner()
        result = runner.invoke(cmd, ["--detailed", "--config-dir", "."])

        # Assert
        assert result.exit_code == 1  # Error exit code
        # Verify workflow execution order
        assert mock_engine.register_check.called
        mock_asyncio_run.assert_called_once()
        mock_engine.display_results.assert_called_once_with(detailed=True)
        mock_engine.get_summary.assert_called_once()
