import pytest
from click.testing import CliRunner

from sbkube.cli import main


class TestProfilesCommand:
    def test_profiles_list_command(self):
        """profiles list 명령어 테스트"""
        runner = CliRunner()
        
        with runner.isolated_filesystem():
            # 프로젝트 초기화
            init_result = runner.invoke(main, [
                'init',
                '--name', 'profiles-test',
                '--non-interactive'
            ])
            assert init_result.exit_code == 0
            
            # profiles list 실행
            list_result = runner.invoke(main, ['profiles', 'list'])
            assert list_result.exit_code == 0
            assert '사용 가능한 프로파일' in list_result.output
            assert 'development' in list_result.output
            assert 'staging' in list_result.output
            assert 'production' in list_result.output
    
    def test_profiles_list_detailed_command(self):
        """profiles list --detailed 명령어 테스트"""
        runner = CliRunner()
        
        with runner.isolated_filesystem():
            # 프로젝트 초기화
            init_result = runner.invoke(main, [
                'init',
                '--name', 'detailed-test',
                '--non-interactive'
            ])
            assert init_result.exit_code == 0
            
            # profiles list --detailed 실행
            list_result = runner.invoke(main, ['profiles', 'list', '--detailed'])
            assert list_result.exit_code == 0
            assert '네임스페이스:' in list_result.output
            assert '앱 개수:' in list_result.output
            assert '상태:' in list_result.output
    
    def test_profiles_validate_command(self):
        """profiles validate 명령어 테스트"""
        runner = CliRunner()
        
        with runner.isolated_filesystem():
            # 프로젝트 초기화
            init_result = runner.invoke(main, [
                'init',
                '--name', 'validate-test',
                '--non-interactive'
            ])
            assert init_result.exit_code == 0
            
            # profiles validate development 실행
            validate_result = runner.invoke(main, ['profiles', 'validate', 'development'])
            assert validate_result.exit_code == 0
            assert '검증 결과' in validate_result.output
            assert '프로파일이 유효합니다' in validate_result.output
    
    def test_profiles_validate_all_command(self):
        """profiles validate --all 명령어 테스트"""
        runner = CliRunner()
        
        with runner.isolated_filesystem():
            # 프로젝트 초기화
            init_result = runner.invoke(main, [
                'init',
                '--name', 'validate-all-test',
                '--non-interactive'
            ])
            assert init_result.exit_code == 0
            
            # profiles validate --all 실행
            validate_result = runner.invoke(main, ['profiles', 'validate', '--all'])
            assert validate_result.exit_code == 0
            assert '프로파일 검증 중' in validate_result.output
            assert '검증 완료' in validate_result.output
    
    def test_profiles_show_command(self):
        """profiles show 명령어 테스트"""
        runner = CliRunner()
        
        with runner.isolated_filesystem():
            # 프로젝트 초기화
            init_result = runner.invoke(main, [
                'init',
                '--name', 'show-test',
                '--non-interactive'
            ])
            assert init_result.exit_code == 0
            
            # profiles show development 실행
            show_result = runner.invoke(main, ['profiles', 'show', 'development'])
            assert show_result.exit_code == 0
            assert '원본 설정' in show_result.output
            assert 'namespace:' in show_result.output
    
    def test_profiles_show_merged_command(self):
        """profiles show --merged 명령어 테스트"""
        runner = CliRunner()
        
        with runner.isolated_filesystem():
            # 프로젝트 초기화
            init_result = runner.invoke(main, [
                'init',
                '--name', 'show-merged-test',
                '--non-interactive'
            ])
            assert init_result.exit_code == 0
            
            # profiles show development --merged 실행
            show_result = runner.invoke(main, ['profiles', 'show', 'development', '--merged'])
            assert show_result.exit_code == 0
            assert '병합된 설정' in show_result.output
            assert 'namespace:' in show_result.output
    
    def test_profiles_validate_nonexistent_profile(self):
        """존재하지 않는 프로파일 검증 테스트"""
        runner = CliRunner()
        
        with runner.isolated_filesystem():
            # 프로젝트 초기화
            init_result = runner.invoke(main, [
                'init',
                '--name', 'nonexistent-test',
                '--non-interactive'
            ])
            assert init_result.exit_code == 0
            
            # 존재하지 않는 프로파일 검증
            validate_result = runner.invoke(main, ['profiles', 'validate', 'nonexistent'])
            assert validate_result.exit_code == 1
            assert '검증 실패' in validate_result.output
    
    def test_profiles_show_nonexistent_profile(self):
        """존재하지 않는 프로파일 조회 테스트"""
        runner = CliRunner()
        
        with runner.isolated_filesystem():
            # 프로젝트 초기화
            init_result = runner.invoke(main, [
                'init',
                '--name', 'nonexistent-show-test',
                '--non-interactive'
            ])
            assert init_result.exit_code == 0
            
            # 존재하지 않는 프로파일 조회
            show_result = runner.invoke(main, ['profiles', 'show', 'nonexistent'])
            assert show_result.exit_code == 1
            assert '조회 실패' in show_result.output
    
    def test_profiles_list_no_profiles(self):
        """프로파일이 없는 경우 테스트"""
        runner = CliRunner()
        
        with runner.isolated_filesystem():
            # 프로젝트 초기화 없이 profiles list 실행
            list_result = runner.invoke(main, ['profiles', 'list'])
            assert list_result.exit_code == 0
            assert '사용 가능한 프로파일이 없습니다' in list_result.output
            assert 'sbkube init' in list_result.output
    
    def test_profiles_help_command(self):
        """profiles 도움말 테스트"""
        runner = CliRunner()
        
        # profiles --help 실행
        help_result = runner.invoke(main, ['profiles', '--help'])
        assert help_result.exit_code == 0
        assert '프로파일 관리 명령어' in help_result.output
        assert 'list' in help_result.output
        assert 'validate' in help_result.output
        assert 'show' in help_result.output
    
    def test_profiles_subcommand_help(self):
        """profiles 서브명령어 도움말 테스트"""
        runner = CliRunner()
        
        # profiles list --help
        list_help_result = runner.invoke(main, ['profiles', 'list', '--help'])
        assert list_help_result.exit_code == 0
        assert '프로파일 목록 조회' in list_help_result.output
        
        # profiles validate --help
        validate_help_result = runner.invoke(main, ['profiles', 'validate', '--help'])
        assert validate_help_result.exit_code == 0
        assert '프로파일 설정 검증' in validate_help_result.output
        
        # profiles show --help
        show_help_result = runner.invoke(main, ['profiles', 'show', '--help'])
        assert show_help_result.exit_code == 0
        assert '프로파일 설정 내용 표시' in show_help_result.output