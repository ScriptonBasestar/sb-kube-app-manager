"""Unit tests for delete.py command.

Tests verify:
- Helm release deletion (helm uninstall)
- YAML resource deletion (kubectl delete)
- Action app uninstall scripts
- Namespace resolution (App > CLI > Global)
- Context handling (app.context > sources.yaml)
- Dry-run mode
- Skip-not-found option
- Target app filtering
- Error handling
"""

from pathlib import Path
from unittest.mock import patch

from click.testing import CliRunner

from sbkube.commands.delete import cmd


class TestDeleteHelmAppBasic:
    """Test basic Helm app deletion."""

    @patch("sbkube.commands.delete.get_installed_charts")
    @patch("sbkube.commands.delete.run_command")
    @patch("sbkube.commands.delete.check_helm_installed_or_exit")
    @patch("sbkube.commands.delete.find_sources_file")
    def test_delete_helm_app_success_with_target(
        self,
        mock_find_sources,
        mock_check_helm,
        mock_run_command,
        mock_get_charts,
        tmp_path: Path,
    ) -> None:
        """Test successful Helm app deletion with positional TARGET."""
        base_dir = tmp_path
        app_config_dir = base_dir / "config"
        app_config_dir.mkdir(exist_ok=True)

        (app_config_dir / "sbkube.yaml").write_text(
            """
apiVersion: sbkube/v1
settings:
  namespace: default
apps:
  nginx:
    type: helm
    chart: bitnami/nginx
    release_name: my-nginx
"""
        )

        mock_find_sources.return_value = None
        mock_get_charts.return_value = ["my-nginx"]
        mock_run_command.return_value = (0, "release uninstalled", "")

        runner = CliRunner()
        result = runner.invoke(cmd, [str(app_config_dir)], obj={"namespace": None})

        assert result.exit_code == 0
        assert "삭제 완료" in result.output
        mock_run_command.assert_called_once()

    @patch("sbkube.commands.delete.get_installed_charts")
    @patch("sbkube.commands.delete.run_command")
    @patch("sbkube.commands.delete.check_helm_installed_or_exit")
    @patch("sbkube.commands.delete.find_sources_file")
    def test_delete_helm_app_success(
        self,
        mock_find_sources,
        mock_check_helm,
        mock_run_command,
        mock_get_charts,
        tmp_path: Path,
    ) -> None:
        """Test successful Helm app deletion."""
        # Arrange
        base_dir = tmp_path
        app_config_dir = base_dir / "config"
        app_config_dir.mkdir(exist_ok=True)

        config_file = app_config_dir / "config.yaml"
        config_file.write_text(
            """
namespace: default
apps:
  nginx:
    type: helm
    chart: bitnami/nginx
    release_name: my-nginx
"""
        )

        # Mock sources file not found
        mock_find_sources.return_value = None

        # Mock helm list showing release exists
        mock_get_charts.return_value = ["my-nginx"]

        # Mock helm uninstall success
        mock_run_command.return_value = (0, "release uninstalled", "")

        # Act
        runner = CliRunner()
        result = runner.invoke(
            cmd,
            [str(base_dir / "config")],
            obj={"namespace": None},
        )

        # Assert
        assert result.exit_code == 0
        assert "삭제 완료" in result.output
        mock_run_command.assert_called_once()

        # Verify helm uninstall command
        call_args = mock_run_command.call_args[0][0]
        assert call_args[0] == "helm"
        assert call_args[1] == "uninstall"
        assert call_args[2] == "my-nginx"
        assert "--namespace" in call_args
        assert "default" in call_args

    @patch("sbkube.commands.delete.get_installed_charts")
    @patch("sbkube.commands.delete.check_helm_installed_or_exit")
    @patch("sbkube.commands.delete.find_sources_file")
    def test_delete_helm_app_not_installed(
        self,
        mock_find_sources,
        mock_check_helm,
        mock_get_charts,
        tmp_path: Path,
    ) -> None:
        """Test skip when Helm release not installed."""
        # Arrange
        base_dir = tmp_path
        app_config_dir = base_dir / "config"
        app_config_dir.mkdir(exist_ok=True)

        config_file = app_config_dir / "config.yaml"
        config_file.write_text(
            """
namespace: default
apps:
  nginx:
    type: helm
    chart: bitnami/nginx
"""
        )

        mock_find_sources.return_value = None
        # Release not installed
        mock_get_charts.return_value = []

        # Act
        runner = CliRunner()
        result = runner.invoke(
            cmd,
            [str(base_dir / "config")],
            obj={"namespace": None},
        )

        # Assert
        assert result.exit_code == 0
        assert "설치되어 있지 않습니다" in result.output
        assert "건너뜀" in result.output or "스킵" in result.output


