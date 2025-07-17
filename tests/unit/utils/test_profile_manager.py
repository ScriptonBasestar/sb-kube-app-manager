import pytest
import tempfile
import yaml
from pathlib import Path
from sbkube.utils.profile_manager import ProfileManager, ConfigPriority, ProfileInheritance


class TestProfileManager:
    def test_discover_profiles(self):
        """프로파일 발견 테스트"""
        with tempfile.TemporaryDirectory() as tmpdir:
            config_dir = Path(tmpdir) / "config"
            config_dir.mkdir()
            
            # 테스트 파일 생성
            (config_dir / "config.yaml").write_text("namespace: default")
            (config_dir / "config-dev.yaml").write_text("namespace: dev")
            (config_dir / "config-prod.yaml").write_text("namespace: prod")
            
            pm = ProfileManager(tmpdir, "config")
            profiles = pm._discover_profiles()
            
            assert "dev" in profiles
            assert "prod" in profiles
            assert len(profiles) == 2
    
    def test_load_profile(self):
        """프로파일 로드 테스트"""
        with tempfile.TemporaryDirectory() as tmpdir:
            self._create_test_configs(tmpdir)
            
            pm = ProfileManager(tmpdir, "config")
            config = pm.load_profile("development")
            
            assert config['namespace'] == 'dev'
            assert config['apps'][0]['name'] == 'test-app'
    
    def test_load_base_config_only(self):
        """기본 설정만 로드 테스트"""
        with tempfile.TemporaryDirectory() as tmpdir:
            self._create_test_configs(tmpdir)
            
            pm = ProfileManager(tmpdir, "config")
            config = pm.load_profile()  # 프로파일 이름 없음
            
            assert config['namespace'] == 'default'
            assert config['apps'][0]['name'] == 'test-app'
    
    def test_merge_configs(self):
        """설정 병합 테스트"""
        pm = ProfileManager(".", "config")
        
        base = {
            "namespace": "default",
            "apps": [{"name": "app1", "replicas": 1}],
            "common": {"debug": False}
        }
        
        profile = {
            "namespace": "prod",
            "apps": [{"name": "app1", "replicas": 3}],
            "common": {"debug": True, "timeout": 30}
        }
        
        merged = pm._merge_configs(base, profile)
        
        assert merged['namespace'] == 'prod'
        assert merged['apps'][0]['replicas'] == 3
        assert merged['common']['debug'] == True
        assert merged['common']['timeout'] == 30
    
    def test_validate_profile(self):
        """프로파일 검증 테스트"""
        with tempfile.TemporaryDirectory() as tmpdir:
            self._create_test_configs(tmpdir)
            
            pm = ProfileManager(tmpdir, "config")
            result = pm.validate_profile("development")
            
            assert result['valid'] == True
            assert len(result['errors']) == 0
    
    def test_validate_invalid_profile(self):
        """잘못된 프로파일 검증 테스트"""
        with tempfile.TemporaryDirectory() as tmpdir:
            config_dir = Path(tmpdir) / "config"
            config_dir.mkdir()
            
            # 잘못된 설정 파일 (namespace 없음)
            invalid_config = {
                "apps": [
                    {
                        "name": "test-app",
                        "type": "install-helm",
                        # specs.path 없음
                    }
                ]
            }
            
            with open(config_dir / "config.yaml", 'w') as f:
                yaml.dump(invalid_config, f)
            
            with open(config_dir / "config-invalid.yaml", 'w') as f:
                yaml.dump({}, f)
            
            pm = ProfileManager(tmpdir, "config")
            result = pm.validate_profile("invalid")
            
            assert result['valid'] == False
            assert len(result['errors']) > 0
            assert "namespace is required" in result['errors']
    
    def test_list_profiles(self):
        """프로파일 목록 테스트"""
        with tempfile.TemporaryDirectory() as tmpdir:
            self._create_test_configs(tmpdir)
            
            pm = ProfileManager(tmpdir, "config")
            profiles = pm.list_profiles()
            
            assert len(profiles) == 1
            assert profiles[0]['name'] == 'development'
            assert profiles[0]['namespace'] == 'dev'
            assert profiles[0]['apps_count'] == 1
            assert profiles[0]['valid'] == True
    
    def test_resolve_values_paths(self):
        """Values 파일 경로 해결 테스트"""
        with tempfile.TemporaryDirectory() as tmpdir:
            # 디렉토리 구조 생성
            config_dir = Path(tmpdir) / "config"
            values_dir = Path(tmpdir) / "values"
            dev_values_dir = values_dir / "development"
            common_values_dir = values_dir / "common"
            
            config_dir.mkdir()
            values_dir.mkdir()
            dev_values_dir.mkdir()
            common_values_dir.mkdir()
            
            # Values 파일 생성
            (dev_values_dir / "app-values.yaml").write_text("replicas: 2")
            (common_values_dir / "common-values.yaml").write_text("debug: true")
            (values_dir / "default-values.yaml").write_text("timeout: 30")
            
            # 설정 파일 생성
            base_config = {
                "namespace": "default",
                "apps": [
                    {
                        "name": "test-app",
                        "type": "install-helm",
                        "specs": {
                            "path": "test-chart",
                            "values": [
                                "app-values.yaml",
                                "common-values.yaml", 
                                "default-values.yaml",
                                "nonexistent-values.yaml"
                            ]
                        }
                    }
                ]
            }
            
            dev_config = {"namespace": "dev"}
            
            with open(config_dir / "config.yaml", 'w') as f:
                yaml.dump(base_config, f)
            
            with open(config_dir / "config-development.yaml", 'w') as f:
                yaml.dump(dev_config, f)
            
            pm = ProfileManager(tmpdir, "config")
            config = pm.load_profile("development")
            
            resolved_values = config['apps'][0]['specs']['values']
            
            assert "values/development/app-values.yaml" in resolved_values
            assert "values/common/common-values.yaml" in resolved_values
            assert "values/default-values.yaml" in resolved_values
            assert "nonexistent-values.yaml" in resolved_values  # 원본 유지
    
    def test_profile_not_found(self):
        """존재하지 않는 프로파일 테스트"""
        with tempfile.TemporaryDirectory() as tmpdir:
            self._create_test_configs(tmpdir)
            
            pm = ProfileManager(tmpdir, "config")
            
            with pytest.raises(ValueError, match="Profile 'nonexistent' not found"):
                pm.load_profile("nonexistent")
    
    def test_missing_base_config(self):
        """기본 설정 파일이 없는 경우 테스트"""
        with tempfile.TemporaryDirectory() as tmpdir:
            config_dir = Path(tmpdir) / "config"
            config_dir.mkdir()
            
            pm = ProfileManager(tmpdir, "config")
            
            with pytest.raises(FileNotFoundError, match="Base config file not found"):
                pm.load_profile()
    
    def _create_test_configs(self, tmpdir):
        """테스트용 설정 파일 생성"""
        config_dir = Path(tmpdir) / "config"
        config_dir.mkdir()
        
        base_config = {
            "namespace": "default",
            "apps": [
                {
                    "name": "test-app",
                    "type": "install-helm",
                    "specs": {"path": "test-chart"}
                }
            ]
        }
        
        dev_config = {
            "namespace": "dev",
            "apps": [
                {
                    "name": "test-app",
                    "specs": {"replicas": 1}
                }
            ]
        }
        
        with open(config_dir / "config.yaml", 'w') as f:
            yaml.dump(base_config, f)
        
        with open(config_dir / "config-development.yaml", 'w') as f:
            yaml.dump(dev_config, f)


