"""Tests for helm_command_builder module (Phase 4 refactoring)."""

from pathlib import Path
from unittest.mock import MagicMock

import pytest

from sbkube.utils.helm_command_builder import (
    HelmCommand,
    HelmCommandBuilder,
    HelmCommandResult,
    build_helm_template_command,
    build_helm_upgrade_command,
)


class TestHelmCommandResult:
    """Test HelmCommandResult dataclass."""

    def test_cleanup_removes_temp_files(self, tmp_path: Path) -> None:
        """Test cleanup removes temporary files."""
        temp_file = tmp_path / "temp.yaml"
        temp_file.write_text("test: value")

        result = HelmCommandResult(
            command=["helm", "template"],
            temp_files=[temp_file],
        )

        assert temp_file.exists()
        result.cleanup()
        assert not temp_file.exists()

    def test_cleanup_handles_missing_files(self, tmp_path: Path) -> None:
        """Test cleanup handles already-deleted files gracefully."""
        temp_file = tmp_path / "nonexistent.yaml"

        result = HelmCommandResult(
            command=["helm", "template"],
            temp_files=[temp_file],
        )

        # Should not raise
        result.cleanup()


class TestHelmCommandBuilderTemplate:
    """Test HelmCommandBuilder for template command."""

    def test_basic_template_command(self, tmp_path: Path) -> None:
        """Test building basic helm template command."""
        result = (
            HelmCommandBuilder(HelmCommand.TEMPLATE)
            .with_release_name("nginx")
            .with_chart_path(tmp_path / "chart")
            .build()
        )

        assert result.command[0] == "helm"
        assert result.command[1] == "template"
        assert result.command[2] == "nginx"
        assert str(tmp_path / "chart") in result.command[3]

    def test_template_with_namespace(self, tmp_path: Path) -> None:
        """Test template command with namespace."""
        result = (
            HelmCommandBuilder(HelmCommand.TEMPLATE)
            .with_release_name("nginx")
            .with_chart_path(tmp_path / "chart")
            .with_namespace("default")
            .build()
        )

        assert "--namespace" in result.command
        namespace_idx = result.command.index("--namespace")
        assert result.command[namespace_idx + 1] == "default"

    def test_template_with_values_file(self, tmp_path: Path) -> None:
        """Test template command with values file."""
        values_file = tmp_path / "values.yaml"
        values_file.write_text("key: value")

        result = (
            HelmCommandBuilder(HelmCommand.TEMPLATE)
            .with_release_name("nginx")
            .with_chart_path(tmp_path / "chart")
            .with_values_file(values_file)
            .build()
        )

        assert "--values" in result.command
        values_idx = result.command.index("--values")
        assert str(values_file) in result.command[values_idx + 1]

    def test_template_with_set_values(self, tmp_path: Path) -> None:
        """Test template command with --set values."""
        result = (
            HelmCommandBuilder(HelmCommand.TEMPLATE)
            .with_release_name("nginx")
            .with_chart_path(tmp_path / "chart")
            .with_set("image.tag", "v1.0.0")
            .with_set("replicas", "3")
            .build()
        )

        assert "--set" in result.command
        # Find all --set arguments
        set_args = []
        for i, arg in enumerate(result.command):
            if arg == "--set":
                set_args.append(result.command[i + 1])

        assert "image.tag=v1.0.0" in set_args
        assert "replicas=3" in set_args

    def test_template_missing_release_name_raises(self, tmp_path: Path) -> None:
        """Test that missing release name raises ValueError."""
        builder = HelmCommandBuilder(HelmCommand.TEMPLATE).with_chart_path(
            tmp_path / "chart"
        )

        with pytest.raises(ValueError, match="Release name is required"):
            builder.build()

    def test_template_missing_chart_path_raises(self) -> None:
        """Test that missing chart path raises ValueError."""
        builder = HelmCommandBuilder(HelmCommand.TEMPLATE).with_release_name("nginx")

        with pytest.raises(ValueError, match="Chart path is required"):
            builder.build()


