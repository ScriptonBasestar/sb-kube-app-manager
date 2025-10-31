"""
Retry mechanisms for network operations and external command execution.

This module provides decorators and utilities for retrying operations that may
fail due to transient network issues or temporary unavailability of external services.
"""

import random
import subprocess
import time
from collections.abc import Callable
from functools import wraps
from typing import Any

from sbkube.exceptions import (CliToolExecutionError, GitRepositoryError,
                               HelmError, NetworkError,
                               RepositoryConnectionError)
from sbkube.utils.logger import logger


class RetryConfig:
    """Configuration for retry behavior."""

    def __init__(
        self,
        max_attempts: int = 3,
        base_delay: float = 1.0,
        max_delay: float = 60.0,
        exponential_base: float = 2.0,
        jitter: bool = True,
        retryable_exceptions: list[type[Exception]] | None = None,
    ):
        """
        Initialize retry configuration.

        Args:
            max_attempts: Maximum number of retry attempts
            base_delay: Initial delay between retries in seconds
            max_delay: Maximum delay between retries in seconds
            exponential_base: Base for exponential backoff
            jitter: Whether to add random jitter to delays
            retryable_exceptions: List of exception types that should trigger retries
        """
        self.max_attempts = max_attempts
        self.base_delay = base_delay
        self.max_delay = max_delay
        self.exponential_base = exponential_base
        self.jitter = jitter
        self.retryable_exceptions = retryable_exceptions or [
            NetworkError,
            RepositoryConnectionError,
            CliToolExecutionError,
            subprocess.CalledProcessError,
            subprocess.TimeoutExpired,
            ConnectionError,
            OSError,
        ]


def calculate_delay(attempt: int, config: RetryConfig) -> float:
    """
    Calculate delay for the given attempt number.

    Args:
        attempt: Current attempt number (0-based)
        config: Retry configuration

    Returns:
        float: Delay in seconds
    """
    # Exponential backoff
    delay = config.base_delay * (config.exponential_base**attempt)

    # Cap at max_delay
    delay = min(delay, config.max_delay)

    # Add jitter if enabled
    if config.jitter and delay > 0:
        jitter_range = delay * 0.1  # 10% jitter
        delay += random.uniform(-jitter_range, jitter_range)
        delay = max(0, delay)  # Ensure non-negative

    return delay


def is_retryable_exception(exc: Exception, config: RetryConfig) -> bool:
    """
    Check if an exception is retryable based on configuration.

    Args:
        exc: The exception to check
        config: Retry configuration

    Returns:
        bool: True if the exception should trigger a retry
    """
    # Check if exception type is in retryable list
    for exc_type in config.retryable_exceptions:
        if isinstance(exc, exc_type):
            # Additional checks for specific exception types
            if isinstance(exc, subprocess.CalledProcessError):
                # Don't retry on certain exit codes that indicate permanent failures
                non_retryable_codes = [127, 126]  # Command not found, permission denied
                if exc.returncode in non_retryable_codes:
                    return False
                # Don't retry on authentication failures
                if exc.stderr and any(
                    keyword in exc.stderr.lower()
                    for keyword in [
                        "authentication failed",
                        "permission denied",
                        "unauthorized",
                        "forbidden",
                    ]
                ):
                    return False
            return True

    return False


def retry_operation(config: RetryConfig | None = None):
    """
    Decorator for retrying operations with configurable behavior.

    Args:
        config: Retry configuration. If None, uses default configuration.

    Returns:
        Decorated function with retry behavior
    """
    if config is None:
        config = RetryConfig()

    def decorator(func: Callable) -> Callable:
        @wraps(func)
        def wrapper(*args, **kwargs) -> Any:
            last_exception = None

            for attempt in range(config.max_attempts):
                try:
                    return func(*args, **kwargs)
                except Exception as exc:
                    last_exception = exc

                    # Check if we should retry this exception
                    if not is_retryable_exception(exc, config):
                        logger.debug(
                            f"Non-retryable exception encountered: {type(exc).__name__}",
                        )
                        raise exc

                    # Don't retry on the last attempt
                    if attempt == config.max_attempts - 1:
                        logger.error(
                            f"Operation failed after {config.max_attempts} attempts",
                        )
                        break

                    # Calculate delay and wait
                    delay = calculate_delay(attempt, config)
                    logger.warning(
                        f"Operation failed (attempt {attempt + 1}/{config.max_attempts}): {exc}. "
                        f"Retrying in {delay:.1f} seconds...",
                    )
                    time.sleep(delay)

            # If we get here, all attempts failed
            raise last_exception

        return wrapper

    return decorator


