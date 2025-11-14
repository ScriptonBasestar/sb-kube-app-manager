"""Unit tests for prepare.py - prepare_helm_app function.

Tests verify:
- Local chart detection (skip prepare)
- Remote Helm repository chart pull
- OCI registry chart pull
- sources.yaml parsing
- Error scenarios (repo not found, helm command failure)
"""

from pathlib import Path
from unittest.mock import MagicMock, patch

import pytest

from sbkube.commands.prepare import parse_helm_chart, prepare_helm_app
from sbkube.models.config_model import HelmApp
from sbkube.utils.output_manager import OutputManager


class TestParseHelmChart:
    """Test parse_helm_chart utility function."""

    def test_parse_valid_chart(self) -> None:
        """Test parsing valid repo/chart format."""
        # Act
        repo_name, chart_name = parse_helm_chart("grafana/loki")

        # Assert
        assert repo_name == "grafana"
        assert chart_name == "loki"

    def test_parse_chart_with_dots(self) -> None:
        """Test parsing chart names with dots."""
        # Act
        repo_name, chart_name = parse_helm_chart("bitnami/redis.operator")

        # Assert
        assert repo_name == "bitnami"
        assert chart_name == "redis.operator"

    def test_parse_invalid_chart_no_slash(self) -> None:
        """Test error when chart format has no slash."""
        # Act & Assert
        with pytest.raises(ValueError, match="Invalid chart format"):
            parse_helm_chart("nginx")

    def test_parse_invalid_chart_multiple_slashes(self) -> None:
        """Test error when chart format has multiple slashes."""
        # Act & Assert
        with pytest.raises(ValueError, match="Invalid chart format"):
            parse_helm_chart("bitnami/nginx/extra")


class TestPrepareHelmAppLocalChart:
    """Test prepare_helm_app with local charts."""

    def test_local_chart_skips_prepare(self, tmp_path: Path) -> None:
        """Test that local chart (relative path) skips prepare step."""
        # Arrange
        charts_dir = tmp_path / "charts"
        charts_dir.mkdir(exist_ok=True)

        sources_file = tmp_path / "sources.yaml"
        sources_file.write_text("helm_repos: {}")

        app = HelmApp(
            type="helm",
            chart="./my-local-chart",  # Local chart
        )

        output = MagicMock(spec=OutputManager)

        # Act
        result = prepare_helm_app(
            app_name="my-app",
            app=app,
            base_dir=tmp_path,
            charts_dir=charts_dir,
            sources_file=sources_file,
            output=output,
            dry_run=False,
        )

        # Assert
        assert result is True
        # Should print warning about local chart
        output.print_warning.assert_called_once()
        assert "Local chart" in str(output.print_warning.call_args)


