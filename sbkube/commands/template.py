import subprocess
import click
from pathlib import Path
from typing import Optional

from sbkube.utils.base_command import BaseCommand
from sbkube.utils.common import common_click_options
from sbkube.utils.logger import logger, setup_logging_from_context
from sbkube.utils.cli_check import check_helm_installed, CliToolNotFoundError, CliToolExecutionError
from sbkube.models.config_model import (
    AppInfoScheme,
    AppInstallHelmSpec,
    AppPullHelmSpec,
)


class TemplateCommand(BaseCommand):
    """Template 명령 구현"""

    def __init__(self, base_dir: str, app_config_dir: str, output_dir_name: str,
                 app_name: Optional[str], cli_namespace: Optional[str], config_file_name: Optional[str]):
        super().__init__(base_dir, app_config_dir, cli_namespace, config_file_name)
        self.output_dir_name = output_dir_name
        self.target_app_name = app_name
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
        
        # 설정 파일 로드
        self.load_config()
        
        # Helm 관련 앱 필터링
        supported_types = ["install-helm"]
        self.parse_apps(app_types=supported_types, app_name=self.target_app_name)
        
        if not self.app_info_list:
            if self.target_app_name:
                logger.warning(f"앱 '{self.target_app_name}'은 template 대상이 아닙니다.")
            else:
                logger.warning("템플릿 생성할 Helm 관련 앱이 설정 파일에 없습니다.")
            logger.heading("Template 작업 완료 (처리할 앱 없음)")
            return
            
        # Helm 설치 확인 (템플릿 생성할 앱이 있는 경우에만)
        try:
            check_helm_installed()
        except (CliToolNotFoundError, CliToolExecutionError):
            raise click.Abort()
        
        total = len(self.app_info_list)
        success = 0
        for app_info in self.app_info_list:
            name = app_info.name
            type_ = app_info.type
            logger.progress(f"앱 '{name}' (타입: {type_}) 템플릿 생성 시작...")
            # 차트 경로 결정
            chart_key = app_info.specs.get("path") if isinstance(app_info.specs, dict) else getattr(app_info.specs, "path", None)
            chart_key = chart_key or name
            built_chart = self.build_dir / chart_key
            if not built_chart.exists() or not built_chart.is_dir():
                logger.error(f"앱 '{name}': 빌드된 Helm 차트 디렉토리를 찾을 수 없습니다: {built_chart}")
                logger.warning("'sbkube build' 명령을 먼저 실행했는지 확인하세요.")
                continue
            # Helm template 명령 구성
            helm_cmd = ["helm", "template", name, str(built_chart)]
            # 네임스페이스 적용
            namespace = self.get_namespace(app_info)
            if namespace:
                helm_cmd.extend(["--namespace", namespace])
                logger.verbose(f"네임스페이스 적용: {namespace}")
            # values 파일 적용
            values_list = []
            try:
                spec_obj = self._create_spec(app_info)
                if spec_obj:
                    values_list = spec_obj.values
            except Exception as e:
                logger.warning(f"앱 '{name}': spec에서 values 추출 중 오류 (무시하고 진행): {e}")
            for vf in values_list:
                vf_path = Path(vf)
                if not vf_path.is_absolute():
                    vf_path = self.values_dir / vf
                if vf_path.exists():
                    helm_cmd.extend(["--values", str(vf_path)])
                    logger.verbose(f"values 파일 사용: {vf_path}")
                else:
                    logger.warning(f"values 파일 없음 (건너뜀): {vf_path}")
            # 명령 실행
            logger.command(" ".join(helm_cmd))
            try:
                result = subprocess.run(helm_cmd, capture_output=True, text=True, check=True, timeout=60)
                out_file = self.output_dir / f"{name}.yaml"
                out_file.write_text(result.stdout, encoding="utf-8")
                logger.success(f"앱 '{name}' 템플릿 생성 완료: {out_file}")
                success += 1
            except subprocess.CalledProcessError as e:
                logger.error(f"앱 '{name}': helm template 실행 실패")
                if e.stdout:
                    logger.verbose(f"STDOUT: {e.stdout.strip()}")
                if e.stderr:
                    logger.error(f"STDERR: {e.stderr.strip()}")
            except subprocess.TimeoutExpired:
                logger.error(f"앱 '{name}': helm template 실행 시간 초과 (60초)")
            except Exception as e:
                logger.error(f"앱 '{name}': 템플릿 생성 중 예기치 못한 오류: {e}")
                if logger._level.value <= logger.LogLevel.DEBUG.value:
                    import traceback
                    logger.debug(traceback.format_exc())
            finally:
                continue
        if total > 0:
            logger.success(f"`template` 작업 요약: 총 {total}개 앱 중 {success}개 성공")
        logger.heading(f"`template` 작업 완료 (결과물 위치: {self.output_dir})")

    def _create_spec(self, app_info: AppInfoScheme):
        """Spec 모델 생성 (install-helm 또는 pull-helm)"""
        try:
            if app_info.type == "install-helm":
                return AppInstallHelmSpec(**app_info.specs)
            elif app_info.type in ["pull-helm", "pull-helm-oci"]:
                return AppPullHelmSpec(**app_info.specs)
        except Exception as e:
            logger.warning(f"앱 '{app_info.name}': spec 변환 중 오류 (무시하고 진행): {e}")
        return None

@click.command(name="template")
@common_click_options
@click.option("--output-dir", "output_dir_name", default="rendered", help="렌더링된 YAML을 저장할 디렉토리 (app-dir 기준 또는 절대경로)")
@click.option("--namespace", "cli_namespace", default=None, help="템플릿 생성 시 적용할 기본 네임스페이스 (없으면 앱별 설정 따름)")
@click.pass_context
def cmd(ctx, app_config_dir_name: str, output_dir_name: str, base_dir: str, cli_namespace: str, config_file_name: str, app_name: str, verbose: bool, debug: bool):
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
        app_name=app_name,
        cli_namespace=cli_namespace,
        config_file_name=config_file_name
    )
    template_cmd.execute()
