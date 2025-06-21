"""
Tests for the retry mechanisms and network operations.
"""

import time
import subprocess
from unittest.mock import Mock, patch, MagicMock
import pytest
from sbkube.utils.retry import (
    RetryConfig,
    retry_operation,
    retry_network_operation,
    retry_helm_operation,
    retry_git_operation,
    calculate_delay,
    is_retryable_exception,
    run_command_with_retry,
    run_helm_command_with_retry,
    run_git_command_with_retry,
    NETWORK_RETRY_CONFIG,
    HELM_RETRY_CONFIG,
    GIT_RETRY_CONFIG
)
from sbkube.exceptions import (
    NetworkError,
    RepositoryConnectionError,
    CliToolExecutionError,
    GitRepositoryError,
    HelmError
)


class TestRetryConfig:
    """Test RetryConfig class and related utilities."""
    
    def test_retry_config_defaults(self):
        """Test default RetryConfig values."""
        config = RetryConfig()
        assert config.max_attempts == 3
        assert config.base_delay == 1.0
        assert config.max_delay == 60.0
        assert config.exponential_base == 2.0
        assert config.jitter is True
        assert len(config.retryable_exceptions) > 0
    
    def test_retry_config_custom(self):
        """Test custom RetryConfig values."""
        config = RetryConfig(
            max_attempts=5,
            base_delay=0.5,
            max_delay=30.0,
            exponential_base=1.5,
            jitter=False,
            retryable_exceptions=[NetworkError]
        )
        assert config.max_attempts == 5
        assert config.base_delay == 0.5
        assert config.max_delay == 30.0
        assert config.exponential_base == 1.5
        assert config.jitter is False
        assert config.retryable_exceptions == [NetworkError]


class TestDelayCalculation:
    """Test delay calculation functions."""
    
    def test_calculate_delay_exponential(self):
        """Test exponential backoff delay calculation."""
        config = RetryConfig(base_delay=1.0, exponential_base=2.0, jitter=False)
        
        assert calculate_delay(0, config) == 1.0
        assert calculate_delay(1, config) == 2.0
        assert calculate_delay(2, config) == 4.0
        assert calculate_delay(3, config) == 8.0
    
    def test_calculate_delay_max_cap(self):
        """Test delay is capped at max_delay."""
        config = RetryConfig(base_delay=1.0, exponential_base=2.0, max_delay=5.0, jitter=False)
        
        assert calculate_delay(0, config) == 1.0
        assert calculate_delay(1, config) == 2.0
        assert calculate_delay(2, config) == 4.0
        assert calculate_delay(3, config) == 5.0  # Capped at max_delay
        assert calculate_delay(4, config) == 5.0  # Still capped
    
    def test_calculate_delay_with_jitter(self):
        """Test delay calculation with jitter."""
        config = RetryConfig(base_delay=10.0, exponential_base=1.0, jitter=True)
        
        # With jitter, delay should be within 10% of base delay
        delay = calculate_delay(0, config)
        assert 9.0 <= delay <= 11.0


class TestRetryableExceptions:
    """Test exception classification for retries."""
    
    def test_retryable_network_exceptions(self):
        """Test that network exceptions are retryable."""
        config = RetryConfig()
        
        assert is_retryable_exception(NetworkError("test"), config)
        assert is_retryable_exception(RepositoryConnectionError("test", "git"), config)
        assert is_retryable_exception(ConnectionError("test"), config)
        assert is_retryable_exception(OSError("test"), config)
    
    def test_retryable_subprocess_exceptions(self):
        """Test subprocess exception retry logic."""
        config = RetryConfig()
        
        # Retryable subprocess errors
        retryable_error = subprocess.CalledProcessError(1, ['test'], stderr="network error")
        assert is_retryable_exception(retryable_error, config)
        
        # Non-retryable exit codes
        non_retryable_error = subprocess.CalledProcessError(127, ['test'])  # Command not found
        assert not is_retryable_exception(non_retryable_error, config)
        
        # Non-retryable authentication failures
        auth_error = subprocess.CalledProcessError(1, ['test'], stderr="authentication failed")
        assert not is_retryable_exception(auth_error, config)
    
    def test_non_retryable_exceptions(self):
        """Test that certain exceptions are not retryable."""
        config = RetryConfig()
        
        assert not is_retryable_exception(ValueError("test"), config)
        assert not is_retryable_exception(TypeError("test"), config)
        assert not is_retryable_exception(KeyError("test"), config)


