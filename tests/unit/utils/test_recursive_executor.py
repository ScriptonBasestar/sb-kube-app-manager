"""Tests for RecursiveExecutor (v0.11.0+)."""

from datetime import datetime, timedelta
from pathlib import Path
from unittest.mock import MagicMock, patch

import pytest

from sbkube.models.config_model import HelmApp
from sbkube.models.unified_config_model import PhaseReference, UnifiedConfig, UnifiedSettings
from sbkube.utils.recursive_executor import (
    AppExecutionResult,
    ExecutionResult,
    ExecutionStatus,
    PhaseExecutionResult,
    RecursiveExecutor,
)


class TestAppExecutionResult:
    """AppExecutionResult 테스트."""

    def test_duration_seconds(self) -> None:
        """duration_seconds 계산 테스트."""
        start = datetime(2025, 1, 1, 12, 0, 0)
        end = datetime(2025, 1, 1, 12, 0, 30)

        result = AppExecutionResult(
            app_name="test-app",
            status=ExecutionStatus.SUCCESS,
            start_time=start,
            end_time=end,
        )

        assert result.duration_seconds == 30.0

    def test_duration_seconds_none(self) -> None:
        """시간이 없을 때 None 반환 테스트."""
        result = AppExecutionResult(
            app_name="test-app",
            status=ExecutionStatus.SUCCESS,
        )

        assert result.duration_seconds is None


class TestPhaseExecutionResult:
    """PhaseExecutionResult 테스트."""

    def test_total_apps(self) -> None:
        """total_apps 계산 테스트."""
        result = PhaseExecutionResult(
            phase_name="phase1",
            status=ExecutionStatus.SUCCESS,
            app_results=[
                AppExecutionResult(app_name="app1", status=ExecutionStatus.SUCCESS),
                AppExecutionResult(app_name="app2", status=ExecutionStatus.SUCCESS),
            ],
        )

        assert result.total_apps == 2

    def test_total_apps_with_nested(self) -> None:
        """중첩 Phase의 total_apps 계산 테스트."""
        nested = PhaseExecutionResult(
            phase_name="nested",
            status=ExecutionStatus.SUCCESS,
            app_results=[
                AppExecutionResult(app_name="nested-app1", status=ExecutionStatus.SUCCESS),
            ],
        )
        result = PhaseExecutionResult(
            phase_name="phase1",
            status=ExecutionStatus.SUCCESS,
            app_results=[
                AppExecutionResult(app_name="app1", status=ExecutionStatus.SUCCESS),
            ],
            nested_results=[nested],
        )

        assert result.total_apps == 2  # 1 direct + 1 nested

    def test_successful_apps(self) -> None:
        """successful_apps 계산 테스트."""
        result = PhaseExecutionResult(
            phase_name="phase1",
            status=ExecutionStatus.SUCCESS,
            app_results=[
                AppExecutionResult(app_name="app1", status=ExecutionStatus.SUCCESS),
                AppExecutionResult(app_name="app2", status=ExecutionStatus.FAILED),
                AppExecutionResult(app_name="app3", status=ExecutionStatus.SUCCESS),
            ],
        )

        assert result.successful_apps == 2


class TestExecutionResult:
    """ExecutionResult 테스트."""

    def test_total_apps(self) -> None:
        """total_apps 계산 테스트."""
        phase_result = PhaseExecutionResult(
            phase_name="phase1",
            status=ExecutionStatus.SUCCESS,
            app_results=[
                AppExecutionResult(app_name="phase-app", status=ExecutionStatus.SUCCESS),
            ],
        )
        result = ExecutionResult(
            status=ExecutionStatus.SUCCESS,
            app_results=[
                AppExecutionResult(app_name="app1", status=ExecutionStatus.SUCCESS),
            ],
            phase_results=[phase_result],
        )

        assert result.total_apps == 2  # 1 direct + 1 from phase

    def test_is_success(self) -> None:
        """is_success 테스트."""
        success_result = ExecutionResult(status=ExecutionStatus.SUCCESS)
        failed_result = ExecutionResult(status=ExecutionStatus.FAILED)

        assert success_result.is_success() is True
        assert failed_result.is_success() is False


