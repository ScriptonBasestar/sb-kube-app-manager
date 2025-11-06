"""Standardized exception hierarchy for sbkube.

This module provides a comprehensive exception hierarchy to ensure consistent
error handling across the entire application.
"""

import sys
from typing import Any


class SbkubeError(Exception):
    """Base exception for all sbkube errors.

    All custom exceptions in sbkube should inherit from this class.
    """

    def __init__(
        self,
        message: str,
        details: dict[str, Any] | None = None,
        exit_code: int = 1,
    ):
        super().__init__(message)
        self.message = message
        self.details = details or {}
        self.exit_code = exit_code

    def __str__(self) -> str:
        return self.message


class ConfigurationError(SbkubeError):
    """Base class for configuration-related errors."""



class ConfigFileNotFoundError(ConfigurationError):
    """Raised when a required configuration file is not found."""

    def __init__(self, file_path: str, searched_paths: list[str] | None = None) -> None:
        self.file_path = file_path
        self.searched_paths = searched_paths or []
        message = f"Configuration file not found: {file_path}"
        if searched_paths:
            message += f" (searched: {', '.join(searched_paths)})"
        super().__init__(
            message,
            {"file_path": file_path, "searched_paths": searched_paths},
        )


class ConfigValidationError(ConfigurationError):
    """Raised when configuration validation fails."""

    def __init__(
        self,
        message: str,
        field: str | None = None,
        value: Any | None = None,
    ) -> None:
        self.field = field
        self.value = value
        super().__init__(message, {"field": field, "value": value})


class SchemaValidationError(ConfigurationError):
    """Raised when schema validation fails."""

    def __init__(self, message: str, schema_errors: list[Any] | None = None) -> None:
        self.schema_errors = schema_errors or []
        super().__init__(message, {"schema_errors": schema_errors})


class ToolError(SbkubeError):
    """Base class for external tool-related errors."""



class CliToolNotFoundError(ToolError):
    """Raised when a required CLI tool is not found."""

    def __init__(self, tool_name: str, suggested_install: str | None = None) -> None:
        self.tool_name = tool_name
        self.suggested_install = suggested_install
        message = f"Required CLI tool '{tool_name}' not found"
        if suggested_install:
            message += f". Install with: {suggested_install}"
        super().__init__(
            message,
            {"tool_name": tool_name, "suggested_install": suggested_install},
        )


class CliToolExecutionError(ToolError):
    """Raised when CLI tool execution fails."""

    def __init__(
        self,
        tool_name: str,
        command: list,
        return_code: int,
        stdout: str | None = None,
        stderr: str | None = None,
    ) -> None:
        self.tool_name = tool_name
        self.command = command
        self.return_code = return_code
        self.stdout = stdout
        self.stderr = stderr

        message = f"CLI tool '{tool_name}' execution failed (exit code: {return_code})"
        if stderr:
            message += f": {stderr}"

        super().__init__(
            message,
            {
                "tool_name": tool_name,
                "command": command,
                "return_code": return_code,
                "stdout": stdout,
                "stderr": stderr,
            },
        )


class CliToolVersionError(ToolError):
    """Raised when CLI tool version requirements are not met."""

    def __init__(
        self, tool_name: str, required_version: str, found_version: str
    ) -> None:
        self.tool_name = tool_name
        self.required_version = required_version
        self.found_version = found_version
        message = f"CLI tool '{tool_name}' version {required_version} required, found {found_version}"
        super().__init__(
            message,
            {
                "tool_name": tool_name,
                "required_version": required_version,
                "found_version": found_version,
            },
        )


class KubernetesError(SbkubeError):
    """Base class for Kubernetes-related errors."""



class KubernetesConnectionError(KubernetesError):
    """Raised when connection to Kubernetes cluster fails."""

    def __init__(
        self,
        context: str | None = None,
        kubeconfig: str | None = None,
        reason: str | None = None,
    ) -> None:
        self.context = context
        self.kubeconfig = kubeconfig
        self.reason = reason
        message = "Failed to connect to Kubernetes cluster"
        if context:
            message += f" (context: {context})"
        if kubeconfig:
            message += f" (kubeconfig: {kubeconfig})"
        if reason:
            message += f": {reason}"
        details: dict[str, Any] = {"context": context, "kubeconfig": kubeconfig}
        if reason:
            details["reason"] = reason
        super().__init__(message, details)


