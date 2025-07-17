---
phase: 3
order: 11
source_plan: /tasks/plan/phase3-intelligent-features.md
priority: high
tags: [doctor-command, diagnostic-system, health-check]
estimated_days: 4
depends_on: [010-progress-manager-implementation]
---

# 📌 작업: sbkube doctor 진단 시스템 구현

## 🎯 목표
종합적인 시스템 진단을 수행하고 문제를 자동으로 탐지하는 `sbkube doctor` 명령어를 구현합니다.

## 📋 작업 내용

### 1. 진단 시스템 기본 구조 구현
```python
# sbkube/utils/diagnostic_system.py
from typing import Dict, Any, List, Optional, Callable
from dataclasses import dataclass, field
from enum import Enum
import asyncio
import time
from abc import ABC, abstractmethod

from rich.console import Console
from rich.table import Table
from rich.panel import Panel
from rich.progress import Progress, SpinnerColumn, TextColumn

from sbkube.utils.logger import logger

class DiagnosticLevel(Enum):
    SUCCESS = "success"
    WARNING = "warning"
    ERROR = "error"
    INFO = "info"

@dataclass
class DiagnosticResult:
    """진단 결과"""
    check_name: str
    level: DiagnosticLevel
    message: str
    details: str = ""
    fix_command: Optional[str] = None
    fix_description: Optional[str] = None
    metadata: Dict[str, Any] = field(default_factory=dict)
    
    @property
    def is_fixable(self) -> bool:
        """자동 수정 가능 여부"""
        return self.fix_command is not None
    
    @property
    def icon(self) -> str:
        """상태 아이콘"""
        icons = {
            DiagnosticLevel.SUCCESS: "🟢",
            DiagnosticLevel.WARNING: "🟡", 
            DiagnosticLevel.ERROR: "🔴",
            DiagnosticLevel.INFO: "🔵"
        }
        return icons[self.level]

class DiagnosticCheck(ABC):
    """진단 체크 기본 클래스"""
    
    def __init__(self, name: str, description: str):
        self.name = name
        self.description = description
    
    @abstractmethod
    async def run(self) -> DiagnosticResult:
        """진단 실행"""
        pass
    
    def create_result(self, level: DiagnosticLevel, message: str, 
                     details: str = "", fix_command: str = None,
                     fix_description: str = None) -> DiagnosticResult:
        """진단 결과 생성"""
        return DiagnosticResult(
            check_name=self.name,
            level=level,
            message=message,
            details=details,
            fix_command=fix_command,
            fix_description=fix_description
        )

class DiagnosticEngine:
    """진단 엔진"""
    
    def __init__(self, console: Console = None):
        self.console = console or Console()
        self.checks: List[DiagnosticCheck] = []
        self.results: List[DiagnosticResult] = []
    
    def register_check(self, check: DiagnosticCheck):
        """진단 체크 등록"""
        self.checks.append(check)
    
    async def run_all_checks(self, show_progress: bool = True) -> List[DiagnosticResult]:
        """모든 진단 체크 실행"""
        self.results.clear()
        
        if show_progress:
            with Progress(
                SpinnerColumn(),
                TextColumn("[bold blue]{task.description}"),
                console=self.console,
                transient=True
            ) as progress:
                task = progress.add_task("진단 실행 중...", total=len(self.checks))
                
                for check in self.checks:
                    progress.update(task, description=f"검사 중: {check.description}")
                    result = await check.run()
                    self.results.append(result)
                    progress.advance(task)
        else:
            for check in self.checks:
                result = await check.run()
                self.results.append(result)
        
        return self.results
    
    def get_summary(self) -> Dict[str, Any]:
        """진단 요약 정보"""
        summary = {
            'total': len(self.results),
            'success': 0,
            'warning': 0,
            'error': 0,
            'info': 0,
            'fixable': 0
        }
        
        for result in self.results:
            summary[result.level.value] += 1
            if result.is_fixable:
                summary['fixable'] += 1
        
        return summary
    
    def display_results(self, detailed: bool = False):
        """진단 결과 표시"""
        summary = self.get_summary()
        
        # 요약 정보 표시
        self._display_summary(summary)
        
        # 상세 결과 표시
        if detailed or summary['error'] > 0 or summary['warning'] > 0:
            self._display_detailed_results()
        
        # 자동 수정 제안
        if summary['fixable'] > 0:
            self._display_fix_suggestions()
    
    def _display_summary(self, summary: Dict[str, Any]):
        """요약 정보 표시"""
        self.console.print("\n🔍 SBKube 종합 진단 결과")
        self.console.print("━" * 50)
        
        table = Table(show_header=False, box=None)
        table.add_column("상태", style="bold")
        table.add_column("개수", justify="right")
        
        if summary['success'] > 0:
            table.add_row("🟢 정상", str(summary['success']))
        if summary['warning'] > 0:
            table.add_row("🟡 경고", str(summary['warning']))
        if summary['error'] > 0:
            table.add_row("🔴 오류", str(summary['error']))
        if summary['info'] > 0:
            table.add_row("🔵 정보", str(summary['info']))
        
        self.console.print(table)
        
        if summary['fixable'] > 0:
            self.console.print(f"\n💡 자동 수정 가능한 문제: {summary['fixable']}개")
    
    def _display_detailed_results(self):
        """상세 결과 표시"""
        for level in [DiagnosticLevel.ERROR, DiagnosticLevel.WARNING, DiagnosticLevel.INFO]:
            level_results = [r for r in self.results if r.level == level]
            if not level_results:
                continue
            
            level_names = {
                DiagnosticLevel.ERROR: "오류",
                DiagnosticLevel.WARNING: "경고", 
                DiagnosticLevel.INFO: "정보"
            }
            
            self.console.print(f"\n{level_results[0].icon} {level_names[level]} ({len(level_results)}개)")
            
            for result in level_results:
                self.console.print(f"├── {result.message}")
                if result.details:
                    self.console.print(f"│   {result.details}")
    
    def _display_fix_suggestions(self):
        """자동 수정 제안 표시"""
        fixable_results = [r for r in self.results if r.is_fixable]
        
        self.console.print(f"\n🔧 자동 수정 가능한 문제:")
        for i, result in enumerate(fixable_results, 1):
            self.console.print(f"  {i}. {result.message}")
            if result.fix_description:
                self.console.print(f"     → {result.fix_description}")
        
        self.console.print(f"\n💡 [bold]sbkube fix[/bold] 명령어로 자동 수정을 실행할 수 있습니다.")
```

