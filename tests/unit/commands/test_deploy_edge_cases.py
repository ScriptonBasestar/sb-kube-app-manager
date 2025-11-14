"""Unit tests for deploy.py edge cases and error scenarios.

Tests verify:
- Connection error detection
- Legacy path handling
- Namespace creation scenarios
- Helm deployment options
"""

from pathlib import Path
from unittest.mock import MagicMock, patch

import pytest

from sbkube.commands.deploy import deploy_helm_app
from sbkube.exceptions import KubernetesConnectionError
from sbkube.models.config_model import HelmApp
from sbkube.utils.output_manager import OutputManager


class TestConnectionErrorHandling:
    """Test connection error detection and handling."""

    @patch("sbkube.commands.deploy.run_command")
    def test_connection_refused_error(self, mock_run_command, tmp_path: Path) -> None:
        """Test detection of connection refused errors."""
        # Arrange
        build_dir = tmp_path / "build"
        build_dir.mkdir(exist_ok=True)
        app_build_dir = build_dir / "nginx"
        app_build_dir.mkdir(exist_ok=True)
        (app_build_dir / "Chart.yaml").write_text("name: nginx")

        app = HelmApp(
            type="helm",
            chart="bitnami/nginx",
            namespace="default",
        )

        # Mock responses:
        # 1. Namespace check succeeds
        # 2. Helm command fails with connection refused
        mock_run_command.side_effect = [
            (0, "", ""),  # namespace check succeeds
            (1, "", "Error: connection refused to kubernetes cluster"),  # helm fails
        ]
        output = MagicMock(spec=OutputManager)

        # Act & Assert
        with pytest.raises(KubernetesConnectionError) as exc_info:
            deploy_helm_app(
                app_name="nginx",
                app=app,
                base_dir=tmp_path,
                charts_dir=tmp_path / "charts",
                build_dir=build_dir,
                app_config_dir=tmp_path / "config",
                output=output,
                dry_run=False,
            )

        # Verify error message contains connection refused
        assert "connection refused" in str(exc_info.value).lower()

    @patch("sbkube.commands.deploy.run_command")
    def test_timeout_error(self, mock_run_command, tmp_path: Path) -> None:
        """Test detection of timeout errors."""
        # Arrange
        build_dir = tmp_path / "build"
        build_dir.mkdir(exist_ok=True)
        app_build_dir = build_dir / "nginx"
        app_build_dir.mkdir(exist_ok=True)
        (app_build_dir / "Chart.yaml").write_text("name: nginx")

        app = HelmApp(
            type="helm",
            chart="bitnami/nginx",
            namespace="default",
        )

        # Mock responses:
        # 1. Namespace check succeeds
        # 2. Helm command fails with timeout
        mock_run_command.side_effect = [
            (0, "", ""),  # namespace check succeeds
            (1, "", "Error: i/o timeout connecting to kubernetes"),  # helm fails
        ]
        output = MagicMock(spec=OutputManager)

        # Act & Assert
        with pytest.raises(KubernetesConnectionError) as exc_info:
            deploy_helm_app(
                app_name="nginx",
                app=app,
                base_dir=tmp_path,
                charts_dir=tmp_path / "charts",
                build_dir=build_dir,
                app_config_dir=tmp_path / "config",
                output=output,
                dry_run=False,
            )

        # Verify error message contains timeout
        assert "timeout" in str(exc_info.value).lower()

    @patch("sbkube.commands.deploy.run_command")
    def test_connection_error_in_stdout(self, mock_run_command, tmp_path: Path) -> None:
        """Test connection error detection in stdout instead of stderr."""
        # Arrange
        build_dir = tmp_path / "build"
        build_dir.mkdir(exist_ok=True)
        app_build_dir = build_dir / "nginx"
        app_build_dir.mkdir(exist_ok=True)
        (app_build_dir / "Chart.yaml").write_text("name: nginx")

        app = HelmApp(
            type="helm",
            chart="bitnami/nginx",
            namespace="default",
        )

        # Mock responses:
        # 1. Namespace check succeeds
        # 2. Helm command fails with error in stdout
        mock_run_command.side_effect = [
            (0, "", ""),  # namespace check succeeds
            (1, "connection refused to cluster", ""),  # error in stdout
        ]
        output = MagicMock(spec=OutputManager)

        # Act & Assert
        with pytest.raises(KubernetesConnectionError) as exc_info:
            deploy_helm_app(
                app_name="nginx",
                app=app,
                base_dir=tmp_path,
                charts_dir=tmp_path / "charts",
                build_dir=build_dir,
                app_config_dir=tmp_path / "config",
                output=output,
                dry_run=False,
            )

        # Verify error message contains connection refused
        assert "connection refused" in str(exc_info.value).lower()


