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
from sbkube.utils.logger import logger, setup_logging_from_context


class UpgradeCommand(BaseCommand):
    """Upgrade 명령 구현"""

    def __init__(self, base_dir: str, app_config_dir: str, cli_namespace: Optional[str],
                 dry_run: bool, skip_install: bool, app_name: Optional[str], config_file_name: Optional[str]):
        super().__init__(base_dir, app_config_dir, cli_namespace, config_file_name)
        self.dry_run = dry_run
        self.skip_install = skip_install
        self.target_app_name = app_name

    def execute(self):
        """upgrade 명령 실행"""
        self.execute_pre_hook()
        
        logger.heading(f"Upgrade 시작 - app-dir: {self.app_config_dir.name}")

        # 설정 파일 로드 및 앱 필터링
        self.load_config()
        supported_types = ["install-helm"]
        self.parse_apps(app_types=supported_types, app_name=self.target_app_name)
        
        if not self.app_info_list:
            if self.target_app_name:
                logger.warning(f"앱 '{self.target_app_name}'은 upgrade 대상이 아닙니다.")
            else:
                logger.warning("업그레이드할 'install-helm' 타입의 앱이 설정 파일에 없습니다.")
            logger.heading("Upgrade 작업 완료 (처리할 앱 없음)")
            return
            
        # Helm 설치 확인 (업그레이드할 앱이 있는 경우에만)
        try:
            check_helm_installed()
        except (CliToolNotFoundError, CliToolExecutionError):
            raise click.Abort()

        total = len(self.app_info_list)
        success = 0
        skipped = 0

        for app_info in self.app_info_list:
            name = app_info.name
            release_name = app_info.release_name or name
            logger.progress(f"앱 '{name}' (릴리스명: '{release_name}') 업그레이드/설치 시도...")

            # 빌드된 차트 경로 확인
            chart_key = (app_info.specs.get("path") if isinstance(app_info.specs, dict) else getattr(app_info.specs, "path", None)) or name
            chart_dir = self.build_dir / chart_key
            if not chart_dir.exists() or not chart_dir.is_dir():
                logger.error(f"앱 '{name}': 빌드된 Helm 차트 디렉토리를 찾을 수 없습니다: {chart_dir}")
                logger.warning("'sbkube build' 명령을 먼저 실행했는지 확인하세요.")
                skipped += 1
                continue

            # Helm upgrade 명령 구성
            cmd_list = ["helm", "upgrade", release_name, str(chart_dir)]
            if not self.skip_install:
                cmd_list.append("--install")
            namespace = self.get_namespace(app_info)
            if namespace:
                cmd_list.extend(["--namespace", namespace, "--create-namespace"])
                logger.verbose(f"네임스페이스 적용: {namespace}")
            else:
                logger.verbose("네임스페이스 미지정, 기본 namespace 사용")

            # values 파일 적용
            spec_obj = None
            try:
                spec_obj = AppInstallHelmSpec(**app_info.specs)
            except Exception as e:
                logger.warning(f"앱 '{name}': spec 처리 중 오류 (무시하고 진행): {e}")
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

            logger.command(" ".join(cmd_list))
            try:
                result = subprocess.run(cmd_list, capture_output=True, text=True, check=True, timeout=600)
                logger.success(f"앱 '{release_name}' 업그레이드/설치 성공")
                if result.stdout:
                    logger.verbose(f"STDOUT: {result.stdout.strip()}")
                if result.stderr:
                    logger.warning(f"STDERR: {result.stderr.strip()}")
                success += 1
            except subprocess.CalledProcessError as e:
                logger.error(f"앱 '{release_name}' 업그레이드/설치 실패")
                if e.stdout:
                    logger.verbose(f"STDOUT: {e.stdout.strip()}")
                if e.stderr:
                    logger.error(f"STDERR: {e.stderr.strip()}")
            except subprocess.TimeoutExpired:
                logger.error(f"앱 '{release_name}' 업그레이드/설치 시간 초과 (600초)")
            except Exception as e:
                logger.error(f"앱 '{release_name}' 처리 중 예기치 못한 오류: {e}")
                if logger._level.value <= logger.LogLevel.DEBUG.value:
                    import traceback
                    logger.debug(traceback.format_exc())

        failures = total - success - skipped
        logger.heading("`upgrade` 작업 요약")
        if total > 0:
            logger.success(f"총 {total}개 앱 중 {success}개 성공")
            if skipped:
                logger.warning(f"{skipped}개 앱 건너뜀")
            if failures:
                logger.error(f"{failures}개 앱 실패")
        logger.heading("`upgrade` 작업 완료")

    def _create_spec(self, app_info: AppInfoScheme) -> Optional[AppInstallHelmSpec]:
        """Spec 모델 생성"""
        try:
            return AppInstallHelmSpec(**app_info.specs)
        except Exception as e:
            logger.warning(f"앱 '{app_info.name}': Spec 변환 중 오류 (무시하고 진행): {e}")
            return None


@click.command(name="upgrade")
@common_click_options
@click.option("--namespace", "cli_namespace", default=None, help="업그레이드 기본 네임스페이스 (없으면 앱별/전역 설정 따름)")
@click.option("--dry-run", is_flag=True, default=False, help="실제 적용 없이 helm --dry-run만 실행")
@click.option("--no-install", "skip_install", is_flag=True, default=False, help="릴리스가 없을 경우 새로 설치하지 않음")
@click.pass_context
def cmd(ctx, app_config_dir_name: str, base_dir: str, cli_namespace: Optional[str], app_name: Optional[str], dry_run: bool, skip_install: bool, config_file_name: Optional[str], verbose: bool, debug: bool):
    """
    config 파일에 정의된 Helm 앱을 업그레이드하거나 설치합니다.
    """
    ctx.ensure_object(dict)
    ctx.obj['verbose'] = verbose
    ctx.obj['debug'] = debug
    setup_logging_from_context(ctx)

    upgrade_cmd = UpgradeCommand(
        base_dir=base_dir,
        app_config_dir=app_config_dir_name,
        cli_namespace=cli_namespace,
        dry_run=dry_run,
        skip_install=skip_install,
        app_name=app_name,
        config_file_name=config_file_name
    )
    upgrade_cmd.execute()
