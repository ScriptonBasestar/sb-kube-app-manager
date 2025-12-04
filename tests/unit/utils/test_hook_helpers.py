"""Tests for hook_helpers module (Phase 3 refactoring)."""

from pathlib import Path
from unittest.mock import MagicMock, patch

import pytest

from sbkube.utils.hook_helpers import (
    HookContext,
    create_hook_executor,
    execute_app_post_hook,
    execute_app_pre_hook,
    execute_global_post_hook,
    execute_global_pre_hook,
)


class TestCreateHookExecutor:
    """Test create_hook_executor function."""

    def test_creates_basic_executor(self, tmp_path: Path) -> None:
        """Test creates HookExecutor with basic parameters."""
        executor = create_hook_executor(
            base_dir=tmp_path,
            work_dir=tmp_path / "work",
        )

        assert executor.base_dir == tmp_path
        assert executor.work_dir == tmp_path / "work"
        assert executor.dry_run is False

    def test_creates_executor_with_all_params(self, tmp_path: Path) -> None:
        """Test creates HookExecutor with all parameters."""
        executor = create_hook_executor(
            base_dir=tmp_path,
            work_dir=tmp_path / "work",
            dry_run=True,
            kubeconfig="/path/to/kubeconfig",
            context="my-context",
            namespace="my-namespace",
        )

        assert executor.base_dir == tmp_path
        assert executor.dry_run is True
        assert executor.kubeconfig == "/path/to/kubeconfig"
        assert executor.context == "my-context"
        assert executor.namespace == "my-namespace"


class TestExecuteGlobalPreHook:
    """Test execute_global_pre_hook function."""

    def test_returns_true_when_no_hooks(self, tmp_path: Path) -> None:
        """Test returns True when config has no hooks."""
        executor = MagicMock()
        config = MagicMock()
        config.hooks = None
        output = MagicMock()

        result = execute_global_pre_hook(executor, config, "build", output)

        assert result is True
        executor.execute_command_hooks.assert_not_called()

    def test_returns_true_when_command_not_in_hooks(self, tmp_path: Path) -> None:
        """Test returns True when command not configured in hooks."""
        executor = MagicMock()
        config = MagicMock()
        config.hooks = {"deploy": MagicMock()}  # No "build" hook
        output = MagicMock()

        result = execute_global_pre_hook(executor, config, "build", output)

        assert result is True
        executor.execute_command_hooks.assert_not_called()

    def test_executes_pre_hook_success(self, tmp_path: Path) -> None:
        """Test executes pre hook and returns True on success."""
        executor = MagicMock()
        executor.execute_command_hooks.return_value = True

        config = MagicMock()
        build_hooks = MagicMock()
        build_hooks.model_dump.return_value = {"pre": ["echo test"]}
        config.hooks = {"build": build_hooks}

        output = MagicMock()

        result = execute_global_pre_hook(executor, config, "build", output)

        assert result is True
        executor.execute_command_hooks.assert_called_once_with(
            hook_config={"pre": ["echo test"]},
            hook_phase="pre",
            command_name="build",
        )

    def test_executes_pre_hook_failure(self, tmp_path: Path) -> None:
        """Test returns False and prints error on hook failure."""
        executor = MagicMock()
        executor.execute_command_hooks.return_value = False

        config = MagicMock()
        build_hooks = MagicMock()
        build_hooks.model_dump.return_value = {"pre": ["exit 1"]}
        config.hooks = {"build": build_hooks}

        output = MagicMock()

        result = execute_global_pre_hook(executor, config, "build", output)

        assert result is False
        output.print_error.assert_called_once()
        assert "Pre-build hook failed" in output.print_error.call_args[0][0]


