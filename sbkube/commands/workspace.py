"""Workspace 명령어 구현."""

import threading
from concurrent.futures import ThreadPoolExecutor, as_completed
from pathlib import Path
from typing import Any

import click
from pydantic import ValidationError as PydanticValidationError
from rich.console import Console
from rich.panel import Panel
from rich.table import Table
from rich.tree import Tree

from sbkube.exceptions import ConfigValidationError
from sbkube.models.unified_config_model import PhaseReference, UnifiedConfig
from sbkube.models.workspace_state import (
    PhaseDeploymentCreate,
    WorkspaceDeploymentCreate,
)
from sbkube.state.database import DeploymentDatabase
from sbkube.state.workspace_tracker import WorkspaceStateTracker
from sbkube.utils.file_loader import load_config_file
from sbkube.utils.logger import logger, setup_logging_from_context


# SBKube version for tracking
def _get_sbkube_version() -> str:
    """Get SBKube version safely."""
    try:
        from importlib.metadata import version
        return version("sbkube")
    except Exception:
        return "unknown"


SBKUBE_VERSION = _get_sbkube_version()


class WorkspaceValidateCommand:
    """Workspace 검증 명령어."""

    def __init__(self, workspace_file: str) -> None:
        """Initialize workspace validate command.

        Args:
            workspace_file: sbkube.yaml 경로

        """
        self.workspace_file = Path(workspace_file)
        self.console = Console()

    def execute(self) -> UnifiedConfig:
        """Execute workspace validation.

        Returns:
            UnifiedConfig: 검증된 workspace 설정

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
            logger.info("Workspace 모델 검증 중 (UnifiedConfig)...")
            workspace = UnifiedConfig(**data)
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

    def _print_validation_summary(self, workspace: UnifiedConfig) -> None:
        """Print workspace validation summary.

        Args:
            workspace: 검증된 workspace 설정

        """
        self.console.print("\n[bold cyan]━━━ Workspace Summary ━━━[/bold cyan]")
        self.console.print(f"  Name: {workspace.metadata.get('name', 'unnamed')}")
        if workspace.metadata.get("description"):
            self.console.print(f"  Description: {workspace.metadata['description']}")
        if workspace.metadata.get("environment"):
            self.console.print(f"  Environment: {workspace.metadata['environment']}")
        if workspace.metadata.get("tags"):
            self.console.print(f"  Tags: {', '.join(workspace.metadata['tags'])}")

        self.console.print(f"\n  API Version: {workspace.apiVersion}")
        self.console.print(f"  Phases: {len(workspace.phases)}")

        # Phase 리스트 출력
        table = Table(show_header=True, header_style="bold magenta")
        table.add_column("Phase", style="cyan")
        table.add_column("App Groups", style="green")
        table.add_column("Dependencies", style="yellow")

        for phase_name, phase_config in workspace.phases.items():
            deps_str = ", ".join(phase_config.depends_on) if phase_config.depends_on else "-"
            groups_str = ", ".join(phase_config.app_groups) if phase_config.app_groups else "(auto)"
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
            workspace_file: sbkube.yaml 경로

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
            workspace = UnifiedConfig(**data)
        except Exception as e:
            logger.error(f"Workspace 로딩 실패: {e}")
            raise click.Abort

        # 의존성 그래프 출력
        self._print_dependency_graph(workspace)

    def _print_dependency_graph(self, workspace: UnifiedConfig) -> None:
        """Print dependency graph using Rich Tree.

        Args:
            workspace: 검증된 workspace 설정

        """
        workspace_name = workspace.metadata.get("name", "unnamed")
        self.console.print(
            f"\n[bold cyan]━━━ Phase Dependency Graph: {workspace_name} ━━━[/bold cyan]"
        )

        # Phase 실행 순서 계산
        try:
            phase_order = workspace.get_phase_order()
        except ValueError as e:
            logger.error(f"Phase 실행 순서 계산 실패 (순환 의존성): {e}")
            raise click.Abort

        # 의존성 그래프 생성
        tree = Tree(f"[bold]Workspace: {workspace_name}[/bold]")

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
            if phase_config.app_groups:
                groups_branch = phase_branch.add("[green]App Groups:[/green]")
                for group in phase_config.app_groups:
                    groups_branch.add(f"├─ {group}")
            else:
                phase_branch.add("[green]App Groups:[/green] (auto-discover)")

            # Source 표시
            if phase_config.source:
                phase_branch.add(f"[magenta]Source:[/magenta] {phase_config.source}")
            else:
                phase_branch.add(f"[magenta]Inline apps:[/magenta] {len(phase_config.apps)}")

        self.console.print(tree)

        # 실행 순서 요약
        self.console.print(
            f"\n[bold green]Execution Order:[/bold green] {' → '.join(phase_order)}"
        )


class WorkspaceInitCommand:
    """Workspace 초기화 명령어."""

    def __init__(
        self,
        output_file: str = "sbkube.yaml",
        interactive: bool = True,
    ) -> None:
        """Initialize workspace init command.

        Args:
            output_file: 생성할 sbkube.yaml 경로
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
                f"Phase {i} sbkube.yaml 경로",
                default=f"p{i}-kube/sbkube.yaml",
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
            "apiVersion": "sbkube/v1",
            "metadata": {
                "name": workspace_name,
                "description": description if description else None,
                "environment": environment,
                "tags": ["workspace", environment],
            },
            "settings": {
                "timeout": 600,
                "on_failure": "stop",
            },
            "phases": phases,
        }

    def _default_template(self) -> dict:
        """기본 템플릿 생성."""
        return {
            "apiVersion": "sbkube/v1",
            "metadata": {
                "name": "my-workspace",
                "description": "Multi-phase deployment workspace",
                "environment": "dev",
                "tags": ["workspace", "multi-phase"],
            },
            "settings": {
                "namespace": "default",
                "timeout": 600,
                "on_failure": "stop",
            },
            "phases": {
                "p1-infra": {
                    "description": "Infrastructure phase",
                    "source": "p1-kube/sbkube.yaml",
                    "depends_on": [],
                },
                "p2-data": {
                    "description": "Data layer phase",
                    "source": "p2-kube/sbkube.yaml",
                    "depends_on": ["p1-infra"],
                },
                "p3-app": {
                    "description": "Application phase",
                    "source": "p3-kube/sbkube.yaml",
                    "depends_on": ["p2-data"],
                },
            },
        }

    def _show_next_steps(self) -> None:
        """다음 단계 안내."""
        self.console.print("\n[bold green]🎉 Workspace 초기화 완료![/bold green]")
        self.console.print("\n[bold cyan]다음 단계:[/bold cyan]")
        self.console.print(f"  1. {self.output_file} 파일을 확인하세요")
        self.console.print("  2. 각 Phase의 sbkube.yaml 파일을 생성하세요:")
        self.console.print("     - p1-kube/sbkube.yaml")
        self.console.print("     - p2-kube/sbkube.yaml")
        self.console.print("     - p3-kube/sbkube.yaml")
        self.console.print("\n  3. Workspace를 검증하세요:")
        self.console.print(f"     sbkube workspace validate {self.output_file}")
        self.console.print("\n  4. Phase 의존성 그래프를 확인하세요:")
        self.console.print(f"     sbkube workspace graph {self.output_file}")


@click.group(name="workspace")
def workspace_group() -> None:
    """Workspace 관리 명령어."""


