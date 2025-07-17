import pytest
import asyncio
from unittest.mock import patch, MagicMock, AsyncMock
from pathlib import Path
import tempfile
import os
import yaml
import subprocess
import requests

from sbkube.utils.diagnostic_system import (
    DiagnosticEngine, DiagnosticLevel, DiagnosticResult, DiagnosticCheck
)
from sbkube.diagnostics.kubernetes_checks import (
    KubernetesConnectivityCheck,
    HelmInstallationCheck,
    ConfigValidityCheck,
    NetworkAccessCheck,
    PermissionsCheck,
    ResourceAvailabilityCheck
)
from sbkube.commands.doctor import get_available_checks, get_check_info


class TestDiagnosticEngine:
    """진단 엔진 테스트"""
    
    def test_engine_creation(self):
        """진단 엔진 생성 테스트"""
        engine = DiagnosticEngine()
        assert engine.checks == []
        assert engine.results == []
        assert engine.console is not None
    
    def test_register_check(self):
        """진단 체크 등록 테스트"""
        engine = DiagnosticEngine()
        
        # Mock 체크 생성
        mock_check = MagicMock(spec=DiagnosticCheck)
        mock_check.name = "test_check"
        mock_check.description = "테스트 체크"
        
        engine.register_check(mock_check)
        assert len(engine.checks) == 1
        assert engine.checks[0] == mock_check
    
    @pytest.mark.asyncio
    async def test_run_all_checks(self):
        """모든 체크 실행 테스트"""
        engine = DiagnosticEngine()
        
        # Mock 체크들 생성
        mock_check1 = MagicMock(spec=DiagnosticCheck)
        mock_check1.name = "check1"
        mock_check1.description = "체크1"
        mock_result1 = DiagnosticResult(
            "check1", DiagnosticLevel.SUCCESS, "성공"
        )
        mock_check1.run = AsyncMock(return_value=mock_result1)
        
        mock_check2 = MagicMock(spec=DiagnosticCheck)
        mock_check2.name = "check2"
        mock_check2.description = "체크2"
        mock_result2 = DiagnosticResult(
            "check2", DiagnosticLevel.ERROR, "실패"
        )
        mock_check2.run = AsyncMock(return_value=mock_result2)
        
        engine.register_check(mock_check1)
        engine.register_check(mock_check2)
        
        # 체크 실행
        results = await engine.run_all_checks(show_progress=False)
        
        assert len(results) == 2
        assert results[0] == mock_result1
        assert results[1] == mock_result2
        assert engine.results == results
    
    def test_get_summary(self):
        """요약 정보 테스트"""
        engine = DiagnosticEngine()
        
        # Mock 결과들 추가
        engine.results = [
            DiagnosticResult("check1", DiagnosticLevel.SUCCESS, "성공"),
            DiagnosticResult("check2", DiagnosticLevel.ERROR, "실패", fix_command="fix"),
            DiagnosticResult("check3", DiagnosticLevel.WARNING, "경고"),
            DiagnosticResult("check4", DiagnosticLevel.INFO, "정보")
        ]
        
        summary = engine.get_summary()
        
        assert summary['total'] == 4
        assert summary['success'] == 1
        assert summary['error'] == 1
        assert summary['warning'] == 1
        assert summary['info'] == 1
        assert summary['fixable'] == 1
    
    def test_get_fixable_results(self):
        """수정 가능한 결과 반환 테스트"""
        engine = DiagnosticEngine()
        
        fixable = DiagnosticResult(
            "check1", DiagnosticLevel.ERROR, "실패", fix_command="fix"
        )
        non_fixable = DiagnosticResult(
            "check2", DiagnosticLevel.ERROR, "실패"
        )
        
        engine.results = [fixable, non_fixable]
        
        fixable_results = engine.get_fixable_results()
        assert len(fixable_results) == 1
        assert fixable_results[0] == fixable
    
    def test_has_errors_and_warnings(self):
        """오류/경고 확인 테스트"""
        engine = DiagnosticEngine()
        
        # 오류 없음
        engine.results = [
            DiagnosticResult("check1", DiagnosticLevel.SUCCESS, "성공")
        ]
        assert not engine.has_errors()
        assert not engine.has_warnings()
        
        # 경고 있음
        engine.results.append(
            DiagnosticResult("check2", DiagnosticLevel.WARNING, "경고")
        )
        assert not engine.has_errors()
        assert engine.has_warnings()
        
        # 오류 있음
        engine.results.append(
            DiagnosticResult("check3", DiagnosticLevel.ERROR, "오류")
        )
        assert engine.has_errors()
        assert engine.has_warnings()


