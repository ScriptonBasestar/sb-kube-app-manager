import json
from abc import ABC, abstractmethod
from dataclasses import dataclass, field
from datetime import datetime
from enum import Enum
from pathlib import Path
from typing import Any

from rich.console import Console
from rich.progress import Progress, SpinnerColumn, TextColumn
from rich.prompt import Confirm

from sbkube.utils.diagnostic_system import DiagnosticResult
from sbkube.utils.logger import logger


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
    backup_path: str | None = None
    error_message: str | None = None
    execution_time: float = 0.0

    def to_dict(self) -> dict[str, Any]:
        """딕셔너리로 변환"""
        return {
            "fix_id": self.fix_id,
            "description": self.description,
            "command": self.command,
            "result": self.result.value,
            "timestamp": self.timestamp.isoformat(),
            "backup_path": self.backup_path,
            "error_message": self.error_message,
            "execution_time": self.execution_time,
        }

    @classmethod
    def from_dict(cls, data: dict[str, Any]) -> "FixAttempt":
        """딕셔너리에서 생성"""
        attempt = cls(
            fix_id=data["fix_id"],
            description=data["description"],
            command=data["command"],
            result=FixResult(data["result"]),
        )
        attempt.timestamp = datetime.fromisoformat(data["timestamp"])
        attempt.backup_path = data.get("backup_path")
        attempt.error_message = data.get("error_message")
        attempt.execution_time = data.get("execution_time", 0.0)
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
    def create_backup(self) -> str | None:
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
        self.fixes: list[AutoFix] = []
        self.fix_history: list[FixAttempt] = []

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

    def find_applicable_fixes(
        self, diagnostic_results: list[DiagnosticResult]
    ) -> list[tuple]:
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

    def apply_fixes(
        self,
        diagnostic_results: list[DiagnosticResult],
        interactive: bool = True,
        force: bool = False,
    ) -> list[FixAttempt]:
        """수정 적용"""
        applicable_fixes = self.find_applicable_fixes(diagnostic_results)

        if not applicable_fixes:
            self.console.print("🤷 적용 가능한 자동 수정이 없습니다.")
            return []

        self.console.print(f"\n🔧 {len(applicable_fixes)}개의 자동 수정을 찾았습니다:")

        # 수정 목록 표시
        for i, (fix, result) in enumerate(applicable_fixes, 1):
            risk_color = {"low": "green", "medium": "yellow", "high": "red"}.get(
                fix.risk_level, "white"
            )
            self.console.print(
                f"  {i}. [{risk_color}]{fix.description}[/{risk_color}] (위험도: {fix.risk_level})"
            )
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
            transient=True,
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
            command=result.fix_command or "",
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
                        try:
                            fix.rollback(backup_path)
                        except Exception as e:
                            logger.warning(f"롤백 실패: {e}")
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
            attempt
            for attempt in reversed(self.fix_history)
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
                with open(history_file, encoding="utf-8") as f:
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

            with open(history_file, "w", encoding="utf-8") as f:
                json.dump(
                    [attempt.to_dict() for attempt in recent_history],
                    f,
                    indent=2,
                    ensure_ascii=False,
                )

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

    def get_history_summary(self) -> dict[str, Any]:
        """히스토리 요약 정보 반환"""
        if not self.fix_history:
            return {}

        from collections import Counter

        result_counts = Counter(attempt.result.value for attempt in self.fix_history)

        recent_attempts = self.fix_history[-10:]  # 최근 10개

        return {
            "total_attempts": len(self.fix_history),
            "success_count": result_counts.get("success", 0),
            "failed_count": result_counts.get("failed", 0),
            "skipped_count": result_counts.get("skipped", 0),
            "backup_failed_count": result_counts.get("backup_failed", 0),
            "recent_attempts": [
                {
                    "description": attempt.description,
                    "result": attempt.result.value,
                    "timestamp": attempt.timestamp.isoformat(),
                }
                for attempt in recent_attempts
            ],
        }

    def get_rollback_candidates(self, limit: int = 5) -> list[FixAttempt]:
        """롤백 가능한 수정 목록 반환"""
        return [
            attempt
            for attempt in reversed(self.fix_history)
            if attempt.result == FixResult.SUCCESS and attempt.backup_path
        ][:limit]
