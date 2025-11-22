"""Unit tests for status.py command.

Tests verify:
- Basic status display
- Filtering options (--managed, --unhealthy, --by-group)
- Cache operations (--refresh)
- App group filtering
- Output format handling
- Error handling
"""

from unittest.mock import MagicMock, patch

import pytest
import yaml
from click.testing import CliRunner

from sbkube.commands.status import cmd


@pytest.fixture
def setup_sources(base_dir):
    """Create minimal sources.yaml in base_dir."""
    sources_file = base_dir / "sources.yaml"
    sources_file.write_text(
        yaml.dump({
            "kubeconfig": "~/.kube/config",
            "kubeconfig_context": "test-context",
            "cluster": "test-cluster",
            "helm_repos": {},
        })
    )
    return base_dir


@pytest.fixture
def mock_config_sources():
    """Create mock sources object."""
    mock_sources = MagicMock()
    mock_sources.kubeconfig = "~/.kube/config"
    mock_sources.kubeconfig_context = "test-context"
    mock_sources.cluster = "test-cluster"
    return mock_sources


class TestStatusBasic:
    """Test basic status command functionality."""

    @patch("sbkube.commands.status._display_status")
    @patch("sbkube.commands.status.ClusterCache")
    @patch("sbkube.commands.status.ClusterStatusCollector")
    @patch("sbkube.commands.status.ConfigManager")
    def test_status_basic_display(self, mock_config_class, mock_collector_class, mock_cache_class, mock_display, setup_sources, mock_config_sources):
        """Test basic status display without options."""
        # Arrange
        base_dir = setup_sources

        mock_config_manager = MagicMock()
        mock_config_class.return_value = mock_config_manager
        mock_config_manager.load_sources.return_value = mock_config_sources

        mock_cache = MagicMock()
        mock_cache_class.return_value = mock_cache
        mock_cache.is_valid.return_value = True
        mock_cache.get_age_seconds.return_value = 60

        mock_collector = MagicMock()
        mock_collector_class.return_value = mock_collector

        # Act
        runner = CliRunner()
        result = runner.invoke(cmd, ["--base-dir", str(base_dir)], obj={"format": "human"})

        # Assert
        assert result.exit_code == 0
        mock_display.assert_called_once()

    @patch("sbkube.commands.status._display_status")
    @patch("sbkube.commands.status._collect_and_cache")
    @patch("sbkube.commands.status.ClusterCache")
    @patch("sbkube.commands.status.ClusterStatusCollector")
    @patch("sbkube.commands.status.ConfigManager")
    def test_status_with_refresh(self, mock_config_class, mock_collector_class, mock_cache_class, mock_collect, mock_display, setup_sources, mock_config_sources):
        """Test status with --refresh flag to force cache update."""
        # Arrange
        base_dir = setup_sources

        mock_config_manager = MagicMock()
        mock_config_class.return_value = mock_config_manager
        mock_config_manager.load_sources.return_value = mock_config_sources

        mock_cache = MagicMock()
        mock_cache_class.return_value = mock_cache

        mock_collector = MagicMock()
        mock_collector_class.return_value = mock_collector

        # Act
        runner = CliRunner()
        result = runner.invoke(cmd, ["--base-dir", str(base_dir), "--refresh"], obj={"format": "human"})

        # Assert
        assert result.exit_code == 0
        mock_collect.assert_called_once()
        mock_display.assert_called_once()

    @patch("sbkube.commands.status._display_status")
    @patch("sbkube.commands.status.ClusterCache")
    @patch("sbkube.commands.status.ClusterStatusCollector")
    @patch("sbkube.commands.status.ConfigManager")
    def test_status_managed_only(self, mock_config_class, mock_collector_class, mock_cache_class, mock_display, setup_sources, mock_config_sources):
        """Test --managed flag to show only sbkube-managed apps."""
        # Arrange
        base_dir = setup_sources

        mock_config_manager = MagicMock()
        mock_config_class.return_value = mock_config_manager
        mock_config_manager.load_sources.return_value = mock_config_sources

        mock_cache = MagicMock()
        mock_cache_class.return_value = mock_cache
        mock_cache.is_valid.return_value = True
        mock_cache.get_age_seconds.return_value = 60

        mock_collector = MagicMock()
        mock_collector_class.return_value = mock_collector

        # Act
        runner = CliRunner()
        result = runner.invoke(cmd, ["--base-dir", str(base_dir), "--managed"], obj={"format": "human"})

        # Assert
        assert result.exit_code == 0