class TestDiagnosticResult:
    """진단 결과 테스트"""
    
    def test_result_creation(self):
        """결과 생성 테스트"""
        result = DiagnosticResult(
            "test_check",
            DiagnosticLevel.SUCCESS,
            "성공 메시지",
            "상세 내용",
            "fix_command",
            "수정 설명"
        )
        
        assert result.check_name == "test_check"
        assert result.level == DiagnosticLevel.SUCCESS
        assert result.message == "성공 메시지"
        assert result.details == "상세 내용"
        assert result.fix_command == "fix_command"
        assert result.fix_description == "수정 설명"
        assert result.is_fixable
        assert result.icon == "🟢"
    
    def test_result_icons(self):
        """결과 아이콘 테스트"""
        levels_and_icons = [
            (DiagnosticLevel.SUCCESS, "🟢"),
            (DiagnosticLevel.WARNING, "🟡"),
            (DiagnosticLevel.ERROR, "🔴"),
            (DiagnosticLevel.INFO, "🔵")
        ]
        
        for level, expected_icon in levels_and_icons:
            result = DiagnosticResult("test", level, "메시지")
            assert result.icon == expected_icon
    
    def test_is_fixable(self):
        """수정 가능성 테스트"""
        fixable = DiagnosticResult("test", DiagnosticLevel.ERROR, "메시지", fix_command="fix")
        non_fixable = DiagnosticResult("test", DiagnosticLevel.ERROR, "메시지")
        
        assert fixable.is_fixable
        assert not non_fixable.is_fixable


class TestKubernetesConnectivityCheck:
    """Kubernetes 연결성 체크 테스트"""
    
    def test_check_creation(self):
        """체크 생성 테스트"""
        check = KubernetesConnectivityCheck()
        assert check.name == "k8s_connectivity"
        assert check.description == "Kubernetes 클러스터 연결"
    
    @pytest.mark.asyncio
    async def test_kubectl_not_installed(self):
        """kubectl 미설치 테스트"""
        check = KubernetesConnectivityCheck()
        
        with patch('subprocess.run') as mock_run:
            mock_run.side_effect = FileNotFoundError()
            
            result = await check.run()
            
            assert result.level == DiagnosticLevel.ERROR
            assert "kubectl 명령어를 찾을 수 없습니다" in result.message
            assert result.is_fixable
    
    @pytest.mark.asyncio
    async def test_kubectl_version_fails(self):
        """kubectl 버전 확인 실패 테스트"""
        check = KubernetesConnectivityCheck()
        
        with patch('subprocess.run') as mock_run:
            mock_run.return_value = MagicMock(returncode=1, stderr="not found")
            
            result = await check.run()
            
            assert result.level == DiagnosticLevel.ERROR
            assert "kubectl이 설치되지 않았습니다" in result.message
            assert result.is_fixable
    
    @pytest.mark.asyncio
    async def test_cluster_connection_fails(self):
        """클러스터 연결 실패 테스트"""
        check = KubernetesConnectivityCheck()
        
        with patch('subprocess.run') as mock_run:
            # kubectl version 성공, cluster-info 실패
            mock_run.side_effect = [
                MagicMock(returncode=0, stdout="Client Version: v1.28.0"),
                MagicMock(returncode=1, stderr="connection refused")
            ]
            
            result = await check.run()
            
            assert result.level == DiagnosticLevel.ERROR
            assert "클러스터에 연결할 수 없습니다" in result.message
            assert result.is_fixable
    
    @pytest.mark.asyncio
    async def test_successful_connection(self):
        """성공적인 연결 테스트"""
        check = KubernetesConnectivityCheck()
        
        with patch('subprocess.run') as mock_run:
            mock_run.side_effect = [
                MagicMock(returncode=0, stdout="Client Version: v1.28.0"),
                MagicMock(returncode=0, stdout="Kubernetes control plane is running"),
                MagicMock(returncode=0, stdout="Client Version: v1.28.0\nServer Version: v1.28.0")
            ]
            
            result = await check.run()
            
            assert result.level == DiagnosticLevel.SUCCESS
            assert "연결 정상" in result.message
            assert not result.is_fixable
    
    @pytest.mark.asyncio
    async def test_timeout_handling(self):
        """시간 초과 처리 테스트"""
        check = KubernetesConnectivityCheck()
        
        with patch('subprocess.run') as mock_run:
            mock_run.side_effect = subprocess.TimeoutExpired("kubectl", 10)
            
            result = await check.run()
            
            assert result.level == DiagnosticLevel.ERROR
            assert "연결 시간 초과" in result.message


