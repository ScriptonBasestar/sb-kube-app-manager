from click.testing import CliRunner
import pytest
from unittest.mock import patch

from sbkube.commands.run import cmd


class TestRunWorkflow:
    def test_run_command_help(self):
        """run 명령어 도움말 테스트"""
        runner = CliRunner()
        result = runner.invoke(cmd, ['--help'])
        
        assert result.exit_code == 0
        assert "전체 워크플로우를 통합 실행합니다" in result.output
        assert "prepare → build → template → deploy" in result.output
        assert "--app-dir" in result.output
        assert "--base-dir" in result.output
        assert "--app" in result.output
        assert "--config-file" in result.output
    
    @patch('sbkube.commands.run.RunCommand.execute')
    def test_run_command_basic_execution(self, mock_execute):
        """기본 run 명령어 실행 테스트"""
        runner = CliRunner()
        
        with runner.isolated_filesystem():
            result = runner.invoke(cmd, [
                '--app-dir', 'config',
                '--base-dir', '.',
            ])
            
            # 명령어가 성공적으로 실행되었는지 확인
            assert result.exit_code == 0
            mock_execute.assert_called_once()
    
    @patch('sbkube.commands.run.RunCommand.execute')
    def test_run_command_with_all_options(self, mock_execute):
        """모든 옵션을 포함한 run 명령어 실행 테스트"""
        runner = CliRunner()
        
        with runner.isolated_filesystem():
            result = runner.invoke(cmd, [
                '--app-dir', 'config',
                '--base-dir', '.',
                '--app', 'test-app',
                '--config-file', 'test-config.yaml',
                '--verbose',
                '--debug'
            ])
            
            assert result.exit_code == 0
            mock_execute.assert_called_once()
    
    @patch('sbkube.commands.run.RunCommand.execute')
    def test_run_command_execution_failure(self, mock_execute):
        """run 명령어 실행 실패 테스트"""
        runner = CliRunner()
        mock_execute.side_effect = Exception("Test execution error")
        
        with runner.isolated_filesystem():
            result = runner.invoke(cmd, [
                '--app-dir', 'config',
                '--base-dir', '.',
            ])
            
            # 예외로 인해 exit code가 1이어야 함
            assert result.exit_code == 1
            mock_execute.assert_called_once()
    
    def test_run_command_parameter_passing(self):
        """run 명령어 매개변수 전달 테스트"""
        runner = CliRunner()
        
        with patch('sbkube.commands.run.RunCommand') as mock_run_command:
            mock_instance = mock_run_command.return_value
            
            result = runner.invoke(cmd, [
                '--app-dir', 'test-config',
                '--base-dir', '/test/path',
                '--app', 'my-app',
                '--config-file', 'my-config.yaml'
            ])
            
            # RunCommand가 올바른 매개변수로 생성되었는지 확인
            mock_run_command.assert_called_once_with(
                base_dir='/test/path',
                app_config_dir='test-config',
                target_app_name='my-app',
                config_file_name='my-config.yaml'
            )
            
            # execute가 호출되었는지 확인
            mock_instance.execute.assert_called_once()