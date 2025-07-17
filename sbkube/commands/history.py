import sys
from datetime import datetime
from typing import Any

import click
from rich.console import Console
from rich.panel import Panel
from rich.table import Table

from sbkube.utils.execution_tracker import ExecutionTracker
from sbkube.utils.logger import logger

console = Console()


@click.command(name="history")
@click.option("--limit", default=10, help="표시할 히스토리 개수 (기본값: 10)")
@click.option("--detailed", is_flag=True, help="상세 정보 표시")
@click.option("--failures", is_flag=True, help="실패한 실행만 표시")
@click.option("--profile", help="특정 프로파일의 히스토리만 표시")
@click.option("--clean", is_flag=True, help="오래된 히스토리 정리")
@click.option("--stats", is_flag=True, help="통계 정보 표시")
@click.pass_context
def cmd(ctx, limit, detailed, failures, profile, clean, stats):
    """실행 히스토리 조회 및 관리

    최근 실행 기록을 조회하고 성공/실패 통계를 확인할 수 있습니다.

    \b
    사용 예시:
        sbkube history                    # 최근 10개 실행 기록
        sbkube history --detailed         # 상세 정보 포함
        sbkube history --failures         # 실패한 실행만 표시
        sbkube history --stats            # 통계 정보 표시
        sbkube history --clean            # 오래된 기록 정리
    """

    try:
        tracker = ExecutionTracker(".", profile)

        if clean:
            _clean_old_history(tracker)
            return

        if stats:
            _show_statistics(tracker)
            return

        history = tracker.load_execution_history(limit)

        if failures:
            history = [h for h in history if h["status"] == "failed"]

        if profile:
            history = [h for h in history if h.get("profile") == profile]

        if not history:
            console.print("📋 히스토리가 없습니다.")
            return

        if detailed:
            _show_detailed_history(history)
        else:
            _show_simple_history(history)

    except Exception as e:
        logger.error(f"❌ 히스토리 조회 실패: {e}")
        sys.exit(1)


@click.command(name="diagnose")
@click.option("--recommendations", is_flag=True, help="개선 권장사항 표시")
@click.pass_context
def diagnose_cmd(ctx, recommendations):
    """실행 패턴 분석 및 진단

    최근 실행 기록을 분석하여 문제 패턴을 찾고 개선 방안을 제시합니다.
    """
    try:
        tracker = ExecutionTracker(".")
        history = tracker.load_execution_history(50)

        if not history:
            console.print("📋 분석할 히스토리가 없습니다.")
            return

        from sbkube.utils.pattern_analyzer import ExecutionPatternAnalyzer

        analyzer = ExecutionPatternAnalyzer(history)

        # 실패 패턴 분석
        failure_analysis = analyzer.analyze_failure_patterns()
        console.print("🔍 실패 패턴 분석")
        console.print(f"총 실패 횟수: {failure_analysis['total_failures']}")
        console.print(f"실패율: {failure_analysis['failure_rate']:.1f}%")

        if failure_analysis["patterns"]:
            console.print("\n발견된 패턴:")
            for pattern in failure_analysis["patterns"]:
                console.print(f"  • {pattern['description']}")

        # 성능 트렌드 분석
        performance_analysis = analyzer.analyze_performance_trends()
        perf_trend = performance_analysis.get("trend", {})

        if perf_trend:
            console.print("\n⚡ 성능 트렌드")
            console.print(f"상태: {perf_trend.get('performance', 'unknown')}")
            if "change" in perf_trend:
                console.print(f"변화: {perf_trend['change']}")

        # 권장사항
        if recommendations:
            recs = analyzer.generate_recommendations()
            if recs:
                console.print("\n💡 개선 권장사항")
                for rec in recs:
                    priority_color = {
                        "high": "red",
                        "medium": "yellow",
                        "low": "green",
                    }.get(rec["priority"], "white")
                    console.print(
                        f"[{priority_color}]• {rec['title']}[/{priority_color}]"
                    )
                    console.print(f"  {rec['description']}")
                    console.print(f"  권장 조치: {rec['action']}")
                    console.print()

    except Exception as e:
        logger.error(f"❌ 진단 실패: {e}")
        sys.exit(1)


