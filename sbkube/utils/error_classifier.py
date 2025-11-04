"""Error classification utility for SBKube.

에러 메시지 패턴을 분석하여 에러 타입을 자동으로 분류합니다.
"""

import re
from typing import Any


class ErrorClassifier:
    """에러 메시지 패턴 기반 분류기."""

    # 에러 패턴 정의 (우선순위 순)
    PATTERNS: list[dict[str, Any]] = [
        # Database Authentication Errors
        {
            "category": "DatabaseAuthenticationError",
            "patterns": [
                r"password authentication failed for user",
                r"FATAL:\s+password authentication failed",
                r"Access denied for user",
                r"authentication failed",
                r"invalid username/password",
                r"could not connect to server.*authentication",
            ],
            "severity": "high",
            "phase": "deploy",
        },
        # Database Connection Errors
        {
            "category": "DatabaseConnectionError",
            "patterns": [
                r"connection to server.*failed",
                r"could not connect to database",
                r"unable to connect to database",
                r"connection refused.*postgresql",
                r"connection refused.*mysql",
                r"connection timed out.*database",
            ],
            "severity": "high",
            "phase": "deploy",
        },
        # Kubernetes Connection Errors
        {
            "category": "KubernetesConnectionError",
            "patterns": [
                r"Unable to connect to the server",
                r"connection refused.*apiserver",
                r"dial tcp.*connection refused",
                r"context deadline exceeded",
                r"i/o timeout.*kubernetes",
            ],
            "severity": "critical",
            "phase": "deploy",
        },
        # Helm Release Errors
        {
            "category": "HelmReleaseError",
            "patterns": [
                r"Error: release.*failed",
                r"Error: INSTALLATION FAILED",
                r"Error: UPGRADE FAILED",
                r"helm.*release.*not found",
                r"another operation.*is in progress",
            ],
            "severity": "high",
            "phase": "deploy",
        },
        # Helm Chart Errors
        {
            "category": "HelmChartNotFoundError",
            "patterns": [
                r"chart.*not found",
                r"failed to download.*chart",
                r"no chart name found",
                r"repo.*not found",
            ],
            "severity": "medium",
            "phase": "prepare",
        },
        # Namespace Errors
        {
            "category": "NamespaceNotFoundError",
            "patterns": [
                r'namespaces ".*" not found',
                r"namespace.*does not exist",
                r"Error from server \(NotFound\).*namespace",
            ],
            "severity": "medium",
            "phase": "deploy",
        },
        # Resource Quota Errors
        {
            "category": "ResourceQuotaExceededError",
            "patterns": [
                r"exceeded quota",
                r"resource quota.*exceeded",
                r"insufficient.*resources",
                r"not enough resources",
            ],
            "severity": "high",
            "phase": "deploy",
        },
        # Permission Errors
        {
            "category": "PermissionDeniedError",
            "patterns": [
                r"forbidden.*User.*cannot",
                r"permission denied",
                r"access denied",
                r"unauthorized",
                r"Error from server \(Forbidden\)",
            ],
            "severity": "high",
            "phase": "deploy",
        },
        # Git Repository Errors
        {
            "category": "GitRepositoryError",
            "patterns": [
                r"fatal: repository.*not found",
                r"git clone failed",
                r"Could not resolve host.*github",
                r"Permission denied \(publickey\)",
            ],
            "severity": "medium",
            "phase": "prepare",
        },
        # Config/Validation Errors
        {
            "category": "ValidationError",
            "patterns": [
                r"validation error",
                r"invalid.*config",
                r"missing required field",
                r"pydantic.*ValidationError",
            ],
            "severity": "medium",
            "phase": "load_config",
        },
    ]

    @classmethod
    def classify(cls, error_message: str, context: str | None = None) -> dict[str, Any]:
        """에러 메시지를 분류합니다.

        Args:
            error_message: 에러 메시지 문자열
            context: 추가 컨텍스트 (옵션)

        Returns:
            분류 결과 딕셔너리:
            {
                "category": "DatabaseAuthenticationError",
                "severity": "high",
                "phase": "deploy",
                "matched_pattern": "password authentication failed",
                "is_classified": True
            }
        """
        error_text = str(error_message).lower()

        for pattern_group in cls.PATTERNS:
            for pattern in pattern_group["patterns"]:
                if re.search(pattern, error_text, re.IGNORECASE):
                    return {
                        "category": pattern_group["category"],
                        "severity": pattern_group["severity"],
                        "phase": pattern_group["phase"],
                        "matched_pattern": pattern,
                        "is_classified": True,
                        "original_error": str(error_message),
                    }

        # 분류되지 않은 에러
        return {
            "category": "UnknownError",
            "severity": "unknown",
            "phase": context or "unknown",
            "matched_pattern": None,
            "is_classified": False,
            "original_error": str(error_message),
        }

    @classmethod
    def extract_db_details(cls, error_message: str) -> dict[str, str | None]:
        """데이터베이스 에러에서 상세 정보를 추출합니다.

        Args:
            error_message: 에러 메시지

        Returns:
            {
                "db_type": "postgresql" | "mysql" | None,
                "user": "airflow_user" | None,
                "host": "postgresql.data.svc.cluster.local" | None,
                "port": "5432" | None
            }
        """
        result: dict[str, str | None] = {
            "db_type": None,
            "user": None,
            "host": None,
            "port": None,
        }

        # DB 타입 감지
        if "postgresql" in error_message.lower() or "postgres" in error_message.lower():
            result["db_type"] = "postgresql"
        elif "mysql" in error_message.lower():
            result["db_type"] = "mysql"

        # User 추출
        user_match = re.search(r"user\s+['\"]?([^'\"@\s]+)['\"]?", error_message, re.IGNORECASE)
        if user_match:
            result["user"] = user_match.group(1)

        # Host 추출
        host_match = re.search(
            r'(?:server at|host)\s+"?([^":\s]+)"?', error_message, re.IGNORECASE
        )
        if host_match:
            result["host"] = host_match.group(1)

        # Port 추출
        port_match = re.search(r"port\s+(\d+)", error_message, re.IGNORECASE)
        if port_match:
            result["port"] = port_match.group(1)

        return result

    @classmethod
    def extract_helm_details(cls, error_message: str) -> dict[str, str | None]:
        """Helm 에러에서 상세 정보를 추출합니다.

        Args:
            error_message: 에러 메시지

        Returns:
            {
                "release_name": "airflow" | None,
                "namespace": "airflow" | None,
                "chart": "apache/airflow" | None
            }
        """
        result: dict[str, str | None] = {
            "release_name": None,
            "namespace": None,
            "chart": None,
        }

        # Release name 추출
        release_match = re.search(
            r'release[:\s]+"?([^"\s]+)"?', error_message, re.IGNORECASE
        )
        if release_match:
            result["release_name"] = release_match.group(1)

        # Namespace 추출
        namespace_match = re.search(
            r'namespace[:\s]+"?([^"\s]+)"?', error_message, re.IGNORECASE
        )
        if namespace_match:
            result["namespace"] = namespace_match.group(1)

        # Chart 추출
        chart_match = re.search(r'chart[:\s]+"?([^"\s]+)"?', error_message, re.IGNORECASE)
        if chart_match:
            result["chart"] = chart_match.group(1)

        return result