# Predefined retry configurations for common scenarios

NETWORK_RETRY_CONFIG = RetryConfig(
    max_attempts=3,
    base_delay=2.0,
    max_delay=30.0,
    exponential_base=2.0,
    jitter=True,
)

HELM_RETRY_CONFIG = RetryConfig(
    max_attempts=3,
    base_delay=1.0,
    max_delay=15.0,
    exponential_base=1.5,
    jitter=True,
    retryable_exceptions=[
        subprocess.CalledProcessError,
        subprocess.TimeoutExpired,
        RepositoryConnectionError,
        HelmError,
        ConnectionError,
        OSError,
    ],
)

GIT_RETRY_CONFIG = RetryConfig(
    max_attempts=3,
    base_delay=2.0,
    max_delay=20.0,
    exponential_base=2.0,
    jitter=True,
    retryable_exceptions=[
        subprocess.CalledProcessError,
        subprocess.TimeoutExpired,
        GitRepositoryError,
        ConnectionError,
        OSError,
    ],
)


def retry_network_operation(func: Callable) -> Callable:
    """Decorator for network operations with default retry configuration."""
    return retry_operation(NETWORK_RETRY_CONFIG)(func)


def retry_helm_operation(func: Callable) -> Callable:
    """Decorator for Helm operations with appropriate retry configuration."""
    return retry_operation(HELM_RETRY_CONFIG)(func)


def retry_git_operation(func: Callable) -> Callable:
    """Decorator for Git operations with appropriate retry configuration."""
    return retry_operation(GIT_RETRY_CONFIG)(func)


def run_command_with_retry(
    cmd: list[str],
    config: RetryConfig | None = None,
    **subprocess_kwargs,
) -> subprocess.CompletedProcess:
    """
    Run a subprocess command with retry logic.

    Args:
        cmd: Command and arguments as list
        config: Retry configuration. If None, uses NETWORK_RETRY_CONFIG
        **subprocess_kwargs: Additional arguments for subprocess.run

    Returns:
        subprocess.CompletedProcess: The completed process result

    Raises:
        subprocess.CalledProcessError: If command fails after all retries
        subprocess.TimeoutExpired: If command times out after all retries
    """
    if config is None:
        config = NETWORK_RETRY_CONFIG

    # Set default subprocess arguments
    subprocess_defaults = {
        "check": True,
        "capture_output": True,
        "text": True,
        "timeout": 300,  # 5 minutes default timeout
    }
    subprocess_defaults.update(subprocess_kwargs)

    @retry_operation(config)
    def _run_command():
        logger.command(" ".join(cmd))
        result = subprocess.run(cmd, **subprocess_defaults)
        if result.stdout:
            logger.verbose(f"STDOUT: {result.stdout.strip()}")
        if result.stderr:
            logger.verbose(f"STDERR: {result.stderr.strip()}")
        return result

    return _run_command()


def run_helm_command_with_retry(
    cmd: list[str],
    **kwargs,
) -> subprocess.CompletedProcess:
    """Run a Helm command with appropriate retry configuration."""
    return run_command_with_retry(cmd, HELM_RETRY_CONFIG, **kwargs)


def run_git_command_with_retry(cmd: list[str], **kwargs) -> subprocess.CompletedProcess:
    """Run a Git command with appropriate retry configuration."""
    return run_command_with_retry(cmd, GIT_RETRY_CONFIG, **kwargs)


class RetryContext:
    """Context manager for retry operations with custom configuration."""

    def __init__(self, config: RetryConfig):
        self.config = config
        self.attempt = 0
        self.last_exception = None

    def __enter__(self):
        return self

    def __exit__(self, exc_type, exc_val, exc_tb):
        if exc_val is None:
            return False  # No exception, continue normally

        self.last_exception = exc_val

        # Check if we should retry
        if not is_retryable_exception(exc_val, self.config):
            return False  # Don't suppress exception, let it propagate

        # Check if we've exhausted attempts
        if self.attempt >= self.config.max_attempts - 1:
            return False  # Don't suppress exception, let it propagate

        # Calculate delay and wait
        delay = calculate_delay(self.attempt, self.config)
        logger.warning(
            f"Operation failed (attempt {self.attempt + 1}/{self.config.max_attempts}): {exc_val}. "
            f"Retrying in {delay:.1f} seconds...",
        )
        time.sleep(delay)
        self.attempt += 1

        return True  # Suppress exception, retry the operation

    def should_continue(self) -> bool:
        """Check if we should continue retrying."""
        return self.attempt < self.config.max_attempts