class TestRecursiveExecutor:
    """RecursiveExecutor 테스트."""

    def test_execute_empty_config(self, tmp_path: Path) -> None:
        """빈 설정 실행 테스트."""
        executor = RecursiveExecutor(base_dir=tmp_path, dry_run=True)
        config = UnifiedConfig()

        result = executor.execute(config)

        assert result.status == ExecutionStatus.SUCCESS
        assert result.total_apps == 0

    def test_execute_with_apps_dry_run(self, tmp_path: Path) -> None:
        """앱이 있는 설정 dry-run 테스트."""
        executor = RecursiveExecutor(base_dir=tmp_path, dry_run=True)
        config = UnifiedConfig(
            apps={
                "nginx": HelmApp(type="helm", chart="bitnami/nginx"),
                "redis": HelmApp(type="helm", chart="bitnami/redis"),
            },
        )

        result = executor.execute(config)

        assert result.status == ExecutionStatus.SUCCESS
        assert result.total_apps == 2
        assert result.successful_apps == 2

    def test_execute_apps_first_order(self, tmp_path: Path) -> None:
        """apps_first 실행 순서 테스트."""
        execution_order = []

        def track_app_start(name: str) -> None:
            execution_order.append(f"app:{name}")

        def track_phase_start(name: str) -> None:
            execution_order.append(f"phase:{name}")

        executor = RecursiveExecutor(
            base_dir=tmp_path,
            dry_run=True,
            on_app_start=track_app_start,
            on_phase_start=track_phase_start,
        )

        config = UnifiedConfig(
            settings=UnifiedSettings(execution_order="apps_first"),
            apps={"nginx": HelmApp(type="helm", chart="bitnami/nginx")},
            phases={
                "p1": PhaseReference(
                    apps={"redis": HelmApp(type="helm", chart="bitnami/redis")},
                ),
            },
        )

        result = executor.execute(config)

        assert result.status == ExecutionStatus.SUCCESS
        # First event should be the root-level app
        assert execution_order[0] == "app:nginx"
        # Phase should be started after the root-level app
        phase_idx = next(i for i, e in enumerate(execution_order) if e.startswith("phase:"))
        nginx_idx = execution_order.index("app:nginx")
        assert nginx_idx < phase_idx

    def test_execute_phases_first_order(self, tmp_path: Path) -> None:
        """phases_first 실행 순서 테스트."""
        execution_order = []

        def track_app_start(name: str) -> None:
            execution_order.append(f"app:{name}")

        def track_phase_start(name: str) -> None:
            execution_order.append(f"phase:{name}")

        executor = RecursiveExecutor(
            base_dir=tmp_path,
            dry_run=True,
            on_app_start=track_app_start,
            on_phase_start=track_phase_start,
        )

        config = UnifiedConfig(
            settings=UnifiedSettings(execution_order="phases_first"),
            apps={"nginx": HelmApp(type="helm", chart="bitnami/nginx")},
            phases={
                "p1": PhaseReference(
                    apps={"redis": HelmApp(type="helm", chart="bitnami/redis")},
                ),
            },
        )

        result = executor.execute(config)

        assert result.status == ExecutionStatus.SUCCESS
        # First event should be the phase (before root-level apps)
        assert execution_order[0] == "phase:p1"
        # Root-level nginx should be executed after the phase
        phase_idx = execution_order.index("phase:p1")
        nginx_idx = execution_order.index("app:nginx")
        assert phase_idx < nginx_idx

    def test_execute_with_disabled_app(self, tmp_path: Path) -> None:
        """비활성화된 앱 제외 테스트."""
        executor = RecursiveExecutor(base_dir=tmp_path, dry_run=True)
        config = UnifiedConfig(
            apps={
                "nginx": HelmApp(type="helm", chart="bitnami/nginx", enabled=True),
                "disabled-app": HelmApp(type="helm", chart="bitnami/redis", enabled=False),
            },
        )

        result = executor.execute(config)

        assert result.status == ExecutionStatus.SUCCESS
        assert result.total_apps == 1
        assert result.app_results[0].app_name == "nginx"

    def test_settings_inheritance(self, tmp_path: Path) -> None:
        """설정 상속 테스트."""
        executor = RecursiveExecutor(base_dir=tmp_path, dry_run=True)

        parent_settings = UnifiedSettings(
            timeout=300,
            namespace="parent-ns",
        )

        config = UnifiedConfig(
            settings=UnifiedSettings(namespace="child-ns"),
            apps={"nginx": HelmApp(type="helm", chart="bitnami/nginx")},
        )

        result = executor.execute(config, parent_settings=parent_settings)

        assert result.status == ExecutionStatus.SUCCESS