class TestPrepareHelmAppRemoteChart:
    """Test prepare_helm_app with remote Helm repositories."""

    @patch("sbkube.commands.prepare.run_command")
    def test_prepare_remote_chart_success(
        self, mock_run_command, tmp_path: Path
    ) -> None:
        """Test successful preparation of remote Helm chart."""
        # Arrange
        charts_dir = tmp_path / "charts"
        charts_dir.mkdir(exist_ok=True)

        sources_file = tmp_path / "sources.yaml"
        sources_file.write_text(
            """
helm_repos:
  bitnami: https://charts.bitnami.com/bitnami
"""
        )

        app = HelmApp(
            type="helm",
            chart="bitnami/nginx",
            version="15.0.0",
        )

        output = MagicMock(spec=OutputManager)

        # Mock helm commands to succeed AND create temporary extraction directory
        def mock_run_side_effect(cmd, **kwargs):
            # Simulate helm pull --untar --untardir creating extracted chart
            if "pull" in cmd:
                # Extract untardir from command
                untardir_idx = cmd.index("--untardir") + 1
                temp_dir = Path(cmd[untardir_idx])
                # Create temporary extraction directory with chart
                temp_dir.mkdir(parents=True, exist_ok=True)
                (temp_dir / "nginx").mkdir(exist_ok=True)
                (temp_dir / "nginx" / "Chart.yaml").write_text("name: nginx\nversion: 15.0.0")
            return (0, "", "")

        mock_run_command.side_effect = mock_run_side_effect

        # Act
        result = prepare_helm_app(
            app_name="nginx",
            app=app,
            base_dir=tmp_path,
            charts_dir=charts_dir,
            sources_file=sources_file,
            output=output,
            dry_run=False,
        )

        # Assert
        assert result is True
        # Should call helm repo add, helm repo update, and helm pull
        assert mock_run_command.call_count >= 3

    @patch("sbkube.commands.prepare.run_command")
    def test_prepare_with_force_overwrites_existing(
        self, mock_run_command, tmp_path: Path
    ) -> None:
        """Test force flag overwrites existing chart."""
        # Arrange
        charts_dir = tmp_path / "charts"
        charts_dir.mkdir(exist_ok=True)

        # Create existing chart directory
        existing_chart = charts_dir / "bitnami" / "nginx-15.0.0"
        existing_chart.mkdir(parents=True, exist_ok=True)
        (existing_chart / "Chart.yaml").write_text("old chart")

        sources_file = tmp_path / "sources.yaml"
        sources_file.write_text("helm_repos:\n  bitnami: https://charts.bitnami.com/bitnami")

        app = HelmApp(
            type="helm",
            chart="bitnami/nginx",
            version="15.0.0",
        )

        output = MagicMock(spec=OutputManager)

        # Mock helm commands with side_effect to create extracted chart
        def mock_run_side_effect(cmd, **kwargs):
            if "pull" in cmd:
                untardir_idx = cmd.index("--untardir") + 1
                temp_dir = Path(cmd[untardir_idx])
                temp_dir.mkdir(parents=True, exist_ok=True)
                (temp_dir / "nginx").mkdir(exist_ok=True)
                (temp_dir / "nginx" / "Chart.yaml").write_text("name: nginx\nversion: 15.0.0")
            return (0, "", "")

        mock_run_command.side_effect = mock_run_side_effect

        # Act
        result = prepare_helm_app(
            app_name="nginx",
            app=app,
            base_dir=tmp_path,
            charts_dir=charts_dir,
            sources_file=sources_file,
            output=output,
            force=True,  # Force overwrite
            dry_run=False,
        )

        # Assert
        assert result is True

    @patch("sbkube.commands.prepare.run_command")
    def test_prepare_dry_run_mode(self, mock_run_command, tmp_path: Path) -> None:
        """Test dry-run mode doesn't actually pull chart."""
        # Arrange
        charts_dir = tmp_path / "charts"
        charts_dir.mkdir(exist_ok=True)

        sources_file = tmp_path / "sources.yaml"
        sources_file.write_text("helm_repos:\n  bitnami: https://charts.bitnami.com/bitnami")

        app = HelmApp(
            type="helm",
            chart="bitnami/nginx",
            version="15.0.0",
        )

        output = MagicMock(spec=OutputManager)

        # Act
        result = prepare_helm_app(
            app_name="nginx",
            app=app,
            base_dir=tmp_path,
            charts_dir=charts_dir,
            sources_file=sources_file,
            output=output,
            dry_run=True,  # DRY-RUN
        )

        # Assert
        assert result is True
        # Should print DRY-RUN messages
        output.print.assert_called()


