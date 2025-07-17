import shlex
import subprocess
from pathlib import Path

import click

from sbkube.models.config_model import AppInfoScheme, get_spec_model
from sbkube.utils.logger import logger


def common_click_options(func):
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


def create_app_spec(app_info: AppInfoScheme):
    """앱 타입에 맞는 Spec 객체 생성"""
    try:
        spec_model_class = get_spec_model(app_info.type)
        if not spec_model_class:
            logger.error(f"앱 '{app_info.name}': 지원하지 않는 타입 '{app_info.type}'")
            return None

        return spec_model_class(**app_info.specs)
    except Exception as e:
        logger.error(
            f"앱 '{app_info.name}' (타입: {app_info.type})의 Spec 데이터 검증/변환 중 오류: {e}",
        )
        logger.warning(f"해당 앱 설정을 건너뜁니다. Specs: {app_info.specs}")
        return None


def execute_command_with_logging(
    cmd: list,
    error_msg: str,
    success_msg: str = None,
    cwd: Path = None,
    timeout: int = 300,
):
    """명령어 실행 및 로깅 처리"""

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
    """앱 목록에 필요한 CLI 도구들 체크"""
    import click

    from sbkube.utils.cli_check import (
        CliToolExecutionError,
        CliToolNotFoundError,
        check_helm_installed,
        check_kubectl_installed,
    )

    needs_helm = any(
        app.type in ["install-helm", "pull-helm", "pull-helm-oci"]
        for app in app_info_list
    )
    needs_kubectl = any(
        app.type in ["install-yaml", "install-kustomize"] for app in app_info_list
    )
    needs_git = any(app.type == "pull-git" for app in app_info_list)

    if needs_helm:
        try:
            check_helm_installed()
        except (CliToolNotFoundError, CliToolExecutionError):
            raise click.Abort()

    if needs_kubectl:
        try:
            check_kubectl_installed()
        except (CliToolNotFoundError, CliToolExecutionError):
            raise click.Abort()

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
    """
    명령어를 실행하고 결과를 반환합니다.

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
    """
    상대 경로를 절대 경로로 변환합니다.

    Args:
        path: 변환할 경로
        base: 기준이 되는 경로

    Returns:
        Path: 절대 경로
    """
    path = Path(path)
    if path.is_absolute():
        return path
    else:
        return Path(base) / path


def check_resource_exists(
    resource_type: str,
    resource_name: str,
    namespace: str | None = None,
    env: dict[str, str] | None = None,
) -> bool:
    """
    Kubernetes 리소스의 존재 여부를 확인합니다.

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