class TestExecuteGlobalPostHook:
    """Test execute_global_post_hook function."""

    def test_does_nothing_when_no_hooks(self, tmp_path: Path) -> None:
        """Test does nothing when config has no hooks."""
        executor = MagicMock()
        config = MagicMock()
        config.hooks = None

        execute_global_post_hook(executor, config, "build")

        executor.execute_command_hooks.assert_not_called()

    def test_executes_post_hook_on_success(self, tmp_path: Path) -> None:
        """Test executes post hook when not failed."""
        executor = MagicMock()

        config = MagicMock()
        build_hooks = MagicMock()
        build_hooks.model_dump.return_value = {"post": ["echo done"]}
        config.hooks = {"build": build_hooks}

        execute_global_post_hook(executor, config, "build", failed=False)

        executor.execute_command_hooks.assert_called_once_with(
            hook_config={"post": ["echo done"]},
            hook_phase="post",
            command_name="build",
        )

    def test_executes_on_failure_hook_when_failed(self, tmp_path: Path) -> None:
        """Test executes on_failure hook when failed=True."""
        executor = MagicMock()

        config = MagicMock()
        build_hooks = MagicMock()
        build_hooks.model_dump.return_value = {"on_failure": ["echo failed"]}
        config.hooks = {"build": build_hooks}

        execute_global_post_hook(executor, config, "build", failed=True)

        executor.execute_command_hooks.assert_called_once_with(
            hook_config={"on_failure": ["echo failed"]},
            hook_phase="on_failure",
            command_name="build",
        )


class TestExecuteAppPreHook:
    """Test execute_app_pre_hook function."""

    def test_returns_true_when_no_hooks(self) -> None:
        """Test returns True when app has no hooks."""
        executor = MagicMock()
        app = MagicMock(spec=[])  # No hooks attribute
        output = MagicMock()

        result = execute_app_pre_hook(executor, "myapp", app, "build", output)

        assert result is True
        executor.execute_app_hook.assert_not_called()

    def test_returns_true_when_hooks_is_none(self) -> None:
        """Test returns True when app.hooks is None."""
        executor = MagicMock()
        app = MagicMock()
        app.hooks = None
        output = MagicMock()

        result = execute_app_pre_hook(executor, "myapp", app, "build", output)

        assert result is True
        executor.execute_app_hook.assert_not_called()

    def test_executes_app_pre_hook_success(self) -> None:
        """Test executes app pre hook and returns True on success."""
        executor = MagicMock()
        executor.execute_app_hook.return_value = True

        app = MagicMock()
        app.hooks.model_dump.return_value = {"pre_build": "echo pre"}
        output = MagicMock()

        result = execute_app_pre_hook(executor, "myapp", app, "build", output)

        assert result is True
        executor.execute_app_hook.assert_called_once_with(
            app_name="myapp",
            app_hooks={"pre_build": "echo pre"},
            hook_type="pre_build",
            context={},
        )

    def test_executes_app_pre_hook_failure(self) -> None:
        """Test returns False and prints error on hook failure."""
        executor = MagicMock()
        executor.execute_app_hook.return_value = False

        app = MagicMock()
        app.hooks.model_dump.return_value = {"pre_build": "exit 1"}
        output = MagicMock()

        result = execute_app_pre_hook(executor, "myapp", app, "build", output)

        assert result is False
        output.print_error.assert_called_once()
        assert "Pre-build hook failed for app: myapp" in output.print_error.call_args[0][0]

    def test_passes_context(self) -> None:
        """Test passes context to hook executor."""
        executor = MagicMock()
        executor.execute_app_hook.return_value = True

        app = MagicMock()
        app.hooks.model_dump.return_value = {"pre_deploy": "echo deploy"}
        output = MagicMock()

        context = {"chart_path": "/path/to/chart"}
        result = execute_app_pre_hook(
            executor, "myapp", app, "deploy", output, context=context
        )

        assert result is True
        executor.execute_app_hook.assert_called_once_with(
            app_name="myapp",
            app_hooks={"pre_deploy": "echo deploy"},
            hook_type="pre_deploy",
            context={"chart_path": "/path/to/chart"},
        )


