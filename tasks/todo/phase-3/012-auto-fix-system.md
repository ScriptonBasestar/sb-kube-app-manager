---
phase: 3
order: 12
source_plan: /tasks/plan/phase3-intelligent-features.md
priority: high
tags: [auto-fix, backup-restore, safety-checks]
estimated_days: 3
depends_on: [011-doctor-diagnostic-system]
---

# 📌 작업: 자동 수정 시스템 고도화

## 🎯 목표
안전한 자동 수정 시스템을 구현하여 진단된 문제들을 자동으로 해결하고, 수정 전 백업 및 롤백 기능을 제공합니다.

## 📋 작업 내용

### 1. 자동 수정 시스템 기본 구조
```python
# sbkube/utils/auto_fix_system.py
from typing import Dict, Any, List, Optional, Callable
from dataclasses import dataclass, field
from enum import Enum
import os
import json
import shutil
import subprocess
from datetime import datetime
from pathlib import Path
from abc import ABC, abstractmethod

from rich.console import Console
from rich.prompt import Confirm
from rich.progress import Progress, SpinnerColumn, TextColumn

from sbkube.utils.logger import logger
from sbkube.utils.diagnostic_system import DiagnosticResult, DiagnosticLevel

class FixResult(Enum):
    SUCCESS = "success"
    FAILED = "failed"
    SKIPPED = "skipped"
    BACKUP_FAILED = "backup_failed"

@dataclass
class FixAttempt:
    """수정 시도 정보"""
    fix_id: str
    description: str
    command: str
    result: FixResult
    timestamp: datetime = field(default_factory=datetime.now)
    backup_path: Optional[str] = None
    error_message: Optional[str] = None
    execution_time: float = 0.0
    
    def to_dict(self) -> Dict[str, Any]:
        """딕셔너리로 변환"""
        return {
            'fix_id': self.fix_id,
            'description': self.description,
            'command': self.command,
            'result': self.result.value,
            'timestamp': self.timestamp.isoformat(),
            'backup_path': self.backup_path,
            'error_message': self.error_message,
            'execution_time': self.execution_time
        }
    
    @classmethod
    def from_dict(cls, data: Dict[str, Any]) -> 'FixAttempt':
        """딕셔너리에서 생성"""
        attempt = cls(
            fix_id=data['fix_id'],
            description=data['description'],
            command=data['command'],
            result=FixResult(data['result'])
        )
        attempt.timestamp = datetime.fromisoformat(data['timestamp'])
        attempt.backup_path = data.get('backup_path')
        attempt.error_message = data.get('error_message')
        attempt.execution_time = data.get('execution_time', 0.0)
        return attempt

class AutoFix(ABC):
    """자동 수정 기본 클래스"""
    
    def __init__(self, fix_id: str, description: str, risk_level: str = "low"):
        self.fix_id = fix_id
        self.description = description
        self.risk_level = risk_level  # low, medium, high
    
    @abstractmethod
    def can_fix(self, diagnostic_result: DiagnosticResult) -> bool:
        """수정 가능 여부 확인"""
        pass
    
    @abstractmethod
    def create_backup(self) -> Optional[str]:
        """백업 생성 (백업 경로 반환, None이면 백업 불필요)"""
        pass
    
    @abstractmethod
    def apply_fix(self, diagnostic_result: DiagnosticResult) -> bool:
        """수정 적용"""
        pass
    
    @abstractmethod
    def rollback(self, backup_path: str) -> bool:
        """롤백 실행"""
        pass
    
    def validate_fix(self, diagnostic_result: DiagnosticResult) -> bool:
        """수정 후 검증 (기본 구현)"""
        return True

class AutoFixEngine:
    """자동 수정 엔진"""
    
    def __init__(self, base_dir: str = ".", console: Console = None):
        self.base_dir = Path(base_dir)
        self.console = console or Console()
        self.fixes: List[AutoFix] = []
        self.fix_history: List[FixAttempt] = []
        
        # 백업 및 히스토리 디렉토리
        self.backup_dir = self.base_dir / ".sbkube" / "backups"
        self.history_dir = self.base_dir / ".sbkube" / "fix_history"
        self.backup_dir.mkdir(parents=True, exist_ok=True)
        self.history_dir.mkdir(parents=True, exist_ok=True)
        
        # 히스토리 로드
        self._load_fix_history()
    
    def register_fix(self, auto_fix: AutoFix):
        """자동 수정 등록"""
        self.fixes.append(auto_fix)
    
    def find_applicable_fixes(self, diagnostic_results: List[DiagnosticResult]) -> List[tuple]:
        """적용 가능한 수정 찾기"""
        applicable = []
        
        for result in diagnostic_results:
            if not result.is_fixable:
                continue
            
            for fix in self.fixes:
                if fix.can_fix(result):
                    applicable.append((fix, result))
                    break  # 하나의 결과에 대해 첫 번째 매칭되는 수정만 사용
        
        return applicable
    
    def apply_fixes(self, diagnostic_results: List[DiagnosticResult], 
                   interactive: bool = True, force: bool = False) -> List[FixAttempt]:
        """수정 적용"""
        applicable_fixes = self.find_applicable_fixes(diagnostic_results)
        
        if not applicable_fixes:
            self.console.print("🤷 적용 가능한 자동 수정이 없습니다.")
            return []
        
        self.console.print(f"\n🔧 {len(applicable_fixes)}개의 자동 수정을 찾았습니다:")
        
        # 수정 목록 표시
        for i, (fix, result) in enumerate(applicable_fixes, 1):
            risk_color = {"low": "green", "medium": "yellow", "high": "red"}.get(fix.risk_level, "white")
            self.console.print(f"  {i}. [{risk_color}]{fix.description}[/{risk_color}] (위험도: {fix.risk_level})")
            self.console.print(f"     문제: {result.message}")
        
        if interactive and not force:
            if not Confirm.ask("\n이 수정들을 적용하시겠습니까?"):
                return []
        
        # 수정 실행
        attempts = []
        
        with Progress(
            SpinnerColumn(),
            TextColumn("[bold blue]{task.description}"),
            console=self.console,
            transient=True
        ) as progress:
            
            for fix, result in applicable_fixes:
                task = progress.add_task(f"적용 중: {fix.description}")
                
                attempt = self._apply_single_fix(fix, result)
                attempts.append(attempt)
                
                # 결과에 따른 메시지
                if attempt.result == FixResult.SUCCESS:
                    self.console.print(f"✅ {fix.description}")
                elif attempt.result == FixResult.FAILED:
                    self.console.print(f"❌ {fix.description}: {attempt.error_message}")
                elif attempt.result == FixResult.BACKUP_FAILED:
                    self.console.print(f"⚠️  {fix.description}: 백업 실패")
                
                progress.remove_task(task)
        
        self._save_fix_history()
        return attempts
    
    def _apply_single_fix(self, fix: AutoFix, result: DiagnosticResult) -> FixAttempt:
        """단일 수정 적용"""
        start_time = datetime.now()
        
        attempt = FixAttempt(
            fix_id=fix.fix_id,
            description=fix.description,
            command=result.fix_command or ""
        )
        
        try:
            # 백업 생성
            backup_path = fix.create_backup()
            attempt.backup_path = backup_path
            
            if backup_path and not Path(backup_path).exists():
                attempt.result = FixResult.BACKUP_FAILED
                attempt.error_message = "백업 생성 실패"
                return attempt
            
            # 수정 적용
            success = fix.apply_fix(result)
            
            if success:
                # 수정 후 검증
                if fix.validate_fix(result):
                    attempt.result = FixResult.SUCCESS
                else:
                    attempt.result = FixResult.FAILED
                    attempt.error_message = "수정 후 검증 실패"
                    
                    # 롤백 시도
                    if backup_path:
                        fix.rollback(backup_path)
            else:
                attempt.result = FixResult.FAILED
                attempt.error_message = "수정 적용 실패"
                
        except Exception as e:
            attempt.result = FixResult.FAILED
            attempt.error_message = str(e)
            logger.error(f"수정 적용 중 오류: {e}")
        
        finally:
            attempt.execution_time = (datetime.now() - start_time).total_seconds()
            self.fix_history.append(attempt)
        
        return attempt
    
    def rollback_last_fixes(self, count: int = 1) -> bool:
        """최근 수정 롤백"""
        recent_successful = [
            attempt for attempt in reversed(self.fix_history)
            if attempt.result == FixResult.SUCCESS and attempt.backup_path
        ][:count]
        
        if not recent_successful:
            self.console.print("롤백할 수 있는 최근 수정이 없습니다.")
            return False
        
        self.console.print(f"최근 {len(recent_successful)}개 수정을 롤백합니다:")
        
        for attempt in recent_successful:
            self.console.print(f"🔄 롤백 중: {attempt.description}")
            
            try:
                # 해당 수정에 대한 AutoFix 찾기
                fix = next((f for f in self.fixes if f.fix_id == attempt.fix_id), None)
                
                if fix and fix.rollback(attempt.backup_path):
                    self.console.print(f"✅ 롤백 완료: {attempt.description}")
                else:
                    self.console.print(f"❌ 롤백 실패: {attempt.description}")
                    return False
                    
            except Exception as e:
                self.console.print(f"❌ 롤백 오류: {e}")
                return False
        
        return True
    
    def _load_fix_history(self):
        """수정 히스토리 로드"""
        history_file = self.history_dir / "fix_history.json"
        
        if history_file.exists():
            try:
                with open(history_file, 'r', encoding='utf-8') as f:
                    data = json.load(f)
                
                self.fix_history = [FixAttempt.from_dict(item) for item in data]
                
            except Exception as e:
                logger.warning(f"수정 히스토리 로드 실패: {e}")
    
    def _save_fix_history(self):
        """수정 히스토리 저장"""
        history_file = self.history_dir / "fix_history.json"
        
        try:
            # 최근 100개만 유지
            recent_history = self.fix_history[-100:]
            
            with open(history_file, 'w', encoding='utf-8') as f:
                json.dump([attempt.to_dict() for attempt in recent_history], 
                         f, indent=2, ensure_ascii=False)
                
        except Exception as e:
            logger.error(f"수정 히스토리 저장 실패: {e}")
    
    def cleanup_old_backups(self, keep_days: int = 7):
        """오래된 백업 정리"""
        if not self.backup_dir.exists():
            return
        
        cutoff_time = datetime.now().timestamp() - (keep_days * 24 * 3600)
        cleaned_count = 0
        
        for backup_path in self.backup_dir.rglob("*"):
            if backup_path.is_file() and backup_path.stat().st_mtime < cutoff_time:
                try:
                    backup_path.unlink()
                    cleaned_count += 1
                except Exception as e:
                    logger.warning(f"백업 파일 삭제 실패 ({backup_path}): {e}")
        
        if cleaned_count > 0:
            logger.info(f"🧹 {cleaned_count}개의 오래된 백업 파일을 정리했습니다")
```

