"""Tests for status command."""

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

    @pytest.mark.skip(
        reason="kubeconfig now has default value for backward compatibility (v0.10.0+)"
    )
    @patch("sbkube.commands.status.ClusterStatusCollector")
    @patch("sbkube.commands.status.ClusterCache")
    def test_status_sources_missing_kubeconfig(
        self,
        mock_cache,
        mock_collector,
        runner,
        tmp_path,
    ) -> None:
        """Test status uses default kubeconfig when not specified.

        Note: As of v0.10.0, kubeconfig defaults to ~/.kube/config for
        backward compatibility with legacy configuration formats.
        """
        # Create sources.yaml without kubeconfig
        sources_file = tmp_path / "sources.yaml"
        sources_data = {
            "cluster": "test-cluster",
        }
        with open(sources_file, "w") as f:
            yaml.dump(sources_data, f)

        result = runner.invoke(main, ["status", "--base-dir", str(tmp_path)])

        # With defaults, this should not fail on validation but may fail
        # on actual kubeconfig access if ~/.kube/config doesn't exist
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


class TestStatusCommandAdvanced:
    """Test advanced status command features."""

    @patch("sbkube.commands.status._display_status")
    @patch("sbkube.commands.status._collect_and_cache")
    @patch("sbkube.commands.status.ClusterStatusCollector")
    @patch("sbkube.commands.status.ClusterCache")
    def test_status_unhealthy_filter(
        self,
        mock_cache_class,
        mock_collector_class,
        mock_collect,
        mock_display,
        runner,
        tmp_path,
    ) -> None:
        """Test --unhealthy option filters to unhealthy resources only."""
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

        # Run status with --unhealthy
        result = runner.invoke(
            main, ["status", "--base-dir", str(tmp_path), "--unhealthy"]
        )

        # Assert
        assert result.exit_code == 0
        # Verify unhealthy=True was passed to _display_status
        mock_display.assert_called_once()
        call_kwargs = mock_display.call_args[1]
        assert call_kwargs["unhealthy"] is True

    @patch("sbkube.commands.status._display_status")
    @patch("sbkube.commands.status._collect_and_cache")
    @patch("sbkube.commands.status.ClusterStatusCollector")
    @patch("sbkube.commands.status.ClusterCache")
    def test_status_health_check(
        self,
        mock_cache_class,
        mock_collector_class,
        mock_collect,
        mock_display,
        runner,
        tmp_path,
    ) -> None:
        """Test --health-check option shows detailed health status."""
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

        # Run status with --health-check
        result = runner.invoke(
            main, ["status", "--base-dir", str(tmp_path), "--health-check"]
        )

        # Assert
        assert result.exit_code == 0
        # Verify health_check=True was passed
        mock_display.assert_called_once()
        call_kwargs = mock_display.call_args[1]
        assert call_kwargs["health_check"] is True

    @patch("sbkube.commands.status._display_status")
    @patch("sbkube.commands.status._collect_and_cache")
    @patch("sbkube.commands.status.ClusterStatusCollector")
    @patch("sbkube.commands.status.ClusterCache")
    def test_status_show_notes(
        self,
        mock_cache_class,
        mock_collector_class,
        mock_collect,
        mock_display,
        runner,
        tmp_path,
    ) -> None:
        """Test --show-notes option displays app notes."""
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

        # Run status with --show-notes
        result = runner.invoke(
            main, ["status", "--base-dir", str(tmp_path), "--show-notes"]
        )

        # Assert
        assert result.exit_code == 0
        # Verify show_notes=True was passed
        mock_display.assert_called_once()
        call_kwargs = mock_display.call_args[1]
        assert call_kwargs["show_notes"] is True

    @patch("sbkube.commands.status._display_status")
    @patch("sbkube.commands.status._collect_and_cache")
    @patch("sbkube.commands.status.ClusterStatusCollector")
    @patch("sbkube.commands.status.ClusterCache")
    def test_status_specific_app_group(
        self,
        mock_cache_class,
        mock_collector_class,
        mock_collect,
        mock_display,
        runner,
        tmp_path,
    ) -> None:
        """Test filtering by specific app_group argument."""
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

        # Run status with app_group argument
        result = runner.invoke(
            main, ["status", "--base-dir", str(tmp_path), "app-group-1"]
        )

        # Assert
        assert result.exit_code == 0
        # Verify app_group was passed to cache
        mock_cache_class.assert_called_once()
        call_kwargs = mock_cache_class.call_args[1]
        assert call_kwargs["app_group"] == "app-group-1"

    @patch("sbkube.commands.status._display_status")
    @patch("sbkube.commands.status._collect_and_cache")
    @patch("sbkube.commands.status.ClusterStatusCollector")
    @patch("sbkube.commands.status.ClusterCache")
    def test_status_cache_expired(
        self,
        mock_cache_class,
        mock_collector_class,
        mock_collect,
        mock_display,
        runner,
        tmp_path,
    ) -> None:
        """Test cache refresh when cache is expired."""
        # Create sources.yaml
        sources_file = tmp_path / "sources.yaml"
        sources_file.write_text(
            """
kubeconfig: /fake/kubeconfig
kubeconfig_context: test-context
cluster: test-cluster
"""
        )

        # Mock cache as expired
        mock_cache = MagicMock()
        mock_cache.is_valid.return_value = False  # Cache expired
        mock_cache_class.return_value = mock_cache
        mock_collector = MagicMock()
        mock_collector_class.return_value = mock_collector
        mock_collect.return_value = None
        mock_display.return_value = None

        # Run status
        result = runner.invoke(main, ["status", "--base-dir", str(tmp_path)])

        # Assert - should trigger refresh
        assert result.exit_code == 0
        mock_collect.assert_called_once()


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

    @patch("sbkube.commands.status.ClusterStatusCollector")
    @patch("sbkube.commands.status.ClusterCache")
    def test_status_collector_timeout(
        self,
        mock_cache_class,
        mock_collector_class,
        runner,
        tmp_path,
    ) -> None:
        """Test error handling when collector times out."""
        import subprocess

        # Create sources.yaml
        sources_file = tmp_path / "sources.yaml"
        sources_file.write_text(
            """
kubeconfig: /fake/kubeconfig
kubeconfig_context: test-context
cluster: test-cluster
"""
        )

        # Mock cache as invalid (needs refresh)
        mock_cache = MagicMock()
        mock_cache.is_valid.return_value = False
        mock_cache.exists.return_value = False  # No fallback cache
        mock_cache_class.return_value = mock_cache

        # Mock collector to raise timeout
        mock_collector = MagicMock()
        mock_collector.collect_all.side_effect = subprocess.TimeoutExpired(
            "kubectl", 30
        )
        mock_collector_class.return_value = mock_collector

        # Run status
        result = runner.invoke(main, ["status", "--base-dir", str(tmp_path)])

        # Assert - should fail with timeout error
        assert result.exit_code != 0

    @patch("sbkube.commands.status.ClusterStatusCollector")
    @patch("sbkube.commands.status.ClusterCache")
    def test_status_collector_error_with_fallback(
        self,
        mock_cache_class,
        mock_collector_class,
        runner,
        tmp_path,
    ) -> None:
        """Test error handling with cache fallback."""
        # Create sources.yaml
        sources_file = tmp_path / "sources.yaml"
        sources_file.write_text(
            """
kubeconfig: /fake/kubeconfig
kubeconfig_context: test-context
cluster: test-cluster
"""
        )

        # Mock cache as invalid but existing (can fallback)
        mock_cache = MagicMock()
        mock_cache.is_valid.return_value = False
        mock_cache.exists.return_value = True  # Fallback available
        mock_cache.get_age_seconds.return_value = 600
        mock_cache.is_expired.return_value = True
        mock_cache_class.return_value = mock_cache

        # Mock collector to raise error
        mock_collector = MagicMock()
        mock_collector.collect_all.side_effect = Exception("Connection error")
        mock_collector_class.return_value = mock_collector

        # Run status with --refresh to trigger collection
        result = runner.invoke(
            main, ["status", "--base-dir", str(tmp_path), "--refresh"]
        )

        # Assert - should succeed using fallback cache
        # (The actual behavior may vary, but it should handle the error gracefully)
        # Based on the code, it will show error but continue with cache
        assert "Connection error" in result.output or "cache" in result.output.lower()

    @pytest.mark.skip(
        reason="kubeconfig now has default value for backward compatibility (v0.10.0+)"
    )
    def test_status_missing_kubeconfig_field(
        self,
        runner,
        tmp_path,
    ) -> None:
        """Test behavior when sources.yaml missing kubeconfig field.

        Note: As of v0.10.0, kubeconfig defaults to ~/.kube/config for
        backward compatibility with legacy configuration formats.
        """
        # Create sources.yaml without kubeconfig
        sources_file = tmp_path / "sources.yaml"
        sources_file.write_text(
            """
kubeconfig_context: test-context
cluster: test-cluster
"""
        )

        result = runner.invoke(main, ["status", "--base-dir", str(tmp_path)])

        assert result.exit_code != 0
        assert "kubeconfig" in result.output.lower()

    @pytest.mark.skip(
        reason="kubeconfig_context now has default value for backward compatibility (v0.10.0+)"
    )
    def test_status_missing_kubeconfig_context_field(
        self,
        runner,
        tmp_path,
    ) -> None:
        """Test behavior when sources.yaml missing kubeconfig_context field.

        Note: As of v0.10.0, kubeconfig_context defaults to 'default' for
        backward compatibility with legacy configuration formats.
        """
        # Create sources.yaml without kubeconfig_context
        sources_file = tmp_path / "sources.yaml"
        sources_file.write_text(
            """
kubeconfig: /fake/kubeconfig
cluster: test-cluster
"""
        )

        result = runner.invoke(main, ["status", "--base-dir", str(tmp_path)])

        assert result.exit_code != 0
        assert "kubeconfig_context" in result.output.lower()

    @patch("sbkube.commands.status.ClusterStatusCollector")
    @patch("sbkube.commands.status.ClusterCache")
    def test_status_timeout_with_cache_fallback(
        self,
        mock_cache_class,
        mock_collector_class,
        runner,
        tmp_path,
    ) -> None:
        """Test TimeoutExpired error with cache fallback."""
        import subprocess

        # Create sources.yaml
        sources_file = tmp_path / "sources.yaml"
        sources_file.write_text(
            """
kubeconfig: /fake/kubeconfig
kubeconfig_context: test-context
cluster: test-cluster
"""
        )

        # Mock cache as invalid but existing (can fallback)
        mock_cache = MagicMock()
        mock_cache.is_valid.return_value = False
        mock_cache.exists.return_value = True  # Fallback available
        mock_cache.load.return_value = {
            "cluster_name": "test-cluster",
            "context": "test-context",
            "helm_releases": [],
        }
        mock_cache.get_age_seconds.return_value = 600
        mock_cache.get_remaining_ttl.return_value = 300
        mock_cache.cache_file = tmp_path / ".sbkube" / "cluster_status" / "cache.json"
        mock_cache_class.return_value = mock_cache

        # Mock collector to raise timeout
        mock_collector = MagicMock()
        mock_collector.collect_all.side_effect = subprocess.TimeoutExpired(
            "kubectl", 30
        )
        mock_collector_class.return_value = mock_collector

        # Run status
        result = runner.invoke(main, ["status", "--base-dir", str(tmp_path)])

        # Assert - should use fallback cache
        assert result.exit_code == 0
        assert "timeout" in result.output.lower() or "cache" in result.output.lower()

    @patch("sbkube.commands.status.ClusterStatusCollector")
    @patch("sbkube.commands.status.ClusterCache")
    def test_status_called_process_error_with_cache(
        self,
        mock_cache_class,
        mock_collector_class,
        runner,
        tmp_path,
    ) -> None:
        """Test CalledProcessError with cache fallback."""
        import subprocess

        # Create sources.yaml
        sources_file = tmp_path / "sources.yaml"
        sources_file.write_text(
            """
kubeconfig: /fake/kubeconfig
kubeconfig_context: test-context
cluster: test-cluster
"""
        )

        # Mock cache as invalid but existing (can fallback)
        mock_cache = MagicMock()
        mock_cache.is_valid.return_value = False
        mock_cache.exists.return_value = True  # Fallback available
        mock_cache.load.return_value = {
            "cluster_name": "test-cluster",
            "context": "test-context",
            "helm_releases": [],
        }
        mock_cache.get_age_seconds.return_value = 600
        mock_cache.get_remaining_ttl.return_value = 300
        mock_cache.cache_file = tmp_path / ".sbkube" / "cluster_status" / "cache.json"
        mock_cache_class.return_value = mock_cache

        # Mock collector to raise CalledProcessError
        mock_collector = MagicMock()
        mock_collector.collect_all.side_effect = subprocess.CalledProcessError(
            1, "kubectl", stderr="Error: connection refused"
        )
        mock_collector_class.return_value = mock_collector

        # Run status
        result = runner.invoke(main, ["status", "--base-dir", str(tmp_path)])

        # Assert - should use fallback cache
        assert result.exit_code == 0
        assert "error" in result.output.lower() or "cache" in result.output.lower()

    @patch("sbkube.commands.status.ClusterStatusCollector")
    @patch("sbkube.commands.status.ClusterCache")
    def test_status_called_process_error_without_cache(
        self,
        mock_cache_class,
        mock_collector_class,
        runner,
        tmp_path,
    ) -> None:
        """Test CalledProcessError without cache fallback."""
        import subprocess

        # Create sources.yaml
        sources_file = tmp_path / "sources.yaml"
        sources_file.write_text(
            """
kubeconfig: /fake/kubeconfig
kubeconfig_context: test-context
cluster: test-cluster
"""
        )

        # Mock cache as invalid and not existing (no fallback)
        mock_cache = MagicMock()
        mock_cache.is_valid.return_value = False
        mock_cache.exists.return_value = False  # No fallback
        mock_cache_class.return_value = mock_cache

        # Mock collector to raise CalledProcessError
        mock_collector = MagicMock()
        mock_collector.collect_all.side_effect = subprocess.CalledProcessError(
            1, "kubectl", stderr="Error: connection refused"
        )
        mock_collector_class.return_value = mock_collector

        # Run status
        result = runner.invoke(main, ["status", "--base-dir", str(tmp_path)])

        # Assert - should fail without cache
        assert result.exit_code != 0
        assert "error" in result.output.lower()

    @patch("sbkube.commands.status.ClusterStatusCollector")
    @patch("sbkube.commands.status.ClusterCache")
    def test_status_empty_cache_data(
        self,
        mock_cache_class,
        mock_collector_class,
        runner,
        tmp_path,
    ) -> None:
        """Test error when cache data is empty."""
        # Create sources.yaml
        sources_file = tmp_path / "sources.yaml"
        sources_file.write_text(
            """
kubeconfig: /fake/kubeconfig
kubeconfig_context: test-context
cluster: test-cluster
"""
        )

        # Mock cache as valid but load returns empty/None
        mock_cache = MagicMock()
        mock_cache.is_valid.return_value = True
        mock_cache.load.return_value = None  # Empty cache data
        mock_cache.get_age_seconds.return_value = 60
        mock_cache_class.return_value = mock_cache

        mock_collector = MagicMock()
        mock_collector_class.return_value = mock_collector

        # Run status
        result = runner.invoke(main, ["status", "--base-dir", str(tmp_path)])

        # Assert - should fail with empty cache
        assert result.exit_code != 0
        assert "no cached data" in result.output.lower() or "available" in result.output.lower()