class TestConfigPriority:
    def test_apply_overrides(self):
        """설정 오버라이드 테스트"""
        base_config = {
            "namespace": "default",
            "apps": [{"name": "app1", "replicas": 1}],
            "settings": {"debug": False, "timeout": 10}
        }
        
        profile_config = {
            "namespace": "staging",
            "apps": [{"name": "app1", "replicas": 2}],
            "settings": {"debug": True}
        }
        
        env_overrides = {
            "apps": [{"name": "app1", "replicas": 3}]
        }
        
        cli_overrides = {
            "namespace": "production",
            "settings": {"timeout": 30}
        }
        
        result = ConfigPriority.apply_overrides(
            base_config, profile_config, env_overrides, cli_overrides
        )
        
        # CLI 오버라이드가 최고 우선순위
        assert result['namespace'] == 'production'
        assert result['settings']['timeout'] == 30
        
        # 환경변수 오버라이드
        assert result['apps'][0]['replicas'] == 3
        
        # 프로파일 설정
        assert result['settings']['debug'] == True
    
    def test_deep_merge(self):
        """딥 머지 테스트"""
        base = {
            "level1": {
                "level2": {
                    "value1": "base",
                    "value2": "keep"
                },
                "simple": "base"
            }
        }
        
        override = {
            "level1": {
                "level2": {
                    "value1": "override",
                    "value3": "new"
                },
                "simple": "override"
            }
        }
        
        result = ConfigPriority._deep_merge(base, override)
        
        assert result['level1']['level2']['value1'] == 'override'
        assert result['level1']['level2']['value2'] == 'keep'
        assert result['level1']['level2']['value3'] == 'new'
        assert result['level1']['simple'] == 'override'