class TestRetryDecorator:
    """Test retry decorator functionality."""
    
    def test_retry_decorator_success_first_attempt(self):
        """Test retry decorator when function succeeds on first attempt."""
        config = RetryConfig(max_attempts=3)
        
        @retry_operation(config)
        def successful_function():
            return "success"
        
        result = successful_function()
        assert result == "success"
    
    def test_retry_decorator_success_after_retries(self):
        """Test retry decorator when function succeeds after retries."""
        config = RetryConfig(max_attempts=3, base_delay=0.01)  # Very short delay for testing
        attempt_count = 0
        
        @retry_operation(config)
        def eventually_successful_function():
            nonlocal attempt_count
            attempt_count += 1
            if attempt_count < 3:
                raise NetworkError("temporary failure")
            return "success"
        
        result = eventually_successful_function()
        assert result == "success"
        assert attempt_count == 3
    
    def test_retry_decorator_exhausts_attempts(self):
        """Test retry decorator when all attempts are exhausted."""
        config = RetryConfig(max_attempts=2, base_delay=0.01)
        
        @retry_operation(config)
        def always_failing_function():
            raise NetworkError("persistent failure")
        
        with pytest.raises(NetworkError, match="persistent failure"):
            always_failing_function()
    
    def test_retry_decorator_non_retryable_exception(self):
        """Test retry decorator with non-retryable exception."""
        config = RetryConfig(max_attempts=3)
        
        @retry_operation(config)
        def function_with_non_retryable_error():
            raise ValueError("non-retryable error")
        
        with pytest.raises(ValueError, match="non-retryable error"):
            function_with_non_retryable_error()


class TestPredefinedDecorators:
    """Test predefined retry decorators."""
    
    def test_network_retry_decorator(self):
        """Test network retry decorator."""
        attempt_count = 0
        
        @retry_network_operation
        def network_function():
            nonlocal attempt_count
            attempt_count += 1
            if attempt_count < 2:
                raise ConnectionError("network issue")
            return "connected"
        
        result = network_function()
        assert result == "connected"
        assert attempt_count == 2
    
    def test_helm_retry_decorator(self):
        """Test Helm retry decorator."""
        attempt_count = 0
        
        @retry_helm_operation
        def helm_function():
            nonlocal attempt_count
            attempt_count += 1
            if attempt_count < 2:
                raise subprocess.CalledProcessError(1, ['helm'], stderr="temporary error")
            return "helm success"
        
        result = helm_function()
        assert result == "helm success"
        assert attempt_count == 2
    
    def test_git_retry_decorator(self):
        """Test Git retry decorator."""
        attempt_count = 0
        
        @retry_git_operation
        def git_function():
            nonlocal attempt_count
            attempt_count += 1
            if attempt_count < 2:
                raise GitRepositoryError("test-repo", "clone", "temporary error")
            return "git success"
        
        result = git_function()
        assert result == "git success"
        assert attempt_count == 2