@workspace_group.command(name="validate")
@click.argument(
    "workspace_file",
    type=click.Path(exists=True, dir_okay=False, resolve_path=True),
    default="sbkube.yaml",
)
@click.option("-v", "--verbose", count=True, help="로깅 상세도 (-v: 정보, -vv: 상세)")
@click.option("--debug", is_flag=True, help="디버그 로그 출력")
@click.pass_context
def validate_cmd(
    ctx: click.Context,
    workspace_file: str,
    verbose: int,
    debug: bool,
) -> None:
    """sbkube.yaml 파일을 검증합니다.

    Examples:
        # Validate default sbkube.yaml
        sbkube workspace validate

        # Validate specific file
        sbkube workspace validate /path/to/sbkube.yaml

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
    default="sbkube.yaml",
)
@click.option("-v", "--verbose", count=True, help="로깅 상세도 (-v: 정보, -vv: 상세)")
@click.option("--debug", is_flag=True, help="디버그 로그 출력")
@click.pass_context
def graph_cmd(
    ctx: click.Context,
    workspace_file: str,
    verbose: int,
    debug: bool,
) -> None:
    """Phase 의존성 그래프를 시각화합니다.

    Examples:
        # Visualize default sbkube.yaml
        sbkube workspace graph

        # Visualize specific file
        sbkube workspace graph /path/to/sbkube.yaml

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
    default="sbkube.yaml",
)
@click.option(
    "--non-interactive",
    is_flag=True,
    help="대화형 입력 없이 기본 템플릿 생성",
)
@click.option("-v", "--verbose", count=True, help="로깅 상세도 (-v: 정보, -vv: 상세)")
@click.option("--debug", is_flag=True, help="디버그 로그 출력")
@click.pass_context
def init_cmd(
    ctx: click.Context,
    output_file: str,
    non_interactive: bool,
    verbose: int,
    debug: bool,
) -> None:
    """sbkube.yaml 템플릿을 생성합니다.

    Examples:
        # Interactive mode (default)
        sbkube workspace init

        # Non-interactive mode (default template)
        sbkube workspace init --non-interactive

        # Custom output path
        sbkube workspace init /path/to/sbkube.yaml

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


class WorkspaceDeployCommand:
    """Workspace 배포 명령어.

    Multi-phase deployment를 실행합니다.
    Phase 의존성 순서대로 각 Phase를 배포합니다.
    병렬 모드에서는 의존성이 없는 Phase들을 동시에 실행합니다.
    """

    def __init__(
        self,
        workspace_file: str,
        phase: str | None = None,
        dry_run: bool = False,
        force: bool = False,
        skip_validation: bool = False,
        parallel: bool = False,
        parallel_apps: bool = False,
        max_workers: int = 4,
        inherited_settings: dict | None = None,
    ) -> None:
        """Initialize workspace deploy command.

        Args:
            workspace_file: sbkube.yaml 경로
            phase: 특정 Phase만 배포 (None이면 전체 배포)
            dry_run: 실제 배포 없이 시뮬레이션
            force: 이전 상태 무시하고 강제 배포
            skip_validation: 파일 존재 검증 건너뛰기
            parallel: 병렬 실행 모드 (Phase 간 병렬)
            parallel_apps: App group 병렬 실행 모드 (Phase 내 병렬)
            max_workers: 최대 병렬 워커 수 (기본: 4)
            inherited_settings: Settings inherited from parent workspace

        """
        self.workspace_file = Path(workspace_file)
        self.workspace_dir = self.workspace_file.parent
        self.phase = phase
        self.dry_run = dry_run
        self.force = force
        self.skip_validation = skip_validation
        self.parallel = parallel
        self.parallel_apps = parallel_apps
        self.max_workers = max_workers
        self.inherited_settings = inherited_settings or {}
        self.console = Console()
        self.phase_results: dict[str, dict[str, Any]] = {}
        self._results_lock = threading.Lock()

        # State tracking
        self.db = DeploymentDatabase()
        self.workspace_deployment_id: str | None = None
        self.phase_names: list[str] = []

    def execute(self) -> bool:
        """Execute workspace deployment.

        Returns:
            bool: 배포 성공 여부

        Raises:
            click.Abort: 배포 실패 시

        """
        logger.heading(f"Workspace Deployment - {self.workspace_file}")

        if self.dry_run:
            self.console.print(
                Panel(
                    "[yellow]DRY-RUN MODE[/yellow]: 실제 배포가 실행되지 않습니다.",
                    style="yellow",
                )
            )

        if self.parallel:
            self.console.print(
                Panel(
                    "[cyan]PARALLEL MODE[/cyan]: 독립적인 Phase들을 병렬로 실행합니다.\n"
                    f"Max workers: {self.max_workers}",
                    style="cyan",
                )
            )

        if self.parallel_apps:
            self.console.print(
                Panel(
                    "[magenta]PARALLEL-APPS MODE[/magenta]: Phase 내 App groups를 병렬로 실행합니다.\n"
                    f"Max workers: {self.max_workers}\n"
                    "app_group_deps로 의존성 정의 가능",
                    style="magenta",
                )
            )

        # 1. Workspace 로드 및 검증
        workspace = self._load_and_validate_workspace()

        # 2. Phase 실행 순서 계산
        phase_order = self._get_execution_order(workspace)

        # 3. State tracking 시작
        self._start_deployment_tracking(workspace, phase_order)

        # 4. 배포 실행
        try:
            if self.parallel and len(phase_order) > 1:
                success = self._execute_phases_parallel(workspace, phase_order)
            else:
                success = self._execute_phases(workspace, phase_order)

            # 5. State tracking 완료
            self._complete_deployment_tracking(success)
        except Exception as e:
            # 예외 발생 시에도 tracking 완료
            self._complete_deployment_tracking(False, str(e))
            raise

        # 6. 결과 요약
        self._print_summary(workspace, phase_order)

        return success

    def _start_deployment_tracking(
        self, workspace: UnifiedConfig, phase_order: list[str]
    ) -> None:
        """Start deployment state tracking.

        Args:
            workspace: Workspace configuration
            phase_order: Phase execution order

        """
        with self.db.get_session() as session:
            tracker = WorkspaceStateTracker(session)

            # Create workspace deployment record
            create_data = WorkspaceDeploymentCreate(
                workspace_name=workspace.metadata.get("name", "unnamed"),
                workspace_file=str(self.workspace_file),
                environment=workspace.metadata.get("environment"),
                dry_run=self.dry_run,
                force=self.force,
                target_phase=self.phase,
                workspace_config=workspace.model_dump(),
            )

            workspace_deployment = tracker.start_workspace_deployment(
                create_data, sbkube_version=SBKUBE_VERSION
            )

            # Store only the ID to avoid detached instance issues
            self.workspace_deployment_id = workspace_deployment.workspace_deployment_id
            self.phase_names = list(phase_order)

            # Create phase deployment records
            for order, phase_name in enumerate(phase_order, 1):
                phase_config = workspace.phases[phase_name]
                phase_data = PhaseDeploymentCreate(
                    phase_name=phase_name,
                    phase_description=phase_config.description,
                    source_path=phase_config.source,
                    execution_order=order,
                    depends_on=phase_config.depends_on,
                    app_groups=phase_config.app_groups,
                    on_failure_action=self._resolve_on_failure(phase_config, workspace.settings.on_failure),
                )
                tracker.add_phase_deployment(workspace_deployment, phase_data)

            logger.verbose(
                f"Started workspace deployment: {self.workspace_deployment_id}"
            )

    def _complete_deployment_tracking(
        self, success: bool, error_message: str | None = None
    ) -> None:
        """Complete deployment state tracking.

        Args:
            success: Whether the deployment succeeded
            error_message: Error message if failed

        """
        if not self.workspace_deployment_id:
            return

        with self.db.get_session() as session:
            tracker = WorkspaceStateTracker(session)

            # Get fresh deployment object from database
            deployment = tracker.get_workspace_deployment(self.workspace_deployment_id)
            if deployment:
                tracker.complete_workspace_deployment(deployment, success, error_message)
                logger.verbose(
                    f"Completed workspace deployment: {deployment.workspace_deployment_id} "
                    f"(success={success})"
                )

    def _load_and_validate_workspace(self) -> UnifiedConfig:
        """Load and validate workspace configuration.

        Returns:
            WorkspaceConfig: 검증된 workspace 설정

        Raises:
            click.Abort: 로드/검증 실패 시

        """
        # 파일 존재 확인
        if not self.workspace_file.exists():
            logger.error(f"Workspace 파일을 찾을 수 없습니다: {self.workspace_file}")
            raise click.Abort

        # 파일 로드
        try:
            logger.info(f"Workspace 파일 로드 중: {self.workspace_file}")
            data = load_config_file(str(self.workspace_file))
        except Exception as e:
            logger.error(f"Workspace 파일 로딩 실패: {e}")
            raise click.Abort

        # Pydantic 모델 검증
        try:
            workspace = UnifiedConfig(**data)
            workspace_name = workspace.metadata.get("name", "unnamed")
            logger.success(f"Workspace '{workspace_name}' 로드 완료")
        except (PydanticValidationError, ConfigValidationError) as e:
            logger.error("Workspace 검증 실패:")
            if isinstance(e, PydanticValidationError):
                for error in e.errors():
                    loc = " -> ".join(str(x) for x in error["loc"])
                    logger.error(f"  - {loc}: {error['msg']}")
            else:
                logger.error(str(e))
            raise click.Abort

        # source 파일 존재 검증 (skip_validation이 아닌 경우)
        if not self.skip_validation:
            self._validate_source_files(workspace)

        return workspace

    def _validate_source_files(self, workspace: UnifiedConfig) -> None:
        """Validate that all source files exist.

        Args:
            workspace: Workspace configuration

        Raises:
            click.Abort: 파일이 존재하지 않는 경우

        """
        missing_files = []
        for phase_name, phase_config in workspace.phases.items():
            # Skip phases with inline apps (no source file)
            if not phase_config.source:
                continue
            source_path = self.workspace_dir / phase_config.source
            if not source_path.exists():
                missing_files.append((phase_name, str(source_path)))

        if missing_files:
            logger.error("다음 source 파일이 존재하지 않습니다:")
            for phase_name, path in missing_files:
                logger.error(f"  - Phase '{phase_name}': {path}")
            raise click.Abort

    def _get_execution_order(self, workspace: UnifiedConfig) -> list[str]:
        """Get phase execution order.

        Args:
            workspace: Workspace configuration

        Returns:
            List of phase names in execution order

        Raises:
            click.Abort: 순환 의존성 등 오류 시

        """
        try:
            if self.phase:
                # 특정 Phase만 배포하는 경우
                if self.phase not in workspace.phases:
                    logger.error(f"Phase '{self.phase}'를 찾을 수 없습니다.")
                    logger.info(f"사용 가능한 Phase: {', '.join(workspace.phases.keys())}")
                    raise click.Abort

                # 의존성 Phase들도 포함 (자동)
                return self._get_phase_with_dependencies(workspace, self.phase)
            # 전체 배포
            return workspace.get_phase_order()
        except ValueError as e:
            logger.error(f"Phase 실행 순서 계산 실패: {e}")
            raise click.Abort

    def _get_phase_with_dependencies(
        self, workspace: UnifiedConfig, target_phase: str
    ) -> list[str]:
        """Get target phase with all its dependencies.

        Args:
            workspace: Workspace configuration
            target_phase: Target phase name

        Returns:
            List of phase names including dependencies

        """
        # BFS로 모든 의존성 수집
        result = []
        visited = set()
        queue = [target_phase]

        while queue:
            phase_name = queue.pop(0)
            if phase_name in visited:
                continue
            visited.add(phase_name)
            result.append(phase_name)

            # 의존성 추가
            phase_config = workspace.phases[phase_name]
            for dep in phase_config.depends_on:
                if dep not in visited:
                    queue.append(dep)

        # 의존성 순서대로 정렬 (역순으로 실행)
        full_order = workspace.get_phase_order()
        return [p for p in full_order if p in result]

    @staticmethod
    def _resolve_on_failure(
        phase_config: "PhaseReference", global_on_failure: str
    ) -> str:
        """Resolve effective on_failure for a phase.

        Priority: phase.on_failure > phase.settings.on_failure > global

        """
        if phase_config.on_failure:
            return phase_config.on_failure
        if phase_config.settings and phase_config.settings.on_failure:
            return phase_config.settings.on_failure
        return global_on_failure

    def _execute_phases(
        self, workspace: UnifiedConfig, phase_order: list[str]
    ) -> bool:
        """Execute phases in order.

        Args:
            workspace: Workspace configuration
            phase_order: Phase execution order

        Returns:
            bool: 전체 성공 여부

        """
        self.console.print(
            f"\n[bold cyan]━━━ Deploying {len(phase_order)} Phase(s) ━━━[/bold cyan]"
        )
        self.console.print(f"Execution order: {' → '.join(phase_order)}\n")

        all_success = True
        global_on_failure = workspace.settings.on_failure

        for i, phase_name in enumerate(phase_order, 1):
            phase_config = workspace.phases[phase_name]

            # Skip disabled phases
            if not phase_config.enabled:
                self.console.print(
                    f"[yellow]⏭️  Phase {i}/{len(phase_order)}: {phase_name} (disabled)[/yellow]"
                )
                self.phase_results[phase_name] = {
                    "success": True,
                    "skipped": True,
                    "app_groups": phase_config.app_groups,
                }
                continue

            on_failure = self._resolve_on_failure(phase_config, global_on_failure)

            self.console.print(
                f"[bold yellow]Phase {i}/{len(phase_order)}: {phase_name}[/bold yellow]"
            )
            self.console.print(f"  Description: {phase_config.description}")
            if phase_config.app_groups:
                self.console.print(f"  App Groups: {', '.join(phase_config.app_groups)}")
            else:
                self.console.print("  App Groups: (auto-discovering...)")

            # Phase 배포 실행
            success, deployed_app_groups = self._deploy_phase(phase_name, phase_config, workspace)

            # 결과 저장
            self.phase_results[phase_name] = {
                "success": success,
                "app_groups": deployed_app_groups,
            }

            if success:
                logger.success(f"Phase '{phase_name}' 배포 완료")
            else:
                logger.error(f"Phase '{phase_name}' 배포 실패")
                all_success = False

                # 실패 시 동작 처리
                if on_failure == "stop":
                    logger.warning("on_failure=stop: 배포를 중단합니다.")
                    break
                if on_failure == "continue":
                    logger.warning("on_failure=continue: 다음 Phase를 계속 진행합니다.")
                elif on_failure == "rollback":
                    logger.warning("on_failure=rollback: 롤백 기능은 v1.1+에서 지원됩니다.")
                    logger.warning("현재는 배포를 중단합니다.")
                    break

            self.console.print()  # 구분선

        return all_success

    def _execute_phases_parallel(
        self, workspace: UnifiedConfig, phase_order: list[str]
    ) -> bool:
        """Execute phases in parallel where possible.

        Phases with satisfied dependencies run concurrently.
        Uses topological levels for parallel execution.

        Args:
            workspace: Workspace configuration
            phase_order: Phase execution order (topologically sorted)

        Returns:
            bool: 전체 성공 여부

        """
        self.console.print(
            f"\n[bold cyan]━━━ Parallel Deploying {len(phase_order)} Phase(s) ━━━[/bold cyan]"
        )

        # 1. Build dependency graph and calculate levels
        levels = self._calculate_parallel_levels(workspace, phase_order)

        self.console.print(f"Parallel execution levels: {len(levels)}")
        for i, level in enumerate(levels):
            self.console.print(f"  Level {i + 1}: {', '.join(level)}")
        self.console.print()

        all_success = True
        global_on_failure = workspace.settings.on_failure
        completed_phases: set[str] = set()
        failed_phases: set[str] = set()

        # 2. Execute level by level
        for level_idx, level_phases in enumerate(levels, 1):
            self.console.print(
                f"[bold magenta]━━━ Level {level_idx}/{len(levels)} "
                f"({len(level_phases)} phase(s)) ━━━[/bold magenta]"
            )

            if len(level_phases) == 1:
                # Single phase - execute sequentially
                phase_name = level_phases[0]
                success = self._execute_single_phase(
                    phase_name, workspace, global_on_failure
                )
                if success:
                    completed_phases.add(phase_name)
                else:
                    failed_phases.add(phase_name)
                    all_success = False
                    phase_on_failure = self._resolve_on_failure(
                        workspace.phases[phase_name], global_on_failure
                    )
                    if phase_on_failure == "stop":
                        logger.warning("on_failure=stop: 배포를 중단합니다.")
                        break
            else:
                # Multiple phases - execute in parallel
                level_results = self._execute_level_parallel(
                    level_phases, workspace, global_on_failure
                )

                for phase_name, success in level_results.items():
                    if success:
                        completed_phases.add(phase_name)
                    else:
                        failed_phases.add(phase_name)
                        all_success = False

                # Check if any failed phase requires stop
                should_stop = any(
                    self._resolve_on_failure(
                        workspace.phases[pn], global_on_failure
                    ) == "stop"
                    for pn in failed_phases
                )
                if should_stop:
                    logger.warning("on_failure=stop: 배포를 중단합니다.")
                    break

            self.console.print()

        return all_success

    def _calculate_parallel_levels(
        self, workspace: UnifiedConfig, phase_order: list[str]
    ) -> list[list[str]]:
        """Calculate parallel execution levels.

        Phases in the same level have no dependencies on each other
        and can be executed in parallel.

        Args:
            workspace: Workspace configuration
            phase_order: Topologically sorted phase order

        Returns:
            List of levels, each containing phases that can run in parallel

        """
        levels: list[list[str]] = []
        assigned: set[str] = set()

        # Calculate in-degree for each phase
        remaining = set(phase_order)

        while remaining:
            # Find phases with all dependencies satisfied
            current_level = []
            for phase_name in phase_order:
                if phase_name not in remaining:
                    continue

                phase_config = workspace.phases[phase_name]
                deps_satisfied = all(
                    dep in assigned for dep in phase_config.depends_on
                )

                if deps_satisfied:
                    current_level.append(phase_name)

            if not current_level:
                # Should not happen with valid topological sort
                logger.warning("Could not find phases with satisfied dependencies")
                break

            levels.append(current_level)
            for phase in current_level:
                assigned.add(phase)
                remaining.discard(phase)

        return levels

    def _execute_single_phase(
        self,
        phase_name: str,
        workspace: UnifiedConfig,
        global_on_failure: str,
    ) -> bool:
        """Execute a single phase and update results.

        Args:
            phase_name: Phase name
            workspace: Workspace configuration
            global_on_failure: Global failure behavior

        Returns:
            bool: 배포 성공 여부

        """
        phase_config = workspace.phases[phase_name]

        # Skip disabled phases
        if not phase_config.enabled:
            self.console.print(
                f"[yellow]⏭️  Phase: {phase_name} (disabled)[/yellow]"
            )
            with self._results_lock:
                self.phase_results[phase_name] = {
                    "success": True,
                    "skipped": True,
                    "app_groups": phase_config.app_groups,
                }
            return True

        self.console.print(f"[bold yellow]Phase: {phase_name}[/bold yellow]")
        self.console.print(f"  Description: {phase_config.description}")
        if phase_config.app_groups:
            self.console.print(f"  App Groups: {', '.join(phase_config.app_groups)}")
        else:
            self.console.print("  App Groups: (auto-discovering...)")

        success, deployed_app_groups = self._deploy_phase(phase_name, phase_config, workspace)

        with self._results_lock:
            self.phase_results[phase_name] = {
                "success": success,
                "app_groups": deployed_app_groups,
            }

        if success:
            logger.success(f"Phase '{phase_name}' 배포 완료")
        else:
            logger.error(f"Phase '{phase_name}' 배포 실패")

        return success

    def _execute_level_parallel(
        self,
        phases: list[str],
        workspace: UnifiedConfig,
        global_on_failure: str,
    ) -> dict[str, bool]:
        """Execute multiple phases in parallel.

        Args:
            phases: List of phase names to execute
            workspace: Workspace configuration
            global_on_failure: Global failure behavior

        Returns:
            Dict mapping phase name to success status

        """
        results: dict[str, bool] = {}

        self.console.print(
            f"[cyan]Executing {len(phases)} phases in parallel: "
            f"{', '.join(phases)}[/cyan]"
        )

        with ThreadPoolExecutor(max_workers=min(self.max_workers, len(phases))) as executor:
            # Submit all phases
            futures = {
                executor.submit(
                    self._deploy_phase_thread_safe,
                    phase_name,
                    workspace.phases[phase_name],
                    workspace,
                ): phase_name
                for phase_name in phases
            }

            # Collect results
            for future in as_completed(futures):
                phase_name = futures[future]
                try:
                    success, deployed_app_groups = future.result()
                    results[phase_name] = success

                    with self._results_lock:
                        self.phase_results[phase_name] = {
                            "success": success,
                            "app_groups": deployed_app_groups,
                        }

                    if success:
                        logger.success(f"Phase '{phase_name}' 배포 완료 (parallel)")
                    else:
                        logger.error(f"Phase '{phase_name}' 배포 실패 (parallel)")

                except Exception as e:
                    logger.error(f"Phase '{phase_name}' 실행 중 오류: {e}")
                    results[phase_name] = False

                    with self._results_lock:
                        self.phase_results[phase_name] = {
                            "success": False,
                            "app_groups": workspace.phases[phase_name].app_groups,
                            "error": str(e),
                        }

        return results

    def _deploy_phase_thread_safe(
        self,
        phase_name: str,
        phase_config: PhaseReference,
        workspace: UnifiedConfig,
    ) -> tuple[bool, list[str]]:
        """Thread-safe wrapper for _deploy_phase.

        Args:
            phase_name: Phase name
            phase_config: Phase configuration
            workspace: Workspace configuration

        Returns:
            tuple[bool, list[str]]: (배포 성공 여부, 배포된 app_groups)

        """
        # Note: Console output may interleave in parallel mode
        # For dry-run, we just return True with original app_groups
        if self.dry_run:
            return (True, phase_config.app_groups)

        return self._deploy_phase(phase_name, phase_config, workspace)

    def _deploy_phase(
        self,
        phase_name: str,
        phase_config: PhaseReference,
        workspace: UnifiedConfig,
    ) -> tuple[bool, list[str]]:
        """Deploy a single phase.

        Args:
            phase_name: Phase name
            phase_config: Phase configuration
            workspace: Workspace configuration

        Returns:
            tuple[bool, list[str]]: (배포 성공 여부, 배포된 app_groups 목록)

        """
        # Handle phases with inline apps (no source file)
        if not phase_config.source:
            # Inline apps deployment
            self._start_phase_tracking(phase_name)

            if self.dry_run:
                self.console.print(
                    f"  [yellow]🔍 [DRY-RUN] Deploying {len(phase_config.apps)} inline apps[/yellow]"
                )
                self._complete_phase_tracking(
                    phase_name, True, completed_app_groups=len(phase_config.apps)
                )
                return (True, list(phase_config.apps.keys()))

            # TODO: Implement inline apps deployment
            self.console.print(
                f"  [yellow]⚠️  Inline apps deployment not yet implemented[/yellow]"
            )
            self._complete_phase_tracking(phase_name, False, "Inline apps not supported yet")
            return (False, list(phase_config.apps.keys()))

        source_path = self.workspace_dir / phase_config.source
        base_dir = source_path.parent

        # Check if source is a nested workspace (sbkube.yaml with phases) or app config (with apps)
        if source_path.name.endswith('.yaml') and source_path.exists():
            try:
                nested_data = load_config_file(str(source_path))
                if 'phases' in nested_data:
                    # This is a nested workspace - deploy recursively
                    self.console.print(
                        f"  [magenta]🔄 Nested workspace detected: {source_path.name}[/magenta]"
                    )
                    nested_workspace = UnifiedConfig(**nested_data)
                    nested_phases = list(nested_workspace.phases.keys())

                    # Start phase tracking for this phase
                    self._start_phase_tracking(phase_name)

                    # Build inherited settings to pass to nested workspace
                    nested_inherited_settings = {
                        "helm_repos": {
                            **self.inherited_settings.get("helm_repos", {}),
                            **(workspace.settings.helm_repos or {}),
                        },
                        "oci_registries": {
                            **self.inherited_settings.get("oci_registries", {}),
                            **(workspace.settings.oci_registries or {}),
                        },
                        "git_repos": {
                            **self.inherited_settings.get("git_repos", {}),
                            **(workspace.settings.git_repos or {}),
                        },
                        "kubeconfig": workspace.settings.kubeconfig or self.inherited_settings.get("kubeconfig"),
                        "kubeconfig_context": workspace.settings.kubeconfig_context or self.inherited_settings.get("kubeconfig_context"),
                    }

                    # Create nested deployer
                    nested_deployer = WorkspaceDeployCommand(
                        workspace_file=str(source_path),
                        phase=None,
                        parallel=self.parallel,
                        parallel_apps=self.parallel_apps,
                        dry_run=self.dry_run,
                        force=self.force,
                        skip_validation=True,  # Already validated parent
                        inherited_settings=nested_inherited_settings,
                    )

                    # Execute nested workspace
                    success = nested_deployer._execute_phases(
                        nested_workspace, nested_workspace.get_phase_order()
                    )

                    # Complete phase tracking
                    self._complete_phase_tracking(
                        phase_name, success, completed_app_groups=len(nested_phases)
                    )
                    return (success, nested_phases)

                elif 'apps' in nested_data and nested_data['apps']:
                    # This is an app config (sbkube.yaml with apps) - deploy using ApplyCommand
                    self.console.print(
                        f"  [cyan]📦 App config detected: {source_path.name}[/cyan]"
                    )
                    nested_config = UnifiedConfig(**nested_data)
                    app_names = list(nested_config.apps.keys())
                    enabled_apps = [
                        name for name, app in nested_config.apps.items()
                        if app.enabled
                    ]

                    if not enabled_apps:
                        self.console.print(
                            f"  [yellow]⚠️  No enabled apps in {source_path.name}[/yellow]"
                        )
                        self._start_phase_tracking(phase_name)
                        self._complete_phase_tracking(phase_name, True, completed_app_groups=0)
                        return (True, [])

                    self.console.print(
                        f"  [cyan]   Apps: {', '.join(enabled_apps)}[/cyan]"
                    )

                    # Start phase tracking for this phase
                    self._start_phase_tracking(phase_name)

                    if self.dry_run:
                        self.console.print(
                            f"  [yellow]🔍 [DRY-RUN] Would deploy {len(enabled_apps)} app(s)[/yellow]"
                        )
                        self._complete_phase_tracking(
                            phase_name, True, completed_app_groups=len(enabled_apps)
                        )
                        return (True, enabled_apps)

                    # Deploy apps using ApplyCommand
                    from sbkube.commands.apply import ApplyCommand

                    # Build inherited settings: merge parent's inherited with current workspace
                    inherited_settings = {
                        "helm_repos": {
                            **self.inherited_settings.get("helm_repos", {}),
                            **(workspace.settings.helm_repos or {}),
                        },
                        "oci_registries": {
                            **self.inherited_settings.get("oci_registries", {}),
                            **(workspace.settings.oci_registries or {}),
                        },
                        "git_repos": {
                            **self.inherited_settings.get("git_repos", {}),
                            **(workspace.settings.git_repos or {}),
                        },
                        "kubeconfig": workspace.settings.kubeconfig or self.inherited_settings.get("kubeconfig"),
                        "kubeconfig_context": workspace.settings.kubeconfig_context or self.inherited_settings.get("kubeconfig_context"),
                    }

                    try:
                        apply_cmd = ApplyCommand(
                            config_file=str(source_path),
                            dry_run=self.dry_run,
                            force=self.force,
                            parallel=self.parallel_apps,
                            inherited_settings=inherited_settings,
                        )
                        success = apply_cmd.execute()
                        self._complete_phase_tracking(
                            phase_name,
                            success,
                            completed_app_groups=len(enabled_apps) if success else 0,
                        )
                        return (success, enabled_apps)
                    except Exception as e:
                        self.console.print(
                            f"  [red]❌ App deployment failed: {e}[/red]"
                        )
                        self._complete_phase_tracking(phase_name, False, str(e))
                        return (False, [])

            except Exception as e:
                self.console.print(
                    f"  [yellow]⚠️  Could not parse nested config: {e}[/yellow]"
                )
                # Fall through to normal processing

        # Auto-discover app_groups if not specified (legacy config.yaml support)
        app_groups = list(phase_config.app_groups)
        if not app_groups:
            from sbkube.utils.common import find_all_app_dirs

            # Try sbkube.yaml first, then config.yaml for backwards compatibility
            discovered_dirs = find_all_app_dirs(base_dir, "sbkube.yaml")
            if not discovered_dirs:
                discovered_dirs = find_all_app_dirs(base_dir, "config.yaml")
            if discovered_dirs:
                app_groups = [d.name for d in discovered_dirs]
                self.console.print(
                    f"  [cyan]📂 Auto-discovered {len(app_groups)} app group(s): "
                    f"{', '.join(app_groups)}[/cyan]"
                )
            else:
                self.console.print(
                    f"  [yellow]⚠️  No app groups found in {base_dir}[/yellow]"
                )

        # Start phase tracking
        self._start_phase_tracking(phase_name)

        if self.dry_run:
            self.console.print("  [yellow]🔍 [DRY-RUN] sbkube apply[/yellow]")
            self.console.print(f"     --base-dir {base_dir}")
            self.console.print(f"     --source {source_path.name}")
            for group in app_groups:
                self.console.print(f"     --app-dir {group}")
            # Complete phase tracking (dry-run is always success)
            self._complete_phase_tracking(
                phase_name, True, completed_app_groups=len(app_groups)
            )
            return (True, app_groups)

        # 실제 배포: sbkube apply 명령 호출
        completed_app_groups = 0

        # Build inherited settings: merge parent's inherited with current workspace
        inherited_settings = {
            "helm_repos": {
                **self.inherited_settings.get("helm_repos", {}),
                **(workspace.settings.helm_repos or {}),
            },
            "oci_registries": {
                **self.inherited_settings.get("oci_registries", {}),
                **(workspace.settings.oci_registries or {}),
            },
            "git_repos": {
                **self.inherited_settings.get("git_repos", {}),
                **(workspace.settings.git_repos or {}),
            },
            "kubeconfig": workspace.settings.kubeconfig or self.inherited_settings.get("kubeconfig"),
            "kubeconfig_context": workspace.settings.kubeconfig_context or self.inherited_settings.get("kubeconfig_context"),
        }

        try:
            from sbkube.commands.apply import ApplyCommand

            # Parallel apps mode: execute app_groups in parallel within each level
            if self.parallel_apps:
                # Use phase_config.get_app_group_order() if app_groups were specified,
                # otherwise use auto-discovered app_groups as a single level
                if phase_config.app_groups:
                    app_group_levels = phase_config.get_app_group_order()
                else:
                    # Auto-discovered: no deps info, treat as single parallel level
                    app_group_levels = [app_groups] if app_groups else []

                self.console.print(
                    f"  [magenta]Parallel mode: {len(app_group_levels)} levels[/magenta]"
                )

                for level_idx, level_groups in enumerate(app_group_levels):
                    if len(level_groups) > 1:
                        self.console.print(
                            f"  [cyan]Level {level_idx + 1}: "
                            f"Deploying {len(level_groups)} app groups in parallel[/cyan]"
                        )
                        success, completed = self._deploy_app_groups_parallel(
                            level_groups, base_dir, source_path, inherited_settings
                        )
                        completed_app_groups += completed
                        if not success:
                            error_msg = f"Level {level_idx + 1} deployment failed"
                            self._complete_phase_tracking(
                                phase_name, False, error_msg, completed_app_groups
                            )
                            return (False, app_groups)
                    else:
                        # Single app group - execute sequentially
                        app_group = level_groups[0]
                        self.console.print(f"  Deploying app group: {app_group}")
                        if not self._deploy_single_app_group(app_group, base_dir, source_path, inherited_settings):
                            error_msg = f"App group '{app_group}' 배포 실패"
                            self._complete_phase_tracking(
                                phase_name, False, error_msg, completed_app_groups
                            )
                            return (False, app_groups)
                        completed_app_groups += 1
            else:
                # Sequential mode: ApplyCommand 생성 및 실행
                for app_group in app_groups:
                    self.console.print(f"  Deploying app group: {app_group}")

                    apply_cmd = ApplyCommand(
                        base_dir=str(base_dir),
                        app_config_dir=app_group,
                        source=source_path.name,
                        dry_run=False,
                        force=self.force,
                        skip_prepare=False,
                        skip_build=False,
                        inherited_settings=inherited_settings,
                    )

                    # Apply 실행
                    result = apply_cmd.execute()

                    if not result:
                        error_msg = f"App group '{app_group}' 배포 실패"
                        logger.error(error_msg)
                        self._complete_phase_tracking(
                            phase_name, False, error_msg, completed_app_groups
                        )
                        return (False, app_groups)

                    completed_app_groups += 1

            self._complete_phase_tracking(phase_name, True, completed_app_groups=completed_app_groups)
            return (True, app_groups)

        except ImportError:
            # ApplyCommand가 없는 경우 subprocess로 실행
            result = self._deploy_phase_subprocess(
                phase_name, phase_config, base_dir, source_path, app_groups
            )
            # For subprocess, we assume all or nothing
            if result:
                self._complete_phase_tracking(
                    phase_name, True, completed_app_groups=len(app_groups)
                )
            else:
                self._complete_phase_tracking(
                    phase_name, False, "Subprocess deployment failed"
                )
            return (result, app_groups)
        except Exception as e:
            error_msg = f"Phase '{phase_name}' 배포 중 오류: {e}"
            logger.error(error_msg)
            self._complete_phase_tracking(phase_name, False, error_msg, completed_app_groups)
            return (False, app_groups)

    def _deploy_single_app_group(
        self,
        app_group: str,
        base_dir: Path,
        source_path: Path,
        inherited_settings: dict | None = None,
    ) -> bool:
        """Deploy a single app group.

        Args:
            app_group: App group name
            base_dir: Base directory for deployment
            source_path: Path to sources.yaml
            inherited_settings: Settings inherited from parent workspace

        Returns:
            bool: True if successful

        """
        from sbkube.commands.apply import ApplyCommand

        apply_cmd = ApplyCommand(
            base_dir=str(base_dir),
            app_config_dir=app_group,
            source=source_path.name,
            dry_run=False,
            force=self.force,
            skip_prepare=False,
            skip_build=False,
            inherited_settings=inherited_settings,
        )

        return apply_cmd.execute()

    def _deploy_app_groups_parallel(
        self,
        app_groups: list[str],
        base_dir: Path,
        source_path: Path,
        inherited_settings: dict | None = None,
    ) -> tuple[bool, int]:
        """Deploy multiple app groups in parallel.

        Args:
            app_groups: List of app group names
            base_dir: Base directory for deployment
            source_path: Path to sources.yaml
            inherited_settings: Settings inherited from parent workspace

        Returns:
            Tuple of (all_success, completed_count)

        """
        results: dict[str, bool] = {}
        completed_count = 0

        with ThreadPoolExecutor(max_workers=self.max_workers) as executor:
            future_to_group = {
                executor.submit(
                    self._deploy_single_app_group,
                    app_group,
                    base_dir,
                    source_path,
                    inherited_settings,
                ): app_group
                for app_group in app_groups
            }

            for future in as_completed(future_to_group):
                app_group = future_to_group[future]
                try:
                    result = future.result()
                    results[app_group] = result
                    if result:
                        completed_count += 1
                        logger.success(f"App group '{app_group}' 배포 완료 (parallel)")
                    else:
                        logger.error(f"App group '{app_group}' 배포 실패 (parallel)")
                except Exception as e:
                    results[app_group] = False
                    logger.error(f"App group '{app_group}' 오류: {e}")

        all_success = all(results.values())
        return all_success, completed_count

    def _start_phase_tracking(self, phase_name: str) -> None:
        """Start tracking for a phase.

        Args:
            phase_name: Phase name

        """
        if phase_name not in self.phase_names:
            return

        if not self.workspace_deployment_id:
            return

        with self.db.get_session() as session:
            tracker = WorkspaceStateTracker(session)
            # Get fresh deployment object from database
            deployment = tracker.get_workspace_deployment(self.workspace_deployment_id)
            if deployment:
                for phase in deployment.phase_deployments:
                    if phase.phase_name == phase_name:
                        tracker.start_phase(phase)
                        break

    def _complete_phase_tracking(
        self,
        phase_name: str,
        success: bool,
        error_message: str | None = None,
        completed_app_groups: int = 0,
    ) -> None:
        """Complete tracking for a phase.

        Args:
            phase_name: Phase name
            success: Whether the phase succeeded
            error_message: Error message if failed
            completed_app_groups: Number of completed app groups

        """
        if phase_name not in self.phase_names:
            return

        if not self.workspace_deployment_id:
            return

        with self.db.get_session() as session:
            tracker = WorkspaceStateTracker(session)
            deployment = tracker.get_workspace_deployment(self.workspace_deployment_id)
            if deployment:
                for phase in deployment.phase_deployments:
                    if phase.phase_name == phase_name:
                        tracker.complete_phase(
                            phase, success, error_message, completed_app_groups
                        )
                        break

    def _deploy_phase_subprocess(
        self,
        phase_name: str,
        phase_config: PhaseReference,
        base_dir: Path,
        source_path: Path,
        app_groups: list[str] | None = None,
    ) -> bool:
        """Deploy phase using subprocess.

        Fallback method when ApplyCommand is not available.

        Args:
            phase_name: Phase name
            phase_config: Phase configuration
            base_dir: Base directory
            source_path: Source file path
            app_groups: List of app groups to deploy (if None, uses phase_config.app_groups)

        Returns:
            bool: 배포 성공 여부

        """
        import subprocess

        # Use provided app_groups or fall back to phase_config
        groups_to_deploy = app_groups if app_groups is not None else phase_config.app_groups

        for app_group in groups_to_deploy:
            self.console.print(f"  Deploying app group: {app_group}")

            cmd = [
                "sbkube",
                "apply",
                "--base-dir",
                str(base_dir),
                "--app-dir",
                app_group,
                "--source",
                source_path.name,
            ]

            if self.force:
                cmd.append("--force")

            try:
                result = subprocess.run(
                    cmd,
                    check=False, capture_output=True,
                    text=True,
                    cwd=str(base_dir),
                )

                if result.returncode != 0:
                    logger.error(f"App group '{app_group}' 배포 실패:")
                    if result.stderr:
                        logger.error(result.stderr)
                    return False

            except subprocess.SubprocessError as e:
                logger.error(f"App group '{app_group}' 배포 중 오류: {e}")
                return False

        return True

    def _print_summary(
        self, workspace: UnifiedConfig, phase_order: list[str]
    ) -> None:
        """Print deployment summary.

        Args:
            workspace: Workspace configuration
            phase_order: Phase execution order

        """
        self.console.print("\n[bold cyan]━━━ Deployment Summary ━━━[/bold cyan]")

        # 결과 테이블
        table = Table(show_header=True, header_style="bold magenta")
        table.add_column("Phase", style="cyan")
        table.add_column("Status", justify="center")
        table.add_column("App Groups", style="green")

        success_count = 0
        fail_count = 0
        skipped_count = 0

        for phase_name in phase_order:
            if phase_name in self.phase_results:
                result = self.phase_results[phase_name]
                groups = ", ".join(result["app_groups"]) if result["app_groups"] else "-"

                if result.get("skipped"):
                    status = "[yellow]⏭ Skipped[/yellow]"
                    skipped_count += 1
                elif result["success"]:
                    status = "[green]✓ Success[/green]"
                    success_count += 1
                else:
                    status = "[red]✗ Failed[/red]"
                    fail_count += 1
            else:
                status = "[dim]- Not run[/dim]"
                phase_config = workspace.phases[phase_name]
                groups = ", ".join(phase_config.app_groups) if phase_config.app_groups else "-"

            table.add_row(phase_name, status, groups)

        self.console.print(table)

        # 전체 결과
        total = success_count + fail_count + skipped_count
        if fail_count == 0:
            skipped_msg = f" ({skipped_count} skipped)" if skipped_count > 0 else ""
            self.console.print(
                f"\n[bold green]✅ Workspace deployment completed: {success_count}/{total} phases succeeded{skipped_msg}[/bold green]"
            )
        else:
            self.console.print(
                f"\n[bold red]❌ Workspace deployment failed: {fail_count}/{total} phases failed[/bold red]"
            )


class WorkspaceStatusCommand:
    """Workspace 상태 조회 명령어."""

    def __init__(
        self,
        workspace_file: str,
        phase: str | None = None,
    ) -> None:
        """Initialize workspace status command.

        Args:
            workspace_file: sbkube.yaml 경로
            phase: 특정 Phase만 조회 (None이면 전체)

        """
        self.workspace_file = Path(workspace_file)
        self.workspace_dir = self.workspace_file.parent
        self.phase = phase
        self.console = Console()

    def execute(self) -> None:
        """Execute workspace status command.

        Raises:
            click.Abort: 조회 실패 시

        """
        logger.heading(f"Workspace Status - {self.workspace_file}")

        # Workspace 로드
        if not self.workspace_file.exists():
            logger.error(f"Workspace 파일을 찾을 수 없습니다: {self.workspace_file}")
            raise click.Abort

        try:
            data = load_config_file(str(self.workspace_file))
            workspace = UnifiedConfig(**data)
        except Exception as e:
            logger.error(f"Workspace 로딩 실패: {e}")
            raise click.Abort

        # 상태 출력
        self._print_workspace_status(workspace)

    def _print_workspace_status(self, workspace: UnifiedConfig) -> None:
        """Print workspace status.

        Args:
            workspace: Workspace configuration

        """
        workspace_name = workspace.metadata.get("name", "unnamed")
        self.console.print(f"\n[bold cyan]━━━ Workspace: {workspace_name} ━━━[/bold cyan]")

        if workspace.metadata.get("description"):
            self.console.print(f"Description: {workspace.metadata['description']}")
        if workspace.metadata.get("environment"):
            self.console.print(f"Environment: {workspace.metadata['environment']}")

        self.console.print(f"API Version: {workspace.apiVersion}")
        self.console.print(f"Total Phases: {len(workspace.phases)}")

        # Phase 상태 테이블
        table = Table(show_header=True, header_style="bold magenta")
        table.add_column("Phase", style="cyan")
        table.add_column("Description")
        table.add_column("Source", style="dim")
        table.add_column("App Groups", style="green")
        table.add_column("Source Exists", justify="center")

        phase_order = workspace.get_phase_order()

        for phase_name in phase_order:
            if self.phase and phase_name != self.phase:
                continue

            phase_config = workspace.phases[phase_name]

            # Handle phases with inline apps (no source)
            if phase_config.source:
                source_path = self.workspace_dir / phase_config.source
                source_exists = "[green]✓[/green]" if source_path.exists() else "[red]✗[/red]"
                source_display = phase_config.source
            else:
                source_exists = "[dim]-[/dim]"
                source_display = f"(inline: {len(phase_config.apps)} apps)"

            app_groups_display = ", ".join(phase_config.app_groups) if phase_config.app_groups else "(auto)"

            table.add_row(
                phase_name,
                phase_config.description or "",
                source_display,
                app_groups_display,
                source_exists,
            )

        self.console.print(table)

        # 실행 순서
        if not self.phase:
            self.console.print(
                f"\n[bold green]Execution Order:[/bold green] {' → '.join(phase_order)}"
            )


@workspace_group.command(name="deploy")
@click.argument(
    "workspace_file",
    type=click.Path(exists=True, dir_okay=False, resolve_path=True),
    default="sbkube.yaml",
)
@click.option(
    "--phase",
    "-p",
    type=str,
    default=None,
    help="특정 Phase만 배포 (의존성 Phase 포함)",
)
@click.option(
    "--dry-run",
    is_flag=True,
    help="실제 배포 없이 시뮬레이션",
)
@click.option(
    "--force",
    is_flag=True,
    help="이전 상태 무시하고 강제 배포",
)
@click.option(
    "--skip-validation",
    is_flag=True,
    help="파일 존재 검증 건너뛰기",
)
@click.option(
    "--parallel",
    is_flag=True,
    help="독립적인 Phase들을 병렬로 실행",
)
@click.option(
    "--parallel-apps",
    is_flag=True,
    help="Phase 내 App groups를 병렬로 실행 (app_group_deps로 의존성 정의)",
)
@click.option(
    "--max-workers",
    type=int,
    default=4,
    help="최대 병렬 워커 수 (기본: 4)",
)
@click.option("-v", "--verbose", count=True, help="로깅 상세도 (-v: 정보, -vv: 상세)")
@click.option("--debug", is_flag=True, help="디버그 로그 출력")
@click.pass_context
def deploy_cmd(
    ctx: click.Context,
    workspace_file: str,
    phase: str | None,
    dry_run: bool,
    force: bool,
    skip_validation: bool,
    parallel: bool,
    parallel_apps: bool,
    max_workers: int,
    verbose: int,
    debug: bool,
) -> None:
    """Workspace를 배포합니다.

    Phase 의존성 순서대로 각 Phase를 배포합니다.
    --parallel 옵션 사용 시 의존성이 없는 Phase들을 동시에 실행합니다.
    --parallel-apps 옵션 사용 시 Phase 내 App groups를 병렬로 실행합니다.

    Examples:
        # 전체 workspace 배포
        sbkube workspace deploy

        # 특정 Phase만 배포 (의존성 Phase 포함)
        sbkube workspace deploy --phase p2-data

        # Dry-run 모드
        sbkube workspace deploy --dry-run

        # 강제 재배포
        sbkube workspace deploy --force

        # Phase 병렬 실행
        sbkube workspace deploy --parallel --max-workers 4

        # App group 병렬 실행
        sbkube workspace deploy --parallel-apps --max-workers 8

        # 전체 병렬 (Phase + App groups)
        sbkube workspace deploy --parallel --parallel-apps --max-workers 4

    """
    ctx.ensure_object(dict)
    ctx.obj["verbose"] = verbose
    ctx.obj["debug"] = debug
    setup_logging_from_context(ctx)

    deploy_command = WorkspaceDeployCommand(
        workspace_file=workspace_file,
        phase=phase,
        dry_run=dry_run,
        force=force,
        skip_validation=skip_validation,
        parallel=parallel,
        parallel_apps=parallel_apps,
        max_workers=max_workers,
    )

    success = deploy_command.execute()
    if not success:
        raise click.Abort


@workspace_group.command(name="status")
@click.argument(
    "workspace_file",
    type=click.Path(exists=True, dir_okay=False, resolve_path=True),
    default="sbkube.yaml",
)
@click.option(
    "--phase",
    "-p",
    type=str,
    default=None,
    help="특정 Phase만 조회",
)
@click.option("-v", "--verbose", count=True, help="로깅 상세도 (-v: 정보, -vv: 상세)")
@click.option("--debug", is_flag=True, help="디버그 로그 출력")
@click.pass_context
def status_cmd(
    ctx: click.Context,
    workspace_file: str,
    phase: str | None,
    verbose: int,
    debug: bool,
) -> None:
    """Workspace 상태를 조회합니다.

    Examples:
        # 전체 workspace 상태
        sbkube workspace status

        # 특정 Phase 상태
        sbkube workspace status --phase p1-infra

    """
    ctx.ensure_object(dict)
    ctx.obj["verbose"] = verbose
    ctx.obj["debug"] = debug
    setup_logging_from_context(ctx)

    status_command = WorkspaceStatusCommand(
        workspace_file=workspace_file,
        phase=phase,
    )
    status_command.execute()


class WorkspaceHistoryCommand:
    """Workspace 배포 히스토리 조회 명령어."""

    def __init__(
        self,
        workspace_name: str | None = None,
        deployment_id: str | None = None,
        limit: int = 10,
    ) -> None:
        """Initialize workspace history command.

        Args:
            workspace_name: 특정 workspace 이름으로 필터링
            deployment_id: 특정 배포 ID 상세 조회
            limit: 조회할 최대 배포 수

        """
        self.workspace_name = workspace_name
        self.deployment_id = deployment_id
        self.limit = limit
        self.console = Console()
        self.db = DeploymentDatabase()

    def execute(self) -> None:
        """Execute workspace history command."""
        with self.db.get_session() as session:
            tracker = WorkspaceStateTracker(session)

            if self.deployment_id:
                # 특정 배포 상세 조회
                self._show_deployment_detail(tracker)
            else:
                # 배포 목록 조회
                self._show_deployment_list(tracker)

    def _show_deployment_list(self, tracker: WorkspaceStateTracker) -> None:
        """Show workspace deployment history list."""
        deployments = tracker.list_workspace_deployments(
            workspace_name=self.workspace_name,
            limit=self.limit,
        )

        if not deployments:
            self.console.print(
                Panel(
                    "[yellow]배포 히스토리가 없습니다.[/yellow]",
                    title="Workspace History",
                )
            )
            return

        # 테이블 생성
        table = Table(title="Workspace Deployment History", show_lines=True)
        table.add_column("ID", style="cyan", no_wrap=True)
        table.add_column("Workspace", style="blue")
        table.add_column("Environment", style="magenta")
        table.add_column("Timestamp", style="green")
        table.add_column("Status", style="bold")
        table.add_column("Phases", justify="center")
        table.add_column("Dry-Run", justify="center")

        for d in deployments:
            # 상태에 따른 색상
            status_color = {
                "success": "green",
                "failed": "red",
                "partially_failed": "yellow",
                "in_progress": "cyan",
                "pending": "white",
                "cancelled": "dim",
            }.get(d.status, "white")

            phases_info = f"{d.completed_phases}/{d.total_phases}"
            if d.failed_phases > 0:
                phases_info += f" ([red]{d.failed_phases} failed[/red])"
            if d.skipped_phases > 0:
                phases_info += f" ([yellow]{d.skipped_phases} skipped[/yellow])"

            table.add_row(
                d.workspace_deployment_id[:12],
                d.workspace_name,
                d.environment or "-",
                d.timestamp.strftime("%Y-%m-%d %H:%M:%S"),
                f"[{status_color}]{d.status}[/{status_color}]",
                phases_info,
                "✓" if d.dry_run else "-",
            )

        self.console.print(table)
        self.console.print(
            "\n[dim]Use 'sbkube workspace history --id <ID>' for details[/dim]"
        )

    def _show_deployment_detail(self, tracker: WorkspaceStateTracker) -> None:
        """Show detailed information for a specific deployment."""
        detail = tracker.get_workspace_deployment_detail(self.deployment_id)

        if not detail:
            self.console.print(
                f"[red]배포를 찾을 수 없습니다: {self.deployment_id}[/red]"
            )
            raise click.Abort

        # 상태 색상
        status_color = {
            "success": "green",
            "failed": "red",
            "partially_failed": "yellow",
            "in_progress": "cyan",
        }.get(detail.status, "white")

        # 배포 정보 패널
        info_lines = [
            f"[bold]Workspace:[/bold] {detail.workspace_name}",
            f"[bold]Environment:[/bold] {detail.environment or '-'}",
            f"[bold]File:[/bold] {detail.workspace_file}",
            f"[bold]Status:[/bold] [{status_color}]{detail.status}[/{status_color}]",
            "",
            f"[bold]Started:[/bold] {detail.timestamp.strftime('%Y-%m-%d %H:%M:%S')}",
        ]

        if detail.completed_at:
            duration = (detail.completed_at - detail.timestamp).total_seconds()
            info_lines.append(
                f"[bold]Completed:[/bold] {detail.completed_at.strftime('%Y-%m-%d %H:%M:%S')} "
                f"(duration: {int(duration)}s)"
            )

        if detail.error_message:
            info_lines.append(f"[bold]Error:[/bold] [red]{detail.error_message}[/red]")

        info_lines.extend([
            "",
            f"[bold]Phases:[/bold] {detail.completed_phases}/{detail.total_phases} completed",
            f"[bold]Failed:[/bold] {detail.failed_phases}",
            f"[bold]Skipped:[/bold] {detail.skipped_phases}",
            f"[bold]Dry-Run:[/bold] {'Yes' if detail.dry_run else 'No'}",
            f"[bold]Force:[/bold] {'Yes' if detail.force else 'No'}",
        ])

        if detail.sbkube_version:
            info_lines.append(f"[bold]SBKube Version:[/bold] {detail.sbkube_version}")
        if detail.operator:
            info_lines.append(f"[bold]Operator:[/bold] {detail.operator}")

        self.console.print(
            Panel(
                "\n".join(info_lines),
                title=f"Deployment {detail.workspace_deployment_id}",
            )
        )

        # Phase 테이블
        if detail.phases:
            table = Table(title="Phase Deployments", show_lines=True)
            table.add_column("Order", justify="center", style="dim")
            table.add_column("Phase", style="cyan")
            table.add_column("Status", style="bold")
            table.add_column("Duration", justify="right")
            table.add_column("App Groups", justify="center")
            table.add_column("Error")

            for phase in detail.phases:
                phase_status_color = {
                    "success": "green",
                    "failed": "red",
                    "skipped": "yellow",
                    "in_progress": "cyan",
                    "pending": "dim",
                }.get(phase.status, "white")

                duration_str = f"{phase.duration_seconds}s" if phase.duration_seconds else "-"
                app_groups_str = f"{phase.completed_app_groups}/{phase.total_app_groups}"

                table.add_row(
                    str(phase.execution_order),
                    phase.phase_name,
                    f"[{phase_status_color}]{phase.status}[/{phase_status_color}]",
                    duration_str,
                    app_groups_str,
                    phase.error_message[:50] + "..." if phase.error_message and len(phase.error_message) > 50 else (phase.error_message or "-"),
                )

            self.console.print()
            self.console.print(table)


@workspace_group.command(name="history")
@click.option(
    "--workspace",
    "-w",
    type=str,
    default=None,
    help="특정 workspace 이름으로 필터링",
)
@click.option(
    "--id",
    "deployment_id",
    type=str,
    default=None,
    help="특정 배포 ID 상세 조회",
)
@click.option(
    "--limit",
    "-n",
    type=int,
    default=10,
    help="조회할 최대 배포 수 (기본: 10)",
)
@click.option("-v", "--verbose", count=True, help="로깅 상세도 (-v: 정보, -vv: 상세)")
@click.option("--debug", is_flag=True, help="디버그 로그 출력")
@click.pass_context
def history_cmd(
    ctx: click.Context,
    workspace: str | None,
    deployment_id: str | None,
    limit: int,
    verbose: int,
    debug: bool,
) -> None:
    """Workspace 배포 히스토리를 조회합니다.

    Examples:
        # 최근 배포 목록 조회
        sbkube workspace history

        # 특정 workspace 배포 히스토리
        sbkube workspace history --workspace my-workspace

        # 특정 배포 상세 조회
        sbkube workspace history --id abc123

        # 최근 20개 조회
        sbkube workspace history --limit 20

    """
    ctx.ensure_object(dict)
    ctx.obj["verbose"] = verbose
    ctx.obj["debug"] = debug
    setup_logging_from_context(ctx)

    history_command = WorkspaceHistoryCommand(
        workspace_name=workspace,
        deployment_id=deployment_id,
        limit=limit,
    )
    history_command.execute()


class WorkspaceCleanupCommand:
    """Workspace 배포 히스토리 정리 명령어."""

    def __init__(
        self,
        max_age_days: int = 30,
        keep_per_workspace: int = 10,
        deployment_id: str | None = None,
        dry_run: bool = False,
    ) -> None:
        """Initialize workspace cleanup command.

        Args:
            max_age_days: 이 일수보다 오래된 배포 삭제
            keep_per_workspace: workspace당 유지할 최소 배포 수
            deployment_id: 특정 배포 ID 삭제
            dry_run: 실제 삭제 없이 시뮬레이션

        """
        self.max_age_days = max_age_days
        self.keep_per_workspace = keep_per_workspace
        self.deployment_id = deployment_id
        self.dry_run = dry_run
        self.console = Console()
        self.db = DeploymentDatabase()

    def execute(self) -> int:
        """Execute workspace cleanup command.

        Returns:
            Number of deployments deleted (or would be deleted in dry-run)

        """
        logger.heading("Workspace History Cleanup")

        if self.dry_run:
            self.console.print(
                Panel(
                    "[yellow]DRY-RUN MODE[/yellow]: 실제 삭제가 실행되지 않습니다.",
                    style="yellow",
                )
            )

        with self.db.get_session() as session:
            tracker = WorkspaceStateTracker(session)

            if self.deployment_id:
                # 특정 배포 삭제
                return self._delete_specific(tracker)
            # 자동 정리
            return self._cleanup_stale(tracker)

    def _delete_specific(self, tracker: WorkspaceStateTracker) -> int:
        """Delete a specific deployment."""
        deployment = tracker.get_workspace_deployment(self.deployment_id)

        if not deployment:
            self.console.print(
                f"[red]배포를 찾을 수 없습니다: {self.deployment_id}[/red]"
            )
            return 0

        self.console.print(f"삭제 대상: {deployment.workspace_deployment_id}")
        self.console.print(f"  Workspace: {deployment.workspace_name}")
        self.console.print(f"  Timestamp: {deployment.timestamp}")
        self.console.print(f"  Status: {deployment.status}")

        if self.dry_run:
            self.console.print("\n[yellow]DRY-RUN: 삭제되지 않았습니다.[/yellow]")
            return 1

        if tracker.delete_deployment(self.deployment_id):
            logger.success(f"배포 삭제 완료: {self.deployment_id}")
            return 1
        return 0

    def _cleanup_stale(self, tracker: WorkspaceStateTracker) -> int:
        """Clean up stale deployments."""
        self.console.print("정리 기준:")
        self.console.print(f"  - {self.max_age_days}일 이상 오래된 배포")
        self.console.print(f"  - workspace당 최근 {self.keep_per_workspace}개 유지")
        self.console.print("  - 1일 이상 된 in_progress 상태 배포")

        if self.dry_run:
            # Dry-run: 삭제될 항목 미리보기
            from sbkube.models.workspace_state import (
                WorkspaceDeployment,
            )

            cutoff_date = tracker.session.query(WorkspaceDeployment).first()
            if not cutoff_date:
                self.console.print("\n[dim]정리할 배포가 없습니다.[/dim]")
                return 0

            # 실제 cleanup 로직을 시뮬레이션
            self.console.print("\n[yellow]DRY-RUN: 삭제되지 않았습니다.[/yellow]")
            self.console.print("[dim]실제 삭제하려면 --dry-run 옵션을 제거하세요.[/dim]")
            return 0

        deleted = tracker.cleanup_stale_deployments(
            max_age_days=self.max_age_days,
            keep_per_workspace=self.keep_per_workspace,
        )

        if deleted > 0:
            logger.success(f"{deleted}개의 배포 기록이 정리되었습니다.")
        else:
            self.console.print("[dim]정리할 배포가 없습니다.[/dim]")

        return deleted


@workspace_group.command(name="cleanup")
@click.option(
    "--max-age",
    type=int,
    default=30,
    help="이 일수보다 오래된 배포 삭제 (기본: 30)",
)
@click.option(
    "--keep",
    type=int,
    default=10,
    help="workspace당 유지할 최소 배포 수 (기본: 10)",
)
@click.option(
    "--id",
    "deployment_id",
    type=str,
    default=None,
    help="특정 배포 ID 삭제",
)
@click.option(
    "--dry-run",
    is_flag=True,
    help="실제 삭제 없이 시뮬레이션",
)
@click.option("-v", "--verbose", count=True, help="로깅 상세도 (-v: 정보, -vv: 상세)")
@click.option("--debug", is_flag=True, help="디버그 로그 출력")
@click.pass_context
def cleanup_cmd(
    ctx: click.Context,
    max_age: int,
    keep: int,
    deployment_id: str | None,
    dry_run: bool,
    verbose: int,
    debug: bool,
) -> None:
    """오래된 배포 히스토리를 정리합니다.

    Examples:
        # 기본 정리 (30일 이상, workspace당 10개 유지)
        sbkube workspace cleanup

        # 커스텀 설정
        sbkube workspace cleanup --max-age 7 --keep 5

        # 특정 배포 삭제
        sbkube workspace cleanup --id abc123

        # Dry-run 모드
        sbkube workspace cleanup --dry-run

    """
    ctx.ensure_object(dict)
    ctx.obj["verbose"] = verbose
    ctx.obj["debug"] = debug
    setup_logging_from_context(ctx)

    cleanup_command = WorkspaceCleanupCommand(
        max_age_days=max_age,
        keep_per_workspace=keep,
        deployment_id=deployment_id,
        dry_run=dry_run,
    )
    cleanup_command.execute()