class TestStatusFiltering:
    """Test status filtering options."""

    @patch("sbkube.commands.status._display_status")
    @patch("sbkube.commands.status.ClusterCache")
    @patch("sbkube.commands.status.ClusterStatusCollector")
    @patch("sbkube.commands.status.ConfigManager")
    def test_status_unhealthy_only(self, mock_config_class, mock_collector_class, mock_cache_class, mock_display, setup_sources, mock_config_sources):
        """Test --unhealthy flag to show only unhealthy resources."""
        # Arrange
        base_dir = setup_sources

        mock_config_manager = MagicMock()
        mock_config_class.return_value = mock_config_manager
        mock_config_manager.load_sources.return_value = mock_config_sources

        mock_cache = MagicMock()
        mock_cache_class.return_value = mock_cache
        mock_cache.is_valid.return_value = True
        mock_cache.get_age_seconds.return_value = 60

        mock_collector = MagicMock()
        mock_collector_class.return_value = mock_collector

        # Act
        runner = CliRunner()
        result = runner.invoke(cmd, ["--base-dir", str(base_dir), "--unhealthy"], obj={"format": "human"})

        # Assert
        assert result.exit_code == 0

    @patch("sbkube.commands.status._display_status")
    @patch("sbkube.commands.status.ClusterCache")
    @patch("sbkube.commands.status.ClusterStatusCollector")
    @patch("sbkube.commands.status.ConfigManager")
    def test_status_by_group(self, mock_config_class, mock_collector_class, mock_cache_class, mock_display, setup_sources, mock_config_sources):
        """Test --by-group flag to group applications by app-group."""
        # Arrange
        base_dir = setup_sources

        mock_config_manager = MagicMock()
        mock_config_class.return_value = mock_config_manager
        mock_config_manager.load_sources.return_value = mock_config_sources

        mock_cache = MagicMock()
        mock_cache_class.return_value = mock_cache
        mock_cache.is_valid.return_value = True
        mock_cache.get_age_seconds.return_value = 60

        mock_collector = MagicMock()
        mock_collector_class.return_value = mock_collector

        # Act
        runner = CliRunner()
        result = runner.invoke(cmd, ["--base-dir", str(base_dir), "--by-group"], obj={"format": "human"})

        # Assert
        assert result.exit_code == 0

    @patch("sbkube.commands.status._display_status")
    @patch("sbkube.commands.status.ClusterCache")
    @patch("sbkube.commands.status.ClusterStatusCollector")
    @patch("sbkube.commands.status.ConfigManager")
    def test_status_with_app_group_filter(self, mock_config_class, mock_collector_class, mock_cache_class, mock_display, setup_sources, mock_config_sources):
        """Test filtering by specific app group argument."""
        # Arrange
        base_dir = setup_sources

        mock_config_manager = MagicMock()
        mock_config_class.return_value = mock_config_manager
        mock_config_manager.load_sources.return_value = mock_config_sources

        mock_cache = MagicMock()
        mock_cache_class.return_value = mock_cache
        mock_cache.is_valid.return_value = True
        mock_cache.get_age_seconds.return_value = 60

        mock_collector = MagicMock()
        mock_collector_class.return_value = mock_collector

        # Act
        runner = CliRunner()
        result = runner.invoke(cmd, ["--base-dir", str(base_dir), "redis"], obj={"format": "human"})

        # Assert
        assert result.exit_code == 0


class TestStatusAdvancedFeatures:
    """Test advanced status features."""

    @patch("sbkube.commands.status._display_dependency_tree")
    @patch("sbkube.commands.status.ClusterCache")
    @patch("sbkube.commands.status.ClusterStatusCollector")
    @patch("sbkube.commands.status.ConfigManager")
    def test_status_with_deps(self, mock_config_class, mock_collector_class, mock_cache_class, mock_display_tree, setup_sources, mock_config_sources):
        """Test --deps flag to show dependency tree."""
        # Arrange
        base_dir = setup_sources

        mock_config_manager = MagicMock()
        mock_config_class.return_value = mock_config_manager
        mock_config_manager.load_sources.return_value = mock_config_sources

        mock_cache = MagicMock()
        mock_cache_class.return_value = mock_cache

        mock_collector = MagicMock()
        mock_collector_class.return_value = mock_collector

        # Act
        runner = CliRunner()
        result = runner.invoke(cmd, ["--base-dir", str(base_dir), "--deps"], obj={"format": "human"})

        # Assert
        assert result.exit_code == 0
        mock_display_tree.assert_called_once()

    @patch("sbkube.commands.status._display_status")
    @patch("sbkube.commands.status.ClusterCache")
    @patch("sbkube.commands.status.ClusterStatusCollector")
    @patch("sbkube.commands.status.ConfigManager")
    def test_status_with_health_check(self, mock_config_class, mock_collector_class, mock_cache_class, mock_display, setup_sources, mock_config_sources):
        """Test --health-check flag for detailed health status."""
        # Arrange
        base_dir = setup_sources

        mock_config_manager = MagicMock()
        mock_config_class.return_value = mock_config_manager
        mock_config_manager.load_sources.return_value = mock_config_sources

        mock_cache = MagicMock()
        mock_cache_class.return_value = mock_cache
        mock_cache.is_valid.return_value = True
        mock_cache.get_age_seconds.return_value = 60

        mock_collector = MagicMock()
        mock_collector_class.return_value = mock_collector

        # Act
        runner = CliRunner()
        result = runner.invoke(cmd, ["--base-dir", str(base_dir), "--health-check"], obj={"format": "human"})

        # Assert
        assert result.exit_code == 0

    @patch("sbkube.commands.status._display_status")
    @patch("sbkube.commands.status.ClusterCache")
    @patch("sbkube.commands.status.ClusterStatusCollector")
    @patch("sbkube.commands.status.ConfigManager")
    def test_status_with_notes(self, mock_config_class, mock_collector_class, mock_cache_class, mock_display, setup_sources, mock_config_sources):
        """Test --show-notes flag to display application notes."""
        # Arrange
        base_dir = setup_sources

        mock_config_manager = MagicMock()
        mock_config_class.return_value = mock_config_manager
        mock_config_manager.load_sources.return_value = mock_config_sources

        mock_cache = MagicMock()
        mock_cache_class.return_value = mock_cache
        mock_cache.is_valid.return_value = True
        mock_cache.get_age_seconds.return_value = 60

        mock_collector = MagicMock()
        mock_collector_class.return_value = mock_collector

        # Act
        runner = CliRunner()
        result = runner.invoke(cmd, ["--base-dir", str(base_dir), "--show-notes"], obj={"format": "human"})

        # Assert
        assert result.exit_code == 0