class TestHelmInstallationCheck:
    """Helm 설치 체크 테스트"""
    
    def test_check_creation(self):
        """체크 생성 테스트"""
        check = HelmInstallationCheck()
        assert check.name == "helm_installation"
        assert check.description == "Helm 설치 상태"
    
    @pytest.mark.asyncio
    async def test_helm_not_installed(self):
        """Helm 미설치 테스트"""
        check = HelmInstallationCheck()
        
        with patch('subprocess.run') as mock_run:
            mock_run.side_effect = FileNotFoundError()
            
            result = await check.run()
            
            assert result.level == DiagnosticLevel.ERROR
            assert "Helm이 설치되지 않았습니다" in result.message
            assert result.is_fixable
    
    @pytest.mark.asyncio
    async def test_helm_v2_warning(self):
        """Helm v2 경고 테스트"""
        check = HelmInstallationCheck()
        
        with patch('subprocess.run') as mock_run:
            mock_run.return_value = MagicMock(returncode=0, stdout="v2.14.0")
            
            result = await check.run()
            
            assert result.level == DiagnosticLevel.WARNING
            assert "v2가 설치되어 있습니다" in result.message
            assert result.is_fixable
    
    @pytest.mark.asyncio
    async def test_helm_v3_success(self):
        """Helm v3 성공 테스트"""
        check = HelmInstallationCheck()
        
        with patch('subprocess.run') as mock_run:
            mock_run.return_value = MagicMock(returncode=0, stdout="v3.12.0")
            
            result = await check.run()
            
            assert result.level == DiagnosticLevel.SUCCESS
            assert "설치 상태 정상" in result.message
            assert not result.is_fixable


