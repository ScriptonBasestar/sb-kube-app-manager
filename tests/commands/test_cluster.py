"""Tests for cluster status command."""

import json
from datetime import datetime, timedelta, timezone
from pathlib import Path
from unittest.mock import MagicMock, patch

import pytest
import yaml

from sbkube.utils.cluster_cache import ClusterCache
from sbkube.utils.cluster_status import ClusterStatusCollector


class TestClusterCache:
    """Test cases for ClusterCache."""

    def test_cache_save_and_load(self, tmp_path):
        """Test saving and loading cache data."""
        cache_dir = tmp_path / ".sbkube" / "cluster_status"
        cache = ClusterCache(cache_dir, context="default", cluster="test-cluster")

        # Save test data
        test_data = {
            "cluster_info": {"api_server": "https://127.0.0.1:6443", "version": "v1.27.3"},
            "nodes": [{"name": "node1", "status": "Ready"}],
            "namespaces": ["default", "kube-system"],
            "helm_releases": [],
        }
        cache.save(test_data)

        # Verify file exists
        assert cache.cache_file.exists()

        # Load and verify
        loaded_data = cache.load()
        assert loaded_data is not None
        assert loaded_data["context"] == "default"
        assert loaded_data["cluster_name"] == "test-cluster"
        assert loaded_data["cluster_info"] == test_data["cluster_info"]
        assert loaded_data["nodes"] == test_data["nodes"]

    def test_cache_ttl_validation(self, tmp_path):
        """Test TTL-based cache validation."""
        cache_dir = tmp_path / ".sbkube" / "cluster_status"
        cache = ClusterCache(cache_dir, context="default", cluster="test-cluster")

        # Save with default TTL (300 seconds)
        test_data = {"cluster_info": {}, "nodes": [], "namespaces": [], "helm_releases": []}
        cache.save(test_data, ttl_seconds=300)

        # Should be valid immediately
        assert cache.is_valid()

        # Manually expire cache by modifying timestamp
        data = cache.load()
        old_time = datetime.now(timezone.utc) - timedelta(seconds=400)
        data["timestamp"] = old_time.isoformat()

        # Write back expired data
        with cache.cache_file.open("w") as f:
            yaml.safe_dump(data, f)

        # Should be invalid now
        assert not cache.is_valid()

    def test_cache_with_unknown_cluster(self, tmp_path):
        """Test cache handling when cluster name is None."""
        cache_dir = tmp_path / ".sbkube" / "cluster_status"
        cache = ClusterCache(cache_dir, context="default", cluster=None)

        # Should use "unknown" as cluster name
        assert "unknown" in cache.cache_file.name
        assert cache.cache_file.name == "default_unknown.yaml"

    def test_cache_age_and_remaining_ttl(self, tmp_path):
        """Test cache age and remaining TTL calculations."""
        cache_dir = tmp_path / ".sbkube" / "cluster_status"
        cache = ClusterCache(cache_dir, context="default", cluster="test-cluster")

        # Save cache
        test_data = {"cluster_info": {}, "nodes": [], "namespaces": [], "helm_releases": []}
        cache.save(test_data, ttl_seconds=300)

        # Age should be close to 0
        age = cache.get_age_seconds()
        assert age is not None
        assert age < 5  # Within 5 seconds

        # Remaining TTL should be close to 300
        remaining = cache.get_remaining_ttl()
        assert remaining is not None
        assert 295 < remaining <= 300

    def test_cache_delete(self, tmp_path):
        """Test cache file deletion."""
        cache_dir = tmp_path / ".sbkube" / "cluster_status"
        cache = ClusterCache(cache_dir, context="default", cluster="test-cluster")

        # Create cache
        test_data = {"cluster_info": {}, "nodes": [], "namespaces": [], "helm_releases": []}
        cache.save(test_data)
        assert cache.exists()

        # Delete cache
        cache.delete()
        assert not cache.exists()


