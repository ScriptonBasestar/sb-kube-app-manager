"""Tests for error_classifier module."""

from sbkube.utils.error_classifier import ErrorClassifier


class TestErrorClassifier:
    """Test ErrorClassifier functionality."""

    def test_classify_postgresql_auth_error(self):
        """PostgreSQL 인증 에러를 올바르게 분류하는지 테스트."""
        error_message = """
        sqlalchemy.exc.OperationalError:
        connection to server at "postgresql.data.svc.cluster.local" (10.43.8.117),
        port 5432 failed:
        FATAL: password authentication failed for user "airflow_user"
        """

        result = ErrorClassifier.classify(error_message)

        assert result["category"] == "DatabaseAuthenticationError"
        assert result["severity"] == "high"
        assert result["phase"] == "deploy"
        assert result["is_classified"] is True

    def test_classify_helm_release_error(self):
        """Helm 릴리스 에러를 올바르게 분류하는지 테스트."""
        error_message = "Error: INSTALLATION FAILED: release airflow failed"

        result = ErrorClassifier.classify(error_message)

        assert result["category"] == "HelmReleaseError"
        assert result["severity"] == "high"
        assert result["is_classified"] is True

    def test_classify_kubernetes_connection_error(self):
        """Kubernetes 연결 에러를 올바르게 분류하는지 테스트."""
        error_message = "Unable to connect to the server: dial tcp 127.0.0.1:6443: connection refused"

        result = ErrorClassifier.classify(error_message)

        assert result["category"] == "KubernetesConnectionError"
        assert result["severity"] == "critical"
        assert result["is_classified"] is True

    def test_classify_unknown_error(self):
        """알 수 없는 에러 처리 테스트."""
        error_message = "Some completely unknown error that doesn't match any pattern"

        result = ErrorClassifier.classify(error_message)

        assert result["category"] == "UnknownError"
        assert result["is_classified"] is False

    def test_extract_db_details_postgresql(self):
        """PostgreSQL 에러에서 상세 정보 추출 테스트."""
        error_message = """
        connection to server at "postgresql.data.svc.cluster.local" (10.43.8.117),
        port 5432 failed:
        FATAL: password authentication failed for user "airflow_user"
        """

        details = ErrorClassifier.extract_db_details(error_message)

        assert details["db_type"] == "postgresql"
        assert details["user"] == "airflow_user"
        assert details["host"] == "postgresql.data.svc.cluster.local"
        assert details["port"] == "5432"

    def test_extract_db_details_mysql(self):
        """MySQL 에러에서 상세 정보 추출 테스트."""
        error_message = "Access denied for user 'root'@'mysql.default.svc.cluster.local' (using password: YES)"

        details = ErrorClassifier.extract_db_details(error_message)

        assert details["db_type"] == "mysql"
        assert details["user"] == "root"

    def test_extract_helm_details(self):
        """Helm 에러에서 상세 정보 추출 테스트."""
        error_message = "Error: release airflow in namespace airflow failed with chart apache/airflow"

        details = ErrorClassifier.extract_helm_details(error_message)

        assert details["release_name"] == "airflow"
        assert details["namespace"] == "airflow"
        assert details["chart"] == "apache/airflow"

    def test_database_connection_error_classification(self):
        """데이터베이스 연결 에러 분류 테스트."""
        error_message = (
            "connection to server at localhost, port 5432 failed: connection refused"
        )

        result = ErrorClassifier.classify(error_message)

        assert result["category"] == "DatabaseConnectionError"
        assert result["severity"] == "high"

    def test_namespace_not_found_error(self):
        """네임스페이스 없음 에러 분류 테스트."""
        error_message = 'Error from server (NotFound): namespaces "airflow" not found'

        result = ErrorClassifier.classify(error_message)

        assert result["category"] == "NamespaceNotFoundError"
        assert result["severity"] == "medium"
