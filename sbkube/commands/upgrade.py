import subprocess
import click
from pathlib import Path
from typing import Optional

from sbkube.utils.cli_check import check_helm_installed, CliToolNotFoundError, CliToolExecutionError
from sbkube.models.config_model import (
    AppInfoScheme,
    AppInstallHelmSpec,
)
from sbkube.utils.base_command import BaseCommand
from sbkube.utils.common import common_click_options
from sbkube.utils.logger import logger, setup_logging_from_context, LogLevel


class UpgradeCommand(BaseCommand):
    """Upgrade 명령 구현"""

    def __init__(self, base_dir: str, app_config_dir: str, cli_namespace: Optional[str],
                 target_app_name: Optional[str], dry_run: bool, skip_install: bool, config_file_name: Optional[str]):
        super().__init__(base_dir, app_config_dir, cli_namespace, config_file_name)
        self.target_app_name = target_app_name
        self.dry_run = dry_run
        self.skip_install = skip_install

    def execute(self):
        """upgrade 명령 실행"""
        self.execute_pre_hook()
        logger.heading(f"Upgrade 시작 - app-dir: {self.app_config_dir.name}")
        
        # 지원하는 앱 타입
        supported_types = ["install-helm"]
        
        # 앱 파싱
        self.parse_apps(app_types=supported_types, app_name=self.target_app_name)
        
        # 필요한 CLI 도구들 체크 (공통 함수 사용)
        if self.app_info_list:
            self.check_required_cli_tools()
        
        # 앱 처리 (공통 로직 사용)
        self.process_apps_with_stats(self._upgrade_app, "업그레이드")
        
    def _upgrade_app(self, app_info: AppInfoScheme) -> bool:
        """개별 앱 업그레이드"""
        app_name = app_info.name
        app_type = app_info.type
        current_ns = self.get_namespace(app_info)
        
        logger.progress(f"앱 '{app_name}' (타입: {app_type}, 네임스페이스: {current_ns or '기본값'}) 업그레이드 시작")
        
        try:
            # Spec 모델 생성 (공통 함수 사용)
            spec_obj = self.create_app_spec(app_info)
            if not spec_obj:
                return False
                
            # Helm 업그레이드 처리
            return self._upgrade_helm(app_info, spec_obj, current_ns)
                
        except Exception as e:
            logger.error(f"앱 '{app_name}' 업그레이드 중 예상치 못한 오류: {e}")
            if logger._level.value <= LogLevel.DEBUG.value:
                import traceback
                logger.debug(traceback.format_exc())
            return False

    def _upgrade_helm(self, app_info: AppInfoScheme, spec_obj: AppInstallHelmSpec, namespace: Optional[str]) -> bool:
        """Helm 차트 업그레이드"""
        app_name = app_info.name
        release_name = app_info.release_name or app_name
        
        # 빌드된 차트 경로 확인
        chart_key = (app_info.specs.get("path") if isinstance(app_info.specs, dict) else getattr(app_info.specs, "path", None)) or app_name
        chart_dir = self.build_dir / chart_key
        
        if not chart_dir.exists() or not chart_dir.is_dir():
            logger.error(f"앱 '{app_name}': 빌드된 Helm 차트 디렉토리를 찾을 수 없습니다: {chart_dir}")
            logger.warning("'sbkube build' 명령을 먼저 실행했는지 확인하세요.")
            return False
        
        # Helm upgrade 명령 구성
        cmd_list = ["helm", "upgrade", release_name, str(chart_dir)]
        if not self.skip_install:
            cmd_list.append("--install")
            
        if namespace:
            cmd_list.extend(["--namespace", namespace, "--create-namespace"])
            logger.verbose(f"네임스페이스 적용: {namespace}")
        else:
            logger.verbose("네임스페이스 미지정, 기본 namespace 사용")
        
        # values 파일 적용
        if spec_obj and spec_obj.values:
            for vf in spec_obj.values:
                vf_path = Path(vf)
                if not vf_path.is_absolute():
                    vf_path = self.values_dir / vf
                if vf_path.exists():
                    cmd_list.extend(["--values", str(vf_path)])
                    logger.verbose(f"values 파일 사용: {vf_path}")
                else:
                    logger.warning(f"values 파일 없음 (건너뜀): {vf_path}")
        
        if self.dry_run:
            cmd_list.append("--dry-run")
            logger.warning("Dry-run 모드 활성화됨")
        
        # 명령 실행
        try:
            result = self.execute_command_with_logging(
                cmd_list, 
                f"앱 '{release_name}' 업그레이드/설치 실패",
                f"앱 '{release_name}' 업그레이드/설치 성공",
                timeout=600
            )
            return True
        except Exception:
            return False


@click.command(name="upgrade")
@common_click_options
@click.option("--namespace", "cli_namespace", default=None, help="업그레이드 기본 네임스페이스 (없으면 앱별/전역 설정 따름)")
@click.option("--dry-run", is_flag=True, default=False, help="실제 적용 없이 helm --dry-run만 실행")
@click.option("--no-install", "skip_install", is_flag=True, default=False, help="릴리스가 없을 경우 새로 설치하지 않음")
@click.pass_context
def cmd(ctx, app_config_dir_name: str, base_dir: str, config_file_name: str, app_name: str, verbose: bool, debug: bool, cli_namespace: Optional[str], dry_run: bool, skip_install: bool):
    """
    Helm 차트를 업그레이드합니다 (helm upgrade --install).
    `build` 명령 이후에 실행해야 합니다.
    """
    ctx.ensure_object(dict)
    ctx.obj['verbose'] = verbose
    ctx.obj['debug'] = debug
    setup_logging_from_context(ctx)

    upgrade_cmd = UpgradeCommand(
        base_dir=base_dir,
        app_config_dir=app_config_dir_name,
        cli_namespace=cli_namespace,
        target_app_name=app_name,
        dry_run=dry_run,
        skip_install=skip_install,
        config_file_name=config_file_name
    )
    upgrade_cmd.execute()
