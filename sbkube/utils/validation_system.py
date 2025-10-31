import json
from abc import abstractmethod
from dataclasses import dataclass, field
from datetime import datetime
from enum import Enum
from pathlib import Path
from typing import Any

from rich.console import Console
from rich.progress import BarColumn, Progress, SpinnerColumn, TextColumn
from rich.table import Table

from sbkube.utils.diagnostic_system import (
    DiagnosticCheck,
    DiagnosticEngine,
    DiagnosticLevel,
    DiagnosticResult,
)
from sbkube.utils.logger import logger


class ValidationMode(Enum):
    """검증 모드"""

    BASIC = "basic"
    COMPREHENSIVE = "comprehensive"
    PRE_DEPLOY = "pre-deploy"
    ENVIRONMENT = "environment"
    DEPENDENCIES = "dependencies"


class ValidationSeverity(Enum):
    """검증 심각도"""

    CRITICAL = "critical"
    HIGH = "high"
    MEDIUM = "medium"
    LOW = "low"
    INFO = "info"


@dataclass
class ValidationContext:
    """검증 컨텍스트"""

    config_dir: str = "config"
    base_dir: str = "."
    target_app: str | None = None
    environment: str | None = None
    profile: str | None = None
    metadata: dict[str, Any] = field(default_factory=dict)


@dataclass
class ValidationResult:
    """검증 결과 (DiagnosticResult 확장)"""

    check_name: str
    category: str  # configuration, environment, dependencies, pre-deployment
    level: DiagnosticLevel
    severity: ValidationSeverity
    message: str
    details: str = ""
    recommendation: str | None = None
    fix_command: str | None = None
    fix_description: str | None = None
    risk_level: str = "low"  # low, medium, high, critical
    affected_components: list[str] = field(default_factory=list)
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

    @property
    def severity_icon(self) -> str:
        """심각도 아이콘"""
        icons = {
            ValidationSeverity.CRITICAL: "🚨",
            ValidationSeverity.HIGH: "⚠️",
            ValidationSeverity.MEDIUM: "⚡",
            ValidationSeverity.LOW: "💡",
            ValidationSeverity.INFO: "ℹ️",
        }
        return icons[self.severity]

    def to_dict(self) -> dict[str, Any]:
        """딕셔너리로 변환"""
        return {
            "check_name": self.check_name,
            "category": self.category,
            "level": self.level.value,
            "severity": self.severity.value,
            "message": self.message,
            "details": self.details,
            "recommendation": self.recommendation,
            "fix_command": self.fix_command,
            "fix_description": self.fix_description,
            "risk_level": self.risk_level,
            "affected_components": self.affected_components,
            "metadata": self.metadata,
        }

    @classmethod
    def from_diagnostic_result(
        cls,
        diagnostic_result: DiagnosticResult,
        category: str = "general",
        severity: ValidationSeverity = ValidationSeverity.MEDIUM,
    ) -> "ValidationResult":
        """DiagnosticResult에서 변환"""
        return cls(
            check_name=diagnostic_result.check_name,
            category=category,
            level=diagnostic_result.level,
            severity=severity,
            message=diagnostic_result.message,
            details=diagnostic_result.details,
            fix_command=diagnostic_result.fix_command,
            fix_description=diagnostic_result.fix_description,
            metadata=diagnostic_result.metadata,
        )


class ValidationCheck(DiagnosticCheck):
    """검증 체크 기본 클래스 (DiagnosticCheck 확장)"""

    def __init__(self, name: str, description: str, category: str = "general"):
        super().__init__(name, description)
        self.category = category

    @abstractmethod
    async def run_validation(self, context: ValidationContext) -> ValidationResult:
        """검증 실행 (확장된 컨텍스트 사용)"""
        pass

    async def run(self) -> DiagnosticResult:
        """기존 DiagnosticCheck 인터페이스 호환성"""
        # 기본 컨텍스트로 실행
        context = ValidationContext()
        validation_result = await self.run_validation(context)

        # DiagnosticResult로 변환
        return DiagnosticResult(
            check_name=validation_result.check_name,
            level=validation_result.level,
            message=validation_result.message,
            details=validation_result.details,
            fix_command=validation_result.fix_command,
            fix_description=validation_result.fix_description,
            metadata=validation_result.metadata,
        )

    def create_validation_result(
        self,
        level: DiagnosticLevel,
        message: str,
        severity: ValidationSeverity = ValidationSeverity.MEDIUM,
        details: str = "",
        recommendation: str = None,
        fix_command: str = None,
        fix_description: str = None,
        risk_level: str = "low",
        affected_components: list[str] = None,
        metadata: dict[str, Any] = None,
    ) -> ValidationResult:
        """검증 결과 생성"""
        return ValidationResult(
            check_name=self.name,
            category=self.category,
            level=level,
            severity=severity,
            message=message,
            details=details,
            recommendation=recommendation,
            fix_command=fix_command,
            fix_description=fix_description,
            risk_level=risk_level,
            affected_components=affected_components or [],
            metadata=metadata or {},
        )


