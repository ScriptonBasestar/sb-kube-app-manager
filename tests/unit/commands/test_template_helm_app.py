"""Unit tests for template.py - template_helm_app function.

Tests verify:
- Helm chart rendering with helm template
- Chart path resolution (build/ → charts/ → local)
- Values files application
- Set values application
- Cluster global values (v0.7.0+)
- Namespace handling
- Error scenarios
"""

from pathlib import Path
from unittest.mock import MagicMock, patch

from sbkube.commands.template import template_helm_app
from sbkube.models.config_model import HelmApp
from sbkube.utils.output_manager import OutputManager


class TestTemplateHelmAppBasic:
    """Test basic Helm template rendering."""

    @patch("sbkube.commands.template.run_command")
    def test_template_from_build_directory(
        self, mock_run_command, tmp_path: Path
    ) -> None:
        """Test rendering from build/ directory (after build command)."""
        # Arrange
        build_dir = tmp_path / "build"
        build_dir.mkdir(exist_ok=True)

        app_build_dir = build_dir / "nginx"
        app_build_dir.mkdir(exist_ok=True)
        (app_build_dir / "Chart.yaml").write_text("name: nginx\nversion: 1.0.0")
        (app_build_dir / "values.yaml").write_text("replicaCount: 1")

        rendered_dir = tmp_path / "rendered"
        rendered_dir.mkdir(exist_ok=True)

        app = HelmApp(
            type="helm",
            chart="bitnami/nginx",
            namespace="default",
        )

        # Mock helm template output
        helm_output = """apiVersion: apps/v1
kind: Deployment
metadata:
  name: nginx"""
        mock_run_command.return_value = (0, helm_output, "")
        output = MagicMock(spec=OutputManager)

        # Act
        result = template_helm_app(
            app_name="nginx",
            app=app,
            base_dir=tmp_path,
            charts_dir=tmp_path / "charts",
            build_dir=build_dir,
            app_config_dir=tmp_path / "config",
            rendered_dir=rendered_dir,
            output=output,
        )

        # Assert
        assert result is True
        # Verify rendered file was created
        rendered_file = rendered_dir / "nginx.yaml"
        assert rendered_file.exists()
        assert "apiVersion: apps/v1" in rendered_file.read_text()

        # Verify helm template was called
        mock_run_command.assert_called()
        call_args = mock_run_command.call_args[0][0]
        assert "helm" in call_args
        assert "template" in call_args

    @patch("sbkube.commands.template.run_command")
    def test_template_from_remote_chart(
        self, mock_run_command, tmp_path: Path
    ) -> None:
        """Test rendering from charts/ directory (no build/)."""
        # Arrange
        charts_dir = tmp_path / "charts"
        charts_dir.mkdir(exist_ok=True)

        # Create remote chart in charts/
        chart_dir = charts_dir / "bitnami" / "nginx-15.0.0"
        chart_dir.mkdir(parents=True, exist_ok=True)
        (chart_dir / "Chart.yaml").write_text("name: nginx\nversion: 15.0.0")
        (chart_dir / "values.yaml").write_text("replicaCount: 1")

        build_dir = tmp_path / "build"  # Empty build dir
        build_dir.mkdir(exist_ok=True)

        rendered_dir = tmp_path / "rendered"
        rendered_dir.mkdir(exist_ok=True)

        app = HelmApp(
            type="helm",
            chart="bitnami/nginx",
            version="15.0.0",
            namespace="default",
        )

        helm_output = "apiVersion: apps/v1\nkind: Deployment"
        mock_run_command.return_value = (0, helm_output, "")
        output = MagicMock(spec=OutputManager)

        # Act
        result = template_helm_app(
            app_name="nginx",
            app=app,
            base_dir=tmp_path,
            charts_dir=charts_dir,
            build_dir=build_dir,
            app_config_dir=tmp_path / "config",
            rendered_dir=rendered_dir,
            output=output,
        )

        # Assert
        assert result is True
        assert (rendered_dir / "nginx.yaml").exists()

    @patch("sbkube.commands.template.run_command")
    def test_template_from_local_chart(self, mock_run_command, tmp_path: Path) -> None:
        """Test rendering from local chart (relative path)."""
        # Arrange
        app_config_dir = tmp_path / "config"
        app_config_dir.mkdir(exist_ok=True)

        local_chart_dir = app_config_dir / "my-chart"
        local_chart_dir.mkdir(exist_ok=True)
        (local_chart_dir / "Chart.yaml").write_text("name: my-chart\nversion: 1.0.0")
        (local_chart_dir / "values.yaml").write_text("replicaCount: 2")

        build_dir = tmp_path / "build"
        build_dir.mkdir(exist_ok=True)

        rendered_dir = tmp_path / "rendered"
        rendered_dir.mkdir(exist_ok=True)

        app = HelmApp(
            type="helm",
            chart="./my-chart",  # Local chart
            namespace="default",
        )

        helm_output = "apiVersion: apps/v1\nkind: Deployment"
        mock_run_command.return_value = (0, helm_output, "")
        output = MagicMock(spec=OutputManager)

        # Act
        result = template_helm_app(
            app_name="my-chart",
            app=app,
            base_dir=tmp_path,
            charts_dir=tmp_path / "charts",
            build_dir=build_dir,
            app_config_dir=app_config_dir,
            rendered_dir=rendered_dir,
            output=output,
        )

        # Assert
        assert result is True
        assert (rendered_dir / "my-chart.yaml").exists()


