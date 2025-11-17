"""Tests for status command."""

from pathlib import Path
from unittest.mock import MagicMock, patch

import pytest
import yaml
from click.testing import CliRunner

from sbkube.cli import main


@pytest.fixture
def runner():
    """Create CliRunner fixture."""
    return CliRunner()


class TestStatusCommandHelp:
    """Test status command help."""

    def test_status_help(self, runner) -> None:
        """Test --help option shows help message."""
        result = runner.invoke(main, ["status", "--help"])

        assert result.exit_code == 0
        assert "status" in result.output.lower()
        assert "application" in result.output.lower() or "cluster" in result.output.lower()


class TestStatusCommandBasic:
    """Test basic status command scenarios."""

    def test_status_requires_sources_yaml(
        self,
        runner,
        tmp_path,
    ) -> None:
        """Test status fails without sources.yaml."""
        result = runner.invoke(main, ["status", "--base-dir", str(tmp_path)])

        assert result.exit_code != 0
        assert "sources" in result.output.lower() or "not found" in result.output.lower()

    @patch("sbkube.commands.status.ClusterStatusCollector")
    @patch("sbkube.commands.status.ClusterCache")
    def test_status_sources_missing_kubeconfig(
        self,
        mock_cache,
        mock_collector,
        runner,
        tmp_path,
    ) -> None:
        """Test status fails when sources.yaml is missing kubeconfig."""
        # Create sources.yaml without kubeconfig
        sources_file = tmp_path / "sources.yaml"
        sources_data = {
            "cluster": "test-cluster",
        }
        with open(sources_file, "w") as f:
            yaml.dump(sources_data, f)

        result = runner.invoke(main, ["status", "--base-dir", str(tmp_path)])

        assert result.exit_code != 0
        assert "kubeconfig" in result.output.lower()

    @patch("sbkube.commands.status._display_status")
    @patch("sbkube.commands.status._collect_and_cache")
    @patch("sbkube.commands.status.ClusterStatusCollector")
    @patch("sbkube.commands.status.ClusterCache")
    def test_status_basic_success(
        self,
        mock_cache_class,
        mock_collector_class,
        mock_collect,
        mock_display,
        runner,
        tmp_path,
    ) -> None:
        """Test basic status command succeeds with valid sources.yaml."""
        # Create sources.yaml
        sources_file = tmp_path / "sources.yaml"
        sources_data = {
            "kubeconfig": "/fake/kubeconfig",
            "kubeconfig_context": "test-context",
            "cluster": "test-cluster",
        }
        with open(sources_file, "w") as f:
            yaml.dump(sources_data, f)

        # Mock cache and collector
        mock_cache = MagicMock()
        mock_cache.get_age_seconds.return_value = 60  # 60 seconds old
        mock_cache.is_expired.return_value = False
        mock_cache_class.return_value = mock_cache
        mock_collector = MagicMock()
        mock_collector_class.return_value = mock_collector

        # Mock collect and display functions
        mock_collect.return_value = None
        mock_display.return_value = None

        # Run status
        result = runner.invoke(main, ["status", "--base-dir", str(tmp_path)])

        # Assert
        assert result.exit_code == 0


