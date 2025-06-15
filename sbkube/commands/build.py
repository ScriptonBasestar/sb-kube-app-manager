import shutil
import click
from pathlib import Path
from typing import Optional, List

from sbkube.utils.base_command import BaseCommand
from sbkube.utils.common import common_click_options
from sbkube.utils.logger import logger, setup_logging_from_context
from sbkube.models.config_model import (
    AppInfoScheme,
    AppPullHelmSpec,
    AppPullHelmOciSpec,
    AppPullGitSpec,
    AppCopySpec,
)


class BuildCommand(BaseCommand):
    """Build 명령 구현"""
    
    def __init__(self, base_dir: str, app_config_dir: str, 
                 app_name: Optional[str], config_file_name: Optional[str]):
        super().__init__(base_dir, app_config_dir, None, config_file_name)
        self.target_app_name = app_name
        
    def execute(self):
        """build 명령 실행"""
        self.execute_pre_hook()
        logger.heading(f"Build 시작 - app-dir: {self.app_config_dir.name}")
        
        # 설정 파일 로드
        self.load_config()
        
        # 빌드 디렉토리 준비
        self._prepare_build_directory()
        
        # 지원하는 앱 타입
        supported_types = ["pull-helm", "pull-helm-oci", "pull-git", "copy-app"]
        
        # 앱 파싱
        self.parse_apps(app_types=supported_types, app_name=self.target_app_name)
        
        if not self.app_info_list:
            if self.target_app_name:
                logger.warning(f"앱 '{self.target_app_name}'은 빌드 대상이 아닙니다.")
            else:
                logger.warning("빌드할 앱이 설정 파일에 없거나, 지원하는 타입의 앱이 없습니다.")
            logger.heading("Build 작업 완료 (처리할 앱 없음)")
            return
            
        # 빌드 통계
        total_apps = len(self.app_info_list)
        success_apps = 0
        
        # 각 앱 빌드
        for app_info in self.app_info_list:
            if self._build_app(app_info):
                success_apps += 1
                
        # 결과 출력
        if total_apps > 0:
            logger.success(f"Build 작업 요약: 총 {total_apps}개 앱 중 {success_apps}개 성공")
            
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
            # Spec 모델 생성
            spec_obj = self._create_spec(app_info)
            if not spec_obj:
                return False
                
            # 타입별 빌드 처리
            if app_type in ["pull-helm", "pull-helm-oci"]:
                self._build_helm(app_info, spec_obj)
            elif app_type == "pull-git":
                self._build_git(app_info, spec_obj)
            elif app_type == "copy-app":
                self._build_copy(app_info, spec_obj)
                
            logger.success(f"앱 '{app_name}' 빌드 완료")
            return True
            
        except FileNotFoundError as e:
            logger.error(f"앱 '{app_name}'의 빌드를 중단합니다. (상세: {e})")
            return False
        except Exception as e:
            logger.error(f"앱 '{app_name}' (타입: {app_type}) 빌드 중 예상치 못한 오류 발생: {e}")
            if logger._level.value <= logger.LogLevel.DEBUG.value:
                import traceback
                logger.debug(traceback.format_exc())
            return False
            
    def _create_spec(self, app_info: AppInfoScheme):
        """앱 타입에 맞는 Spec 객체 생성"""
        try:
            if app_info.type == "pull-helm":
                return AppPullHelmSpec(**app_info.specs)
            elif app_info.type == "pull-helm-oci":
                return AppPullHelmOciSpec(**app_info.specs)
            elif app_info.type == "pull-git":
                return AppPullGitSpec(**app_info.specs)
            elif app_info.type == "copy-app":
                return AppCopySpec(**app_info.specs)
        except Exception as e:
            logger.error(f"앱 '{app_info.name}' (타입: {app_info.type})의 Spec 데이터 검증/변환 중 오류: {e}")
            logger.warning(f"이 앱의 빌드를 건너뜁니다. Specs: {app_info.specs}")
            return None
            
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
            logger.error(f"앱 '{app_info.name}': `prepare` 단계에서 준비된 Helm 차트 소스를 찾을 수 없습니다: {source_chart_path}")
            logger.warning("'sbkube prepare' 명령을 먼저 실행했는지, 'dest' 필드가 올바른지 확인하세요.")
            raise FileNotFoundError(f"Prepared chart not found: {source_chart_path}")
            
        # 차트 복사
        logger.info(f"Helm 차트 복사: {source_chart_path} → {app_final_build_path}")
        shutil.copytree(source_chart_path, app_final_build_path, dirs_exist_ok=True)
        
        # Overrides 적용
        self._apply_overrides(app_info.name, app_build_dest, app_final_build_path, spec_obj.overrides)
        
        # Removes 적용
        self._apply_removes(app_final_build_path, spec_obj.removes)
        
    def _build_git(self, app_info: AppInfoScheme, spec_obj: AppPullGitSpec):
        """Git 소스 빌드"""
        # 준비된 Git 저장소 경로
        prepared_repo_path = self.repos_dir / spec_obj.repo
        
        if not prepared_repo_path.exists() or not prepared_repo_path.is_dir():
            logger.error(f"앱 '{app_info.name}': `prepare` 단계에서 준비된 Git 저장소 소스를 찾을 수 없습니다: {prepared_repo_path}")
            logger.warning("'sbkube prepare' 명령을 먼저 실행했는지 확인하세요.")
            raise FileNotFoundError(f"Prepared Git repo not found: {prepared_repo_path}")
            
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
                logger.warning(f"Git 소스 경로가 파일이나 디렉토리가 아님: {source_path} (건너뜀)")
                
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
                logger.error(f"로컬 소스 경로 없음: {source_path} (원본: '{copy_pair.src}') (건너뜀)")
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
                logger.warning(f"로컬 소스 경로가 파일이나 디렉토리가 아님: {source_path} (건너뜀)")
                
    def _apply_overrides(self, app_name: str, dest_name: str, build_path: Path, overrides: List[str]):
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
                
    def _apply_removes(self, build_path: Path, removes: List[str]):
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
def cmd(ctx, app_config_dir_name: str, base_dir: str, app_name: str | None, config_file_name: str | None, verbose: bool, debug: bool):
    """
    `prepare` 단계의 결과물과 로컬 소스를 사용하여 배포 가능한 애플리케이션 빌드 결과물을 생성합니다.

    이 명령어는 `config.[yaml|toml]` 파일에 정의된 'pull-helm', 'pull-helm-oci', 
    'pull-git', 'copy-app' 타입의 애플리케이션들을 주로 대상으로 하며,
    이들의 소스를 `<base_dir>/<app_dir>/build/<app_name>/` 경로에 최종 빌드합니다.

    주요 작업:
    - 대상 앱 타입: 'pull-helm', 'pull-helm-oci', 'pull-git', 'copy-app'.
      (다른 타입의 앱은 이 단계에서 특별한 빌드 로직이 없을 수 있습니다.)
    - Helm 차트 준비:
        - `prepare` 단계에서 다운로드된 Helm 차트 (`<base_dir>/charts/...`)를 
          빌드 디렉토리 (`<app_dir>/build/<app_name>`)로 복사합니다.
        - `specs.overrides`: 지정된 파일들을 빌드된 차트 내에 덮어씁니다.
          (원본은 `<app_dir>/overrides/<app_name>/...` 경로에서 가져옴)
        - `specs.removes`: 빌드된 차트 내에서 지정된 파일 또는 디렉토리를 삭제합니다.
    - Git 소스 준비:
        - `prepare` 단계에서 클론된 Git 저장소 (`<base_dir>/repos/...`)의 내용을
          `specs.paths` 정의에 따라 빌드 디렉토리로 복사합니다.
    - 로컬 파일 복사 (`copy-app` 타입):
        - `specs.paths`에 정의된 로컬 파일/디렉토리를 빌드 디렉토리로 복사합니다.

    빌드 결과물은 주로 `template` 또는 `deploy` 명령어에서 사용됩니다.
    빌드 작업 전, 기존 빌드 디렉토리 (`<app_dir>/build/`)는 삭제됩니다.
    """
    ctx.ensure_object(dict)
    ctx.obj['verbose'] = verbose
    ctx.obj['debug'] = debug
    setup_logging_from_context(ctx)
    
    build_cmd = BuildCommand(
        base_dir=base_dir,
        app_config_dir=app_config_dir_name,
        app_name=app_name,
        config_file_name=config_file_name
    )
    
    build_cmd.execute()