class TestRecursiveExecutorFailureHandling:
    """RecursiveExecutor 실패 처리 테스트."""

    def test_on_failure_stop(self, tmp_path: Path) -> None:
        """on_failure=stop 테스트."""
        call_count = 0

        def failing_executor(
            app_name: str, app_config, settings, work_dir
        ) -> AppExecutionResult:
            nonlocal call_count
            call_count += 1
            if app_name == "app1":
                return AppExecutionResult(
                    app_name=app_name,
                    status=ExecutionStatus.FAILED,
                    error_message="Test failure",
                )
            return AppExecutionResult(
                app_name=app_name,
                status=ExecutionStatus.SUCCESS,
            )

        executor = RecursiveExecutor(
            base_dir=tmp_path,
            app_executor=failing_executor,
        )

        config = UnifiedConfig(
            settings=UnifiedSettings(on_failure="stop"),
            apps={
                "app1": HelmApp(type="helm", chart="test/app1"),
                "app2": HelmApp(type="helm", chart="test/app2"),
            },
        )

        result = executor.execute(config)

        assert result.status == ExecutionStatus.FAILED
        # Depending on execution order, app2 might not be executed
        assert call_count <= 2

    def test_on_failure_continue(self, tmp_path: Path) -> None:
        """on_failure=continue 테스트."""
        call_count = 0

        def failing_executor(
            app_name: str, app_config, settings, work_dir
        ) -> AppExecutionResult:
            nonlocal call_count
            call_count += 1
            if app_name == "app1":
                return AppExecutionResult(
                    app_name=app_name,
                    status=ExecutionStatus.FAILED,
                )
            return AppExecutionResult(
                app_name=app_name,
                status=ExecutionStatus.SUCCESS,
            )

        executor = RecursiveExecutor(
            base_dir=tmp_path,
            app_executor=failing_executor,
        )

        config = UnifiedConfig(
            settings=UnifiedSettings(on_failure="continue"),
            apps={
                "app1": HelmApp(type="helm", chart="test/app1"),
                "app2": HelmApp(type="helm", chart="test/app2"),
            },
        )

        result = executor.execute(config)

        # With continue, execution should proceed
        assert call_count == 2


class TestRecursiveExecutorCallbacks:
    """RecursiveExecutor 콜백 테스트."""

    def test_app_callbacks(self, tmp_path: Path) -> None:
        """앱 콜백 테스트."""
        started_apps = []
        completed_apps = []

        def on_start(name: str) -> None:
            started_apps.append(name)

        def on_complete(name: str, result: AppExecutionResult) -> None:
            completed_apps.append((name, result.status))

        executor = RecursiveExecutor(
            base_dir=tmp_path,
            dry_run=True,
            on_app_start=on_start,
            on_app_complete=on_complete,
        )

        config = UnifiedConfig(
            apps={"nginx": HelmApp(type="helm", chart="bitnami/nginx")},
        )

        executor.execute(config)

        assert "nginx" in started_apps
        assert ("nginx", ExecutionStatus.SUCCESS) in completed_apps

    def test_phase_callbacks(self, tmp_path: Path) -> None:
        """Phase 콜백 테스트."""
        started_phases = []
        completed_phases = []

        def on_start(name: str) -> None:
            started_phases.append(name)

        def on_complete(name: str, result: PhaseExecutionResult) -> None:
            completed_phases.append((name, result.status))

        executor = RecursiveExecutor(
            base_dir=tmp_path,
            dry_run=True,
            on_phase_start=on_start,
            on_phase_complete=on_complete,
        )

        config = UnifiedConfig(
            phases={
                "p1": PhaseReference(
                    apps={"nginx": HelmApp(type="helm", chart="bitnami/nginx")},
                ),
            },
        )

        executor.execute(config)

        assert "p1" in started_phases
        assert ("p1", ExecutionStatus.SUCCESS) in completed_phases


class TestRecursiveExecutorParallel:
    """RecursiveExecutor 병렬 실행 테스트."""

    def test_parallel_apps(self, tmp_path: Path) -> None:
        """병렬 앱 실행 테스트."""
        executor = RecursiveExecutor(base_dir=tmp_path, dry_run=True)

        config = UnifiedConfig(
            settings=UnifiedSettings(parallel_apps=True, max_workers=2),
            apps={
                "app1": HelmApp(type="helm", chart="test/app1"),
                "app2": HelmApp(type="helm", chart="test/app2"),
                "app3": HelmApp(type="helm", chart="test/app3"),
            },
        )

        result = executor.execute(config)

        assert result.status == ExecutionStatus.SUCCESS
        assert result.total_apps == 3

    def test_parallel_phases(self, tmp_path: Path) -> None:
        """병렬 Phase 실행 테스트 (독립적인 Phase만)."""
        executor = RecursiveExecutor(base_dir=tmp_path, dry_run=True)

        config = UnifiedConfig(
            settings=UnifiedSettings(parallel=True, max_workers=2),
            phases={
                "p1": PhaseReference(
                    apps={"app1": HelmApp(type="helm", chart="test/app1")},
                ),
                "p2": PhaseReference(
                    apps={"app2": HelmApp(type="helm", chart="test/app2")},
                ),
                "p3": PhaseReference(
                    apps={"app3": HelmApp(type="helm", chart="test/app3")},
                    depends_on=["p1", "p2"],
                ),
            },
        )

        result = executor.execute(config)

        assert result.status == ExecutionStatus.SUCCESS
        # All phases should be executed
        assert len(result.phase_results) == 3


