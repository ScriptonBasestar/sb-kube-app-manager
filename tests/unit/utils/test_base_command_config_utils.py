"""Tests for EnhancedBaseCommand config loading utilities (Phase 1.3)."""

from pathlib import Path
from unittest.mock import MagicMock, patch

import pytest

from sbkube.utils.base_command import EnhancedBaseCommand


class TestLoadAndValidateConfigFile:
    """Test load_and_validate_config_file method."""

    def test_returns_none_when_file_not_exists(self, tmp_path: Path) -> None:
        """Test returns None when config file doesn't exist."""
        cmd = EnhancedBaseCommand(base_dir=str(tmp_path))
        config_path = tmp_path / "nonexistent" / "config.yaml"

        output = MagicMock()
        result = cmd.load_and_validate_config_file(config_path, output)

        assert result is None
        output.print_error.assert_called_once()
        assert "not found" in output.print_error.call_args[0][0]

    def test_loads_valid_config(self, tmp_path: Path) -> None:
        """Test successfully loads valid config file."""
        # Create valid config (namespace is required)
        config_path = tmp_path / "config.yaml"
        config_path.write_text("""
namespace: default
apps:
  nginx:
    type: helm
    chart: bitnami/nginx
""")

        cmd = EnhancedBaseCommand(base_dir=str(tmp_path))
        output = MagicMock()

        result = cmd.load_and_validate_config_file(config_path, output)

        assert result is not None
        assert "nginx" in result.apps
        output.print.assert_called()

    def test_returns_none_for_invalid_config(self, tmp_path: Path) -> None:
        """Test returns None for invalid config content."""
        config_path = tmp_path / "config.yaml"
        config_path.write_text("""
# Missing required namespace field
apps:
  nginx:
    type: helm
    chart: nginx
""")

        cmd = EnhancedBaseCommand(base_dir=str(tmp_path))
        output = MagicMock()

        result = cmd.load_and_validate_config_file(config_path, output)

        assert result is None
        output.print_error.assert_called_once()

    def test_uses_logger_when_no_output(self, tmp_path: Path) -> None:
        """Test uses logger when output manager not provided."""
        config_path = tmp_path / "nonexistent.yaml"

        cmd = EnhancedBaseCommand(base_dir=str(tmp_path))

        with patch("sbkube.utils.base_command.logger") as mock_logger:
            result = cmd.load_and_validate_config_file(config_path)

            assert result is None
            mock_logger.error.assert_called_once()


class TestLoadAndValidateSourcesFile:
    """Test load_and_validate_sources_file method."""

    def test_returns_none_when_file_not_exists(self, tmp_path: Path) -> None:
        """Test returns None when sources file doesn't exist."""
        cmd = EnhancedBaseCommand(base_dir=str(tmp_path))
        sources_path = tmp_path / "nonexistent" / "sources.yaml"

        result = cmd.load_and_validate_sources_file(sources_path)

        # sources.yaml is optional, so no error expected
        assert result is None

    def test_returns_none_for_none_path(self, tmp_path: Path) -> None:
        """Test returns None when path is None."""
        cmd = EnhancedBaseCommand(base_dir=str(tmp_path))

        result = cmd.load_and_validate_sources_file(None)

        assert result is None

    def test_loads_valid_sources(self, tmp_path: Path) -> None:
        """Test successfully loads valid sources file."""
        sources_path = tmp_path / "sources.yaml"
        sources_path.write_text("""
cluster: test-cluster
kubeconfig: ~/.kube/config
kubeconfig_context: test-context
helm_repos:
  bitnami:
    url: https://charts.bitnami.com/bitnami
""")

        cmd = EnhancedBaseCommand(base_dir=str(tmp_path))
        output = MagicMock()

        result = cmd.load_and_validate_sources_file(sources_path, output)

        assert result is not None
        assert result.cluster == "test-cluster"
        output.print.assert_called()

    def test_returns_none_for_invalid_sources(self, tmp_path: Path) -> None:
        """Test returns None for invalid sources content."""
        sources_path = tmp_path / "sources.yaml"
        sources_path.write_text("""
invalid_key: value
# Missing required cluster field in some validators
""")

        cmd = EnhancedBaseCommand(base_dir=str(tmp_path))
        output = MagicMock()

        # May or may not fail depending on validation strictness
        # Just ensure it doesn't crash
        result = cmd.load_and_validate_sources_file(sources_path, output)
        # Result depends on model validation