class TestLegacyPathHandling:
    """Test legacy chart path detection and migration guidance."""

    @patch("sbkube.commands.deploy.run_command")
    def test_legacy_v071_path_detected(self, mock_run_command, tmp_path: Path) -> None:
        """Test detection of v0.7.1 legacy chart path."""
        # Arrange
        charts_dir = tmp_path / "charts"
        charts_dir.mkdir(exist_ok=True)

        # Create legacy v0.7.1 path structure: charts/nginx/
        legacy_path = charts_dir / "nginx"
        legacy_path.mkdir(exist_ok=True)
        (legacy_path / "Chart.yaml").write_text("name: nginx\nversion: 1.0.0")

        app = HelmApp(
            type="helm",
            chart="bitnami/nginx",
            namespace="default",
        )

        output = MagicMock(spec=OutputManager)

        # Act
        result = deploy_helm_app(
            app_name="nginx",
            app=app,
            base_dir=tmp_path,
            charts_dir=charts_dir,
            build_dir=tmp_path / "build",
            app_config_dir=tmp_path / "config",
            output=output,
            dry_run=False,
        )

        # Assert
        assert result is False
        # Verify error output was called
        output.print_error.assert_called()

    @patch("sbkube.commands.deploy.run_command")
    def test_legacy_v070_path_detected(self, mock_run_command, tmp_path: Path) -> None:
        """Test detection of v0.7.0 legacy chart path."""
        # Arrange
        charts_dir = tmp_path / "charts"
        charts_dir.mkdir(exist_ok=True)

        # Create legacy v0.7.0 path structure: charts/nginx/nginx/
        legacy_outer = charts_dir / "nginx"
        legacy_outer.mkdir(exist_ok=True)
        legacy_inner = legacy_outer / "nginx"
        legacy_inner.mkdir(exist_ok=True)
        (legacy_inner / "Chart.yaml").write_text("name: nginx\nversion: 1.0.0")

        app = HelmApp(
            type="helm",
            chart="bitnami/nginx",
            namespace="default",
        )

        output = MagicMock(spec=OutputManager)

        # Act
        result = deploy_helm_app(
            app_name="nginx",
            app=app,
            base_dir=tmp_path,
            charts_dir=charts_dir,
            build_dir=tmp_path / "build",
            app_config_dir=tmp_path / "config",
            output=output,
            dry_run=False,
        )

        # Assert
        assert result is False
        # Verify error output was called
        output.print_error.assert_called()

    @patch("sbkube.commands.deploy.run_command")
    def test_chart_not_found_no_legacy(self, mock_run_command, tmp_path: Path) -> None:
        """Test error when chart not found and no legacy paths exist."""
        # Arrange
        charts_dir = tmp_path / "charts"
        charts_dir.mkdir(exist_ok=True)

        app = HelmApp(
            type="helm",
            chart="bitnami/nginx",
            namespace="default",
        )

        output = MagicMock(spec=OutputManager)

        # Act
        result = deploy_helm_app(
            app_name="nginx",
            app=app,
            base_dir=tmp_path,
            charts_dir=charts_dir,
            build_dir=tmp_path / "build",
            app_config_dir=tmp_path / "config",
            output=output,
            dry_run=False,
        )

        # Assert
        assert result is False
        output.print_error.assert_called()