class TestStatusCommandCombinations:
    """Test various option combinations."""

    @patch("sbkube.commands.status._display_status")
    @patch("sbkube.commands.status._collect_and_cache")
    @patch("sbkube.commands.status.ClusterStatusCollector")
    @patch("sbkube.commands.status.ClusterCache")
    def test_status_by_group_and_managed(
        self,
        mock_cache_class,
        mock_collector_class,
        mock_collect,
        mock_display,
        runner,
        tmp_path,
    ) -> None:
        """Test --by-group and --managed together."""
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

        # Run status with both options
        result = runner.invoke(
            main, ["status", "--base-dir", str(tmp_path), "--by-group", "--managed"]
        )

        # Assert
        assert result.exit_code == 0
        # Verify both options were passed
        call_kwargs = mock_display.call_args[1]
        assert call_kwargs["by_group"] is True
        assert call_kwargs["managed"] is True

    @patch("sbkube.commands.status._display_status")
    @patch("sbkube.commands.status._collect_and_cache")
    @patch("sbkube.commands.status.ClusterStatusCollector")
    @patch("sbkube.commands.status.ClusterCache")
    def test_status_all_option(
        self,
        mock_cache_class,
        mock_collector_class,
        mock_collect,
        mock_display,
        runner,
        tmp_path,
    ) -> None:
        """Test --all option shows all resources."""
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

        # Run status with --all
        result = runner.invoke(
            main, ["status", "--base-dir", str(tmp_path), "--all"]
        )

        # Assert
        assert result.exit_code == 0
        # Verify show_all=True was passed
        call_kwargs = mock_display.call_args[1]
        assert call_kwargs["show_all"] is True

    @patch("sbkube.commands.status._display_status")
    @patch("sbkube.commands.status._collect_and_cache")
    @patch("sbkube.commands.status.ClusterStatusCollector")
    @patch("sbkube.commands.status.ClusterCache")
    def test_status_refresh_and_unhealthy(
        self,
        mock_cache_class,
        mock_collector_class,
        mock_collect,
        mock_display,
        runner,
        tmp_path,
    ) -> None:
        """Test --refresh and --unhealthy together."""
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
        mock_cache.is_valid.return_value = True  # Cache is valid
        mock_cache.get_age_seconds.return_value = 60
        mock_cache.is_expired.return_value = False
        mock_cache_class.return_value = mock_cache
        mock_collector = MagicMock()
        mock_collector_class.return_value = mock_collector
        mock_collect.return_value = None
        mock_display.return_value = None

        # Run status with both options
        result = runner.invoke(
            main,
            ["status", "--base-dir", str(tmp_path), "--refresh", "--unhealthy"],
        )

        # Assert
        assert result.exit_code == 0
        # Verify refresh was called even though cache was valid
        mock_collect.assert_called_once()
        call_kwargs = mock_collect.call_args[1]
        assert call_kwargs["force_refresh"] is True
        # Verify unhealthy filter was passed
        call_kwargs_display = mock_display.call_args[1]
        assert call_kwargs_display["unhealthy"] is True

    @patch("sbkube.commands.status._display_status")
    @patch("sbkube.commands.status._prepare_cache_data")
    @patch("sbkube.commands.status.ClusterStatusCollector")
    @patch("sbkube.commands.status.ClusterCache")
    def test_status_with_collect_all_data(
        self,
        mock_cache_class,
        mock_collector_class,
        mock_prepare_cache,
        mock_display,
        runner,
        tmp_path,
    ) -> None:
        """Test actual data flow through collect_all."""
        # Create sources.yaml
        sources_file = tmp_path / "sources.yaml"
        sources_file.write_text(
            """
kubeconfig: /fake/kubeconfig
kubeconfig_context: test-context
cluster: test-cluster
"""
        )

        # Mock cache as invalid (needs refresh)
        mock_cache = MagicMock()
        mock_cache.is_valid.return_value = False
        mock_cache_class.return_value = mock_cache

        # Mock collector to return some status data
        mock_collector = MagicMock()
        mock_status_data = {
            "helm_releases": [
                {"name": "nginx", "namespace": "default", "status": "deployed"}
            ],
            "deployments": [],
            "services": [],
        }
        mock_collector.collect_all.return_value = mock_status_data
        mock_collector_class.return_value = mock_collector

        # Mock prepare_cache_data
        mock_prepare_cache.return_value = mock_status_data
        mock_display.return_value = None

        # Run status
        result = runner.invoke(main, ["status", "--base-dir", str(tmp_path)])

        # Assert
        assert result.exit_code == 0
        # Verify data flow
        mock_collector.collect_all.assert_called_once()
        mock_prepare_cache.assert_called_once()
        mock_cache.save.assert_called_once_with(mock_status_data)

    @patch("sbkube.commands.status._display_status")
    @patch("sbkube.commands.status._collect_and_cache")
    @patch("sbkube.commands.status.ClusterStatusCollector")
    @patch("sbkube.commands.status.ClusterCache")
    @patch("time.sleep")
    def test_status_watch_mode_interrupted(
        self,
        mock_sleep,
        mock_cache_class,
        mock_collector_class,
        mock_collect,
        mock_display,
        runner,
        tmp_path,
    ) -> None:
        """Test --watch mode with KeyboardInterrupt."""
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

        # Mock sleep to raise KeyboardInterrupt after first iteration
        mock_sleep.side_effect = KeyboardInterrupt()

        # Run status with --watch
        result = runner.invoke(
            main, ["status", "--base-dir", str(tmp_path), "--watch"]
        )

        # Assert - should exit cleanly with KeyboardInterrupt
        assert result.exit_code == 0
        # Verify it tried to sleep (watch loop started)
        mock_sleep.assert_called_once()
        assert "Stopped watching" in result.output or "watch" in result.output.lower()