### 2. 구체적인 자동 수정 구현
```python
# sbkube/fixes/namespace_fixes.py
import subprocess
from pathlib import Path
import shutil
from datetime import datetime

from sbkube.utils.auto_fix_system import AutoFix
from sbkube.utils.diagnostic_system import DiagnosticResult

class MissingNamespaceFix(AutoFix):
    """누락된 네임스페이스 생성"""
    
    def __init__(self):
        super().__init__(
            fix_id="create_missing_namespace",
            description="누락된 네임스페이스 생성",
            risk_level="low"
        )
    
    def can_fix(self, diagnostic_result: DiagnosticResult) -> bool:
        """수정 가능 여부 확인"""
        return (
            "네임스페이스" in diagnostic_result.message and
            "존재하지 않음" in diagnostic_result.message
        )
    
    def create_backup(self) -> Optional[str]:
        """백업 생성 (네임스페이스는 백업 불필요)"""
        return None
    
    def apply_fix(self, diagnostic_result: DiagnosticResult) -> bool:
        """네임스페이스 생성"""
        try:
            # 네임스페이스 이름 추출
            namespace = self._extract_namespace_name(diagnostic_result.message)
            if not namespace:
                return False
            
            # 네임스페이스 생성
            result = subprocess.run([
                "kubectl", "create", "namespace", namespace
            ], capture_output=True, text=True, timeout=30)
            
            return result.returncode == 0
            
        except Exception:
            return False
    
    def rollback(self, backup_path: str) -> bool:
        """롤백 (네임스페이스 삭제)"""
        try:
            # 실제 환경에서는 신중하게 처리해야 함
            # 여기서는 기본 구현만 제공
            return True
        except Exception:
            return False
    
    def _extract_namespace_name(self, message: str) -> Optional[str]:
        """오류 메시지에서 네임스페이스 이름 추출"""
        import re
        match = re.search(r"'([^']+)'", message)
        return match.group(1) if match else None

class ConfigFileFix(AutoFix):
    """설정 파일 수정"""
    
    def __init__(self):
        super().__init__(
            fix_id="fix_config_file",
            description="설정 파일 오류 수정",
            risk_level="medium"
        )
    
    def can_fix(self, diagnostic_result: DiagnosticResult) -> bool:
        """수정 가능 여부 확인"""
        return (
            "설정 파일" in diagnostic_result.message or
            "config.yaml" in diagnostic_result.message
        )
    
    def create_backup(self) -> Optional[str]:
        """설정 파일 백업"""
        try:
            config_file = Path("config/config.yaml")
            if not config_file.exists():
                return None
            
            backup_dir = Path(".sbkube/backups")
            backup_dir.mkdir(parents=True, exist_ok=True)
            
            timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
            backup_path = backup_dir / f"config_backup_{timestamp}.yaml"
            
            shutil.copy2(config_file, backup_path)
            return str(backup_path)
            
        except Exception:
            return None
    
    def apply_fix(self, diagnostic_result: DiagnosticResult) -> bool:
        """설정 파일 수정"""
        try:
            if "필수 설정이 누락" in diagnostic_result.message:
                return self._add_missing_fields(diagnostic_result)
            elif "YAML 문법 오류" in diagnostic_result.message:
                return self._fix_yaml_syntax(diagnostic_result)
            
            return False
            
        except Exception:
            return False
    
    def rollback(self, backup_path: str) -> bool:
        """설정 파일 롤백"""
        try:
            config_file = Path("config/config.yaml")
            shutil.copy2(backup_path, config_file)
            return True
        except Exception:
            return False
    
    def _add_missing_fields(self, diagnostic_result: DiagnosticResult) -> bool:
        """누락된 필드 추가"""
        import yaml
        
        try:
            config_file = Path("config/config.yaml")
            
            with open(config_file, 'r', encoding='utf-8') as f:
                config = yaml.safe_load(f) or {}
            
            # 기본 필드 추가
            if 'namespace' not in config:
                config['namespace'] = 'default'
            
            if 'apps' not in config:
                config['apps'] = []
            
            with open(config_file, 'w', encoding='utf-8') as f:
                yaml.dump(config, f, default_flow_style=False, allow_unicode=True)
            
            return True
            
        except Exception:
            return False
    
    def _fix_yaml_syntax(self, diagnostic_result: DiagnosticResult) -> bool:
        """YAML 문법 오류 수정 (기본적인 것만)"""
        try:
            config_file = Path("config/config.yaml")
            
            with open(config_file, 'r', encoding='utf-8') as f:
                content = f.read()
            
            # 기본적인 YAML 수정
            # 탭을 스페이스로 변경
            content = content.replace('\t', '  ')
            
            # 기본 구조가 없으면 추가
            if not content.strip():
                content = "namespace: default\napps: []\n"
            
            with open(config_file, 'w', encoding='utf-8') as f:
                f.write(content)
            
            # YAML 파싱 테스트
            import yaml
            yaml.safe_load(content)
            
            return True
            
        except Exception:
            return False

class HelmRepositoryFix(AutoFix):
    """Helm 리포지토리 추가"""
    
    def __init__(self):
        super().__init__(
            fix_id="add_helm_repository",
            description="필요한 Helm 리포지토리 추가",
            risk_level="low"
        )
    
    def can_fix(self, diagnostic_result: DiagnosticResult) -> bool:
        """수정 가능 여부 확인"""
        return (
            "helm" in diagnostic_result.message.lower() and
            ("리포지토리" in diagnostic_result.message or "repository" in diagnostic_result.message)
        )
    
    def create_backup(self) -> Optional[str]:
        """백업 생성 (리포지토리 목록 백업)"""
        try:
            result = subprocess.run([
                "helm", "repo", "list", "-o", "json"
            ], capture_output=True, text=True, timeout=10)
            
            if result.returncode == 0:
                backup_dir = Path(".sbkube/backups")
                backup_dir.mkdir(parents=True, exist_ok=True)
                
                timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
                backup_path = backup_dir / f"helm_repos_backup_{timestamp}.json"
                
                with open(backup_path, 'w', encoding='utf-8') as f:
                    f.write(result.stdout)
                
                return str(backup_path)
            
            return None
            
        except Exception:
            return None
    
    def apply_fix(self, diagnostic_result: DiagnosticResult) -> bool:
        """Helm 리포지토리 추가"""
        try:
            # 기본 리포지토리들 추가
            repositories = [
                ("bitnami", "https://charts.bitnami.com/bitnami"),
                ("stable", "https://charts.helm.sh/stable")
            ]
            
            success = True
            for name, url in repositories:
                result = subprocess.run([
                    "helm", "repo", "add", name, url
                ], capture_output=True, text=True, timeout=30)
                
                if result.returncode != 0:
                    success = False
            
            if success:
                # 리포지토리 업데이트
                subprocess.run([
                    "helm", "repo", "update"
                ], capture_output=True, text=True, timeout=60)
            
            return success
            
        except Exception:
            return False
    
    def rollback(self, backup_path: str) -> bool:
        """Helm 리포지토리 롤백"""
        try:
            # 현재 리포지토리 제거
            result = subprocess.run([
                "helm", "repo", "list", "-o", "json"
            ], capture_output=True, text=True, timeout=10)
            
            if result.returncode == 0:
                import json
                current_repos = json.loads(result.stdout)
                
                for repo in current_repos:
                    subprocess.run([
                        "helm", "repo", "remove", repo["name"]
                    ], capture_output=True, text=True, timeout=10)
            
            # 백업된 리포지토리 복원
            with open(backup_path, 'r', encoding='utf-8') as f:
                backup_repos = json.load(f)
            
            for repo in backup_repos:
                subprocess.run([
                    "helm", "repo", "add", repo["name"], repo["url"]
                ], capture_output=True, text=True, timeout=30)
            
            return True
            
        except Exception:
            return False
```

