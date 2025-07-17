from click.testing import CliRunner
import pytest
from unittest.mock import patch

from sbkube.cli import main
from sbkube.commands.run import cmd


class TestRunCLIIntegration:
    def test_run_command_in_main_cli(self):
        """메인 CLI에서 run 명령어 확인"""
        runner = CliRunner()
        result = runner.invoke(main, ['--help'])
        
        assert result.exit_code == 0
        assert 'run' in result.output
        assert '전체 워크플로우를 통합 실행' in result.output
    
    def test_run_help_message(self):
        """run 명령어 도움말 메시지"""
        runner = CliRunner()
        result = runner.invoke(main, ['run', '--help'])
        
        assert result.exit_code == 0
        assert '전체 워크플로우를 통합 실행' in result.output
        assert '--from-step' in result.output
        assert '--to-step' in result.output
        assert '--only' in result.output
        assert '--dry-run' in result.output
        assert '기본 사용법:' in result.output
        assert '단계별 실행 제어:' in result.output
        assert '환경 설정:' in result.output
        assert '문제 해결:' in result.output
    
    @patch('sbkube.commands.run.RunCommand.execute')
    def test_dry_run_functionality(self, mock_execute):
        """dry-run 기능 테스트"""
        runner = CliRunner()
        
        with runner.isolated_filesystem():
            result = runner.invoke(main, ['run', '--dry-run'])
            
            assert result.exit_code == 0
            # dry-run 모드에서는 execute가 호출되지만 실제 단계는 실행되지 않음
            mock_execute.assert_called_once()
    
    @patch('sbkube.commands.run.RunCommand._show_execution_plan')
    def test_dry_run_shows_plan(self, mock_show_plan):
        """dry-run이 실행 계획을 표시하는지 테스트"""
        runner = CliRunner()
        
        with runner.isolated_filesystem():
            result = runner.invoke(cmd, ['--dry-run'])
            
            assert result.exit_code == 0
            # _show_execution_plan이 호출되었는지 확인
            mock_show_plan.assert_called_once()
    
    @patch('sbkube.commands.run.RunCommand.execute')
    def test_run_with_global_options(self, mock_execute):
        """전역 옵션과 함께 run 명령어 테스트"""
        runner = CliRunner()
        result = runner.invoke(main, ['-v', 'run', '--dry-run'])
        
        assert result.exit_code == 0
        mock_execute.assert_called_once()
    
    @patch('sbkube.commands.run.RunCommand.execute')
    def test_dry_run_with_step_options(self, mock_execute):
        """단계 옵션과 함께 dry-run 테스트"""
        runner = CliRunner()
        
        test_cases = [
            ['run', '--dry-run', '--from-step', 'build'],
            ['run', '--dry-run', '--to-step', 'template'],
            ['run', '--dry-run', '--only', 'prepare'],
        ]
        
        for args in test_cases:
            result = runner.invoke(main, args)
            assert result.exit_code == 0, f"Failed with args: {args}"
        
        # 각 테스트 케이스에 대해 execute가 호출되었는지 확인
        assert mock_execute.call_count == len(test_cases)
    
    def test_run_command_order_in_help(self):
        """메인 CLI 도움말에서 run 명령어 순서 확인"""
        runner = CliRunner()
        result = runner.invoke(main, ['--help'])
        
        assert result.exit_code == 0
        
        # run 명령어가 적절한 위치에 있는지 확인
        lines = result.output.split('\n')
        commands_section = False
        run_found = False
        
        for line in lines:
            if 'Commands:' in line:
                commands_section = True
                continue
            if commands_section and 'run' in line:
                run_found = True
                assert '전체 워크플로우를 통합 실행' in line
                break
        
        assert run_found, "run 명령어가 메인 CLI 도움말에 없습니다"
    
    @patch('sbkube.commands.run.RunCommand')
    def test_parameter_passing_with_dry_run(self, mock_run_command):
        """dry-run 매개변수 전달 테스트"""
        runner = CliRunner()
        mock_instance = mock_run_command.return_value
        
        with runner.isolated_filesystem():
            result = runner.invoke(main, [
                'run',
                '--app-dir', 'test-config',
                '--base-dir', '/test/path',
                '--app', 'my-app',
                '--config-file', 'my-config.yaml',
                '--from-step', 'build',
                '--dry-run'
            ])
            
            # RunCommand가 올바른 매개변수로 생성되었는지 확인
            mock_run_command.assert_called_once_with(
                base_dir='/test/path',
                app_config_dir='test-config',
                target_app_name='my-app',
                config_file_name='my-config.yaml',
                from_step='build',
                to_step=None,
                only_step=None,
                dry_run=True
            )
            
            mock_instance.execute.assert_called_once()
    
    def test_help_message_formatting(self):
        """도움말 메시지 형식 테스트"""
        runner = CliRunner()
        result = runner.invoke(cmd, ['--help'])
        
        assert result.exit_code == 0
        
        # 섹션별 헤딩이 올바르게 표시되는지 확인
        assert '기본 사용법:' in result.output
        assert '단계별 실행 제어:' in result.output
        assert '환경 설정:' in result.output
        assert '문제 해결:' in result.output
        
        # 예시 명령어들이 포함되어 있는지 확인
        assert 'sbkube run' in result.output
        assert '--from-step template' in result.output
        assert '--to-step build' in result.output
        assert '--only template' in result.output
        assert '--dry-run' in result.output
    
    @patch('sbkube.commands.run.RunCommand.execute')
    def test_all_option_combinations_valid(self, mock_execute):
        """모든 유효한 옵션 조합 테스트"""
        runner = CliRunner()
        
        # 유효한 옵션 조합들
        valid_combinations = [
            ['run'],
            ['run', '--dry-run'],
            ['run', '--from-step', 'build'],
            ['run', '--to-step', 'template'],
            ['run', '--only', 'deploy'],
            ['run', '--from-step', 'build', '--to-step', 'template'],
            ['run', '--from-step', 'prepare', '--dry-run'],
            ['run', '--to-step', 'deploy', '--dry-run'],
            ['run', '--only', 'build', '--dry-run'],
            ['run', '--app', 'test-app'],
            ['run', '--app-dir', 'custom'],
            ['run', '--config-file', 'custom.yaml'],
        ]
        
        for combo in valid_combinations:
            result = runner.invoke(main, combo)
            assert result.exit_code == 0, f"Failed combination: {combo}"
        
        # execute가 각 조합에 대해 호출되었는지 확인
        assert mock_execute.call_count == len(valid_combinations)