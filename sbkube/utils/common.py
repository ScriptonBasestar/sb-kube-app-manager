import subprocess
import shlex
from typing import List, Union, Tuple, Optional, Dict, Any
from pathlib import Path

import click

from sbkube.utils import logger

def common_click_options(func):
    options = [
        click.option("--app-dir", "app_config_dir_name", default="config", help="앱 설정 디렉토리 이름 (base-dir 기준)"),
        click.option("--base-dir", default=".", type=click.Path(exists=True, file_okay=False, dir_okay=True), help="프로젝트 루트 디렉토리"),
        click.option("--config-file", "config_file_name", default=None, help="사용할 설정 파일 이름 (app-dir 내부)"),
        click.option("--app", "app_name", default=None, help="대상 앱 이름 (지정하지 않으면 전체 처리)"),
        click.option("-v", "--verbose", is_flag=True, help="상세 로그 출력"),
        click.option("--debug", is_flag=True, help="디버그 로그 출력"),
    ]
    for opt in reversed(options):
        func = opt(func)
    return func

from sbkube.models.config_model import *

def create_spec(app_info: AppInfoScheme):
    type_ = app_info.type
    try:
        if type_ == "pull-helm":
            return AppPullHelmSpec(**app_info.specs)
        elif type_ == "pull-helm-oci":
            return AppPullHelmOciSpec(**app_info.specs)
        elif type_ == "pull-git":
            return AppPullGitSpec(**app_info.specs)
        elif type_ == "copy-app":
            return AppCopySpec(**app_info.specs)
        elif type_ == "install-helm":
            return AppInstallHelmSpec(**app_info.specs)
        elif type_ == "install-yaml":
            return AppInstallActionSpec(**app_info.specs)
        elif type_ == "exec":
            return AppExecSpec(**app_info.specs)
    except Exception as e:
        logger.warning(f"앱 '{app_info.name}' Spec 변환 실패: {e}")
        return None

def run_command(
    cmd: Union[List[str], str],
    capture_output: bool = True,
    text: bool = True,
    check: bool = False,
    env: Optional[Dict[str, str]] = None,
    cwd: Optional[Union[str, Path]] = None,
    **kwargs
) -> Tuple[int, str, str]:
    """
    명령어를 실행하고 결과를 반환합니다.
    
    Args:
        cmd: 실행할 명령어 (리스트 또는 문자열)
        capture_output: 출력을 캡처할지 여부
        text: 텍스트 모드로 실행할지 여부
        check: 실행 실패시 예외를 발생시킬지 여부
        env: 환경 변수
        cwd: 작업 디렉토리
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
            **kwargs
        )
        
        return (
            result.returncode,
            result.stdout or "",
            result.stderr or ""
        )
        
    except subprocess.CalledProcessError as e:
        return (
            e.returncode,
            e.stdout or "",
            e.stderr or ""
        )
    except Exception as e:
        return (
            1,
            "",
            str(e)
        )


def get_absolute_path(path: Union[str, Path], base: Union[str, Path]) -> Path:
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
    namespace: Optional[str] = None,
    env: Optional[Dict[str, str]] = None
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