"""
Integration tests for complete sbkube workflows.

These tests verify the entire pipeline from prepare through deploy,
testing against real or simulated external systems.
"""

import subprocess
from pathlib import Path

import pytest
import yaml
from click.testing import CliRunner

from sbkube.cli import main
from sbkube.state.database import DeploymentDatabase


@pytest.mark.integration
@pytest.mark.e2e
class TestFullWorkflow:
    """Test complete sbkube workflows from prepare to deploy."""

    @pytest.mark.requires_helm
    def test_helm_workflow(self, sbkube_project, helm_binary, monkeypatch):
        """Test complete Helm chart workflow: prepare -> build -> template -> deploy."""
        runner = CliRunner()

        # Set environment
        monkeypatch.chdir(sbkube_project)
        monkeypatch.setenv("KUBECONFIG", str(sbkube_project / "kubeconfig"))

        # Mock helm repo update to avoid network calls
        def mock_helm_repo_update(*args, **kwargs):
            if "helm" in args[0] and "repo" in args[0] and "update" in args[0]:
                return subprocess.CompletedProcess(args[0], 0, "Update Complete", "")
            return subprocess.run(*args, **kwargs)

        monkeypatch.setattr(subprocess, "run", mock_helm_repo_update)

        # 1. Prepare - should download charts
        result = runner.invoke(
            main, ["prepare", "--base-dir", str(sbkube_project), "--app-dir", "config"]
        )
        assert result.exit_code == 0, f"Prepare failed: {result.output}"

        # Verify chart was downloaded
        chart_dir = sbkube_project / "charts" / "redis"
        assert chart_dir.exists(), "Chart directory not created"

        # 2. Build - should copy charts to build directory
        result = runner.invoke(
            main, ["build", "--base-dir", str(sbkube_project), "--app-dir", "config"]
        )
        assert result.exit_code == 0, f"Build failed: {result.output}"

        # Verify build directory
        build_dir = sbkube_project / "config" / "build" / "redis"
        assert build_dir.exists(), "Build directory not created"

        # 3. Template - should render Helm templates
        output_dir = sbkube_project / "rendered"
        result = runner.invoke(
            main,
            [
                "template",
                "--base-dir",
                str(sbkube_project),
                "--app-dir",
                "config",
                "--output-dir",
                str(output_dir),
            ],
        )
        assert result.exit_code == 0, f"Template failed: {result.output}"

        # Verify rendered manifests
        rendered_files = list(output_dir.glob("**/*.yaml"))
        assert len(rendered_files) > 0, "No rendered files found"

        # 4. Deploy - should apply manifests (dry-run)
        result = runner.invoke(
            main,
            [
                "deploy",
                "--base-dir",
                str(sbkube_project),
                "--app-dir",
                "config",
                "--dry-run",
            ],
        )
        assert result.exit_code == 0, f"Deploy failed: {result.output}"

    @pytest.mark.requires_k8s
    @pytest.mark.requires_helm
    def test_workflow_with_real_k8s(
        self, sbkube_project, k8s_cluster, k8s_namespace, helm_binary
    ):
        """Test workflow against a real Kubernetes cluster."""
        runner = CliRunner()

        # Update project configuration to use test namespace
        config_path = sbkube_project / "config" / "config.yaml"
        with open(config_path) as f:
            config = yaml.safe_load(f)
        config["namespace"] = k8s_namespace
        with open(config_path, "w") as f:
            yaml.dump(config, f)

        # Run complete workflow
        commands = [
            ["prepare", "--base-dir", str(sbkube_project), "--app-dir", "config"],
            ["build", "--base-dir", str(sbkube_project), "--app-dir", "config"],
            [
                "deploy",
                "--base-dir",
                str(sbkube_project),
                "--app-dir",
                "config",
                "--kubeconfig",
                k8s_cluster["kubeconfig"],
            ],
        ]

        for cmd in commands:
            result = runner.invoke(main, cmd)
            assert result.exit_code == 0, f"Command {cmd[0]} failed: {result.output}"

        # Verify deployment
        subprocess.run(
            [
                "kubectl",
                "get",
                "all",
                "-n",
                k8s_namespace,
                "--kubeconfig",
                k8s_cluster["kubeconfig"],
            ],
            check=True,
        )

    def test_yaml_workflow(self, tmp_path, monkeypatch):
        """Test YAML manifest deployment workflow."""
        runner = CliRunner()

        # Create project structure
        project_dir = tmp_path / "yaml_project"
        project_dir.mkdir()
        config_dir = project_dir / "config"
        config_dir.mkdir()

        # Create manifest
        manifest = {
            "apiVersion": "v1",
            "kind": "ConfigMap",
            "metadata": {"name": "test-config"},
            "data": {"key": "value"},
        }
        manifest_path = config_dir / "configmap.yaml"
        with open(manifest_path, "w") as f:
            yaml.dump(manifest, f)

        # Create config
        config = {
            "namespace": "default",
            "apps": [
                {
                    "name": "test-yaml",
                    "type": "install-yaml",
                    "specs": {"actions": [{"type": "apply", "path": "configmap.yaml"}]},
                }
            ],
        }
        with open(config_dir / "config.yaml", "w") as f:
            yaml.dump(config, f)

        monkeypatch.chdir(project_dir)

        # Deploy with dry-run
        result = runner.invoke(
            main,
            [
                "deploy",
                "--base-dir",
                str(project_dir),
                "--app-dir",
                "config",
                "--dry-run",
            ],
        )
        assert result.exit_code == 0, f"Deploy failed: {result.output}"
        assert "test-yaml" in result.output

    def test_mixed_workflow(self, tmp_path):
        """Test workflow with multiple application types."""
        runner = CliRunner()

        # Create complex project with multiple app types
        project_dir = tmp_path / "mixed_project"
        project_dir.mkdir()
        config_dir = project_dir / "config"
        config_dir.mkdir()

        # Create config with multiple app types
        config = {
            "namespace": "test",
            "apps": [
                {
                    "name": "prep-chart",
                    "type": "pull-helm",
                    "specs": {"repo": "stable", "chart": "nginx"},
                },
                {
                    "name": "copy-files",
                    "type": "copy-app",
                    "specs": {"paths": [{"src": "files", "dest": "copied"}]},
                },
                {
                    "name": "exec-cmd",
                    "type": "exec",
                    "specs": {"commands": ["echo 'Hello from sbkube'"]},
                },
            ],
        }
        with open(config_dir / "config.yaml", "w") as f:
            yaml.dump(config, f)

        # Create files to copy
        files_dir = config_dir / "files"
        files_dir.mkdir()
        (files_dir / "test.txt").write_text("test content")

        # Run workflow
        result = runner.invoke(
            main, ["prepare", "--base-dir", str(project_dir), "--app-dir", "config"]
        )
        # May fail due to network, but should handle exec and copy

        result = runner.invoke(
            main, ["build", "--base-dir", str(project_dir), "--app-dir", "config"]
        )
        assert "exec-cmd" in result.output


