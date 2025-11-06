import subprocess
from pathlib import Path

from sbkube.exceptions import CliToolExecutionError, CliToolNotFoundError
from sbkube.utils.logger import logger
from sbkube.utils.retry import (
    NETWORK_RETRY_CONFIG,
    run_command_with_retry,
    run_git_command_with_retry,
    run_helm_command_with_retry,
)


def run_cmd_with_logging(
    cmd: list,
    timeout: int = 300,
    cwd: Path | None = None,
) -> bool:
    """Run command with logging and structured error handling.

    Args:
        cmd: Command and arguments as list
        timeout: Command timeout in seconds
        cwd: Working directory for command execution

    Returns:
        bool: True if command succeeded, False otherwise

    Raises:
        CliToolExecutionError: When command execution fails
        CliToolNotFoundError: When command tool is not found

    """
    logger.command(" ".join(map(str, cmd)))

    if not cmd:
        msg = "Command cannot be empty"
        raise ValueError(msg)

    tool_name = cmd[0]

    try:
        result = subprocess.run(
            cmd,
            capture_output=True,
            text=True,
            check=True,
            timeout=timeout,
            cwd=str(cwd) if cwd else None,
        )

        if result.stdout:
            logger.verbose(f"STDOUT: {result.stdout.strip()}")
        if result.stderr:
            logger.verbose(f"STDERR: {result.stderr.strip()}")
        return True

    except FileNotFoundError:
        logger.error(f"Command '{tool_name}' not found")
        raise CliToolNotFoundError(tool_name)

    except subprocess.CalledProcessError as e:
        error_msg = (
            e.stderr.strip() if e.stderr else e.stdout.strip() if e.stdout else str(e)
        )
        logger.error(f"명령 실행 실패: {error_msg}")
        raise CliToolExecutionError(tool_name, cmd, e.returncode, e.stdout, e.stderr)

    except subprocess.TimeoutExpired as e:
        logger.error(f"명령 실행 시간 초과 ({timeout}초)")
        raise CliToolExecutionError(
            tool_name,
            cmd,
            -1,
            e.stdout.decode() if e.stdout else None,
            (
                e.stderr.decode()
                if e.stderr
                else f"Command timed out after {timeout} seconds"
            ),
        )

    except Exception as e:
        logger.error(f"예기치 못한 오류: {e}")
        raise CliToolExecutionError(tool_name, cmd, -1, None, str(e))


def run_cmd_safely(cmd: list, timeout: int = 300, cwd: Path | None = None) -> bool:
    """Run command safely without raising exceptions.

    This is a wrapper around run_cmd_with_logging that catches exceptions
    and returns False instead of raising them.

    Args:
        cmd: Command and arguments as list
        timeout: Command timeout in seconds
        cwd: Working directory for command execution

    Returns:
        bool: True if command succeeded, False otherwise

    """
    try:
        return run_cmd_with_logging(cmd, timeout, cwd)
    except (CliToolExecutionError, CliToolNotFoundError):
        return False


def run_network_cmd_with_retry(
    cmd: list[str],
    timeout: int = 300,
    cwd: Path | None = None,
    max_attempts: int = 3,
) -> bool:
    """Run network-related command with retry mechanism.

    This function is specifically designed for commands that involve network
    operations and may fail due to transient network issues.

    Args:
        cmd: Command and arguments as list
        timeout: Command timeout in seconds
        cwd: Working directory for command execution
        max_attempts: Maximum number of retry attempts

    Returns:
        bool: True if command succeeded, False otherwise

    Raises:
        CliToolExecutionError: When command execution fails after all retries
        CliToolNotFoundError: When command tool is not found

    """
    if not cmd:
        msg = "Command cannot be empty"
        raise ValueError(msg)

    tool_name = cmd[0]

    try:
        from sbkube.utils.retry import RetryConfig

        custom_config = RetryConfig(
            max_attempts=max_attempts,
            base_delay=NETWORK_RETRY_CONFIG.base_delay,
            max_delay=NETWORK_RETRY_CONFIG.max_delay,
            exponential_base=NETWORK_RETRY_CONFIG.exponential_base,
            jitter=NETWORK_RETRY_CONFIG.jitter,
            retryable_exceptions=NETWORK_RETRY_CONFIG.retryable_exceptions,
        )
        run_command_with_retry(
            cmd,
            config=custom_config,
            timeout=timeout,
            cwd=str(cwd) if cwd else None,
        )
        return True

    except FileNotFoundError:
        logger.error(f"Command '{tool_name}' not found")
        raise CliToolNotFoundError(tool_name)

    except subprocess.CalledProcessError as e:
        error_msg = (
            e.stderr.strip() if e.stderr else e.stdout.strip() if e.stdout else str(e)
        )
        logger.error(f"명령 실행 실패 (모든 재시도 후): {error_msg}")
        raise CliToolExecutionError(tool_name, cmd, e.returncode, e.stdout, e.stderr)

    except subprocess.TimeoutExpired as e:
        logger.error(f"명령 실행 시간 초과 (모든 재시도 후): {timeout}초")
        raise CliToolExecutionError(
            tool_name,
            cmd,
            -1,
            e.stdout.decode() if e.stdout else None,
            (
                e.stderr.decode()
                if e.stderr
                else f"Command timed out after {timeout} seconds"
            ),
        )

    except Exception as e:
        logger.error(f"예기치 못한 오류 (모든 재시도 후): {e}")
        raise CliToolExecutionError(tool_name, cmd, -1, None, str(e))


def run_helm_cmd_with_retry(
    cmd: list[str],
    timeout: int = 300,
    cwd: Path | None = None,
) -> bool:
    """Run Helm command with appropriate retry configuration.

    Args:
        cmd: Command and arguments as list (should start with 'helm')
        timeout: Command timeout in seconds
        cwd: Working directory for command execution

    Returns:
        bool: True if command succeeded, False otherwise

    """
    try:
        run_helm_command_with_retry(cmd, timeout=timeout, cwd=str(cwd) if cwd else None)
        return True
    except Exception as e:
        logger.error(f"Helm command failed after retries: {e}")
        return False


def run_git_cmd_with_retry(
    cmd: list[str],
    timeout: int = 300,
    cwd: Path | None = None,
) -> bool:
    """Run Git command with appropriate retry configuration.

    Args:
        cmd: Command and arguments as list (should start with 'git')
        timeout: Command timeout in seconds
        cwd: Working directory for command execution

    Returns:
        bool: True if command succeeded, False otherwise

    """
    try:
        run_git_command_with_retry(cmd, timeout=timeout, cwd=str(cwd) if cwd else None)
        return True
    except Exception as e:
        logger.error(f"Git command failed after retries: {e}")
        return False
