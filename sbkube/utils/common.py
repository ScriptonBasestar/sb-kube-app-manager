import shlex
import subprocess
from pathlib import Path

import click

from sbkube.utils.logger import logger


def common_click_options(func):
    """Click 명령어에 공통 옵션을 추가하는 데코레이터.

    다음 옵션들을 자동으로 추가합니다:
    - --app-dir: 앱 설정 디렉토리
    - --base-dir: 프로젝트 루트 디렉토리
    - --config-file: 설정 파일 이름
    - --app: 대상 앱 이름
    - --verbose: 상세 로그
    - --debug: 디버그 로그

    Args:
        func: 데코레이트할 Click 명령어 함수

    Returns:
        데코레이트된 함수

    """
    options = [
        click.option(
            "--app-dir",
            "app_config_dir_name",
            default="config",
            help="앱 설정 디렉토리 이름 (base-dir 기준)",
        ),
        click.option(
            "--base-dir",
            default=".",
            type=click.Path(exists=True, file_okay=False, dir_okay=True),
            help="프로젝트 루트 디렉토리",
        ),
        click.option(
            "--config-file",
            "config_file_name",
            default=None,
            help="사용할 설정 파일 이름 (app-dir 내부)",
        ),
        click.option(
            "--app",
            "app_name",
            default=None,
            help="대상 앱 이름 (지정하지 않으면 전체 처리)",
        ),
        click.option("-v", "--verbose", is_flag=True, help="상세 로그 출력"),
        click.option("--debug", is_flag=True, help="디버그 로그 출력"),
    ]
    for opt in reversed(options):
        func = opt(func)
    return func


def execute_command_with_logging(
    cmd: list,
    error_msg: str,
    success_msg: str | None = None,
    cwd: Path | None = None,
    timeout: int = 300,
):
    """명령어 실행 및 로깅 처리."""
    logger.command(" ".join(cmd))

    try:
        result = subprocess.run(
            cmd,
            capture_output=True,
            text=True,
            check=True,
            timeout=timeout,
            cwd=cwd,
        )

        if result.stdout:
            logger.verbose(f"STDOUT: {result.stdout.strip()}")

        if success_msg:
            logger.success(success_msg)

        return result

    except subprocess.CalledProcessError as e:
        logger.error(error_msg)
        if e.stdout:
            logger.verbose(f"STDOUT: {e.stdout.strip()}")
        if e.stderr:
            logger.error(f"STDERR: {e.stderr.strip()}")
        raise
    except subprocess.TimeoutExpired:
        logger.error(f"명령어 실행 시간 초과 ({timeout}초): {' '.join(cmd)}")
        raise
    except Exception as e:
        logger.error(f"명령어 실행 중 예기치 못한 오류: {e}")
        raise


def check_required_cli_tools(app_info_list: list):
    """앱 목록에 필요한 CLI 도구들을 체크합니다.

    앱 타입에 따라 필요한 도구(helm, kubectl, git)를 확인하고,
    설치되지 않은 경우 프로그램을 종료합니다.

    Args:
        app_info_list: 앱 정보 리스트

    Returns:
        dict: 필요한 도구 목록 {"helm": bool, "kubectl": bool, "git": bool}

    Raises:
        click.Abort: 필수 CLI 도구가 설치되지 않은 경우

    """
    import click

    from sbkube.utils.cli_check import (
        CliToolExecutionError,
        CliToolNotFoundError,
        check_helm_installed,
        check_kubectl_installed,
    )

    needs_helm = any(app.type in ["helm", "helm", "helm-oci"] for app in app_info_list)
    needs_kubectl = any(
        app.type in ["yaml", "install-kustomize"] for app in app_info_list
    )
    needs_git = any(app.type == "pull-git" for app in app_info_list)

    if needs_helm:
        try:
            check_helm_installed()
        except (CliToolNotFoundError, CliToolExecutionError):
            raise click.Abort

    if needs_kubectl:
        try:
            check_kubectl_installed()
        except (CliToolNotFoundError, CliToolExecutionError):
            raise click.Abort

    # Git은 대부분 시스템에 설치되어 있으므로 별도 체크하지 않음
    return {"helm": needs_helm, "kubectl": needs_kubectl, "git": needs_git}


def run_command(
    cmd: list[str] | str,
    capture_output: bool = True,
    text: bool = True,
    check: bool = False,
    env: dict[str, str] | None = None,
    cwd: str | Path | None = None,
    timeout: int | None = None,
    **kwargs,
) -> tuple[int, str, str]:
    """명령어를 실행하고 결과를 반환합니다.

    Args:
        cmd: 실행할 명령어 (리스트 또는 문자열)
        capture_output: 출력을 캡처할지 여부
        text: 텍스트 모드로 실행할지 여부
        check: 실행 실패시 예외를 발생시킬지 여부
        env: 환경 변수
        cwd: 작업 디렉토리
        timeout: 명령어 타임아웃
        **kwargs: subprocess.run에 전달할 추가 인자

    Returns:
        Tuple[int, str, str]: (return_code, stdout, stderr)

    """
    # 문자열인 경우 shlex로 분할
    if isinstance(cmd, str):
        cmd = shlex.split(cmd)

    try:
        result = subprocess.run(
            cmd,
            capture_output=capture_output,
            text=text,
            check=check,
            env=env,
            cwd=cwd,
            timeout=timeout,
            **kwargs,
        )

        return (result.returncode, result.stdout or "", result.stderr or "")

    except subprocess.CalledProcessError as e:
        return (e.returncode, e.stdout or "", e.stderr or "")
    except subprocess.TimeoutExpired as e:
        return (
            -1,
            e.stdout or "",
            f"Timeout expired after {timeout} seconds.\n{e.stderr or ''}",
        )
    except Exception as e:
        return (1, "", str(e))