class TestTemplateHelmAppValues:
    """Test values files and set values."""

    @patch("sbkube.commands.template.run_command")
    def test_template_with_values_file(self, mock_run_command, tmp_path: Path) -> None:
        """Test rendering with values file."""
        # Arrange
        build_dir = tmp_path / "build"
        build_dir.mkdir(exist_ok=True)
        app_build_dir = build_dir / "nginx"
        app_build_dir.mkdir(exist_ok=True)
        (app_build_dir / "Chart.yaml").write_text("name: nginx")

        app_config_dir = tmp_path / "config"
        app_config_dir.mkdir(exist_ok=True)
        values_file = app_config_dir / "custom-values.yaml"
        values_file.write_text("replicaCount: 5")

        rendered_dir = tmp_path / "rendered"
        rendered_dir.mkdir(exist_ok=True)

        app = HelmApp(
            type="helm",
            chart="bitnami/nginx",
            namespace="default",
            values=["custom-values.yaml"],
        )

        helm_output = "apiVersion: apps/v1"
        mock_run_command.return_value = (0, helm_output, "")
        output = MagicMock(spec=OutputManager)

        # Act
        result = template_helm_app(
            app_name="nginx",
            app=app,
            base_dir=tmp_path,
            charts_dir=tmp_path / "charts",
            build_dir=build_dir,
            app_config_dir=app_config_dir,
            rendered_dir=rendered_dir,
            output=output,
        )

        # Assert
        assert result is True
        # Verify --values was passed
        call_args = mock_run_command.call_args[0][0]
        assert "--values" in call_args
        assert any("custom-values.yaml" in str(arg) for arg in call_args)

    @patch("sbkube.commands.template.run_command")
    def test_template_with_set_values(self, mock_run_command, tmp_path: Path) -> None:
        """Test rendering with --set values."""
        # Arrange
        build_dir = tmp_path / "build"
        build_dir.mkdir(exist_ok=True)
        app_build_dir = build_dir / "nginx"
        app_build_dir.mkdir(exist_ok=True)
        (app_build_dir / "Chart.yaml").write_text("name: nginx")

        rendered_dir = tmp_path / "rendered"
        rendered_dir.mkdir(exist_ok=True)

        app = HelmApp(
            type="helm",
            chart="bitnami/nginx",
            namespace="default",
            set_values={"replicaCount": "3", "image.tag": "latest"},
        )

        helm_output = "apiVersion: apps/v1"
        mock_run_command.return_value = (0, helm_output, "")
        output = MagicMock(spec=OutputManager)

        # Act
        result = template_helm_app(
            app_name="nginx",
            app=app,
            base_dir=tmp_path,
            charts_dir=tmp_path / "charts",
            build_dir=build_dir,
            app_config_dir=tmp_path / "config",
            rendered_dir=rendered_dir,
            output=output,
        )

        # Assert
        assert result is True
        # Verify --set was passed
        call_args = mock_run_command.call_args[0][0]
        assert "--set" in call_args
        assert "replicaCount=3" in call_args
        assert "image.tag=latest" in call_args

    @patch("sbkube.commands.template.run_command")
    def test_template_with_cluster_global_values(
        self, mock_run_command, tmp_path: Path
    ) -> None:
        """Test rendering with cluster global values (v0.7.0+)."""
        # Arrange
        build_dir = tmp_path / "build"
        build_dir.mkdir(exist_ok=True)
        app_build_dir = build_dir / "nginx"
        app_build_dir.mkdir(exist_ok=True)
        (app_build_dir / "Chart.yaml").write_text("name: nginx")

        rendered_dir = tmp_path / "rendered"
        rendered_dir.mkdir(exist_ok=True)

        app = HelmApp(
            type="helm",
            chart="bitnami/nginx",
            namespace="default",
        )

        cluster_global_values = {
            "global": {"environment": "production", "region": "us-west-2"}
        }

        helm_output = "apiVersion: apps/v1"
        mock_run_command.return_value = (0, helm_output, "")
        output = MagicMock(spec=OutputManager)

        # Act
        result = template_helm_app(
            app_name="nginx",
            app=app,
            base_dir=tmp_path,
            charts_dir=tmp_path / "charts",
            build_dir=build_dir,
            app_config_dir=tmp_path / "config",
            rendered_dir=rendered_dir,
            output=output,
            cluster_global_values=cluster_global_values,
        )

        # Assert
        assert result is True
        # Verify cluster global values were applied
        call_args = mock_run_command.call_args[0][0]
        # Should have --values pointing to temp file with cluster global values
        values_count = call_args.count("--values")
        assert values_count >= 1  # At least cluster global values

    @patch("sbkube.commands.template.run_command")
    def test_template_with_values_file_not_found(
        self, mock_run_command, tmp_path: Path
    ) -> None:
        """Test warning when values file doesn't exist."""
        # Arrange
        build_dir = tmp_path / "build"
        build_dir.mkdir(exist_ok=True)
        app_build_dir = build_dir / "nginx"
        app_build_dir.mkdir(exist_ok=True)
        (app_build_dir / "Chart.yaml").write_text("name: nginx")

        app_config_dir = tmp_path / "config"
        app_config_dir.mkdir(exist_ok=True)

        rendered_dir = tmp_path / "rendered"
        rendered_dir.mkdir(exist_ok=True)

        app = HelmApp(
            type="helm",
            chart="bitnami/nginx",
            namespace="default",
            values=["nonexistent.yaml"],
        )

        helm_output = "apiVersion: apps/v1"
        mock_run_command.return_value = (0, helm_output, "")
        output = MagicMock(spec=OutputManager)

        # Act
        result = template_helm_app(
            app_name="nginx",
            app=app,
            base_dir=tmp_path,
            charts_dir=tmp_path / "charts",
            build_dir=build_dir,
            app_config_dir=app_config_dir,
            rendered_dir=rendered_dir,
            output=output,
        )

        # Assert
        assert result is True  # Still succeeds but prints warning
        output.print_warning.assert_called()
        warning_msg = str(output.print_warning.call_args)
        assert "values file not found" in warning_msg.lower()