class TestClusterStatusCollector:
    """Test cases for ClusterStatusCollector."""

    @patch("subprocess.run")
    def test_collect_cluster_info(self, mock_run):
        """Test cluster info collection."""
        # Mock kubectl cluster-info
        mock_run.return_value = MagicMock(
            returncode=0,
            stdout="Kubernetes control plane is running at https://127.0.0.1:6443\n",
            stderr="",
        )

        collector = ClusterStatusCollector(kubeconfig=None, context=None)

        with patch.object(collector, "_run_kubectl") as mock_kubectl:
            # Mock cluster-info
            mock_kubectl.side_effect = [
                MagicMock(stdout="Kubernetes control plane is running at https://127.0.0.1:6443\n"),
                MagicMock(
                    stdout=json.dumps({"serverVersion": {"gitVersion": "v1.27.3"}})
                ),
            ]

            info = collector._collect_cluster_info()

            assert "api_server" in info
            assert info["api_server"] == "https://127.0.0.1:6443"
            assert "version" in info
            assert info["version"] == "v1.27.3"

    @patch("subprocess.run")
    def test_collect_nodes(self, mock_run):
        """Test node collection."""
        # Mock kubectl get nodes response
        nodes_response = {
            "items": [
                {
                    "metadata": {
                        "name": "node1",
                        "labels": {"node-role.kubernetes.io/control-plane": ""},
                    },
                    "status": {
                        "conditions": [{"type": "Ready", "status": "True"}],
                        "nodeInfo": {"kubeletVersion": "v1.27.3"},
                    },
                }
            ]
        }

        collector = ClusterStatusCollector(kubeconfig=None, context=None)

        with patch.object(collector, "_run_kubectl") as mock_kubectl:
            mock_kubectl.return_value = MagicMock(stdout=json.dumps(nodes_response))

            nodes = collector._collect_nodes()

            assert len(nodes) == 1
            assert nodes[0]["name"] == "node1"
            assert nodes[0]["status"] == "Ready"
            assert "control-plane" in nodes[0]["roles"]
            assert nodes[0]["version"] == "v1.27.3"

    @patch("subprocess.run")
    def test_collect_namespaces(self, mock_run):
        """Test namespace collection."""
        # Mock kubectl get namespaces response
        ns_response = {
            "items": [
                {"metadata": {"name": "default"}},
                {"metadata": {"name": "kube-system"}},
                {"metadata": {"name": "my-app"}},
            ]
        }

        collector = ClusterStatusCollector(kubeconfig=None, context=None)

        with patch.object(collector, "_run_kubectl") as mock_kubectl:
            mock_kubectl.return_value = MagicMock(stdout=json.dumps(ns_response))

            namespaces = collector._collect_namespaces()

            assert len(namespaces) == 3
            assert "default" in namespaces
            assert "kube-system" in namespaces
            assert "my-app" in namespaces

    @patch("subprocess.run")
    def test_collect_helm_releases(self, mock_run):
        """Test Helm release collection."""
        # Mock helm list response
        releases_response = [
            {
                "name": "redis",
                "namespace": "data",
                "status": "deployed",
                "chart": "redis-18.0.0",
                "app_version": "7.2.0",
                "revision": 1,
            },
            {
                "name": "postgres",
                "namespace": "database",
                "status": "deployed",
                "chart": "postgresql-12.1.0",
                "app_version": "15.2.0",
                "revision": 2,
            },
        ]

        collector = ClusterStatusCollector(kubeconfig=None, context=None)

        with patch.object(collector, "_run_helm") as mock_helm:
            mock_helm.return_value = MagicMock(stdout=json.dumps(releases_response))

            releases = collector._collect_helm_releases()

            assert len(releases) == 2
            assert releases[0]["name"] == "redis"
            assert releases[0]["namespace"] == "data"
            assert releases[0]["status"] == "deployed"
            assert releases[1]["name"] == "postgres"

    @patch("subprocess.run")
    def test_collect_all_with_partial_failure(self, mock_run):
        """Test collect_all with partial failures (non-blocking)."""
        collector = ClusterStatusCollector(kubeconfig=None, context=None)

        with patch.object(collector, "_collect_cluster_info") as mock_info, \
             patch.object(collector, "_collect_nodes") as mock_nodes, \
             patch.object(collector, "_collect_namespaces") as mock_namespaces, \
             patch.object(collector, "_collect_helm_releases") as mock_helm:

            # Simulate helm failure
            mock_info.return_value = {"api_server": "https://test", "version": "v1.27.3"}
            mock_nodes.return_value = [{"name": "node1", "status": "Ready"}]
            mock_namespaces.return_value = ["default"]
            mock_helm.side_effect = Exception("Helm command failed")

            result = collector.collect_all()

            # Should succeed with partial data
            assert "cluster_info" in result
            assert "nodes" in result
            assert "namespaces" in result
            assert "helm_releases" in result
            assert result["helm_releases"] == []  # Empty due to failure


class TestClusterCommand:
    """Integration tests for cluster status command."""

    def test_cache_file_naming(self, tmp_path):
        """Test cache file naming convention."""
        cache_dir = tmp_path / ".sbkube" / "cluster_status"
        cache = ClusterCache(cache_dir, context="my-context", cluster="my-cluster")

        expected_filename = "my-context_my-cluster.yaml"
        assert cache.cache_file.name == expected_filename

    def test_yaml_format_readability(self, tmp_path):
        """Test that cache YAML is human-readable."""
        cache_dir = tmp_path / ".sbkube" / "cluster_status"
        cache = ClusterCache(cache_dir, context="default", cluster="test")

        test_data = {
            "cluster_info": {"api_server": "https://127.0.0.1:6443"},
            "nodes": [{"name": "node1", "status": "Ready"}],
            "namespaces": ["default", "kube-system"],
            "helm_releases": [],
        }
        cache.save(test_data)

        # Read raw YAML
        with cache.cache_file.open("r") as f:
            content = f.read()

        # Should be readable YAML (not flow style)
        assert "cluster_info:" in content
        assert "nodes:" in content
        assert "api_server: https://127.0.0.1:6443" in content

    def test_atomic_write(self, tmp_path):
        """Test atomic write (temp file + rename)."""
        cache_dir = tmp_path / ".sbkube" / "cluster_status"
        cache = ClusterCache(cache_dir, context="default", cluster="test")

        test_data = {"cluster_info": {}, "nodes": [], "namespaces": [], "helm_releases": []}
        cache.save(test_data)

        # Temp file should not exist after save
        temp_file = cache.cache_file.with_suffix(".tmp")
        assert not temp_file.exists()

        # Only final file should exist
        assert cache.cache_file.exists()