### 2. 개별 진단 체크 구현
```python
# sbkube/diagnostics/kubernetes_checks.py
import subprocess
import asyncio
from pathlib import Path
import yaml
import requests

from sbkube.utils.diagnostic_system import DiagnosticCheck, DiagnosticLevel

class KubernetesConnectivityCheck(DiagnosticCheck):
    """Kubernetes 연결성 검사"""
    
    def __init__(self):
        super().__init__("k8s_connectivity", "Kubernetes 클러스터 연결")
    
    async def run(self) -> DiagnosticResult:
        try:
            # kubectl 설치 확인
            result = subprocess.run(
                ["kubectl", "version", "--client=true", "--short"],
                capture_output=True, text=True, timeout=10
            )
            
            if result.returncode != 0:
                return self.create_result(
                    DiagnosticLevel.ERROR,
                    "kubectl이 설치되지 않았습니다",
                    "Kubernetes CLI 도구가 필요합니다",
                    "curl -LO https://dl.k8s.io/release/v1.28.0/bin/linux/amd64/kubectl",
                    "kubectl 최신 버전 설치"
                )
            
            # 클러스터 연결 확인
            result = subprocess.run(
                ["kubectl", "cluster-info"],
                capture_output=True, text=True, timeout=10
            )
            
            if result.returncode != 0:
                return self.create_result(
                    DiagnosticLevel.ERROR,
                    "Kubernetes 클러스터에 연결할 수 없습니다",
                    result.stderr.strip(),
                    "kubectl config get-contexts",
                    "kubeconfig 설정 확인"
                )
            
            return self.create_result(
                DiagnosticLevel.SUCCESS,
                "Kubernetes 클러스터 연결 정상"
            )
            
        except subprocess.TimeoutExpired:
            return self.create_result(
                DiagnosticLevel.ERROR,
                "Kubernetes 연결 시간 초과",
                "클러스터 응답이 너무 느립니다"
            )
        except Exception as e:
            return self.create_result(
                DiagnosticLevel.ERROR,
                f"Kubernetes 연결 검사 실패: {str(e)}"
            )

class HelmInstallationCheck(DiagnosticCheck):
    """Helm 설치 상태 검사"""
    
    def __init__(self):
        super().__init__("helm_installation", "Helm 설치 상태")
    
    async def run(self) -> DiagnosticResult:
        try:
            # Helm 설치 확인
            result = subprocess.run(
                ["helm", "version", "--short"],
                capture_output=True, text=True, timeout=5
            )
            
            if result.returncode != 0:
                return self.create_result(
                    DiagnosticLevel.ERROR,
                    "Helm이 설치되지 않았습니다",
                    "Kubernetes 패키지 매니저가 필요합니다",
                    "curl https://raw.githubusercontent.com/helm/helm/main/scripts/get-helm-3 | bash",
                    "Helm 3 최신 버전 설치"
                )
            
            # 버전 확인
            version_output = result.stdout.strip()
            if "v2." in version_output:
                return self.create_result(
                    DiagnosticLevel.WARNING,
                    "Helm v2가 설치되어 있습니다",
                    "Helm v3 사용을 권장합니다",
                    "curl https://raw.githubusercontent.com/helm/helm/main/scripts/get-helm-3 | bash",
                    "Helm v3로 업그레이드"
                )
            
            return self.create_result(
                DiagnosticLevel.SUCCESS,
                f"Helm 설치 상태 정상: {version_output}"
            )
            
        except FileNotFoundError:
            return self.create_result(
                DiagnosticLevel.ERROR,
                "Helm이 설치되지 않았습니다",
                "PATH에서 helm 명령어를 찾을 수 없습니다",
                "curl https://raw.githubusercontent.com/helm/helm/main/scripts/get-helm-3 | bash",
                "Helm 3 설치"
            )
        except Exception as e:
            return self.create_result(
                DiagnosticLevel.ERROR,
                f"Helm 설치 확인 실패: {str(e)}"
            )

class ConfigValidityCheck(DiagnosticCheck):
    """설정 파일 유효성 검사"""
    
    def __init__(self, config_dir: str = "config"):
        super().__init__("config_validity", "설정 파일 유효성")
        self.config_dir = Path(config_dir)
    
    async def run(self) -> DiagnosticResult:
        try:
            # 기본 설정 파일 존재 확인
            config_file = self.config_dir / "config.yaml"
            if not config_file.exists():
                return self.create_result(
                    DiagnosticLevel.ERROR,
                    "기본 설정 파일이 없습니다",
                    f"{config_file} 파일이 존재하지 않습니다",
                    "sbkube init",
                    "프로젝트 초기화로 설정 파일 생성"
                )
            
            # YAML 파싱 확인
            try:
                with open(config_file, 'r', encoding='utf-8') as f:
                    config = yaml.safe_load(f)
                
                if not config:
                    return self.create_result(
                        DiagnosticLevel.WARNING,
                        "설정 파일이 비어있습니다",
                        "config.yaml에 유효한 설정이 없습니다"
                    )
                
                # 필수 필드 확인
                required_fields = ['namespace', 'apps']
                missing_fields = [field for field in required_fields if field not in config]
                
                if missing_fields:
                    return self.create_result(
                        DiagnosticLevel.WARNING,
                        f"필수 설정이 누락되었습니다: {', '.join(missing_fields)}",
                        "설정 파일을 확인하고 필수 필드를 추가해주세요"
                    )
                
                # 앱 설정 검증
                apps = config.get('apps', [])
                if not apps:
                    return self.create_result(
                        DiagnosticLevel.WARNING,
                        "배포할 앱이 정의되지 않았습니다",
                        "apps 섹션에 하나 이상의 앱을 정의해주세요"
                    )
                
                # 각 앱의 필수 필드 확인
                for i, app in enumerate(apps):
                    if 'name' not in app:
                        return self.create_result(
                            DiagnosticLevel.ERROR,
                            f"앱 #{i+1}에 name 필드가 없습니다",
                            "모든 앱에는 name 필드가 필요합니다"
                        )
                    
                    if 'type' not in app:
                        return self.create_result(
                            DiagnosticLevel.ERROR,
                            f"앱 '{app.get('name', f'#{i+1}')}에 type 필드가 없습니다",
                            "앱 타입(install-helm, install-yaml 등)을 지정해주세요"
                        )
                
                return self.create_result(
                    DiagnosticLevel.SUCCESS,
                    f"설정 파일 유효성 검사 통과 ({len(apps)}개 앱 정의됨)"
                )
                
            except yaml.YAMLError as e:
                return self.create_result(
                    DiagnosticLevel.ERROR,
                    "설정 파일 YAML 문법 오류",
                    f"YAML 파싱 실패: {str(e)}"
                )
                
        except Exception as e:
            return self.create_result(
                DiagnosticLevel.ERROR,
                f"설정 파일 검사 실패: {str(e)}"
            )

class NetworkAccessCheck(DiagnosticCheck):
    """네트워크 접근성 검사"""
    
    def __init__(self):
        super().__init__("network_access", "네트워크 접근성")
    
    async def run(self) -> DiagnosticResult:
        try:
            # 주요 서비스 연결 테스트
            test_urls = [
                ("Docker Hub", "https://registry-1.docker.io/v2/"),
                ("Bitnami Charts", "https://charts.bitnami.com/bitnami/index.yaml"),
                ("Kubernetes API", "https://kubernetes.io/")
            ]
            
            failed_connections = []
            
            for name, url in test_urls:
                try:
                    response = requests.get(url, timeout=5)
                    if response.status_code >= 400:
                        failed_connections.append(f"{name}: HTTP {response.status_code}")
                except requests.RequestException:
                    failed_connections.append(f"{name}: 연결 실패")
            
            if failed_connections:
                return self.create_result(
                    DiagnosticLevel.WARNING,
                    "일부 네트워크 연결에 문제가 있습니다",
                    "; ".join(failed_connections)
                )
            
            return self.create_result(
                DiagnosticLevel.SUCCESS,
                "네트워크 연결 상태 정상"
            )
            
        except Exception as e:
            return self.create_result(
                DiagnosticLevel.ERROR,
                f"네트워크 접근성 검사 실패: {str(e)}"
            )

class PermissionsCheck(DiagnosticCheck):
    """권한 검사"""
    
    def __init__(self):
        super().__init__("permissions", "Kubernetes 권한")
    
    async def run(self) -> DiagnosticResult:
        try:
            # 기본 권한 확인
            permissions_to_check = [
                ("get", "namespaces"),
                ("create", "namespaces"), 
                ("get", "pods"),
                ("create", "deployments"),
                ("create", "services")
            ]
            
            failed_permissions = []
            
            for action, resource in permissions_to_check:
                try:
                    result = subprocess.run([
                        "kubectl", "auth", "can-i", action, resource
                    ], capture_output=True, text=True, timeout=5)
                    
                    if result.returncode != 0 or "no" in result.stdout.lower():
                        failed_permissions.append(f"{action} {resource}")
                        
                except subprocess.TimeoutExpired:
                    failed_permissions.append(f"{action} {resource} (시간 초과)")
            
            if failed_permissions:
                return self.create_result(
                    DiagnosticLevel.ERROR,
                    "필요한 Kubernetes 권한이 부족합니다",
                    f"부족한 권한: {', '.join(failed_permissions)}",
                    "kubectl config view --minify",
                    "현재 사용자 권한 확인"
                )
            
            return self.create_result(
                DiagnosticLevel.SUCCESS,
                "Kubernetes 권한 확인 완료"
            )
            
        except Exception as e:
            return self.create_result(
                DiagnosticLevel.WARNING,
                f"권한 검사를 완료할 수 없습니다: {str(e)}",
                "수동으로 권한을 확인해주세요"
            )

class ResourceAvailabilityCheck(DiagnosticCheck):
    """리소스 가용성 검사"""
    
    def __init__(self):
        super().__init__("resource_availability", "클러스터 리소스")
    
    async def run(self) -> DiagnosticResult:
        try:
            # 노드 상태 확인
            result = subprocess.run([
                "kubectl", "get", "nodes", "--no-headers"
            ], capture_output=True, text=True, timeout=10)
            
            if result.returncode != 0:
                return self.create_result(
                    DiagnosticLevel.WARNING,
                    "노드 정보를 가져올 수 없습니다",
                    result.stderr.strip()
                )
            
            nodes = result.stdout.strip().split('\n') if result.stdout.strip() else []
            ready_nodes = [node for node in nodes if 'Ready' in node and 'NotReady' not in node]
            
            if not ready_nodes:
                return self.create_result(
                    DiagnosticLevel.ERROR,
                    "사용 가능한 노드가 없습니다",
                    "모든 노드가 NotReady 상태입니다"
                )
            
            # 디스크 공간 확인 (로컬)
            import shutil
            disk_usage = shutil.disk_usage('.')
            free_gb = disk_usage.free / (1024**3)
            
            if free_gb < 1:
                return self.create_result(
                    DiagnosticLevel.ERROR,
                    f"디스크 공간이 부족합니다 ({free_gb:.1f}GB 남음)",
                    "최소 1GB 이상의 여유 공간이 필요합니다"
                )
            elif free_gb < 5:
                return self.create_result(
                    DiagnosticLevel.WARNING,
                    f"디스크 공간이 부족합니다 ({free_gb:.1f}GB 남음)",
                    "5GB 이상의 여유 공간을 권장합니다"
                )
            
            return self.create_result(
                DiagnosticLevel.SUCCESS,
                f"리소스 상태 정상 ({len(ready_nodes)}개 노드, {free_gb:.1f}GB 여유 공간)"
            )
            
        except Exception as e:
            return self.create_result(
                DiagnosticLevel.WARNING,
                f"리소스 가용성 검사 실패: {str(e)}"
            )
```

