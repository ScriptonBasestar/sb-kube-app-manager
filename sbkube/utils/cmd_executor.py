import subprocess
from sbkube.utils.logger import logger

def run_cmd_with_logging(cmd: list, timeout: int = 300, cwd: Path = None) -> bool:
    logger.command(" ".join(map(str, cmd)))
    try:
        result = subprocess.run(cmd, capture_output=True, text=True, check=True, timeout=timeout, cwd=str(cwd) if cwd else None)
        if result.stdout:
            logger.verbose(f"STDOUT: {result.stdout.strip()}")
        if result.stderr:
            logger.verbose(f"STDERR: {result.stderr.strip()}")
        return True
    except subprocess.CalledProcessError as e:
        logger.error(f"명령 실행 실패: {e.stderr.strip() if e.stderr else e.stdout.strip()}")
    except subprocess.TimeoutExpired:
        logger.error(f"명령 실행 시간 초과 ({timeout}초)")
    except Exception as e:
        logger.error(f"예기치 못한 오류: {e}")
    return False
