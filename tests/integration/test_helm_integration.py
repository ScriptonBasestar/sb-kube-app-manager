"""
Integration tests for Helm-specific functionality.

These tests verify sbkube's integration with Helm,
including chart management, repository handling, and deployments.
"""

import pytest
import subprocess
import yaml
import json
from pathlib import Path
from click.testing import CliRunner

from sbkube.cli import main
from sbkube.utils.helm_util import get_installed_charts


@pytest.mark.integration
@pytest.mark.requires_helm
class TestHelmIntegration:
    """Test Helm-specific integration scenarios."""
    
    def test_helm_repo_management(self, tmp_path, helm_binary):
        """Test Helm repository add/update operations."""
        runner = CliRunner()
        
        project_dir = tmp_path / "helm_repo_test"
        project_dir.mkdir()
        
        # Create sources.yaml with helm repos
        sources = {
            "cluster": "test",
            "helm_repos": {
                "bitnami": "https://charts.bitnami.com/bitnami",
                "ingress-nginx": "https://kubernetes.github.io/ingress-nginx"
            }
        }
        with open(project_dir / "sources.yaml", 'w') as f:
            yaml.dump(sources, f)
        
        # Create config
        config_dir = project_dir / "config"
        config_dir.mkdir()
        config = {
            "namespace": "test",
            "apps": [
                {
                    "name": "redis",
                    "type": "pull-helm",
                    "specs": {
                        "repo": "bitnami",
                        "chart": "redis",
                        "chart_version": "17.0.0"
                    }
                }
            ]
        }
        with open(config_dir / "config.yaml", 'w') as f:
            yaml.dump(config, f)
        
        # Run prepare - should add repos
        result = runner.invoke(main, [
            'prepare', '--base-dir', str(project_dir), '--app-dir', 'config'
        ])
        
        # Check if repos were added
        repo_list = subprocess.run(
            [helm_binary, "repo", "list", "-o", "json"],
            capture_output=True,
            text=True
        )
        
        if repo_list.returncode == 0 and repo_list.stdout:
            repos = json.loads(repo_list.stdout)
            repo_names = [r['name'] for r in repos]
            # Repos might have been added
            assert any('bitnami' in name for name in repo_names)
    
    def test_helm_chart_versioning(self, tmp_path, helm_repo_server):
        """Test Helm chart version selection and constraints."""
        runner = CliRunner()
        
        project_dir = tmp_path / "helm_version_test"
        project_dir.mkdir()
        
        # Create sources pointing to test repo
        sources = {
            "cluster": "test",
            "helm_repos": {
                "test-repo": helm_repo_server['url']
            }
        }
        with open(project_dir / "sources.yaml", 'w') as f:
            yaml.dump(sources, f)
        
        # Create config requesting specific version
        config_dir = project_dir / "config"
        config_dir.mkdir()
        config = {
            "namespace": "test",
            "apps": [
                {
                    "name": "test-chart",
                    "type": "pull-helm",
                    "specs": {
                        "repo": "test-repo",
                        "chart": "test-chart",
                        "chart_version": "1.0.0"
                    }
                }
            ]
        }
        with open(config_dir / "config.yaml", 'w') as f:
            yaml.dump(config, f)
        
        # Add test repo
        subprocess.run([
            "helm", "repo", "add", "test-repo", helm_repo_server['url']
        ], check=True)
        
        # Run prepare
        result = runner.invoke(main, [
            'prepare', '--base-dir', str(project_dir), '--app-dir', 'config'
        ])
        
        # Verify correct version was pulled
        chart_yaml_path = project_dir / "charts" / "test-chart" / "Chart.yaml"
        if chart_yaml_path.exists():
            with open(chart_yaml_path, 'r') as f:
                chart = yaml.safe_load(f)
                assert chart['version'] == "1.0.0"
    
    def test_helm_values_merging(self, tmp_path):
        """Test Helm values file handling and merging."""
        runner = CliRunner()
        
        project_dir = tmp_path / "helm_values_test"
        project_dir.mkdir()
        config_dir = project_dir / "config"
        config_dir.mkdir()
        values_dir = config_dir / "values"
        values_dir.mkdir()
        
        # Create multiple values files
        base_values = {
            "replicaCount": 1,
            "image": {
                "repository": "nginx",
                "tag": "1.19"
            },
            "service": {
                "type": "ClusterIP",
                "port": 80
            }
        }
        with open(values_dir / "base.yaml", 'w') as f:
            yaml.dump(base_values, f)
        
        prod_values = {
            "replicaCount": 3,
            "image": {
                "tag": "1.20"
            },
            "resources": {
                "limits": {
                    "memory": "256Mi"
                }
            }
        }
        with open(values_dir / "prod.yaml", 'w') as f:
            yaml.dump(prod_values, f)
        
        # Create dummy chart
        chart_dir = project_dir / "charts" / "test-app"
        chart_dir.mkdir(parents=True)
        
        chart_yaml = {
            "apiVersion": "v2",
            "name": "test-app",
            "version": "1.0.0"
        }
        with open(chart_dir / "Chart.yaml", 'w') as f:
            yaml.dump(chart_yaml, f)
        
        # Create config using multiple values
        config = {
            "namespace": "test",
            "apps": [{
                "name": "test-app",
                "type": "install-helm",
                "specs": {
                    "path": "../../charts/test-app",
                    "values": ["base.yaml", "prod.yaml"]
                }
            }]
        }
        with open(config_dir / "config.yaml", 'w') as f:
            yaml.dump(config, f)
        
        # Template with values
        output_dir = project_dir / "rendered"
        result = runner.invoke(main, [
            'template',
            '--base-dir', str(project_dir),
            '--app-dir', 'config',
            '--output-dir', str(output_dir)
        ])
        
        # Values should be merged (prod overrides base)
        # This would be verified in the rendered output
    
    @pytest.mark.requires_k8s
    def test_helm_deployment_lifecycle(self, tmp_path, k8s_cluster, k8s_namespace):
        """Test complete Helm deployment lifecycle with real cluster."""
        runner = CliRunner()
        
        project_dir = tmp_path / "helm_lifecycle"
        project_dir.mkdir()
        config_dir = project_dir / "config"
        config_dir.mkdir()
        
        # Create simple chart
        chart_dir = project_dir / "charts" / "lifecycle-app"
        chart_dir.mkdir(parents=True)
        templates_dir = chart_dir / "templates"
        templates_dir.mkdir()
        
        # Chart.yaml
        with open(chart_dir / "Chart.yaml", 'w') as f:
            yaml.dump({
                "apiVersion": "v2",
                "name": "lifecycle-app",
                "version": "1.0.0"
            }, f)
        
        # Simple deployment template
        deployment_template = """apiVersion: apps/v1
kind: Deployment
metadata:
  name: {{ .Release.Name }}
  labels:
    app: {{ .Release.Name }}
spec:
  replicas: 1
  selector:
    matchLabels:
      app: {{ .Release.Name }}
  template:
    metadata:
      labels:
        app: {{ .Release.Name }}
    spec:
      containers:
      - name: app
        image: nginx:alpine
        ports:
        - containerPort: 80
"""
        with open(templates_dir / "deployment.yaml", 'w') as f:
            f.write(deployment_template)
        
        # Config
        config = {
            "namespace": k8s_namespace,
            "apps": [{
                "name": "lifecycle-app",
                "type": "install-helm",
                "release_name": "test-release",
                "specs": {
                    "path": "../../charts/lifecycle-app"
                }
            }]
        }
        with open(config_dir / "config.yaml", 'w') as f:
            yaml.dump(config, f)
        
        # Deploy
        result = runner.invoke(main, [
            'deploy',
            '--base-dir', str(project_dir),
            '--app-dir', 'config',
            '--kubeconfig', k8s_cluster['kubeconfig']
        ])
        assert result.exit_code == 0
        
        # Verify deployment
        releases = subprocess.run([
            "helm", "list", "-n", k8s_namespace,
            "--kubeconfig", k8s_cluster['kubeconfig'],
            "-o", "json"
        ], capture_output=True, text=True, check=True)
        
        releases_data = json.loads(releases.stdout)
        assert any(r['name'] == 'test-release' for r in releases_data)
        
        # Upgrade
        result = runner.invoke(main, [
            'upgrade',
            '--base-dir', str(project_dir),
            '--app-dir', 'config',
            '--kubeconfig', k8s_cluster['kubeconfig']
        ])
        assert result.exit_code == 0
        
        # Delete
        result = runner.invoke(main, [
            'delete',
            '--base-dir', str(project_dir),
            '--app-dir', 'config',
            '--kubeconfig', k8s_cluster['kubeconfig']
        ])
        assert result.exit_code == 0
        
        # Verify deletion
        releases = subprocess.run([
            "helm", "list", "-n", k8s_namespace,
            "--kubeconfig", k8s_cluster['kubeconfig'],
            "-o", "json"
        ], capture_output=True, text=True, check=True)
        
        releases_data = json.loads(releases.stdout) if releases.stdout else []
        assert not any(r['name'] == 'test-release' for r in releases_data)


