import subprocess
from pathlib import Path
from typing import Optional
from sbkube.utils.logger import logger
from sbkube.exceptions import CliToolExecutionError, CliToolNotFoundError


def run_cmd_with_logging(cmd: list, timeout: int = 300, cwd: Optional[Path] = None) -> bool:
    """
    Run command with logging and structured error handling.
    
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
        raise ValueError("Command cannot be empty")
    
    tool_name = cmd[0]
    
    try:
        result = subprocess.run(
            cmd, 
            capture_output=True, 
            text=True, 
            check=True, 
            timeout=timeout, 
            cwd=str(cwd) if cwd else None
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
        error_msg = e.stderr.strip() if e.stderr else e.stdout.strip() if e.stdout else str(e)
        logger.error(f"명령 실행 실패: {error_msg}")
        raise CliToolExecutionError(tool_name, cmd, e.returncode, e.stdout, e.stderr)
        
    except subprocess.TimeoutExpired as e:
        logger.error(f"명령 실행 시간 초과 ({timeout}초)")
        raise CliToolExecutionError(
            tool_name, cmd, -1, 
            e.stdout.decode() if e.stdout else None,
            e.stderr.decode() if e.stderr else f"Command timed out after {timeout} seconds"
        )
        
    except Exception as e:
        logger.error(f"예기치 못한 오류: {e}")
        raise CliToolExecutionError(tool_name, cmd, -1, None, str(e))


def run_cmd_safely(cmd: list, timeout: int = 300, cwd: Optional[Path] = None) -> bool:
    """
    Run command safely without raising exceptions.
    
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