### 3. Doctor 명령어 구현
```python
# sbkube/commands/doctor.py
import click
import sys
import asyncio
from typing import List

from rich.console import Console
from sbkube.utils.diagnostic_system import DiagnosticEngine
from sbkube.diagnostics.kubernetes_checks import (
    KubernetesConnectivityCheck,
    HelmInstallationCheck, 
    ConfigValidityCheck,
    NetworkAccessCheck,
    PermissionsCheck,
    ResourceAvailabilityCheck
)
from sbkube.utils.logger import logger

console = Console()

@click.command(name="doctor")
@click.option("--detailed", is_flag=True, help="상세한 진단 결과 표시")
@click.option("--fix", is_flag=True, help="자동 수정 가능한 문제들을 수정")
@click.option("--check", help="특정 검사만 실행 (예: k8s_connectivity)")
@click.pass_context
def cmd(ctx, detailed, fix, check):
    """SBKube 시스템 종합 진단
    
    Kubernetes 클러스터 연결, Helm 설치, 설정 파일 유효성 등을
    종합적으로 진단하고 문제점을 찾아 해결 방안을 제시합니다.
    
    \\b
    사용 예시:
        sbkube doctor                     # 기본 진단 실행
        sbkube doctor --detailed          # 상세 결과 표시
        sbkube doctor --fix               # 자동 수정 실행
        sbkube doctor --check k8s_connectivity  # 특정 검사만 실행
    """
    
    try:
        # 진단 엔진 초기화
        engine = DiagnosticEngine(console)
        
        # 진단 체크 등록
        checks = [
            KubernetesConnectivityCheck(),
            HelmInstallationCheck(),
            ConfigValidityCheck(),
            NetworkAccessCheck(), 
            PermissionsCheck(),
            ResourceAvailabilityCheck()
        ]
        
        # 특정 체크만 실행하는 경우
        if check:
            checks = [c for c in checks if c.name == check]
            if not checks:
                console.print(f"❌ 알 수 없는 검사: {check}")
                console.print("사용 가능한 검사:")
                for c in [KubernetesConnectivityCheck(), HelmInstallationCheck(), 
                         ConfigValidityCheck(), NetworkAccessCheck(), 
                         PermissionsCheck(), ResourceAvailabilityCheck()]:
                    console.print(f"  - {c.name}: {c.description}")
                sys.exit(1)
        
        for diagnostic_check in checks:
            engine.register_check(diagnostic_check)
        
        # 진단 실행
        results = asyncio.run(engine.run_all_checks())
        
        # 결과 표시
        engine.display_results(detailed=detailed)
        
        # 자동 수정 실행
        if fix:
            _run_auto_fixes(engine, results)
        
        # 종료 코드 결정
        summary = engine.get_summary()
        if summary['error'] > 0:
            sys.exit(1)
        elif summary['warning'] > 0:
            sys.exit(2)
        else:
            sys.exit(0)
            
    except Exception as e:
        logger.error(f"❌ 진단 실행 실패: {e}")
        sys.exit(1)

def _run_auto_fixes(engine: DiagnosticEngine, results: List) -> None:
    """자동 수정 실행"""
    fixable_results = [r for r in results if r.is_fixable]
    
    if not fixable_results:
        console.print("🤷 자동 수정 가능한 문제가 없습니다.")
        return
    
    console.print(f"\n🔧 {len(fixable_results)}개 문제의 자동 수정을 시작합니다...")
    
    for result in fixable_results:
        if not click.confirm(f"'{result.message}' 문제를 수정하시겠습니까?"):
            continue
        
        console.print(f"🔄 수정 중: {result.fix_description}")
        
        try:
            import subprocess
            fix_result = subprocess.run(
                result.fix_command.split(),
                capture_output=True,
                text=True,
                timeout=30
            )
            
            if fix_result.returncode == 0:
                console.print(f"✅ 수정 완료: {result.message}")
            else:
                console.print(f"❌ 수정 실패: {fix_result.stderr}")
                
        except Exception as e:
            console.print(f"❌ 수정 중 오류 발생: {e}")
            console.print(f"💡 수동 실행: {result.fix_command}")
```

