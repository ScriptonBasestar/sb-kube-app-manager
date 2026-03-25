"""Hook Executor for SBKube.

명령어 및 앱별 훅 실행을 담당하는 유틸리티 모듈.
"""

import os
import shlex
import subprocess
from pathlib import Path
from typing import Literal

from sbkube.exceptions import SbkubeError
from sbkube.utils.cluster_config import apply_cluster_config_to_command
from sbkube.utils.common import run_command
from sbkube.utils.logger import logger
from sbkube.utils.security import is_exec_allowed

# Use logger's console so it respects --format (quiet in non-human modes)
console = logger.console

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


class HookExecutor:
    """Hook 실행 관리자.

    명령어 수준 및 앱 수준의 훅을 실행하고 결과를 처리합니다.
    """

    def __init__(
        self,
        base_dir: Path,
        work_dir: Path | None = None,
        env: dict[str, str] | None = None,
        dry_run: bool = False,
        timeout: int = 300,
        kubeconfig: str | None = None,
        context: str | None = None,
        namespace: str | None = None,
    ) -> None:
        """HookExecutor 초기화.

        Args:
            base_dir: 프로젝트 루트 디렉토리 (BASE_DIR)
            work_dir: 훅 스크립트를 실행할 작업 디렉토리 (일반적으로 APP_CONFIG_DIR)
                     None이면 base_dir 사용. 상대 경로는 이 디렉토리 기준으로 해석됨.
            env: 추가 환경변수
            dry_run: dry-run 모드 활성화 여부
            timeout: 명령어 실행 타임아웃 (초)
            kubeconfig: kubeconfig 파일 경로 (manifests 배포용)
            context: kubectl context (manifests 배포용)
            namespace: 기본 namespace (manifests 배포용)

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
        self.kubeconfig = kubeconfig
        self.context = context
        self.namespace = namespace

    def execute_command_hooks(
        self,
        hook_config: dict,
        hook_phase: CommandHookPhase,
        command_name: str = "",
    ) -> bool:
        """명령어 수준 훅 실행.

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
        """앱별 훅 실행.

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
            hook_env.update({f"SBKUBE_{k.upper()}": str(v) for k, v in context.items()})

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
        """단일 명령어 실행.

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

        if not is_exec_allowed():
            console.print(
                "[red]❌ Hook execution disabled (SBKUBE_ALLOW_EXEC=false)[/red]"
            )
            return False

        console.print(f"  ▶ Running: [dim]{command}[/dim]")

        try:
            # 환경변수 병합
            full_env = os.environ.copy()
            full_env.update(self.env)
            if env:
                full_env.update(env)

            result = subprocess.run(
                shlex.split(command),
                check=False,
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

    def execute_app_hook_with_manifests(
        self,
        app_name: str,
        app_hooks: dict | None,
        hook_type: HookType,
        context: dict | None = None,
    ) -> bool:
        """앱별 훅 실행 (shell 명령어 + manifests 지원).

        Phase 1: Manifests 지원 - shell 명령어와 manifests를 모두 실행합니다.

        Args:
            app_name: 앱 이름
            app_hooks: app.hooks 설정 (AppHooks 인스턴스의 dict 형태)
            hook_type: "pre_deploy", "post_deploy" 등
            context: 추가 컨텍스트 (namespace, release_name 등)

        Returns:
            성공 여부

        """
        if not app_hooks:
            return True

        success = True

        # 1. Shell 명령어 hooks 실행 (기존)
        if hook_type in app_hooks:
            commands = app_hooks.get(hook_type, [])
            if commands:
                success = self.execute_app_hook(app_name, app_hooks, hook_type, context)
                if not success:
                    return False

        # 2. Manifests hooks 실행 (신규 - Phase 1)
        manifests_hook_type = f"{hook_type}_manifests"
        if manifests_hook_type in app_hooks:
            manifests = app_hooks.get(manifests_hook_type, [])
            if manifests:
                console.print(
                    f"[cyan]🪝 Deploying {manifests_hook_type} manifests for app '{app_name}'...[/cyan]"
                )
                success = self._deploy_manifests(
                    app_name=app_name,
                    manifests=manifests,
                    namespace=context.get("namespace") if context else None,
                )
                if not success:
                    return False

                console.print(
                    f"[green]✅ {manifests_hook_type} manifests deployed for '{app_name}'[/green]"
                )

        return success

    def _deploy_manifests(
        self,
        app_name: str,
        manifests: list[str],
        namespace: str | None = None,
    ) -> bool:
        """Manifests 파일 배포 (kubectl apply).

        YamlApp 배포 로직과 유사하게 처리합니다.

        Args:
            app_name: 앱 이름 (로깅용)
            manifests: 배포할 YAML 파일 경로 리스트
            namespace: 배포 대상 namespace (None이면 기본값 또는 manifest 내 지정)

        Returns:
            성공 여부

        """
        # namespace 결정 (우선순위: 파라미터 > 초기화 시 설정)
        target_namespace = namespace or self.namespace

        for yaml_file in manifests:
            # 경로 해석: 절대경로면 그대로, 상대경로면 work_dir 기준
            yaml_path = Path(yaml_file)
            if not yaml_path.is_absolute():
                yaml_path = self.work_dir / yaml_file

            if not yaml_path.exists():
                console.print(f"[red]❌ Manifest file not found: {yaml_path}[/red]")
                return False

            # kubectl apply 명령어 구성
            cmd = ["kubectl", "apply", "-f", str(yaml_path)]

            if target_namespace:
                cmd.extend(["--namespace", target_namespace])

            if self.dry_run:
                cmd.append("--dry-run=client")
                cmd.append("--validate=false")

            # Apply cluster configuration (kubeconfig, context)
            cmd = apply_cluster_config_to_command(cmd, self.kubeconfig, self.context)

            console.print(f"  Applying manifest: {yaml_file}")

            # 명령어 실행
            return_code, stdout, stderr = run_command(cmd)

            if return_code != 0:
                console.print(f"[red]❌ Failed to apply manifest: {yaml_file}[/red]")
                if stderr:
                    console.print(f"[red]   Error: {stderr.strip()}[/red]")
                return False

            # 성공 메시지 출력
            if stdout:
                for line in stdout.strip().split("\n"):
                    if line.strip():
                        console.print(f"    {line}")

        return True

    # ========================================================================
    # Phase 2: Type System - Hook Tasks 처리
    # ========================================================================

    def execute_hook_tasks(
        self,
        app_name: str,
        tasks: list,
        hook_type: str,
        context: dict | None = None,
    ) -> bool:
        """Phase 2/3: Hook Tasks 실행 (타입별 처리 + validation, dependency, rollback).

        Args:
            app_name: 앱 이름
            tasks: HookTask 리스트
            hook_type: "pre_deploy", "post_deploy" 등
            context: 추가 컨텍스트

        Returns:
            성공 여부

        """
        if not tasks:
            return True

        console.print(
            f"[cyan]🪝 Executing {len(tasks)} {hook_type} tasks for app '{app_name}'...[/cyan]"
        )

        completed_tasks: set[str] = set()

        for task in tasks:
            task_dict = task if isinstance(task, dict) else task.model_dump()
            task_name = task_dict.get("name", "unnamed-task")

            # Phase 3: Dependency 검증
            if not self._check_task_dependencies(
                app_name=app_name,
                task=task_dict,
                completed_tasks=completed_tasks,
                context=context,
            ):
                # Dependency 실패 시 rollback 실행
                self._execute_rollback(app_name, task_dict, context)
                return False

            # Task 실행
            task_success = self._execute_single_task(
                app_name=app_name,
                task=task_dict,
                context=context,
            )

            if not task_success:
                # Task 실행 실패 시 rollback 실행
                self._execute_rollback(app_name, task_dict, context)
                return False

            # Phase 3: Validation 검증
            if not self._validate_task_result(
                app_name=app_name,
                task=task_dict,
                context=context,
            ):
                # Validation 실패 시 rollback 실행
                self._execute_rollback(app_name, task_dict, context)
                return False

            # Task 성공적으로 완료
            completed_tasks.add(task_name)

        console.print(
            f"[green]✅ All {hook_type} tasks completed for '{app_name}'[/green]"
        )
        return True

    def _execute_single_task(
        self,
        app_name: str,
        task: dict,
        context: dict | None = None,
    ) -> bool:
        """단일 Hook Task 실행 (타입별 분기).

        Args:
            app_name: 앱 이름
            task: HookTask dict (type 필드로 구분)
            context: 추가 컨텍스트

        Returns:
            성공 여부

        """
        task_type = task.get("type")
        task_name = task.get("name", "unnamed")

        console.print(f"  ▶ Task: [bold]{task_name}[/bold] (type: {task_type})")

        if task_type == "manifests":
            return self._execute_manifests_task(app_name, task, context)
        if task_type == "inline":
            return self._execute_inline_task(app_name, task, context)
        if task_type == "command":
            return self._execute_command_task(app_name, task, context)
        console.print(f"[red]❌ Unknown task type: {task_type}[/red]")
        return False

    def _execute_manifests_task(
        self,
        app_name: str,
        task: dict,
        context: dict | None = None,
    ) -> bool:
        """Manifests 타입 Task 실행.

        Phase 1의 _deploy_manifests()를 재사용합니다.

        Args:
            app_name: 앱 이름
            task: ManifestsHookTask dict
            context: 추가 컨텍스트

        Returns:
            성공 여부

        """
        files = task.get("files", [])
        validation = task.get("validation")

        if not files:
            console.print("[yellow]⚠️  No files specified in manifests task[/yellow]")
            return True

        # Phase 1의 _deploy_manifests 재사용
        success = self._deploy_manifests(
            app_name=app_name,
            manifests=files,
            namespace=context.get("namespace") if context else None,
        )

        # Phase 3에서 validation 처리 예정
        if validation and success:
            console.print(f"    [dim](validation: {validation})[/dim]")

        return success

    def _execute_inline_task(
        self,
        app_name: str,
        task: dict,
        context: dict | None = None,
    ) -> bool:
        """Inline 타입 Task 실행.

        YAML 콘텐츠를 임시 파일로 저장하고 kubectl apply 실행.

        Args:
            app_name: 앱 이름
            task: InlineHookTask dict
            context: 추가 컨텍스트

        Returns:
            성공 여부

        """
        import os
        import tempfile

        import yaml

        content = task.get("content")
        if not content:
            console.print("[red]❌ No content specified in inline task[/red]")
            return False

        if self.dry_run:
            console.print("[yellow]🔍 [DRY-RUN] Would apply inline content[/yellow]")
            console.print(
                f"    [dim]{yaml.dump(content, default_flow_style=False)}[/dim]"
            )
            return True

        # 임시 파일 생성
        tmp_path = None
        try:
            with tempfile.NamedTemporaryFile(
                mode="w",
                suffix=".yaml",
                delete=False,
            ) as tmp_file:
                yaml.dump(content, tmp_file, default_flow_style=False)
                tmp_path = tmp_file.name

            # kubectl apply 실행
            target_namespace = (
                context.get("namespace") if context else None or self.namespace
            )

            cmd = ["kubectl", "apply", "-f", tmp_path]
            if target_namespace:
                cmd.extend(["--namespace", target_namespace])

            # Apply cluster configuration
            cmd = apply_cluster_config_to_command(cmd, self.kubeconfig, self.context)

            console.print("    Applying inline content...")

            return_code, stdout, stderr = run_command(cmd)

            if return_code != 0:
                console.print("[red]❌ Failed to apply inline content[/red]")
                if stderr:
                    console.print(f"[red]   Error: {stderr.strip()}[/red]")
                return False

            if stdout:
                for line in stdout.strip().split("\n"):
                    if line.strip():
                        console.print(f"    {line}")

            return True

        except Exception as e:
            console.print(f"[red]❌ Inline task error: {e}[/red]")
            return False

        finally:
            # 임시 파일 삭제
            if tmp_path and os.path.exists(tmp_path):
                os.unlink(tmp_path)

    def _execute_command_task(
        self,
        app_name: str,
        task: dict,
        context: dict | None = None,
    ) -> bool:
        """Command 타입 Task 실행 (retry 및 on_failure 지원).

        Args:
            app_name: 앱 이름
            task: CommandHookTask dict
            context: 추가 컨텍스트

        Returns:
            성공 여부

        """
        import time

        command = task.get("command")
        retry_config = task.get("retry")
        on_failure = task.get("on_failure", "fail")

        if not command:
            console.print("[red]❌ No command specified in command task[/red]")
            return False

        # Retry 설정
        max_attempts = 1
        delay = 0
        if retry_config:
            max_attempts = retry_config.get("max_attempts", 1)
            delay = retry_config.get("delay", 0)

        # 환경변수 설정
        hook_env = self.env.copy()
        hook_env["SBKUBE_APP_NAME"] = app_name
        if context:
            hook_env.update({f"SBKUBE_{k.upper()}": str(v) for k, v in context.items()})

        # Retry 로직
        for attempt in range(1, max_attempts + 1):
            if max_attempts > 1:
                console.print(f"    Attempt {attempt}/{max_attempts}...")

            success = self._execute_single_command(command, "command", hook_env)

            if success:
                return True

            # 실패 처리
            if attempt < max_attempts:
                if delay > 0:
                    console.print(f"    [yellow]Retrying in {delay}s...[/yellow]")
                    time.sleep(delay)
            # 최종 실패
            elif on_failure == "warn":
                console.print(
                    "[yellow]⚠️  Command failed but on_failure=warn, continuing...[/yellow]"
                )
                return True
            elif on_failure == "ignore":
                console.print(
                    "[dim]ℹ️  Command failed but on_failure=ignore, skipping...[/dim]"
                )
                return True
            else:  # fail
                console.print(
                    f"[red]❌ Command failed after {max_attempts} attempts[/red]"
                )
                return False

        return False

    # ========================================================================
    # Phase 3: Validation, Dependency, Rollback
    # ========================================================================

    def _validate_task_result(
        self,
        app_name: str,
        task: dict,
        context: dict | None = None,
    ) -> bool:
        """Task 실행 후 validation 규칙 검증.

        Args:
            app_name: 앱 이름
            task: Task 정의 (validation 필드 포함)
            context: 추가 컨텍스트

        Returns:
            성공 여부

        """
        validation = task.get("validation")
        if not validation:
            return True

        console.print("  [cyan]🔍 Validating task result...[/cyan]")

        kind = validation.get("kind")
        name = validation.get("name")
        namespace = (
            validation.get("namespace")
            or (context.get("namespace") if context else None)
            or self.namespace
        )
        wait_for_ready = validation.get("wait_for_ready", False)
        timeout = validation.get("timeout", 60)
        conditions = validation.get("conditions")

        if not kind:
            console.print(
                "[yellow]⚠️  No kind specified in validation, skipping...[/yellow]"
            )
            return True

        if self.dry_run:
            console.print(f"[yellow]🔍 [DRY-RUN] Would validate {kind}[/yellow]")
            return True

        # kubectl get 명령어 구성
        cmd = ["kubectl", "get", kind.lower()]
        if name:
            cmd.append(name)
        if namespace:
            cmd.extend(["--namespace", namespace])

        cmd = apply_cluster_config_to_command(cmd, self.kubeconfig, self.context)

        # wait_for_ready 처리
        if wait_for_ready:
            # kubectl wait 명령어 사용
            wait_cmd = ["kubectl", "wait", kind.lower()]
            if name:
                wait_cmd.append(name)
            else:
                wait_cmd.append("--all")

            if conditions:
                for condition in conditions:
                    cond_type = condition.get("type", "Ready")
                    cond_status = condition.get("status", "True")
                    wait_cmd.append(f"--for=condition={cond_type}={cond_status}")
            else:
                wait_cmd.append("--for=condition=Ready")

            if namespace:
                wait_cmd.extend(["--namespace", namespace])

            wait_cmd.append(f"--timeout={timeout}s")
            wait_cmd = apply_cluster_config_to_command(
                wait_cmd, self.kubeconfig, self.context
            )

            console.print(
                f"    Waiting for {kind} to be ready (timeout: {timeout}s)..."
            )

            return_code, stdout, stderr = run_command(wait_cmd)
            if return_code != 0:
                console.print(
                    f"[red]❌ Validation failed: {kind} not ready within {timeout}s[/red]"
                )
                if stderr:
                    console.print(f"[red]   Error: {stderr.strip()}[/red]")
                return False

            console.print(f"[green]✅ Validation passed: {kind} is ready[/green]")
            return True
        # 단순 존재 확인
        return_code, _stdout, stderr = run_command(cmd)
        if return_code != 0:
            console.print(f"[red]❌ Validation failed: {kind} not found[/red]")
            if stderr:
                console.print(f"[red]   Error: {stderr.strip()}[/red]")
            return False

        console.print(f"[green]✅ Validation passed: {kind} exists[/green]")
        return True

    def _check_task_dependencies(
        self,
        app_name: str,
        task: dict,
        completed_tasks: set[str],
        context: dict | None = None,
    ) -> bool:
        """Task 실행 전 의존성 검증.

        Args:
            app_name: 앱 이름
            task: Task 정의 (dependency 필드 포함)
            completed_tasks: 완료된 task 이름 집합
            context: 추가 컨텍스트

        Returns:
            성공 여부

        """
        dependency = task.get("dependency")
        if not dependency:
            return True

        # depends_on 검증
        depends_on = dependency.get("depends_on", [])
        if depends_on:
            for dep_task_name in depends_on:
                if dep_task_name not in completed_tasks:
                    console.print(
                        f"[red]❌ Dependency not satisfied: task '{dep_task_name}' must complete first[/red]"
                    )
                    return False

        # wait_for 검증
        wait_for = dependency.get("wait_for")
        if wait_for:
            console.print("  [cyan]⏳ Waiting for external resources...[/cyan]")

            for wait_config in wait_for:
                kind = wait_config.get("kind")
                label_selector = wait_config.get("label_selector")
                name = wait_config.get("name")
                condition = wait_config.get("condition", "Ready")
                timeout = wait_config.get("timeout", 60)
                namespace = (
                    wait_config.get("namespace")
                    or (context.get("namespace") if context else None)
                    or self.namespace
                )

                if not kind:
                    console.print(
                        "[yellow]⚠️  No kind specified in wait_for, skipping...[/yellow]"
                    )
                    continue

                if self.dry_run:
                    console.print(
                        f"[yellow]🔍 [DRY-RUN] Would wait for {kind}[/yellow]"
                    )
                    continue

                # kubectl wait 명령어 구성
                wait_cmd = ["kubectl", "wait", kind.lower()]

                if name:
                    wait_cmd.append(name)
                elif label_selector:
                    wait_cmd.extend(["--selector", label_selector])
                else:
                    wait_cmd.append("--all")

                wait_cmd.append(f"--for=condition={condition}")

                if namespace:
                    wait_cmd.extend(["--namespace", namespace])

                wait_cmd.append(f"--timeout={timeout}s")
                wait_cmd = apply_cluster_config_to_command(
                    wait_cmd, self.kubeconfig, self.context
                )

                console.print(
                    f"    Waiting for {kind} to satisfy condition '{condition}' (timeout: {timeout}s)..."
                )

                return_code, _stdout, stderr = run_command(wait_cmd)
                if return_code != 0:
                    console.print(
                        f"[red]❌ wait_for failed: {kind} condition '{condition}' not met within {timeout}s[/red]"
                    )
                    if stderr:
                        console.print(f"[red]   Error: {stderr.strip()}[/red]")
                    return False

                console.print(
                    f"[green]✅ {kind} condition '{condition}' satisfied[/green]"
                )

        return True

    def _execute_rollback(
        self,
        app_name: str,
        task: dict,
        context: dict | None = None,
    ) -> bool:
        """Task 실패 시 rollback 정책 실행.

        Args:
            app_name: 앱 이름
            task: Task 정의 (rollback 필드 포함)
            context: 추가 컨텍스트

        Returns:
            성공 여부

        """
        rollback = task.get("rollback")
        if not rollback:
            return True

        enabled = rollback.get("enabled", False)
        if not enabled:
            return True

        on_failure = rollback.get("on_failure", "always")

        # manual은 현재 자동 실행 안 함 (나중에 사용자 확인 추가 가능)
        if on_failure == "manual":
            console.print(
                "[yellow]⚠️  Rollback policy is 'manual', skipping automatic rollback[/yellow]"
            )
            return True
        if on_failure == "never":
            return True

        console.print(
            f"[yellow]🔄 Executing rollback for task '{task.get('name')}'...[/yellow]"
        )

        # Rollback manifests 적용
        rollback_manifests = rollback.get("manifests", [])
        if rollback_manifests:
            console.print("  Applying rollback manifests...")
            namespace = (
                context.get("namespace") if context else None
            ) or self.namespace
            if not self._deploy_manifests(app_name, rollback_manifests, namespace):
                console.print("[red]❌ Rollback manifests failed[/red]")
                return False

        # Rollback commands 실행
        rollback_commands = rollback.get("commands", [])
        if rollback_commands:
            console.print("  Executing rollback commands...")
            for cmd in rollback_commands:
                if not self._execute_single_command(cmd, "rollback", self.env):
                    console.print(f"[red]❌ Rollback command failed: {cmd}[/red]")
                    return False

        console.print("[green]✅ Rollback completed[/green]")
        return True