class ValidationReport:
    """검증 보고서"""

    def __init__(self, validation_mode: ValidationMode, context: ValidationContext):
        self.validation_mode = validation_mode
        self.context = context
        self.results: list[ValidationResult] = []
        self.start_time: datetime | None = None
        self.end_time: datetime | None = None
        self.metadata: dict[str, Any] = {}

    def add_result(self, result: ValidationResult):
        """검증 결과 추가"""
        self.results.append(result)

    def add_results(self, results: list[ValidationResult]):
        """여러 검증 결과 추가"""
        self.results.extend(results)

    def get_summary(self) -> dict[str, Any]:
        """검증 요약 정보"""
        summary = {
            "validation_mode": self.validation_mode.value,
            "total_checks": len(self.results),
            "start_time": self.start_time.isoformat() if self.start_time else None,
            "end_time": self.end_time.isoformat() if self.end_time else None,
            "duration_seconds": 0,
            "by_level": {"success": 0, "warning": 0, "error": 0, "info": 0},
            "by_severity": {"critical": 0, "high": 0, "medium": 0, "low": 0, "info": 0},
            "by_category": {},
            "by_risk_level": {"critical": 0, "high": 0, "medium": 0, "low": 0},
            "fixable_count": 0,
            "critical_issues": 0,
            "deployment_ready": True,
        }

        # 실행 시간 계산
        if self.start_time and self.end_time:
            duration = self.end_time - self.start_time
            summary["duration_seconds"] = duration.total_seconds()

        # 결과 집계
        for result in self.results:
            summary["by_level"][result.level.value] += 1
            summary["by_severity"][result.severity.value] += 1
            summary["by_risk_level"][result.risk_level] += 1

            if result.category not in summary["by_category"]:
                summary["by_category"][result.category] = 0
            summary["by_category"][result.category] += 1

            if result.is_fixable:
                summary["fixable_count"] += 1

            if result.severity in [
                ValidationSeverity.CRITICAL,
                ValidationSeverity.HIGH,
            ]:
                summary["critical_issues"] += 1

            # 배포 준비 상태 평가
            if (
                result.level == DiagnosticLevel.ERROR
                or result.severity == ValidationSeverity.CRITICAL
            ):
                summary["deployment_ready"] = False

        return summary

    def get_results_by_category(self, category: str) -> list[ValidationResult]:
        """카테고리별 결과 반환"""
        return [r for r in self.results if r.category == category]

    def get_results_by_level(self, level: DiagnosticLevel) -> list[ValidationResult]:
        """레벨별 결과 반환"""
        return [r for r in self.results if r.level == level]

    def get_results_by_severity(
        self, severity: ValidationSeverity
    ) -> list[ValidationResult]:
        """심각도별 결과 반환"""
        return [r for r in self.results if r.severity == severity]

    def get_fixable_results(self) -> list[ValidationResult]:
        """자동 수정 가능한 결과 반환"""
        return [r for r in self.results if r.is_fixable]

    def get_critical_results(self) -> list[ValidationResult]:
        """심각한 문제 결과 반환"""
        return [
            r
            for r in self.results
            if r.level == DiagnosticLevel.ERROR
            or r.severity in [ValidationSeverity.CRITICAL, ValidationSeverity.HIGH]
        ]

    def is_deployment_ready(self) -> bool:
        """배포 준비 상태 확인"""
        summary = self.get_summary()
        return summary["deployment_ready"]

    def to_dict(self) -> dict[str, Any]:
        """딕셔너리로 변환"""
        return {
            "validation_mode": self.validation_mode.value,
            "context": {
                "config_dir": self.context.config_dir,
                "base_dir": self.context.base_dir,
                "target_app": self.context.target_app,
                "environment": self.context.environment,
                "profile": self.context.profile,
                "metadata": self.context.metadata,
            },
            "summary": self.get_summary(),
            "results": [result.to_dict() for result in self.results],
            "metadata": self.metadata,
        }