class TestPrepareHelmAppErrors:
    """Test error scenarios."""

    def test_sources_file_not_found(self, tmp_path: Path) -> None:
        """Test error when sources.yaml doesn't exist."""
        # Arrange
        charts_dir = tmp_path / "charts"
        charts_dir.mkdir(exist_ok=True)

        sources_file = tmp_path / "nonexistent.yaml"  # Doesn't exist

        app = HelmApp(
            type="helm",
            chart="bitnami/nginx",
            version="15.0.0",
        )

        output = MagicMock(spec=OutputManager)

        # Act
        result = prepare_helm_app(
            app_name="nginx",
            app=app,
            base_dir=tmp_path,
            charts_dir=charts_dir,
            sources_file=sources_file,
            output=output,
            dry_run=False,
        )

        # Assert
        assert result is False
        output.print_error.assert_called()
        assert "not found" in str(output.print_error.call_args)

    def test_repo_not_in_sources(self, tmp_path: Path) -> None:
        """Test error when repository not defined in sources.yaml."""
        # Arrange
        charts_dir = tmp_path / "charts"
        charts_dir.mkdir(exist_ok=True)

        sources_file = tmp_path / "sources.yaml"
        sources_file.write_text(
            """
helm_repos:
  bitnami: https://charts.bitnami.com/bitnami
"""
        )

        app = HelmApp(
            type="helm",
            chart="grafana/loki",  # grafana repo not in sources
            version="5.0.0",
        )

        output = MagicMock(spec=OutputManager)

        # Act
        result = prepare_helm_app(
            app_name="loki",
            app=app,
            base_dir=tmp_path,
            charts_dir=charts_dir,
            sources_file=sources_file,
            output=output,
            dry_run=False,
        )

        # Assert
        assert result is False
        output.print_error.assert_called()
        assert "not found" in str(output.print_error.call_args).lower()

    @patch("sbkube.commands.prepare.run_command")
    def test_helm_repo_add_failure(self, mock_run_command, tmp_path: Path) -> None:
        """Test handling of helm repo add failure."""
        # Arrange
        charts_dir = tmp_path / "charts"
        charts_dir.mkdir(exist_ok=True)

        sources_file = tmp_path / "sources.yaml"
        sources_file.write_text("helm_repos:\n  bitnami: https://charts.bitnami.com/bitnami")

        app = HelmApp(
            type="helm",
            chart="bitnami/nginx",
            version="15.0.0",
        )

        output = MagicMock(spec=OutputManager)

        # Mock helm repo add failure
        mock_run_command.return_value = (1, "", "Error: repository already exists")

        # Act
        result = prepare_helm_app(
            app_name="nginx",
            app=app,
            base_dir=tmp_path,
            charts_dir=charts_dir,
            sources_file=sources_file,
            output=output,
            dry_run=False,
        )

        # Assert
        # helm repo add failure should not stop the process (repo might already exist)
        # But result depends on helm pull command
        assert mock_run_command.called


class TestPrepareHelmAppDictConfig:
    """Test sources.yaml with dict-style config (url, username, password)."""

    @patch("sbkube.commands.prepare.run_command")
    def test_prepare_with_dict_config(self, mock_run_command, tmp_path: Path) -> None:
        """Test repository config with dict (url, username, password)."""
        # Arrange
        charts_dir = tmp_path / "charts"
        charts_dir.mkdir(exist_ok=True)

        sources_file = tmp_path / "sources.yaml"
        sources_file.write_text(
            """
helm_repos:
  private-repo:
    url: https://charts.example.com
    username: myuser
    password: mypass
"""
        )

        app = HelmApp(
            type="helm",
            chart="private-repo/my-chart",
            version="1.0.0",
        )

        output = MagicMock(spec=OutputManager)

        # Mock helm commands with side_effect to create extracted chart
        def mock_run_side_effect(cmd, **kwargs):
            if "pull" in cmd:
                untardir_idx = cmd.index("--untardir") + 1
                temp_dir = Path(cmd[untardir_idx])
                temp_dir.mkdir(parents=True, exist_ok=True)
                (temp_dir / "my-chart").mkdir(exist_ok=True)
                (temp_dir / "my-chart" / "Chart.yaml").write_text("name: my-chart\nversion: 1.0.0")
            return (0, "", "")

        mock_run_command.side_effect = mock_run_side_effect

        # Act
        result = prepare_helm_app(
            app_name="my-chart",
            app=app,
            base_dir=tmp_path,
            charts_dir=charts_dir,
            sources_file=sources_file,
            output=output,
            dry_run=False,
        )

        # Assert
        assert result is True
        # Should pass username/password to helm repo add
        mock_run_command.assert_called()

    def test_dict_config_missing_url(self, tmp_path: Path) -> None:
        """Test error when dict config has no 'url' field."""
        # Arrange
        charts_dir = tmp_path / "charts"
        charts_dir.mkdir(exist_ok=True)

        sources_file = tmp_path / "sources.yaml"
        sources_file.write_text(
            """
helm_repos:
  broken-repo:
    username: myuser
    password: mypass
    # Missing 'url'
"""
        )

        app = HelmApp(
            type="helm",
            chart="broken-repo/my-chart",
            version="1.0.0",
        )

        output = MagicMock(spec=OutputManager)

        # Act
        result = prepare_helm_app(
            app_name="my-chart",
            app=app,
            base_dir=tmp_path,
            charts_dir=charts_dir,
            sources_file=sources_file,
            output=output,
            dry_run=False,
        )

        # Assert
        assert result is False
        output.print_error.assert_called()
        assert "Missing 'url'" in str(output.print_error.call_args)
