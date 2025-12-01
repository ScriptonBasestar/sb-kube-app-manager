"""Unit tests for helm utility functions."""

import json
import subprocess
from unittest.mock import MagicMock, patch

import pytest

from sbkube.exceptions import (
    CliToolExecutionError,
    CliToolNotFoundError,
    KubernetesConnectionError,
)
from sbkube.utils.helm_util import (
    get_all_chart_versions,
    get_all_helm_releases,
    get_latest_chart_version,
    search_helm_chart,
)


class TestGetAllHelmReleases:
    """Test getting all Helm releases across namespaces."""

    def test_get_all_releases_success(self):
        """Test successful retrieval of Helm releases."""
        mock_releases = [
            {
                "name": "grafana",
                "namespace": "monitoring",
                "chart": "grafana-10.1.2",
                "app_version": "10.4.0",
                "status": "deployed",
                "revision": 1,
            },
            {
                "name": "nginx",
                "namespace": "default",
                "chart": "nginx-1.0.0",
                "app_version": "1.25.0",
                "status": "deployed",
                "revision": 2,
            },
        ]

        with patch("subprocess.run") as mock_run:
            mock_run.return_value = MagicMock(
                stdout=json.dumps(mock_releases), returncode=0
            )

            releases = get_all_helm_releases()

            assert len(releases) == 2
            assert releases[0]["name"] == "grafana"
            assert releases[1]["name"] == "nginx"
            mock_run.assert_called_once()
            args = mock_run.call_args[0][0]
            assert args[0] == "helm"
            assert args[1] == "list"
            assert "--all-namespaces" in args

    def test_get_all_releases_with_kubeconfig(self):
        """Test with kubeconfig parameter."""
        with patch("subprocess.run") as mock_run:
            mock_run.return_value = MagicMock(stdout="[]", returncode=0)

            get_all_helm_releases(kubeconfig="/path/to/kubeconfig")

            args = mock_run.call_args[0][0]
            assert "--kubeconfig" in args
            assert "/path/to/kubeconfig" in args

    def test_get_all_releases_with_context(self):
        """Test with context parameter."""
        with patch("subprocess.run") as mock_run:
            mock_run.return_value = MagicMock(stdout="[]", returncode=0)

            get_all_helm_releases(context="my-context")

            args = mock_run.call_args[0][0]
            assert "--kube-context" in args
            assert "my-context" in args

    def test_get_all_releases_helm_not_found(self):
        """Test when helm is not installed."""
        with patch("subprocess.run", side_effect=FileNotFoundError()):
            with pytest.raises(CliToolNotFoundError) as exc_info:
                get_all_helm_releases()
            assert "helm" in str(exc_info.value)

    def test_get_all_releases_cluster_unreachable(self):
        """Test when cluster is unreachable."""
        with patch("subprocess.run") as mock_run:
            mock_run.side_effect = subprocess.CalledProcessError(
                1,
                ["helm", "list"],
                stderr="connection refused: unable to connect to server",
            )

            with pytest.raises(KubernetesConnectionError):
                get_all_helm_releases()


class TestSearchHelmChart:
    """Test searching for Helm charts."""

    def test_search_chart_success(self):
        """Test successful chart search."""
        mock_results = [
            {
                "name": "grafana/grafana",
                "version": "10.2.0",
                "app_version": "10.5.0",
                "description": "Grafana Helm chart",
            }
        ]

        with patch("subprocess.run") as mock_run:
            mock_run.return_value = MagicMock(
                stdout=json.dumps(mock_results), returncode=0
            )

            results = search_helm_chart("grafana", "grafana")

            assert len(results) == 1
            assert results[0]["version"] == "10.2.0"
            args = mock_run.call_args[0][0]
            assert "helm" in args
            assert "search" in args
            assert "repo" in args
            assert "grafana/grafana" in args

    def test_search_chart_with_version(self):
        """Test searching for specific version."""
        with patch("subprocess.run") as mock_run:
            mock_run.return_value = MagicMock(stdout="[]", returncode=0)

            search_helm_chart("grafana", "grafana", version="10.1.2")

            args = mock_run.call_args[0][0]
            assert "--version" in args
            assert "10.1.2" in args

    def test_search_chart_all_versions(self):
        """Test searching for all versions."""
        mock_results = [
            {"name": "grafana/grafana", "version": "10.2.0", "app_version": "10.5.0"},
            {"name": "grafana/grafana", "version": "10.1.2", "app_version": "10.4.0"},
            {"name": "grafana/grafana", "version": "10.0.0", "app_version": "10.3.0"},
        ]

        with patch("subprocess.run") as mock_run:
            mock_run.return_value = MagicMock(
                stdout=json.dumps(mock_results), returncode=0
            )

            results = search_helm_chart("grafana", "grafana", all_versions=True)

            assert len(results) == 3
            args = mock_run.call_args[0][0]
            assert "--versions" in args

    def test_search_chart_not_found(self):
        """Test when chart is not found."""
        with patch("subprocess.run") as mock_run:
            mock_run.return_value = MagicMock(stdout="[]", returncode=0)

            results = search_helm_chart("nonexistent", "chart")

            assert results == []

    def test_search_chart_helm_not_found(self):
        """Test when helm is not installed."""
        with patch("subprocess.run", side_effect=FileNotFoundError()):
            with pytest.raises(CliToolNotFoundError):
                search_helm_chart("grafana", "grafana")


class TestGetLatestChartVersion:
    """Test getting latest chart version."""

    def test_get_latest_version_success(self):
        """Test successful retrieval of latest version."""
        mock_results = [{"name": "grafana/grafana", "version": "10.2.0"}]

        with patch("subprocess.run") as mock_run:
            mock_run.return_value = MagicMock(
                stdout=json.dumps(mock_results), returncode=0
            )

            version = get_latest_chart_version("grafana", "grafana")

            assert version == "10.2.0"

    def test_get_latest_version_chart_not_found(self):
        """Test when chart is not found."""
        with patch("subprocess.run") as mock_run:
            mock_run.return_value = MagicMock(stdout="[]", returncode=0)

            version = get_latest_chart_version("nonexistent", "chart")

            assert version is None


class TestGetAllChartVersions:
    """Test getting all available chart versions."""

    def test_get_all_versions_success(self):
        """Test successful retrieval of all versions."""
        mock_results = [
            {"name": "grafana/grafana", "version": "10.2.0"},
            {"name": "grafana/grafana", "version": "10.1.2"},
            {"name": "grafana/grafana", "version": "10.0.0"},
        ]

        with patch("subprocess.run") as mock_run:
            mock_run.return_value = MagicMock(
                stdout=json.dumps(mock_results), returncode=0
            )

            versions = get_all_chart_versions("grafana", "grafana")

            assert len(versions) == 3
            assert "10.2.0" in versions
            assert "10.1.2" in versions
            assert "10.0.0" in versions

    def test_get_all_versions_empty(self):
        """Test when no versions are found."""
        with patch("subprocess.run") as mock_run:
            mock_run.return_value = MagicMock(stdout="[]", returncode=0)

            versions = get_all_chart_versions("nonexistent", "chart")

            assert versions == []
