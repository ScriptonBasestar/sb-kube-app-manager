import pytest
import subprocess
from unittest.mock import Mock, patch, MagicMock

from sbkube.fixes.namespace_fixes import (
    MissingNamespaceFix, ConfigFileFix, HelmRepositoryFix
)
from sbkube.utils.diagnostic_system import DiagnosticResult, DiagnosticLevel


@pytest.fixture
def sample_namespace_result():
    """네임스페이스 관련 진단 결과"""
    return DiagnosticResult(
        check_name="namespace_check",
        level=DiagnosticLevel.ERROR,
        message="네임스페이스 'test-namespace'가 존재하지 않습니다",
        is_fixable=True,
        fix_command="kubectl create namespace test-namespace"
    )


@pytest.fixture
def sample_config_result():
    """설정 파일 관련 진단 결과"""
    return DiagnosticResult(
        check_name="config_check",
        level=DiagnosticLevel.ERROR,
        message="필수 설정이 누락되었습니다: namespace",
        is_fixable=True,
        fix_command="config 파일 수정 필요"
    )


@pytest.fixture
def sample_helm_result():
    """Helm 관련 진단 결과"""
    return DiagnosticResult(
        check_name="helm_check",
        level=DiagnosticLevel.ERROR,
        message="helm 리포지토리가 설정되지 않았습니다",
        is_fixable=True,
        fix_command="helm repo add bitnami https://charts.bitnami.com/bitnami"
    )


class TestMissingNamespaceFix:
    """MissingNamespaceFix 테스트"""
    
    def test_init(self):
        """초기화 테스트"""
        fix = MissingNamespaceFix()
        
        assert fix.fix_id == "create_missing_namespace"
        assert fix.description == "누락된 네임스페이스 생성"
        assert fix.risk_level == "low"
    
    def test_can_fix_positive(self, sample_namespace_result):
        """수정 가능한 경우 테스트"""
        fix = MissingNamespaceFix()
        
        assert fix.can_fix(sample_namespace_result) is True
    
    def test_can_fix_negative(self):
        """수정 불가능한 경우 테스트"""
        fix = MissingNamespaceFix()
        
        unrelated_result = DiagnosticResult(
            check_name="other_check",
            level=DiagnosticLevel.ERROR,
            message="다른 종류의 오류",
            is_fixable=True
        )
        
        assert fix.can_fix(unrelated_result) is False
    
    def test_create_backup(self):
        """백업 생성 테스트 (네임스페이스는 백업 불필요)"""
        fix = MissingNamespaceFix()
        
        backup_path = fix.create_backup()
        
        assert backup_path is None
    
    @patch('subprocess.run')
    def test_apply_fix_success(self, mock_run, sample_namespace_result):
        """성공적인 네임스페이스 생성 테스트"""
        fix = MissingNamespaceFix()
        
        # kubectl 명령 성공 시뮬레이션
        mock_run.return_value = Mock(returncode=0, stderr="")
        
        result = fix.apply_fix(sample_namespace_result)
        
        assert result is True
        mock_run.assert_called_once_with(
            ["kubectl", "create", "namespace", "test-namespace"],
            capture_output=True,
            text=True,
            timeout=30
        )
    
    @patch('subprocess.run')
    def test_apply_fix_failure(self, mock_run, sample_namespace_result):
        """네임스페이스 생성 실패 테스트"""
        fix = MissingNamespaceFix()
        
        # kubectl 명령 실패 시뮬레이션
        mock_run.return_value = Mock(returncode=1, stderr="Error creating namespace")
        
        result = fix.apply_fix(sample_namespace_result)
        
        assert result is False
    
    @patch('subprocess.run')
    def test_apply_fix_timeout(self, mock_run, sample_namespace_result):
        """타임아웃 테스트"""
        fix = MissingNamespaceFix()
        
        # 타임아웃 발생 시뮬레이션
        mock_run.side_effect = subprocess.TimeoutExpired("kubectl", 30)
        
        result = fix.apply_fix(sample_namespace_result)
        
        assert result is False
    
    def test_rollback(self):
        """롤백 테스트 (기본적으로 수행하지 않음)"""
        fix = MissingNamespaceFix()
        
        result = fix.rollback("/fake/backup")
        
        assert result is True
    
    @patch('subprocess.run')
    def test_validate_fix_success(self, mock_run, sample_namespace_result):
        """검증 성공 테스트"""
        fix = MissingNamespaceFix()
        
        # kubectl get namespace 성공 시뮬레이션
        mock_run.return_value = Mock(returncode=0)
        
        result = fix.validate_fix(sample_namespace_result)
        
        assert result is True
        mock_run.assert_called_once_with(
            ["kubectl", "get", "namespace", "test-namespace"],
            capture_output=True,
            text=True,
            timeout=10
        )
    
    @patch('subprocess.run')
    def test_validate_fix_failure(self, mock_run, sample_namespace_result):
        """검증 실패 테스트"""
        fix = MissingNamespaceFix()
        
        # kubectl get namespace 실패 시뮬레이션
        mock_run.return_value = Mock(returncode=1)
        
        result = fix.validate_fix(sample_namespace_result)
        
        assert result is False
    
    def test_extract_namespace_name(self):
        """네임스페이스 이름 추출 테스트"""
        fix = MissingNamespaceFix()
        
        # 따옴표 테스트
        assert fix._extract_namespace_name("네임스페이스 'test-ns'가 존재하지 않습니다") == "test-ns"
        
        # 쌍따옴표 테스트
        assert fix._extract_namespace_name('네임스페이스 "prod-ns"가 존재하지 않습니다') == "prod-ns"
        
        # 단어 매칭 테스트
        assert fix._extract_namespace_name("네임스페이스 dev-env 존재하지 않음") == "dev-env"
        
        # 매칭되지 않는 경우
        assert fix._extract_namespace_name("다른 종류의 오류") is None


