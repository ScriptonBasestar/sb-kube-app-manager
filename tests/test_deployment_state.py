"""
Tests for deployment state tracking and rollback functionality.
"""

import pytest
import tempfile
from pathlib import Path
from datetime import datetime, timedelta
import json
import yaml
from unittest.mock import patch, MagicMock

from sbkube.models.deployment_state import (
    DeploymentStatus, ResourceAction, DeploymentCreate,
    AppDeploymentCreate, ResourceInfo, HelmReleaseInfo,
    RollbackRequest
)
from sbkube.state.database import DeploymentDatabase
from sbkube.state.tracker import DeploymentTracker
from sbkube.state.rollback import RollbackManager
from sbkube.exceptions import DeploymentError, RollbackError


@pytest.fixture
def temp_db():
    """Create a temporary database for testing."""
    with tempfile.NamedTemporaryFile(suffix=".db", delete=False) as f:
        db_path = Path(f.name)
    
    yield db_path
    
    # Cleanup
    if db_path.exists():
        db_path.unlink()


@pytest.fixture
def deployment_db(temp_db):
    """Create a DeploymentDatabase instance."""
    return DeploymentDatabase(temp_db)


@pytest.fixture
def sample_deployment_data():
    """Sample deployment data for testing."""
    return DeploymentCreate(
        deployment_id="dep-20240120-test",
        cluster="test-cluster",
        namespace="test-namespace",
        app_config_dir="/test/config",
        config_file_path="/test/config/config.yaml",
        command="deploy",
        command_args={"dry_run": False},
        config_snapshot={
            "namespace": "test-namespace",
            "apps": [
                {
                    "name": "test-app",
                    "type": "install-helm",
                    "specs": {"path": "charts/test-app"}
                }
            ]
        },
        sbkube_version="1.0.0",
        operator="test-user"
    )


@pytest.fixture
def sample_app_data():
    """Sample app deployment data for testing."""
    return AppDeploymentCreate(
        app_name="test-app",
        app_type="install-helm",
        namespace="test-namespace",
        app_config={"path": "charts/test-app"}
    )


class TestDeploymentDatabase:
    """Test deployment database operations."""
    
    def test_create_deployment(self, deployment_db, sample_deployment_data):
        """Test creating a deployment record."""
        deployment = deployment_db.create_deployment(sample_deployment_data)
        
        assert deployment.deployment_id == "dep-20240120-test"
        assert deployment.cluster == "test-cluster"
        assert deployment.namespace == "test-namespace"
        assert deployment.status == DeploymentStatus.PENDING.value
    
    def test_add_app_deployment(self, deployment_db, sample_deployment_data, sample_app_data):
        """Test adding app deployment to deployment."""
        deployment = deployment_db.create_deployment(sample_deployment_data)
        app_deployment = deployment_db.add_app_deployment(deployment.id, sample_app_data)
        
        assert app_deployment.app_name == "test-app"
        assert app_deployment.app_type == "install-helm"
        assert app_deployment.deployment_id == deployment.id
    
    def test_add_deployed_resource(self, deployment_db, sample_deployment_data, sample_app_data):
        """Test adding deployed resource."""
        deployment = deployment_db.create_deployment(sample_deployment_data)
        app_deployment = deployment_db.add_app_deployment(deployment.id, sample_app_data)
        
        resource_info = ResourceInfo(
            api_version="apps/v1",
            kind="Deployment",
            name="test-deployment",
            namespace="test-namespace",
            action=ResourceAction.CREATE,
            current_state={"spec": {"replicas": 3}}
        )
        
        resource = deployment_db.add_deployed_resource(app_deployment.id, resource_info)
        
        assert resource.kind == "Deployment"
        assert resource.name == "test-deployment"
        assert resource.action == ResourceAction.CREATE.value
    
    def test_update_deployment_status(self, deployment_db, sample_deployment_data):
        """Test updating deployment status."""
        deployment = deployment_db.create_deployment(sample_deployment_data)
        
        deployment_db.update_deployment_status(
            deployment.deployment_id,
            DeploymentStatus.SUCCESS
        )
        
        # Retrieve and check
        updated = deployment_db.get_deployment(deployment.deployment_id)
        assert updated.status == DeploymentStatus.SUCCESS
    
    def test_list_deployments(self, deployment_db):
        """Test listing deployments with filtering."""
        # Create multiple deployments
        for i in range(5):
            data = DeploymentCreate(
                deployment_id=f"dep-{i}",
                cluster="test-cluster",
                namespace=f"ns-{i % 2}",  # Alternate between ns-0 and ns-1
                app_config_dir="/test/config",
                config_file_path="/test/config.yaml",
                command="deploy",
                config_snapshot={"test": i}
            )
            deployment_db.create_deployment(data)
        
        # Test listing all
        all_deployments = deployment_db.list_deployments()
        assert len(all_deployments) == 5
        
        # Test filtering by namespace
        ns0_deployments = deployment_db.list_deployments(namespace="ns-0")
        assert len(ns0_deployments) == 3
        
        # Test pagination
        paginated = deployment_db.list_deployments(limit=2, offset=2)
        assert len(paginated) == 2
    
    def test_compute_resource_checksum(self):
        """Test resource checksum computation."""
        resource_data = {
            "apiVersion": "v1",
            "kind": "ConfigMap",
            "metadata": {
                "name": "test-config",
                "namespace": "default",
                "resourceVersion": "12345",  # Should be ignored
                "uid": "abc-123"  # Should be ignored
            },
            "data": {
                "key": "value"
            }
        }
        
        checksum1 = DeploymentDatabase.compute_resource_checksum(resource_data)
        
        # Change volatile field - checksum should remain same
        resource_data["metadata"]["resourceVersion"] = "67890"
        checksum2 = DeploymentDatabase.compute_resource_checksum(resource_data)
        
        assert checksum1 == checksum2
        
        # Change actual data - checksum should change
        resource_data["data"]["key"] = "new-value"
        checksum3 = DeploymentDatabase.compute_resource_checksum(resource_data)
        
        assert checksum1 != checksum3


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
        detail = db.get_deployment(tracker.current_deployment_id)
        assert len(detail.resources) == 1
        assert detail.resources[0].kind == "ConfigMap"
        assert detail.resources[0].name == "test-config"


