"""
Shared fixtures for state management tests.
"""

import tempfile
from pathlib import Path

import pytest

from sbkube.models.deployment_state import AppDeploymentCreate, DeploymentCreate
from sbkube.state.database import DeploymentDatabase


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
def db_session(deployment_db):
    """Create a database session for testing."""
    with deployment_db.get_session() as session:
        yield session


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
                    "specs": {"path": "charts/test-app"},
                }
            ],
        },
        sbkube_version="1.0.0",
        operator="test-user",
    )


@pytest.fixture
def sample_app_data():
    """Sample app deployment data for testing."""
    return AppDeploymentCreate(
        app_name="test-app",
        app_type="install-helm",
        namespace="test-namespace",
        app_config={"path": "charts/test-app"},
    )