class TestExecuteAppPostHook:
    """Test execute_app_post_hook function."""

    def test_does_nothing_when_no_hooks(self) -> None:
        """Test does nothing when app has no hooks."""
        executor = MagicMock()
        app = MagicMock(spec=[])  # No hooks attribute

        execute_app_post_hook(executor, "myapp", app, "build")

        executor.execute_app_hook.assert_not_called()

    def test_executes_app_post_hook(self) -> None:
        """Test executes app post hook."""
        executor = MagicMock()

        app = MagicMock()
        app.hooks.model_dump.return_value = {"post_build": "echo post"}

        execute_app_post_hook(executor, "myapp", app, "build")

        executor.execute_app_hook.assert_called_once_with(
            app_name="myapp",
            app_hooks={"post_build": "echo post"},
            hook_type="post_build",
            context={},
        )


class TestHookContext:
    """Test HookContext context manager."""

    def test_executes_pre_and_post_hooks(self) -> None:
        """Test executes pre hook on enter and post hook on exit."""
        executor = MagicMock()
        executor.execute_command_hooks.return_value = True

        config = MagicMock()
        build_hooks = MagicMock()
        build_hooks.model_dump.return_value = {"pre": [], "post": []}
        config.hooks = {"build": build_hooks}

        output = MagicMock()

        with HookContext(executor, config, "build", output) as ctx:
            assert ctx.pre_hook_success is True
            assert ctx.failed is False

        # Should have called pre and post
        assert executor.execute_command_hooks.call_count == 2
        calls = executor.execute_command_hooks.call_args_list
        assert calls[0][1]["hook_phase"] == "pre"
        assert calls[1][1]["hook_phase"] == "post"

    def test_executes_on_failure_when_marked_failed(self) -> None:
        """Test executes on_failure hook when mark_failed() called."""
        executor = MagicMock()
        executor.execute_command_hooks.return_value = True

        config = MagicMock()
        build_hooks = MagicMock()
        build_hooks.model_dump.return_value = {"pre": [], "on_failure": []}
        config.hooks = {"build": build_hooks}

        output = MagicMock()

        with HookContext(executor, config, "build", output) as ctx:
            ctx.mark_failed()
            assert ctx.failed is True

        # Should have called pre and on_failure (not post)
        assert executor.execute_command_hooks.call_count == 2
        calls = executor.execute_command_hooks.call_args_list
        assert calls[0][1]["hook_phase"] == "pre"
        assert calls[1][1]["hook_phase"] == "on_failure"

    def test_executes_on_failure_on_exception(self) -> None:
        """Test executes on_failure hook when exception raised."""
        executor = MagicMock()
        executor.execute_command_hooks.return_value = True

        config = MagicMock()
        build_hooks = MagicMock()
        build_hooks.model_dump.return_value = {"pre": [], "on_failure": []}
        config.hooks = {"build": build_hooks}

        output = MagicMock()

        with pytest.raises(ValueError):
            with HookContext(executor, config, "build", output):
                raise ValueError("Test error")

        # Should have called pre and on_failure
        assert executor.execute_command_hooks.call_count == 2
        calls = executor.execute_command_hooks.call_args_list
        assert calls[1][1]["hook_phase"] == "on_failure"

    def test_skips_post_hook_when_pre_hook_fails(self) -> None:
        """Test skips post hook when pre hook fails."""
        executor = MagicMock()
        executor.execute_command_hooks.return_value = False  # Pre hook fails

        config = MagicMock()
        build_hooks = MagicMock()
        build_hooks.model_dump.return_value = {"pre": ["exit 1"], "post": []}
        config.hooks = {"build": build_hooks}

        output = MagicMock()

        with HookContext(executor, config, "build", output) as ctx:
            assert ctx.pre_hook_success is False

        # Should have only called pre (not post)
        assert executor.execute_command_hooks.call_count == 1

    def test_works_without_hooks(self) -> None:
        """Test works when config has no hooks."""
        executor = MagicMock()

        config = MagicMock()
        config.hooks = None

        output = MagicMock()

        with HookContext(executor, config, "build", output) as ctx:
            assert ctx.pre_hook_success is True

        executor.execute_command_hooks.assert_not_called()
