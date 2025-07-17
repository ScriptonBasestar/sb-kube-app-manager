from abc import ABC, abstractmethod
from dataclasses import dataclass, field
from enum import Enum
from typing import Any

from rich.console import Console
from rich.progress import Progress, SpinnerColumn, TextColumn
from rich.table import Table


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
    fix_command: str | None = None
    fix_description: str | None = None
    metadata: dict[str, Any] = field(default_factory=dict)

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
            DiagnosticLevel.INFO: "🔵",
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

    def create_result(
        self,
        level: DiagnosticLevel,
        message: str,
        details: str = "",
        fix_command: str = None,
        fix_description: str = None,
        metadata: dict[str, Any] = None,
    ) -> DiagnosticResult:
        """진단 결과 생성"""
        return DiagnosticResult(
            check_name=self.name,
            level=level,
            message=message,
            details=details,
            fix_command=fix_command,
            fix_description=fix_description,
            metadata=metadata or {},
        )


class DiagnosticEngine:
    """진단 엔진"""

    def __init__(self, console: Console = None):
        self.console = console or Console()
        self.checks: list[DiagnosticCheck] = []
        self.results: list[DiagnosticResult] = []

    def register_check(self, check: DiagnosticCheck):
        """진단 체크 등록"""
        self.checks.append(check)

    async def run_all_checks(
        self, show_progress: bool = True
    ) -> list[DiagnosticResult]:
        """모든 진단 체크 실행"""
        self.results.clear()

        if show_progress:
            with Progress(
                SpinnerColumn(),
                TextColumn("[bold blue]{task.description}"),
                console=self.console,
                transient=True,
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

    def get_summary(self) -> dict[str, Any]:
        """진단 요약 정보"""
        summary = {
            "total": len(self.results),
            "success": 0,
            "warning": 0,
            "error": 0,
            "info": 0,
            "fixable": 0,
        }

        for result in self.results:
            summary[result.level.value] += 1
            if result.is_fixable:
                summary["fixable"] += 1

        return summary

    def display_results(self, detailed: bool = False):
        """진단 결과 표시"""
        summary = self.get_summary()

        # 요약 정보 표시
        self._display_summary(summary)

        # 상세 결과 표시
        if detailed or summary["error"] > 0 or summary["warning"] > 0:
            self._display_detailed_results()

        # 자동 수정 제안
        if summary["fixable"] > 0:
            self._display_fix_suggestions()

    def _display_summary(self, summary: dict[str, Any]):
        """요약 정보 표시"""
        self.console.print("\n🔍 SBKube 종합 진단 결과")
        self.console.print("━" * 50)

        table = Table(show_header=False, box=None)
        table.add_column("상태", style="bold")
        table.add_column("개수", justify="right")

        if summary["success"] > 0:
            table.add_row("🟢 정상", str(summary["success"]))
        if summary["warning"] > 0:
            table.add_row("🟡 경고", str(summary["warning"]))
        if summary["error"] > 0:
            table.add_row("🔴 오류", str(summary["error"]))
        if summary["info"] > 0:
            table.add_row("🔵 정보", str(summary["info"]))

        self.console.print(table)

        if summary["fixable"] > 0:
            self.console.print(f"\n💡 자동 수정 가능한 문제: {summary['fixable']}개")

    def _display_detailed_results(self):
        """상세 결과 표시"""
        for level in [
            DiagnosticLevel.ERROR,
            DiagnosticLevel.WARNING,
            DiagnosticLevel.INFO,
        ]:
            level_results = [r for r in self.results if r.level == level]
            if not level_results:
                continue

            level_names = {
                DiagnosticLevel.ERROR: "오류",
                DiagnosticLevel.WARNING: "경고",
                DiagnosticLevel.INFO: "정보",
            }

            self.console.print(
                f"\n{level_results[0].icon} {level_names[level]} ({len(level_results)}개)"
            )

            for result in level_results:
                self.console.print(f"├── {result.message}")
                if result.details:
                    self.console.print(f"│   {result.details}")

    def _display_fix_suggestions(self):
        """자동 수정 제안 표시"""
        fixable_results = [r for r in self.results if r.is_fixable]

        self.console.print("\n🔧 자동 수정 가능한 문제:")
        for i, result in enumerate(fixable_results, 1):
            self.console.print(f"  {i}. {result.message}")
            if result.fix_description:
                self.console.print(f"     → {result.fix_description}")

        self.console.print(
            "\n💡 [bold]sbkube doctor --fix[/bold] 명령어로 자동 수정을 실행할 수 있습니다."
        )

    def get_fixable_results(self) -> list[DiagnosticResult]:
        """자동 수정 가능한 결과 반환"""
        return [r for r in self.results if r.is_fixable]

    def get_results_by_level(self, level: DiagnosticLevel) -> list[DiagnosticResult]:
        """특정 레벨의 결과 반환"""
        return [r for r in self.results if r.level == level]

    def has_errors(self) -> bool:
        """오류가 있는지 확인"""
        return any(r.level == DiagnosticLevel.ERROR for r in self.results)

    def has_warnings(self) -> bool:
        """경고가 있는지 확인"""
        return any(r.level == DiagnosticLevel.WARNING for r in self.results)