class TestConfigValidityCheck:
    """설정 파일 유효성 체크 테스트"""
    
    def test_check_creation(self):
        """체크 생성 테스트"""
        check = ConfigValidityCheck("test_config")
        assert check.name == "config_validity"
        assert check.description == "설정 파일 유효성"
        assert check.config_dir == Path("test_config")
    
    @pytest.mark.asyncio
    async def test_no_config_file(self):
        """설정 파일 없음 테스트"""
        with tempfile.TemporaryDirectory() as temp_dir:
            check = ConfigValidityCheck(temp_dir)
            
            result = await check.run()
            
            assert result.level == DiagnosticLevel.ERROR
            assert "설정 파일이 없습니다" in result.message
            assert result.is_fixable
    
    @pytest.mark.asyncio
    async def test_empty_config_file(self):
        """빈 설정 파일 테스트"""
        with tempfile.TemporaryDirectory() as temp_dir:
            config_file = Path(temp_dir) / "config.yaml"
            config_file.write_text("")
            
            check = ConfigValidityCheck(temp_dir)
            
            result = await check.run()
            
            assert result.level == DiagnosticLevel.WARNING
            assert "설정 파일이 비어있습니다" in result.message
    
    @pytest.mark.asyncio
    async def test_invalid_yaml(self):
        """잘못된 YAML 테스트"""
        with tempfile.TemporaryDirectory() as temp_dir:
            config_file = Path(temp_dir) / "config.yaml"
            config_file.write_text("invalid: yaml: content:")
            
            check = ConfigValidityCheck(temp_dir)
            
            result = await check.run()
            
            assert result.level == DiagnosticLevel.ERROR
            assert "YAML 문법 오류" in result.message
    
    @pytest.mark.asyncio
    async def test_missing_required_fields(self):
        """필수 필드 누락 테스트"""
        with tempfile.TemporaryDirectory() as temp_dir:
            config_file = Path(temp_dir) / "config.yaml"
            config_file.write_text(yaml.dump({"other": "value"}))
            
            check = ConfigValidityCheck(temp_dir)
            
            result = await check.run()
            
            assert result.level == DiagnosticLevel.WARNING
            assert "필수 설정이 누락되었습니다" in result.message
    
    @pytest.mark.asyncio
    async def test_valid_config(self):
        """유효한 설정 테스트"""
        with tempfile.TemporaryDirectory() as temp_dir:
            config_data = {
                "namespace": "test",
                "apps": [
                    {"name": "app1", "type": "install-helm"},
                    {"name": "app2", "type": "install-yaml"}
                ]
            }
            config_file = Path(temp_dir) / "config.yaml"
            config_file.write_text(yaml.dump(config_data))
            
            check = ConfigValidityCheck(temp_dir)
            
            result = await check.run()
            
            assert result.level == DiagnosticLevel.SUCCESS
            assert "유효성 검사 통과" in result.message
            assert "2개 앱 정의됨" in result.message
    
    @pytest.mark.asyncio
    async def test_app_missing_name(self):
        """앱 이름 누락 테스트"""
        with tempfile.TemporaryDirectory() as temp_dir:
            config_data = {
                "namespace": "test",
                "apps": [
                    {"type": "install-helm"}  # name 누락
                ]
            }
            config_file = Path(temp_dir) / "config.yaml"
            config_file.write_text(yaml.dump(config_data))
            
            check = ConfigValidityCheck(temp_dir)
            
            result = await check.run()
            
            assert result.level == DiagnosticLevel.ERROR
            assert "name 필드가 없습니다" in result.message


class TestNetworkAccessCheck:
    """네트워크 접근성 체크 테스트"""
    
    def test_check_creation(self):
        """체크 생성 테스트"""
        check = NetworkAccessCheck()
        assert check.name == "network_access"
        assert check.description == "네트워크 접근성"
    
    @pytest.mark.asyncio
    async def test_all_connections_successful(self):
        """모든 연결 성공 테스트"""
        check = NetworkAccessCheck()
        
        with patch('requests.get') as mock_get:
            mock_get.return_value = MagicMock(status_code=200)
            
            result = await check.run()
            
            assert result.level == DiagnosticLevel.SUCCESS
            assert "네트워크 연결 상태 정상" in result.message
    
    @pytest.mark.asyncio
    async def test_some_connections_fail(self):
        """일부 연결 실패 테스트"""
        check = NetworkAccessCheck()
        
        with patch('requests.get') as mock_get:
            def side_effect(url, **kwargs):
                if "docker.io" in url:
                    raise requests.RequestException("Connection failed")
                return MagicMock(status_code=200)
            
            mock_get.side_effect = side_effect
            
            result = await check.run()
            
            assert result.level == DiagnosticLevel.WARNING
            assert "일부 네트워크 연결에 문제가 있습니다" in result.message
            assert "Docker Hub" in result.details


