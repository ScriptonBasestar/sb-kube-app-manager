"""
Hook Executor for SBKube.

명령어 및 앱별 훅 실행을 담당하는 유틸리티 모듈.
"""

import os
import shlex
import subprocess
from pathlib import Path
from typing import Literal

from rich.console import Console

from sbkube.exceptions import SbkubeError

console = Console()

HookType = Literal[
    "pre_prepare",
    "post_prepare",
    "pre_build",
    "post_build",
    "pre_template",
    "post_template",
    "pre_deploy",
    "post_deploy",
    "on_deploy_failure",
]

CommandHookPhase = Literal["pre", "post", "on_failure"]


class HookExecutionError(SbkubeError):
    """Hook 실행 중 발생한 오류."""

    pass


class HookExecutor:
    """
    Hook 실행 관리자.

    명령어 수준 및 앱 수준의 훅을 실행하고 결과를 처리합니다.
    """

    def __init__(
        self,
        base_dir: Path,
        work_dir: Path | None = None,
        env: dict[str, str] | None = None,
        dry_run: bool = False,
        timeout: int = 300,
    ):
        """
        HookExecutor 초기화.

        Args:
            base_dir: 프로젝트 루트 디렉토리 (BASE_DIR)
            work_dir: 훅 스크립트를 실행할 작업 디렉토리 (일반적으로 APP_CONFIG_DIR)
                     None이면 base_dir 사용. 상대 경로는 이 디렉토리 기준으로 해석됨.
            env: 추가 환경변수
            dry_run: dry-run 모드 활성화 여부
            timeout: 명령어 실행 타임아웃 (초)

        Example:
            # redis_dir/config.yaml이 있는 경우
            executor = HookExecutor(
                base_dir=Path("/project"),           # 프로젝트 루트
                work_dir=Path("/project/redis_dir"), # 훅 실행 위치
            )
            # 훅에서 "./scripts/pre-deploy.sh" 실행 시
            # → /project/redis_dir/scripts/pre-deploy.sh 실행
        """
        self.base_dir = base_dir
        self.work_dir = work_dir or base_dir
        self.env = env or {}
        self.dry_run = dry_run
        self.timeout = timeout

    def execute_command_hooks(
        self,
        hook_config: dict,
        hook_phase: CommandHookPhase,
        command_name: str = "",
    ) -> bool:
        """
        명령어 수준 훅 실행.

        Args:
            hook_config: hooks.{command} 설정 (CommandHooks 인스턴스의 dict 형태)
            hook_phase: "pre", "post", "on_failure"
            command_name: 명령어 이름 (로깅용)

        Returns:
            성공 여부 (모든 명령어가 성공하면 True)
        """
        if not hook_config or hook_phase not in hook_config:
            return True

        commands = hook_config.get(hook_phase, [])
        if not commands:
            return True

        console.print(
            f"[cyan]🪝 Executing {hook_phase}-hook for command '{command_name}'...[/cyan]"
        )

        for cmd in commands:
            if not self._execute_single_command(cmd, hook_phase):
                return False

        console.print(f"[green]✅ {hook_phase}-hook completed successfully[/green]")
        return True

    def execute_app_hook(
        self,
        app_name: str,
        app_hooks: dict | None,
        hook_type: HookType,
        context: dict | None = None,
    ) -> bool:
        """
        앱별 훅 실행.

        Args:
            app_name: 앱 이름
            app_hooks: app.hooks 설정 (AppHooks 인스턴스의 dict 형태)
            hook_type: "pre_deploy", "post_deploy" 등
            context: 추가 컨텍스트 (namespace, release_name 등)

        Returns:
            성공 여부
        """
        if not app_hooks or hook_type not in app_hooks:
            return True

        commands = app_hooks.get(hook_type, [])
        if not commands:
            return True

        console.print(
            f"[cyan]🪝 Executing {hook_type} hook for app '{app_name}'...[/cyan]"
        )

        # 컨텍스트를 환경변수로 주입
        hook_env = self.env.copy()
        hook_env["SBKUBE_APP_NAME"] = app_name
        if context:
            hook_env.update(
                {f"SBKUBE_{k.upper()}": str(v) for k, v in context.items()}
            )

        for cmd in commands:
            if not self._execute_single_command(cmd, hook_type, hook_env):
                return False

        console.print(
            f"[green]✅ {hook_type} hook for '{app_name}' completed successfully[/green]"
        )
        return True

    def _execute_single_command(
        self,
        command: str,
        hook_type: str,
        env: dict | None = None,
    ) -> bool:
        """
        단일 명령어 실행.

        Args:
            command: 실행할 명령어
            hook_type: 훅 타입 (로깅용)
            env: 추가 환경변수

        Returns:
            성공 여부
        """
        if self.dry_run:
            console.print(
                f"[yellow]🔍 [DRY-RUN] Would execute hook: {command}[/yellow]"
            )
            return True

        console.print(f"  ▶ Running: [dim]{command}[/dim]")

        try:
            # 환경변수 병합
            full_env = os.environ.copy()
            full_env.update(self.env)
            if env:
                full_env.update(env)

            result = subprocess.run(
                shlex.split(command),
                shell=False,
                cwd=self.work_dir,
                env=full_env,
                capture_output=True,
                text=True,
                timeout=self.timeout,
            )

            if result.returncode != 0:
                console.print(f"[red]❌ Hook command failed: {command}[/red]")
                console.print(f"[red]   Exit code: {result.returncode}[/red]")
                if result.stderr:
                    console.print(f"[red]   Error: {result.stderr.strip()}[/red]")
                return False

            if result.stdout:
                for line in result.stdout.strip().split("\n"):
                    console.print(f"    {line}")

            return True

        except subprocess.TimeoutExpired:
            console.print(
                f"[red]❌ Hook command timed out (>{self.timeout}s): {command}[/red]"
            )
            return False

        except Exception as e:
            console.print(f"[red]❌ Hook execution error: {e}[/red]")
            return False