class TestNamespaceCreation:
    """Test namespace creation scenarios."""

    @patch("sbkube.commands.deploy.run_command")
    def test_namespace_created_manually_when_missing(
        self, mock_run_command, tmp_path: Path
    ) -> None:
        """Test namespace is created manually when missing and create_namespace=False."""
        # Arrange
        build_dir = tmp_path / "build"
        build_dir.mkdir(exist_ok=True)
        app_build_dir = build_dir / "nginx"
        app_build_dir.mkdir(exist_ok=True)
        (app_build_dir / "Chart.yaml").write_text("name: nginx")

        app = HelmApp(
            type="helm",
            chart="bitnami/nginx",
            namespace="custom-ns",
            create_namespace=False,  # Manual creation via kubectl
        )

        # Mock responses:
        # 1. Namespace check fails (doesn't exist)
        # 2. Namespace creation succeeds
        # 3. Helm upgrade succeeds
        mock_run_command.side_effect = [
            (1, "", "namespace not found"),  # namespace check
            (0, "namespace created", ""),     # namespace create
            (0, "Release installed", ""),     # helm upgrade
        ]
        output = MagicMock(spec=OutputManager)

        # Act
        result = deploy_helm_app(
            app_name="nginx",
            app=app,
            base_dir=tmp_path,
            charts_dir=tmp_path / "charts",
            build_dir=build_dir,
            app_config_dir=tmp_path / "config",
            output=output,
            dry_run=False,
        )

        # Assert
        assert result is True
        # Should have 3 calls: namespace check, namespace create, helm upgrade
        assert mock_run_command.call_count == 3

    @patch("sbkube.commands.deploy.run_command")
    def test_namespace_creation_fails(self, mock_run_command, tmp_path: Path) -> None:
        """Test deployment fails when namespace creation fails."""
        # Arrange
        build_dir = tmp_path / "build"
        build_dir.mkdir(exist_ok=True)
        app_build_dir = build_dir / "nginx"
        app_build_dir.mkdir(exist_ok=True)
        (app_build_dir / "Chart.yaml").write_text("name: nginx")

        app = HelmApp(
            type="helm",
            chart="bitnami/nginx",
            namespace="custom-ns",
            create_namespace=False,  # Don't use helm's --create-namespace
        )

        # Mock responses:
        # 1. Namespace check fails (doesn't exist)
        # 2. Namespace creation fails
        mock_run_command.side_effect = [
            (1, "", "namespace not found"),  # namespace check
            (1, "", "permission denied"),    # namespace create fails
        ]
        output = MagicMock(spec=OutputManager)

        # Act
        result = deploy_helm_app(
            app_name="nginx",
            app=app,
            base_dir=tmp_path,
            charts_dir=tmp_path / "charts",
            build_dir=build_dir,
            app_config_dir=tmp_path / "config",
            output=output,
            dry_run=False,
        )

        # Assert
        assert result is False
        output.print_error.assert_called()

    @patch("sbkube.commands.deploy.run_command")
    def test_dry_run_skips_namespace_creation(
        self, mock_run_command, tmp_path: Path
    ) -> None:
        """Test dry-run mode skips namespace creation."""
        # Arrange
        build_dir = tmp_path / "build"
        build_dir.mkdir(exist_ok=True)
        app_build_dir = build_dir / "nginx"
        app_build_dir.mkdir(exist_ok=True)
        (app_build_dir / "Chart.yaml").write_text("name: nginx")

        app = HelmApp(
            type="helm",
            chart="bitnami/nginx",
            namespace="custom-ns",
        )

        # Mock responses:
        # 1. Namespace check fails (doesn't exist)
        # 2. Helm dry-run succeeds
        mock_run_command.side_effect = [
            (1, "", "namespace not found"),  # namespace check
            (0, "Dry-run output", ""),       # helm dry-run
        ]
        output = MagicMock(spec=OutputManager)

        # Act
        result = deploy_helm_app(
            app_name="nginx",
            app=app,
            base_dir=tmp_path,
            charts_dir=tmp_path / "charts",
            build_dir=build_dir,
            app_config_dir=tmp_path / "config",
            output=output,
            dry_run=True,
        )

        # Assert
        assert result is True
        # Should only have 2 calls: namespace check + helm dry-run
        # No namespace creation in dry-run mode
        assert mock_run_command.call_count == 2


class TestDeploymentTimeout:
    """Test deployment timeout scenarios."""

    @patch("sbkube.commands.deploy.run_command")
    def test_helm_deployment_timeout(self, mock_run_command, tmp_path: Path) -> None:
        """Test timeout detection and error message."""
        # Arrange
        build_dir = tmp_path / "build"
        build_dir.mkdir(exist_ok=True)
        app_build_dir = build_dir / "nginx"
        app_build_dir.mkdir(exist_ok=True)
        (app_build_dir / "Chart.yaml").write_text("name: nginx")

        app = HelmApp(
            type="helm",
            chart="bitnami/nginx",
            namespace="default",
        )

        # Mock responses:
        # 1. Namespace check succeeds
        # 2. Helm command times out (return code -1)
        mock_run_command.side_effect = [
            (0, "", ""),  # namespace check succeeds
            (-1, "", "Timeout expired after 300 seconds"),  # helm timeout
        ]
        output = MagicMock(spec=OutputManager)

        # Act
        result = deploy_helm_app(
            app_name="nginx",
            app=app,
            base_dir=tmp_path,
            charts_dir=tmp_path / "charts",
            build_dir=build_dir,
            app_config_dir=tmp_path / "config",
            output=output,
            dry_run=False,
        )

        # Assert
        assert result is False
        # Verify timeout error was printed
        output.print_error.assert_called()
        # Check that error message contains timeout info
        call_args = output.print_error.call_args
        assert "timeout" in str(call_args).lower()


