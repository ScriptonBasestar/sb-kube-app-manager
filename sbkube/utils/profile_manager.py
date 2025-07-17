from pathlib import Path
from typing import Dict, Any, Optional, List
import yaml
from sbkube.utils.logger import logger


class ProfileManager:
    """환경별 프로파일 관리"""
    
    def __init__(self, base_dir: str, app_config_dir: str):
        self.base_dir = Path(base_dir)
        self.app_config_dir = self.base_dir / app_config_dir
        self.available_profiles = self._discover_profiles()
    
    def load_profile(self, profile_name: str = None) -> Dict[str, Any]:
        """프로파일 로드 및 병합"""
        if profile_name and profile_name not in self.available_profiles:
            raise ValueError(f"Profile '{profile_name}' not found. Available: {self.available_profiles}")
        
        # 기본 설정 로드
        base_config = self._load_base_config()
        
        if not profile_name:
            return base_config
        
        # 프로파일 설정 로드 및 병합
        profile_config = self._load_profile_config(profile_name)
        merged_config = self._merge_configs(base_config, profile_config)
        
        # Values 파일 경로 해결
        self._resolve_values_paths(merged_config, profile_name)
        
        return merged_config
    
    def _discover_profiles(self) -> List[str]:
        """사용 가능한 프로파일 발견"""
        profiles = []
        pattern = "config-*.yaml"
        
        for config_file in self.app_config_dir.glob(pattern):
            profile_name = config_file.stem.replace('config-', '')
            profiles.append(profile_name)
        
        return sorted(profiles)
    
    def _load_base_config(self) -> Dict[str, Any]:
        """기본 설정 파일 로드"""
        config_file = self.app_config_dir / "config.yaml"
        
        if not config_file.exists():
            raise FileNotFoundError(f"Base config file not found: {config_file}")
        
        with open(config_file, 'r', encoding='utf-8') as f:
            return yaml.safe_load(f) or {}
    
    def _load_profile_config(self, profile_name: str) -> Dict[str, Any]:
        """프로파일 설정 파일 로드"""
        config_file = self.app_config_dir / f"config-{profile_name}.yaml"
        
        if not config_file.exists():
            logger.warning(f"Profile config file not found: {config_file}")
            return {}
        
        with open(config_file, 'r', encoding='utf-8') as f:
            return yaml.safe_load(f) or {}
    
    def _merge_configs(self, base: Dict[str, Any], profile: Dict[str, Any]) -> Dict[str, Any]:
        """설정 병합 (deep merge)"""
        result = base.copy()
        
        for key, value in profile.items():
            if key in result and isinstance(result[key], dict) and isinstance(value, dict):
                result[key] = self._merge_configs(result[key], value)
            else:
                result[key] = value
        
        return result
    
    def _resolve_values_paths(self, config: Dict[str, Any], profile_name: str):
        """Values 파일 경로 자동 해결"""
        if 'apps' not in config:
            return
        
        for app in config['apps']:
            if app.get('type') == 'install-helm' and 'specs' in app:
                specs = app['specs']
                if 'values' in specs:
                    resolved_values = []
                    for value_file in specs['values']:
                        # 프로파일별 values 파일 우선 검색
                        profile_value_path = f"values/{profile_name}/{value_file}"
                        common_value_path = f"values/common/{value_file}"
                        default_value_path = f"values/{value_file}"
                        
                        if (self.base_dir / profile_value_path).exists():
                            resolved_values.append(profile_value_path)
                        elif (self.base_dir / common_value_path).exists():
                            resolved_values.append(common_value_path)
                        elif (self.base_dir / default_value_path).exists():
                            resolved_values.append(default_value_path)
                        else:
                            logger.warning(f"Values file not found: {value_file}")
                            resolved_values.append(value_file)  # 원본 유지
                    
                    specs['values'] = resolved_values
    
    def validate_profile(self, profile_name: str) -> Dict[str, Any]:
        """프로파일 검증"""
        result = {
            "profile": profile_name,
            "valid": True,
            "errors": [],
            "warnings": []
        }
        
        try:
            config = self.load_profile(profile_name)
            
            # 기본 검증
            if not config.get('namespace'):
                result["errors"].append("namespace is required")
            
            if not config.get('apps'):
                result["warnings"].append("no apps defined")
            
            # 앱별 검증
            for app in config.get('apps', []):
                if not app.get('name'):
                    result["errors"].append(f"app name is required")
                
                if app.get('type') == 'install-helm':
                    if not app.get('specs', {}).get('path'):
                        result["errors"].append(f"helm path is required for app: {app.get('name')}")
            
        except Exception as e:
            result["errors"].append(str(e))
        
        result["valid"] = len(result["errors"]) == 0
        return result
    
    def list_profiles(self) -> List[Dict[str, Any]]:
        """프로파일 목록 및 정보 반환"""
        profiles = []
        
        for profile_name in self.available_profiles:
            try:
                config = self.load_profile(profile_name)
                validation = self.validate_profile(profile_name)
                
                profiles.append({
                    "name": profile_name,
                    "namespace": config.get('namespace', 'default'),
                    "apps_count": len(config.get('apps', [])),
                    "valid": validation["valid"],
                    "errors": len(validation["errors"]),
                    "warnings": len(validation["warnings"])
                })
            except Exception as e:
                profiles.append({
                    "name": profile_name,
                    "namespace": "unknown",
                    "apps_count": 0,
                    "valid": False,
                    "errors": 1,
                    "warnings": 0,
                    "error_message": str(e)
                })
        
        return profiles


