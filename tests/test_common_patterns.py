"""
공통 패턴 테스트

리팩토링된 코드의 일관성과 공통 기능을 테스트합니다.
"""
import pytest
from pathlib import Path
from sbkube.utils.base_command import BaseCommand
from sbkube.utils.logger import logger, LogLevel, SbkubeLogger
from sbkube.models.config_model import AppInfoScheme


class TestLogger:
    """로거 시스템 테스트"""
    
    def test_log_levels(self):
        """로그 레벨 테스트"""
        test_logger = SbkubeLogger()
        
        # 각 레벨 테스트
        assert test_logger._level == LogLevel.INFO
        
        test_logger.set_level(LogLevel.DEBUG)
        assert test_logger._level == LogLevel.DEBUG
        
        test_logger.set_level(LogLevel.VERBOSE)
        assert test_logger._level == LogLevel.VERBOSE
        
    def test_log_level_filtering(self):
        """로그 레벨 필터링 테스트"""
        test_logger = SbkubeLogger()
        test_logger.set_level(LogLevel.WARNING)
        
        # WARNING 레벨에서는 DEBUG, VERBOSE, INFO가 출력되지 않아야 함
        assert test_logger._level > LogLevel.DEBUG
        assert test_logger._level > LogLevel.VERBOSE
        assert test_logger._level > LogLevel.INFO
        

class TestBaseCommand:
    """BaseCommand 클래스 테스트"""
    
    def test_initialization(self, tmp_path):
        """초기화 테스트"""
        base_cmd = BaseCommand(
            base_dir=str(tmp_path),
            app_config_dir="config",
            cli_namespace="test-ns"
        )
        
        assert base_cmd.base_dir == tmp_path
        assert base_cmd.app_config_dir == tmp_path / "config"
        assert base_cmd.cli_namespace == "test-ns"
        assert base_cmd.build_dir == tmp_path / "config" / "build"
        
    def test_find_config_file(self, tmp_path):
        """설정 파일 찾기 테스트"""
        config_dir = tmp_path / "config"
        config_dir.mkdir()
        
        # YAML 파일 생성
        config_file = config_dir / "config.yaml"
        config_file.write_text("namespace: test\napps: []")
        
        base_cmd = BaseCommand(str(tmp_path), "config")
        found_config = base_cmd.find_config_file()
        
        assert found_config == config_file
        
    def test_find_config_file_priority(self, tmp_path):
        """설정 파일 우선순위 테스트"""
        config_dir = tmp_path / "config"
        config_dir.mkdir()
        
        # 여러 형식의 파일 생성
        yaml_file = config_dir / "config.yaml"
        yaml_file.write_text("namespace: yaml")
        
        yml_file = config_dir / "config.yml"
        yml_file.write_text("namespace: yml")
        
        toml_file = config_dir / "config.toml"
        toml_file.write_text('namespace = "toml"')
        
        base_cmd = BaseCommand(str(tmp_path), "config")
        found_config = base_cmd.find_config_file()
        
        # .yaml이 최우선
        assert found_config == yaml_file
        
    def test_namespace_priority(self, tmp_path):
        """네임스페이스 우선순위 테스트"""
        base_cmd = BaseCommand(
            base_dir=str(tmp_path),
            app_config_dir="config",
            cli_namespace="cli-ns"
        )
        
        # CLI 네임스페이스가 최우선
        app_info = AppInfoScheme(
            name="test-app",
            type="install-helm",
            namespace="app-ns",
            specs={}
        )
        
        assert base_cmd.get_namespace(app_info) == "cli-ns"
        
        # CLI 없으면 앱 네임스페이스
        base_cmd.cli_namespace = None
        assert base_cmd.get_namespace(app_info) == "app-ns"
        
        # 특수값은 무시
        app_info.namespace = "!ignore"
        assert base_cmd.get_namespace(app_info) is None
        
    def test_parse_apps_filtering(self, tmp_path):
        """앱 필터링 테스트"""
        base_cmd = BaseCommand(str(tmp_path), "config")
        base_cmd.apps_config_dict = {
            "apps": [
                {"name": "helm-app", "type": "install-helm", "specs": {"values": []}},
                {"name": "yaml-app", "type": "install-yaml", "specs": {"actions": []}},
                {"name": "exec-app", "type": "exec", "specs": {"commands": []}}
            ]
        }
        
        # 특정 타입만 필터링
        apps = base_cmd.parse_apps(app_types=["install-helm"])
        assert len(apps) == 1
        assert apps[0].name == "helm-app"
        
        # 특정 앱 이름 필터링
        apps = base_cmd.parse_apps(app_name="yaml-app")
        assert len(apps) == 1
        assert apps[0].name == "yaml-app"
        
        # 타입과 이름 조합
        apps = base_cmd.parse_apps(app_types=["exec"], app_name="exec-app")
        assert len(apps) == 1
        assert apps[0].type == "exec"
        

class TestCommandConsistency:
    """명령어 간 일관성 테스트"""
    
    def test_common_options(self):
        """공통 옵션 확인"""
        from sbkube.commands import deploy, build
        
        # 모든 명령어가 verbose와 debug 옵션을 가져야 함
        deploy_params = [p.name for p in deploy.cmd.params]
        build_params = [p.name for p in build.cmd.params]
        
        assert "verbose" in deploy_params
        assert "debug" in deploy_params
        assert "verbose" in build_params
        assert "debug" in build_params
        
    def test_error_handling_patterns(self, tmp_path):
        """에러 처리 패턴 테스트"""
        base_cmd = BaseCommand(str(tmp_path), "config")
        
        # 존재하지 않는 설정 파일
        with pytest.raises(SystemExit):
            base_cmd.find_config_file()
            
        # 잘못된 앱 설정
        base_cmd.apps_config_dict = {
            "apps": [
                {"name": "invalid-app"}  # type 필드 누락
            ]
        }
        
        # 에러가 발생해도 계속 진행
        apps = base_cmd.parse_apps()
        assert len(apps) == 0  # 잘못된 앱은 건너뜀
        

class TestPathResolution:
    """경로 해석 테스트"""
    
    def test_absolute_vs_relative_paths(self, tmp_path):
        """절대 경로 vs 상대 경로 처리"""
        base_cmd = BaseCommand(str(tmp_path), "config")
        
        # 디렉토리 생성
        base_cmd.ensure_directory(base_cmd.build_dir, "빌드 디렉토리")
        assert base_cmd.build_dir.exists()
        
        # 디렉토리 정리
        test_file = base_cmd.build_dir / "test.txt"
        test_file.write_text("test")
        
        base_cmd.clean_directory(base_cmd.build_dir, "빌드 디렉토리")
        assert base_cmd.build_dir.exists()
        assert not test_file.exists()  # 내용은 삭제됨 