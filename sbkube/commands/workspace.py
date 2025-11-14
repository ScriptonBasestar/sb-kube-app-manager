"""Workspace 명령어 구현."""

from pathlib import Path

import click
from pydantic import ValidationError as PydanticValidationError
from rich.console import Console
from rich.table import Table
from rich.tree import Tree

from sbkube.exceptions import ConfigValidationError
from sbkube.models.workspace_model import WorkspaceConfig
from sbkube.utils.file_loader import load_config_file
from sbkube.utils.logger import logger, setup_logging_from_context


class WorkspaceValidateCommand:
    """Workspace 검증 명령어."""

    def __init__(self, workspace_file: str) -> None:
        """Initialize workspace validate command.

        Args:
            workspace_file: workspace.yaml 경로

        """
        self.workspace_file = Path(workspace_file)
        self.console = Console()

    def execute(self) -> WorkspaceConfig:
        """Execute workspace validation.

        Returns:
            WorkspaceConfig: 검증된 workspace 설정

        Raises:
            click.Abort: 검증 실패 시

        """
        logger.heading(f"Workspace Validation - {self.workspace_file}")

        # 파일 존재 확인
        if not self.workspace_file.exists():
            logger.error(f"Workspace 파일을 찾을 수 없습니다: {self.workspace_file}")
            raise click.Abort

        # 파일 로드
        try:
            logger.info(f"Workspace 파일 로드 중: {self.workspace_file}")
            data = load_config_file(str(self.workspace_file))
            logger.success("Workspace 파일 로드 성공")
        except Exception as e:
            logger.error(f"Workspace 파일 로딩 실패: {e}")
            raise click.Abort

        # Pydantic 모델 검증
        try:
            logger.info("Workspace 모델 검증 중 (WorkspaceConfig)...")
            workspace = WorkspaceConfig(**data)
            logger.success("Workspace 모델 검증 통과")
        except (PydanticValidationError, ConfigValidationError) as e:
            logger.error("Workspace 모델 검증 실패:")
            if isinstance(e, PydanticValidationError):
                for error in e.errors():
                    loc = " -> ".join(str(x) for x in error["loc"])
                    logger.error(f"  - {loc}: {error['msg']}")
            else:
                # ConfigValidationError는 이미 포맷된 메시지 포함
                logger.error(str(e))
            raise click.Abort

        # 검증 결과 출력
        self._print_validation_summary(workspace)

        logger.success("✅ Workspace 검증 완료")
        return workspace

    def _print_validation_summary(self, workspace: WorkspaceConfig) -> None:
        """Print workspace validation summary.

        Args:
            workspace: 검증된 workspace 설정

        """
        self.console.print("\n[bold cyan]━━━ Workspace Summary ━━━[/bold cyan]")
        self.console.print(f"  Name: {workspace.metadata.name}")
        if workspace.metadata.description:
            self.console.print(f"  Description: {workspace.metadata.description}")
        if workspace.metadata.environment:
            self.console.print(f"  Environment: {workspace.metadata.environment}")
        if workspace.metadata.tags:
            self.console.print(f"  Tags: {', '.join(workspace.metadata.tags)}")

        self.console.print(f"\n  Version: {workspace.version}")
        self.console.print(f"  Phases: {len(workspace.phases)}")

        # Phase 리스트 출력
        table = Table(show_header=True, header_style="bold magenta")
        table.add_column("Phase", style="cyan")
        table.add_column("App Groups", style="green")
        table.add_column("Dependencies", style="yellow")

        for phase_name, phase_config in workspace.phases.items():
            deps_str = ", ".join(phase_config.depends_on) if phase_config.depends_on else "-"
            groups_str = ", ".join(phase_config.app_groups)
            table.add_row(phase_name, groups_str, deps_str)

        self.console.print(table)

        # Phase 실행 순서 출력
        try:
            phase_order = workspace.get_phase_order()
            self.console.print(
                f"\n[bold green]Execution Order:[/bold green] {' → '.join(phase_order)}"
            )
        except ValueError as e:
            logger.error(f"Phase 실행 순서 계산 실패: {e}")