class TestProfileInheritance:
    def test_load_with_inheritance(self):
        """프로파일 상속 테스트"""
        with tempfile.TemporaryDirectory() as tmpdir:
            config_dir = Path(tmpdir) / "config"
            config_dir.mkdir()
            
            # 기본 설정
            base_config = {
                "namespace": "default",
                "apps": [{"name": "app1", "replicas": 1}]
            }
            
            # 부모 프로파일
            parent_config = {
                "namespace": "staging",
                "apps": [{"name": "app1", "replicas": 2}],
                "settings": {"debug": True}
            }
            
            # 자식 프로파일 (부모 상속)
            child_config = {
                "inherits": "staging",
                "namespace": "production",
                "settings": {"timeout": 30}
            }
            
            with open(config_dir / "config.yaml", 'w') as f:
                yaml.dump(base_config, f)
            
            with open(config_dir / "config-staging.yaml", 'w') as f:
                yaml.dump(parent_config, f)
            
            with open(config_dir / "config-production.yaml", 'w') as f:
                yaml.dump(child_config, f)
            
            pm = ProfileManager(tmpdir, "config")
            inheritance = ProfileInheritance(pm)
            
            result = inheritance.load_with_inheritance("production")
            
            # 자식 설정이 우선
            assert result['namespace'] == 'production'
            
            # 부모 설정 상속
            assert result['apps'][0]['replicas'] == 2
            assert result['settings']['debug'] == True
            
            # 자식 고유 설정
            assert result['settings']['timeout'] == 30
    
    def test_circular_inheritance_detection(self):
        """순환 상속 감지 테스트"""
        with tempfile.TemporaryDirectory() as tmpdir:
            config_dir = Path(tmpdir) / "config"
            config_dir.mkdir()
            
            # 순환 상속 설정
            config1 = {"inherits": "profile2"}
            config2 = {"inherits": "profile1"}
            
            with open(config_dir / "config.yaml", 'w') as f:
                yaml.dump({}, f)
            
            with open(config_dir / "config-profile1.yaml", 'w') as f:
                yaml.dump(config1, f)
            
            with open(config_dir / "config-profile2.yaml", 'w') as f:
                yaml.dump(config2, f)
            
            pm = ProfileManager(tmpdir, "config")
            inheritance = ProfileInheritance(pm)
            
            with pytest.raises(ValueError, match="Circular inheritance detected"):
                inheritance.load_with_inheritance("profile1")