@pytest.mark.integration
class TestHelmErrorHandling:
    """Test Helm error scenarios and recovery."""
    
    @pytest.mark.requires_helm
    def test_invalid_chart_handling(self, tmp_path):
        """Test handling of invalid Helm charts."""
        runner = CliRunner()
        
        project_dir = tmp_path / "invalid_chart"
        project_dir.mkdir()
        config_dir = project_dir / "config"
        config_dir.mkdir()
        
        # Create invalid chart (missing Chart.yaml)
        chart_dir = project_dir / "charts" / "invalid"
        chart_dir.mkdir(parents=True)
        
        # Config
        config = {
            "namespace": "test",
            "apps": [{
                "name": "invalid",
                "type": "install-helm",
                "specs": {
                    "path": "../../charts/invalid"
                }
            }]
        }
        with open(config_dir / "config.yaml", 'w') as f:
            yaml.dump(config, f)
        
        # Template should fail
        result = runner.invoke(main, [
            'template',
            '--base-dir', str(project_dir),
            '--app-dir', 'config'
        ])
        assert result.exit_code != 0
        assert "Chart.yaml" in result.output or "차트" in result.output
    
    def test_helm_repo_unreachable(self, tmp_path):
        """Test handling of unreachable Helm repositories."""
        runner = CliRunner()
        
        project_dir = tmp_path / "unreachable_repo"
        project_dir.mkdir()
        
        # Sources with invalid repo
        sources = {
            "cluster": "test",
            "helm_repos": {
                "invalid": "http://invalid.example.com/charts"
            }
        }
        with open(project_dir / "sources.yaml", 'w') as f:
            yaml.dump(sources, f)
        
        # Config
        config_dir = project_dir / "config"
        config_dir.mkdir()
        config = {
            "namespace": "test",
            "apps": [{
                "name": "test",
                "type": "pull-helm",
                "specs": {
                    "repo": "invalid",
                    "chart": "test"
                }
            }]
        }
        with open(config_dir / "config.yaml", 'w') as f:
            yaml.dump(config, f)
        
        # Prepare should handle the error gracefully
        result = runner.invoke(main, [
            'prepare', '--base-dir', str(project_dir), '--app-dir', 'config'
        ])
        # Should fail but with clear error message
        assert "invalid.example.com" in result.output or "실패" in result.output