class TestConfigFileFix:
    """ConfigFileFix 테스트"""
    
    def test_init(self):
        """초기화 테스트"""
        fix = ConfigFileFix()
        
        assert fix.fix_id == "fix_config_file"
        assert fix.description == "설정 파일 오류 수정"
        assert fix.risk_level == "medium"
    
    def test_can_fix_positive(self, sample_config_result):
        """수정 가능한 경우 테스트"""
        fix = ConfigFileFix()
        
        assert fix.can_fix(sample_config_result) is True
    
    def test_can_fix_yaml_error(self):
        """YAML 오류 수정 가능 테스트"""
        fix = ConfigFileFix()
        
        yaml_error_result = DiagnosticResult(
            check_name="config_check",
            level=DiagnosticLevel.ERROR,
            message="YAML 문법 오류가 발견되었습니다",
            is_fixable=True
        )
        
        assert fix.can_fix(yaml_error_result) is True
    
    @patch('pathlib.Path.exists')
    @patch('shutil.copy2')
    def test_create_backup_success(self, mock_copy, mock_exists):
        """백업 생성 성공 테스트"""
        fix = ConfigFileFix()
        
        mock_exists.return_value = True
        
        with patch('pathlib.Path.mkdir'):
            backup_path = fix.create_backup()
        
        assert backup_path is not None
        assert "config_backup_" in backup_path
        assert backup_path.endswith(".yaml")
        mock_copy.assert_called_once()
    
    @patch('pathlib.Path.exists')
    def test_create_backup_no_file(self, mock_exists):
        """설정 파일이 없는 경우 백업 테스트"""
        fix = ConfigFileFix()
        
        mock_exists.return_value = False
        
        backup_path = fix.create_backup()
        
        assert backup_path is None
    
    @patch('sbkube.fixes.namespace_fixes.ConfigFileFix._add_missing_fields')
    def test_apply_fix_missing_fields(self, mock_add_fields, sample_config_result):
        """필수 설정 누락 수정 테스트"""
        fix = ConfigFileFix()
        mock_add_fields.return_value = True
        
        result = fix.apply_fix(sample_config_result)
        
        assert result is True
        mock_add_fields.assert_called_once_with(sample_config_result)
    
    @patch('shutil.copy2')
    def test_rollback_success(self, mock_copy):
        """롤백 성공 테스트"""
        fix = ConfigFileFix()
        
        result = fix.rollback("/test/backup.yaml")
        
        assert result is True
        mock_copy.assert_called_once()
    
    @patch('builtins.open', create=True)
    @patch('yaml.safe_load')
    @patch('pathlib.Path.exists')
    def test_validate_fix_success(self, mock_exists, mock_yaml_load, mock_open):
        """검증 성공 테스트"""
        fix = ConfigFileFix()
        
        mock_exists.return_value = True
        mock_yaml_load.return_value = {'namespace': 'default', 'apps': []}
        
        result = fix.validate_fix(sample_config_result)
        
        assert result is True
    
    @patch('builtins.open', create=True)
    @patch('yaml.dump')
    @patch('yaml.safe_load')
    @patch('pathlib.Path.exists')
    def test_add_missing_fields(self, mock_exists, mock_yaml_load, mock_yaml_dump, mock_open):
        """누락된 필드 추가 테스트"""
        fix = ConfigFileFix()
        
        mock_exists.return_value = True
        mock_yaml_load.return_value = {}  # 빈 설정
        
        with patch('pathlib.Path.mkdir'):
            result = fix._add_missing_fields(sample_config_result)
        
        assert result is True
        mock_yaml_dump.assert_called_once()
        
        # dump 호출 시 전달된 config 확인
        call_args = mock_yaml_dump.call_args[0]
        config = call_args[0]
        assert 'namespace' in config
        assert 'apps' in config
    
    @patch('builtins.open', create=True)
    @patch('yaml.dump')
    def test_create_default_config(self, mock_yaml_dump, mock_open):
        """기본 설정 파일 생성 테스트"""
        fix = ConfigFileFix()
        
        with patch('pathlib.Path.mkdir'):
            result = fix._create_default_config()
        
        assert result is True
        mock_yaml_dump.assert_called_once()


