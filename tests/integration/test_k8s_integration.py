"""
Integration tests for Kubernetes-specific functionality.

These tests verify sbkube's integration with Kubernetes,
including resource management, namespace handling, and deployments.
"""

import json
import subprocess
from pathlib import Path

import pytest
import yaml
from click.testing import CliRunner

from sbkube.cli import main


@pytest.mark.integration
@pytest.mark.requires_k8s
class TestKubernetesIntegration:
    """Test Kubernetes-specific integration scenarios."""

    def test_namespace_management(self, k8s_cluster, k8s_namespace):
        """Test namespace creation and resource deployment."""
        runner = CliRunner()

        # Create project
        with runner.isolated_filesystem() as tmp_dir:
            project_dir = Path(tmp_dir) / "k8s_namespace_test"
            project_dir.mkdir()
            config_dir = project_dir / "config"
            config_dir.mkdir()

            # Create ConfigMap manifest
            configmap = {
                "apiVersion": "v1",
                "kind": "ConfigMap",
                "metadata": {"name": "test-config", "namespace": k8s_namespace},
                "data": {"key1": "value1", "key2": "value2"},
            }
            manifest_path = config_dir / "configmap.yaml"
            with open(manifest_path, "w") as f:
                yaml.dump(configmap, f)

            # Create config
            config = {
                "namespace": k8s_namespace,
                "apps": [
                    {
                        "name": "test-configmap",
                        "type": "install-yaml",
                        "specs": {
                            "actions": [{"type": "apply", "path": "configmap.yaml"}]
                        },
                    }
                ],
            }
            with open(config_dir / "config.yaml", "w") as f:
                yaml.dump(config, f)

            # Deploy
            result = runner.invoke(
                main,
                [
                    "deploy",
                    "--base-dir",
                    str(project_dir),
                    "--app-dir",
                    "config",
                    "--kubeconfig",
                    k8s_cluster["kubeconfig"],
                ],
            )
            assert result.exit_code == 0

            # Verify ConfigMap exists
            cm = subprocess.run(
                [
                    "kubectl",
                    "get",
                    "configmap",
                    "test-config",
                    "-n",
                    k8s_namespace,
                    "--kubeconfig",
                    k8s_cluster["kubeconfig"],
                    "-o",
                    "json",
                ],
                capture_output=True,
                text=True,
                check=True,
            )

            cm_data = json.loads(cm.stdout)
            assert cm_data["data"]["key1"] == "value1"
            assert cm_data["data"]["key2"] == "value2"

    def test_multi_resource_deployment(self, k8s_cluster, k8s_namespace):
        """Test deploying multiple Kubernetes resources."""
        runner = CliRunner()

        with runner.isolated_filesystem() as tmp_dir:
            project_dir = Path(tmp_dir) / "multi_resource"
            project_dir.mkdir()
            config_dir = project_dir / "config"
            config_dir.mkdir()
            manifests_dir = config_dir / "manifests"
            manifests_dir.mkdir()

            # Create multiple resources
            resources = [
                {
                    "apiVersion": "v1",
                    "kind": "ConfigMap",
                    "metadata": {"name": "app-config"},
                    "data": {"config": "value"},
                },
                {
                    "apiVersion": "v1",
                    "kind": "Secret",
                    "metadata": {"name": "app-secret"},
                    "type": "Opaque",
                    "stringData": {"password": "secret123"},
                },
                {
                    "apiVersion": "v1",
                    "kind": "Service",
                    "metadata": {"name": "app-service"},
                    "spec": {
                        "selector": {"app": "test"},
                        "ports": [{"port": 80, "targetPort": 80}],
                    },
                },
            ]

            # Write resources to single file
            all_manifests_path = manifests_dir / "all.yaml"
            with open(all_manifests_path, "w") as f:
                yaml.dump_all(resources, f)

            # Create config
            config = {
                "namespace": k8s_namespace,
                "apps": [
                    {
                        "name": "multi-resource-app",
                        "type": "install-yaml",
                        "specs": {
                            "actions": [{"type": "apply", "path": "manifests/all.yaml"}]
                        },
                    }
                ],
            }
            with open(config_dir / "config.yaml", "w") as f:
                yaml.dump(config, f)

            # Deploy
            result = runner.invoke(
                main,
                [
                    "deploy",
                    "--base-dir",
                    str(project_dir),
                    "--app-dir",
                    "config",
                    "--kubeconfig",
                    k8s_cluster["kubeconfig"],
                ],
            )
            assert result.exit_code == 0

            # Verify all resources exist
            for resource in resources:
                kind = resource["kind"].lower()
                name = resource["metadata"]["name"]

                check = subprocess.run(
                    [
                        "kubectl",
                        "get",
                        kind,
                        name,
                        "-n",
                        k8s_namespace,
                        "--kubeconfig",
                        k8s_cluster["kubeconfig"],
                    ],
                    capture_output=True,
                )
                assert check.returncode == 0, f"{kind}/{name} not found"

    def test_resource_updates(self, k8s_cluster, k8s_namespace):
        """Test updating existing Kubernetes resources."""
        runner = CliRunner()

        with runner.isolated_filesystem() as tmp_dir:
            project_dir = Path(tmp_dir) / "resource_update"
            project_dir.mkdir()
            config_dir = project_dir / "config"
            config_dir.mkdir()

            # Initial ConfigMap
            configmap_v1 = {
                "apiVersion": "v1",
                "kind": "ConfigMap",
                "metadata": {"name": "update-test"},
                "data": {"version": "1", "key": "initial"},
            }

            manifest_path = config_dir / "configmap.yaml"
            with open(manifest_path, "w") as f:
                yaml.dump(configmap_v1, f)

            # Config
            config = {
                "namespace": k8s_namespace,
                "apps": [
                    {
                        "name": "update-app",
                        "type": "install-yaml",
                        "specs": {
                            "actions": [{"type": "apply", "path": "configmap.yaml"}]
                        },
                    }
                ],
            }
            with open(config_dir / "config.yaml", "w") as f:
                yaml.dump(config, f)

            # Initial deployment
            result = runner.invoke(
                main,
                [
                    "deploy",
                    "--base-dir",
                    str(project_dir),
                    "--app-dir",
                    "config",
                    "--kubeconfig",
                    k8s_cluster["kubeconfig"],
                ],
            )
            assert result.exit_code == 0

            # Update ConfigMap
            configmap_v2 = {
                "apiVersion": "v1",
                "kind": "ConfigMap",
                "metadata": {"name": "update-test"},
                "data": {"version": "2", "key": "updated", "new-key": "new-value"},
            }
            with open(manifest_path, "w") as f:
                yaml.dump(configmap_v2, f)

            # Deploy update
            result = runner.invoke(
                main,
                [
                    "deploy",
                    "--base-dir",
                    str(project_dir),
                    "--app-dir",
                    "config",
                    "--kubeconfig",
                    k8s_cluster["kubeconfig"],
                ],
            )
            assert result.exit_code == 0

            # Verify update
            cm = subprocess.run(
                [
                    "kubectl",
                    "get",
                    "configmap",
                    "update-test",
                    "-n",
                    k8s_namespace,
                    "--kubeconfig",
                    k8s_cluster["kubeconfig"],
                    "-o",
                    "json",
                ],
                capture_output=True,
                text=True,
                check=True,
            )

            cm_data = json.loads(cm.stdout)
            assert cm_data["data"]["version"] == "2"
            assert cm_data["data"]["key"] == "updated"
            assert cm_data["data"]["new-key"] == "new-value"

    def test_deployment_rollout(self, k8s_cluster, k8s_namespace):
        """Test Deployment rollout and readiness."""
        runner = CliRunner()

        with runner.isolated_filesystem() as tmp_dir:
            project_dir = Path(tmp_dir) / "rollout_test"
            project_dir.mkdir()
            config_dir = project_dir / "config"
            config_dir.mkdir()

            # Create Deployment
            deployment = {
                "apiVersion": "apps/v1",
                "kind": "Deployment",
                "metadata": {"name": "rollout-test"},
                "spec": {
                    "replicas": 2,
                    "selector": {"matchLabels": {"app": "rollout-test"}},
                    "template": {
                        "metadata": {"labels": {"app": "rollout-test"}},
                        "spec": {
                            "containers": [
                                {
                                    "name": "nginx",
                                    "image": "nginx:alpine",
                                    "ports": [{"containerPort": 80}],
                                    "readinessProbe": {
                                        "httpGet": {"path": "/", "port": 80},
                                        "initialDelaySeconds": 2,
                                        "periodSeconds": 5,
                                    },
                                }
                            ]
                        },
                    },
                },
            }

            manifest_path = config_dir / "deployment.yaml"
            with open(manifest_path, "w") as f:
                yaml.dump(deployment, f)

            # Config
            config = {
                "namespace": k8s_namespace,
                "apps": [
                    {
                        "name": "rollout-app",
                        "type": "install-yaml",
                        "specs": {
                            "actions": [{"type": "apply", "path": "deployment.yaml"}]
                        },
                    }
                ],
            }
            with open(config_dir / "config.yaml", "w") as f:
                yaml.dump(config, f)

            # Deploy
            result = runner.invoke(
                main,
                [
                    "deploy",
                    "--base-dir",
                    str(project_dir),
                    "--app-dir",
                    "config",
                    "--kubeconfig",
                    k8s_cluster["kubeconfig"],
                ],
            )
            assert result.exit_code == 0

            # Wait for rollout
            rollout_status = subprocess.run(
                [
                    "kubectl",
                    "rollout",
                    "status",
                    "deployment/rollout-test",
                    "-n",
                    k8s_namespace,
                    "--kubeconfig",
                    k8s_cluster["kubeconfig"],
                    "--timeout=30s",
                ],
                capture_output=True,
                text=True,
            )

            assert (
                rollout_status.returncode == 0
            ), f"Rollout failed: {rollout_status.stderr}"

            # Verify pods are running
            pods = subprocess.run(
                [
                    "kubectl",
                    "get",
                    "pods",
                    "-n",
                    k8s_namespace,
                    "--kubeconfig",
                    k8s_cluster["kubeconfig"],
                    "-l",
                    "app=rollout-test",
                    "-o",
                    "json",
                ],
                capture_output=True,
                text=True,
                check=True,
            )

            pods_data = json.loads(pods.stdout)
            assert len(pods_data["items"]) == 2

            for pod in pods_data["items"]:
                phase = pod["status"]["phase"]
                assert phase == "Running", f"Pod not running: {phase}"


