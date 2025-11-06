"""Tests for the standardized exception hierarchy.
"""

from sbkube.exceptions import (
    CliToolExecutionError,
    CliToolNotFoundError,
    ConfigFileNotFoundError,
    ConfigurationError,
    ConfigValidationError,
    FileSystemError,
    GitError,
    HelmError,
    KubernetesError,
    PathTraversalError,
    SbkubeError,
    SecurityError,
    format_error_with_suggestions,
    handle_exception,
)


class TestSbkubeExceptionHierarchy:
    """Test the exception hierarchy structure."""

    def test_base_exception(self):
        """Test SbkubeError base exception."""
        exc = SbkubeError("Test error", {"key": "value"}, 42)
        assert str(exc) == "Test error"
        assert exc.message == "Test error"
        assert exc.details == {"key": "value"}
        assert exc.exit_code == 42

    def test_configuration_errors(self):
        """Test configuration-related exceptions."""
        # Test ConfigFileNotFoundError
        exc = ConfigFileNotFoundError("config.yaml", ["./config.yaml", "./config.yml"])
        assert isinstance(exc, ConfigurationError)
        assert isinstance(exc, SbkubeError)
        assert exc.file_path == "config.yaml"
        assert exc.searched_paths == ["./config.yaml", "./config.yml"]

        # Test ConfigValidationError
        exc = ConfigValidationError("Invalid value", "field_name", "invalid_value")
        assert isinstance(exc, ConfigurationError)
        assert exc.field == "field_name"
        assert exc.value == "invalid_value"

    def test_tool_errors(self):
        """Test CLI tool-related exceptions."""
        # Test CliToolNotFoundError
        exc = CliToolNotFoundError("helm", "https://helm.sh/install")
        assert exc.tool_name == "helm"
        assert exc.suggested_install == "https://helm.sh/install"

        # Test CliToolExecutionError
        exc = CliToolExecutionError(
            "kubectl", ["kubectl", "version"], 1, "stdout", "stderr"
        )
        assert exc.tool_name == "kubectl"
        assert exc.command == ["kubectl", "version"]
        assert exc.return_code == 1
        assert exc.stdout == "stdout"
        assert exc.stderr == "stderr"

    def test_kubernetes_errors(self):
        """Test Kubernetes-related exceptions."""
        exc = KubernetesError("Test kubernetes error")
        assert isinstance(exc, SbkubeError)

    def test_helm_errors(self):
        """Test Helm-related exceptions."""
        exc = HelmError("Test helm error")
        assert isinstance(exc, SbkubeError)

    def test_git_errors(self):
        """Test Git-related exceptions."""
        exc = GitError("Test git error")
        assert isinstance(exc, SbkubeError)

    def test_filesystem_errors(self):
        """Test file system-related exceptions."""
        exc = FileSystemError("Test filesystem error")
        assert isinstance(exc, SbkubeError)

    def test_security_errors(self):
        """Test security-related exceptions."""
        exc = PathTraversalError("/malicious/../../etc/passwd", "/safe/base")
        assert isinstance(exc, SecurityError)
        assert isinstance(exc, SbkubeError)
        assert exc.attempted_path == "/malicious/../../etc/passwd"
        assert exc.base_path == "/safe/base"


class TestExceptionHandlers:
    """Test exception handling utilities."""

    def test_handle_exception_with_sbkube_error(self):
        """Test handle_exception with SbkubeError."""
        exc = SbkubeError("Test error", exit_code=42)
        exit_code = handle_exception(exc)
        assert exit_code == 42

    def test_handle_exception_with_standard_error(self):
        """Test handle_exception with standard Exception."""
        exc = ValueError("Test error")
        exit_code = handle_exception(exc)
        assert exit_code == 1

    def test_format_error_with_suggestions_cli_tool_not_found(self):
        """Test error formatting for CliToolNotFoundError."""
        exc = CliToolNotFoundError("helm", "brew install helm")
        formatted = format_error_with_suggestions(exc)
        assert "helm" in formatted
        assert "💡 Install helm:" in formatted
        assert "brew install helm" in formatted

    def test_format_error_with_suggestions_config_file_not_found(self):
        """Test error formatting for ConfigFileNotFoundError."""
        exc = ConfigFileNotFoundError("config.yaml", ["./config.yaml", "./config.yml"])
        formatted = format_error_with_suggestions(exc)
        assert "config.yaml" in formatted
        assert "💡 Expected configuration file" in formatted
        assert "./config.yaml" in formatted

    def test_format_error_with_suggestions_generic(self):
        """Test error formatting for generic SbkubeError."""
        exc = SbkubeError("Generic error")
        formatted = format_error_with_suggestions(exc)
        assert formatted == "Generic error"


class TestExceptionIntegration:
    """Integration tests for exception handling."""

    def test_exception_hierarchy_consistency(self):
        """Test that all custom exceptions inherit from SbkubeError."""
        exceptions_to_test = [
            ConfigurationError("test"),
            ConfigFileNotFoundError("test"),
            ConfigValidationError("test"),
            CliToolNotFoundError("test"),
            CliToolExecutionError("test", [], 1),
            KubernetesError("test"),
            HelmError("test"),
            GitError("test"),
            FileSystemError("test"),
            SecurityError("test"),
            PathTraversalError("test", "test"),
        ]

        for exc in exceptions_to_test:
            assert isinstance(exc, SbkubeError), (
                f"{type(exc).__name__} should inherit from SbkubeError"
            )

    def test_exception_details_preservation(self):
        """Test that exception details are preserved correctly."""
        details = {"operation": "test", "file": "test.yaml"}
        exc = SbkubeError("Test error", details, 5)

        assert exc.details == details
        assert exc.exit_code == 5
        assert str(exc) == "Test error"
