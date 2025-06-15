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
from sbkube.utils.logger import logger, setup_logging_from_context, LogLevel

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
    
    def __init__(self, base_dir: str, app_config_dir: str, sources_file: str, 
                 target_app_name: Optional[str], config_file_name: Optional[str]):
        super().__init__(base_dir, app_config_dir, None, config_file_name)
        self.sources_file = sources_file
        self.target_app_name = target_app_name
        
    def execute(self):
        """prepare 명령 실행"""
        self.execute_pre_hook()
        logger.heading("Prepare 시작")
        
        # 지원하는 앱 타입
        supported_types = ["pull-helm", "pull-helm-oci", "pull-git"]
        
        # 앱 파싱
        self.parse_apps(app_types=supported_types, app_name=self.target_app_name)
        
        # 필요한 CLI 도구들 체크 (공통 함수 사용)
        if self.app_info_list:
            self.check_required_cli_tools()
        
        # 앱 처리 (공통 로직 사용)
        self.process_apps_with_stats(self._prepare_app, "준비")
        
    def _prepare_app(self, app_info: AppInfoScheme) -> bool:
        """개별 앱 준비"""
        app_name = app_info.name
        app_type = app_info.type
        
        logger.progress(f"앱 '{app_name}' (타입: {app_type}) 준비 시작...")
        
        try:
            # Spec 모델 생성 (공통 함수 사용)
            spec_obj = self.create_app_spec(app_info)
            if not spec_obj:
                return False
                
            # 타입별 준비 처리
            if app_type in ["pull-helm", "pull-helm-oci"]:
                self._prepare_helm(app_info, spec_obj)
            elif app_type == "pull-git":
                self._prepare_git(app_info, spec_obj)
                
            logger.success(f"앱 '{app_name}' 준비 완료")
            return True
            
        except Exception as e:
            logger.error(f"앱 '{app_name}' 준비 중 예상치 못한 오류: {e}")
            if logger._level.value <= LogLevel.DEBUG.value:
                import traceback
                logger.debug(traceback.format_exc())
            return False

    def _prepare_helm(self, app_info: AppInfoScheme, spec_obj):
        """Helm 차트 준비 (placeholder)"""
        logger.info(f"Helm 차트 준비: {app_info.name}")
        # TODO: 실제 helm 차트 준비 로직 구현
        return True
    
    def _prepare_git(self, app_info: AppInfoScheme, spec_obj):
        """Git 저장소 준비 (placeholder)"""
        logger.info(f"Git 저장소 준비: {app_info.name}")
        # TODO: 실제 git 저장소 준비 로직 구현
        return True

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
def cmd(ctx, app_config_dir_name, base_dir, config_file_name, app_name, verbose, debug, sources_file, sources_override):
    ctx.ensure_object(dict)
    ctx.obj['verbose'] = verbose
    ctx.obj['debug'] = debug
    setup_logging_from_context(ctx)
    
    cmd = PrepareCommand(
        base_dir=base_dir,
        app_config_dir=app_config_dir_name,
        sources_file=sources_file,
        target_app_name=app_name,
        config_file_name=config_file_name
    )
    cmd.execute()
