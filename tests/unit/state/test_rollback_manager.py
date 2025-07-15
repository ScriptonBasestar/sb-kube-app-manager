"""
Tests for rollback functionality.
"""

from unittest.mock import MagicMock, patch

import pytest

from sbkube.models.deployment_state import (
    AppDeployment,
    DeployedResource,
    Deployment,
    DeploymentStatus,
    ResourceAction,
    RollbackRequest,
)
from sbkube.state.database import DeploymentDatabase
from sbkube.state.rollback import RollbackManager


@pytest.mark.unit
class TestRollbackManager:
    """Test rollback functionality."""

    def create_test_deployment(self, db: DeploymentDatabase) -> str:
        """Create a test deployment with resources."""
        with db.get_session() as session:
            # Create deployment
            deployment = Deployment(
                deployment_id="dep-test-001",
                cluster="test-cluster",
                namespace="test-namespace",
                app_config_dir="/test/config",
                config_file_path="/test/config.yaml",
                command="deploy",
                config_snapshot={"test": True},
            )
            session.add(deployment)
            session.flush()

            # Create app deployment
            app_deployment = AppDeployment(
                deployment_id=deployment.id,
                app_name="test-app",
                app_type="install-helm",
                namespace="test-namespace",
                app_config={"path": "charts/test"},
                metadata={"release_name": "test-release", "chart_version": "1.0.0"},
                rollback_info={
                    "type": "helm",
                    "release_name": "test-release",
                    "namespace": "test-namespace",
                    "revision": 2,
                },
            )
            session.add(app_deployment)
            session.flush()

            # Create deployed resource
            resource = DeployedResource(
                app_deployment_id=app_deployment.id,
                api_version="v1",
                kind="ConfigMap",
                name="test-config",
                namespace="test-namespace",
                action=ResourceAction.CREATE.value,
                current_state={"data": {"key": "value"}},
            )
            session.add(resource)
            session.flush()

            # Mark deployment as success
            deployment.status = DeploymentStatus.SUCCESS.value
            session.flush()

            return deployment.deployment_id

    def test_validate_rollback(self, temp_db):
        """Test rollback validation."""
        db = DeploymentDatabase(temp_db)
        deployment_id = self.create_test_deployment(db)

        rollback_manager = RollbackManager(temp_db)
        deployment = db.get_deployment(deployment_id)

        # Should pass validation
        request = RollbackRequest(deployment_id=deployment_id, dry_run=True)

        # This should not raise
        rollback_manager._validate_rollback(deployment, None, request)

    def test_simulate_rollback(self, temp_db):
        """Test rollback simulation."""
        db = DeploymentDatabase(temp_db)
        deployment_id = self.create_test_deployment(db)

        rollback_manager = RollbackManager(temp_db)

        request = RollbackRequest(deployment_id=deployment_id, dry_run=True)

        result = rollback_manager.rollback_deployment(request)

        assert result["dry_run"] is True
        assert len(result["actions"]) > 0

        # Check Helm rollback action
        helm_actions = [a for a in result["actions"] if a["type"] == "helm_rollback"]
        assert len(helm_actions) == 1
        assert helm_actions[0]["details"]["release"] == "test-release"
        assert helm_actions[0]["details"]["from_revision"] == 2
        assert helm_actions[0]["details"]["to_revision"] == 1

    @patch("subprocess.run")
    def test_execute_helm_rollback(self, mock_run, temp_db):
        """Test executing Helm rollback."""
        db = DeploymentDatabase(temp_db)
        deployment_id = self.create_test_deployment(db)

        rollback_manager = RollbackManager(temp_db)

        # Mock successful helm rollback
        mock_run.return_value = MagicMock(returncode=0)

        request = RollbackRequest(deployment_id=deployment_id, dry_run=False)

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
        with db.get_session() as session:
            for i in range(3):
                deployment = Deployment(
                    deployment_id=f"dep-test-{i:03d}",
                    cluster="test-cluster",
                    namespace="test-namespace",
                    app_config_dir="/test/config",
                    config_file_path="/test/config.yaml",
                    command="deploy",
                    config_snapshot={"version": i},
                )

                # Mark some as success, some as failed
                if i % 2 == 0:
                    deployment.status = DeploymentStatus.SUCCESS.value
                else:
                    deployment.status = DeploymentStatus.FAILED.value

                session.add(deployment)
            session.flush()

        rollback_manager = RollbackManager(temp_db)
        points = rollback_manager.list_rollback_points(
            cluster="test-cluster",
            namespace="test-namespace",
            app_config_dir="/test/config",
        )

        assert len(points) == 3

        # Check rollback eligibility
        rollbackable = [p for p in points if p["can_rollback"]]
        assert len(rollbackable) == 2  # Only successful deployments