## 🧪 테스트 구현

### 단위 테스트
```python
# tests/unit/commands/test_doctor.py
import pytest
import asyncio
from unittest.mock import patch, MagicMock

from sbkube.utils.diagnostic_system import DiagnosticEngine, DiagnosticLevel
from sbkube.diagnostics.kubernetes_checks import KubernetesConnectivityCheck

class TestDoctorCommand:
    def test_diagnostic_engine_basic(self):
        """진단 엔진 기본 동작 테스트"""
        engine = DiagnosticEngine()
        
        # Mock 체크 등록
        mock_check = MagicMock()
        mock_check.name = "test_check"
        mock_check.run = MagicMock(return_value=MagicMock(
            level=DiagnosticLevel.SUCCESS,
            message="테스트 성공"
        ))
        
        engine.register_check(mock_check)
        assert len(engine.checks) == 1
    
    @pytest.mark.asyncio
    async def test_kubernetes_connectivity_check(self):
        """Kubernetes 연결성 검사 테스트"""
        check = KubernetesConnectivityCheck()
        
        with patch('subprocess.run') as mock_run:
            # kubectl 성공 시나리오
            mock_run.side_effect = [
                MagicMock(returncode=0, stdout="Client Version: v1.28.0"),
                MagicMock(returncode=0, stdout="Kubernetes control plane is running")
            ]
            
            result = await check.run()
            assert result.level == DiagnosticLevel.SUCCESS
            assert "정상" in result.message
    
    def test_diagnostic_result_creation(self):
        """진단 결과 생성 테스트"""
        check = KubernetesConnectivityCheck()
        result = check.create_result(
            DiagnosticLevel.ERROR,
            "테스트 오류",
            "상세 내용",
            "kubectl version",
            "kubectl 설치"
        )
        
        assert result.level == DiagnosticLevel.ERROR
        assert result.message == "테스트 오류"
        assert result.is_fixable
        assert result.icon == "🔴"
```

