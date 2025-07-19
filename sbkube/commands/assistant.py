import sys
from typing import Any

import click
from rich.console import Console

from sbkube.utils.context_aware_suggestions import ContextAwareSuggestions
from sbkube.utils.interactive_assistant import InteractiveSession
from sbkube.utils.logger import logger

console = Console()


@click.command(name="assistant")
@click.option(
    "--context", help="문제 컨텍스트 (예: 'network', 'config', 'permissions')"
)
@click.option("--error", help="발생한 오류 메시지")
@click.option("--quick", is_flag=True, help="빠른 제안만 표시 (대화형 없음)")
def cmd(context, error, quick):
    """대화형 문제 해결 도우미

    SBKube 사용 중 발생한 문제를 대화형으로 진단하고 해결 방안을 제시합니다.

    \\b
    사용 예시:
        sbkube assistant                           # 대화형 문제 해결
        sbkube assistant --context network         # 네트워크 문제로 시작
        sbkube assistant --error "connection refused"  # 특정 오류 분석
        sbkube assistant --quick                   # 빠른 제안만 표시
    """

    try:
        # 초기 컨텍스트 구성
        initial_context = {}

        if context:
            initial_context["problem_category"] = context

        if error:
            initial_context["error_message"] = error

        # 빠른 제안 모드
        if quick:
            _show_quick_suggestions(initial_context)
            return

        # 대화형 세션 시작
        session = InteractiveSession(console)
        solution = session.start_session(initial_context)

        # 세션 결과 저장 (선택적)
        _save_session_result(solution)

    except KeyboardInterrupt:
        console.print(
            "\n\n👋 언제든 다시 도움이 필요하면 sbkube assistant를 실행하세요!"
        )
        sys.exit(0)
    except Exception as e:
        logger.error(f"❌ 지원 시스템 오류: {e}")
        sys.exit(1)


def _show_quick_suggestions(context: dict[str, Any]):
    """빠른 제안 표시"""
    suggestions_system = ContextAwareSuggestions()
    suggestions = suggestions_system.get_suggestions(context)

    if not suggestions:
        console.print("💡 현재 컨텍스트에 대한 특별한 제안이 없습니다.")
        console.print(
            "더 구체적인 도움을 받으려면 대화형 모드를 사용하세요: sbkube assistant"
        )
        return

    console.print("💡 빠른 제안:")
    console.print("=" * 40)

    for i, suggestion in enumerate(suggestions[:5], 1):  # 상위 5개만 표시
        priority_icon = {"high": "🔴", "medium": "🟡", "low": "🟢"}.get(
            suggestion.get("priority", "low"), "🔵"
        )

        console.print(f"\n{priority_icon} {i}. {suggestion['title']}")
        console.print(f"   {suggestion['description']}")

        if suggestion.get("commands"):
            console.print("   권장 명령어:")
            for cmd in suggestion["commands"]:
                console.print(f"     $ {cmd}")


def _save_session_result(solution: dict[str, Any]):
    """세션 결과 저장"""
    try:
        import json
        from datetime import datetime
        from pathlib import Path

        # 세션 히스토리 디렉토리
        history_dir = Path(".sbkube") / "assistant_history"
        history_dir.mkdir(parents=True, exist_ok=True)

        # 세션 파일 저장
        session_id = solution.get("session_id", "unknown")
        session_file = history_dir / f"session_{session_id}.json"

        session_data = {
            "timestamp": datetime.now().isoformat(),
            "session_id": session_id,
            "solution": solution,
        }

        with open(session_file, "w", encoding="utf-8") as f:
            json.dump(session_data, f, indent=2, ensure_ascii=False)

        # 최근 세션 링크 업데이트
        latest_file = history_dir / "latest_session.json"
        with open(latest_file, "w", encoding="utf-8") as f:
            json.dump(session_data, f, indent=2, ensure_ascii=False)

    except Exception as e:
        # 저장 실패는 치명적이지 않음
        logger.warning(f"세션 결과 저장 실패: {e}")


@click.command(name="assistant-history")
@click.option("--limit", default=10, help="표시할 세션 수")
def history_cmd(limit):
    """지원 세션 히스토리 조회"""
    try:
        import json
        from pathlib import Path

        history_dir = Path(".sbkube") / "assistant_history"

        if not history_dir.exists():
            console.print("📋 저장된 지원 세션이 없습니다.")
            return

        # 세션 파일들 로드
        session_files = sorted(
            history_dir.glob("session_*.json"),
            key=lambda x: x.stat().st_mtime,
            reverse=True,
        )[:limit]

        if not session_files:
            console.print("📋 저장된 지원 세션이 없습니다.")
            return

        console.print(f"📋 최근 {len(session_files)}개 지원 세션:")
        console.print("=" * 50)

        for session_file in session_files:
            with open(session_file, encoding="utf-8") as f:
                session_data = json.load(f)

            session_id = session_data.get("session_id", "unknown")
            timestamp = session_data.get("timestamp", "unknown")
            solution = session_data.get("solution", {})

            console.print(f"\n🔍 세션 {session_id} ({timestamp[:19]})")

            if solution.get("recommendations"):
                console.print(f"   권장사항: {len(solution['recommendations'])}개")
            if solution.get("commands"):
                console.print(f"   명령어: {len(solution['commands'])}개")

    except Exception as e:
        logger.error(f"❌ 히스토리 조회 실패: {e}")
        sys.exit(1)