class TestTemplateHelmAppErrors:
    """Test error scenarios."""

    def test_chart_not_found(self, tmp_path: Path) -> None:
        """Test error when chart not found in any location."""
        # Arrange
        build_dir = tmp_path / "build"
        build_dir.mkdir(exist_ok=True)

        charts_dir = tmp_path / "charts"
        charts_dir.mkdir(exist_ok=True)

        rendered_dir = tmp_path / "rendered"
        rendered_dir.mkdir(exist_ok=True)

        app = HelmApp(
            type="helm",
            chart="nonexistent/chart",
            namespace="default",
        )

        output = MagicMock(spec=OutputManager)

        # Act
        result = template_helm_app(
            app_name="nonexistent",
            app=app,
            base_dir=tmp_path,
            charts_dir=charts_dir,
            build_dir=build_dir,
            app_config_dir=tmp_path / "config",
            rendered_dir=rendered_dir,
            output=output,
        )

        # Assert
        assert result is False
        output.print_error.assert_called()
        error_msg = str(output.print_error.call_args)
        assert "chart not found" in error_msg.lower()

    @patch("sbkube.commands.template.run_command")
    def test_helm_template_command_failure(
        self, mock_run_command, tmp_path: Path
    ) -> None:
        """Test handling of helm template command failure."""
        # Arrange
        build_dir = tmp_path / "build"
        build_dir.mkdir(exist_ok=True)
        app_build_dir = build_dir / "nginx"
        app_build_dir.mkdir(exist_ok=True)
        (app_build_dir / "Chart.yaml").write_text("name: nginx")

        rendered_dir = tmp_path / "rendered"
        rendered_dir.mkdir(exist_ok=True)

        app = HelmApp(
            type="helm",
            chart="bitnami/nginx",
            namespace="default",
        )

        # Mock helm template failure
        mock_run_command.return_value = (1, "", "Error: invalid chart")
        output = MagicMock(spec=OutputManager)

        # Act
        result = template_helm_app(
            app_name="nginx",
            app=app,
            base_dir=tmp_path,
            charts_dir=tmp_path / "charts",
            build_dir=build_dir,
            app_config_dir=tmp_path / "config",
            rendered_dir=rendered_dir,
            output=output,
        )

        # Assert
        assert result is False
        output.print_error.assert_called()

    @patch("sbkube.commands.template.run_command")
    def test_helm_template_exception(self, mock_run_command, tmp_path: Path) -> None:
        """Test handling of exception during helm template."""
        # Arrange
        build_dir = tmp_path / "build"
        build_dir.mkdir(exist_ok=True)
        app_build_dir = build_dir / "nginx"
        app_build_dir.mkdir(exist_ok=True)
        (app_build_dir / "Chart.yaml").write_text("name: nginx")

        rendered_dir = tmp_path / "rendered"
        rendered_dir.mkdir(exist_ok=True)

        app = HelmApp(
            type="helm",
            chart="bitnami/nginx",
            namespace="default",
        )

        # Mock exception
        mock_run_command.side_effect = Exception("Unexpected error")
        output = MagicMock(spec=OutputManager)

        # Act
        result = template_helm_app(
            app_name="nginx",
            app=app,
            base_dir=tmp_path,
            charts_dir=tmp_path / "charts",
            build_dir=build_dir,
            app_config_dir=tmp_path / "config",
            rendered_dir=rendered_dir,
            output=output,
        )

        # Assert
        assert result is False
        output.print_error.assert_called()
        error_msg = str(output.print_error.call_args)
        assert "template rendering failed" in error_msg.lower()