class KubernetesResourceError(KubernetesError):
    """Raised when Kubernetes resource operations fail."""

    def __init__(
        self,
        resource_type: str,
        resource_name: str,
        operation: str,
        namespace: str | None = None,
        reason: str | None = None,
    ) -> None:
        self.resource_type = resource_type
        self.resource_name = resource_name
        self.operation = operation
        self.namespace = namespace
        self.reason = reason

        message = f"Failed to {operation} {resource_type} '{resource_name}'"
        if namespace:
            message += f" in namespace '{namespace}'"
        if reason:
            message += f": {reason}"

        super().__init__(
            message,
            {
                "resource_type": resource_type,
                "resource_name": resource_name,
                "operation": operation,
                "namespace": namespace,
                "reason": reason,
            },
        )


class HelmError(SbkubeError):
    """Base class for Helm-related errors."""



class HelmChartNotFoundError(HelmError):
    """Raised when a Helm chart is not found."""

    def __init__(
        self,
        chart_name: str,
        repo: str | None = None,
        version: str | None = None,
    ) -> None:
        self.chart_name = chart_name
        self.repo = repo
        self.version = version

        message = f"Helm chart '{chart_name}' not found"
        if repo:
            message += f" in repository '{repo}'"
        if version:
            message += f" (version: {version})"

        super().__init__(
            message,
            {"chart_name": chart_name, "repo": repo, "version": version},
        )


class HelmInstallationError(HelmError):
    """Raised when Helm installation/upgrade fails."""

    def __init__(
        self,
        release_name: str,
        chart_name: str,
        operation: str,
        namespace: str | None = None,
        reason: str | None = None,
    ) -> None:
        self.release_name = release_name
        self.chart_name = chart_name
        self.operation = operation
        self.namespace = namespace
        self.reason = reason

        message = f"Helm {operation} failed for release '{release_name}' (chart: {chart_name})"
        if namespace:
            message += f" in namespace '{namespace}'"
        if reason:
            message += f": {reason}"

        super().__init__(
            message,
            {
                "release_name": release_name,
                "chart_name": chart_name,
                "operation": operation,
                "namespace": namespace,
                "reason": reason,
            },
        )


class GitError(SbkubeError):
    """Base class for Git-related errors."""



class GitRepositoryError(GitError):
    """Raised when Git repository operations fail."""

    def __init__(
        self,
        repository_url: str,
        operation: str,
        reason: str | None = None,
    ) -> None:
        self.repository_url = repository_url
        self.operation = operation
        self.reason = reason

        message = f"Git {operation} failed for repository '{repository_url}'"
        if reason:
            message += f": {reason}"

        super().__init__(
            message,
            {
                "repository_url": repository_url,
                "operation": operation,
                "reason": reason,
            },
        )


class FileSystemError(SbkubeError):
    """Base class for file system-related errors."""



class FileOperationError(FileSystemError):
    """Raised when file operations fail."""

    def __init__(
        self, file_path: str, operation: str, reason: str | None = None
    ) -> None:
        self.file_path = file_path
        self.operation = operation
        self.reason = reason

        message = f"File {operation} failed for '{file_path}'"
        if reason:
            message += f": {reason}"

        super().__init__(
            message,
            {"file_path": file_path, "operation": operation, "reason": reason},
        )


class DirectoryNotFoundError(FileSystemError):
    """Raised when a required directory is not found."""

    def __init__(self, directory_path: str) -> None:
        self.directory_path = directory_path
        message = f"Required directory not found: {directory_path}"
        super().__init__(message, {"directory_path": directory_path})


class SecurityError(SbkubeError):
    """Base class for security-related errors."""



class PathTraversalError(SecurityError):
    """Raised when path traversal attempt is detected."""

    def __init__(self, attempted_path: str, base_path: str) -> None:
        self.attempted_path = attempted_path
        self.base_path = base_path
        message = f"Path traversal attempt detected: '{attempted_path}' outside of '{base_path}'"
        super().__init__(
            message,
            {"attempted_path": attempted_path, "base_path": base_path},
        )


class ValidationError(SbkubeError):
    """Base class for validation errors."""



class InputValidationError(ValidationError):
    """Raised when user input validation fails."""

    def __init__(self, field_name: str, value: Any, reason: str) -> None:
        self.field_name = field_name
        self.value = value
        self.reason = reason
        message = f"Invalid value for '{field_name}': {reason}"
        super().__init__(
            message,
            {"field_name": field_name, "value": value, "reason": reason},
        )


