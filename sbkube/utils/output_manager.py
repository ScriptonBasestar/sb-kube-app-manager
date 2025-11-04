"""
OutputManager: Human/LLM/JSON/YAML 출력을 통합 관리하는 매니저.

이 모듈은 SBKube 명령어의 출력을 통합 관리하여,
human/llm/json/yaml 포맷 간 일관된 인터페이스를 제공합니다.
"""

import re
from typing import Any

from rich.console import Console

from sbkube.utils.output_formatter import OutputFormatter


class OutputManager:
    """
    Human/LLM/JSON/YAML 출력을 통합 관리하는 매니저.

    - human 모드: Rich Console로 컬러풀한 출력 (즉시 출력)
    - llm/json/yaml 모드: 구조화된 데이터 수집 후 최종 출력

    Usage:
        output = OutputManager(format_type="human")
        output.print("Processing...", level="info")
        output.print_section("Deployment", app="traefik")
        output.print_error("Failed to deploy", error="Connection timeout")
        output.finalize(status="success", summary={"deployed": 3})
    """

    def __init__(self, format_type: str = "human"):
        """
        OutputManager 초기화.

        Args:
            format_type: 출력 포맷 (human, llm, json, yaml)
        """
        self.format_type = format_type
        self.console = Console(quiet=(format_type != "human"))
        self.formatter = OutputFormatter(format_type=format_type)
        self.events: list[dict[str, Any]] = []  # LLM/JSON/YAML용 이벤트 수집
        self.deployments: list[dict[str, Any]] = []  # Deployment 정보 추적
        self.error_messages: list[str] = []  # 에러 메시지 누적
        self._finalized = False

    @staticmethod
    def _strip_markup(text: str) -> str:
        """
        Rich 마크업 제거 (LLM/JSON/YAML 출력용).

        Args:
            text: Rich 마크업이 포함된 텍스트

        Returns:
            마크업이 제거된 순수 텍스트

        Examples:
            >>> OutputManager._strip_markup("[bold]Hello[/bold]")
            'Hello'
            >>> OutputManager._strip_markup("[bold cyan]Title[/bold cyan]")
            'Title'
            >>> OutputManager._strip_markup("[dim red]Error[/dim red]")
            'Error'
        """
        # Remove Rich markup including complex styles like [bold cyan], [dim red], RGB colors, etc.
        # Supports: colors, styles, closing tags, combinations with spaces, RGB, hex colors
        # Pattern matches [tag], [/tag], [tag with spaces], [RGB(...)], [#hex], etc.
        return re.sub(r"\[/?[^\]]+\]", "", text)

    def print(
        self,
        message: str,
        level: str = "info",
        emoji: str | None = None,
        **metadata: Any,
    ) -> None:
        """
        통합 출력 메서드.

        Args:
            message: 출력할 메시지
            level: 로그 레벨 (info, warning, error, success)
            emoji: 이모지 (human 모드에서만 사용)
            **metadata: 추가 메타데이터 (LLM/JSON/YAML 모드에서 사용)
        """
        if self.format_type == "human":
            self.console.print(message)
        else:
            # 구조화된 이벤트로 수집
            self.events.append(
                {
                    "type": "message",
                    "level": level,
                    "message": self._strip_markup(message),
                    "emoji": emoji,
                    **metadata,
                }
            )

    def print_section(self, title: str, **metadata: Any) -> None:
        """
        섹션 헤더 출력.

        Args:
            title: 섹션 제목
            **metadata: 추가 메타데이터 (LLM/JSON/YAML 모드에서 사용)
        """
        if self.format_type == "human":
            self.console.print(f"\n[bold cyan]━━━ {title} ━━━[/bold cyan]")
        else:
            self.events.append(
                {
                    "type": "section",
                    "title": title,
                    **metadata,
                }
            )

    def print_error(self, message: str, error: str | None = None, **metadata: Any) -> None:
        """
        에러 메시지 출력.

        Args:
            message: 에러 메시지
            error: 에러 상세 정보
            **metadata: 추가 메타데이터
        """
        # 에러 메시지 누적 (LLM/JSON/YAML 모드용)
        clean_message = self._strip_markup(message)
        if clean_message not in self.error_messages:
            self.error_messages.append(clean_message)

        if self.format_type == "human":
            self.console.print(f"[red]❌ {message}[/red]")
            if error:
                self.console.print(f"[dim]   {error}[/dim]")
        else:
            self.events.append(
                {
                    "type": "error",
                    "level": "error",
                    "message": clean_message,
                    "error": error,
                    **metadata,
                }
            )

    def print_warning(self, message: str, **metadata: Any) -> None:
        """
        경고 메시지 출력.

        Args:
            message: 경고 메시지
            **metadata: 추가 메타데이터
        """
        if self.format_type == "human":
            self.console.print(f"[yellow]⚠️  {message}[/yellow]")
        else:
            self.events.append(
                {
                    "type": "warning",
                    "level": "warning",
                    "message": message,
                    **metadata,
                }
            )

    def print_success(self, message: str, **metadata: Any) -> None:
        """
        성공 메시지 출력.

        Args:
            message: 성공 메시지
            **metadata: 추가 메타데이터
        """
        if self.format_type == "human":
            self.console.print(f"[green]✅ {message}[/green]")
        else:
            self.events.append(
                {
                    "type": "success",
                    "level": "success",
                    "message": message,
                    **metadata,
                }
            )

    def print_list(self, items: list[str], title: str | None = None) -> None:
        """
        리스트 출력.

        Args:
            items: 출력할 항목 리스트
            title: 리스트 제목 (선택)
        """
        if self.format_type == "human":
            if title:
                self.console.print(f"\n[cyan]{title}:[/cyan]")
            for item in items:
                self.console.print(f"  {item}")
        else:
            self.events.append(
                {
                    "type": "list",
                    "title": title,
                    "items": [self._strip_markup(item) for item in items],
                }
            )

    def add_deployment(
        self,
        name: str,
        namespace: str,
        status: str,
        version: str | None = None,
    ) -> None:
        """
        배포 정보 기록 (LLM/JSON/YAML 출력용).

        Args:
            name: 앱 이름
            namespace: 네임스페이스
            status: 배포 상태 (deployed, failed, skipped 등)
            version: 차트 버전 (선택)
        """
        self.deployments.append(
            {
                "name": name,
                "namespace": namespace,
                "status": status,
                "version": version or "",
            }
        )

    def finalize(
        self,
        status: str,
        summary: dict[str, Any],
        next_steps: list[str] | None = None,
        errors: list[str] | None = None,
    ) -> None:
        """
        최종 출력 (LLM/JSON/YAML 모드에서 구조화된 데이터 출력).

        Args:
            status: 최종 상태 (success, failed, warning)
            summary: 요약 정보
            next_steps: 다음 단계 제안 (선택)
            errors: 에러 목록 (선택)
        """
        if self._finalized:
            return  # 중복 호출 방지

        self._finalized = True

        if self.format_type == "human":
            # Human 모드에서는 finalize가 특별한 동작을 하지 않음
            # (이미 즉시 출력되었으므로)
            return

        # LLM/JSON/YAML 모드: 수집된 deployment 정보를 구조화하여 출력
        # 에러 메시지 우선순위: 명시적 전달 > 누적된 에러 > 이벤트에서 추출
        final_errors = errors if errors is not None else self.error_messages
        if not final_errors:
            # 최후의 수단: events에서 추출
            final_errors = [e["message"] for e in self.events if e.get("level") == "error"]

        result = self.formatter.format_deployment_result(
            status=status,
            summary=summary,
            deployments=self.deployments,  # ✅ self.events 대신 self.deployments 사용
            next_steps=next_steps or [],
            errors=final_errors,
        )
        self.formatter.print_output(result)

    def get_console(self) -> Console:
        """
        Rich Console 객체 반환 (고급 기능용).

        Returns:
            Rich Console 객체
        """
        return self.console