class TestDeleteYamlAppBasic:
    """Test basic YAML app deletion."""

    @patch("sbkube.commands.delete.run_command")
    @patch("sbkube.commands.delete.check_kubectl_installed_or_exit")
    @patch("sbkube.commands.delete.find_sources_file")
    def test_delete_yaml_app_success(
        self,
        mock_find_sources,
        mock_check_kubectl,
        mock_run_command,
        tmp_path: Path,
    ) -> None:
        """Test successful YAML app deletion."""
        # Arrange
        base_dir = tmp_path
        app_config_dir = base_dir / "config"
        app_config_dir.mkdir(exist_ok=True)

        # Create YAML files
        (app_config_dir / "deployment.yaml").write_text(
            "apiVersion: apps/v1\nkind: Deployment"
        )
        (app_config_dir / "service.yaml").write_text("apiVersion: v1\nkind: Service")

        config_file = app_config_dir / "config.yaml"
        config_file.write_text(
            """
namespace: default
apps:
  my-app:
    type: yaml
    manifests:
      - deployment.yaml
      - service.yaml
"""
        )

        mock_find_sources.return_value = None

        # Mock kubectl delete success for both files
        mock_run_command.return_value = (0, "deleted", "")

        # Act
        runner = CliRunner()
        result = runner.invoke(
            cmd,
            [str(base_dir / "config")],
            obj={"namespace": None},
        )

        # Assert
        assert result.exit_code == 0
        assert "삭제 요청 성공" in result.output
        # kubectl delete called twice (for each manifest in reverse order)
        assert mock_run_command.call_count == 2

        # Verify kubectl delete commands
        first_call = mock_run_command.call_args_list[0][0][0]
        assert first_call[0] == "kubectl"
        assert first_call[1] == "delete"
        assert "-f" in first_call

    @patch("sbkube.commands.delete.check_kubectl_installed_or_exit")
    @patch("sbkube.commands.delete.find_sources_file")
    def test_delete_yaml_app_file_not_found(
        self,
        mock_find_sources,
        mock_check_kubectl,
        tmp_path: Path,
    ) -> None:
        """Test warning when YAML file doesn't exist."""
        # Arrange
        base_dir = tmp_path
        app_config_dir = base_dir / "config"
        app_config_dir.mkdir(exist_ok=True)

        config_file = app_config_dir / "config.yaml"
        config_file.write_text(
            """
namespace: default
apps:
  my-app:
    type: yaml
    manifests:
      - nonexistent.yaml
"""
        )

        mock_find_sources.return_value = None

        # Act
        runner = CliRunner()
        result = runner.invoke(
            cmd,
            [str(base_dir / "config")],
            obj={"namespace": None},
        )

        # Assert
        assert result.exit_code == 0
        assert "찾을 수 없음" in result.output


class TestDeleteDryRun:
    """Test dry-run mode."""

    @patch("sbkube.commands.delete.get_installed_charts")
    @patch("sbkube.commands.delete.run_command")
    @patch("sbkube.commands.delete.check_helm_installed_or_exit")
    @patch("sbkube.commands.delete.find_sources_file")
    def test_delete_helm_app_dry_run(
        self,
        mock_find_sources,
        mock_check_helm,
        mock_run_command,
        mock_get_charts,
        tmp_path: Path,
    ) -> None:
        """Test Helm app deletion in dry-run mode."""
        # Arrange
        base_dir = tmp_path
        app_config_dir = base_dir / "config"
        app_config_dir.mkdir(exist_ok=True)

        config_file = app_config_dir / "config.yaml"
        config_file.write_text(
            """
namespace: default
apps:
  nginx:
    type: helm
    chart: bitnami/nginx
"""
        )

        mock_find_sources.return_value = None
        mock_get_charts.return_value = ["nginx"]
        mock_run_command.return_value = (0, "dry-run output", "")

        # Act
        runner = CliRunner()
        result = runner.invoke(
            cmd,
            [str(base_dir / "config"), "--dry-run"],
            obj={"namespace": None},
        )

        # Assert
        assert result.exit_code == 0
        assert "DRY-RUN" in result.output
        assert "삭제 예정" in result.output
        call_args = mock_run_command.call_args[0][0]
        assert "--dry-run" in call_args

    @patch("sbkube.commands.delete.run_command")
    @patch("sbkube.commands.delete.check_kubectl_installed_or_exit")
    @patch("sbkube.commands.delete.find_sources_file")
    def test_delete_yaml_app_dry_run(
        self,
        mock_find_sources,
        mock_check_kubectl,
        mock_run_command,
        tmp_path: Path,
    ) -> None:
        """Test YAML app dry-run mode."""
        # Arrange
        base_dir = tmp_path
        app_config_dir = base_dir / "config"
        app_config_dir.mkdir(exist_ok=True)

        (app_config_dir / "deployment.yaml").write_text(
            "apiVersion: apps/v1\nkind: Deployment"
        )

        config_file = app_config_dir / "config.yaml"
        config_file.write_text(
            """
namespace: default
apps:
  my-app:
    type: yaml
    manifests:
      - deployment.yaml
"""
        )

        mock_find_sources.return_value = None
        mock_run_command.return_value = (0, "dry-run output", "")

        # Act
        runner = CliRunner()
        result = runner.invoke(
            cmd,
            [str(base_dir / "config"), "--dry-run"],
            obj={"namespace": None},
        )

        # Assert
        assert result.exit_code == 0
        assert "DRY-RUN" in result.output
        assert "삭제 예정" in result.output
        call_args = mock_run_command.call_args[0][0]
        assert "--dry-run=client" in call_args