class TestCommandRetry:
    """Test command execution with retry."""
    
    @patch('subprocess.run')
    def test_run_command_with_retry_success(self, mock_run):
        """Test successful command execution with retry."""
        mock_result = Mock()
        mock_result.stdout = "success output"
        mock_result.stderr = ""
        mock_run.return_value = mock_result
        
        result = run_command_with_retry(['echo', 'test'])
        assert result == mock_result
        mock_run.assert_called_once()
    
    @patch('subprocess.run')
    @patch('time.sleep')  # Mock sleep to speed up test
    def test_run_command_with_retry_eventual_success(self, mock_sleep, mock_run):
        """Test command execution that succeeds after retries."""
        # First call fails, second succeeds
        mock_run.side_effect = [
            subprocess.CalledProcessError(1, ['test'], stderr="network error"),
            Mock(stdout="success", stderr="")
        ]
        
        result = run_command_with_retry(['test', 'command'])
        assert result.stdout == "success"
        assert mock_run.call_count == 2
        mock_sleep.assert_called_once()
    
    @patch('subprocess.run')
    @patch('time.sleep')
    def test_run_command_with_retry_exhausted(self, mock_sleep, mock_run):
        """Test command execution that fails after all retries."""
        mock_run.side_effect = subprocess.CalledProcessError(1, ['test'], stderr="persistent error")
        
        with pytest.raises(subprocess.CalledProcessError):
            run_command_with_retry(['test', 'command'])
        
        # Should retry the configured number of times
        assert mock_run.call_count == NETWORK_RETRY_CONFIG.max_attempts
    
    @patch('subprocess.run')
    def test_run_helm_command_with_retry(self, mock_run):
        """Test Helm command execution with retry."""
        mock_result = Mock()
        mock_result.stdout = "helm output"
        mock_result.stderr = ""
        mock_run.return_value = mock_result
        
        result = run_helm_command_with_retry(['helm', 'version'])
        assert result == mock_result
        mock_run.assert_called_once()
    
    @patch('subprocess.run')
    def test_run_git_command_with_retry(self, mock_run):
        """Test Git command execution with retry."""
        mock_result = Mock()
        mock_result.stdout = "git output"
        mock_result.stderr = ""
        mock_run.return_value = mock_result
        
        result = run_git_command_with_retry(['git', 'status'])
        assert result == mock_result
        mock_run.assert_called_once()


class TestRetryConfigurations:
    """Test predefined retry configurations."""
    
    def test_network_retry_config(self):
        """Test network retry configuration."""
        assert NETWORK_RETRY_CONFIG.max_attempts == 3
        assert NETWORK_RETRY_CONFIG.base_delay == 2.0
        assert NETWORK_RETRY_CONFIG.max_delay == 30.0
        assert NETWORK_RETRY_CONFIG.jitter is True
    
    def test_helm_retry_config(self):
        """Test Helm retry configuration."""
        assert HELM_RETRY_CONFIG.max_attempts == 3
        assert HELM_RETRY_CONFIG.base_delay == 1.0
        assert HELM_RETRY_CONFIG.max_delay == 15.0
        assert HELM_RETRY_CONFIG.exponential_base == 1.5
    
    def test_git_retry_config(self):
        """Test Git retry configuration."""
        assert GIT_RETRY_CONFIG.max_attempts == 3
        assert GIT_RETRY_CONFIG.base_delay == 2.0
        assert GIT_RETRY_CONFIG.max_delay == 20.0
        assert GIT_RETRY_CONFIG.exponential_base == 2.0


class TestIntegration:
    """Integration tests for retry functionality."""
    
    @patch('subprocess.run')
    @patch('time.sleep')
    def test_network_operation_with_intermittent_failure(self, mock_sleep, mock_run):
        """Test realistic scenario with intermittent network failures."""
        # Simulate network failure followed by success
        mock_run.side_effect = [
            subprocess.CalledProcessError(1, ['curl'], stderr="connection timeout"),
            subprocess.CalledProcessError(1, ['curl'], stderr="connection refused"),
            Mock(stdout="success", stderr="")
        ]
        
        @retry_network_operation
        def network_download():
            return subprocess.run(['curl', 'https://example.com'], check=True, capture_output=True, text=True)
        
        result = network_download()
        assert result.stdout == "success"
        assert mock_run.call_count == 3
        assert mock_sleep.call_count == 2  # Two retries
    
    def test_retry_with_context_manager(self):
        """Test retry functionality using context manager approach."""
        from sbkube.utils.retry import RetryContext, RetryConfig
        
        attempt_count = 0
        config = RetryConfig(max_attempts=3, base_delay=0.01)
        
        while True:
            with RetryContext(config) as retry_ctx:
                attempt_count += 1
                if attempt_count < 3:
                    raise NetworkError("temporary failure")
                break  # Success on third attempt
        
        assert attempt_count == 3