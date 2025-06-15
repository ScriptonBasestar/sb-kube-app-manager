import json
import subprocess
import shutil
from pathlib import Path
import click
from shutil import which
from typing import Optional

# config_model 임포트
from sbkube.models.config_model import (
    AppInfoScheme,
    AppPullHelmSpec,
    AppPullHelmOciSpec,
    AppPullGitSpec,
    # TODO: 다른 App Spec 모델들도 필요에 따라 임포트
)
from sbkube.utils.common import common_click_options
from sbkube.utils.file_loader import load_config_file
# sbkube.utils.cli_check 임포트는 check_helm_installed_or_exit 만 사용
from sbkube.utils.cli_check import check_helm_installed, CliToolNotFoundError, CliToolExecutionError
from sbkube.utils.base_command import BaseCommand
from sbkube.utils.logger import logger, setup_logging_from_context

def check_command_available(command):
    if which(command) is None:
        logger.warning(f"'{command}' 명령을 찾을 수 없습니다. PATH에 등록되어 있는지 확인하세요.")
        return False
    try:
        result = subprocess.run([command, "--help"], capture_output=True, text=True, timeout=5)
        if result.returncode != 0:
            return False
        return True
    except Exception:
        return False

class PrepareCommand(BaseCommand):
    """Prepare 명령 구현"""
    def __init__(self, base_dir: str, app_config_dir: str, 
                 sources_file: str, sources_override: Optional[str],
                 app_name: Optional[str], config_file_name: Optional[str]):
        super().__init__(base_dir, app_config_dir, None, config_file_name)
        self.sources_file = sources_file
        self.sources_override = sources_override
        self.target_app_name = app_name
    
    def execute(self):
        """prepare 명령 실행"""
        self.execute_pre_hook()
    
        logger.heading("Prepare 시작")
        
        # 설정 파일 로드
        self.load_config()
        
        # 소스 파일 결정
        sources_path = Path(self.base_dir) / (self.sources_override or self.sources_file)
        if not sources_path.exists():
            logger.error(f"소스 설정 파일이 존재하지 않습니다: {sources_path}")
            raise click.Abort()
        logger.info(f"소스 설정 파일 사용: {sources_path}")
        sources_config = load_config_file(str(sources_path))
        helm_repos = sources_config.get("helm_repos", {})
        oci_repos = sources_config.get("oci_repos", {})
        git_repos = sources_config.get("git_repos", {})
        
        # 앱 파싱 (pull-helm, pull-helm-oci, pull-git)
        self.parse_apps(app_types=["pull-helm", "pull-helm-oci", "pull-git"], app_name=self.target_app_name)
        if not self.app_info_list:
            logger.warning("준비할 앱이 없습니다.")
            return
        
        # 필요한 CLI 도구들 체크
        self._check_required_tools()
        
        # Helm 저장소 준비
        # ... existing logic 이식, console.print → logger 사용 ...
        # Git 저장소 준비
        # ...
        # Helm 차트 풀링
        # ...
        
        logger.heading("Prepare 완료")
        
    def _check_required_tools(self):
        """준비할 앱들에 필요한 CLI 도구들 체크"""
        needs_helm = any(app.type in ["pull-helm", "pull-helm-oci"] for app in self.app_info_list)
        needs_git = any(app.type == "pull-git" for app in self.app_info_list)
        
        if needs_helm:
            try:
                check_helm_installed()
            except (CliToolNotFoundError, CliToolExecutionError):
                raise click.Abort()
                
        if needs_git:
            if not check_command_available("git"):
                logger.error("git 명령이 필요하지만 사용할 수 없습니다.")
                raise click.Abort()

@click.command(name="prepare")
@common_click_options
@click.option("--sources", "sources_file", default="sources.yaml", help="소스 설정 파일")
@click.option("--sources-file", "sources_override", default=None, help="소스 설정 파일 경로(테스트 호환)")
@click.pass_context
def cmd(ctx, app_dir, sources_file, base_dir, config_file_name, sources_override, app_name, verbose, debug):
    ctx.ensure_object(dict)
    ctx.obj['verbose'] = verbose
    ctx.obj['debug'] = debug
    setup_logging_from_context(ctx)
    
    cmd = PrepareCommand(
        base_dir=base_dir,
        app_config_dir=app_dir,
        sources_file=sources_file,
        sources_override=sources_override,
        app_name=app_name,
        config_file_name=config_file_name
    )
    cmd.execute()
