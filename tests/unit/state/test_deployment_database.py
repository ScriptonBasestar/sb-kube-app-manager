"""
Tests for deployment database operations.
"""

import pytest

from sbkube.models.deployment_state import (
    AppDeployment,
    DeployedResource,
    Deployment,
    DeploymentStatus,
    ResourceAction,
)
from sbkube.state.database import DeploymentDatabase


@pytest.mark.unit
class TestDeploymentDatabase:
    """Test deployment database operations."""

    def test_create_deployment(self, deployment_db, sample_deployment_data):
        """Test creating a deployment record."""
        # Use session context to avoid detached instance issues
        with deployment_db.get_session() as session:
            deployment = Deployment(
                deployment_id=sample_deployment_data.deployment_id,
                cluster=sample_deployment_data.cluster,
                namespace=sample_deployment_data.namespace,
                app_config_dir=sample_deployment_data.app_config_dir,
                config_file_path=sample_deployment_data.config_file_path,
                command=sample_deployment_data.command,
                command_args=sample_deployment_data.command_args,
                dry_run=sample_deployment_data.dry_run,
                config_snapshot=sample_deployment_data.config_snapshot,
                sources_snapshot=sample_deployment_data.sources_snapshot,
                sbkube_version=sample_deployment_data.sbkube_version,
                operator=sample_deployment_data.operator,
            )
            session.add(deployment)
            session.flush()

            # Test within session context
            assert deployment.deployment_id == "dep-20240120-test"
            assert deployment.cluster == "test-cluster"
            assert deployment.namespace == "test-namespace"
            assert deployment.status == DeploymentStatus.PENDING.value

    def test_add_app_deployment(
        self, deployment_db, sample_deployment_data, sample_app_data
    ):
        """Test adding app deployment to deployment."""
        with deployment_db.get_session() as session:
            # Create deployment
            deployment = Deployment(
                deployment_id=sample_deployment_data.deployment_id,
                cluster=sample_deployment_data.cluster,
                namespace=sample_deployment_data.namespace,
                app_config_dir=sample_deployment_data.app_config_dir,
                config_file_path=sample_deployment_data.config_file_path,
                command=sample_deployment_data.command,
                config_snapshot=sample_deployment_data.config_snapshot,
                sbkube_version=sample_deployment_data.sbkube_version,
                operator=sample_deployment_data.operator,
            )
            session.add(deployment)
            session.flush()

            # Create app deployment
            app_deployment = AppDeployment(
                deployment_id=deployment.id,
                app_name=sample_app_data.app_name,
                app_type=sample_app_data.app_type,
                namespace=sample_app_data.namespace,
                app_config=sample_app_data.app_config,
            )
            session.add(app_deployment)
            session.flush()

            assert app_deployment.app_name == "test-app"
            assert app_deployment.app_type == "install-helm"
            assert app_deployment.deployment_id == deployment.id

    def test_add_deployed_resource(
        self, deployment_db, sample_deployment_data, sample_app_data
    ):
        """Test adding deployed resource."""
        with deployment_db.get_session() as session:
            # Create deployment
            deployment = Deployment(
                deployment_id=sample_deployment_data.deployment_id,
                cluster=sample_deployment_data.cluster,
                namespace=sample_deployment_data.namespace,
                app_config_dir=sample_deployment_data.app_config_dir,
                config_file_path=sample_deployment_data.config_file_path,
                command=sample_deployment_data.command,
                config_snapshot=sample_deployment_data.config_snapshot,
                sbkube_version=sample_deployment_data.sbkube_version,
                operator=sample_deployment_data.operator,
            )
            session.add(deployment)
            session.flush()

            # Create app deployment
            app_deployment = AppDeployment(
                deployment_id=deployment.id,
                app_name=sample_app_data.app_name,
                app_type=sample_app_data.app_type,
                namespace=sample_app_data.namespace,
                app_config=sample_app_data.app_config,
            )
            session.add(app_deployment)
            session.flush()

            # Create deployed resource
            resource = DeployedResource(
                app_deployment_id=app_deployment.id,
                api_version="apps/v1",
                kind="Deployment",
                name="test-deployment",
                namespace="test-namespace",
                action=ResourceAction.CREATE.value,
                current_state={"spec": {"replicas": 3}},
            )
            session.add(resource)
            session.flush()

            assert resource.kind == "Deployment"
            assert resource.name == "test-deployment"
            assert resource.action == ResourceAction.CREATE.value

    def test_update_deployment_status(self, deployment_db, sample_deployment_data):
        """Test updating deployment status."""
        # Create deployment first
        deployment_id = None
        with deployment_db.get_session() as session:
            deployment = Deployment(
                deployment_id=sample_deployment_data.deployment_id,
                cluster=sample_deployment_data.cluster,
                namespace=sample_deployment_data.namespace,
                app_config_dir=sample_deployment_data.app_config_dir,
                config_file_path=sample_deployment_data.config_file_path,
                command=sample_deployment_data.command,
                config_snapshot=sample_deployment_data.config_snapshot,
                sbkube_version=sample_deployment_data.sbkube_version,
                operator=sample_deployment_data.operator,
            )
            session.add(deployment)
            session.flush()
            deployment_id = deployment.deployment_id

        # Update status using database method
        deployment_db.update_deployment_status(deployment_id, DeploymentStatus.SUCCESS)

        # Verify update
        with deployment_db.get_session() as session:
            updated = (
                session.query(Deployment)
                .filter(Deployment.deployment_id == deployment_id)
                .first()
            )
            assert updated.status == DeploymentStatus.SUCCESS.value

    def test_list_deployments(self, deployment_db):
        """Test listing deployments with filtering."""
        # Create multiple deployments
        with deployment_db.get_session() as session:
            for i in range(5):
                deployment = Deployment(
                    deployment_id=f"dep-{i}",
                    cluster="test-cluster",
                    namespace=f"ns-{i % 2}",  # Alternate between ns-0 and ns-1
                    app_config_dir="/test/config",
                    config_file_path="/test/config.yaml",
                    command="deploy",
                    config_snapshot={"test": i},
                )
                session.add(deployment)
            session.flush()

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
                "uid": "abc-123",  # Should be ignored
            },
            "data": {"key": "value"},
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