class TestStatusCombinedOptions:
    """Test combinations of status options."""

    @patch("sbkube.commands.status._display_status")
    @patch("sbkube.commands.status.ClusterCache")
    @patch("sbkube.commands.status.ClusterStatusCollector")
    @patch("sbkube.commands.status.ConfigManager")
    def test_status_managed_unhealthy_combined(self, mock_config_class, mock_collector_class, mock_cache_class, mock_display, setup_sources, mock_config_sources):
        """Test combining --managed and --unhealthy flags."""
        # Arrange
        base_dir = setup_sources

        mock_config_manager = MagicMock()
        mock_config_class.return_value = mock_config_manager
        mock_config_manager.load_sources.return_value = mock_config_sources

        mock_cache = MagicMock()
        mock_cache_class.return_value = mock_cache
        mock_cache.is_valid.return_value = True
        mock_cache.get_age_seconds.return_value = 60

        mock_collector = MagicMock()
        mock_collector_class.return_value = mock_collector

        # Act
        runner = CliRunner()
        result = runner.invoke(
            cmd, ["--base-dir", str(base_dir), "--managed", "--unhealthy"], obj={"format": "human"}
        )

        # Assert
        assert result.exit_code == 0

    @patch("sbkube.commands.status._display_status")
    @patch("sbkube.commands.status.ClusterCache")
    @patch("sbkube.commands.status.ClusterStatusCollector")
    @patch("sbkube.commands.status.ConfigManager")
    def test_status_by_group_with_filter(self, mock_config_class, mock_collector_class, mock_cache_class, mock_display, setup_sources, mock_config_sources):
        """Test --by-group with specific app group filter."""
        # Arrange
        base_dir = setup_sources

        mock_config_manager = MagicMock()
        mock_config_class.return_value = mock_config_manager
        mock_config_manager.load_sources.return_value = mock_config_sources

        mock_cache = MagicMock()
        mock_cache_class.return_value = mock_cache
        mock_cache.is_valid.return_value = True
        mock_cache.get_age_seconds.return_value = 60

        mock_collector = MagicMock()
        mock_collector_class.return_value = mock_collector

        # Act
        runner = CliRunner()
        result = runner.invoke(
            cmd, ["--base-dir", str(base_dir), "--by-group", "redis"], obj={"format": "human"}
        )

        # Assert
        assert result.exit_code == 0


class TestStatusBaseDir:
    """Test base directory handling."""

    @patch("sbkube.commands.status._display_status")
    @patch("sbkube.commands.status.ClusterCache")
    @patch("sbkube.commands.status.ClusterStatusCollector")
    @patch("sbkube.commands.status.ConfigManager")
    def test_status_custom_base_dir(self, mock_config_class, mock_collector_class, mock_cache_class, mock_display, tmp_path, mock_config_sources):
        """Test status with custom --base-dir."""
        # Arrange
        custom_base = tmp_path / "custom"
        custom_base.mkdir()
        sources_file = custom_base / "sources.yaml"
        sources_file.write_text(
            yaml.dump({
                "kubeconfig": "~/.kube/config",
                "kubeconfig_context": "test-context",
                "cluster": "test-cluster",
                "helm_repos": {},
            })
        )

        mock_config_manager = MagicMock()
        mock_config_class.return_value = mock_config_manager
        mock_config_manager.load_sources.return_value = mock_config_sources

        mock_cache = MagicMock()
        mock_cache_class.return_value = mock_cache
        mock_cache.is_valid.return_value = True
        mock_cache.get_age_seconds.return_value = 60

        mock_collector = MagicMock()
        mock_collector_class.return_value = mock_collector

        # Act
        runner = CliRunner()
        result = runner.invoke(
            cmd, ["--base-dir", str(custom_base)], obj={"format": "human"}
        )

        # Assert
        assert result.exit_code == 0
