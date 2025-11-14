"""Unit tests for deploy.py cluster global values feature.

Tests verify:
- Cluster global values file creation and cleanup
- Cluster values integration with Helm
"""

from pathlib import Path
from unittest.mock import MagicMock, patch

import pytest

from sbkube.commands.deploy import deploy_helm_app
from sbkube.models.config_model import HelmApp
from sbkube.utils.output_manager import OutputManager


class TestClusterGlobalValues:
    """Test cluster global values feature."""

    @patch("sbkube.commands.deploy.run_command")
    def test_cluster_values_injected(self, mock_run_command, tmp_path: Path) -> None:
        """Test that cluster global values are injected into Helm command."""
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

        cluster_global_values = {
            "global": {
                "storageClass": "fast-ssd",
                "imageRegistry": "registry.example.com",
            }
        }

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
            cluster_global_values=cluster_global_values,
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
        # Verify --values flag was added (temp file for cluster values)
        assert "--values" in helm_cmd

    @patch("sbkube.commands.deploy.run_command")
    def test_cluster_values_temp_file_cleanup(
        self, mock_run_command, tmp_path: Path
    ) -> None:
        """Test that cluster values temp file is cleaned up after deployment."""
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

        cluster_global_values = {"global": {"env": "production"}}

        mock_run_command.return_value = (0, "Release installed", "")
        output = MagicMock(spec=OutputManager)

        # Track temp files created during deployment
        import tempfile

        original_tempfile = tempfile.NamedTemporaryFile
        temp_files_created = []

        def track_tempfile(*args, **kwargs):
            temp_file = original_tempfile(*args, **kwargs)
            temp_files_created.append(temp_file.name)
            return temp_file

        with patch("tempfile.NamedTemporaryFile", side_effect=track_tempfile):
            # Act
            result = deploy_helm_app(
                app_name="nginx",
                app=app,
                base_dir=tmp_path,
                charts_dir=tmp_path / "charts",
                build_dir=build_dir,
                app_config_dir=tmp_path / "config",
                output=output,
                cluster_global_values=cluster_global_values,
                dry_run=False,
            )

        # Assert
        assert result is True
        # Verify temp files were created and cleaned up
        for temp_file in temp_files_created:
            # Temp file should be deleted after deployment
            assert not Path(temp_file).exists()

    @patch("sbkube.commands.deploy.run_command")
    def test_no_cluster_values(self, mock_run_command, tmp_path: Path) -> None:
        """Test deployment without cluster global values."""
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
            cluster_global_values=None,  # No cluster values
            dry_run=False,
        )

        # Assert
        assert result is True
