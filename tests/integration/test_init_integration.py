from click.testing import CliRunner
import pytest
import tempfile
from pathlib import Path
from unittest.mock import patch

from sbkube.cli import main
from sbkube.commands.init import cmd


class TestInitIntegration:
    def test_init_command_in_main_cli(self):
        """메인 CLI에서 init 명령어 확인"""
        runner = CliRunner()
        result = runner.invoke(main, ['--help'])
        
        assert result.exit_code == 0
        assert 'init' in result.output
        assert '새 프로젝트를 초기화' in result.output
    
    def test_init_help_message(self):
        """init 명령어 도움말 메시지"""
        runner = CliRunner()
        result = runner.invoke(main, ['init', '--help'])
        
        assert result.exit_code == 0
        assert '새 프로젝트를 초기화합니다' in result.output
        assert '--template' in result.output
        assert '--name' in result.output
        assert '--non-interactive' in result.output
        assert '--force' in result.output
        assert '사용 예시:' in result.output
    
    @patch('sbkube.commands.init.InitCommand.execute')
    def test_init_basic_execution(self, mock_execute):
        """기본 init 명령어 실행 테스트"""
        runner = CliRunner()
        
        with runner.isolated_filesystem():
            result = runner.invoke(main, ['init', '--non-interactive'])
            
            assert result.exit_code == 0
            mock_execute.assert_called_once()
    
    @patch('sbkube.commands.init.InitCommand.execute')
    def test_init_with_all_options(self, mock_execute):
        """모든 옵션을 포함한 init 명령어 실행 테스트"""
        runner = CliRunner()
        
        with runner.isolated_filesystem():
            result = runner.invoke(main, [
                'init',
                '--template', 'basic',
                '--name', 'my-project',
                '--non-interactive',
                '--force'
            ])
            
            assert result.exit_code == 0
            mock_execute.assert_called_once()
    
    def test_init_parameter_passing(self):
        """init 명령어 매개변수 전달 테스트"""
        runner = CliRunner()
        
        with patch('sbkube.commands.init.InitCommand') as mock_init_command:
            mock_instance = mock_init_command.return_value
            
            with runner.isolated_filesystem():
                result = runner.invoke(main, [
                    'init',
                    '--template', 'basic',
                    '--name', 'test-project',
                    '--non-interactive'
                ])
                
                # InitCommand가 올바른 매개변수로 생성되었는지 확인
                mock_init_command.assert_called_once()
                args, kwargs = mock_init_command.call_args
                
                assert kwargs['template_name'] == 'basic'
                assert kwargs['project_name'] == 'test-project'
                assert kwargs['interactive'] is False
                
                mock_instance.execute.assert_called_once()
    
    def test_init_existing_files_detection(self):
        """기존 파일 감지 테스트"""
        runner = CliRunner()
        
        with runner.isolated_filesystem():
            # 기존 파일 생성
            Path('config').mkdir()
            Path('config/config.yaml').touch()
            
            # force 옵션 없이 실행 시 확인 메시지
            with patch('click.confirm', return_value=False):
                result = runner.invoke(main, ['init', '--non-interactive'])
                
                assert result.exit_code == 0
                assert '초기화가 취소되었습니다' in result.output
    
    def test_init_force_option(self):
        """force 옵션 테스트"""
        runner = CliRunner()
        
        with patch('sbkube.commands.init.InitCommand.execute') as mock_execute:
            with runner.isolated_filesystem():
                # 기존 파일 생성
                Path('config').mkdir()
                Path('config/config.yaml').touch()
                
                # force 옵션으로 실행
                result = runner.invoke(main, [
                    'init',
                    '--non-interactive',
                    '--force'
                ])
                
                assert result.exit_code == 0
                mock_execute.assert_called_once()
    
    @patch('sbkube.commands.init.InitCommand.execute')
    def test_init_execution_failure(self, mock_execute):
        """init 명령어 실행 실패 테스트"""
        runner = CliRunner()
        mock_execute.side_effect = Exception("Test initialization error")
        
        with runner.isolated_filesystem():
            result = runner.invoke(main, ['init', '--non-interactive'])
            
            assert result.exit_code == 1
            assert "❌ 초기화 실패: Test initialization error" in result.output
    
    def test_init_template_choices(self):
        """템플릿 선택 옵션 테스트"""
        runner = CliRunner()
        
        # 유효한 템플릿 옵션들
        valid_templates = ['basic', 'web-app', 'microservice']
        
        for template in valid_templates:
            with patch('sbkube.commands.init.InitCommand.execute') as mock_execute:
                with runner.isolated_filesystem():
                    result = runner.invoke(main, [
                        'init',
                        '--template', template,
                        '--non-interactive'
                    ])
                    
                    assert result.exit_code == 0, f"Failed with template: {template}"
                    mock_execute.assert_called_once()
    
    def test_init_invalid_template(self):
        """잘못된 템플릿 옵션 테스트"""
        runner = CliRunner()
        
        result = runner.invoke(main, [
            'init',
            '--template', 'invalid-template',
            '--non-interactive'
        ])
        
        # Click이 자동으로 잘못된 선택을 거부함
        assert result.exit_code != 0
    
    @patch('click.confirm')
    @patch('click.prompt')
    def test_init_interactive_mode(self, mock_prompt, mock_confirm):
        """대화형 모드 통합 테스트"""
        mock_prompt.side_effect = [
            'interactive-project',  # 프로젝트 이름
            'interactive-ns',       # 네임스페이스
            'interactive-app',      # 앱 이름
            'install-helm'          # 앱 타입
        ]
        mock_confirm.side_effect = [True, True, False]  # 환경설정, Bitnami, Prometheus
        
        runner = CliRunner()
        
        with patch('sbkube.commands.init.InitCommand._validate_template'):
            with patch('sbkube.commands.init.InitCommand._create_directory_structure'):
                with patch('sbkube.commands.init.InitCommand._render_templates'):
                    with patch('sbkube.commands.init.InitCommand._create_readme'):
                        with runner.isolated_filesystem():
                            result = runner.invoke(main, ['init'])
                            
                            assert result.exit_code == 0
                            assert '프로젝트 정보를 입력해주세요' in result.output
    
    def test_init_current_directory_name_default(self):
        """현재 디렉토리명을 기본 프로젝트명으로 사용하는 테스트"""
        runner = CliRunner()
        
        with patch('sbkube.commands.init.InitCommand') as mock_init_command:
            with runner.isolated_filesystem():
                # 임시 디렉토리 이름이 기본값으로 사용되는지 확인
                result = runner.invoke(main, ['init', '--non-interactive'])
                
                args, kwargs = mock_init_command.call_args
                # base_dir는 현재 작업 디렉토리
                assert 'base_dir' in kwargs or len(args) > 0
    
    def test_init_option_combinations(self):
        """다양한 옵션 조합 테스트"""
        runner = CliRunner()
        
        option_combinations = [
            ['init'],
            ['init', '--non-interactive'],
            ['init', '--template', 'basic'],
            ['init', '--name', 'test-project'],
            ['init', '--template', 'basic', '--name', 'test', '--non-interactive'],
            ['init', '--force'],
            ['init', '--non-interactive', '--force']
        ]
        
        for combo in option_combinations:
            with patch('sbkube.commands.init.InitCommand.execute') as mock_execute:
                with runner.isolated_filesystem():
                    result = runner.invoke(main, combo)
                    # 일부 조합은 대화형 입력을 요구할 수 있지만 실행은 되어야 함
                    assert result.exit_code == 0 or '프로젝트 정보를 입력해주세요' in result.output
    
    def test_init_working_directory_isolation(self):
        """작업 디렉토리 격리 테스트"""
        runner = CliRunner()
        
        with patch('sbkube.commands.init.InitCommand.execute') as mock_execute:
            with runner.isolated_filesystem():
                # 격리된 디렉토리에서 실행
                result = runner.invoke(main, ['init', '--non-interactive'])
                
                assert result.exit_code == 0
                mock_execute.assert_called_once()
                
                # InitCommand에 전달된 base_dir 확인
                args, kwargs = mock_execute.call_args_list[0][1] if hasattr(mock_execute.call_args_list[0], 'kwargs') else ([], {})
                # base_dir가 격리된 디렉토리인지 확인 (정확한 검증은 InitCommand 생성자에서)