class TestHelmRepositoryFix:
    """HelmRepositoryFix 테스트"""
    
    def test_init(self):
        """초기화 테스트"""
        fix = HelmRepositoryFix()
        
        assert fix.fix_id == "add_helm_repository"
        assert fix.description == "필요한 Helm 리포지토리 추가"
        assert fix.risk_level == "low"
    
    def test_can_fix_positive(self, sample_helm_result):
        """수정 가능한 경우 테스트"""
        fix = HelmRepositoryFix()
        
        assert fix.can_fix(sample_helm_result) is True
    
    def test_can_fix_negative(self):
        """수정 불가능한 경우 테스트"""
        fix = HelmRepositoryFix()
        
        unrelated_result = DiagnosticResult(
            check_name="other_check",
            level=DiagnosticLevel.ERROR,
            message="다른 종류의 오류",
            is_fixable=True
        )
        
        assert fix.can_fix(unrelated_result) is False
    
    @patch('subprocess.run')
    @patch('builtins.open', create=True)
    def test_create_backup_success(self, mock_open, mock_run):
        """백업 생성 성공 테스트"""
        fix = HelmRepositoryFix()
        
        # helm repo list 성공 시뮬레이션
        mock_run.return_value = Mock(returncode=0, stdout='[{"name": "stable", "url": "https://charts.helm.sh/stable"}]')
        
        with patch('pathlib.Path.mkdir'):
            backup_path = fix.create_backup()
        
        assert backup_path is not None
        assert "helm_repos_backup_" in backup_path
        assert backup_path.endswith(".json")
        mock_run.assert_called_once_with(
            ["helm", "repo", "list", "-o", "json"],
            capture_output=True,
            text=True,
            timeout=10
        )
    
    @patch('subprocess.run')
    def test_apply_fix_success(self, mock_run, sample_helm_result):
        """Helm 리포지토리 추가 성공 테스트"""
        fix = HelmRepositoryFix()
        
        # helm repo add 명령들 성공 시뮬레이션
        mock_run.side_effect = [
            Mock(returncode=0, stderr=""),  # bitnami 추가
            Mock(returncode=0, stderr=""),  # stable 추가
            Mock(returncode=0, stderr="")   # repo update
        ]
        
        result = fix.apply_fix(sample_helm_result)
        
        assert result is True
        assert mock_run.call_count == 3
    
    @patch('subprocess.run')
    def test_apply_fix_partial_success(self, mock_run, sample_helm_result):
        """일부 리포지토리만 성공하는 경우 테스트"""
        fix = HelmRepositoryFix()
        
        # bitnami 성공, stable 실패
        mock_run.side_effect = [
            Mock(returncode=0, stderr=""),  # bitnami 성공
            Mock(returncode=1, stderr="Failed to add stable"),  # stable 실패
            Mock(returncode=0, stderr="")   # repo update
        ]
        
        result = fix.apply_fix(sample_helm_result)
        
        assert result is True  # 하나라도 성공하면 True
    
    @patch('subprocess.run')
    def test_validate_fix_success(self, mock_run, sample_helm_result):
        """검증 성공 테스트"""
        fix = HelmRepositoryFix()
        
        # helm repo list에 bitnami가 포함된 출력
        mock_run.return_value = Mock(
            returncode=0,
            stdout="NAME\tURL\nbitnami\thttps://charts.bitnami.com/bitnami\n"
        )
        
        result = fix.validate_fix(sample_helm_result)
        
        assert result is True
        mock_run.assert_called_once_with(
            ["helm", "repo", "list"],
            capture_output=True,
            text=True,
            timeout=10
        )
    
    @patch('subprocess.run')
    def test_validate_fix_failure(self, mock_run, sample_helm_result):
        """검증 실패 테스트"""
        fix = HelmRepositoryFix()
        
        # helm repo list에 필요한 리포지토리가 없음
        mock_run.return_value = Mock(
            returncode=0,
            stdout="NAME\tURL\n"
        )
        
        result = fix.validate_fix(sample_helm_result)
        
        assert result is False
    
    @patch('subprocess.run')
    @patch('builtins.open', create=True)
    @patch('json.load')
    @patch('json.loads')
    def test_rollback_success(self, mock_json_loads, mock_json_load, mock_open, mock_run):
        """롤백 성공 테스트"""
        fix = HelmRepositoryFix()
        
        # 현재 리포지토리 목록
        mock_run.side_effect = [
            Mock(returncode=0, stdout='[{"name": "new-repo", "url": "https://new.repo"}]'),
            Mock(returncode=0),  # remove new-repo
            Mock(returncode=0),  # add original repo
        ]
        
        # 백업된 리포지토리
        mock_json_load.return_value = [{"name": "original-repo", "url": "https://original.repo"}]
        mock_json_loads.return_value = [{"name": "new-repo", "url": "https://new.repo"}]
        
        result = fix.rollback("/test/backup.json")
        
        assert result is True


