import pytest
import tempfile
from pathlib import Path
from unittest.mock import patch, Mock

from sbkube.commands.init import InitCommand


class TestInitCommand:
    def test_init_basic_template(self):
        """기본 템플릿 초기화 테스트"""
        with tempfile.TemporaryDirectory() as tmpdir:
            cmd = InitCommand(
                base_dir=tmpdir,
                template_name="basic",
                project_name="test-project",
                interactive=False
            )
            
            cmd.execute()
            
            # 생성된 파일 확인
            assert (Path(tmpdir) / "config" / "config.yaml").exists()
            assert (Path(tmpdir) / "config" / "sources.yaml").exists()
            assert (Path(tmpdir) / "README.md").exists()
            
            # values 파일 확인
            values_file = Path(tmpdir) / "values" / "test-project-values.yaml"
            assert values_file.exists()
    
    def test_init_non_interactive_mode(self):
        """비대화형 모드 테스트"""
        with tempfile.TemporaryDirectory() as tmpdir:
            cmd = InitCommand(
                base_dir=tmpdir,
                template_name="basic",
                project_name="my-app",
                interactive=False
            )
            
            cmd._set_default_values()
            
            # 기본값이 올바르게 설정되었는지 확인
            assert cmd.template_vars['project_name'] == 'my-app'
            assert cmd.template_vars['app_name'] == 'my-app'
            assert cmd.template_vars['namespace'] == 'my-app'
            assert cmd.template_vars['app_type'] == 'install-helm'
            assert cmd.template_vars['create_environments'] is True
            assert cmd.template_vars['use_bitnami'] is True
    
    def test_template_rendering(self):
        """템플릿 렌더링 테스트"""
        with tempfile.TemporaryDirectory() as tmpdir:
            cmd = InitCommand(
                base_dir=tmpdir,
                template_name="basic",
                project_name="my-app",
                interactive=False
            )
            
            cmd.template_vars = {
                'project_name': 'my-app',
                'app_name': 'my-app',
                'namespace': 'my-app',
                'app_type': 'install-helm'
            }
            
            cmd._create_directory_structure()
            cmd._render_templates()
            
            # config.yaml 내용 확인
            config_file = Path(tmpdir) / "config" / "config.yaml"
            content = config_file.read_text()
            
            assert 'namespace: my-app' in content
            assert 'name: my-app' in content
            assert 'type: install-helm' in content
    
    def test_directory_structure_creation(self):
        """디렉토리 구조 생성 테스트"""
        with tempfile.TemporaryDirectory() as tmpdir:
            cmd = InitCommand(
                base_dir=tmpdir,
                template_name="basic",
                project_name="test-project",
                interactive=False
            )
            
            cmd.template_vars = {
                'create_environments': True,
                'environments': ['dev', 'prod']
            }
            
            cmd._create_directory_structure()
            
            # 기본 디렉토리 확인
            assert (Path(tmpdir) / "config").exists()
            assert (Path(tmpdir) / "values").exists()
            assert (Path(tmpdir) / "manifests").exists()
            
            # 환경별 디렉토리 확인
            assert (Path(tmpdir) / "values" / "dev").exists()
            assert (Path(tmpdir) / "values" / "prod").exists()
            assert (Path(tmpdir) / "config-dev").exists()
            assert (Path(tmpdir) / "config-prod").exists()
    
    def test_environment_configs_creation(self):
        """환경별 설정 파일 생성 테스트"""
        with tempfile.TemporaryDirectory() as tmpdir:
            cmd = InitCommand(
                base_dir=tmpdir,
                template_name="basic",
                project_name="test-app",
                interactive=False
            )
            
            cmd.template_vars = {
                'project_name': 'test-app',
                'app_name': 'test-app',
                'app_type': 'install-helm',
                'create_environments': True,
                'environments': ['staging', 'production']
            }
            
            cmd._create_directory_structure()
            cmd._render_templates()
            
            # 환경별 설정 파일 확인
            staging_config = Path(tmpdir) / "config" / "config-staging.yaml"
            production_config = Path(tmpdir) / "config" / "config-production.yaml"
            
            assert staging_config.exists()
            assert production_config.exists()
            
            # 내용 확인
            staging_content = staging_config.read_text()
            production_content = production_config.read_text()
            
            assert 'namespace: test-app-staging' in staging_content
            assert 'namespace: test-app-production' in production_content
    
    def test_readme_creation(self):
        """README 파일 생성 테스트"""
        with tempfile.TemporaryDirectory() as tmpdir:
            cmd = InitCommand(
                base_dir=tmpdir,
                template_name="basic",
                project_name="my-project",
                interactive=False
            )
            
            cmd.template_vars = {
                'project_name': 'my-project',
                'app_name': 'my-project',
                'create_environments': True
            }
            
            cmd._create_readme()
            
            readme_file = Path(tmpdir) / "README.md"
            assert readme_file.exists()
            
            content = readme_file.read_text()
            assert '# my-project' in content
            assert 'sbkube run' in content
            assert '환경별 설정' in content
    
    def test_template_validation(self):
        """템플릿 검증 테스트"""
        with tempfile.TemporaryDirectory() as tmpdir:
            # 존재하지 않는 템플릿
            cmd = InitCommand(
                base_dir=tmpdir,
                template_name="nonexistent",
                project_name="test",
                interactive=False
            )
            
            with pytest.raises(ValueError, match="템플릿 'nonexistent'을 찾을 수 없습니다"):
                cmd._validate_template()
    
    def test_get_template_dir(self):
        """템플릿 디렉토리 경로 반환 테스트"""
        cmd = InitCommand(
            base_dir="/tmp",
            template_name="basic",
            project_name="test",
            interactive=False
        )
        
        template_dir = cmd._get_template_dir()
        assert template_dir.name == "basic"
        assert "templates" in str(template_dir)
    
    @patch('click.prompt')
    def test_interactive_input(self, mock_prompt):
        """대화형 입력 테스트"""
        mock_prompt.side_effect = [
            'my-project',  # 프로젝트 이름
            'my-namespace',  # 네임스페이스
            'my-app',  # 앱 이름
            'install-yaml'  # 앱 타입
        ]
        
        with patch('click.confirm') as mock_confirm:
            mock_confirm.side_effect = [True, True, False]  # 환경설정, Bitnami, Prometheus
            
            cmd = InitCommand(
                base_dir="/tmp",
                template_name="basic",
                project_name=None,
                interactive=True
            )
            
            cmd._interactive_input()
            
            assert cmd.template_vars['project_name'] == 'my-project'
            assert cmd.template_vars['namespace'] == 'my-namespace'
            assert cmd.template_vars['app_name'] == 'my-app'
            assert cmd.template_vars['app_type'] == 'install-yaml'
            assert cmd.template_vars['create_environments'] is True
            assert cmd.template_vars['use_bitnami'] is True
            assert cmd.template_vars['use_prometheus'] is False
    
    def test_show_next_steps(self):
        """다음 단계 안내 테스트"""
        with tempfile.TemporaryDirectory() as tmpdir:
            cmd = InitCommand(
                base_dir=tmpdir,
                template_name="basic",
                project_name="test-project",
                interactive=False
            )
            
            cmd.template_vars = {
                'app_name': 'test-project',
                'create_environments': True,
                'environments': ['dev', 'prod']
            }
            
            # 파일들을 실제로 생성
            (Path(tmpdir) / "config").mkdir()
            (Path(tmpdir) / "config" / "config.yaml").touch()
            (Path(tmpdir) / "config" / "sources.yaml").touch()
            (Path(tmpdir) / "values").mkdir()
            (Path(tmpdir) / "values" / "test-project-values.yaml").touch()
            (Path(tmpdir) / "README.md").touch()
            
            # 예외 없이 실행되는지 확인
            cmd._show_next_steps()
    
    def test_template_vars_initialization(self):
        """템플릿 변수 초기화 테스트"""
        cmd = InitCommand(
            base_dir="/tmp",
            template_name="basic",
            project_name="test",
            interactive=False
        )
        
        assert cmd.template_vars == {}
        assert cmd.template_name == "basic"
        assert cmd.project_name == "test"
        assert cmd.interactive is False