class TestDeleteSkipNotFound:
    """Test --skip-not-found option."""

    @patch("sbkube.commands.delete.get_installed_charts")
    @patch("sbkube.commands.delete.check_helm_installed_or_exit")
    @patch("sbkube.commands.delete.find_sources_file")
    def test_delete_helm_skip_not_found(
        self,
        mock_find_sources,
        mock_check_helm,
        mock_get_charts,
        tmp_path: Path,
    ) -> None:
        """Test skip when release not found with --skip-not-found."""
        # Arrange
        base_dir = tmp_path
        app_config_dir = base_dir / "config"
        app_config_dir.mkdir(exist_ok=True)

        config_file = app_config_dir / "config.yaml"
        config_file.write_text(
            """
namespace: default
apps:
  nginx:
    type: helm
    chart: bitnami/nginx
"""
        )

        mock_find_sources.return_value = None
        mock_get_charts.return_value = []  # Not installed

        # Act
        runner = CliRunner()
        result = runner.invoke(
            cmd,
            [
                str(base_dir / "config"),
                "--skip-not-found",
            ],
            obj={"namespace": None},
        )

        # Assert
        assert result.exit_code == 0
        assert "--skip-not-found" in result.output
        assert "건너뜁니다" in result.output

    @patch("sbkube.commands.delete.run_command")
    @patch("sbkube.commands.delete.check_kubectl_installed_or_exit")
    @patch("sbkube.commands.delete.find_sources_file")
    def test_delete_yaml_skip_not_found(
        self,
        mock_find_sources,
        mock_check_kubectl,
        mock_run_command,
        tmp_path: Path,
    ) -> None:
        """Test YAML deletion with --ignore-not-found."""
        # Arrange
        base_dir = tmp_path
        app_config_dir = base_dir / "config"
        app_config_dir.mkdir(exist_ok=True)

        (app_config_dir / "deployment.yaml").write_text(
            "apiVersion: apps/v1\nkind: Deployment"
        )

        config_file = app_config_dir / "config.yaml"
        config_file.write_text(
            """
namespace: default
apps:
  my-app:
    type: yaml
    manifests:
      - deployment.yaml
"""
        )

        mock_find_sources.return_value = None
        mock_run_command.return_value = (0, "deleted", "")

        # Act
        runner = CliRunner()
        result = runner.invoke(
            cmd,
            [
                str(base_dir / "config"),
                "--skip-not-found",
            ],
            obj={"namespace": None},
        )

        # Assert
        assert result.exit_code == 0
        call_args = mock_run_command.call_args[0][0]
        assert "--ignore-not-found=true" in call_args


