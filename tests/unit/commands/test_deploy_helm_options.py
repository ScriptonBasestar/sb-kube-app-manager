"""Unit tests for various Helm deployment options.

Tests verify:
- Atomic deployments
- Combined deployment options
- Progress tracking
"""

from pathlib import Path
from unittest.mock import MagicMock, patch

from sbkube.commands.deploy import deploy_helm_app
from sbkube.models.config_model import HelmApp
from sbkube.utils.output_manager import OutputManager


class TestHelmAtomicDeployment:
    """Test atomic deployment option."""

    @patch("sbkube.commands.deploy.run_command")
    def test_atomic_option(self, mock_run_command, tmp_path: Path) -> None:
        """Test deployment with --atomic option."""
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
            atomic=True,
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
        assert "--atomic" in helm_cmd


class TestHelmCombinedOptions:
    """Test combinations of Helm options."""

    @patch("sbkube.commands.deploy.run_command")
    def test_wait_and_timeout_combined(
        self, mock_run_command, tmp_path: Path
    ) -> None:
        """Test deployment with both --wait and --timeout options."""
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
        assert "--wait" in helm_cmd
        assert "--timeout" in helm_cmd
        assert "10m" in helm_cmd

    @patch("sbkube.commands.deploy.run_command")
    def test_all_options_combined(self, mock_run_command, tmp_path: Path) -> None:
        """Test deployment with all Helm options enabled."""
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
            wait=True,
            timeout="15m",
            atomic=True,
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
        assert "--wait" in helm_cmd
        assert "--timeout" in helm_cmd
        assert "15m" in helm_cmd
        assert "--atomic" in helm_cmd


class TestHelmDeploymentSuccess:
    """Test successful deployment paths."""

    @patch("sbkube.commands.deploy.run_command")
    def test_successful_deployment_output(
        self, mock_run_command, tmp_path: Path
    ) -> None:
        """Test success message is printed after successful deployment."""
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
            release_name="my-nginx",
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
        # Verify success message was printed
        output.print_success.assert_called_once()
        call_args = output.print_success.call_args[0][0]
        assert "nginx" in call_args
        assert "my-nginx" in call_args