@pytest.mark.integration
class TestFixesIntegration:
    """수정 클래스들 통합 테스트"""
    
    def test_all_fixes_basic_interface(self):
        """모든 수정 클래스의 기본 인터페이스 테스트"""
        fixes = [
            MissingNamespaceFix(),
            ConfigFileFix(),
            HelmRepositoryFix()
        ]
        
        for fix in fixes:
            assert hasattr(fix, 'fix_id')
            assert hasattr(fix, 'description') 
            assert hasattr(fix, 'risk_level')
            assert fix.risk_level in ['low', 'medium', 'high']
            
            # 모든 추상 메서드가 구현되어 있는지 확인
            assert callable(fix.can_fix)
            assert callable(fix.create_backup)
            assert callable(fix.apply_fix)
            assert callable(fix.rollback)
            assert callable(fix.validate_fix)
    
    def test_risk_level_distribution(self):
        """위험도 수준 분포 테스트"""
        fixes = [
            MissingNamespaceFix(),
            ConfigFileFix(),
            HelmRepositoryFix()
        ]
        
        risk_levels = [fix.risk_level for fix in fixes]
        
        # 최소한 하나의 low 위험도 수정이 있어야 함
        assert 'low' in risk_levels
        
        # 각 수정의 위험도가 적절한지 확인
        assert MissingNamespaceFix().risk_level == 'low'
        assert ConfigFileFix().risk_level == 'medium'
        assert HelmRepositoryFix().risk_level == 'low'