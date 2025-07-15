import shutil
from pathlib import Path

import click

from sbkube.models.config_model import (
    AppCopySpec,
    AppInfoScheme,
    AppInstallActionSpec,
    AppPullGitSpec,
    AppPullHelmSpec,
)
from sbkube.utils.base_command import BaseCommand
from sbkube.utils.common import common_click_options
from sbkube.utils.logger import LogLevel, logger, setup_logging_from_context


class BuildCommand(BaseCommand):
    """Build 명령 구현"""

    def __init__(
        self,
        base_dir: str,
        app_config_dir: str,
        target_app_name: str | None,
        config_file_name: str | None,
    ):
        super().__init__(base_dir, app_config_dir, None, config_file_name)
        self.target_app_name = target_app_name

    def execute(self):
        """build 명령 실행"""
        self.execute_pre_hook()
        logger.heading(f"Build 시작 - app-dir: {self.app_config_dir.name}")

        # 빌드 디렉토리 준비
        self._prepare_build_directory()

        # 지원하는 앱 타입
        supported_types = [
            "pull-helm",
            "pull-helm-oci",
            "pull-git",
            "copy-app",
            "install-yaml",
        ]

        # 앱 파싱
        self.parse_apps(app_types=supported_types, app_name=self.target_app_name)

        # 앱 처리 (공통 로직 사용)
        self.process_apps_with_stats(self._build_app, "빌드")

        logger.heading(f"Build 작업 완료 (결과물 위치: {self.build_dir})")

    def _prepare_build_directory(self):
        """빌드 디렉토리 준비"""
        logger.info(f"기존 빌드 디렉토리 정리 중: {self.build_dir}")
        self.clean_directory(self.build_dir, "빌드 디렉토리")
        logger.success(f"빌드 디렉토리 준비 완료: {self.build_dir}")

    def _build_app(self, app_info: AppInfoScheme) -> bool:
        """개별 앱 빌드"""
        app_name = app_info.name
        app_type = app_info.type

        logger.progress(f"앱 '{app_name}' (타입: {app_type}) 빌드 시작...")

        try:
            # Spec 모델 생성 (공통 함수 사용)
            spec_obj = self.create_app_spec(app_info)
            if not spec_obj:
                return False

            # 타입별 빌드 처리
            if app_type in ["pull-helm", "pull-helm-oci"]:
                self._build_helm(app_info, spec_obj)
            elif app_type == "pull-git":
                self._build_git(app_info, spec_obj)
            elif app_type == "copy-app":
                self._build_copy(app_info, spec_obj)
            elif app_type == "install-yaml":
                self._build_install_yaml(app_info, spec_obj)

            logger.success(f"앱 '{app_name}' 빌드 완료")
            return True

        except FileNotFoundError as e:
            logger.error(f"앱 '{app_name}'의 빌드를 중단합니다. (상세: {e})")
            return False
        except Exception as e:
            logger.error(
                f"앱 '{app_name}' (타입: {app_type}) 빌드 중 예상치 못한 오류 발생: {e}",
            )
            if logger._level.value <= LogLevel.DEBUG.value:
                import traceback

                logger.debug(traceback.format_exc())
            return False

    def _build_helm(self, app_info: AppInfoScheme, spec_obj: AppPullHelmSpec):
        """Helm 차트 빌드"""
        # 대상 디렉토리 결정
        app_build_dest = spec_obj.dest or spec_obj.chart
        app_final_build_path = self.build_dir / app_build_dest

        # 기존 빌드 디렉토리 정리
        if app_final_build_path.exists():
            logger.verbose(f"기존 앱 빌드 디렉토리 삭제: {app_final_build_path}")
            shutil.rmtree(app_final_build_path)

        # 소스 차트 경로
        prepared_chart_name = spec_obj.dest or spec_obj.chart
        source_chart_path = self.charts_dir / prepared_chart_name

        # 소스 확인
        if not source_chart_path.exists() or not source_chart_path.is_dir():
            logger.error(
                f"앱 '{app_info.name}': `prepare` 단계에서 준비된 Helm 차트 소스를 찾을 수 없습니다: {source_chart_path}",
            )
            logger.warning(
                "'sbkube prepare' 명령을 먼저 실행했는지, 'dest' 필드가 올바른지 확인하세요.",
            )
            raise FileNotFoundError(f"Prepared chart not found: {source_chart_path}")

        # 차트 복사
        logger.info(f"Helm 차트 복사: {source_chart_path} → {app_final_build_path}")
        shutil.copytree(source_chart_path, app_final_build_path, dirs_exist_ok=True)

        # Overrides 적용
        self._apply_overrides(
            app_info.name,
            app_build_dest,
            app_final_build_path,
            spec_obj.overrides,
        )

        # Removes 적용
        self._apply_removes(app_final_build_path, spec_obj.removes)

    def _build_git(self, app_info: AppInfoScheme, spec_obj: AppPullGitSpec):
        """Git 소스 빌드"""
        # 준비된 Git 저장소 경로
        prepared_repo_path = self.repos_dir / spec_obj.repo

        if not prepared_repo_path.exists() or not prepared_repo_path.is_dir():
            logger.error(
                f"앱 '{app_info.name}': `prepare` 단계에서 준비된 Git 저장소 소스를 찾을 수 없습니다: {prepared_repo_path}",
            )
            logger.warning("'sbkube prepare' 명령을 먼저 실행했는지 확인하세요.")
            raise FileNotFoundError(
                f"Prepared Git repo not found: {prepared_repo_path}",
            )

        # 각 path 처리
        for copy_pair in spec_obj.paths:
            dest_build_path = self.build_dir / copy_pair.dest
            source_path = prepared_repo_path / copy_pair.src

            if not source_path.exists():
                logger.error(f"Git 소스 경로 없음: {source_path} (건너뜀)")
                continue

            # 기존 빌드 디렉토리 정리
            if dest_build_path.exists():
                logger.verbose(f"기존 빌드 디렉토리 삭제: {dest_build_path}")
                shutil.rmtree(dest_build_path)

            # 복사
            logger.info(f"Git 콘텐츠 복사: {source_path} → {dest_build_path}")
            dest_build_path.parent.mkdir(parents=True, exist_ok=True)

            if source_path.is_dir():
                shutil.copytree(source_path, dest_build_path, dirs_exist_ok=True)
            elif source_path.is_file():
                dest_build_path.mkdir(parents=True, exist_ok=True)
                shutil.copy2(source_path, dest_build_path / source_path.name)
            else:
                logger.warning(
                    f"Git 소스 경로가 파일이나 디렉토리가 아님: {source_path} (건너뜀)",
                )

    def _build_copy(self, app_info: AppInfoScheme, spec_obj: AppCopySpec):
        """로컬 파일 복사"""
        # 각 path 처리
        for copy_pair in spec_obj.paths:
            dest_build_path = self.build_dir / copy_pair.dest

            # 소스 경로 해석
            source_path = Path(copy_pair.src)
            if not source_path.is_absolute():
                source_path = self.app_config_dir / copy_pair.src

            if not source_path.exists():
                logger.error(
                    f"로컬 소스 경로 없음: {source_path} (원본: '{copy_pair.src}') (건너뜀)",
                )
                continue

            # 기존 빌드 디렉토리 정리
            if dest_build_path.exists():
                logger.verbose(f"기존 빌드 디렉토리 삭제: {dest_build_path}")
                shutil.rmtree(dest_build_path)

            # 복사
            logger.info(f"로컬 콘텐츠 복사: {source_path} → {dest_build_path}")
            dest_build_path.parent.mkdir(parents=True, exist_ok=True)

            if source_path.is_dir():
                shutil.copytree(source_path, dest_build_path, dirs_exist_ok=True)
            elif source_path.is_file():
                dest_build_path.mkdir(parents=True, exist_ok=True)
                shutil.copy2(source_path, dest_build_path / source_path.name)
            else:
                logger.warning(
                    f"로컬 소스 경로가 파일이나 디렉토리가 아님: {source_path} (건너뜀)",
                )

    def _build_install_yaml(
        self,
        app_info: AppInfoScheme,
        spec_obj: AppInstallActionSpec,
    ):
        """install-yaml 타입 빌드 - YAML 파일들을 빌드 디렉토리에 준비"""
        app_name = app_info.name
        app_build_dest = app_name  # install-yaml은 앱 이름으로 디렉토리 생성
        app_final_build_path = self.build_dir / app_build_dest

        # 기존 빌드 디렉토리 정리
        if app_final_build_path.exists():
            logger.verbose(f"기존 앱 빌드 디렉토리 삭제: {app_final_build_path}")
            shutil.rmtree(app_final_build_path)

        # 빌드 디렉토리 생성
        app_final_build_path.mkdir(parents=True, exist_ok=True)

        # 각 action 처리
        for action in spec_obj.actions:
            action_path = action.path

            # 절대 경로가 아닌 경우 app_config_dir 기준으로 해석
            if not Path(action_path).is_absolute():
                source_path = self.app_config_dir / action_path
            else:
                source_path = Path(action_path)

            # 파일이 존재하는지 확인
            if not source_path.exists():
                logger.warning(
                    f"install-yaml 액션 파일 없음: {source_path} (원본: '{action_path}') (건너뜀)",
                )
                continue

            # 파일인지 확인
            if not source_path.is_file():
                logger.warning(
                    f"install-yaml 액션 경로가 파일이 아님: {source_path} (건너뜀)",
                )
                continue

            # 대상 파일명 결정 (원본 파일명 유지)
            dest_file_path = app_final_build_path / source_path.name

            # 파일 복사
            logger.info(f"install-yaml 파일 복사: {source_path} → {dest_file_path}")
            shutil.copy2(source_path, dest_file_path)

    def _apply_overrides(
        self,
        app_name: str,
        dest_name: str,
        build_path: Path,
        overrides: list[str],
    ):
        """Override 파일 적용"""
        if not overrides:
            return

        logger.verbose("Overrides 적용 중...")

        for override_rel_path in overrides:
            override_src = self.overrides_dir / dest_name / override_rel_path
            override_dst = build_path / override_rel_path

            if override_src.exists() and override_src.is_file():
                override_dst.parent.mkdir(parents=True, exist_ok=True)
                shutil.copy2(override_src, override_dst)
                logger.verbose(f"Override 적용: {override_src} → {override_dst}")
            else:
                logger.warning(f"Override 원본 파일 없음 (건너뜀): {override_src}")

    def _apply_removes(self, build_path: Path, removes: list[str]):
        """Remove 파일/디렉토리 처리"""
        if not removes:
            return

        logger.verbose("Removes 적용 중...")

        for remove_rel_path in removes:
            target = build_path / remove_rel_path

            if target.exists():
                if target.is_file():
                    target.unlink()
                    logger.verbose(f"파일 삭제: {target}")
                elif target.is_dir():
                    shutil.rmtree(target)
                    logger.verbose(f"디렉토리 삭제: {target}")
            else:
                logger.warning(f"삭제할 파일/디렉토리 없음 (건너뜀): {target}")


@click.command(name="build")
@common_click_options
@click.pass_context
def cmd(
    ctx,
    app_config_dir_name: str,
    base_dir: str,
    config_file_name: str | None,
    app_name: str | None,
    verbose: bool,
    debug: bool,
):
    """앱 설정을 기반으로 빌드 디렉토리에 배포 가능한 형태로 준비"""
    ctx.ensure_object(dict)
    ctx.obj["verbose"] = verbose
    ctx.obj["debug"] = debug
    setup_logging_from_context(ctx)

    build_cmd = BuildCommand(
        base_dir=base_dir,
        app_config_dir=app_config_dir_name,
        target_app_name=app_name,
        config_file_name=config_file_name,
    )

    build_cmd.execute()
