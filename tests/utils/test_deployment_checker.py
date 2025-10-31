"""Tests for DeploymentChecker utility class."""

from pathlib import Path
from unittest.mock import MagicMock, patch

import pytest

from sbkube.state.database import DeploymentStatus
from sbkube.utils.deployment_checker import DeploymentChecker, get_current_cluster


class TestGetCurrentCluster:
    """Tests for get_current_cluster() function."""

    @patch("subprocess.run")
    def test_get_current_cluster_success(self, mock_run):
        """Test successful kubectl context retrieval."""
        mock_run.return_value = MagicMock(
            returncode=0,
            stdout="my-cluster\n",
        )

        result = get_current_cluster()

        assert result == "my-cluster"
        mock_run.assert_called_once()

    @patch("subprocess.run")
    def test_get_current_cluster_failure(self, mock_run):
        """Test kubectl command failure."""
        mock_run.return_value = MagicMock(
            returncode=1,
            stdout="",
        )

        result = get_current_cluster()

        assert result == "unknown"

    @patch("subprocess.run", side_effect=FileNotFoundError)
    def test_get_current_cluster_no_kubectl(self, mock_run):
        """Test when kubectl is not installed."""
        result = get_current_cluster()

        assert result == "unknown"


class TestDeploymentChecker:
    """Tests for DeploymentChecker class."""

    @pytest.fixture
    def base_dir(self, tmp_path):
        """Create a temporary base directory."""
        return tmp_path

    @pytest.fixture
    def mock_db(self):
        """Mock DeploymentDatabase."""
        with patch("sbkube.utils.deployment_checker.DeploymentDatabase") as mock:
            yield mock.return_value

    @pytest.fixture
    def checker(self, base_dir, mock_db):
        """Create a DeploymentChecker instance with mocked database."""
        checker = DeploymentChecker(
            base_dir=base_dir,
            cluster="test-cluster",
            namespace="test-namespace",
        )
        # Replace the real db with our mock
        checker.db = mock_db
        return checker

    def test_init(self, base_dir):
        """Test DeploymentChecker initialization."""
        checker = DeploymentChecker(
            base_dir=base_dir,
            cluster="my-cluster",
            namespace="my-namespace",
        )

        assert checker.base_dir == Path(base_dir)
        assert checker.cluster == "my-cluster"
        assert checker.namespace == "my-namespace"

    def test_init_default_cluster(self, base_dir):
        """Test initialization with default cluster."""
        with patch(
            "sbkube.utils.deployment_checker.get_current_cluster",
            return_value="default-cluster",
        ):
            checker = DeploymentChecker(base_dir=base_dir)

            assert checker.cluster == "default-cluster"

    def test_check_app_group_deployed_success(self, checker, mock_db, base_dir):
        """Test checking successfully deployed app-group."""
        # Mock deployment detail
        mock_deployment = MagicMock()
        mock_deployment.status = DeploymentStatus.SUCCESS
        mock_deployment.timestamp = "2025-10-30T10:00:00"
        mock_deployment.namespace = "test-namespace"
        mock_db.get_latest_deployment_any_namespace.return_value = mock_deployment

        # Create app-group directory
        app_dir = base_dir / "a000_infra"
        app_dir.mkdir()

        is_deployed, msg = checker.check_app_group_deployed("a000_infra")

        assert is_deployed is True
        assert "deployed at" in msg
        assert "test-namespace" in msg
        mock_db.get_latest_deployment_any_namespace.assert_called_once()

    def test_check_app_group_deployed_never_deployed(self, checker, mock_db):
        """Test checking app-group that was never deployed."""
        mock_db.get_latest_deployment_any_namespace.return_value = None

        is_deployed, msg = checker.check_app_group_deployed("a000_infra")

        assert is_deployed is False
        assert msg == "never deployed"

    def test_check_app_group_deployed_failed_status(self, checker, mock_db):
        """Test checking app-group with failed deployment."""
        mock_deployment = MagicMock()
        mock_deployment.status = DeploymentStatus.FAILED
        mock_db.get_latest_deployment_any_namespace.return_value = mock_deployment

        is_deployed, msg = checker.check_app_group_deployed("a000_infra")

        assert is_deployed is False
        assert "failed" in msg.lower()

    def test_check_app_group_deployed_database_error(self, checker, mock_db):
        """Test handling database errors."""
        mock_db.get_latest_deployment_any_namespace.side_effect = Exception(
            "DB connection failed"
        )

        is_deployed, msg = checker.check_app_group_deployed("a000_infra")

        assert is_deployed is False
        assert "database error" in msg

    def test_check_app_group_deployed_with_namespace_override(self, checker, mock_db):
        """Test checking with namespace override."""
        mock_deployment = MagicMock()
        mock_deployment.status = DeploymentStatus.SUCCESS
        mock_deployment.timestamp = "2025-10-30T10:00:00"
        mock_db.get_latest_deployment.return_value = mock_deployment

        is_deployed, msg = checker.check_app_group_deployed(
            "a000_infra", namespace="custom-namespace"
        )

        assert is_deployed is True
        # Verify namespace override was used
        call_args = mock_db.get_latest_deployment.call_args
        assert call_args[1]["namespace"] == "custom-namespace"

    def test_check_dependencies_all_deployed(self, checker, mock_db):
        """Test checking dependencies when all are deployed."""
        mock_deployment = MagicMock()
        mock_deployment.status = DeploymentStatus.SUCCESS
        mock_deployment.timestamp = "2025-10-30T10:00:00"
        mock_deployment.namespace = "test-namespace"
        mock_db.get_latest_deployment_any_namespace.return_value = mock_deployment

        deps = ["a000_infra", "a100_data"]
        result = checker.check_dependencies(deps)

        assert result["all_deployed"] is True
        assert result["missing"] == []
        assert len(result["details"]) == 2
        assert result["details"]["a000_infra"][0] is True
        assert result["details"]["a100_data"][0] is True

    def test_check_dependencies_some_missing(self, checker, mock_db):
        """Test checking dependencies when some are missing."""

        def mock_get_deployment(cluster, app_config_dir):
            if "a100_data" in app_config_dir:
                return None  # Not deployed
            mock_dep = MagicMock()
            mock_dep.status = DeploymentStatus.SUCCESS
            mock_dep.timestamp = "2025-10-30T10:00:00"
            mock_dep.namespace = "test-namespace"
            return mock_dep

        mock_db.get_latest_deployment_any_namespace.side_effect = mock_get_deployment

        deps = ["a000_infra", "a100_data"]
        result = checker.check_dependencies(deps)

        assert result["all_deployed"] is False
        assert result["missing"] == ["a100_data"]
        assert len(result["details"]) == 2
        assert result["details"]["a000_infra"][0] is True
        assert result["details"]["a100_data"][0] is False

    def test_check_dependencies_empty_list(self, checker, mock_db):
        """Test checking empty dependency list."""
        result = checker.check_dependencies([])

        assert result["all_deployed"] is True
        assert result["missing"] == []
        assert result["details"] == {}

    def test_get_deployment_info_success(self, checker, mock_db):
        """Test getting deployment info."""
        mock_deployment = MagicMock()
        mock_deployment.cluster = "test-cluster"
        mock_deployment.namespace = "test-namespace"
        mock_deployment.app_config_dir = "/path/to/app"
        mock_deployment.status = DeploymentStatus.SUCCESS
        mock_deployment.timestamp = "2025-10-30T10:00:00"
        mock_db.get_latest_deployment.return_value = mock_deployment

        info = checker.get_deployment_info("a000_infra")

        assert info is not None
        assert info["cluster"] == "test-cluster"
        assert info["namespace"] == "test-namespace"
        assert info["status"] == "success"

    def test_get_deployment_info_not_found(self, checker, mock_db):
        """Test getting deployment info when not found."""
        mock_db.get_latest_deployment.return_value = None

        info = checker.get_deployment_info("a000_infra")

        assert info is None

    def test_get_deployment_info_database_error(self, checker, mock_db):
        """Test handling database errors in get_deployment_info."""
        mock_db.get_latest_deployment.side_effect = Exception("DB error")

        info = checker.get_deployment_info("a000_infra")

        assert info is None

    def test_check_app_group_deployed_namespace_auto_detect(self, checker, mock_db):
        """Test automatic namespace detection when namespace not provided."""
        # Mock deployment in different namespace
        mock_deployment = MagicMock()
        mock_deployment.status = DeploymentStatus.SUCCESS
        mock_deployment.timestamp = "2025-10-30T15:00:00"
        mock_deployment.namespace = "postgresql"  # Different namespace
        mock_db.get_latest_deployment_any_namespace.return_value = mock_deployment

        # Check without providing namespace (auto-detect)
        is_deployed, msg = checker.check_app_group_deployed("a101_data_rdb")

        assert is_deployed is True
        assert "postgresql" in msg  # Should include namespace in message
        assert "deployed at" in msg
        mock_db.get_latest_deployment_any_namespace.assert_called_once()

    def test_check_app_group_deployed_with_namespace_specific_query(
        self, checker, mock_db
    ):
        """Test that providing namespace uses namespace-specific query."""
        mock_deployment = MagicMock()
        mock_deployment.status = DeploymentStatus.SUCCESS
        mock_deployment.timestamp = "2025-10-30T15:00:00"
        mock_db.get_latest_deployment.return_value = mock_deployment

        # Check with specific namespace
        is_deployed, msg = checker.check_app_group_deployed(
            "a101_data_rdb", namespace="postgresql"
        )

        assert is_deployed is True
        # Should use get_latest_deployment (not any_namespace)
        mock_db.get_latest_deployment.assert_called_once()
        mock_db.get_latest_deployment_any_namespace.assert_not_called()

    def test_check_dependencies_different_namespaces(self, checker, mock_db):
        """Test checking dependencies deployed in different namespaces."""

        def mock_get_any_namespace(cluster, app_config_dir):
            if "a000_infra" in app_config_dir:
                mock_dep = MagicMock()
                mock_dep.status = DeploymentStatus.SUCCESS
                mock_dep.timestamp = "2025-10-30"
                mock_dep.namespace = "infra"
                return mock_dep
            elif "a101_data" in app_config_dir:
                mock_dep = MagicMock()
                mock_dep.status = DeploymentStatus.SUCCESS
                mock_dep.timestamp = "2025-10-30"
                mock_dep.namespace = "postgresql"
                return mock_dep
            return None

        mock_db.get_latest_deployment_any_namespace.side_effect = mock_get_any_namespace

        deps = ["a000_infra", "a101_data"]
        result = checker.check_dependencies(deps, namespace=None)

        assert result["all_deployed"] is True
        assert result["missing"] == []
        # Check that namespaces are included in messages
        assert "infra" in result["details"]["a000_infra"][1]
        assert "postgresql" in result["details"]["a101_data"][1]