class NetworkError(SbkubeError):
    """Base class for network-related errors."""



class DownloadError(NetworkError):
    """Raised when file download fails."""

    def __init__(self, url: str, reason: str | None = None) -> None:
        self.url = url
        self.reason = reason
        message = f"Download failed for URL '{url}'"
        if reason:
            message += f": {reason}"
        super().__init__(message, {"url": url, "reason": reason})


class RepositoryConnectionError(NetworkError):
    """Raised when repository connection fails."""

    def __init__(
        self,
        repository_url: str,
        repository_type: str,
        reason: str | None = None,
    ) -> None:
        self.repository_url = repository_url
        self.repository_type = repository_type
        self.reason = reason
        message = (
            f"Failed to connect to {repository_type} repository '{repository_url}'"
        )
        if reason:
            message += f": {reason}"
        super().__init__(
            message,
            {
                "repository_url": repository_url,
                "repository_type": repository_type,
                "reason": reason,
            },
        )


class StateError(SbkubeError):
    """Base class for state management errors."""



class StateCorruptionError(StateError):
    """Raised when state corruption is detected."""

    def __init__(self, state_file: str, reason: str | None = None) -> None:
        self.state_file = state_file
        self.reason = reason
        message = f"State corruption detected in '{state_file}'"
        if reason:
            message += f": {reason}"
        super().__init__(message, {"state_file": state_file, "reason": reason})


class DeploymentError(SbkubeError):
    """Base class for deployment-related errors."""



class RollbackError(SbkubeError):
    """Base class for rollback-related errors."""



def handle_exception(exc: Exception, logger=None) -> int:
    """Centralized exception handler for sbkube.

    Args:
        exc: The exception to handle
        logger: Optional logger instance for logging

    Returns:
        int: Exit code for the application

    """
    if isinstance(exc, SbkubeError):
        if logger:
            logger.error(str(exc))
            if exc.details:
                logger.verbose(f"Error details: {exc.details}")
        else:
            print(f"Error: {exc}", file=sys.stderr)
        return exc.exit_code
    # Handle unexpected exceptions
    if logger:
        logger.error(f"Unexpected error: {exc}")
    else:
        print(f"Unexpected error: {exc}", file=sys.stderr)
    return 1


def format_error_with_suggestions(exc: SbkubeError) -> str:
    """Format error with helpful suggestions based on error type.

    Args:
        exc: The SbkubeError to format

    Returns:
        str: Formatted error message with suggestions

    """
    from sbkube.utils.error_suggestions import format_suggestions

    message = str(exc)

    # Try to get suggestions from ERROR_GUIDE database first
    error_type = type(exc).__name__
    suggestions = format_suggestions(error_type)

    if suggestions:
        # Use comprehensive suggestions from ERROR_GUIDE
        message += suggestions
    # Fallback to legacy inline suggestions for backward compatibility
    elif isinstance(exc, CliToolNotFoundError):
        message += f"\n💡 Install {exc.tool_name}:"
        if exc.suggested_install:
            message += f"\n   {exc.suggested_install}"
        else:
            message += f"\n   Please check the official documentation for {exc.tool_name} installation"

    elif isinstance(exc, ConfigFileNotFoundError):
        message += f"\n💡 Expected configuration file at: {exc.file_path}"
        if exc.searched_paths:
            message += f"\n   Searched paths: {', '.join(exc.searched_paths)}"
        message += "\n   Create the configuration file or check the path"

    elif isinstance(exc, KubernetesConnectionError):
        message += "\n💡 Check your Kubernetes connection:"
        message += "\n   kubectl config current-context"
        message += "\n   kubectl cluster-info"
        if exc.kubeconfig:
            message += f"\n   Verify kubeconfig file: {exc.kubeconfig}"

    elif isinstance(exc, HelmChartNotFoundError):
        message += "\n💡 Check chart availability:"
        message += "\n   helm search repo <chart_name>"
        message += "\n   helm repo update"
        if exc.repo:
            message += f"\n   helm repo list (verify {exc.repo} is added)"

    elif isinstance(exc, GitRepositoryError):
        message += "\n💡 Check repository access:"
        message += f"\n   git ls-remote {exc.repository_url}"
        message += "\n   Verify repository URL and credentials"

    return message