### 3. Fix 명령어 구현
```python
# sbkube/commands/fix.py
import click
import sys

from rich.console import Console
from sbkube.utils.auto_fix_system import AutoFixEngine
from sbkube.utils.diagnostic_system import DiagnosticEngine
from sbkube.fixes.namespace_fixes import MissingNamespaceFix, ConfigFileFix, HelmRepositoryFix
from sbkube.diagnostics.kubernetes_checks import (
    KubernetesConnectivityCheck, HelmInstallationCheck, ConfigValidityCheck
)

console = Console()

@click.command(name="fix")
@click.option("--dry-run", is_flag=True, help="실제 적용하지 않고 수정 계획만 표시")
@click.option("--force", is_flag=True, help="대화형 확인 없이 자동 실행")
@click.option("--rollback", type=int, help="최근 N개 수정 롤백")
@click.option("--backup-cleanup", is_flag=True, help="오래된 백업 파일 정리")
@click.pass_context
def cmd(ctx, dry_run, force, rollback, backup_cleanup):
    """자동 수정 시스템
    
    sbkube doctor에서 발견된 문제들을 자동으로 수정합니다.
    수정 전 백업을 생성하고 필요시 롤백할 수 있습니다.
    
    \\b
    사용 예시:
        sbkube fix                    # 대화형 자동 수정
        sbkube fix --force            # 확인 없이 자동 수정
        sbkube fix --dry-run          # 수정 계획만 표시
        sbkube fix --rollback 2       # 최근 2개 수정 롤백
        sbkube fix --backup-cleanup   # 오래된 백업 정리
    """
    
    try:
        # 자동 수정 엔진 초기화
        fix_engine = AutoFixEngine(console=console)
        
        # 자동 수정 등록
        fix_engine.register_fix(MissingNamespaceFix())
        fix_engine.register_fix(ConfigFileFix())
        fix_engine.register_fix(HelmRepositoryFix())
        
        # 백업 정리
        if backup_cleanup:
            fix_engine.cleanup_old_backups()
            console.print("✅ 백업 정리가 완료되었습니다.")
            return
        
        # 롤백
        if rollback:
            success = fix_engine.rollback_last_fixes(rollback)
            sys.exit(0 if success else 1)
        
        # 진단 실행
        console.print("🔍 문제 진단 중...")
        
        diagnostic_engine = DiagnosticEngine()
        diagnostic_engine.register_check(KubernetesConnectivityCheck())
        diagnostic_engine.register_check(HelmInstallationCheck())
        diagnostic_engine.register_check(ConfigValidityCheck())
        
        import asyncio
        results = asyncio.run(diagnostic_engine.run_all_checks(show_progress=False))
        
        # 수정 가능한 문제 필터링
        fixable_results = [r for r in results if r.is_fixable]
        
        if not fixable_results:
            console.print("🎉 수정 가능한 문제가 없습니다!")
            return
        
        # Dry run
        if dry_run:
            _show_fix_plan(fix_engine, fixable_results)
            return
        
        # 자동 수정 실행
        attempts = fix_engine.apply_fixes(
            fixable_results, 
            interactive=not force,
            force=force
        )
        
        # 결과 요약
        _show_fix_summary(attempts)
        
        # 실패한 수정이 있으면 종료 코드 1
        failed_attempts = [a for a in attempts if a.result.value != "success"]
        sys.exit(1 if failed_attempts else 0)
        
    except Exception as e:
        console.print(f"❌ 자동 수정 실행 실패: {e}")
        sys.exit(1)

def _show_fix_plan(fix_engine: AutoFixEngine, results: List) -> None:
    """수정 계획 표시"""
    applicable_fixes = fix_engine.find_applicable_fixes(results)
    
    console.print("🔍 자동 수정 계획:")
    console.print("━" * 50)
    
    for i, (fix, result) in enumerate(applicable_fixes, 1):
        risk_color = {"low": "green", "medium": "yellow", "high": "red"}.get(fix.risk_level, "white")
        console.print(f"{i}. [{risk_color}]{fix.description}[/{risk_color}]")
        console.print(f"   문제: {result.message}")
        console.print(f"   위험도: {fix.risk_level}")
        if result.fix_command:
            console.print(f"   명령어: {result.fix_command}")
        console.print()
    
    console.print(f"💡 실제 수정을 실행하려면 --dry-run 옵션을 제거하세요.")

def _show_fix_summary(attempts: List) -> None:
    """수정 결과 요약"""
    from collections import Counter
    
    results = Counter(attempt.result.value for attempt in attempts)
    
    console.print("\n📊 수정 결과 요약:")
    console.print("━" * 30)
    
    if results['success'] > 0:
        console.print(f"✅ 성공: {results['success']}개")
    if results['failed'] > 0:
        console.print(f"❌ 실패: {results['failed']}개")
    if results['skipped'] > 0:
        console.print(f"⏭️  건너뜀: {results['skipped']}개")
    if results['backup_failed'] > 0:
        console.print(f"⚠️  백업 실패: {results['backup_failed']}개")
    
    # 실패한 수정들 상세 표시
    failed_attempts = [a for a in attempts if a.result.value == 'failed']
    if failed_attempts:
        console.print("\n❌ 실패한 수정:")
        for attempt in failed_attempts:
            console.print(f"  • {attempt.description}: {attempt.error_message}")
    
    console.print(f"\n💡 문제가 지속되면 [bold]sbkube fix --rollback 1[/bold]로 롤백할 수 있습니다.")
```

