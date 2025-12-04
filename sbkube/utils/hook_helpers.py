"""Hook execution helper functions for SBKube commands.

This module provides high-level helper functions that simplify hook execution
patterns commonly used across multiple commands (build, deploy, prepare, template, apply).

Phase 3 refactoring: Centralize repetitive hook execution patterns.
"""

from pathlib import Path
from typing import TYPE_CHECKING

from sbkube.utils.hook_executor import HookExecutor
from sbkube.utils.output_manager import OutputManager

if TYPE_CHECKING:
    from sbkube.models.config_model import AppConfig, SBKubeConfig


def create_hook_executor(
    base_dir: Path,
    work_dir: Path,
    dry_run: bool = False,
    kubeconfig: str | None = None,
    context: str | None = None,
    namespace: str | None = None,
) -> HookExecutor:
    """Create a HookExecutor instance with common parameters.

    Args:
        base_dir: Project root directory (BASE_DIR)
        work_dir: Working directory for hook execution (usually APP_CONFIG_DIR)
        dry_run: If True, only print commands without executing
        kubeconfig: Path to kubeconfig file
        context: Kubernetes context name
        namespace: Default namespace for kubectl commands

    Returns:
        Configured HookExecutor instance

    """
    return HookExecutor(
        base_dir=base_dir,
        work_dir=work_dir,
        dry_run=dry_run,
        kubeconfig=kubeconfig,
        context=context,
        namespace=namespace,
    )


def execute_global_pre_hook(
    hook_executor: HookExecutor,
    config: "SBKubeConfig",
    command_name: str,
    output: OutputManager,
) -> bool:
    """Execute global pre-command hook if configured.

    Args:
        hook_executor: HookExecutor instance
        config: SBKubeConfig with hooks configuration
        command_name: Command name (e.g., "build", "deploy", "prepare", "template")
        output: OutputManager for error messages

    Returns:
        True if hook succeeded or not configured, False if hook failed

    """
    if not config.hooks or command_name not in config.hooks:
        return True

    command_hooks = config.hooks[command_name].model_dump()
    if not hook_executor.execute_command_hooks(
        hook_config=command_hooks,
        hook_phase="pre",
        command_name=command_name,
    ):
        output.print_error(f"Pre-{command_name} hook failed")
        return False

    return True


def execute_global_post_hook(
    hook_executor: HookExecutor,
    config: "SBKubeConfig",
    command_name: str,
    failed: bool = False,
) -> None:
    """Execute global post-command or on_failure hook based on result.

    Args:
        hook_executor: HookExecutor instance
        config: SBKubeConfig with hooks configuration
        command_name: Command name (e.g., "build", "deploy", "prepare", "template")
        failed: If True, execute on_failure hook instead of post hook

    """
    if not config.hooks or command_name not in config.hooks:
        return

    command_hooks = config.hooks[command_name].model_dump()

    if failed:
        hook_executor.execute_command_hooks(
            hook_config=command_hooks,
            hook_phase="on_failure",
            command_name=command_name,
        )
    else:
        hook_executor.execute_command_hooks(
            hook_config=command_hooks,
            hook_phase="post",
            command_name=command_name,
        )


def execute_app_pre_hook(
    hook_executor: HookExecutor,
    app_name: str,
    app: "AppConfig",
    command_name: str,
    output: OutputManager,
    context: dict | None = None,
) -> bool:
    """Execute app-level pre-command hook if configured.

    Args:
        hook_executor: HookExecutor instance
        app_name: Name of the app
        app: AppConfig with hooks configuration
        command_name: Command name (e.g., "build", "deploy", "prepare", "template")
        output: OutputManager for error messages
        context: Additional context variables for hook execution

    Returns:
        True if hook succeeded or not configured, False if hook failed

    """
    if not hasattr(app, "hooks") or not app.hooks:
        return True

    hook_type = f"pre_{command_name}"
    app_hooks = app.hooks.model_dump()

    if not hook_executor.execute_app_hook(
        app_name=app_name,
        app_hooks=app_hooks,
        hook_type=hook_type,
        context=context or {},
    ):
        output.print_error(f"Pre-{command_name} hook failed for app: {app_name}")
        return False

    return True


def execute_app_post_hook(
    hook_executor: HookExecutor,
    app_name: str,
    app: "AppConfig",
    command_name: str,
    context: dict | None = None,
) -> None:
    """Execute app-level post-command hook if configured.

    Args:
        hook_executor: HookExecutor instance
        app_name: Name of the app
        app: AppConfig with hooks configuration
        command_name: Command name (e.g., "build", "deploy", "prepare", "template")
        context: Additional context variables for hook execution

    """
    if not hasattr(app, "hooks") or not app.hooks:
        return

    hook_type = f"post_{command_name}"
    app_hooks = app.hooks.model_dump()

    hook_executor.execute_app_hook(
        app_name=app_name,
        app_hooks=app_hooks,
        hook_type=hook_type,
        context=context or {},
    )


class HookContext:
    """Context manager for command-level hook execution.

    Handles pre/post/on_failure hooks automatically with proper cleanup.

    Example:
        ```python
        with HookContext(hook_executor, config, "build", output) as ctx:
            if not ctx.pre_hook_success:
                continue  # Pre-hook failed

            # Do work...
            if error:
                ctx.mark_failed()

        # Post/on_failure hook executed automatically on exit
        ```

    """

    def __init__(
        self,
        hook_executor: HookExecutor,
        config: "SBKubeConfig",
        command_name: str,
        output: OutputManager,
    ) -> None:
        """Initialize HookContext.

        Args:
            hook_executor: HookExecutor instance
            config: SBKubeConfig with hooks configuration
            command_name: Command name for hooks
            output: OutputManager for messages

        """
        self.hook_executor = hook_executor
        self.config = config
        self.command_name = command_name
        self.output = output
        self.pre_hook_success = False
        self._failed = False

    def __enter__(self) -> "HookContext":
        """Execute pre-hook on context entry."""
        self.pre_hook_success = execute_global_pre_hook(
            self.hook_executor,
            self.config,
            self.command_name,
            self.output,
        )
        return self

    def __exit__(self, exc_type, exc_val, exc_tb) -> None:
        """Execute post/on_failure hook on context exit."""
        # Only execute post hooks if pre-hook succeeded
        if self.pre_hook_success:
            execute_global_post_hook(
                self.hook_executor,
                self.config,
                self.command_name,
                failed=self._failed or exc_type is not None,
            )

    def mark_failed(self) -> None:
        """Mark the command as failed for on_failure hook."""
        self._failed = True

    @property
    def failed(self) -> bool:
        """Check if command was marked as failed."""
        return self._failed