class TestTemplateHelmAppNamespace:
    """Test namespace handling."""

    @patch("sbkube.commands.template.run_command")
    def test_template_with_namespace(self, mock_run_command, tmp_path: Path) -> None:
        """Test rendering with namespace specified."""
        # Arrange
        build_dir = tmp_path / "build"
        build_dir.mkdir(exist_ok=True)
        app_build_dir = build_dir / "nginx"
        app_build_dir.mkdir(exist_ok=True)
        (app_build_dir / "Chart.yaml").write_text("name: nginx")

        rendered_dir = tmp_path / "rendered"
        rendered_dir.mkdir(exist_ok=True)

        app = HelmApp(
            type="helm",
            chart="bitnami/nginx",
            namespace="custom-ns",
        )

        helm_output = "apiVersion: apps/v1"
        mock_run_command.return_value = (0, helm_output, "")
        output = MagicMock(spec=OutputManager)

        # Act
        result = template_helm_app(
            app_name="nginx",
            app=app,
            base_dir=tmp_path,
            charts_dir=tmp_path / "charts",
            build_dir=build_dir,
            app_config_dir=tmp_path / "config",
            rendered_dir=rendered_dir,
            output=output,
        )

        # Assert
        assert result is True
        # Verify --namespace was passed
        call_args = mock_run_command.call_args[0][0]
        assert "--namespace" in call_args
        assert "custom-ns" in call_args

    @patch("sbkube.commands.template.run_command")
    def test_template_with_release_name(
        self, mock_run_command, tmp_path: Path
    ) -> None:
        """Test rendering with custom release name."""
        # Arrange
        build_dir = tmp_path / "build"
        build_dir.mkdir(exist_ok=True)
        app_build_dir = build_dir / "nginx"
        app_build_dir.mkdir(exist_ok=True)
        (app_build_dir / "Chart.yaml").write_text("name: nginx")

        rendered_dir = tmp_path / "rendered"
        rendered_dir.mkdir(exist_ok=True)

        app = HelmApp(
            type="helm",
            chart="bitnami/nginx",
            namespace="default",
            release_name="my-release",
        )

        helm_output = "apiVersion: apps/v1"
        mock_run_command.return_value = (0, helm_output, "")
        output = MagicMock(spec=OutputManager)

        # Act
        result = template_helm_app(
            app_name="nginx",
            app=app,
            base_dir=tmp_path,
            charts_dir=tmp_path / "charts",
            build_dir=build_dir,
            app_config_dir=tmp_path / "config",
            rendered_dir=rendered_dir,
            output=output,
        )

        # Assert
        assert result is True
        # Verify release name was used
        call_args = mock_run_command.call_args[0][0]
        assert "my-release" in call_args