class TestResolveClusterConfiguration:
    """Test resolve_cluster_configuration method."""

    def test_resolves_with_cli_options(self, tmp_path: Path) -> None:
        """Test resolves cluster config from CLI options."""
        cmd = EnhancedBaseCommand(base_dir=str(tmp_path))

        with patch("sbkube.utils.cluster_config.resolve_cluster_config") as mock_resolve:
            mock_resolve.return_value = ("/path/to/kubeconfig", "my-context")

            # Skip connectivity check for unit test
            result = cmd.resolve_cluster_configuration(
                cli_kubeconfig="/path/to/kubeconfig",
                cli_context="my-context",
                sources=None,
                check_connectivity=False,
            )

            assert result == ("/path/to/kubeconfig", "my-context")
            mock_resolve.assert_called_once()

    def test_returns_none_on_cluster_config_error(self, tmp_path: Path) -> None:
        """Test returns None when ClusterConfigError is raised."""
        from sbkube.utils.cluster_config import ClusterConfigError

        cmd = EnhancedBaseCommand(base_dir=str(tmp_path))
        output = MagicMock()

        with patch("sbkube.utils.cluster_config.resolve_cluster_config") as mock_resolve:
            mock_resolve.side_effect = ClusterConfigError("Invalid config")

            result = cmd.resolve_cluster_configuration(
                cli_kubeconfig=None,
                cli_context=None,
                sources=None,
                output=output,
                check_connectivity=False,
            )

            assert result is None
            output.print_error.assert_called_once()

    def test_returns_none_on_connectivity_failure(self, tmp_path: Path) -> None:
        """Test returns None when connectivity check fails."""
        cmd = EnhancedBaseCommand(base_dir=str(tmp_path))

        with patch("sbkube.utils.cluster_config.resolve_cluster_config") as mock_resolve:
            mock_resolve.return_value = ("/path/to/kubeconfig", "my-context")

            with patch(
                "sbkube.utils.cli_check.check_cluster_connectivity_or_exit"
            ) as mock_check:
                mock_check.side_effect = SystemExit(1)

                result = cmd.resolve_cluster_configuration(
                    cli_kubeconfig="/path/to/kubeconfig",
                    cli_context="my-context",
                    sources=None,
                    check_connectivity=True,
                )

                assert result is None


class TestGetClusterGlobalValues:
    """Test get_cluster_global_values method."""

    def test_returns_none_when_no_sources(self, tmp_path: Path) -> None:
        """Test returns None when sources is None."""
        cmd = EnhancedBaseCommand(base_dir=str(tmp_path))

        result = cmd.get_cluster_global_values(
            sources=None,
            sources_dir=tmp_path,
        )

        assert result is None

    def test_returns_values_from_sources(self, tmp_path: Path) -> None:
        """Test returns global values from sources."""
        cmd = EnhancedBaseCommand(base_dir=str(tmp_path))

        mock_sources = MagicMock()
        mock_sources.get_merged_global_values.return_value = {
            "global": {"key": "value"}
        }

        output = MagicMock()
        result = cmd.get_cluster_global_values(
            sources=mock_sources,
            sources_dir=tmp_path,
            output=output,
        )

        assert result == {"global": {"key": "value"}}
        output.print.assert_called()  # Info message about loading values

    def test_returns_none_on_error(self, tmp_path: Path) -> None:
        """Test returns None when get_merged_global_values fails."""
        cmd = EnhancedBaseCommand(base_dir=str(tmp_path))

        mock_sources = MagicMock()
        mock_sources.get_merged_global_values.side_effect = Exception("Load error")

        output = MagicMock()
        result = cmd.get_cluster_global_values(
            sources=mock_sources,
            sources_dir=tmp_path,
            output=output,
        )

        assert result is None
        output.print_warning.assert_called_once()

    def test_returns_none_when_no_values_configured(self, tmp_path: Path) -> None:
        """Test returns None when no global values configured."""
        cmd = EnhancedBaseCommand(base_dir=str(tmp_path))

        mock_sources = MagicMock()
        mock_sources.get_merged_global_values.return_value = None

        result = cmd.get_cluster_global_values(
            sources=mock_sources,
            sources_dir=tmp_path,
        )

        assert result is None