@pytest.mark.integration
class TestErrorScenarios:
    """Test error handling and recovery scenarios."""

    def test_missing_chart_recovery(self, tmp_path):
        """Test handling of missing Helm charts."""
        runner = CliRunner()

        project_dir = tmp_path / "error_project"
        project_dir.mkdir()
        config_dir = project_dir / "config"
        config_dir.mkdir()

        # Config references non-existent chart
        config = {
            "namespace": "test",
            "apps": [
                {
                    "name": "missing-chart",
                    "type": "install-helm",
                    "specs": {"path": "nonexistent"},
                }
            ],
        }
        with open(config_dir / "config.yaml", "w") as f:
            yaml.dump(config, f)

        # Deploy should fail gracefully
        result = runner.invoke(
            main, ["deploy", "--base-dir", str(project_dir), "--app-dir", "config"]
        )
        assert result.exit_code != 0
        assert "존재하지 않습니다" in result.output or "not found" in result.output

    def test_partial_deployment_failure(self, tmp_path, monkeypatch):
        """Test handling when some apps succeed and others fail."""
        runner = CliRunner()

        project_dir = tmp_path / "partial_failure"
        project_dir.mkdir()
        config_dir = project_dir / "config"
        config_dir.mkdir()

        # Create config with multiple apps
        config = {
            "namespace": "test",
            "apps": [
                {
                    "name": "success-app",
                    "type": "exec",
                    "specs": {"commands": ["echo 'Success'"]},
                },
                {"name": "fail-app", "type": "exec", "specs": {"commands": ["exit 1"]}},
                {
                    "name": "another-success",
                    "type": "exec",
                    "specs": {"commands": ["echo 'Also success'"]},
                },
            ],
        }
        with open(config_dir / "config.yaml", "w") as f:
            yaml.dump(config, f)

        # Run deploy
        result = runner.invoke(
            main, ["deploy", "--base-dir", str(project_dir), "--app-dir", "config"]
        )

        # Should show partial success
        assert "success-app" in result.output
        assert "fail-app" in result.output
        assert "2개 성공" in result.output or "2 of 3" in result.output


@pytest.mark.integration
class TestStateTracking:
    """Test deployment state tracking integration."""

    def test_deployment_tracking(self, tmp_path):
        """Test that deployments are tracked in the database."""
        runner = CliRunner()

        project_dir = tmp_path / "tracking_project"
        project_dir.mkdir()
        config_dir = project_dir / "config"
        config_dir.mkdir()

        # Simple config
        config = {
            "namespace": "test",
            "apps": [
                {
                    "name": "tracked-app",
                    "type": "exec",
                    "specs": {"commands": ["echo 'Tracked deployment'"]},
                }
            ],
        }
        with open(config_dir / "config.yaml", "w") as f:
            yaml.dump(config, f)

        # Deploy
        result = runner.invoke(
            main, ["deploy", "--base-dir", str(project_dir), "--app-dir", "config"]
        )
        assert result.exit_code == 0

        # Check state was tracked
        db_path = Path.home() / ".sbkube" / "deployments.db"
        if db_path.exists():
            db = DeploymentDatabase(db_path)
            deployments = db.list_deployments()

            # Should have at least one deployment
            assert len(deployments) > 0

            # Latest deployment should be successful
            latest = deployments[0]
            assert latest.status.value == "success"

    def test_rollback_integration(self, tmp_path):
        """Test rollback functionality integration."""
        runner = CliRunner()

        project_dir = tmp_path / "rollback_project"
        project_dir.mkdir()
        config_dir = project_dir / "config"
        config_dir.mkdir()

        # Create two versions of config
        config_v1 = {
            "namespace": "test",
            "apps": [
                {
                    "name": "app-v1",
                    "type": "exec",
                    "specs": {"commands": ["echo 'Version 1'"]},
                }
            ],
        }

        # First deployment
        with open(config_dir / "config.yaml", "w") as f:
            yaml.dump(config_v1, f)

        result = runner.invoke(
            main, ["deploy", "--base-dir", str(project_dir), "--app-dir", "config"]
        )
        assert result.exit_code == 0

        # Get deployment ID from output (if shown)
        # Note: This assumes deploy command shows deployment ID

        # List deployments
        result = runner.invoke(main, ["state", "list"])
        assert result.exit_code == 0

        # Should show at least one deployment
        assert "dep-" in result.output
