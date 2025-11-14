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


class WorkspaceInitCommand:
    """Workspace 초기화 명령어."""

    def __init__(
        self,
        output_file: str = "workspace.yaml",
        interactive: bool = True,
    ) -> None:
        """Initialize workspace init command.

        Args:
            output_file: 생성할 workspace.yaml 경로
            interactive: 대화형 모드 여부

        """
        self.output_file = Path(output_file)
        self.interactive = interactive
        self.console = Console()

    def execute(self) -> None:
        """Execute workspace initialization.

        Raises:
            click.Abort: 초기화 실패 시

        """
        logger.heading("Workspace Initialization")

        # 파일 존재 확인
        if self.output_file.exists():
            if not click.confirm(
                f"{self.output_file} 파일이 이미 존재합니다. 덮어쓰시겠습니까?",
                default=False,
            ):
                logger.info("Workspace 초기화가 취소되었습니다.")
                raise click.Abort

        # 템플릿 생성
        if self.interactive:
            workspace_config = self._interactive_template()
        else:
            workspace_config = self._default_template()

        # YAML 저장
        try:
            import yaml

            self.output_file.parent.mkdir(parents=True, exist_ok=True)
            with open(self.output_file, "w", encoding="utf-8") as f:
                yaml.dump(
                    workspace_config,
                    f,
                    allow_unicode=True,
                    default_flow_style=False,
                    sort_keys=False,
                )
            logger.success(f"✅ Workspace 파일 생성 완료: {self.output_file}")
        except Exception as e:
            logger.error(f"Workspace 파일 생성 실패: {e}")
            raise click.Abort

        # 다음 단계 안내
        self._show_next_steps()

    def _interactive_template(self) -> dict:
        """대화형 템플릿 생성."""
        self.console.print("\n[bold cyan]📝 Workspace 설정 입력[/bold cyan]")

        workspace_name = click.prompt(
            "Workspace 이름", default="my-workspace", type=str
        )
        description = click.prompt(
            "설명 (선택사항)", default="", type=str, show_default=False
        )
        environment = click.prompt(
            "환경 (dev/staging/prod)", default="dev", type=str
        )

        # Phase 개수 입력
        num_phases = click.prompt("Phase 개수", default=2, type=int)

        phases = {}
        for i in range(1, num_phases + 1):
            self.console.print(f"\n[bold yellow]Phase {i} 설정[/bold yellow]")
            phase_name = click.prompt(
                f"Phase {i} 이름", default=f"p{i}-phase", type=str
            )
            phase_desc = click.prompt(
                f"Phase {i} 설명", default=f"Phase {i}", type=str
            )
            phase_source = click.prompt(
                f"Phase {i} sources.yaml 경로",
                default=f"p{i}-kube/sources.yaml",
                type=str,
            )

            # App groups 입력
            app_groups_str = click.prompt(
                f"Phase {i} 앱 그룹 (쉼표 구분)",
                default=f"a{i*100:03d}_app",
                type=str,
            )
            app_groups = [g.strip() for g in app_groups_str.split(",")]

            # 의존성 입력 (Phase 2부터)
            depends_on = []
            if i > 1:
                prev_phases = list(phases.keys())
                if click.confirm(
                    f"Phase {i}가 이전 Phase에 의존합니까?", default=True
                ):
                    depends_str = click.prompt(
                        f"의존하는 Phase (쉼표 구분, 가능: {', '.join(prev_phases)})",
                        default=prev_phases[-1] if prev_phases else "",
                        type=str,
                    )
                    depends_on = [d.strip() for d in depends_str.split(",") if d.strip()]

            phases[phase_name] = {
                "description": phase_desc,
                "source": phase_source,
                "app_groups": app_groups,
            }
            if depends_on:
                phases[phase_name]["depends_on"] = depends_on

        return {
            "version": "1.0",
            "metadata": {
                "name": workspace_name,
                "description": description if description else None,
                "environment": environment,
                "tags": ["workspace", environment],
            },
            "global": {
                "timeout": 600,
                "on_failure": "stop",
            },
            "phases": phases,
        }

    def _default_template(self) -> dict:
        """기본 템플릿 생성."""
        return {
            "version": "1.0",
            "metadata": {
                "name": "my-workspace",
                "description": "Multi-phase deployment workspace",
                "environment": "dev",
                "tags": ["workspace", "multi-phase"],
            },
            "global": {
                "kubeconfig": None,
                "context": None,
                "timeout": 600,
                "on_failure": "stop",
                "helm_repos": {},
            },
            "phases": {
                "p1-infra": {
                    "description": "Infrastructure phase",
                    "source": "p1-kube/sources.yaml",
                    "app_groups": ["a000_network", "a001_storage"],
                    "depends_on": [],
                },
                "p2-data": {
                    "description": "Data layer phase",
                    "source": "p2-kube/sources.yaml",
                    "app_groups": ["a100_postgres", "a101_redis"],
                    "depends_on": ["p1-infra"],
                },
                "p3-app": {
                    "description": "Application phase",
                    "source": "p3-kube/sources.yaml",
                    "app_groups": ["a200_backend", "a201_frontend"],
                    "depends_on": ["p2-data"],
                },
            },
        }

    def _show_next_steps(self) -> None:
        """다음 단계 안내."""
        self.console.print("\n[bold green]🎉 Workspace 초기화 완료![/bold green]")
        self.console.print("\n[bold cyan]다음 단계:[/bold cyan]")
        self.console.print(f"  1. {self.output_file} 파일을 확인하세요")
        self.console.print("  2. 각 Phase의 sources.yaml 파일을 생성하세요:")
        self.console.print("     - p1-kube/sources.yaml")
        self.console.print("     - p2-kube/sources.yaml")
        self.console.print("     - p3-kube/sources.yaml")
        self.console.print("\n  3. Workspace를 검증하세요:")
        self.console.print(f"     sbkube workspace validate {self.output_file}")
        self.console.print("\n  4. Phase 의존성 그래프를 확인하세요:")
        self.console.print(f"     sbkube workspace graph {self.output_file}")


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


@workspace_group.command(name="init")
@click.argument(
    "output_file",
    type=click.Path(dir_okay=False, resolve_path=True),
    default="workspace.yaml",
)
@click.option(
    "--non-interactive",
    is_flag=True,
    help="대화형 입력 없이 기본 템플릿 생성",
)
@click.option("-v", "--verbose", is_flag=True, help="상세 로그 출력")
@click.option("--debug", is_flag=True, help="디버그 로그 출력")
@click.pass_context
def init_cmd(
    ctx: click.Context,
    output_file: str,
    non_interactive: bool,
    verbose: bool,
    debug: bool,
) -> None:
    """workspace.yaml 템플릿을 생성합니다.

    Examples:
        # Interactive mode (default)
        sbkube workspace init

        # Non-interactive mode (default template)
        sbkube workspace init --non-interactive

        # Custom output path
        sbkube workspace init /path/to/workspace.yaml

    """
    ctx.ensure_object(dict)
    ctx.obj["verbose"] = verbose
    ctx.obj["debug"] = debug
    setup_logging_from_context(ctx)

    init_command = WorkspaceInitCommand(
        output_file=output_file,
        interactive=not non_interactive,
    )
    init_command.execute()