def _show_simple_history(history: list[dict[str, Any]]):
    """간단한 히스토리 표시"""
    table = Table(title="📋 최근 실행 히스토리")
    table.add_column("Run ID", style="cyan", width=10)
    table.add_column("프로파일", style="blue")
    table.add_column("상태", justify="center")
    table.add_column("시작 시간", style="dim")
    table.add_column("소요 시간", justify="right")

    for record in history:
        # 상태 아이콘
        status_icon = {"completed": "✅", "failed": "❌", "in_progress": "🔄"}.get(
            record["status"], "❓"
        )

        # 소요 시간 계산
        duration = ""
        if record.get("completed_at"):
            start = datetime.fromisoformat(record["started_at"])
            end = datetime.fromisoformat(record["completed_at"])
            duration = _format_duration((end - start).total_seconds())
        elif record["status"] == "in_progress":
            start = datetime.fromisoformat(record["started_at"])
            duration = (
                _format_duration((datetime.now() - start).total_seconds()) + " (진행중)"
            )

        # 시작 시간 포맷
        start_time = datetime.fromisoformat(record["started_at"])
        formatted_time = start_time.strftime("%m/%d %H:%M")

        table.add_row(
            record["run_id"][:8],
            record.get("profile", "default"),
            f"{status_icon} {record['status']}",
            formatted_time,
            duration,
        )

    console.print(table)


def _show_detailed_history(history: list[dict[str, Any]]):
    """상세한 히스토리 표시"""
    for i, record in enumerate(history):
        if i > 0:
            console.print()

        # 상태별 색상
        status_color = {
            "completed": "green",
            "failed": "red",
            "in_progress": "yellow",
        }.get(record["status"], "white")

        # 기본 정보
        panel_content = f"[bold]Run ID:[/bold] {record['run_id']}\n"
        panel_content += f"[bold]프로파일:[/bold] {record.get('profile', 'default')}\n"
        panel_content += (
            f"[bold]상태:[/bold] [{status_color}]{record['status']}[/{status_color}]\n"
        )
        panel_content += (
            f"[bold]시작 시간:[/bold] {_format_datetime(record['started_at'])}\n"
        )

        if record.get("completed_at"):
            panel_content += (
                f"[bold]완료 시간:[/bold] {_format_datetime(record['completed_at'])}\n"
            )
            start = datetime.fromisoformat(record["started_at"])
            end = datetime.fromisoformat(record["completed_at"])
            duration = _format_duration((end - start).total_seconds())
            panel_content += f"[bold]소요 시간:[/bold] {duration}\n"

        # 단계별 정보 로드
        step_info = _load_step_details(record["file"])
        if step_info:
            panel_content += "\n[bold]단계별 상태:[/bold]\n"
            for step_name, step_data in step_info.items():
                step_status = step_data.get("status", "pending")
                step_icon = {
                    "completed": "✅",
                    "failed": "❌",
                    "in_progress": "🔄",
                    "pending": "⏳",
                    "skipped": "⏭️",
                }.get(step_status, "❓")

                panel_content += f"  {step_icon} {step_name}"

                if step_data.get("duration"):
                    duration = _format_duration(step_data["duration"])
                    panel_content += f" ({duration})"

                if step_data.get("error"):
                    panel_content += f"\n    [red]오류: {step_data['error']}[/red]"

                panel_content += "\n"

        console.print(
            Panel(panel_content.rstrip(), title=f"🔍 실행 기록 #{i + 1}", expand=False)
        )


