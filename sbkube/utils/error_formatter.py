"""Enhanced error formatting for SBKube.

에러를 사용자 친화적인 형태로 포맷팅하여 출력합니다.
기본: 간결한 출력 / verbose: 상세 출력
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
    verbose: bool = False,
) -> None:
    """배포 에러를 포맷팅하여 출력합니다.

    Args:
        error: 발생한 예외
        app_name: 애플리케이션 이름
        step: 실패한 단계 (prepare, build, deploy)
        step_number: 단계 번호 (1, 2, 3)
        total_steps: 전체 단계 수
        console: Rich Console 인스턴스 (None이면 새로 생성)
        verbose: 상세 출력 여부 (기본 False)

    """
    if console is None:
        console = Console()

    error_message = str(error)
    classification = ErrorClassifier.classify(error_message, context=step)
    guide = get_error_suggestions(classification["category"])

    # 심각도 색상
    severity_colors = {
        "critical": "bold red",
        "high": "red",
        "medium": "yellow",
        "low": "cyan",
        "unknown": "white",
    }
    severity_color = severity_colors.get(classification["severity"], "red")

    # ============================================================
    # 기본 출력 (항상 표시) - 3줄로 핵심만
    # ============================================================
    console.print()

    # 1줄: 앱 이름 + 에러 타입
    error_type = classification["category"] if classification["is_classified"] else "UnknownError"
    console.print(f"[{severity_color}]❌ {app_name}[/{severity_color}] [{step}] {error_type}")

    # 2줄: 핵심 원인 (guide title 또는 에러 메시지 첫 80자)
    if guide:
        console.print(f"   [yellow]→ {guide['title']}[/yellow]")
    else:
        short_msg = error_message[:80] + "..." if len(error_message) > 80 else error_message
        console.print(f"   [dim]→ {short_msg}[/dim]")

    # 3줄: 빠른 해결 명령어
    if guide and guide.get("quick_fix"):
        console.print(f"   [green]⚡ {guide['quick_fix']}[/green]")

    # verbose 힌트
    if not verbose:
        console.print("   [dim](상세: --verbose 또는 -v)[/dim]")
        console.print()
        return

    # ============================================================
    # Verbose 출력 (--verbose 옵션)
    # ============================================================
    console.print()
    console.print("[dim]─" * 50 + "[/dim]")

    # 상세 에러 내용
    truncated_error = (
        error_message if len(error_message) < 300 else error_message[:300] + "..."
    )
    console.print(f"[bold]상세:[/bold] {truncated_error}")
    console.print()

    # 타입별 추가 정보 추출 및 표시
    _print_extracted_details(console, classification, error_message)

    # 해결 방법 가이드
    if guide:
        console.print("[bold]📋 해결 방법:[/bold]")
        for suggestion in guide["suggestions"]:
            console.print(f"  • {suggestion}")

        if guide["commands"]:
            console.print()
            console.print("[bold]🔧 명령어:[/bold]")
            for cmd, desc in guide["commands"].items():
                console.print(f"  • [cyan]sbkube {cmd}[/cyan]: {desc}")

        if guide.get("doc_link"):
            console.print(f"\n[dim]📚 {guide['doc_link']}[/dim]")

        # 예제 코드 (verbose에서만)
        if guide.get("example_fix"):
            console.print()
            console.print("[bold magenta]📝 예시:[/bold magenta]")
            for line in guide["example_fix"].strip().split("\n"):
                if line.strip().startswith("#"):
                    console.print(f"[dim]{line}[/dim]")
                else:
                    console.print(f"[cyan]{line}[/cyan]")
    else:
        console.print("[bold]📋 일반 해결:[/bold]")
        console.print("  • sbkube doctor")
        console.print("  • kubectl get pods,events -n <namespace>")

    console.print()


def _print_extracted_details(
    console: Console,
    classification: dict,
    error_message: str,
) -> None:
    """에러 타입별 추출된 상세 정보를 출력합니다."""

    category = classification["category"]

    # Database 에러
    if "Database" in category:
        details = ErrorClassifier.extract_db_details(error_message)
        if any(details.values()):
            info_parts = []
            if details["db_type"]:
                info_parts.append(f"DB={details['db_type']}")
            if details["user"]:
                info_parts.append(f"user={details['user']}")
            if details["host"]:
                info_parts.append(f"host={details['host']}")
            if details["port"]:
                info_parts.append(f"port={details['port']}")
            console.print(f"[cyan]🗄️  {' | '.join(info_parts)}[/cyan]")
            console.print()

    # Helm 에러
    if "Helm" in category:
        details = ErrorClassifier.extract_helm_details(error_message)
        if any(details.values()):
            info_parts = []
            if details["release_name"]:
                info_parts.append(f"release={details['release_name']}")
            if details["namespace"]:
                info_parts.append(f"ns={details['namespace']}")
            if details["chart"]:
                info_parts.append(f"chart={details['chart']}")
            console.print(f"[cyan]⎈ {' | '.join(info_parts)}[/cyan]")
            console.print()

    # StorageClass 에러
    if "Storage" in category:
        details = ErrorClassifier.extract_storage_details(error_message)
        if any(details.values()):
            info_parts = []
            if details["storageclass"]:
                info_parts.append(f"[red]sc={details['storageclass']}[/red]")
            if details["pvc_name"]:
                info_parts.append(f"pvc={details['pvc_name']}")
            if details["namespace"]:
                info_parts.append(f"ns={details['namespace']}")
            console.print(f"[cyan]💾 {' | '.join(info_parts)}[/cyan]")
            console.print("[yellow]   💡 K3s: 'local-path' 사용 (standard 아님)[/yellow]")
            console.print()

    # Webhook 에러
    if "Webhook" in category:
        details = ErrorClassifier.extract_webhook_details(error_message)
        if any(details.values()):
            info_parts = []
            if details["webhook_type"]:
                info_parts.append(f"type={details['webhook_type']}")
            if details["webhook_name"]:
                info_parts.append(f"name={details['webhook_name']}")
            if details["conflicting_manager"]:
                info_parts.append(f"conflict={details['conflicting_manager']}")
            console.print(f"[cyan]🔗 {' | '.join(info_parts)}[/cyan]")
            console.print()


def format_simple_error(
    error: Exception,
    context: str | None = None,
    console: Console | None = None,
    verbose: bool = False,
) -> None:
    """간단한 에러 메시지 출력 (배포 외 일반 에러).

    Args:
        error: 발생한 예외
        context: 에러 발생 컨텍스트 (옵션)
        console: Rich Console 인스턴스
        verbose: 상세 출력 여부

    """
    if console is None:
        console = Console()

    error_message = str(error)
    classification = ErrorClassifier.classify(error_message, context=context)
    guide = get_error_suggestions(classification["category"])

    severity_color = "red" if classification["severity"] == "high" else "yellow"

    # 기본 출력
    console.print()
    error_type = classification["category"] if classification["is_classified"] else "Error"
    console.print(f"[{severity_color}]❌ {error_type}[/{severity_color}]")

    if guide and guide.get("quick_fix"):
        console.print(f"   [green]⚡ {guide['quick_fix']}[/green]")

    if not verbose:
        short_msg = error_message[:80] + "..." if len(error_message) > 80 else error_message
        console.print(f"   [dim]{short_msg}[/dim]")
        console.print()
        return

    # Verbose
    console.print(f"\n[bold]메시지:[/bold] {error_message}")
    if guide:
        console.print(f"\n[yellow]💡 {guide['title']}[/yellow]")
        for suggestion in guide["suggestions"][:3]:  # 상위 3개만
            console.print(f"  • {suggestion}")
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
