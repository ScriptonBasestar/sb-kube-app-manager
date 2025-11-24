"""Unit tests for upgrade.py command.

Tests verify:
- Helm app upgrade with --install flag
- Config file loading (yaml/toml)
- Namespace resolution (CLI > App > Global)
- Values file processing
- Dry-run mode
- Skip install mode
- Target app filtering
- Error handling
"""

from pathlib import Path
from unittest.mock import patch

from click.testing import CliRunner

from sbkube.commands.upgrade import cmd


class TestUpgradeBasicSuccess:
    """Test basic upgrade functionality."""

    @patch("sbkube.commands.upgrade.run_command")
    @patch("sbkube.commands.upgrade.check_helm_installed_or_exit")
    def test_upgrade_single_helm_app_success(
        self, mock_check_helm, mock_run_command, tmp_path: Path
    ) -> None:
        """Test successful upgrade of single Helm app."""
        # Arrange
        base_dir = tmp_path
        app_config_dir = base_dir / "config"
        app_config_dir.mkdir(exist_ok=True)

        # Create config.yaml
        config_file = app_config_dir / "config.yaml"
        config_file.write_text(
            """
namespace: default
apps:
  nginx:
    type: helm
    chart: bitnami/nginx
    version: 15.0.0
"""
        )

        # Create build directory with chart
        build_dir = base_dir / ".sbkube" / "build" / "nginx"
        build_dir.mkdir(parents=True, exist_ok=True)
        (build_dir / "Chart.yaml").write_text("name: nginx\nversion: 15.0.0")

        # Mock helm upgrade success
        mock_run_command.return_value = (0, "Release upgraded successfully", "")

        # Act
        runner = CliRunner()
        result = runner.invoke(
            cmd,
            [
                "--base-dir",
                str(base_dir),
                "--app-dir",
                "config",
            ],
            obj={"namespace": None},
        )

        # Assert
        assert result.exit_code == 0
        assert "업그레이드/설치 성공" in result.output
        mock_run_command.assert_called_once()

        # Verify helm command structure
        call_args = mock_run_command.call_args[0][0]
        assert call_args[0] == "helm"
        assert call_args[1] == "upgrade"
        assert call_args[2] == "nginx"  # Release name
        assert "--install" in call_args
        assert "--namespace" in call_args
        assert "default" in call_args

    @patch("sbkube.commands.upgrade.run_command")
    @patch("sbkube.commands.upgrade.check_helm_installed_or_exit")
    def test_upgrade_with_release_name(
        self, mock_check_helm, mock_run_command, tmp_path: Path
    ) -> None:
        """Test upgrade with custom release name."""
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
    version: 15.0.0
    release_name: my-custom-nginx
