"""Unit tests for deploy_helm_app() function.

Tests verify Helm app deployment with various scenarios:
- Basic deployment with built chart
- Remote chart deployment
- Dry-run mode
- Custom release names
- Error handling
"""

from pathlib import Path
from unittest.mock import MagicMock, patch

from sbkube.commands.deploy import deploy_helm_app
from sbkube.models.config_model import HelmApp
from sbkube.utils.output_manager import OutputManager


class TestDeployHelmAppBasic:
    """Test basic deployment scenarios."""

    @patch("sbkube.commands.deploy.run_command")
    def test_deploy_with_built_chart(self, mock_run_command, tmp_path: Path) -> None:
        """Test deployment using built chart from .sbkube/build/."""
        # Arrange
        build_dir = tmp_path / "build"
        build_dir.mkdir(exist_ok=True)
        app_build_dir = build_dir / "nginx"
        app_build_dir.mkdir(exist_ok=True)
        (app_build_dir / "Chart.yaml").write_text("name: nginx\nversion: 1.0.0")

        app = HelmApp(
            type="helm",
            chart="bitnami/nginx",
            version="15.0.0",
            namespace="default",
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
        assert mock_run_command.call_count >= 2  # namespace check + helm upgrade
        # Check helm command (usually second call)
        helm_cmd = None
        for call_args in mock_run_command.call_args_list:
            cmd = call_args[0][0]
            if "helm" in cmd:
                helm_cmd = cmd
                break
        assert helm_cmd is not None
        assert "upgrade" in helm_cmd
        assert "--install" in helm_cmd
        assert str(app_build_dir) in helm_cmd

    @patch("sbkube.commands.deploy.run_command")
    def test_deploy_with_remote_chart(self, mock_run_command, tmp_path: Path) -> None:
        """Test deployment using remote chart from .sbkube/charts/."""
        # Arrange
        charts_dir = tmp_path / "charts"
        charts_dir.mkdir(exist_ok=True)
        repo_dir = charts_dir / "bitnami"
        repo_dir.mkdir(exist_ok=True)
        chart_dir = repo_dir / "nginx-15.0.0"
        chart_dir.mkdir(exist_ok=True)
        (chart_dir / "Chart.yaml").write_text("name: nginx\nversion: 15.0.0")

        app = HelmApp(
            type="helm",
            chart="bitnami/nginx",
            version="15.0.0",
            namespace="default",
        )

        mock_run_command.return_value = (0, "Release installed", "")
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
        assert result is True
        helm_cmd = None
        for call_args in mock_run_command.call_args_list:
            cmd = call_args[0][0]
            if "helm" in cmd:
                helm_cmd = cmd
                break
        assert helm_cmd is not None
        assert str(chart_dir) in helm_cmd

    @patch("sbkube.commands.deploy.run_command")
    def test_deploy_with_custom_release_name(
        self, mock_run_command, tmp_path: Path
    ) -> None:
        """Test deployment with custom release name."""
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
            release_name="my-nginx-release",
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
        helm_cmd = None
        for call_args in mock_run_command.call_args_list:
            cmd = call_args[0][0]
            if "helm" in cmd:
                helm_cmd = cmd
                break
        assert helm_cmd is not None
        assert "my-nginx-release" in helm_cmd


class TestDeployHelmAppDryRun:
    """Test dry-run mode."""

    @patch("sbkube.commands.deploy.run_command")
    def test_dry_run_mode(self, mock_run_command, tmp_path: Path) -> None:
        """Test deployment in dry-run mode."""
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

        mock_run_command.return_value = (0, "Dry-run output", "")
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
        helm_cmd = None
        for call_args in mock_run_command.call_args_list:
            cmd = call_args[0][0]
            if "helm" in cmd:
                helm_cmd = cmd
                break
        assert helm_cmd is not None
        assert "--dry-run" in helm_cmd


class TestDeployHelmAppErrorHandling:
    """Test error handling scenarios."""

    @patch("sbkube.commands.deploy.run_command")
    def test_handles_helm_command_failure(
        self, mock_run_command, tmp_path: Path
    ) -> None:
        """Test handling of helm command failures."""
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

        # Simulate helm failure (non-connection error)
        mock_run_command.return_value = (1, "", "Error: chart not found")
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


class TestDeployHelmAppValues:
    """Test values file handling."""

    @patch("sbkube.commands.deploy.run_command")
    def test_deploy_with_values_files(self, mock_run_command, tmp_path: Path) -> None:
        """Test deployment with custom values files."""
        # Arrange
        build_dir = tmp_path / "build"
        build_dir.mkdir(exist_ok=True)
        app_build_dir = build_dir / "nginx"
        app_build_dir.mkdir(exist_ok=True)
        (app_build_dir / "Chart.yaml").write_text("name: nginx")

        values_dir = tmp_path / "config" / "nginx"
        values_dir.mkdir(parents=True, exist_ok=True)
        (values_dir / "values.yaml").write_text("replicas: 3")

        app = HelmApp(
            type="helm",
            chart="bitnami/nginx",
            namespace="default",
            values=["values.yaml"],  # Correct field name
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
        # Verify helm command was called
        helm_called = False
        for call_args in mock_run_command.call_args_list:
            cmd = call_args[0][0]
            if "helm" in cmd:
                helm_called = True
                break
        assert helm_called

    @patch("sbkube.commands.deploy.run_command")
    def test_deploy_with_set_values(self, mock_run_command, tmp_path: Path) -> None:
        """Test deployment with --set values."""
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
            set_values={"replicaCount": 3, "image.tag": "latest"},
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
        helm_cmd = None
        for call_args in mock_run_command.call_args_list:
            cmd = call_args[0][0]
            if "helm" in cmd:
                helm_cmd = cmd
                break
        assert helm_cmd is not None
        assert "--set" in helm_cmd
