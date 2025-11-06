"""Enhanced error formatting for SBKube.

에러를 사용자 친화적인 형태로 포맷팅하여 출력합니다.
"""

from rich.console import Console
from rich.panel import Panel
from rich.text import Text

from sbkube.utils.error_classifier import ErrorClassifier
from sbkube.utils.error_suggestions import get_error_suggestions


def format_deployment_error(
    error: Exception,
    app_name: str,
    step: str,
    step_number: int,
    total_steps: int,
    console: Console | None = None,
) -> None:
    """배포 에러를 포맷팅하여 출력합니다.

    Args:
        error: 발생한 예외
        app_name: 애플리케이션 이름
        step: 실패한 단계 (prepare, build, deploy)
        step_number: 단계 번호 (1, 2, 3)
        total_steps: 전체 단계 수
        console: Rich Console 인스턴스 (None이면 새로 생성)

    """
    if console is None:
        console = Console()

    error_message = str(error)

    # 에러 분류
    classification = ErrorClassifier.classify(error_message, context=step)

    # 단계 아이콘 매핑
    step_icons = {
        "prepare": "📦",
        "build": "🔨",
        "deploy": "🚀",
        "load_config": "📄",
    }
    step_icon = step_icons.get(step, "⚙️")

    # 심각도 색상 매핑
    severity_colors = {
        "critical": "bold red",
        "high": "red",
        "medium": "yellow",
        "low": "cyan",
        "unknown": "white",
    }
    severity_color = severity_colors.get(classification["severity"], "red")

    # 기본 에러 메시지
    console.print()
    console.print(f"[{severity_color}]❌ 배포 실패: {app_name}[/{severity_color}]")
    console.print(
        f"[dim]({step_number}/{total_steps} 단계에서 실패)[/dim]", style="dim"
    )
    console.print()

    # 실패 단계 표시
    console.print(f"[bold cyan]📍 실패 단계:[/bold cyan] {step_icon} {step.title()}")

    # 에러 타입 표시
    if classification["is_classified"]:
        console.print(
            f"[bold cyan]🔍 에러 타입:[/bold cyan] {classification['category']}"
        )
    else:
        console.print("[bold cyan]🔍 에러 타입:[/bold cyan] 알 수 없음 (일반 에러)")

    # 상세 에러 내용 (축약)
    truncated_error = (
        error_message
        if len(error_message) < 200
        else error_message[:200] + "... (생략)"
    )
    console.print(f"[bold cyan]💬 상세 내용:[/bold cyan] {truncated_error}")

    # 데이터베이스 에러일 경우 추가 정보
    if "Database" in classification["category"]:
        db_details = ErrorClassifier.extract_db_details(error_message)
        if any(db_details.values()):
            console.print()
            console.print("[bold cyan]🗄️  데이터베이스 정보:[/bold cyan]")
            if db_details["db_type"]:
                console.print(f"  • DB 종류: {db_details['db_type']}")
            if db_details["user"]:
                console.print(f"  • 사용자: {db_details['user']}")
            if db_details["host"]:
                console.print(f"  • 호스트: {db_details['host']}")
            if db_details["port"]:
                console.print(f"  • 포트: {db_details['port']}")

    # Helm 에러일 경우 추가 정보
    if "Helm" in classification["category"]:
        helm_details = ErrorClassifier.extract_helm_details(error_message)
        if any(helm_details.values()):
            console.print()
            console.print("[bold cyan]⎈ Helm 정보:[/bold cyan]")
            if helm_details["release_name"]:
                console.print(f"  • Release: {helm_details['release_name']}")
            if helm_details["namespace"]:
                console.print(f"  • Namespace: {helm_details['namespace']}")
            if helm_details["chart"]:
                console.print(f"  • Chart: {helm_details['chart']}")

    # ERROR_GUIDE에서 해결 방법 가져오기
    guide = get_error_suggestions(classification["category"])

    if guide:
        console.print()
        console.print(f"[bold yellow]💡 {guide['title']}[/bold yellow]")
        console.print()
        console.print("[bold]📋 해결 방법:[/bold]")
        for suggestion in guide["suggestions"]:
            console.print(f"  • {suggestion}")

        if guide["commands"]:
            console.print()
            console.print("[bold]🔧 유용한 명령어:[/bold]")
            for cmd, desc in guide["commands"].items():
                console.print(f"  • [cyan]sbkube {cmd}[/cyan]: {desc}")

        if guide["quick_fix"]:
            console.print()
            console.print(
                f"[bold green]⚡ 빠른 해결:[/bold green] [cyan]{guide['quick_fix']}[/cyan]"
            )

        if guide["doc_link"]:
            console.print()
            console.print(f"[dim]📚 자세한 내용: {guide['doc_link']}[/dim]")
    else:
        # 가이드가 없는 경우 기본 제안
        console.print()
        console.print("[bold yellow]💡 일반적인 해결 방법:[/bold yellow]")
        console.print("  • 전체 에러 로그 확인")
        console.print("  • [cyan]sbkube doctor[/cyan]: 시스템 진단")
        console.print(
            "  • [cyan]kubectl get pods,svc -n <namespace>[/cyan]: 리소스 확인"
        )

    console.print()


def format_simple_error(
    error: Exception,
    context: str | None = None,
    console: Console | None = None,
) -> None:
    """간단한 에러 메시지 출력 (배포 외 일반 에러).

    Args:
        error: 발생한 예외
        context: 에러 발생 컨텍스트 (옵션)
        console: Rich Console 인스턴스

    """
    if console is None:
        console = Console()

    error_message = str(error)
    classification = ErrorClassifier.classify(error_message, context=context)

    severity_color = "red" if classification["severity"] == "high" else "yellow"

    console.print()
    console.print(f"[{severity_color}]❌ 에러 발생[/{severity_color}]")
    if context:
        console.print(f"[dim]컨텍스트: {context}[/dim]")

    console.print(f"[bold]메시지:[/bold] {error_message}")

    # ERROR_GUIDE 조회
    guide = get_error_suggestions(classification["category"])
    if guide and guide.get("quick_fix"):
        console.print()
        console.print(
            f"[bold green]⚡ 빠른 해결:[/bold green] [cyan]{guide['quick_fix']}[/cyan]"
        )

    console.print()


def create_error_panel(
    title: str,
    message: str,
    suggestions: list[str] | None = None,
    severity: str = "error",
) -> Panel:
    """에러 정보를 담은 Rich Panel을 생성합니다.

    Args:
        title: 패널 제목
        message: 에러 메시지
        suggestions: 해결 방법 목록 (옵션)
        severity: 심각도 (error, warning, info)

    Returns:
        Rich Panel 객체

    """
    border_styles = {
        "error": "red",
        "warning": "yellow",
        "info": "cyan",
    }
    border_style = border_styles.get(severity, "red")

    content = Text()
    content.append(f"{message}\n\n", style="white")

    if suggestions:
        content.append("💡 해결 방법:\n", style="bold yellow")
        for suggestion in suggestions:
            content.append(f"  • {suggestion}\n", style="white")

    return Panel(
        content,
        title=f"[bold]{title}[/bold]",
        border_style=border_style,
        expand=False,
    )