class TestHelmCommandBuilderUpgrade:
    """Test HelmCommandBuilder for upgrade command."""

    def test_basic_upgrade_command(self, tmp_path: Path) -> None:
        """Test building basic helm upgrade command."""
        result = (
            HelmCommandBuilder(HelmCommand.UPGRADE)
            .with_release_name("nginx")
            .with_chart_path(tmp_path / "chart")
            .build()
        )

        assert result.command[0] == "helm"
        assert result.command[1] == "upgrade"
        assert "nginx" in result.command
        assert "--install" not in result.command

    def test_upgrade_with_install_flag(self, tmp_path: Path) -> None:
        """Test upgrade command with --install flag."""
        result = (
            HelmCommandBuilder(HelmCommand.UPGRADE)
            .with_release_name("nginx")
            .with_chart_path(tmp_path / "chart")
            .with_install_flag()
            .build()
        )

        assert "--install" in result.command

    def test_upgrade_with_wait(self, tmp_path: Path) -> None:
        """Test upgrade command with --wait flag."""
        result = (
            HelmCommandBuilder(HelmCommand.UPGRADE)
            .with_release_name("nginx")
            .with_chart_path(tmp_path / "chart")
            .with_wait()
            .build()
        )

        assert "--wait" in result.command

    def test_upgrade_with_atomic(self, tmp_path: Path) -> None:
        """Test upgrade command with --atomic flag."""
        result = (
            HelmCommandBuilder(HelmCommand.UPGRADE)
            .with_release_name("nginx")
            .with_chart_path(tmp_path / "chart")
            .with_atomic()
            .build()
        )

        assert "--atomic" in result.command

    def test_upgrade_with_timeout(self, tmp_path: Path) -> None:
        """Test upgrade command with --timeout."""
        result = (
            HelmCommandBuilder(HelmCommand.UPGRADE)
            .with_release_name("nginx")
            .with_chart_path(tmp_path / "chart")
            .with_timeout("5m0s")
            .build()
        )

        assert "--timeout" in result.command
        timeout_idx = result.command.index("--timeout")
        assert result.command[timeout_idx + 1] == "5m0s"

    def test_upgrade_with_create_namespace(self, tmp_path: Path) -> None:
        """Test upgrade command with --create-namespace."""
        result = (
            HelmCommandBuilder(HelmCommand.UPGRADE)
            .with_release_name("nginx")
            .with_chart_path(tmp_path / "chart")
            .with_create_namespace()
            .build()
        )

        assert "--create-namespace" in result.command


class TestHelmCommandBuilderPull:
    """Test HelmCommandBuilder for pull command."""

    def test_basic_pull_command(self) -> None:
        """Test building basic helm pull command."""
        result = (
            HelmCommandBuilder(HelmCommand.PULL)
            .with_chart_ref("bitnami/nginx")
            .build()
        )

        assert result.command == ["helm", "pull", "bitnami/nginx"]

    def test_pull_with_version(self) -> None:
        """Test pull command with version."""
        result = (
            HelmCommandBuilder(HelmCommand.PULL)
            .with_chart_ref("bitnami/nginx")
            .with_version("1.0.0")
            .build()
        )

        assert "--version" in result.command
        version_idx = result.command.index("--version")
        assert result.command[version_idx + 1] == "1.0.0"

    def test_pull_with_destination(self, tmp_path: Path) -> None:
        """Test pull command with destination."""
        result = (
            HelmCommandBuilder(HelmCommand.PULL)
            .with_chart_ref("bitnami/nginx")
            .with_destination(tmp_path)
            .build()
        )

        assert "--destination" in result.command
        dest_idx = result.command.index("--destination")
        assert str(tmp_path) in result.command[dest_idx + 1]

    def test_pull_with_untar(self) -> None:
        """Test pull command with --untar flag."""
        result = (
            HelmCommandBuilder(HelmCommand.PULL)
            .with_chart_ref("bitnami/nginx")
            .with_untar()
            .build()
        )

        assert "--untar" in result.command

    def test_pull_missing_chart_ref_raises(self) -> None:
        """Test that missing chart ref raises ValueError."""
        builder = HelmCommandBuilder(HelmCommand.PULL)

        with pytest.raises(ValueError, match="Chart reference is required"):
            builder.build()


class TestHelmCommandBuilderRepoAdd:
    """Test HelmCommandBuilder for repo add command."""

    def test_repo_add_command(self) -> None:
        """Test building helm repo add command."""
        result = (
            HelmCommandBuilder(HelmCommand.REPO_ADD)
            .with_repo("bitnami", "https://charts.bitnami.com/bitnami")
            .build()
        )

        assert result.command[:3] == ["helm", "repo", "add"]
        assert "bitnami" in result.command
        assert "https://charts.bitnami.com/bitnami" in result.command

    def test_repo_add_missing_params_raises(self) -> None:
        """Test that missing repo params raises ValueError."""
        builder = HelmCommandBuilder(HelmCommand.REPO_ADD)

        with pytest.raises(ValueError, match="Repo name and URL are required"):
            builder.build()


class TestHelmCommandBuilderClusterValues:
    """Test HelmCommandBuilder with cluster global values."""

    def test_cluster_values_creates_temp_file(self, tmp_path: Path) -> None:
        """Test that cluster values creates temporary file."""
        cluster_values = {"global": {"env": "production"}}

        result = (
            HelmCommandBuilder(HelmCommand.TEMPLATE)
            .with_release_name("nginx")
            .with_chart_path(tmp_path / "chart")
            .with_cluster_global_values(cluster_values)
            .build()
        )

        # Should have temp file
        assert len(result.temp_files) == 1
        temp_file = result.temp_files[0]
        assert temp_file.exists()

        # Should include --values with temp file
        assert "--values" in result.command
        values_idx = result.command.index("--values")
        assert str(temp_file) == result.command[values_idx + 1]

        # Cleanup
        result.cleanup()
        assert not temp_file.exists()