"""
        )

        build_dir = base_dir / ".sbkube" / "build" / "nginx"
        build_dir.mkdir(parents=True, exist_ok=True)
        (build_dir / "Chart.yaml").write_text("name: nginx\nversion: 15.0.0")

        mock_run_command.return_value = (0, "Release upgraded", "")

        # Act
        runner = CliRunner()
        result = runner.invoke(
            cmd,
            ["--base-dir", str(base_dir), "--app-dir", "config"],
            obj={"namespace": None},
        )

        # Assert
        assert result.exit_code == 0
        call_args = mock_run_command.call_args[0][0]
        assert call_args[2] == "my-custom-nginx"  # Custom release name


class TestUpgradeNamespaceHandling:
    """Test namespace resolution logic."""

    @patch("sbkube.commands.upgrade.run_command")
    @patch("sbkube.commands.upgrade.check_helm_installed_or_exit")
    def test_upgrade_cli_namespace_priority(
        self, mock_check_helm, mock_run_command, tmp_path: Path
    ) -> None:
        """Test CLI namespace has highest priority."""
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

        build_dir = base_dir / ".sbkube" / "build" / "nginx"
        build_dir.mkdir(parents=True, exist_ok=True)
        (build_dir / "Chart.yaml").write_text("name: nginx")

        mock_run_command.return_value = (0, "", "")

        # Act
        runner = CliRunner()
        result = runner.invoke(
            cmd,
            ["--base-dir", str(base_dir), "--app-dir", "config"],
            obj={"namespace": "cli-ns"},  # CLI namespace
        )

        # Assert
        assert result.exit_code == 0
        call_args = mock_run_command.call_args[0][0]
        assert "cli-ns" in call_args  # CLI namespace used

    @patch("sbkube.commands.upgrade.run_command")
    @patch("sbkube.commands.upgrade.check_helm_installed_or_exit")
    def test_upgrade_app_namespace_priority(
        self, mock_check_helm, mock_run_command, tmp_path: Path
    ) -> None:
        """Test app-level namespace overrides global."""
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

        build_dir = base_dir / ".sbkube" / "build" / "nginx"
        build_dir.mkdir(parents=True, exist_ok=True)
        (build_dir / "Chart.yaml").write_text("name: nginx")

        mock_run_command.return_value = (0, "", "")

        # Act
        runner = CliRunner()
        result = runner.invoke(
            cmd,
            ["--base-dir", str(base_dir), "--app-dir", "config"],
            obj={"namespace": None},
        )

        # Assert
        assert result.exit_code == 0
        call_args = mock_run_command.call_args[0][0]
        assert "app-ns" in call_args


class TestUpgradeValuesFiles:
    """Test values file processing."""

    @patch("sbkube.commands.upgrade.run_command")
    @patch("sbkube.commands.upgrade.check_helm_installed_or_exit")
    def test_upgrade_with_values_files(
        self, mock_check_helm, mock_run_command, tmp_path: Path
    ) -> None:
        """Test upgrade with values files."""
        # Arrange
        base_dir = tmp_path
        app_config_dir = base_dir / "config"
        app_config_dir.mkdir(exist_ok=True)

        # Create values directory and files
        values_dir = app_config_dir / "values"
        values_dir.mkdir(exist_ok=True)
        (values_dir / "common.yaml").write_text("replicaCount: 3")
        (values_dir / "production.yaml").write_text("image.tag: v2.0")

        config_file = app_config_dir / "config.yaml"
        config_file.write_text(
            """
namespace: default
apps:
  nginx:
    type: helm
    chart: bitnami/nginx
    values:
      - common.yaml
      - production.yaml