@pytest.mark.integration
@pytest.mark.requires_k8s
class TestKubernetesErrorScenarios:
    """Test Kubernetes error handling scenarios."""

    def test_invalid_manifest(self, k8s_cluster, k8s_namespace):
        """Test handling of invalid Kubernetes manifests."""
        runner = CliRunner()

        with runner.isolated_filesystem() as tmp_dir:
            project_dir = Path(tmp_dir) / "invalid_manifest"
            project_dir.mkdir()
            config_dir = project_dir / "config"
            config_dir.mkdir()

            # Invalid manifest (missing required fields)
            invalid_manifest = {
                "apiVersion": "v1",
                "kind": "Service",
                "metadata": {"name": "invalid-service"},
                "spec": {
                    # Missing required selector
                    "ports": [{"port": 80}]
                },
            }

            manifest_path = config_dir / "invalid.yaml"
            with open(manifest_path, "w") as f:
                yaml.dump(invalid_manifest, f)

            # Config
            config = {
                "namespace": k8s_namespace,
                "apps": [
                    {
                        "name": "invalid-app",
                        "type": "install-yaml",
                        "specs": {
                            "actions": [{"type": "apply", "path": "invalid.yaml"}]
                        },
                    }
                ],
            }
            with open(config_dir / "config.yaml", "w") as f:
                yaml.dump(config, f)

            # Deploy should fail
            result = runner.invoke(
                main,
                [
                    "deploy",
                    "--base-dir",
                    str(project_dir),
                    "--app-dir",
                    "config",
                    "--kubeconfig",
                    k8s_cluster["kubeconfig"],
                ],
            )
            assert result.exit_code != 0
            assert "invalid-app" in result.output

    def test_resource_conflicts(self, k8s_cluster, k8s_namespace):
        """Test handling of resource naming conflicts."""
        runner = CliRunner()

        with runner.isolated_filesystem() as tmp_dir:
            project_dir = Path(tmp_dir) / "conflict_test"
            project_dir.mkdir()
            config_dir = project_dir / "config"
            config_dir.mkdir()

            # Create ConfigMap
            configmap = {
                "apiVersion": "v1",
                "kind": "ConfigMap",
                "metadata": {"name": "conflict-test"},
                "data": {"key": "value"},
            }

            manifest_path = config_dir / "configmap.yaml"
            with open(manifest_path, "w") as f:
                yaml.dump(configmap, f)

            # Config with create action (will fail if exists)
            config = {
                "namespace": k8s_namespace,
                "apps": [
                    {
                        "name": "conflict-app",
                        "type": "install-yaml",
                        "specs": {
                            "actions": [
                                {
                                    "type": "create",  # create fails if exists
                                    "path": "configmap.yaml",
                                }
                            ]
                        },
                    }
                ],
            }
            with open(config_dir / "config.yaml", "w") as f:
                yaml.dump(config, f)

            # First deployment should succeed
            result = runner.invoke(
                main,
                [
                    "deploy",
                    "--base-dir",
                    str(project_dir),
                    "--app-dir",
                    "config",
                    "--kubeconfig",
                    k8s_cluster["kubeconfig"],
                ],
            )
            assert result.exit_code == 0

            # Second deployment should fail due to conflict
            result = runner.invoke(
                main,
                [
                    "deploy",
                    "--base-dir",
                    str(project_dir),
                    "--app-dir",
                    "config",
                    "--kubeconfig",
                    k8s_cluster["kubeconfig"],
                ],
            )
            assert result.exit_code != 0
            assert "already exists" in result.output or "이미 존재" in result.output
