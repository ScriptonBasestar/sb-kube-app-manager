import subprocess
import click
from pathlib import Path
import yaml # kubectl delete 시 YAML 파싱용

from sbkube.utils.cli_check import check_helm_installed_or_exit, check_kubectl_installed_or_exit
from sbkube.utils.helm_util import get_installed_charts
from sbkube.models.config_model import (
    AppInfoScheme,
    AppInstallActionSpec # uninstall 액션 지원을 위해
)

from sbkube.models import get_spec_model

from typing import Optional
from sbkube.utils.base_command import BaseCommand
from sbkube.utils.logger import logger, setup_logging_from_context

class DeleteCommand(BaseCommand):
    """Delete 명령 구현"""

    def __init__(self, base_dir: str, app_config_dir: str, cli_namespace: Optional[str],
                 target_app_name: Optional[str], skip_not_found: bool, config_file_name: Optional[str]):
        super().__init__(base_dir, app_config_dir, cli_namespace, config_file_name)
        self.target_app_name = target_app_name
        self.skip_not_found = skip_not_found

    def execute(self):
        """delete 명령 실행"""
        logger.heading(f"Delete 시작 - app-dir: {self.app_config_dir.name}")
        # 설정 파일 로드
        self.load_config()
        # YAMLS_DIR 설정
        YAMLS_DIR = self.app_config_dir / 'yamls'
        # 글로벌 네임스페이스
        global_ns = self.apps_config_dict.get('config', {}).get('namespace')
        # 앱 목록 로드
        apps = self.apps_config_dict.get('apps', [])
        # 특정 앱 필터링
        if self.target_app_name:
            apps = [a for a in apps if a.get('name') == self.target_app_name]
            if not apps:
                logger.error(f"삭제 대상 앱 '{self.target_app_name}'을(를) 설정 파일에서 찾을 수 없습니다.")
                raise click.Abort()
        if not apps:
            logger.warning('삭제할 앱이 설정 파일에 없습니다.')
            logger.heading('Delete 작업 완료 (처리할 앱 없음)')
            return
        total = success = skipped = 0
        for app_dict in apps:
            try:
                app_info = AppInfoScheme(**app_dict)
            except Exception as e:
                name = app_dict.get('name', '알 수 없는 앱')
                logger.error(f"앱 정보 '{name}' 처리 중 오류: {e}")
                skipped += 1
                continue
            # 지원 타입 필터링
            if app_info.type not in ['install-helm', 'install-yaml', 'install-action']:
                continue
            total += 1
            name = app_info.name
            type_ = app_info.type
            release = app_info.release_name or name
            logger.progress(f"앱 '{name}' (타입: {type_}) 삭제 시도...")
            # 네임스페이스 결정
            ns = self.get_namespace(app_info) or global_ns
            if ns:
                logger.verbose(f"네임스페이스 사용: {ns}")
            else:
                logger.verbose('네임스페이스 미지정 (default)')
            deleted = False
            # 타입별 삭제 처리
            if type_ == 'install-helm':
                check_helm_installed_or_exit()
                installed = get_installed_charts(ns)
                if release not in installed:
                    logger.warning(f"Helm 릴리스 '{release}'이 설치되어 있지 않습니다.")
                    skipped += 1
                    continue
                cmd = ['helm', 'uninstall', release]
                if ns:
                    cmd.extend(['--namespace', ns])
                logger.command(' '.join(cmd))
                try:
                    subprocess.run(cmd, capture_output=True, text=True, check=True, timeout=300)
                    logger.success(f"Helm 릴리스 '{release}' 삭제 완료")
                    success += 1
                    deleted = True
                except subprocess.CalledProcessError as e:
                    logger.error(f"Helm 릴리스 '{release}' 삭제 실패")
                    if e.stderr:
                        logger.error(f"STDERR: {e.stderr.strip()}")
                except Exception as e:
                    logger.error(f"Helm 삭제 중 오류: {e}")
            elif type_ == 'install-yaml':
                check_kubectl_installed_or_exit()
                spec = None
                if app_info.specs:
                    try:
                        spec = AppInstallActionSpec(**app_info.specs)
                    except Exception as e:
                        logger.error(f"앱 '{name}': YAML Spec 파싱 실패: {e}")
                if not spec or not spec.actions:
                    logger.warning(f"앱 '{name}': 삭제할 YAML이 없습니다.")
                    skipped += 1
                    continue
                for action in reversed(spec.actions):
                    if action.type not in ['apply', 'create']:
                        continue
                    path = Path(action.path)
                    if not path.is_absolute():
                        path = YAMLS_DIR / path
                    cmd = ['kubectl', 'delete', '-f', str(path)]
                    if ns:
                        cmd.extend(['--namespace', ns])
                    if self.skip_not_found:
                        cmd.append('--ignore-not-found=true')
                    logger.command(' '.join(cmd))
                    try:
                        subprocess.run(cmd, capture_output=True, text=True, check=True, timeout=120)
                        logger.success(f"YAML '{path.name}' 삭제 완료")
                        success += 1
                        deleted = True
                    except subprocess.CalledProcessError as e:
                        logger.error(f"YAML '{path.name}' 삭제 실패: {e.stderr.strip() if e.stderr else ''}")
                    except Exception as e:
                        logger.error(f"YAML 삭제 중 오류 '{path.name}': {e}")
            elif type_ == 'install-action':
                logger.warning(f"앱 '{name}': install-action 타입 삭제 미구현")
                skipped += 1
            if deleted:
                logger.verbose('')  # 구분용 빈 줄
        logger.heading('`delete` 작업 요약')
        if total > 0:
            logger.success(f"총 {total}개 앱 중 {success}개 삭제 성공")
            if skipped:
                logger.warning(f"{skipped}개 앱 건너뜀")
        logger.heading('`delete` 작업 완료')

@click.command(name="delete")
@click.option("--app-dir", "app_config_dir_name", default="config", help="앱 설정 파일이 위치한 디렉토리 이름 (base-dir 기준)")
@click.option("--base-dir", default=".", type=click.Path(exists=True, file_okay=False, dir_okay=True), help="프로젝트 루트 디렉토리")
@click.option("--namespace", "cli_namespace", default=None, help="삭제 작업을 수행할 기본 네임스페이스 (없으면 앱별 설정 또는 최상위 설정 따름)")
@click.option("--app", "target_app_name", default=None, help="특정 앱만 삭제 (지정하지 않으면 모든 앱 대상)")
@click.option("--skip-not-found", is_flag=True, help="삭제 대상 리소스가 없을 경우 오류 대신 건너뜁니다.")
@click.option("--config-file", "config_file_name", default=None, help="사용할 설정 파일 이름 (app-dir 내부, 기본값: config.yaml 자동 탐색)")
@click.option("-v", "--verbose", is_flag=True, help="상세 로그 출력")
@click.option("--debug", is_flag=True, help="디버그 로그 출력")
@click.pass_context
def cmd(ctx, app_config_dir_name: str, base_dir: str, cli_namespace: Optional[str], target_app_name: Optional[str], skip_not_found: bool, config_file_name: Optional[str], verbose: bool, debug: bool):
    ctx.ensure_object(dict)
    ctx.obj['verbose'] = verbose
    ctx.obj['debug'] = debug
    setup_logging_from_context(ctx)

    delete_cmd = DeleteCommand(
        base_dir=base_dir,
        app_config_dir=app_config_dir_name,
        cli_namespace=cli_namespace,
        target_app_name=target_app_name,
        skip_not_found=skip_not_found,
        config_file_name=config_file_name
    )
    delete_cmd.execute()