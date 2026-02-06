"""Tests for doctor command."""

from unittest.mock import MagicMock, patch

import pytest
from click.testing import CliRunner

from sbkube.cli import main


@pytest.fixture
def runner():
    """Create CliRunner fixture."""
    return CliRunner()


class TestDoctorCommandHelp:
    """Test doctor command help."""

    def test_doctor_help(self, runner) -> None:
        """Test --help option shows help message."""
        result = runner.invoke(main, ["doctor", "--help"])

        assert result.exit_code == 0
        assert "doctor" in result.output.lower()
        assert "진단" in result.output or "diagnostic" in result.output.lower()


class TestDoctorCommandBasic:
    """Test basic doctor command scenarios."""

    @patch("sbkube.commands.doctor.DiagnosticEngine")
    @patch("sbkube.commands.doctor.asyncio.run")
    def test_doctor_basic_success(
        self,
        mock_asyncio_run,
        mock_engine_class,
        runner,
    ) -> None:
        """Test successful doctor run with all checks passing."""
        # Mock DiagnosticEngine
        mock_engine = MagicMock()
        mock_engine.get_summary.return_value = {
            "total": 7,
            "passed": 7,
            "warning": 0,
            "error": 0,
        }
        mock_engine_class.return_value = mock_engine

        # Run doctor
        result = runner.invoke(main, ["doctor"])

        # Assert
        assert result.exit_code == 0
        # Verify engine was initialized
        mock_engine_class.assert_called_once()
        # Verify checks were registered (7 checks)
        assert mock_engine.register_check.call_count == 7
        # Verify engine ran
        mock_asyncio_run.assert_called_once()
        # Verify results displayed
        mock_engine.display_results.assert_called_once_with(detailed=False)

    @patch("sbkube.commands.doctor.DiagnosticEngine")
    @patch("sbkube.commands.doctor.asyncio.run")
    def test_doctor_detailed_mode(
        self,
        mock_asyncio_run,
        mock_engine_class,
        runner,
    ) -> None:
        """Test doctor with --detailed flag."""
        # Mock DiagnosticEngine
        mock_engine = MagicMock()
        mock_engine.get_summary.return_value = {
            "total": 7,
            "passed": 7,
            "warning": 0,
            "error": 0,
        }
        mock_engine_class.return_value = mock_engine

        # Run doctor with --detailed
        result = runner.invoke(main, ["doctor", "--detailed"])

        # Assert
        assert result.exit_code == 0
        # Verify detailed flag was passed
        mock_engine.display_results.assert_called_once_with(detailed=True)

    @patch("sbkube.commands.doctor.DiagnosticEngine")
    @patch("sbkube.commands.doctor.asyncio.run")
    def test_doctor_with_warnings(
        self,
        mock_asyncio_run,
        mock_engine_class,
        runner,
    ) -> None:
        """Test doctor exit code when warnings are present."""
        # Mock DiagnosticEngine with warnings
        mock_engine = MagicMock()
        mock_engine.get_summary.return_value = {
            "total": 6,
            "passed": 5,
            "warning": 1,
            "error": 0,
        }
        mock_engine_class.return_value = mock_engine

        # Run doctor
        result = runner.invoke(main, ["doctor"])

        # Assert - should exit with code 2 for warnings
        assert result.exit_code == 2

    @patch("sbkube.commands.doctor.DiagnosticEngine")
    @patch("sbkube.commands.doctor.asyncio.run")
    def test_doctor_with_errors(
        self,
        mock_asyncio_run,
        mock_engine_class,
        runner,
    ) -> None:
        """Test doctor exit code when errors are present."""
        # Mock DiagnosticEngine with errors
        mock_engine = MagicMock()
        mock_engine.get_summary.return_value = {
            "total": 6,
            "passed": 4,
            "warning": 1,
            "error": 1,
        }
        mock_engine_class.return_value = mock_engine

        # Run doctor
        result = runner.invoke(main, ["doctor"])

        # Assert - should exit with code 1 for errors
        assert result.exit_code == 1


class TestDoctorCommandSpecificCheck:
    """Test doctor command with specific check selection."""

    @patch("sbkube.commands.doctor.DiagnosticEngine")
    @patch("sbkube.commands.doctor.asyncio.run")
    def test_doctor_specific_check(
        self,
        mock_asyncio_run,
        mock_engine_class,
        runner,
    ) -> None:
        """Test doctor with --check option."""
        # Mock DiagnosticEngine
        mock_engine = MagicMock()
        mock_engine.get_summary.return_value = {
            "total": 1,
            "passed": 1,
            "warning": 0,
            "error": 0,
        }
        mock_engine_class.return_value = mock_engine

        # Run doctor with specific check
        result = runner.invoke(main, ["doctor", "--check", "k8s_connectivity"])

        # Assert
        assert result.exit_code == 0
        # Verify only one check was registered
        assert mock_engine.register_check.call_count == 1

    def test_doctor_invalid_check_name(
        self,
        runner,
    ) -> None:
        """Test doctor with invalid --check name."""
        # Run doctor with invalid check name
        result = runner.invoke(main, ["doctor", "--check", "invalid_check"])

        # Assert - should fail
        assert result.exit_code != 0
        assert "알 수 없는" in result.output or "unknown" in result.output.lower()


class TestDoctorCommandErrors:
    """Test doctor command error handling."""

    @patch("sbkube.commands.doctor.DiagnosticEngine")
    def test_doctor_engine_init_failure(
        self,
        mock_engine_class,
        runner,
    ) -> None:
        """Test error when DiagnosticEngine init fails."""
        # Mock engine to raise exception
        mock_engine_class.side_effect = Exception("Engine init failed")

        # Run doctor
        result = runner.invoke(main, ["doctor"])

        # Assert - should fail
        assert result.exit_code != 0

    @patch("sbkube.commands.doctor.DiagnosticEngine")
    @patch("sbkube.commands.doctor.asyncio.run")
    def test_doctor_check_execution_failure(
        self,
        mock_asyncio_run,
        mock_engine_class,
        runner,
    ) -> None:
        """Test error when check execution fails."""
        # Mock engine but asyncio.run raises exception
        mock_engine = MagicMock()
        mock_engine_class.return_value = mock_engine
        mock_asyncio_run.side_effect = Exception("Check execution failed")

        # Run doctor
        result = runner.invoke(main, ["doctor"])

        # Assert - should fail
        assert result.exit_code != 0


class TestDoctorCommandOptions:
    """Test doctor command options."""

    @patch("sbkube.commands.doctor.DiagnosticEngine")
    @patch("sbkube.commands.doctor.asyncio.run")
    def test_doctor_with_config_dir(
        self,
        mock_asyncio_run,
        mock_engine_class,
        runner,
        tmp_path,
    ) -> None:
        """Test doctor with --config-dir option."""
        # Mock DiagnosticEngine
        mock_engine = MagicMock()
        mock_engine.get_summary.return_value = {
            "total": 7,
            "passed": 7,
            "warning": 0,
            "error": 0,
        }
        mock_engine_class.return_value = mock_engine

        # Run doctor with custom config dir
        result = runner.invoke(
            main, ["doctor", "--config-dir", str(tmp_path)]
        )

        # Assert
        assert result.exit_code == 0
        # Verify engine ran
        mock_asyncio_run.assert_called_once()
