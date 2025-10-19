import asyncio
import sys

import click
from rich.console import Console

from sbkube.diagnostics.kubernetes_checks import (
    ConfigValidityCheck,
    HelmInstallationCheck,
    KubernetesConnectivityCheck,
    NetworkAccessCheck,
    PermissionsCheck,
    ResourceAvailabilityCheck,
)
from sbkube.fixes.namespace_fixes import (
    ConfigFileFix,
    HelmRepositoryFix,
    MissingNamespaceFix,
)
from sbkube.utils.auto_fix_system import AutoFixEngine, FixAttempt
from sbkube.utils.diagnostic_system import DiagnosticEngine
from sbkube.utils.logger import logger

console = Console()


@click.command(name="fix")
@click.option("--dry-run", is_flag=True, help="실제 적용하지 않고 수정 계획만 표시")
@click.option("--force", is_flag=True, help="대화형 확인 없이 자동 실행")
@click.option("--rollback", type=int, help="최근 N개 수정 롤백")
@click.option("--backup-cleanup", is_flag=True, help="오래된 백업 파일 정리")
@click.option("--history", is_flag=True, help="수정 히스토리 표시")
@click.option("--config-dir", default=".", help="설정 파일 디렉토리")
@click.pass_context
async def _cmd(ctx, dry_run, force, rollback, backup_cleanup, history, config_dir):
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
        sbkube fix --history          # 수정 히스토리 표시
    """

    try:
        # 자동 수정 엔진 초기화
        fix_engine = AutoFixEngine(console=console)

        # 자동 수정 등록
        fix_engine.register_fix(MissingNamespaceFix())
        fix_engine.register_fix(ConfigFileFix())
        fix_engine.register_fix(HelmRepositoryFix())

        # 히스토리 표시
        if history:
            _show_fix_history(fix_engine)
            return

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

        diagnostic_engine = DiagnosticEngine(console=console)
        diagnostic_engine.register_check(KubernetesConnectivityCheck())
        diagnostic_engine.register_check(HelmInstallationCheck())
        diagnostic_engine.register_check(ConfigValidityCheck(config_dir))
        diagnostic_engine.register_check(NetworkAccessCheck())
        diagnostic_engine.register_check(PermissionsCheck())
        diagnostic_engine.register_check(ResourceAvailabilityCheck())

        results = await asyncio.create_task(
            diagnostic_engine.run_all_checks(show_progress=False)
        )

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
            fixable_results, interactive=not force, force=force
        )

        # 결과 요약
        _show_fix_summary(attempts)

        # 실패한 수정이 있으면 종료 코드 1
        failed_attempts = [a for a in attempts if a.result.value != "success"]
        sys.exit(1 if failed_attempts else 0)

    except Exception as e:
        console.print(f"❌ 자동 수정 실행 실패: {e}")
        logger.error(f"자동 수정 실행 중 오류: {e}")
        sys.exit(1)


def _show_fix_plan(fix_engine: AutoFixEngine, results: list) -> None:
    """수정 계획 표시"""
    applicable_fixes = fix_engine.find_applicable_fixes(results)

    console.print("🔍 자동 수정 계획:")
    console.print("━" * 50)

    if not applicable_fixes:
        console.print("적용 가능한 자동 수정이 없습니다.")
        return

    for i, (fix, result) in enumerate(applicable_fixes, 1):
        risk_color = {"low": "green", "medium": "yellow", "high": "red"}.get(
            fix.risk_level, "white"
        )
        console.print(f"{i}. [{risk_color}]{fix.description}[/{risk_color}]")
        console.print(f"   문제: {result.message}")
        console.print(f"   위험도: {fix.risk_level}")
        if result.fix_command:
            console.print(f"   명령어: {result.fix_command}")
        console.print()

    console.print("💡 실제 수정을 실행하려면 --dry-run 옵션을 제거하세요.")


def _show_fix_summary(attempts: list[FixAttempt]) -> None:
    """수정 결과 요약"""
    from collections import Counter

    results = Counter(attempt.result.value for attempt in attempts)

    console.print("\n📊 수정 결과 요약:")
    console.print("━" * 30)

    if results.get("success", 0) > 0:
        console.print(f"✅ 성공: {results['success']}개")
    if results.get("failed", 0) > 0:
        console.print(f"❌ 실패: {results['failed']}개")
    if results.get("skipped", 0) > 0:
        console.print(f"⏭️  건너뜀: {results['skipped']}개")
    if results.get("backup_failed", 0) > 0:
        console.print(f"⚠️  백업 실패: {results['backup_failed']}개")

    # 실패한 수정들 상세 표시
    failed_attempts = [a for a in attempts if a.result.value == "failed"]
    if failed_attempts:
        console.print("\n❌ 실패한 수정:")
        for attempt in failed_attempts:
            console.print(f"  • {attempt.description}: {attempt.error_message}")

    # 롤백 가능한 수정들 표시
    successful_attempts = [a for a in attempts if a.result.value == "success"]
    if successful_attempts:
        console.print(
            f"\n💡 문제가 지속되면 [bold]sbkube fix --rollback {len(successful_attempts)}[/bold]로 롤백할 수 있습니다."
        )


def _show_fix_history(fix_engine: AutoFixEngine) -> None:
    """수정 히스토리 표시"""
    from rich.table import Table
    from rich.text import Text

    history_summary = fix_engine.get_history_summary()

    if not history_summary:
        console.print("📋 수정 히스토리가 없습니다.")
        return

    console.print("📋 자동 수정 히스토리")
    console.print("━" * 50)

    # 전체 통계
    console.print(f"총 수정 시도: {history_summary['total_attempts']}개")
    console.print(f"✅ 성공: {history_summary['success_count']}개")
    console.print(f"❌ 실패: {history_summary['failed_count']}개")
    console.print(f"⏭️  건너뜀: {history_summary['skipped_count']}개")
    console.print(f"⚠️  백업 실패: {history_summary['backup_failed_count']}개")

    # 최근 수정 내역
    recent_attempts = history_summary.get("recent_attempts", [])
    if recent_attempts:
        console.print("\n🕐 최근 수정 내역:")

        table = Table(show_header=True, header_style="bold magenta")
        table.add_column("설명", style="white")
        table.add_column("결과", style="white")
        table.add_column("시간", style="cyan")

        for attempt in recent_attempts:
            result_text = Text(attempt["result"])
            if attempt["result"] == "success":
                result_text.stylize("green")
            elif attempt["result"] == "failed":
                result_text.stylize("red")
            elif attempt["result"] == "skipped":
                result_text.stylize("yellow")

            timestamp = attempt["timestamp"][:19].replace("T", " ")
            table.add_row(attempt["description"], result_text, timestamp)

        console.print(table)

    # 롤백 가능한 수정들
    rollback_candidates = fix_engine.get_rollback_candidates()
    if rollback_candidates:
        console.print(f"\n🔄 롤백 가능한 수정 ({len(rollback_candidates)}개):")
        for i, attempt in enumerate(rollback_candidates, 1):
            console.print(
                f"  {i}. {attempt.description} ({attempt.timestamp.strftime('%Y-%m-%d %H:%M:%S')})"
            )

        console.print(
            "\n💡 [bold]sbkube fix --rollback N[/bold] 명령어로 최근 N개 수정을 롤백할 수 있습니다."
        )


async def run_fix_command(
    ctx, dry_run, force, rollback, backup_cleanup, history, config_dir
):
    """비동기 실행을 위한 래퍼 함수"""
    return await _cmd(
        ctx, dry_run, force, rollback, backup_cleanup, history, config_dir
    )


# 비동기 실행을 위한 명령어 래퍼
@click.command(name="fix")
@click.option("--dry-run", is_flag=True, help="실제 적용하지 않고 수정 계획만 표시")
@click.option("--force", is_flag=True, help="대화형 확인 없이 자동 실행")
@click.option("--rollback", type=int, help="최근 N개 수정 롤백")
@click.option("--backup-cleanup", is_flag=True, help="오래된 백업 파일 정리")
@click.option("--history", is_flag=True, help="수정 히스토리 표시")
@click.option("--config-dir", default=".", help="설정 파일 디렉토리")
@click.pass_context
def cmd_wrapper(ctx, dry_run, force, rollback, backup_cleanup, history, config_dir):
    """자동 수정 시스템 래퍼"""
    return asyncio.run(
        _cmd(ctx, dry_run, force, rollback, backup_cleanup, history, config_dir)
    )


# 실제 export될 명령어는 wrapper
cmd = cmd_wrapper