class WorkspaceGraphCommand:
    """Workspace Phase 의존성 그래프 시각화 명령어."""

    def __init__(self, workspace_file: str) -> None:
        """Initialize workspace graph command.

        Args:
            workspace_file: workspace.yaml 경로

        """
        self.workspace_file = Path(workspace_file)
        self.console = Console()

    def execute(self) -> None:
        """Execute workspace graph visualization.

        Raises:
            click.Abort: 검증 실패 시

        """
        logger.heading(f"Workspace Dependency Graph - {self.workspace_file}")

        # 파일 존재 확인
        if not self.workspace_file.exists():
            logger.error(f"Workspace 파일을 찾을 수 없습니다: {self.workspace_file}")
            raise click.Abort

        # 파일 로드
        try:
            data = load_config_file(str(self.workspace_file))
            workspace = WorkspaceConfig(**data)
        except Exception as e:
            logger.error(f"Workspace 로딩 실패: {e}")
            raise click.Abort

        # 의존성 그래프 출력
        self._print_dependency_graph(workspace)

    def _print_dependency_graph(self, workspace: WorkspaceConfig) -> None:
        """Print dependency graph using Rich Tree.

        Args:
            workspace: 검증된 workspace 설정

        """
        self.console.print(
            f"\n[bold cyan]━━━ Phase Dependency Graph: {workspace.metadata.name} ━━━[/bold cyan]"
        )

        # Phase 실행 순서 계산
        try:
            phase_order = workspace.get_phase_order()
        except ValueError as e:
            logger.error(f"Phase 실행 순서 계산 실패 (순환 의존성): {e}")
            raise click.Abort

        # 의존성 그래프 생성
        tree = Tree(f"[bold]Workspace: {workspace.metadata.name}[/bold]")

        # 각 Phase를 실행 순서대로 트리에 추가
        for phase_name in phase_order:
            phase_config = workspace.phases[phase_name]
            phase_label = f"[cyan]{phase_name}[/cyan]"
            if phase_config.description:
                phase_label += f" - {phase_config.description}"

            phase_branch = tree.add(phase_label)

            # 의존성 표시
            if phase_config.depends_on:
                deps_str = ", ".join(phase_config.depends_on)
                phase_branch.add(f"[yellow]Depends on:[/yellow] {deps_str}")

            # App Groups 표시
            groups_branch = phase_branch.add("[green]App Groups:[/green]")
            for group in phase_config.app_groups:
                groups_branch.add(f"├─ {group}")

            # Source 표시
            phase_branch.add(f"[magenta]Source:[/magenta] {phase_config.source}")

        self.console.print(tree)

        # 실행 순서 요약
        self.console.print(
            f"\n[bold green]Execution Order:[/bold green] {' → '.join(phase_order)}"
        )


@click.group(name="workspace")
def workspace_group() -> None:
    """Workspace 관리 명령어."""
    pass


@workspace_group.command(name="validate")
@click.argument(
    "workspace_file",
    type=click.Path(exists=True, dir_okay=False, resolve_path=True),
    default="workspace.yaml",
)
@click.option("-v", "--verbose", is_flag=True, help="상세 로그 출력")
@click.option("--debug", is_flag=True, help="디버그 로그 출력")
@click.pass_context
def validate_cmd(
    ctx: click.Context,
    workspace_file: str,
    verbose: bool,
    debug: bool,
) -> None:
    """workspace.yaml 파일을 검증합니다.

    Examples:
        # Validate default workspace.yaml
        sbkube workspace validate

        # Validate specific file
        sbkube workspace validate /path/to/workspace.yaml

    """
    ctx.ensure_object(dict)
    ctx.obj["verbose"] = verbose
    ctx.obj["debug"] = debug
    setup_logging_from_context(ctx)

    validate_command = WorkspaceValidateCommand(workspace_file)
    validate_command.execute()


@workspace_group.command(name="graph")
@click.argument(
    "workspace_file",
    type=click.Path(exists=True, dir_okay=False, resolve_path=True),
    default="workspace.yaml",
)
@click.option("-v", "--verbose", is_flag=True, help="상세 로그 출력")
@click.option("--debug", is_flag=True, help="디버그 로그 출력")
@click.pass_context
def graph_cmd(
    ctx: click.Context,
    workspace_file: str,
    verbose: bool,
    debug: bool,
) -> None:
    """Phase 의존성 그래프를 시각화합니다.

    Examples:
        # Visualize default workspace.yaml
        sbkube workspace graph

        # Visualize specific file
        sbkube workspace graph /path/to/workspace.yaml

    """
    ctx.ensure_object(dict)
    ctx.obj["verbose"] = verbose
    ctx.obj["debug"] = debug
    setup_logging_from_context(ctx)

    graph_command = WorkspaceGraphCommand(workspace_file)
    graph_command.execute()