class TestDeleteTargetApp:
    """Test specific app targeting."""

    @patch("sbkube.commands.delete.get_installed_charts")
    @patch("sbkube.commands.delete.run_command")
    @patch("sbkube.commands.delete.check_helm_installed_or_exit")
    @patch("sbkube.commands.delete.find_sources_file")
    def test_delete_specific_app(
        self,
        mock_find_sources,
        mock_check_helm,
        mock_run_command,
        mock_get_charts,
        tmp_path: Path,
    ) -> None:
        """Test deleting only specific app."""
        # Arrange
        base_dir = tmp_path
        app_config_dir = base_dir / "config"
        app_config_dir.mkdir(exist_ok=True)

        config_file = app_config_dir / "config.yaml"
        config_file.write_text(
            """
namespace: default
apps:
  nginx:
    type: helm
    chart: bitnami/nginx
  redis:
    type: helm
    chart: bitnami/redis
"""
        )

        mock_find_sources.return_value = None
        mock_get_charts.return_value = ["nginx", "redis"]
        mock_run_command.return_value = (0, "uninstalled", "")

        # Act - delete only nginx
        runner = CliRunner()
        result = runner.invoke(
            cmd,
            [str(base_dir / "config"), "--app", "nginx"],
            obj={"namespace": None},
        )

        # Assert
        assert result.exit_code == 0
        # Should only call helm uninstall once (for nginx)
        assert mock_run_command.call_count == 1
        call_args = mock_run_command.call_args[0][0]
        assert "nginx" in call_args
        assert "redis" not in str(call_args)

    @patch("sbkube.commands.delete.find_sources_file")
    def test_delete_target_app_not_found(
        self,
        mock_find_sources,
        tmp_path: Path,
    ) -> None:
        """Test error when target app doesn't exist."""
        # Arrange
        base_dir = tmp_path
        app_config_dir = base_dir / "config"
        app_config_dir.mkdir(exist_ok=True)

        config_file = app_config_dir / "config.yaml"
        config_file.write_text(
            """
namespace: default
apps:
  nginx:
    type: helm
    chart: bitnami/nginx
"""
        )

        mock_find_sources.return_value = None

        # Act
        runner = CliRunner()
        result = runner.invoke(
            cmd,
            [
                str(base_dir / "config"),
                "--app",
                "nonexistent",
            ],
            obj={"namespace": None},
        )

        # Assert
        assert result.exit_code != 0
        assert "찾을 수 없습니다" in result.output


class TestDeleteNamespaceHandling:
    """Test namespace resolution."""

    @patch("sbkube.commands.delete.get_installed_charts")
    @patch("sbkube.commands.delete.run_command")
    @patch("sbkube.commands.delete.check_helm_installed_or_exit")
    @patch("sbkube.commands.delete.find_sources_file")
    def test_delete_app_level_namespace_priority(
        self,
        mock_find_sources,
        mock_check_helm,
        mock_run_command,
        mock_get_charts,
        tmp_path: Path,
    ) -> None:
        """Test app-level namespace has priority."""
        # Arrange
        base_dir = tmp_path
        app_config_dir = base_dir / "config"
        app_config_dir.mkdir(exist_ok=True)

        config_file = app_config_dir / "config.yaml"
        config_file.write_text(
            """
namespace: global-ns
apps:
  nginx:
    type: helm
    chart: bitnami/nginx
    namespace: app-ns
"""
        )

        mock_find_sources.return_value = None
        mock_get_charts.return_value = ["nginx"]
        mock_run_command.return_value = (0, "uninstalled", "")

        # Act
        runner = CliRunner()
        result = runner.invoke(
            cmd,
            [str(base_dir / "config")],
            obj={"namespace": "cli-ns"},  # CLI namespace
        )

        # Assert
        assert result.exit_code == 0
        call_args = mock_run_command.call_args[0][0]
        # App-level namespace should be used
        assert "app-ns" in call_args


