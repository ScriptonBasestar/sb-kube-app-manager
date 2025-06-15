import subprocess
import click
from pathlib import Path
import yaml # kubectl delete 시 YAML 파싱용

from sbkube.utils.cli_check import check_helm_installed, check_kubectl_installed, CliToolNotFoundError, CliToolExecutionError
from sbkube.utils.common import common_click_options
from sbkube.utils.helm_util import get_installed_charts
from sbkube.models.config_model import (
    AppInfoScheme,
    AppInstallActionSpec # uninstall 액션 지원을 위해
)

from sbkube.models import get_spec_model

from typing import Optional
from sbkube.utils.base_command import BaseCommand
from sbkube.utils.logger import logger, setup_logging_from_context, LogLevel

class DeleteCommand(BaseCommand):
    """Delete 명령 구현"""

    def __init__(self, base_dir: str, app_config_dir: str, cli_namespace: Optional[str],
                 target_app_name: Optional[str], skip_not_found: bool, config_file_name: Optional[str]):
        super().__init__(base_dir, app_config_dir, cli_namespace, config_file_name)
        self.target_app_name = target_app_name
        self.skip_not_found = skip_not_found

    def execute(self):
        """delete 명령 실행"""
        self.execute_pre_hook()
        logger.heading(f"Delete 시작 - app-dir: {self.app_config_dir.name}")
        
        # 지원하는 앱 타입
        supported_types = ["install-helm", "install-yaml", "install-action"]
        
        # 앱 파싱
        self.parse_apps(app_types=supported_types, app_name=self.target_app_name)
        
        # 필요한 CLI 도구들 체크 (공통 함수 사용)
        if self.app_info_list:
            self.check_required_cli_tools()
        
        # 앱 처리 (공통 로직 사용)
        self.process_apps_with_stats(self._delete_app, "삭제")
        
    def _delete_app(self, app_info: AppInfoScheme) -> bool:
        """개별 앱 삭제"""
        app_name = app_info.name
        app_type = app_info.type
        current_ns = self.get_namespace(app_info)
        
        logger.progress(f"앱 '{app_name}' (타입: {app_type}, 네임스페이스: {current_ns or '기본값'}) 삭제 시작")
        
        try:
            # Spec 모델 생성 (공통 함수 사용)
            spec_obj = self.create_app_spec(app_info)
            if not spec_obj:
                return False
                
            # 타입별 삭제 처리
            if app_type == "install-helm":
                return self._delete_helm(app_info, current_ns)
            elif app_type in ["install-yaml", "install-action"]:
                return self._delete_yaml(app_info, spec_obj, current_ns)
                
            return True
                
        except Exception as e:
            logger.error(f"앱 '{app_name}' 삭제 중 예상치 못한 오류: {e}")
            if logger._level.value <= LogLevel.DEBUG.value:
                import traceback
                logger.debug(traceback.format_exc())
            return False

    def _delete_helm(self, app_info: AppInfoScheme, ns: Optional[str]) -> bool:
        """Helm 릴리스 삭제"""
        release = app_info.release_name or app_info.name
        installed = get_installed_charts(ns)
        if release not in installed:
            logger.warning(f"Helm 릴리스 '{release}'이 설치되어 있지 않습니다.")
            return False
        cmd = ['helm', 'uninstall', release]
        if ns:
            cmd.extend(['--namespace', ns])
        logger.command(' '.join(cmd))
        try:
            subprocess.run(cmd, capture_output=True, text=True, check=True, timeout=300)
            logger.success(f"Helm 릴리스 '{release}' 삭제 완료")
            return True
        except subprocess.CalledProcessError as e:
            logger.error(f"Helm 릴리스 '{release}' 삭제 실패")
            if e.stderr:
                logger.error(f"STDERR: {e.stderr.strip()}")
            return False
        except Exception as e:
            logger.error(f"Helm 삭제 중 오류: {e}")
            return False

    def _delete_yaml(self, app_info: AppInfoScheme, spec_obj: AppInstallActionSpec, ns: Optional[str]) -> bool:
        """YAML 삭제"""
        if not spec_obj or not spec_obj.actions:
            logger.warning(f"앱 '{app_info.name}': 삭제할 YAML이 없습니다.")
            return False
        for action in reversed(spec_obj.actions):
            if action.type not in ['apply', 'create']:
                continue
            path = Path(action.path)
            if not path.is_absolute():
                path = self.app_config_dir / path
            cmd = ['kubectl', 'delete', '-f', str(path)]
            if ns:
                cmd.extend(['--namespace', ns])
            if self.skip_not_found:
                cmd.append('--ignore-not-found=true')
            logger.command(' '.join(cmd))
            try:
                subprocess.run(cmd, capture_output=True, text=True, check=True, timeout=120)
                logger.success(f"YAML '{path.name}' 삭제 완료")
                return True
            except subprocess.CalledProcessError as e:
                logger.error(f"YAML '{path.name}' 삭제 실패: {e.stderr.strip() if e.stderr else ''}")
            except Exception as e:
                logger.error(f"YAML 삭제 중 오류 '{path.name}': {e}")
        return False



@click.command(name="delete")
@common_click_options
@click.option("--skip-not-found", is_flag=True, help="삭제 대상 리소스가 없을 경우 오류 대신 건너뜁니다.")
@click.option("--namespace", "cli_namespace", default=None, help="삭제 작업을 수행할 기본 네임스페이스 (없으면 앱별 설정 또는 최상위 설정 따름)")
@click.pass_context
def cmd(ctx, app_config_dir_name: str, base_dir: str, config_file_name: str, app_name: str, verbose: bool, debug: bool, skip_not_found: bool, cli_namespace: Optional[str]):
    """
    설정 파일에 정의된 앱들을 클러스터에서 삭제합니다.
    
    지원하는 앱 타입:
    - install-helm: Helm 릴리스 삭제 (helm uninstall)
    - install-yaml: YAML 매니페스트 삭제 (kubectl delete)
    """
    ctx.ensure_object(dict)
    ctx.obj['verbose'] = verbose
    ctx.obj['debug'] = debug
    setup_logging_from_context(ctx)
    
    delete_cmd = DeleteCommand(
        base_dir=base_dir,
        app_config_dir=app_config_dir_name,
        cli_namespace=cli_namespace,
        target_app_name=app_name,
        skip_not_found=skip_not_found,
        config_file_name=config_file_name
    )
    
    delete_cmd.execute()