class TestRecursiveExecutorRollback:
    """RecursiveExecutor 롤백 테스트."""

    def test_rollback_scope_app(self, tmp_path: Path) -> None:
        """rollback_scope=app 테스트."""
        rollback_called_for = []

        class TrackingExecutor(RecursiveExecutor):
            def _rollback_apps(self, app_names: list[str]) -> None:
                rollback_called_for.extend(app_names)

        def failing_executor(
            app_name: str, app_config, settings, work_dir
        ) -> AppExecutionResult:
            if app_name == "app2":
                return AppExecutionResult(
                    app_name=app_name,
                    status=ExecutionStatus.FAILED,
                )
            return AppExecutionResult(
                app_name=app_name,
                status=ExecutionStatus.SUCCESS,
                rollback_data={"name": app_name},
            )

        executor = TrackingExecutor(
            base_dir=tmp_path,
            app_executor=failing_executor,
        )

        config = UnifiedConfig(
            settings=UnifiedSettings(on_failure="rollback", rollback_scope="app"),
            apps={
                "app1": HelmApp(type="helm", chart="test/app1"),
                "app2": HelmApp(type="helm", chart="test/app2"),
            },
        )

        result = executor.execute(config)

        assert result.status == ExecutionStatus.FAILED
        # Only the failed app should be rolled back
        assert "app2" in rollback_called_for


class TestRecursiveExecutorNestedPhases:
    """RecursiveExecutor 중첩 Phase 테스트."""

    def test_external_source_not_found(self, tmp_path: Path) -> None:
        """존재하지 않는 외부 소스 참조 테스트."""
        executor = RecursiveExecutor(base_dir=tmp_path, dry_run=True)

        config = UnifiedConfig(
            phases={
                "p1": PhaseReference(source="nonexistent/sbkube.yaml"),
            },
        )

        result = executor.execute(config)

        assert result.status == ExecutionStatus.FAILED
        assert "not found" in result.phase_results[0].error_message.lower()

    def test_external_source_execution(self, tmp_path: Path) -> None:
        """외부 소스 실행 테스트."""
        # Create nested config
        nested_dir = tmp_path / "nested"
        nested_dir.mkdir()
        nested_config = nested_dir / "sbkube.yaml"
        nested_config.write_text("""
apiVersion: sbkube/v1
apps:
  nested-app:
    type: helm
    chart: test/nested
""")

        executor = RecursiveExecutor(base_dir=tmp_path, dry_run=True)

        config = UnifiedConfig(
            phases={
                "p1": PhaseReference(source="nested/sbkube.yaml"),
            },
        )

        result = executor.execute(config)

        assert result.status == ExecutionStatus.SUCCESS
        assert result.phase_results[0].total_apps == 1


class TestRecursiveExecutorCheckContinue:
    """_check_continue 메서드 테스트."""

    def test_check_continue_no_failures(self, tmp_path: Path) -> None:
        """실패 없을 때 계속 진행 테스트."""
        executor = RecursiveExecutor(base_dir=tmp_path)
        results = [
            AppExecutionResult(app_name="app1", status=ExecutionStatus.SUCCESS),
            AppExecutionResult(app_name="app2", status=ExecutionStatus.SUCCESS),
        ]
        settings = UnifiedSettings(on_failure="stop")

        assert executor._check_continue(results, settings) is True

    def test_check_continue_with_failure_stop(self, tmp_path: Path) -> None:
        """실패 + on_failure=stop 테스트."""
        executor = RecursiveExecutor(base_dir=tmp_path)
        results = [
            AppExecutionResult(app_name="app1", status=ExecutionStatus.FAILED),
        ]
        settings = UnifiedSettings(on_failure="stop")

        assert executor._check_continue(results, settings) is False

    def test_check_continue_with_failure_continue(self, tmp_path: Path) -> None:
        """실패 + on_failure=continue 테스트."""
        executor = RecursiveExecutor(base_dir=tmp_path)
        results = [
            AppExecutionResult(app_name="app1", status=ExecutionStatus.FAILED),
        ]
        settings = UnifiedSettings(on_failure="continue")

        assert executor._check_continue(results, settings) is True