class TestKeyboardInterrupt:
    """Test keyboard interrupt (Ctrl+C) handling."""

    @patch("sbkube.commands.deploy.run_command")
    def test_keyboard_interrupt_during_deployment(
        self, mock_run_command, tmp_path: Path
    ) -> None:
        """Test that KeyboardInterrupt is properly re-raised."""
        # Arrange
        build_dir = tmp_path / "build"
        build_dir.mkdir(exist_ok=True)
        app_build_dir = build_dir / "nginx"
        app_build_dir.mkdir(exist_ok=True)
        (app_build_dir / "Chart.yaml").write_text("name: nginx")

        app = HelmApp(
            type="helm",
            chart="bitnami/nginx",
            namespace="default",
        )

        # Mock run_command to raise KeyboardInterrupt
        mock_run_command.side_effect = [
            (0, "", ""),  # namespace check succeeds
            KeyboardInterrupt(),  # User presses Ctrl+C during helm command
        ]
        output = MagicMock(spec=OutputManager)

        # Act & Assert
        with pytest.raises(KeyboardInterrupt):
            deploy_helm_app(
                app_name="nginx",
                app=app,
                base_dir=tmp_path,
                charts_dir=tmp_path / "charts",
                build_dir=build_dir,
                app_config_dir=tmp_path / "config",
                output=output,
                dry_run=False,
            )


class TestHelmDeploymentOptions:
    """Test various Helm deployment options."""

    @patch("sbkube.commands.deploy.run_command")
    def test_helm_wait_option(self, mock_run_command, tmp_path: Path) -> None:
        """Test deployment with --wait option."""
        # Arrange
        build_dir = tmp_path / "build"
        build_dir.mkdir(exist_ok=True)
        app_build_dir = build_dir / "nginx"
        app_build_dir.mkdir(exist_ok=True)
        (app_build_dir / "Chart.yaml").write_text("name: nginx")

        app = HelmApp(
            type="helm",
            chart="bitnami/nginx",
            namespace="default",
            wait=True,
        )

        mock_run_command.return_value = (0, "Release installed", "")
        output = MagicMock(spec=OutputManager)

        # Act
        result = deploy_helm_app(
            app_name="nginx",
            app=app,
            base_dir=tmp_path,
            charts_dir=tmp_path / "charts",
            build_dir=build_dir,
            app_config_dir=tmp_path / "config",
            output=output,
            dry_run=False,
        )

        # Assert
        assert result is True
        # Find helm command in calls
        helm_cmd = None
        for call_args in mock_run_command.call_args_list:
            cmd = call_args[0][0]
            if "helm" in cmd:
                helm_cmd = cmd
                break
        assert helm_cmd is not None
        assert "--wait" in helm_cmd

    @patch("sbkube.commands.deploy.run_command")
    def test_helm_timeout_option(self, mock_run_command, tmp_path: Path) -> None:
        """Test deployment with --timeout option."""
        # Arrange
        build_dir = tmp_path / "build"
        build_dir.mkdir(exist_ok=True)
        app_build_dir = build_dir / "nginx"
        app_build_dir.mkdir(exist_ok=True)
        (app_build_dir / "Chart.yaml").write_text("name: nginx")

        app = HelmApp(
            type="helm",
            chart="bitnami/nginx",
            namespace="default",
            timeout="10m",
        )

        mock_run_command.return_value = (0, "Release installed", "")
        output = MagicMock(spec=OutputManager)

        # Act
        result = deploy_helm_app(
            app_name="nginx",
            app=app,
            base_dir=tmp_path,
            charts_dir=tmp_path / "charts",
            build_dir=build_dir,
            app_config_dir=tmp_path / "config",
            output=output,
            dry_run=False,
        )

        # Assert
        assert result is True
        # Find helm command in calls
        helm_cmd = None
        for call_args in mock_run_command.call_args_list:
            cmd = call_args[0][0]
            if "helm" in cmd:
                helm_cmd = cmd
                break
        assert helm_cmd is not None
        assert "--timeout" in helm_cmd
        assert "10m" in helm_cmd

    @patch("sbkube.commands.deploy.run_command")
    def test_helm_create_namespace_flag(self, mock_run_command, tmp_path: Path) -> None:
        """Test deployment with --create-namespace flag."""
        # Arrange
        build_dir = tmp_path / "build"
        build_dir.mkdir(exist_ok=True)
        app_build_dir = build_dir / "nginx"
        app_build_dir.mkdir(exist_ok=True)
        (app_build_dir / "Chart.yaml").write_text("name: nginx")

        app = HelmApp(
            type="helm",
            chart="bitnami/nginx",
            namespace="custom-ns",
            create_namespace=True,
        )

        mock_run_command.return_value = (0, "Release installed", "")
        output = MagicMock(spec=OutputManager)

        # Act
        result = deploy_helm_app(
            app_name="nginx",
            app=app,
            base_dir=tmp_path,
            charts_dir=tmp_path / "charts",
            build_dir=build_dir,
            app_config_dir=tmp_path / "config",
            output=output,
            dry_run=False,
        )

        # Assert
        assert result is True
        # Find helm command in calls
        helm_cmd = None
        for call_args in mock_run_command.call_args_list:
            cmd = call_args[0][0]
            if "helm" in cmd:
                helm_cmd = cmd
                break
        assert helm_cmd is not None
        assert "--create-namespace" in helm_cmd