class ConfigPriority:
    """설정 우선순위 관리"""
    
    PRIORITY_ORDER = [
        "command_line_args",    # 1. 명령행 인수 (최고 우선순위)
        "environment_variables", # 2. 환경 변수
        "profile_config",       # 3. 프로파일 설정 파일
        "base_config",          # 4. 기본 설정 파일 (최저 우선순위)
    ]
    
    @classmethod
    def apply_overrides(cls, base_config: Dict[str, Any], 
                       profile_config: Dict[str, Any] = None,
                       env_overrides: Dict[str, Any] = None,
                       cli_overrides: Dict[str, Any] = None) -> Dict[str, Any]:
        """우선순위에 따른 설정 적용"""
        result = base_config.copy()
        
        # 프로파일 설정 적용
        if profile_config:
            result = cls._deep_merge(result, profile_config)
        
        # 환경변수 오버라이드 적용
        if env_overrides:
            result = cls._deep_merge(result, env_overrides)
        
        # CLI 인수 오버라이드 적용 (최고 우선순위)
        if cli_overrides:
            result = cls._deep_merge(result, cli_overrides)
        
        return result
    
    @staticmethod
    def _deep_merge(base: Dict[str, Any], override: Dict[str, Any]) -> Dict[str, Any]:
        """딥 머지 구현"""
        result = base.copy()
        
        for key, value in override.items():
            if (key in result and 
                isinstance(result[key], dict) and 
                isinstance(value, dict)):
                result[key] = ConfigPriority._deep_merge(result[key], value)
            else:
                result[key] = value
        
        return result


class ProfileInheritance:
    """프로파일 상속 관리"""
    
    def __init__(self, profile_manager: ProfileManager):
        self.profile_manager = profile_manager
    
    def load_with_inheritance(self, profile_name: str) -> Dict[str, Any]:
        """상속을 고려한 프로파일 로드"""
        visited = set()
        return self._load_recursive(profile_name, visited)
    
    def _load_recursive(self, profile_name: str, visited: set) -> Dict[str, Any]:
        """재귀적 상속 로드"""
        if profile_name in visited:
            raise ValueError(f"Circular inheritance detected: {profile_name}")
        
        visited.add(profile_name)
        
        # 프로파일 설정 로드
        config = self.profile_manager._load_profile_config(profile_name)
        
        # 상속 확인
        if 'inherits' in config:
            parent_profile = config.pop('inherits')
            parent_config = self._load_recursive(parent_profile, visited.copy())
            
            # 부모 설정과 병합
            config = self.profile_manager._merge_configs(parent_config, config)
        
        return config