import subprocess
import click
from pathlib import Path
from typing import Optional

from sbkube.utils.base_command import BaseCommand
from sbkube.utils.common import common_click_options
from sbkube.utils.logger import logger, setup_logging_from_context, LogLevel
from sbkube.utils.cli_check import check_helm_installed, CliToolNotFoundError, CliToolExecutionError
from sbkube.models.config_model import (
    AppInfoScheme,
    AppInstallHelmSpec,
    AppPullHelmSpec,
)


class TemplateCommand(BaseCommand):
    """Template 명령 구현"""

    def __init__(self, base_dir: str, app_config_dir: str, output_dir_name: str,
                 target_app_name: Optional[str], cli_namespace: Optional[str], config_file_name: Optional[str]):
        super().__init__(base_dir, app_config_dir, cli_namespace, config_file_name)
        self.output_dir_name = output_dir_name
        self.target_app_name = target_app_name
        # 출력 디렉토리 결정
        output_dir = Path(output_dir_name)
        if not output_dir.is_absolute():
            output_dir = self.app_config_dir / output_dir_name
        self.output_dir = output_dir

    def execute(self):
        """template 명령 실행"""
        self.execute_pre_hook()
        logger.heading(f"Template 시작 - app-dir: {self.app_config_dir.name}")
        
        # 출력 디렉토리 준비
        logger.info(f"출력 디렉토리 준비: {self.output_dir}")
        self.ensure_directory(self.output_dir, "출력 디렉토리")
        
        # Helm 관련 앱 필터링
        supported_types = ["install-helm"]
        self.parse_apps(app_types=supported_types, app_name=self.target_app_name)
        
        # Helm 설치 확인 (템플릿 생성할 앱이 있는 경우에만)
        if self.app_info_list:
            self.check_required_cli_tools()
        
        # 앱 처리 (공통 로직 사용)
        self.process_apps_with_stats(self._template_app, "템플릿 생성")
        
        logger.heading(f"Template 작업 완료 (결과물 위치: {self.output_dir})")

    def _template_app(self, app_info: AppInfoScheme) -> bool:
        """개별 앱 템플릿 생성"""
        app_name = app_info.name
        app_type = app_info.type
        
        logger.progress(f"앱 '{app_name}' (타입: {app_type}) 템플릿 생성 시작...")
        
        try:
            # 차트 경로 결정
            chart_key = app_info.specs.get("path") if isinstance(app_info.specs, dict) else getattr(app_info.specs, "path", None)
            chart_key = chart_key or app_name
            built_chart = self.build_dir / chart_key
            
            if not built_chart.exists() or not built_chart.is_dir():
                logger.error(f"앱 '{app_name}': 빌드된 Helm 차트 디렉토리를 찾을 수 없습니다: {built_chart}")
                logger.warning("'sbkube build' 명령을 먼저 실행했는지 확인하세요.")
                return False
            
            # Helm template 명령 구성
            helm_cmd = self._build_helm_template_command(app_info, built_chart)
            
            # 명령 실행
            result = self.execute_command_with_logging(
                helm_cmd, 
                f"앱 '{app_name}': helm template 실행 실패",
                timeout=60
            )
            
            # 결과 저장
            out_file = self.output_dir / f"{app_name}.yaml"
            out_file.write_text(result.stdout, encoding="utf-8")
            logger.success(f"앱 '{app_name}' 템플릿 생성 완료: {out_file}")
            return True
            
        except Exception as e:
            logger.error(f"앱 '{app_name}': 템플릿 생성 중 예기치 못한 오류: {e}")
            if logger._level.value <= LogLevel.DEBUG.value:
                import traceback
                logger.debug(traceback.format_exc())
            return False
    
    def _build_helm_template_command(self, app_info: AppInfoScheme, built_chart: Path) -> list:
        """Helm template 명령 구성"""
        app_name = app_info.name
        helm_cmd = ["helm", "template", app_name, str(built_chart)]
        
        # 네임스페이스 적용
        namespace = self.get_namespace(app_info)
        if namespace:
            helm_cmd.extend(["--namespace", namespace])
            logger.verbose(f"네임스페이스 적용: {namespace}")
        
        # values 파일 적용
        values_list = []
        try:
            spec_obj = self.create_app_spec(app_info)
            if spec_obj:
                values_list = spec_obj.values
        except Exception as e:
            logger.warning(f"앱 '{app_name}': spec에서 values 추출 중 오류 (무시하고 진행): {e}")
        
        for vf in values_list:
            vf_path = Path(vf)
            if not vf_path.is_absolute():
                vf_path = self.values_dir / vf
            if vf_path.exists():
                helm_cmd.extend(["--values", str(vf_path)])
                logger.verbose(f"values 파일 사용: {vf_path}")
            else:
                logger.warning(f"values 파일 없음 (건너뜀): {vf_path}")
        
        return helm_cmd

@click.command(name="template")
@common_click_options
@click.option("--output-dir", "output_dir_name", default="rendered", help="렌더링된 YAML을 저장할 디렉토리 (app-dir 기준 또는 절대경로)")
@click.option("--namespace", "cli_namespace", default=None, help="템플릿 생성 시 적용할 기본 네임스페이스 (없으면 앱별 설정 따름)")
@click.pass_context
def cmd(ctx, app_config_dir_name: str, base_dir: str, config_file_name: str, app_name: str, verbose: bool, debug: bool, output_dir_name: str, cli_namespace: str):
    """
    Helm 차트를 YAML로 렌더링합니다 (helm template).
    `build` 명령 이후에 실행해야 합니다.
    """
    ctx.ensure_object(dict)
    ctx.obj['verbose'] = verbose
    ctx.obj['debug'] = debug
    setup_logging_from_context(ctx)

    template_cmd = TemplateCommand(
        base_dir=base_dir,
        app_config_dir=app_config_dir_name,
        output_dir_name=output_dir_name,
        target_app_name=app_name,
        cli_namespace=cli_namespace,
        config_file_name=config_file_name
    )
    template_cmd.execute()