class TestHelmCommandBuilderFromHelmApp:
    """Test HelmCommandBuilder.from_helm_app method."""

    def test_from_helm_app_basic(self, tmp_path: Path) -> None:
        """Test configuring builder from HelmApp."""
        app = MagicMock()
        app.release_name = "my-nginx"
        app.namespace = "web"
        app.create_namespace = True
        app.wait = True
        app.atomic = False
        app.timeout = "10m"
        app.values = []
        app.set_values = {}

        result = (
            HelmCommandBuilder(HelmCommand.UPGRADE)
            .with_chart_path(tmp_path / "chart")
            .from_helm_app(app, tmp_path)
            .build()
        )

        assert "my-nginx" in result.command
        assert "--namespace" in result.command
        assert "web" in result.command
        assert "--create-namespace" in result.command
        assert "--wait" in result.command
        assert "--atomic" not in result.command
        assert "--timeout" in result.command
        assert "10m" in result.command

    def test_from_helm_app_with_values_files(self, tmp_path: Path) -> None:
        """Test from_helm_app with values files."""
        # Create values file
        values_file = tmp_path / "values.yaml"
        values_file.write_text("key: value")

        app = MagicMock()
        app.release_name = "nginx"
        app.namespace = None
        app.create_namespace = False
        app.wait = False
        app.atomic = False
        app.timeout = None
        app.values = ["values.yaml"]
        app.set_values = {}

        result = (
            HelmCommandBuilder(HelmCommand.TEMPLATE)
            .with_chart_path(tmp_path / "chart")
            .from_helm_app(app, tmp_path)
            .build()
        )

        assert "--values" in result.command
        values_idx = result.command.index("--values")
        assert str(values_file) in result.command[values_idx + 1]

    def test_from_helm_app_with_set_values(self, tmp_path: Path) -> None:
        """Test from_helm_app with set values."""
        app = MagicMock()
        app.release_name = "nginx"
        app.namespace = None
        app.create_namespace = False
        app.wait = False
        app.atomic = False
        app.timeout = None
        app.values = []
        app.set_values = {"image.tag": "v2.0.0", "replicas": "5"}

        result = (
            HelmCommandBuilder(HelmCommand.TEMPLATE)
            .with_chart_path(tmp_path / "chart")
            .from_helm_app(app, tmp_path)
            .build()
        )

        # Find all --set arguments
        set_args = []
        for i, arg in enumerate(result.command):
            if arg == "--set":
                set_args.append(result.command[i + 1])

        assert "image.tag=v2.0.0" in set_args
        assert "replicas=5" in set_args


class TestConvenienceFunctions:
    """Test convenience functions."""

    def test_build_helm_template_command(self, tmp_path: Path) -> None:
        """Test build_helm_template_command convenience function."""
        app = MagicMock()
        app.release_name = "my-app"
        app.namespace = "default"
        app.create_namespace = False
        app.wait = False
        app.atomic = False
        app.timeout = None
        app.values = []
        app.set_values = {"key": "value"}

        result = build_helm_template_command(
            app=app,
            app_name="nginx",
            chart_path=tmp_path / "chart",
            app_config_dir=tmp_path,
        )

        assert result.command[0] == "helm"
        assert result.command[1] == "template"
        assert "my-app" in result.command  # Uses release_name from app
        assert "--set" in result.command

    def test_build_helm_upgrade_command(self, tmp_path: Path) -> None:
        """Test build_helm_upgrade_command convenience function."""
        app = MagicMock()
        app.release_name = None  # Uses app_name as fallback
        app.namespace = "production"
        app.create_namespace = True
        app.wait = True
        app.atomic = True
        app.timeout = "5m"
        app.values = []
        app.set_values = {}

        result = build_helm_upgrade_command(
            app=app,
            app_name="nginx",
            chart_path=tmp_path / "chart",
            app_config_dir=tmp_path,
            install=True,
        )

        assert result.command[0] == "helm"
        assert result.command[1] == "upgrade"
        assert "nginx" in result.command  # Falls back to app_name
        assert "--install" in result.command
        assert "--create-namespace" in result.command
        assert "--wait" in result.command
        assert "--atomic" in result.command
        assert "--timeout" in result.command

    def test_build_helm_upgrade_without_install(self, tmp_path: Path) -> None:
        """Test build_helm_upgrade_command without install flag."""
        app = MagicMock()
        app.release_name = "nginx"
        app.namespace = None
        app.create_namespace = False
        app.wait = False
        app.atomic = False
        app.timeout = None
        app.values = []
        app.set_values = {}

        result = build_helm_upgrade_command(
            app=app,
            app_name="nginx",
            chart_path=tmp_path / "chart",
            app_config_dir=tmp_path,
            install=False,
        )

        assert "--install" not in result.command
