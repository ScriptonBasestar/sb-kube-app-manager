"""로깅 유틸리티 모듈.

sbkube 전체에서 사용할 수 있는 통합 로깅 시스템
verbose, debug, info, warning, error 레벨 지원
"""

from enum import IntEnum

import click
from rich.console import Console


class LogLevel(IntEnum):
    """로그 레벨 정의."""

    DEBUG = 10
    VERBOSE = 15  # DEBUG와 INFO 사이
    INFO = 20
    WARNING = 30
    ERROR = 40


class SbkubeLogger:
    """sbkube 통합 로거 클래스."""

    def __init__(self, console: Console | None = None) -> None:
        self.console = console or Console()
        self._level = LogLevel.INFO

    def set_level(self, level: LogLevel) -> None:
        """로그 레벨 설정."""
        self._level = level

    def debug(self, message: str, **kwargs) -> None:
        """디버그 메시지 출력."""
        if self._level <= LogLevel.DEBUG:
            self.console.print(f"[dim]🐛 DEBUG: {message}[/dim]", **kwargs)

    def verbose(self, message: str, **kwargs) -> None:
        """상세 메시지 출력 (디버그보다는 덜 상세)."""
        if self._level <= LogLevel.VERBOSE:
            self.console.print(f"[cyan]📝 {message}[/cyan]", **kwargs)

    def info(self, message: str, **kwargs) -> None:
        """정보 메시지 출력."""
        if self._level <= LogLevel.INFO:
            self.console.print(f"[green]ℹ️  {message}[/green]", **kwargs)

    def warning(self, message: str, **kwargs) -> None:
        """경고 메시지 출력."""
        if self._level <= LogLevel.WARNING:
            self.console.print(f"[yellow]⚠️  {message}[/yellow]", **kwargs)

    def error(self, message: str, **kwargs) -> None:
        """에러 메시지 출력."""
        if self._level <= LogLevel.ERROR:
            self.console.print(f"[red]❌ {message}[/red]", **kwargs)

    def success(self, message: str, **kwargs) -> None:
        """성공 메시지 출력 (항상 표시)."""
        self.console.print(f"[bold green]✅ {message}[/bold green]", **kwargs)

    def progress(self, message: str, **kwargs) -> None:
        """진행 상황 메시지 출력 (항상 표시)."""
        self.console.print(f"[magenta]➡️  {message}[/magenta]", **kwargs)

    def command(self, command: str, **kwargs) -> None:
        """실행 명령어 출력."""
        if self._level <= LogLevel.VERBOSE:
            self.console.print(f"[cyan]$ {command}[/cyan]", **kwargs)

    def heading(self, message: str, **kwargs) -> None:
        """헤딩 메시지 출력 (항상 표시)."""
        self.console.print(f"[bold blue]✨ {message} ✨[/bold blue]", **kwargs)


# 전역 로거 인스턴스
logger = SbkubeLogger()


def get_logger() -> SbkubeLogger:
    """전역 로거 인스턴스 반환."""
    return logger


def setup_logging_from_context(ctx: click.Context) -> None:
    """Click 컨텍스트에서 verbose 옵션을 읽어 로깅 레벨 설정."""
    verbose = ctx.obj.get("verbose", False) if ctx.obj else False
    debug = ctx.obj.get("debug", False) if ctx.obj else False

    if debug:
        logger.set_level(LogLevel.DEBUG)
    elif verbose:
        logger.set_level(LogLevel.VERBOSE)
    else:
        logger.set_level(LogLevel.INFO)
