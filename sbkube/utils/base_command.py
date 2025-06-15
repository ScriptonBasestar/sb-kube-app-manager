"""
Command 공통 베이스 클래스

모든 sbkube command가 상속받아 사용할 공통 기능 제공
"""
import click
from pathlib import Path
from typing import Optional, Dict, Any, List
from sbkube.utils.file_loader import load_config_file
from sbkube.utils.logger import logger, setup_logging_from_context
from sbkube.models.config_model import AppInfoScheme, AppGroupScheme


class BaseCommand:
    """모든 Command의 베이스 클래스"""
    
    def __init__(self, base_dir: str = ".", app_config_dir: str = "config", 
                 cli_namespace: Optional[str] = None, config_file_name: Optional[str] = None):
        """
        Args:
            base_dir: 프로젝트 루트 디렉토리
            app_config_dir: 앱 설정 디렉토리 이름 
            cli_namespace: CLI로 지정된 네임스페이스
            config_file_name: 사용할 설정 파일 이름
        """
        self.base_dir = Path(base_dir).resolve()
        self.app_config_dir = self.base_dir / app_config_dir
        self.cli_namespace = cli_namespace
        self.config_file_name = config_file_name
        
        # 공통 디렉토리 설정
        self.build_dir = self.app_config_dir / "build"
        self.values_dir = self.app_config_dir / "values"
        self.overrides_dir = self.app_config_dir / "overrides"
        self.charts_dir = self.base_dir / "charts"
        self.repos_dir = self.base_dir / "repos"
        
        # 설정 파일과 앱 목록
        self.config_file_path: Optional[Path] = None
        self.apps_config_dict: Dict[str, Any] = {}
        self.app_info_list: List[AppInfoScheme] = []
        
    def find_config_file(self) -> Path:
        """설정 파일 찾기 (config.yaml, config.yml, config.toml)"""
        if self.config_file_name:
            # --config-file 옵션이 지정된 경우
            config_path = self.app_config_dir / self.config_file_name
            if not config_path.exists() or not config_path.is_file():
                logger.error(f"지정된 설정 파일을 찾을 수 없습니다: {config_path}")
                raise click.Abort()
            return config_path
        else:
            # 자동 탐색
            for ext in [".yaml", ".yml", ".toml"]:
                candidate = self.app_config_dir / f"config{ext}"
                if candidate.exists() and candidate.is_file():
                    return candidate
            
            logger.error(f"앱 설정 파일이 존재하지 않습니다: {self.app_config_dir}/config.[yaml|yml|toml]")
            raise click.Abort()
    
    def load_config(self) -> Dict[str, Any]:
        """설정 파일 로드"""
        self.config_file_path = self.find_config_file()
        logger.info(f"설정 파일 사용: {self.config_file_path}")
        self.apps_config_dict = load_config_file(str(self.config_file_path))
        return self.apps_config_dict
    
    def parse_apps(self, app_types: Optional[List[str]] = None, app_name: Optional[str] = None) -> List[AppInfoScheme]:
        """
        앱 정보 파싱 및 필터링
        
        Args:
            app_types: 처리할 앱 타입 리스트 (None이면 모든 타입)
            app_name: 특정 앱 이름 (None이면 모든 앱)
            
        Returns:
            필터링된 AppInfoScheme 리스트
        """
        parsed_apps = []
        
        for app_dict in self.apps_config_dict.get("apps", []):
            try:
                app_info = AppInfoScheme(**app_dict)
                
                # 타입 필터링
                if app_types and app_info.type not in app_types:
                    if app_name and app_info.name == app_name:
                        logger.warning(f"앱 '{app_info.name}' (타입: {app_info.type}): 이 명령에서 지원하지 않는 타입입니다.")
                    continue
                    
                # 이름 필터링
                if app_name and app_info.name != app_name:
                    continue
                    
                parsed_apps.append(app_info)
                
            except Exception as e:
                app_name_for_error = app_dict.get('name', '알 수 없는 앱')
                logger.error(f"앱 정보 '{app_name_for_error}' 처리 중 오류 발생: {e}")
                logger.warning(f"해당 앱 설정을 건너뜁니다: {app_dict}")
                continue
        
        # 특정 앱을 찾지 못한 경우
        if app_name and not parsed_apps:
            logger.error(f"지정된 앱 '{app_name}'을 찾을 수 없습니다.")
            raise click.Abort()
            
        self.app_info_list = parsed_apps
        return parsed_apps
    
    def get_namespace(self, app_info: AppInfoScheme) -> Optional[str]:
        """
        앱의 네임스페이스 결정
        우선순위: CLI > 앱 설정 > 전역 설정
        """
        if self.cli_namespace:
            return self.cli_namespace
            
        if app_info.namespace and app_info.namespace not in ["!ignore", "!none", "!false", ""]:
            return app_info.namespace
            
        global_ns = self.apps_config_dict.get("namespace")
        if global_ns and global_ns not in ["!ignore", "!none", "!false", ""]:
            return global_ns
            
        return None
    
    def ensure_directory(self, path: Path, description: str = "디렉토리"):
        """디렉토리 존재 확인 및 생성"""
        try:
            path.mkdir(parents=True, exist_ok=True)
            logger.verbose(f"{description} 준비 완료: {path}")
        except OSError as e:
            logger.error(f"{description} 생성 실패: {e}")
            raise click.Abort()
    
    def clean_directory(self, path: Path, description: str = "디렉토리"):
        """디렉토리 정리 (삭제 후 재생성)"""
        import shutil
        try:
            if path.exists():
                shutil.rmtree(path)
                logger.verbose(f"기존 {description} 삭제: {path}")
            path.mkdir(parents=True, exist_ok=True)
            logger.verbose(f"{description} 준비 완료: {path}")
        except OSError as e:
            logger.error(f"{description} 정리/생성 실패: {e}")
            raise click.Abort() 