## ✅ 완료 기준

- [ ] DiagnosticEngine 및 DiagnosticCheck 기본 구조 구현
- [ ] 6개 핵심 진단 체크 구현 (K8s, Helm, Config, Network, Permissions, Resources)
- [ ] sbkube doctor 명령어 구현
- [ ] 진단 결과 시각화 (Rich 기반)
- [ ] 자동 수정 시스템 기본 구조
- [ ] 단위 테스트 작성 및 통과

## 🔍 검증 명령어

```bash
# 기본 진단 실행
sbkube doctor

# 상세 진단 결과 
sbkube doctor --detailed

# 특정 검사만 실행
sbkube doctor --check k8s_connectivity

# 자동 수정 포함 실행
sbkube doctor --fix

# 테스트 실행
pytest tests/unit/commands/test_doctor.py -v
```

## 📝 예상 결과

```
🔍 SBKube 종합 진단 결과
━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━

🟢 정상     5
🟡 경고     2  
🔴 오류     1

💡 자동 수정 가능한 문제: 2개

🔴 오류 (1개)
├── 필수 네임스페이스 'production' 존재하지 않음
│   네임스페이스를 생성하거나 설정을 확인해주세요

🟡 경고 (2개)
├── config.yaml에 권장되지 않는 설정 발견
│   일부 설정이 보안 모범 사례를 따르지 않습니다
├── values 파일 중복 정의 존재
│   같은 키가 여러 values 파일에 정의되어 있습니다

🔧 자동 수정 가능한 문제:
  1. 필수 네임스페이스 'production' 존재하지 않음
     → kubectl을 사용하여 네임스페이스 생성
  2. values 파일 중복 정의 존재
     → 중복 정의 자동 정리

💡 sbkube fix 명령어로 자동 수정을 실행할 수 있습니다.
```

## 🔄 다음 단계

이 작업 완료 후 다음 작업으로 진행:
- `012-auto-fix-system.md` - 자동 수정 시스템 고도화