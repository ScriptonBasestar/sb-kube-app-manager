"""Integration tests for error message formatting."""

from sbkube.exceptions import (
    ConfigFileNotFoundError,
    DeploymentError,
    GitRepositoryError,
    HelmChartNotFoundError,
    KubernetesConnectionError,
    KubernetesResourceError,
    ValidationError,
    format_error_with_suggestions,
)


def test_config_file_not_found_error_formatting() -> None:
    """ConfigFileNotFoundError should show comprehensive suggestions."""
    error = ConfigFileNotFoundError(
        file_path="config.yaml", searched_paths=["./config.yaml", "../config.yaml"]
    )

    formatted = format_error_with_suggestions(error)

    # Check ERROR_GUIDE suggestions are included
    assert "💡 설정 파일을 찾을 수 없습니다" in formatted
    assert "📋 해결 방법:" in formatted
    assert "sbkube init" in formatted
    assert "🔧 유용한 명령어:" in formatted
    assert "📖 자세한 내용:" in formatted
    assert "docs/02-features/commands.md#init" in formatted
    assert "⚡ 빠른 해결:" in formatted


def test_kubernetes_connection_error_formatting() -> None:
    """KubernetesConnectionError should show comprehensive suggestions."""
    error = KubernetesConnectionError(
        context="minikube", kubeconfig="/home/user/.kube/config"
    )

    formatted = format_error_with_suggestions(error)

    # Check ERROR_GUIDE suggestions
    assert "💡 Kubernetes 클러스터에 연결할 수 없습니다" in formatted
    assert "kubectl cluster-info" in formatted
    assert "sbkube doctor" in formatted
    assert "📖 자세한 내용:" in formatted


def test_helm_chart_not_found_error_formatting() -> None:
    """HelmChartNotFoundError should show comprehensive suggestions."""
    error = HelmChartNotFoundError(chart_name="grafana", repo="grafana")

    formatted = format_error_with_suggestions(error)

    # Check ERROR_GUIDE suggestions
    assert "💡 Helm 차트를 찾을 수 없습니다" in formatted
    assert "helm search repo" in formatted
    assert "helm repo update" in formatted
    assert "sbkube validate" in formatted


def test_git_repository_error_formatting() -> None:
    """GitRepositoryError should show comprehensive suggestions."""
    error = GitRepositoryError(
        repository_url="https://github.com/user/repo.git", operation="clone"
    )

    formatted = format_error_with_suggestions(error)

    # Check ERROR_GUIDE suggestions
    assert "💡 Git 리포지토리를 클론할 수 없습니다" in formatted
    assert "git ls-remote" in formatted
    assert "인증 정보 확인" in formatted


def test_kubernetes_resource_error_formatting() -> None:
    """KubernetesResourceError can be used to test namespace issues."""
    error = KubernetesResourceError(
        resource_type="namespace", resource_name="production", operation="get"
    )

    formatted = format_error_with_suggestions(error)

    # Base error message should be included
    assert "production" in formatted


def test_validation_error_formatting() -> None:
    """ValidationError should show comprehensive suggestions."""
    error = ValidationError(
        message="Invalid configuration",
        exit_code=1,
    )

    formatted = format_error_with_suggestions(error)

    # Check ERROR_GUIDE suggestions
    assert "💡 설정 파일 검증 실패" in formatted
    assert "sbkube validate" in formatted
    assert "docs/03-configuration/config-schema.md" in formatted


def test_deployment_error_formatting() -> None:
    """DeploymentError should show comprehensive suggestions."""
    error = DeploymentError(
        message="Failed to deploy my-app to namespace default",
        exit_code=1,
    )

    formatted = format_error_with_suggestions(error)

    # Base error message should be included
    assert "Failed to deploy" in formatted


def test_error_without_guide_uses_fallback() -> None:
    """Errors without ERROR_GUIDE entry should use fallback suggestions."""
    # Create a custom error that's not in ERROR_GUIDE
    from sbkube.exceptions import SbkubeError

    class CustomError(SbkubeError):
        """Custom error for testing."""


    error = CustomError(message="Custom error message", exit_code=1)
    formatted = format_error_with_suggestions(error)

    # Should only contain the base error message (no suggestions)
    assert "Custom error message" in formatted
    # Should not contain ERROR_GUIDE formatting
    assert "💡" not in formatted or "Custom" not in formatted