"""
        )

        build_dir = base_dir / ".sbkube" / "build" / "nginx"
        build_dir.mkdir(parents=True, exist_ok=True)
        (build_dir / "Chart.yaml").write_text("name: nginx")

        mock_run_command.return_value = (0, "", "")

        # Act
        runner = CliRunner()
        result = runner.invoke(
            cmd,
            ["--base-dir", str(base_dir), "--app-dir", "config"],
            obj={"namespace": None},
        )

        # Assert
        assert result.exit_code == 0
        call_args = mock_run_command.call_args[0][0]
        assert "--values" in call_args
        # Both values files should be included
        values_count = call_args.count("--values")
        assert values_count == 2


class TestUpgradeDryRun:
    """Test dry-run mode."""

    @patch("sbkube.commands.upgrade.run_command")
    @patch("sbkube.commands.upgrade.check_helm_installed_or_exit")
    def test_upgrade_dry_run_mode(
        self, mock_check_helm, mock_run_command, tmp_path: Path
    ) -> None:
        """Test upgrade with --dry-run flag."""
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

        build_dir = base_dir / ".sbkube" / "build" / "nginx"
        build_dir.mkdir(parents=True, exist_ok=True)
        (build_dir / "Chart.yaml").write_text("name: nginx")

        mock_run_command.return_value = (0, "Dry-run output", "")

        # Act
        runner = CliRunner()
        result = runner.invoke(
            cmd,
            ["--base-dir", str(base_dir), "--app-dir", "config", "--dry-run"],
            obj={"namespace": None},
        )

        # Assert
        assert result.exit_code == 0
        assert "Dry-run 모드" in result.output
        call_args = mock_run_command.call_args[0][0]
        assert "--dry-run" in call_args


class TestUpgradeSkipInstall:
    """Test --no-install flag."""

    @patch("sbkube.commands.upgrade.run_command")
    @patch("sbkube.commands.upgrade.check_helm_installed_or_exit")
    def test_upgrade_skip_install_flag(
        self, mock_check_helm, mock_run_command, tmp_path: Path
    ) -> None:
        """Test upgrade without --install flag."""
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

        build_dir = base_dir / ".sbkube" / "build" / "nginx"
        build_dir.mkdir(parents=True, exist_ok=True)
        (build_dir / "Chart.yaml").write_text("name: nginx")

        mock_run_command.return_value = (0, "", "")

        # Act
        runner = CliRunner()
        result = runner.invoke(
            cmd,
            ["--base-dir", str(base_dir), "--app-dir", "config", "--no-install"],
            obj={"namespace": None},
        )

        # Assert
        assert result.exit_code == 0
        call_args = mock_run_command.call_args[0][0]
        assert "--install" not in call_args


class TestUpgradeTargetApp:
    """Test specific app targeting."""

    @patch("sbkube.commands.upgrade.run_command")
    @patch("sbkube.commands.upgrade.check_helm_installed_or_exit")
    def test_upgrade_specific_app(
        self, mock_check_helm, mock_run_command, tmp_path: Path
    ) -> None:
        """Test upgrading only specific app."""
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

        # Create build directories for both apps
        for app_name in ["nginx", "redis"]:
            build_dir = base_dir / ".sbkube" / "build" / app_name
            build_dir.mkdir(parents=True, exist_ok=True)
            (build_dir / "Chart.yaml").write_text(f"name: {app_name}")

        mock_run_command.return_value = (0, "", "")

        # Act
        runner = CliRunner()
        result = runner.invoke(
            cmd,
            ["--base-dir", str(base_dir), "--app-dir", "config", "--app", "nginx"],
            obj={"namespace": None},
        )

        # Assert
        assert result.exit_code == 0
        # Should only call helm upgrade once (for nginx)
        assert mock_run_command.call_count == 1
        call_args = mock_run_command.call_args[0][0]
        assert call_args[2] == "nginx"

    @patch("sbkube.commands.upgrade.check_helm_installed_or_exit")
    def test_upgrade_target_app_not_found(
        self, mock_check_helm, tmp_path: Path
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

        # Act
        runner = CliRunner()
        result = runner.invoke(
            cmd,
            [
                "--base-dir",
                str(base_dir),
                "--app-dir",
                "config",
                "--app",
                "nonexistent",
            ],
            obj={"namespace": None},
        )

        # Assert
        assert result.exit_code != 0
        assert "찾을 수 없습니다" in result.output

    @patch("sbkube.commands.upgrade.check_helm_installed_or_exit")
    def test_upgrade_target_app_wrong_type(
        self, mock_check_helm, tmp_path: Path
    ) -> None:
        """Test skip when target app is not helm type."""
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
      - deployment.yaml
"""
        )

        # Act
        runner = CliRunner()
        result = runner.invoke(
            cmd,
            ["--base-dir", str(base_dir), "--app-dir", "config", "--app", "my-app"],
            obj={"namespace": None},
        )

        # Assert
        assert result.exit_code == 0
        assert "'helm' 타입이 아니므로" in result.output


