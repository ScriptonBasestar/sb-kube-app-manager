"""
Tests for deployment tracking functionality.
"""

import pytest
import json
from unittest.mock import patch, MagicMock

from sbkube.models.deployment_state import DeploymentStatus, ResourceAction
from sbkube.state.database import DeploymentDatabase
from sbkube.state.tracker import DeploymentTracker


@pytest.mark.unit
class TestDeploymentTracker:
    """Test deployment tracking functionality."""
    
    def test_track_deployment_context(self, temp_db):
        """Test deployment tracking context manager."""
        tracker = DeploymentTracker(temp_db)
        
        config_data = {
            "namespace": "test",
            "apps": [{"name": "app1", "type": "install-helm"}]
        }
        
        with tracker.track_deployment(
            cluster="test-cluster",
            namespace="test-namespace",
            app_config_dir="/test",
            config_file_path="/test/config.yaml",
            config_data=config_data,
            command="deploy"
        ) as deployment_id:
            assert deployment_id is not None
            assert tracker.current_deployment_id == deployment_id
        
        # After context, deployment should be marked as success
        db = DeploymentDatabase(temp_db)
        deployment = db.get_deployment(deployment_id)
        assert deployment.status == DeploymentStatus.SUCCESS
    
    def test_track_deployment_failure(self, temp_db):
        """Test deployment tracking with failure."""
        tracker = DeploymentTracker(temp_db)
        
        config_data = {"namespace": "test", "apps": []}
        
        try:
            with tracker.track_deployment(
                cluster="test-cluster",
                namespace="test-namespace",
                app_config_dir="/test",
                config_file_path="/test/config.yaml",
                config_data=config_data
            ) as deployment_id:
                # Simulate failure
                raise Exception("Deployment failed")
        except Exception:
            pass
        
        # Check deployment marked as failed
        db = DeploymentDatabase(temp_db)
        deployments = db.list_deployments()
        assert len(deployments) == 1
        assert deployments[0].status == DeploymentStatus.FAILED
    
    def test_track_app_deployment(self, temp_db):
        """Test app deployment tracking."""
        tracker = DeploymentTracker(temp_db)
        
        with tracker.track_deployment(
            cluster="test",
            namespace="test",
            app_config_dir="/test",
            config_file_path="/test/config.yaml",
            config_data={"test": True}
        ):
            with tracker.track_app_deployment(
                app_name="test-app",
                app_type="install-helm",
                app_namespace="test",
                app_config={"path": "charts/test"}
            ) as app_id:
                assert app_id is not None
    
    @patch('subprocess.run')
    def test_track_helm_release(self, mock_run, temp_db):
        """Test Helm release tracking."""
        tracker = DeploymentTracker(temp_db)
        
        # Mock helm list output
        mock_run.return_value = MagicMock(
            stdout=json.dumps([{
                "name": "test-release",
                "revision": 1,
                "status": "deployed"
            }]),
            returncode=0
        )
        
        with tracker.track_deployment(
            cluster="test",
            namespace="test",
            app_config_dir="/test",
            config_file_path="/test/config.yaml",
            config_data={"test": True}
        ):
            with tracker.track_app_deployment(
                app_name="test-app",
                app_type="install-helm",
                app_namespace="test",
                app_config={}
            ):
                tracker.track_helm_release(
                    release_name="test-release",
                    namespace="test",
                    chart="test-chart",
                    chart_version="1.0.0"
                )
        
        # Verify release was tracked
        db = DeploymentDatabase(temp_db)
        deployment = db.list_deployments()[0]
        detail = db.get_deployment(deployment.deployment_id)
        assert len(detail.helm_releases) == 1
        assert detail.helm_releases[0].release_name == "test-release"
    
    def test_track_resource(self, temp_db):
        """Test Kubernetes resource tracking."""
        tracker = DeploymentTracker(temp_db)
        
        manifest = {
            "apiVersion": "v1",
            "kind": "ConfigMap",
            "metadata": {
                "name": "test-config",
                "namespace": "test"
            },
            "data": {"key": "value"}
        }
        
        with tracker.track_deployment(
            cluster="test",
            namespace="test",
            app_config_dir="/test",
            config_file_path="/test/config.yaml",
            config_data={"test": True}
        ):
            with tracker.track_app_deployment(
                app_name="test-app",
                app_type="install-yaml",
                app_namespace="test",
                app_config={}
            ):
                tracker.track_resource(
                    manifest=manifest,
                    action=ResourceAction.CREATE,
                    source_file="test.yaml"
                )
        
        # Verify resource was tracked
        db = DeploymentDatabase(temp_db)
        deployment = db.list_deployments()[0]
        detail = db.get_deployment(deployment.deployment_id)
        assert len(detail.resources) == 1
        assert detail.resources[0].kind == "ConfigMap"
        assert detail.resources[0].name == "test-config"