def _show_statistics(tracker: ExecutionTracker):
    """통계 정보 표시"""
    history = tracker.load_execution_history(100)  # 최근 100개 기록

    if not history:
        console.print("📊 통계를 계산할 히스토리가 없습니다.")
        return

    # 기본 통계
    total_runs = len(history)
    successful_runs = len([h for h in history if h["status"] == "completed"])
    failed_runs = len([h for h in history if h["status"] == "failed"])
    success_rate = (successful_runs / total_runs * 100) if total_runs > 0 else 0

    # 프로파일별 통계
    profile_stats = {}
    for record in history:
        profile = record.get("profile", "default")
        if profile not in profile_stats:
            profile_stats[profile] = {"total": 0, "success": 0, "failed": 0}

        profile_stats[profile]["total"] += 1
        if record["status"] == "completed":
            profile_stats[profile]["success"] += 1
        elif record["status"] == "failed":
            profile_stats[profile]["failed"] += 1

    # 시간대별 분석
    time_analysis = _analyze_execution_times(history)

    # 통계 표시
    console.print("📊 실행 통계 (최근 100회)")
    console.print()

    # 전체 통계
    stats_table = Table(title="전체 실행 통계")
    stats_table.add_column("항목", style="bold")
    stats_table.add_column("값", justify="right")

    stats_table.add_row("총 실행 횟수", str(total_runs))
    stats_table.add_row("성공", f"[green]{successful_runs}[/green]")
    stats_table.add_row("실패", f"[red]{failed_runs}[/red]")
    stats_table.add_row("성공률", f"[bold]{success_rate:.1f}%[/bold]")

    console.print(stats_table)
    console.print()

    # 프로파일별 통계
    if len(profile_stats) > 1:
        profile_table = Table(title="프로파일별 통계")
        profile_table.add_column("프로파일", style="cyan")
        profile_table.add_column("총 실행", justify="center")
        profile_table.add_column("성공", justify="center")
        profile_table.add_column("실패", justify="center")
        profile_table.add_column("성공률", justify="right")

        for profile, stats in profile_stats.items():
            rate = (
                (stats["success"] / stats["total"] * 100) if stats["total"] > 0 else 0
            )
            profile_table.add_row(
                profile,
                str(stats["total"]),
                f"[green]{stats['success']}[/green]",
                f"[red]{stats['failed']}[/red]",
                f"{rate:.1f}%",
            )

        console.print(profile_table)
        console.print()

    # 시간 분석
    if time_analysis:
        console.print("⏱️  실행 시간 분석")
        console.print(f"평균 실행 시간: {time_analysis['avg_duration']}")
        console.print(f"최단 실행 시간: {time_analysis['min_duration']}")
        console.print(f"최장 실행 시간: {time_analysis['max_duration']}")


def _analyze_execution_times(history: list[dict[str, Any]]) -> dict[str, str]:
    """실행 시간 분석"""
    durations = []

    for record in history:
        if record.get("completed_at") and record["status"] == "completed":
            start = datetime.fromisoformat(record["started_at"])
            end = datetime.fromisoformat(record["completed_at"])
            duration = (end - start).total_seconds()
            durations.append(duration)

    if not durations:
        return {}

    return {
        "avg_duration": _format_duration(sum(durations) / len(durations)),
        "min_duration": _format_duration(min(durations)),
        "max_duration": _format_duration(max(durations)),
    }


def _clean_old_history(tracker: ExecutionTracker):
    """오래된 히스토리 정리"""
    console.print("🧹 오래된 히스토리를 정리하고 있습니다...")

    # 30일 이상 된 기록 정리
    tracker.cleanup_old_states(keep_days=30)

    console.print("✅ 히스토리 정리가 완료되었습니다.")


def _load_step_details(file_path: str) -> dict[str, Any]:
    """상태 파일에서 단계별 상세 정보 로드"""
    try:
        import json

        with open(file_path, encoding="utf-8") as f:
            data = json.load(f)
        return data.get("steps", {})
    except Exception:
        return {}


def _format_datetime(iso_string: str) -> str:
    """날짜시간 포맷팅"""
    dt = datetime.fromisoformat(iso_string)
    return dt.strftime("%Y-%m-%d %H:%M:%S")


def _format_duration(seconds: float) -> str:
    """소요 시간 포맷팅"""
    if seconds < 60:
        return f"{seconds:.1f}초"
    elif seconds < 3600:
        return f"{seconds / 60:.1f}분"
    else:
        return f"{seconds / 3600:.1f}시간"