class TestUpgradeErrors:
    """Test error handling scenarios."""

    @patch("sbkube.commands.upgrade.check_helm_installed_or_exit")
    def test_upgrade_config_file_not_found(
        self, mock_check_helm, tmp_path: Path
    ) -> None:
        """Test error when config file doesn't exist."""
        # Arrange
        base_dir = tmp_path
        app_config_dir = base_dir / "config"
        app_config_dir.mkdir(exist_ok=True)
        # No config file created

        # Act
        runner = CliRunner()
        result = runner.invoke(
            cmd,
            ["--base-dir", str(base_dir), "--app-dir", "config"],
            obj={"namespace": None},
        )

        # Assert
        assert result.exit_code != 0
        assert "찾을 수 없습니다" in result.output

    @patch("sbkube.commands.upgrade.check_helm_installed_or_exit")
    def test_upgrade_chart_not_built(self, mock_check_helm, tmp_path: Path) -> None:
        """Test skip when chart not built."""
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
        # No build directory created

        # Act
        runner = CliRunner()
        result = runner.invoke(
            cmd,
            ["--base-dir", str(base_dir), "--app-dir", "config"],
            obj={"namespace": None},
        )

        # Assert
        assert result.exit_code == 0  # Completes but skips app
        assert "빌드된 Helm 차트 디렉토리를 찾을 수 없습니다" in result.output
        assert "건너뜀" in result.output

    @patch("sbkube.commands.upgrade.run_command")
    @patch("sbkube.commands.upgrade.check_helm_installed_or_exit")
    def test_upgrade_helm_command_failure(
        self, mock_check_helm, mock_run_command, tmp_path: Path
    ) -> None:
        """Test handling of helm upgrade failure."""
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

        build_dir = base_dir / ".sbkube" / "build" / "nginx"
        build_dir.mkdir(parents=True, exist_ok=True)
        (build_dir / "Chart.yaml").write_text("name: nginx")

        # Mock helm upgrade failure
        mock_run_command.return_value = (1, "", "Error: upgrade failed")

        # Act
        runner = CliRunner()
        result = runner.invoke(
            cmd,
            ["--base-dir", str(base_dir), "--app-dir", "config"],
            obj={"namespace": None},
        )

        # Assert
        assert result.exit_code == 0  # Command completes
        assert "실패" in result.output


class TestUpgradeMultipleApps:
    """Test upgrading multiple apps."""

    @patch("sbkube.commands.upgrade.run_command")
    @patch("sbkube.commands.upgrade.check_helm_installed_or_exit")
    def test_upgrade_all_helm_apps(
        self, mock_check_helm, mock_run_command, tmp_path: Path
    ) -> None:
        """Test upgrading all helm apps."""
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
  my-yaml-app:
    type: yaml
    manifests:
      - deployment.yaml
"""
        )

        # Create build directories for helm apps only
        for app_name in ["nginx", "redis"]:
            build_dir = base_dir / ".sbkube" / "build" / app_name
            build_dir.mkdir(parents=True, exist_ok=True)
            (build_dir / "Chart.yaml").write_text(f"name: {app_name}")

        mock_run_command.return_value = (0, "", "")

        # Act
        runner = CliRunner()
        result = runner.invoke(
            cmd,
            ["--base-dir", str(base_dir), "--app-dir", "config"],
            obj={"namespace": None},
        )

        # Assert
        assert result.exit_code == 0
        # Should call helm upgrade twice (nginx, redis), skip yaml app
        assert mock_run_command.call_count == 2
        assert "2개 업그레이드/설치 성공" in result.output

    @patch("sbkube.commands.upgrade.check_helm_installed_or_exit")
    def test_upgrade_no_helm_apps(self, mock_check_helm, tmp_path: Path) -> None:
        """Test when no helm apps in config."""
        # Arrange
        base_dir = tmp_path
        app_config_dir = base_dir / "config"
        app_config_dir.mkdir(exist_ok=True)

        config_file = app_config_dir / "config.yaml"
        config_file.write_text(
            """
namespace: default
apps:
  my-yaml-app:
    type: yaml
    manifests:
      - deployment.yaml
"""
        )

        # Act
        runner = CliRunner()
        result = runner.invoke(
            cmd,
            ["--base-dir", str(base_dir), "--app-dir", "config"],
            obj={"namespace": None},
        )

        # Assert
        assert result.exit_code == 0
        assert "처리할 앱 없음" in result.output
