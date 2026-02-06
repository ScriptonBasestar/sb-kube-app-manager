"""Recursive Executor for SBKube v0.11.0+.

This module provides the RecursiveExecutor that executes UnifiedConfig
with proper settings inheritance, phase ordering, and nested execution.

Key Features:
- Recursive execution of nested phases
- Settings inheritance (global -> phase -> app)
- Configurable execution order (apps_first, phases_first)
- Parallel execution support
- Failure handling with rollback support

Usage:
    from sbkube.utils.recursive_executor import RecursiveExecutor

    executor = RecursiveExecutor(
        base_dir=Path("."),
        dry_run=False,
        output=output_manager,
    )

    result = executor.execute(config)
"""

from collections.abc import Callable
from concurrent.futures import ThreadPoolExecutor, as_completed
from dataclasses import dataclass, field
from datetime import datetime
from enum import Enum
from pathlib import Path
from typing import Any

from sbkube.models.config_model import AppConfig
from sbkube.models.unified_config_model import (
    PhaseReference,
    UnifiedConfig,
    UnifiedSettings,
)
from sbkube.utils.logger import logger
from sbkube.utils.settings_merger import merge_settings


class ExecutionStatus(Enum):
    """Execution status enum."""

    PENDING = "pending"
    RUNNING = "running"
    SUCCESS = "success"
    FAILED = "failed"
    SKIPPED = "skipped"
    ROLLED_BACK = "rolled_back"


@dataclass
class AppExecutionResult:
    """Result of executing a single app."""

    app_name: str
    status: ExecutionStatus
    start_time: datetime | None = None
    end_time: datetime | None = None
    error_message: str | None = None
    rollback_data: dict[str, Any] | None = None

    @property
    def duration_seconds(self) -> float | None:
        """Get execution duration in seconds."""
        if self.start_time and self.end_time:
            return (self.end_time - self.start_time).total_seconds()
        return None


@dataclass
class PhaseExecutionResult:
    """Result of executing a phase."""

    phase_name: str
    status: ExecutionStatus
    app_results: list[AppExecutionResult] = field(default_factory=list)
    nested_results: list["PhaseExecutionResult"] = field(default_factory=list)
    start_time: datetime | None = None
    end_time: datetime | None = None
    error_message: str | None = None

    @property
    def duration_seconds(self) -> float | None:
        """Get execution duration in seconds."""
        if self.start_time and self.end_time:
            return (self.end_time - self.start_time).total_seconds()
        return None

    @property
    def total_apps(self) -> int:
        """Get total number of apps including nested."""
        count = len(self.app_results)
        for nested in self.nested_results:
            count += nested.total_apps
        return count

    @property
    def successful_apps(self) -> int:
        """Get number of successful apps including nested."""
        count = sum(1 for r in self.app_results if r.status == ExecutionStatus.SUCCESS)
        for nested in self.nested_results:
            count += nested.successful_apps
        return count


@dataclass
class ExecutionResult:
    """Overall execution result."""

    status: ExecutionStatus
    app_results: list[AppExecutionResult] = field(default_factory=list)
    phase_results: list[PhaseExecutionResult] = field(default_factory=list)
    start_time: datetime | None = None
    end_time: datetime | None = None
    error_message: str | None = None

    @property
    def duration_seconds(self) -> float | None:
        """Get total execution duration in seconds."""
        if self.start_time and self.end_time:
            return (self.end_time - self.start_time).total_seconds()
        return None

    @property
    def total_apps(self) -> int:
        """Get total number of apps."""
        count = len(self.app_results)
        for phase in self.phase_results:
            count += phase.total_apps
        return count

    @property
    def successful_apps(self) -> int:
        """Get number of successful apps."""
        count = sum(1 for r in self.app_results if r.status == ExecutionStatus.SUCCESS)
        for phase in self.phase_results:
            count += phase.successful_apps
        return count

    def is_success(self) -> bool:
        """Check if execution was successful."""
        return self.status == ExecutionStatus.SUCCESS


# Type alias for app executor function
AppExecutorFunc = Callable[[str, AppConfig, UnifiedSettings, Path], AppExecutionResult]