class ValidationEngine(DiagnosticEngine):
    """검증 엔진 (DiagnosticEngine 확장)"""

    def __init__(
        self,
        console: Console = None,
        validation_mode: ValidationMode = ValidationMode.BASIC,
    ):
        super().__init__(console)
        self.validation_mode = validation_mode
        self.validators: list[ValidationCheck] = []
        self.current_report: ValidationReport | None = None

    def register_validator(self, validator: ValidationCheck):
        """검증기 등록 (DiagnosticCheck 호환성 유지)"""
        self.validators.append(validator)
        # 부모 클래스의 checks에도 추가 (호환성)
        super().register_check(validator)

    async def run_validation_suite(
        self, context: ValidationContext, show_progress: bool = True
    ) -> ValidationReport:
        """검증 스위트 실행"""
        # 새 보고서 생성
        self.current_report = ValidationReport(self.validation_mode, context)
        self.current_report.start_time = datetime.now()

        logger.info(f"🔍 {self.validation_mode.value} 검증 시작")

        if show_progress:
            with Progress(
                SpinnerColumn(),
                TextColumn("[bold blue]{task.description}"),
                BarColumn(),
                TextColumn("[progress.percentage]{task.percentage:>3.0f}%"),
                console=self.console,
                transient=True,
            ) as progress:
                task = progress.add_task("검증 실행 중...", total=len(self.validators))

                for validator in self.validators:
                    progress.update(
                        task, description=f"검증 중: {validator.description}"
                    )
                    try:
                        result = await validator.run_validation(context)
                        self.current_report.add_result(result)
                    except Exception as e:
                        # 검증 실행 오류 처리
                        error_result = ValidationResult(
                            check_name=validator.name,
                            category=validator.category,
                            level=DiagnosticLevel.ERROR,
                            severity=ValidationSeverity.HIGH,
                            message=f"검증 실행 실패: {str(e)}",
                            details=f"검증기 '{validator.description}' 실행 중 오류가 발생했습니다.",
                            risk_level="high",
                        )
                        self.current_report.add_result(error_result)
                        logger.error(f"검증기 {validator.name} 실행 실패: {e}")

                    progress.advance(task)
        else:
            for validator in self.validators:
                try:
                    result = await validator.run_validation(context)
                    self.current_report.add_result(result)
                except Exception as e:
                    error_result = ValidationResult(
                        check_name=validator.name,
                        category=validator.category,
                        level=DiagnosticLevel.ERROR,
                        severity=ValidationSeverity.HIGH,
                        message=f"검증 실행 실패: {str(e)}",
                        details=f"검증기 '{validator.description}' 실행 중 오류가 발생했습니다.",
                        risk_level="high",
                    )
                    self.current_report.add_result(error_result)
                    logger.error(f"검증기 {validator.name} 실행 실패: {e}")

        self.current_report.end_time = datetime.now()

        # DiagnosticEngine의 results도 업데이트 (호환성)
        self.results = [
            self._validation_to_diagnostic_result(r)
            for r in self.current_report.results
        ]

        return self.current_report

    def _validation_to_diagnostic_result(
        self, validation_result: ValidationResult
    ) -> DiagnosticResult:
        """ValidationResult를 DiagnosticResult로 변환"""
        return DiagnosticResult(
            check_name=validation_result.check_name,
            level=validation_result.level,
            message=validation_result.message,
            details=validation_result.details,
            fix_command=validation_result.fix_command,
            fix_description=validation_result.fix_description,
            metadata=validation_result.metadata,
        )

    def display_validation_results(self, detailed: bool = False):
        """검증 결과 표시"""
        if not self.current_report:
            self.console.print("❌ 검증 결과가 없습니다.")
            return

        summary = self.current_report.get_summary()

        # 헤더 표시
        self._display_validation_header(summary)

        # 요약 정보 표시
        self._display_validation_summary(summary)

        # 카테고리별 결과 표시
        if (
            detailed
            or summary["by_level"]["error"] > 0
            or summary["by_level"]["warning"] > 0
        ):
            self._display_detailed_validation_results()

        # 배포 준비 상태 표시
        self._display_deployment_readiness(summary)

        # 자동 수정 제안
        if summary["fixable_count"] > 0:
            self._display_validation_fix_suggestions()

    def _display_validation_header(self, summary: dict[str, Any]):
        """검증 헤더 표시"""
        mode_descriptions = {
            ValidationMode.BASIC.value: "기본 검증",
            ValidationMode.COMPREHENSIVE.value: "종합 검증",
            ValidationMode.PRE_DEPLOY.value: "배포 전 검증",
            ValidationMode.ENVIRONMENT.value: "환경 검증",
            ValidationMode.DEPENDENCIES.value: "의존성 검증",
        }

        title = f"🔍 SBKube {mode_descriptions.get(summary['validation_mode'], '검증')} 결과"
        self.console.print(f"\n{title}")
        self.console.print("━" * len(title))

        if summary["duration_seconds"] > 0:
            self.console.print(f"실행 시간: {summary['duration_seconds']:.2f}초")

    def _display_validation_summary(self, summary: dict[str, Any]):
        """검증 요약 표시"""
        table = Table(show_header=False, box=None)
        table.add_column("상태", style="bold")
        table.add_column("개수", justify="right")

        if summary["by_level"]["success"] > 0:
            table.add_row("🟢 정상", str(summary["by_level"]["success"]))
        if summary["by_level"]["warning"] > 0:
            table.add_row("🟡 경고", str(summary["by_level"]["warning"]))
        if summary["by_level"]["error"] > 0:
            table.add_row("🔴 오류", str(summary["by_level"]["error"]))
        if summary["by_level"]["info"] > 0:
            table.add_row("🔵 정보", str(summary["by_level"]["info"]))

        self.console.print(table)

        # 심각도별 요약
        if summary["critical_issues"] > 0:
            self.console.print(f"\n⚠️  심각한 문제: {summary['critical_issues']}개")

        if summary["fixable_count"] > 0:
            self.console.print(f"💡 자동 수정 가능: {summary['fixable_count']}개")

    def _display_detailed_validation_results(self):
        """상세 검증 결과 표시"""
        categories = {r.category for r in self.current_report.results}

        for category in sorted(categories):
            category_results = self.current_report.get_results_by_category(category)
            error_results = [
                r for r in category_results if r.level == DiagnosticLevel.ERROR
            ]
            warning_results = [
                r for r in category_results if r.level == DiagnosticLevel.WARNING
            ]

            if not error_results and not warning_results:
                continue

            category_names = {
                "configuration": "설정 파일",
                "environment": "Kubernetes 환경",
                "dependencies": "의존성",
                "pre-deployment": "배포 전 검증",
                "general": "일반",
            }

            category_title = category_names.get(category, category)
            self.console.print(f"\n📁 {category_title}")

            # 오류 먼저 표시
            for result in error_results:
                self.console.print(f"  🔴 {result.message}")
                if result.details:
                    self.console.print(f"     {result.details}")
                if result.recommendation:
                    self.console.print(f"     💡 권장사항: {result.recommendation}")

            # 경고 표시
            for result in warning_results:
                self.console.print(f"  🟡 {result.message}")
                if result.details:
                    self.console.print(f"     {result.details}")
                if result.recommendation:
                    self.console.print(f"     💡 권장사항: {result.recommendation}")

    def _display_deployment_readiness(self, summary: dict[str, Any]):
        """배포 준비 상태 표시"""
        if summary["deployment_ready"]:
            self.console.print("\n✅ 배포 준비 완료")
        else:
            self.console.print("\n❌ 배포 준비 미완료 - 문제 해결 필요")

            critical_results = self.current_report.get_critical_results()
            if critical_results:
                self.console.print(f"   해결 필요한 문제: {len(critical_results)}개")

    def _display_validation_fix_suggestions(self):
        """검증 자동 수정 제안 표시"""
        fixable_results = self.current_report.get_fixable_results()

        self.console.print("\n🔧 자동 수정 가능한 문제:")
        for i, result in enumerate(fixable_results, 1):
            self.console.print(f"  {i}. {result.message}")
            if result.fix_description:
                self.console.print(f"     → {result.fix_description}")

        self.console.print(
            "\n💡 [bold]sbkube fix[/bold] 명령어로 자동 수정을 실행할 수 있습니다."
        )

    def save_report(self, file_path: str | Path, format: str = "json") -> bool:
        """보고서 저장"""
        if not self.current_report:
            logger.error("저장할 검증 보고서가 없습니다.")
            return False

        try:
            report_path = Path(file_path)
            report_path.parent.mkdir(parents=True, exist_ok=True)

            if format.lower() == "json":
                with open(report_path, "w", encoding="utf-8") as f:
                    json.dump(
                        self.current_report.to_dict(), f, indent=2, ensure_ascii=False
                    )
            else:
                logger.error(f"지원하지 않는 형식: {format}")
                return False

            logger.info(f"검증 보고서 저장됨: {report_path}")
            return True

        except Exception as e:
            logger.error(f"보고서 저장 실패: {e}")
            return False

    def get_validation_report(self) -> ValidationReport | None:
        """현재 검증 보고서 반환"""
        return self.current_report