def get_absolute_path(path: str | Path, base: str | Path) -> Path:
    """상대 경로를 절대 경로로 변환합니다.

    Args:
        path: 변환할 경로
        base: 기준이 되는 경로

    Returns:
        Path: 절대 경로

    """
    path = Path(path)
    if path.is_absolute():
        return path
    return Path(base) / path


def check_resource_exists(
    resource_type: str,
    resource_name: str,
    namespace: str | None = None,
    env: dict[str, str] | None = None,
) -> bool:
    """Kubernetes 리소스의 존재 여부를 확인합니다.

    Args:
        resource_type: 리소스 타입 (예: "release", "deployment", "pod")
        resource_name: 리소스 이름
        namespace: 네임스페이스 (선택적)
        env: 환경 변수

    Returns:
        bool: 리소스가 존재하면 True, 그렇지 않으면 False

    """
    if resource_type == "release":
        # Helm 릴리스 확인
        cmd = ["helm", "status", resource_name]
        if namespace:
            cmd.extend(["--namespace", namespace])
    else:
        # kubectl 리소스 확인
        cmd = ["kubectl", "get", resource_type, resource_name]
        if namespace:
            cmd.extend(["--namespace", namespace])

    return_code, _, _ = run_command(cmd, env=env)
    return return_code == 0


def find_all_app_dirs(
    base_dir: Path, config_file_name: str = "config.yaml"
) -> list[Path]:
    """base_dir 하위의 모든 앱 그룹 디렉토리를 찾습니다.

    config.yaml 파일이 존재하는 모든 하위 디렉토리를 반환합니다.
    숨김 디렉토리(. 시작)와 시스템 디렉토리는 제외합니다.

    Args:
        base_dir: 프로젝트 루트 디렉토리
        config_file_name: 찾을 설정 파일 이름 (기본값: "config.yaml")

    Returns:
        list[Path]: 앱 그룹 디렉토리 경로 리스트 (정렬됨)

    Example:
        >>> # 프로젝트 구조:
        >>> # /project/
        >>> #   ├── sources.yaml
        >>> #   ├── redis/config.yaml
        >>> #   ├── postgres/config.yaml
        >>> #   └── nginx/config.yaml
        >>> find_all_app_dirs(Path("/project"))
        [Path("/project/nginx"), Path("/project/postgres"), Path("/project/redis")]

    """
    excluded_dirs = {
        "charts",
        "repos",
        "build",
        "rendered",
        "values",
        ".git",
        ".venv",
        "__pycache__",
        "node_modules",
        "schemas",
        "examples",
        "docs",
        "tests",
    }

    app_dirs = []

    if not base_dir.exists() or not base_dir.is_dir():
        return app_dirs

    for path in base_dir.iterdir():
        # 디렉토리만 검사
        if not path.is_dir():
            continue

        # 숨김 디렉토리 제외
        if path.name.startswith("."):
            continue

        # 시스템 디렉토리 제외
        if path.name in excluded_dirs:
            continue

        # config.yaml 존재 확인
        config_file = path / config_file_name
        if config_file.exists() and config_file.is_file():
            app_dirs.append(path)

    # 정렬하여 반환 (일관된 순서)
    return sorted(app_dirs)


def find_sources_file(
    base_dir: Path,
    app_config_dir: Path,
    sources_file_name: str = "sources.yaml",
) -> Path | None:
    """sources.yaml 파일을 찾습니다.

    다음 순서로 검색합니다:
    1. app_config_dir (현재 작업 디렉토리, .)
    2. app_config_dir 상위 디렉토리 (..)
    3. base_dir (프로젝트 루트)

    이 로직을 통해 다음 두 가지 실행 방법을 모두 지원합니다:
    - `sbkube apply --app-dir app1` (base-dir에서 실행)
    - `cd app1 && sbkube apply` (app-dir에서 실행)

    Args:
        base_dir: 프로젝트 루트 디렉토리
        app_config_dir: 앱 설정 디렉토리 (config.yaml 위치)
        sources_file_name: sources 파일 이름 (기본값: "sources.yaml")

    Returns:
        Path | None: 찾은 sources 파일 경로, 없으면 None

    Example:
        >>> # Case 1: base-dir에서 실행
        >>> # sbkube apply --app-dir app1
        >>> find_sources_file(Path("/project"), Path("/project/app1"))
        Path("/project/sources.yaml")

        >>> # Case 2: app-dir에서 실행
        >>> # cd app1 && sbkube apply
        >>> find_sources_file(Path("/project/app1"), Path("/project/app1"))
        Path("/project/sources.yaml")  # 상위 디렉토리에서 발견

    """
    # 1. app_config_dir에서 sources.yaml 찾기 (현재 디렉토리)
    sources_path = app_config_dir / sources_file_name
    if sources_path.exists():
        return sources_path

    # 2. app_config_dir 상위 디렉토리에서 sources.yaml 찾기 (..)
    parent_sources_path = app_config_dir.parent / sources_file_name
    if parent_sources_path.exists():
        return parent_sources_path

    # 3. base_dir에서 sources.yaml 찾기 (프로젝트 루트)
    base_sources_path = base_dir / sources_file_name
    if base_sources_path.exists():
        return base_sources_path

    # 찾지 못함
    return None