## 🧪 테스트 구현

### 단위 테스트
```python
# tests/unit/utils/test_auto_fix_system.py
import pytest
import tempfile
from pathlib import Path
from unittest.mock import patch, MagicMock

from sbkube.utils.auto_fix_system import AutoFixEngine, FixResult
from sbkube.fixes.namespace_fixes import MissingNamespaceFix
from sbkube.utils.diagnostic_system import DiagnosticResult, DiagnosticLevel

class TestAutoFixSystem:
    def test_auto_fix_engine_initialization(self):
        """자동 수정 엔진 초기화 테스트"""
        with tempfile.TemporaryDirectory() as tmpdir:
            engine = AutoFixEngine(tmpdir)
            
            assert engine.base_dir == Path(tmpdir)
            assert len(engine.fixes) == 0
            assert len(engine.fix_history) == 0
    
    def test_missing_namespace_fix_detection(self):
        """네임스페이스 수정 감지 테스트"""
        fix = MissingNamespaceFix()
        
        # 매칭되는 경우
        result = DiagnosticResult(
            check_name="test",
            level=DiagnosticLevel.ERROR,
            message="네임스페이스 'production'이 존재하지 않음",
            fix_command="kubectl create namespace production"
        )
        
        assert fix.can_fix(result)
        
        # 매칭되지 않는 경우
        result2 = DiagnosticResult(
            check_name="test",
            level=DiagnosticLevel.ERROR,
            message="Helm이 설치되지 않음"
        )
        
        assert not fix.can_fix(result2)
    
    @patch('subprocess.run')
    def test_namespace_fix_application(self, mock_run):
        """네임스페이스 수정 적용 테스트"""
        mock_run.return_value = MagicMock(returncode=0)
        
        fix = MissingNamespaceFix()
        result = DiagnosticResult(
            check_name="test",
            level=DiagnosticLevel.ERROR,
            message="네임스페이스 'test-ns'이 존재하지 않음"
        )
        
        success = fix.apply_fix(result)
        assert success
        
        mock_run.assert_called_with([
            "kubectl", "create", "namespace", "test-ns"
        ], capture_output=True, text=True, timeout=30)
    
    def test_fix_history_persistence(self):
        """수정 히스토리 저장/로드 테스트"""
        with tempfile.TemporaryDirectory() as tmpdir:
            engine = AutoFixEngine(tmpdir)
            
            # 히스토리 추가
            from sbkube.utils.auto_fix_system import FixAttempt
            attempt = FixAttempt(
                fix_id="test_fix",
                description="테스트 수정",
                command="test command",
                result=FixResult.SUCCESS
            )
            
            engine.fix_history.append(attempt)
            engine._save_fix_history()
            
            # 새 엔진으로 로드
            engine2 = AutoFixEngine(tmpdir)
            assert len(engine2.fix_history) == 1
            assert engine2.fix_history[0].fix_id == "test_fix"
```