class TestStatusCommandOptions:
    """Test status command options."""

    @patch("sbkube.commands.status._display_status")
    @patch("sbkube.commands.status._collect_and_cache")
    @patch("sbkube.commands.status.ClusterStatusCollector")
    @patch("sbkube.commands.status.ClusterCache")
    def test_status_managed_filter(
        self,
        mock_cache_class,
        mock_collector_class,
        mock_collect,
        mock_display,
        runner,
        tmp_path,
    ) -> None:
        """Test --managed option filters sbkube-managed apps."""
        # Create sources.yaml
        sources_file = tmp_path / "sources.yaml"
        sources_file.write_text(
            """
kubeconfig: /fake/kubeconfig
kubeconfig_context: test-context
cluster: test-cluster
"""
        )

        # Mock cache and collector
        mock_cache = MagicMock()
        mock_cache.get_age_seconds.return_value = 60
        mock_cache.is_expired.return_value = False
        mock_cache_class.return_value = mock_cache
        mock_collector = MagicMock()
        mock_collector_class.return_value = mock_collector
        mock_collect.return_value = None
        mock_display.return_value = None

        # Run status with --managed
        result = runner.invoke(
            main, ["status", "--base-dir", str(tmp_path), "--managed"]
        )

        # Assert
        assert result.exit_code == 0

    @patch("sbkube.commands.status._display_status")
    @patch("sbkube.commands.status._collect_and_cache")
    @patch("sbkube.commands.status.ClusterStatusCollector")
    @patch("sbkube.commands.status.ClusterCache")
    def test_status_by_group(
        self,
        mock_cache_class,
        mock_collector_class,
        mock_collect,
        mock_display,
        runner,
        tmp_path,
    ) -> None:
        """Test --by-group option groups apps by app-group."""
        # Create sources.yaml
        sources_file = tmp_path / "sources.yaml"
        sources_file.write_text(
            """
kubeconfig: /fake/kubeconfig
kubeconfig_context: test-context
cluster: test-cluster
"""
        )

        # Mock cache and collector
        mock_cache = MagicMock()
        mock_cache.get_age_seconds.return_value = 60
        mock_cache.is_expired.return_value = False
        mock_cache_class.return_value = mock_cache
        mock_collector = MagicMock()
        mock_collector_class.return_value = mock_collector
        mock_collect.return_value = None
        mock_display.return_value = None

        # Run status with --by-group
        result = runner.invoke(
            main, ["status", "--base-dir", str(tmp_path), "--by-group"]
        )

        # Assert
        assert result.exit_code == 0
        # Verify by_group was passed to ClusterCache
        mock_cache_class.assert_called_once()
        call_kwargs = mock_cache_class.call_args[1]
        assert call_kwargs["by_group"] is True

    @patch("sbkube.commands.status._display_status")
    @patch("sbkube.commands.status._collect_and_cache")
    @patch("sbkube.commands.status.ClusterStatusCollector")
    @patch("sbkube.commands.status.ClusterCache")
    def test_status_refresh_cache(
        self,
        mock_cache_class,
        mock_collector_class,
        mock_collect,
        mock_display,
        runner,
        tmp_path,
    ) -> None:
        """Test --refresh option forces cache refresh."""
        # Create sources.yaml
        sources_file = tmp_path / "sources.yaml"
        sources_file.write_text(
            """
kubeconfig: /fake/kubeconfig
kubeconfig_context: test-context
cluster: test-cluster
"""
        )

        # Mock cache and collector
        mock_cache = MagicMock()
        mock_cache.get_age_seconds.return_value = 60
        mock_cache.is_expired.return_value = False
        mock_cache_class.return_value = mock_cache
        mock_collector = MagicMock()
        mock_collector_class.return_value = mock_collector
        mock_collect.return_value = None
        mock_display.return_value = None

        # Run status with --refresh
        result = runner.invoke(
            main, ["status", "--base-dir", str(tmp_path), "--refresh"]
        )

        # Assert
        assert result.exit_code == 0
        # Verify collect was called with force_refresh=True
        mock_collect.assert_called_once()
        call_kwargs = mock_collect.call_args[1]
        assert call_kwargs["force_refresh"] is True

    @patch("sbkube.commands.status._display_dependency_tree")
    @patch("sbkube.commands.status.ClusterStatusCollector")
    @patch("sbkube.commands.status.ClusterCache")
    def test_status_deps_tree(
        self,
        mock_cache_class,
        mock_collector_class,
        mock_display_deps,
        runner,
        tmp_path,
    ) -> None:
        """Test --deps option shows dependency tree."""
        # Create sources.yaml
        sources_file = tmp_path / "sources.yaml"
        sources_file.write_text(
            """
kubeconfig: /fake/kubeconfig
kubeconfig_context: test-context
cluster: test-cluster
"""
        )

        # Mock cache and collector
        mock_cache = MagicMock()
        mock_cache_class.return_value = mock_cache
        mock_collector = MagicMock()
        mock_collector_class.return_value = mock_collector
        mock_display_deps.return_value = None

        # Run status with --deps
        result = runner.invoke(main, ["status", "--base-dir", str(tmp_path), "--deps"])

        # Assert
        assert result.exit_code == 0
        # Verify dependency tree was displayed
        mock_display_deps.assert_called_once()


class TestStatusCommandErrors:
    """Test status command error handling."""

    def test_status_invalid_sources_yaml(
        self,
        runner,
        tmp_path,
    ) -> None:
        """Test error when sources.yaml is invalid."""
        # Create invalid sources.yaml
        sources_file = tmp_path / "sources.yaml"
        sources_file.write_text("invalid: yaml: content:\n  broken")

        result = runner.invoke(main, ["status", "--base-dir", str(tmp_path)])

        assert result.exit_code != 0