class RecursiveExecutor:
    """Recursive executor for UnifiedConfig.

    Executes configuration with:
    - Settings inheritance
    - Phase ordering with dependency resolution
    - Nested phase execution
    - Parallel execution support
    - Failure handling

    """

    def __init__(
        self,
        base_dir: Path | str,
        dry_run: bool = False,
        app_executor: AppExecutorFunc | None = None,
        on_app_start: Callable[[str], None] | None = None,
        on_app_complete: Callable[[str, AppExecutionResult], None] | None = None,
        on_phase_start: Callable[[str], None] | None = None,
        on_phase_complete: Callable[[str, PhaseExecutionResult], None] | None = None,
    ) -> None:
        """Initialize RecursiveExecutor.

        Args:
            base_dir: Base directory for configuration files
            dry_run: If True, simulate execution without actual deployment
            app_executor: Custom function to execute individual apps
            on_app_start: Callback when app execution starts
            on_app_complete: Callback when app execution completes
            on_phase_start: Callback when phase execution starts
            on_phase_complete: Callback when phase execution completes

        """
        self.base_dir = Path(base_dir)
        self.dry_run = dry_run
        self.app_executor = app_executor or self._default_app_executor
        self.on_app_start = on_app_start
        self.on_app_complete = on_app_complete
        self.on_phase_start = on_phase_start
        self.on_phase_complete = on_phase_complete

        # Execution state
        self._executed_apps: set[str] = set()
        self._rollback_stack: list[tuple[str, dict[str, Any]]] = []

    def execute(
        self,
        config: UnifiedConfig,
        parent_settings: UnifiedSettings | None = None,
    ) -> ExecutionResult:
        """Execute a UnifiedConfig.

        Args:
            config: Configuration to execute
            parent_settings: Parent settings for inheritance

        Returns:
            ExecutionResult with execution details

        """
        result = ExecutionResult(
            status=ExecutionStatus.RUNNING,
            start_time=datetime.now(),
        )

        try:
            # Merge settings with parent
            effective_settings = (
                merge_settings(parent_settings, config.settings)
                if parent_settings
                else config.settings
            )

            # Execute based on execution_order
            if effective_settings.execution_order == "apps_first":
                # Execute apps first, then phases
                if config.apps:
                    app_results = self._execute_apps(
                        config.apps, effective_settings, self.base_dir
                    )
                    result.app_results.extend(app_results)

                    # Check for failures
                    if not self._check_continue(app_results, effective_settings):
                        result.status = ExecutionStatus.FAILED
                        result.error_message = "App execution failed"
                        result.end_time = datetime.now()
                        return result

                if config.phases:
                    phase_results = self._execute_phases(
                        config, effective_settings
                    )
                    result.phase_results.extend(phase_results)

                    # Check for failures
                    failed_phases = [
                        p for p in phase_results if p.status == ExecutionStatus.FAILED
                    ]
                    if failed_phases:
                        result.status = ExecutionStatus.FAILED
                        result.error_message = f"Phase(s) failed: {[p.phase_name for p in failed_phases]}"
                        result.end_time = datetime.now()
                        return result
            else:
                # Execute phases first, then apps
                if config.phases:
                    phase_results = self._execute_phases(
                        config, effective_settings
                    )
                    result.phase_results.extend(phase_results)

                    # Check for failures
                    failed_phases = [
                        p for p in phase_results if p.status == ExecutionStatus.FAILED
                    ]
                    if failed_phases:
                        result.status = ExecutionStatus.FAILED
                        result.error_message = f"Phase(s) failed: {[p.phase_name for p in failed_phases]}"
                        result.end_time = datetime.now()
                        return result

                if config.apps:
                    app_results = self._execute_apps(
                        config.apps, effective_settings, self.base_dir
                    )
                    result.app_results.extend(app_results)

                    # Check for failures
                    if not self._check_continue(app_results, effective_settings):
                        result.status = ExecutionStatus.FAILED
                        result.error_message = "App execution failed"
                        result.end_time = datetime.now()
                        return result

            result.status = ExecutionStatus.SUCCESS
            result.end_time = datetime.now()

        except Exception as e:
            result.status = ExecutionStatus.FAILED
            result.error_message = str(e)
            result.end_time = datetime.now()
            logger.error(f"Execution failed: {e}")

        return result

    def _execute_apps(
        self,
        apps: dict[str, AppConfig],
        settings: UnifiedSettings,
        work_dir: Path,
    ) -> list[AppExecutionResult]:
        """Execute apps with optional parallelism.

        Args:
            apps: Apps to execute
            settings: Effective settings
            work_dir: Working directory

        Returns:
            List of app execution results

        """
        results: list[AppExecutionResult] = []

        # Filter enabled apps
        enabled_apps = {name: app for name, app in apps.items() if app.enabled}

        if not enabled_apps:
            return results

        if settings.parallel_apps and len(enabled_apps) > 1:
            # Parallel execution
            results = self._execute_apps_parallel(enabled_apps, settings, work_dir)
        else:
            # Sequential execution
            for app_name, app_config in enabled_apps.items():
                result = self._execute_single_app(
                    app_name, app_config, settings, work_dir
                )
                results.append(result)

                # Check if we should continue
                if result.status == ExecutionStatus.FAILED:
                    if settings.on_failure == "stop":
                        break
                    elif settings.on_failure == "rollback":
                        self._handle_rollback(settings.rollback_scope, results)
                        break

        return results

    def _execute_apps_parallel(
        self,
        apps: dict[str, AppConfig],
        settings: UnifiedSettings,
        work_dir: Path,
    ) -> list[AppExecutionResult]:
        """Execute apps in parallel.

        Args:
            apps: Apps to execute
            settings: Effective settings
            work_dir: Working directory

        Returns:
            List of app execution results

        """
        results: list[AppExecutionResult] = []

        with ThreadPoolExecutor(max_workers=settings.max_workers) as executor:
            future_to_app = {
                executor.submit(
                    self._execute_single_app,
                    app_name,
                    app_config,
                    settings,
                    work_dir,
                ): app_name
                for app_name, app_config in apps.items()
            }

            for future in as_completed(future_to_app):
                app_name = future_to_app[future]
                try:
                    result = future.result()
                    results.append(result)
                except Exception as e:
                    results.append(
                        AppExecutionResult(
                            app_name=app_name,
                            status=ExecutionStatus.FAILED,
                            error_message=str(e),
                        )
                    )

        return results

    def _execute_single_app(
        self,
        app_name: str,
        app_config: AppConfig,
        settings: UnifiedSettings,
        work_dir: Path,
    ) -> AppExecutionResult:
        """Execute a single app.

        Args:
            app_name: Name of the app
            app_config: App configuration
            settings: Effective settings
            work_dir: Working directory

        Returns:
            App execution result

        """
        if self.on_app_start:
            self.on_app_start(app_name)

        result = self.app_executor(app_name, app_config, settings, work_dir)

        if self.on_app_complete:
            self.on_app_complete(app_name, result)

        # Track for rollback
        if result.status == ExecutionStatus.SUCCESS and result.rollback_data:
            self._rollback_stack.append((app_name, result.rollback_data))

        self._executed_apps.add(app_name)

        return result

    def _execute_phases(
        self,
        config: UnifiedConfig,
        settings: UnifiedSettings,
    ) -> list[PhaseExecutionResult]:
        """Execute phases in dependency order.

        Args:
            config: Configuration with phases
            settings: Effective settings

        Returns:
            List of phase execution results

        """
        results: list[PhaseExecutionResult] = []
        phase_order = config.get_phase_order()

        if settings.parallel and len(phase_order) > 1:
            # Find independent phases (no dependencies) for parallel execution
            results = self._execute_phases_with_parallelism(
                config, settings, phase_order
            )
        else:
            # Sequential execution
            for phase_name in phase_order:
                phase_ref = config.phases[phase_name]
                result = self._execute_single_phase(
                    phase_name, phase_ref, settings
                )
                results.append(result)

                # Check if we should continue
                if result.status == ExecutionStatus.FAILED:
                    effective_on_failure = phase_ref.get_on_failure(settings.on_failure)
                    if effective_on_failure == "stop":
                        break
                    elif effective_on_failure == "rollback":
                        self._handle_rollback(settings.rollback_scope, result=result)
                        break

        return results

    def _execute_phases_with_parallelism(
        self,
        config: UnifiedConfig,
        settings: UnifiedSettings,
        phase_order: list[str],
    ) -> list[PhaseExecutionResult]:
        """Execute phases with parallelism for independent phases.

        Args:
            config: Configuration with phases
            settings: Effective settings
            phase_order: Ordered list of phase names

        Returns:
            List of phase execution results

        """
        results: list[PhaseExecutionResult] = []
        completed_phases: set[str] = set()
        remaining_phases = set(phase_order)

        while remaining_phases:
            # Find phases that can be executed (dependencies satisfied)
            ready_phases = []
            for phase_name in remaining_phases:
                phase_ref = config.phases[phase_name]
                deps_satisfied = all(
                    dep in completed_phases for dep in phase_ref.depends_on
                )
                if deps_satisfied:
                    ready_phases.append(phase_name)

            if not ready_phases:
                # No progress possible - should not happen with valid config
                logger.error("No phases ready for execution - possible dependency issue")
                break

            if len(ready_phases) > 1:
                # Execute ready phases in parallel
                parallel_results = self._execute_phases_parallel(
                    [(name, config.phases[name]) for name in ready_phases],
                    settings,
                )
                results.extend(parallel_results)

                # Check for failures
                failed = [r for r in parallel_results if r.status == ExecutionStatus.FAILED]
                should_stop = any(
                    config.phases[r.phase_name].get_on_failure(settings.on_failure) == "stop"
                    for r in failed
                )
                if should_stop:
                    break

                for r in parallel_results:
                    completed_phases.add(r.phase_name)
                    remaining_phases.discard(r.phase_name)
            else:
                # Single phase - execute sequentially
                phase_name = ready_phases[0]
                phase_ref = config.phases[phase_name]
                result = self._execute_single_phase(
                    phase_name, phase_ref, settings
                )
                results.append(result)

                if result.status == ExecutionStatus.FAILED and phase_ref.get_on_failure(settings.on_failure) == "stop":
                    break

                completed_phases.add(phase_name)
                remaining_phases.discard(phase_name)

        return results

    def _execute_phases_parallel(
        self,
        phases: list[tuple[str, PhaseReference]],
        settings: UnifiedSettings,
    ) -> list[PhaseExecutionResult]:
        """Execute multiple phases in parallel.

        Args:
            phases: List of (phase_name, phase_ref) tuples
            settings: Effective settings

        Returns:
            List of phase execution results

        """
        results: list[PhaseExecutionResult] = []

        with ThreadPoolExecutor(max_workers=settings.max_workers) as executor:
            future_to_phase = {
                executor.submit(
                    self._execute_single_phase,
                    phase_name,
                    phase_ref,
                    settings,
                ): phase_name
                for phase_name, phase_ref in phases
            }

            for future in as_completed(future_to_phase):
                phase_name = future_to_phase[future]
                try:
                    result = future.result()
                    results.append(result)
                except Exception as e:
                    results.append(
                        PhaseExecutionResult(
                            phase_name=phase_name,
                            status=ExecutionStatus.FAILED,
                            error_message=str(e),
                        )
                    )

        return results

    def _execute_single_phase(
        self,
        phase_name: str,
        phase_ref: PhaseReference,
        parent_settings: UnifiedSettings,
    ) -> PhaseExecutionResult:
        """Execute a single phase.

        Args:
            phase_name: Name of the phase
            phase_ref: Phase reference/configuration
            parent_settings: Parent settings for inheritance

        Returns:
            Phase execution result

        """
        if self.on_phase_start:
            self.on_phase_start(phase_name)

        result = PhaseExecutionResult(
            phase_name=phase_name,
            status=ExecutionStatus.RUNNING,
            start_time=datetime.now(),
        )

        try:
            # Merge phase-specific settings
            effective_settings = (
                merge_settings(parent_settings, phase_ref.settings)
                if phase_ref.settings
                else parent_settings
            )

            if phase_ref.source:
                # External source - load and execute recursively
                source_path = self.base_dir / phase_ref.source
                if not source_path.exists():
                    result.status = ExecutionStatus.FAILED
                    result.error_message = f"Source file not found: {source_path}"
                    result.end_time = datetime.now()
                    return result

                # Load nested config
                nested_config = UnifiedConfig.from_yaml(source_path)

                # Create sub-executor with source directory as base
                sub_executor = RecursiveExecutor(
                    base_dir=source_path.parent,
                    dry_run=self.dry_run,
                    app_executor=self.app_executor,
                    on_app_start=self.on_app_start,
                    on_app_complete=self.on_app_complete,
                    on_phase_start=self.on_phase_start,
                    on_phase_complete=self.on_phase_complete,
                )

                # Execute nested config
                nested_result = sub_executor.execute(nested_config, effective_settings)

                # Transfer results
                result.app_results.extend(nested_result.app_results)
                result.nested_results.extend(nested_result.phase_results)
                result.status = nested_result.status
                result.error_message = nested_result.error_message

            else:
                # Inline apps - execute directly
                if phase_ref.apps:
                    app_results = self._execute_apps(
                        phase_ref.apps,
                        effective_settings,
                        self.base_dir,
                    )
                    result.app_results.extend(app_results)

                    # Check for failures
                    failed_apps = [
                        r for r in app_results if r.status == ExecutionStatus.FAILED
                    ]
                    if failed_apps:
                        result.status = ExecutionStatus.FAILED
                        result.error_message = f"Apps failed: {[r.app_name for r in failed_apps]}"
                    else:
                        result.status = ExecutionStatus.SUCCESS

            result.end_time = datetime.now()

        except Exception as e:
            result.status = ExecutionStatus.FAILED
            result.error_message = str(e)
            result.end_time = datetime.now()
            logger.error(f"Phase '{phase_name}' execution failed: {e}")

        if self.on_phase_complete:
            self.on_phase_complete(phase_name, result)

        return result

    def _check_continue(
        self,
        results: list[AppExecutionResult],
        settings: UnifiedSettings,
    ) -> bool:
        """Check if execution should continue after app results.

        Args:
            results: App execution results
            settings: Current settings

        Returns:
            True if execution should continue

        """
        failed = [r for r in results if r.status == ExecutionStatus.FAILED]

        if not failed:
            return True

        if settings.on_failure == "continue":
            return True

        return False

    def _handle_rollback(
        self,
        scope: str,
        app_results: list[AppExecutionResult] | None = None,
        result: PhaseExecutionResult | None = None,
    ) -> None:
        """Handle rollback based on scope.

        Args:
            scope: Rollback scope (app, phase, all)
            app_results: App results for app-level rollback
            result: Phase result for phase-level rollback

        """
        logger.warning(f"Initiating rollback with scope: {scope}")

        if scope == "app" and app_results:
            # Rollback only the failed app (last one)
            failed_apps = [r for r in app_results if r.status == ExecutionStatus.FAILED]
            if failed_apps:
                self._rollback_apps([failed_apps[-1].app_name])

        elif scope == "phase" and result:
            # Rollback all apps in the phase
            app_names = [r.app_name for r in result.app_results]
            self._rollback_apps(app_names)

        elif scope == "all":
            # Rollback all executed apps
            self._rollback_apps(list(self._executed_apps))

    def _rollback_apps(self, app_names: list[str]) -> None:
        """Rollback specified apps.

        Args:
            app_names: Names of apps to rollback

        """
        for app_name in reversed(app_names):
            logger.info(f"Rolling back app: {app_name}")

            # Find rollback data
            for name, data in reversed(self._rollback_stack):
                if name == app_name:
                    self._perform_rollback(app_name, data)
                    break

    def _perform_rollback(self, app_name: str, rollback_data: dict[str, Any]) -> None:
        """Perform actual rollback for an app.

        Args:
            app_name: Name of the app
            rollback_data: Data needed for rollback

        """
        if self.dry_run:
            logger.info(f"[DRY-RUN] Would rollback app: {app_name}")
            return

        # This is a placeholder - actual rollback implementation
        # would depend on the app type and deployment method
        logger.info(f"Rollback data for {app_name}: {rollback_data}")

    def _default_app_executor(
        self,
        app_name: str,
        app_config: AppConfig,
        settings: UnifiedSettings,
        work_dir: Path,
    ) -> AppExecutionResult:
        """Default app executor (placeholder).

        This default implementation just simulates execution.
        In production, this would be replaced with actual deployment logic.

        Args:
            app_name: Name of the app
            app_config: App configuration
            settings: Effective settings
            work_dir: Working directory

        Returns:
            App execution result

        """
        start_time = datetime.now()

        if self.dry_run:
            logger.info(f"[DRY-RUN] Would execute app: {app_name} (type={app_config.type})")
            return AppExecutionResult(
                app_name=app_name,
                status=ExecutionStatus.SUCCESS,
                start_time=start_time,
                end_time=datetime.now(),
            )

        # Placeholder execution
        logger.info(f"Executing app: {app_name} (type={app_config.type})")

        return AppExecutionResult(
            app_name=app_name,
            status=ExecutionStatus.SUCCESS,
            start_time=start_time,
            end_time=datetime.now(),
            rollback_data={"app_name": app_name, "type": app_config.type},
        )