## ✅ 완료 기준

- [ ] AutoFixEngine 및 AutoFix 기본 구조 구현
- [ ] 백업 및 롤백 시스템 구현
- [ ] 3개 핵심 자동 수정 구현 (Namespace, Config, Helm)
- [ ] sbkube fix 명령어 구현
- [ ] 수정 히스토리 관리 시스템
- [ ] 안전성 검증 및 검증 로직
- [ ] 단위 테스트 작성 및 통과

## 🔍 검증 명령어

```bash
# 자동 수정 계획 확인
sbkube fix --dry-run

# 대화형 자동 수정
sbkube fix

# 강제 자동 수정 (확인 없음)
sbkube fix --force

# 최근 수정 롤백
sbkube fix --rollback 1

# 백업 정리
sbkube fix --backup-cleanup

# 테스트 실행
pytest tests/unit/utils/test_auto_fix_system.py -v
```

## 📝 예상 결과

```
🔍 문제 진단 중...

🔧 3개의 자동 수정을 찾았습니다:
  1. 누락된 네임스페이스 생성 (위험도: low)
     문제: 네임스페이스 'production'이 존재하지 않음
  2. 설정 파일 오류 수정 (위험도: medium)  
     문제: 필수 설정이 누락되었습니다: namespace
  3. 필요한 Helm 리포지토리 추가 (위험도: low)
     문제: bitnami 리포지토리가 설정되지 않음

이 수정들을 적용하시겠습니까? (y/n): y

✅ 누락된 네임스페이스 생성
✅ 설정 파일 오류 수정
✅ 필요한 Helm 리포지토리 추가

📊 수정 결과 요약:
━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
✅ 성공: 3개

💡 문제가 지속되면 sbkube fix --rollback 1로 롤백할 수 있습니다.
```

## 🔄 다음 단계

이 작업 완료 후 다음 작업으로 진행:
- `013-intelligent-validation-system.md` - 지능형 설정 검증 시스템 구현