class TestDeleteErrors:
    """Test error handling."""

    @patch("sbkube.commands.delete.find_sources_file")
    def test_delete_config_file_not_found(
        self,
        mock_find_sources,
        tmp_path: Path,
    ) -> None:
        """Test error when config file doesn't exist."""
        # Arrange
        base_dir = tmp_path
        app_config_dir = base_dir / "config"
        app_config_dir.mkdir(exist_ok=True)

        mock_find_sources.return_value = None

        # Act
        runner = CliRunner()
        result = runner.invoke(
            cmd,
            [str(base_dir / "config")],
            obj={"namespace": None},
        )

        # Assert
        assert result.exit_code != 0
        assert "찾을 수 없습니다" in result.output

    @patch("sbkube.commands.delete.get_installed_charts")
    @patch("sbkube.commands.delete.run_command")
    @patch("sbkube.commands.delete.check_helm_installed_or_exit")
    @patch("sbkube.commands.delete.find_sources_file")
    def test_delete_helm_command_failure(
        self,
        mock_find_sources,
        mock_check_helm,
        mock_run_command,
        mock_get_charts,
        tmp_path: Path,
    ) -> None:
        """Test handling of helm uninstall failure."""
        # Arrange
        base_dir = tmp_path
        app_config_dir = base_dir / "config"
        app_config_dir.mkdir(exist_ok=True)

        config_file = app_config_dir / "config.yaml"
        config_file.write_text(
            """
namespace: default
apps:
  nginx:
    type: helm
    chart: bitnami/nginx
"""
        )

        mock_find_sources.return_value = None
        mock_get_charts.return_value = ["nginx"]
        # Mock helm uninstall failure
        mock_run_command.return_value = (1, "", "Error: uninstall failed")

        # Act
        runner = CliRunner()
        result = runner.invoke(
            cmd,
            [str(base_dir / "config")],
            obj={"namespace": None},
        )

        # Assert
        assert result.exit_code == 0  # Command completes
        assert "실패" in result.output

    @patch("sbkube.commands.delete.run_command")
    @patch("sbkube.commands.delete.check_kubectl_installed_or_exit")
    @patch("sbkube.commands.delete.find_sources_file")
    def test_delete_yaml_command_failure(
        self,
        mock_find_sources,
        mock_check_kubectl,
        mock_run_command,
        tmp_path: Path,
    ) -> None:
        """Test handling of kubectl delete failure."""
        # Arrange
        base_dir = tmp_path
        app_config_dir = base_dir / "config"
        app_config_dir.mkdir(exist_ok=True)

        (app_config_dir / "deployment.yaml").write_text(
            "apiVersion: apps/v1\nkind: Deployment"
        )

        config_file = app_config_dir / "config.yaml"
        config_file.write_text(
            """
namespace: default
apps:
  my-app:
    type: yaml
    manifests:
      - deployment.yaml
"""
        )

        mock_find_sources.return_value = None
        # Mock kubectl delete failure
        mock_run_command.return_value = (1, "", "Error: resource not found")

        # Act
        runner = CliRunner()
        result = runner.invoke(
            cmd,
            [str(base_dir / "config")],
            obj={"namespace": None},
        )

        # Assert
        assert result.exit_code == 0
        assert "실패" in result.output


class TestDeleteMultipleApps:
    """Test deleting multiple apps."""

    @patch("sbkube.commands.delete.get_installed_charts")
    @patch("sbkube.commands.delete.run_command")
    @patch("sbkube.commands.delete.check_helm_installed_or_exit")
    @patch("sbkube.commands.delete.check_kubectl_installed_or_exit")
    @patch("sbkube.commands.delete.find_sources_file")
    def test_delete_multiple_helm_and_yaml_apps(
        self,
        mock_find_sources,
        mock_check_kubectl,
        mock_check_helm,
        mock_run_command,
        mock_get_charts,
        tmp_path: Path,
    ) -> None:
        """Test deleting multiple Helm and YAML apps."""
        # Arrange
        base_dir = tmp_path
        app_config_dir = base_dir / "config"
        app_config_dir.mkdir(exist_ok=True)

        (app_config_dir / "deployment.yaml").write_text(
            "apiVersion: apps/v1\nkind: Deployment"
        )

        config_file = app_config_dir / "config.yaml"
        config_file.write_text(
            """
namespace: default
apps:
  nginx:
    type: helm
    chart: bitnami/nginx
  redis:
    type: helm
    chart: bitnami/redis
  my-yaml-app:
    type: yaml
    manifests:
      - deployment.yaml
"""
        )

        mock_find_sources.return_value = None
        mock_get_charts.return_value = ["nginx", "redis"]
        mock_run_command.return_value = (0, "success", "")

        # Act
        runner = CliRunner()
        result = runner.invoke(
            cmd,
            [str(base_dir / "config")],
            obj={"namespace": None},
        )

        # Assert
        assert result.exit_code == 0
        # helm uninstall (2) + kubectl delete (1) = 3
        assert mock_run_command.call_count == 3
        assert "3개 삭제 성공" in result.output

    @patch("sbkube.commands.delete.find_sources_file")
    def test_delete_no_apps(
        self,
        mock_find_sources,
        tmp_path: Path,
    ) -> None:
        """Test when no apps in config."""
        # Arrange
        base_dir = tmp_path
        app_config_dir = base_dir / "config"
        app_config_dir.mkdir(exist_ok=True)

        config_file = app_config_dir / "config.yaml"
        config_file.write_text(
            """
namespace: default
apps: {}
"""
        )

        mock_find_sources.return_value = None

        # Act
        runner = CliRunner()
        result = runner.invoke(
            cmd,
            [str(base_dir / "config")],
            obj={"namespace": None},
        )

        # Assert
        assert result.exit_code == 0
        assert "처리할 앱 없음" in result.output