class TestRollbackManager:
    """Test rollback functionality."""
    
    def create_test_deployment(self, db: DeploymentDatabase) -> str:
        """Create a test deployment with resources."""
        # Create deployment
        deployment_data = DeploymentCreate(
            deployment_id="dep-test-001",
            cluster="test-cluster",
            namespace="test-namespace",
            app_config_dir="/test/config",
            config_file_path="/test/config.yaml",
            command="deploy",
            config_snapshot={"test": True}
        )
        deployment = db.create_deployment(deployment_data)
        
        # Add app deployment
        app_data = AppDeploymentCreate(
            app_name="test-app",
            app_type="install-helm",
            namespace="test-namespace",
            app_config={"path": "charts/test"},
            metadata={
                "release_name": "test-release",
                "chart_version": "1.0.0"
            }
        )
        app_deployment = db.add_app_deployment(deployment.id, app_data)
        
        # Add rollback info
        db.update_app_deployment_status(
            app_deployment.id,
            DeploymentStatus.SUCCESS,
            rollback_info={
                "type": "helm",
                "release_name": "test-release",
                "namespace": "test-namespace",
                "revision": 2
            }
        )
        
        # Add resources
        resource_info = ResourceInfo(
            api_version="v1",
            kind="ConfigMap",
            name="test-config",
            namespace="test-namespace",
            action=ResourceAction.CREATE,
            current_state={"data": {"key": "value"}}
        )
        db.add_deployed_resource(app_deployment.id, resource_info)
        
        # Mark deployment as success
        db.update_deployment_status(deployment.deployment_id, DeploymentStatus.SUCCESS)
        
        return deployment.deployment_id
    
    def test_validate_rollback(self, temp_db):
        """Test rollback validation."""
        db = DeploymentDatabase(temp_db)
        deployment_id = self.create_test_deployment(db)
        
        rollback_manager = RollbackManager(temp_db)
        deployment = db.get_deployment(deployment_id)
        
        # Should pass validation
        request = RollbackRequest(
            deployment_id=deployment_id,
            dry_run=True
        )
        
        # This should not raise
        rollback_manager._validate_rollback(deployment, None, request)
    
    def test_simulate_rollback(self, temp_db):
        """Test rollback simulation."""
        db = DeploymentDatabase(temp_db)
        deployment_id = self.create_test_deployment(db)
        
        rollback_manager = RollbackManager(temp_db)
        
        request = RollbackRequest(
            deployment_id=deployment_id,
            dry_run=True
        )
        
        result = rollback_manager.rollback_deployment(request)
        
        assert result["dry_run"] is True
        assert len(result["actions"]) > 0
        
        # Check Helm rollback action
        helm_actions = [a for a in result["actions"] if a["type"] == "helm_rollback"]
        assert len(helm_actions) == 1
        assert helm_actions[0]["details"]["release"] == "test-release"
        assert helm_actions[0]["details"]["from_revision"] == 2
        assert helm_actions[0]["details"]["to_revision"] == 1
    
    @patch('subprocess.run')
    def test_execute_helm_rollback(self, mock_run, temp_db):
        """Test executing Helm rollback."""
        db = DeploymentDatabase(temp_db)
        deployment_id = self.create_test_deployment(db)
        
        rollback_manager = RollbackManager(temp_db)
        
        # Mock successful helm rollback
        mock_run.return_value = MagicMock(returncode=0)
        
        request = RollbackRequest(
            deployment_id=deployment_id,
            dry_run=False
        )
        
        result = rollback_manager.rollback_deployment(request)
        
        assert result["success"] is True
        assert len(result["rollbacks"]) > 0
        
        # Verify helm rollback was called
        mock_run.assert_called()
        call_args = mock_run.call_args[0][0]
        assert call_args[0] == "helm"
        assert call_args[1] == "rollback"
    
    def test_list_rollback_points(self, temp_db):
        """Test listing rollback points."""
        db = DeploymentDatabase(temp_db)
        
        # Create multiple deployments
        for i in range(3):
            deployment_data = DeploymentCreate(
                deployment_id=f"dep-test-{i:03d}",
                cluster="test-cluster",
                namespace="test-namespace",
                app_config_dir="/test/config",
                config_file_path="/test/config.yaml",
                command="deploy",
                config_snapshot={"version": i}
            )
            deployment = db.create_deployment(deployment_data)
            
            # Mark some as success, some as failed
            status = DeploymentStatus.SUCCESS if i % 2 == 0 else DeploymentStatus.FAILED
            db.update_deployment_status(deployment.deployment_id, status)
        
        rollback_manager = RollbackManager(temp_db)
        points = rollback_manager.list_rollback_points(
            cluster="test-cluster",
            namespace="test-namespace",
            app_config_dir="/test/config"
        )
        
        assert len(points) == 3
        
        # Check rollback eligibility
        rollbackable = [p for p in points if p["can_rollback"]]
        assert len(rollbackable) == 2  # Only successful deployments