class TestPermissionsCheck:
    """권한 체크 테스트"""
    
    def test_check_creation(self):
        """체크 생성 테스트"""
        check = PermissionsCheck()
        assert check.name == "permissions"
        assert check.description == "Kubernetes 권한"
    
    @pytest.mark.asyncio
    async def test_all_permissions_ok(self):
        """모든 권한 정상 테스트"""
        check = PermissionsCheck()
        
        with patch('subprocess.run') as mock_run:
            mock_run.return_value = MagicMock(returncode=0, stdout="yes")
            
            result = await check.run()
            
            assert result.level == DiagnosticLevel.SUCCESS
            assert "권한 확인 완료" in result.message
    
    @pytest.mark.asyncio
    async def test_some_permissions_missing(self):
        """일부 권한 누락 테스트"""
        check = PermissionsCheck()
        
        with patch('subprocess.run') as mock_run:
            def side_effect(cmd, **kwargs):
                if "create" in cmd and "namespaces" in cmd:
                    return MagicMock(returncode=1, stdout="no")
                return MagicMock(returncode=0, stdout="yes")
            
            mock_run.side_effect = side_effect
            
            result = await check.run()
            
            assert result.level == DiagnosticLevel.ERROR
            assert "권한이 부족합니다" in result.message
            assert "create namespaces" in result.details


class TestResourceAvailabilityCheck:
    """리소스 가용성 체크 테스트"""
    
    def test_check_creation(self):
        """체크 생성 테스트"""
        check = ResourceAvailabilityCheck()
        assert check.name == "resource_availability"
        assert check.description == "클러스터 리소스"
    
    @pytest.mark.asyncio
    async def test_no_ready_nodes(self):
        """Ready 노드 없음 테스트"""
        check = ResourceAvailabilityCheck()
        
        with patch('subprocess.run') as mock_run:
            mock_run.return_value = MagicMock(
                returncode=0, 
                stdout="node1   NotReady\nnode2   NotReady"
            )
            
            with patch('shutil.disk_usage') as mock_disk:
                mock_disk.return_value = MagicMock(free=10 * 1024**3)  # 10GB
                
                result = await check.run()
                
                assert result.level == DiagnosticLevel.ERROR
                assert "사용 가능한 노드가 없습니다" in result.message
    
    @pytest.mark.asyncio
    async def test_low_disk_space(self):
        """디스크 공간 부족 테스트"""
        check = ResourceAvailabilityCheck()
        
        with patch('subprocess.run') as mock_run:
            mock_run.return_value = MagicMock(
                returncode=0, 
                stdout="node1   Ready"
            )
            
            with patch('shutil.disk_usage') as mock_disk:
                mock_disk.return_value = MagicMock(free=0.5 * 1024**3)  # 0.5GB
                
                result = await check.run()
                
                assert result.level == DiagnosticLevel.ERROR
                assert "디스크 공간이 부족합니다" in result.message
    
    @pytest.mark.asyncio
    async def test_resources_ok(self):
        """리소스 정상 테스트"""
        check = ResourceAvailabilityCheck()
        
        with patch('subprocess.run') as mock_run:
            mock_run.return_value = MagicMock(
                returncode=0, 
                stdout="node1   Ready\nnode2   Ready"
            )
            
            with patch('shutil.disk_usage') as mock_disk:
                mock_disk.return_value = MagicMock(free=10 * 1024**3)  # 10GB
                
                result = await check.run()
                
                assert result.level == DiagnosticLevel.SUCCESS
                assert "리소스 상태 정상" in result.message
                assert "2개 노드" in result.message


class TestDoctorCommandHelpers:
    """Doctor 명령어 헬퍼 함수 테스트"""
    
    def test_get_available_checks(self):
        """사용 가능한 체크 목록 테스트"""
        checks = get_available_checks()
        
        assert len(checks) == 6
        check_names = [check.name for check in checks]
        
        expected_names = [
            "k8s_connectivity",
            "helm_installation", 
            "config_validity",
            "network_access",
            "permissions",
            "resource_availability"
        ]
        
        for name in expected_names:
            assert name in check_names
    
    def test_get_check_info(self):
        """체크 정보 반환 테스트"""
        info = get_check_info("k8s_connectivity")
        
        assert info is not None
        assert info['name'] == "k8s_connectivity"
        assert info['description'] == "Kubernetes 클러스터 연결"
        assert info['class'] == "KubernetesConnectivityCheck"
        
        # 존재하지 않는 체크
        assert get_check_info("non_existent") is None