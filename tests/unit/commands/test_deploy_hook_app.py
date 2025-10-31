"""
Phase 4 deploy_hook_app() 함수 단위 테스트.

HookApp 배포 기능 검증.
"""

import pytest
from pathlib import Path
from unittest.mock import Mock, patch, MagicMock

from sbkube.commands.deploy import deploy_hook_app
from sbkube.models.config_model import HookApp


# ============================================================================
# deploy_hook_app() 기본 테스트
# ============================================================================


@patch("sbkube.commands.deploy.HookExecutor")
def test_deploy_hook_app_basic(mock_hook_executor_class):
    """기본 HookApp 배포 테스트."""
    # Mock HookExecutor
    mock_executor = MagicMock()
    mock_executor.execute_hook_tasks.return_value = True
    mock_hook_executor_class.return_value = mock_executor

    # HookApp 생성
    app = HookApp(
        type="hook",
        tasks=[
            {
                "type": "command",
                "name": "verify-deployment",
                "command": "kubectl get pods",
            }
        ],
    )

    # deploy_hook_app 호출
    result = deploy_hook_app(
        app_name="test-hook",
        app=app,
        base_dir=Path("/test"),
        app_config_dir=Path("/test/config"),
        namespace="default",
        dry_run=False,
    )

    # 검증
    assert result is True
    mock_hook_executor_class.assert_called_once()
    mock_executor.execute_hook_tasks.assert_called_once()

    # execute_hook_tasks 호출 인자 확인
    call_kwargs = mock_executor.execute_hook_tasks.call_args[1]
    assert call_kwargs["app_name"] == "test-hook"
    assert call_kwargs["hook_type"] == "hook_app_deploy"
    assert len(call_kwargs["tasks"]) == 1


@patch("sbkube.commands.deploy.HookExecutor")
def test_deploy_hook_app_with_multiple_tasks(mock_hook_executor_class):
    """여러 태스크를 가진 HookApp 배포 테스트."""
    mock_executor = MagicMock()
    mock_executor.execute_hook_tasks.return_value = True
    mock_hook_executor_class.return_value = mock_executor

    app = HookApp(
        type="hook",
        tasks=[
            {
                "type": "manifests",
                "name": "deploy-config",
                "files": ["config.yaml"],
            },
            {
                "type": "command",
                "name": "verify",
                "command": "kubectl get pods",
            },
            {
                "type": "inline",
                "name": "create-secret",
                "content": {"apiVersion": "v1", "kind": "Secret"},
            },
        ],
    )

    result = deploy_hook_app(
        app_name="multi-task-hook",
        app=app,
        base_dir=Path("/test"),
        app_config_dir=Path("/test/config"),
        namespace="default",
        dry_run=False,
    )

    assert result is True
    call_kwargs = mock_executor.execute_hook_tasks.call_args[1]
    assert len(call_kwargs["tasks"]) == 3


@patch("sbkube.commands.deploy.HookExecutor")
def test_deploy_hook_app_with_custom_namespace(mock_hook_executor_class):
    """커스텀 네임스페이스를 가진 HookApp 배포 테스트."""
    mock_executor = MagicMock()
    mock_executor.execute_hook_tasks.return_value = True
    mock_hook_executor_class.return_value = mock_executor

    app = HookApp(
        type="hook",
        tasks=[{"type": "command", "name": "test", "command": "echo test"}],
        namespace="custom-namespace",
    )

    result = deploy_hook_app(
        app_name="custom-ns-hook",
        app=app,
        base_dir=Path("/test"),
        app_config_dir=Path("/test/config"),
        namespace="default",  # 명령어 인자
        dry_run=False,
    )

    assert result is True

    # HookExecutor 초기화 시 앱의 namespace가 우선됨
    init_kwargs = mock_hook_executor_class.call_args[1]
    assert init_kwargs["namespace"] == "custom-namespace"


@patch("sbkube.commands.deploy.HookExecutor")
def test_deploy_hook_app_namespace_fallback(mock_hook_executor_class):
    """앱에 namespace가 없을 때 명령어 인자 사용 테스트."""
    mock_executor = MagicMock()
    mock_executor.execute_hook_tasks.return_value = True
    mock_hook_executor_class.return_value = mock_executor

    app = HookApp(
        type="hook",
        tasks=[{"type": "command", "name": "test", "command": "echo test"}],
        # namespace 지정 안 함
    )

    result = deploy_hook_app(
        app_name="fallback-ns-hook",
        app=app,
        base_dir=Path("/test"),
        app_config_dir=Path("/test/config"),
        namespace="fallback-namespace",
        dry_run=False,
    )

    assert result is True
    init_kwargs = mock_hook_executor_class.call_args[1]
    assert init_kwargs["namespace"] == "fallback-namespace"


@patch("sbkube.commands.deploy.HookExecutor")
def test_deploy_hook_app_with_kubeconfig(mock_hook_executor_class):
    """kubeconfig와 context가 있는 경우 테스트."""
    mock_executor = MagicMock()
    mock_executor.execute_hook_tasks.return_value = True
    mock_hook_executor_class.return_value = mock_executor

    app = HookApp(
        type="hook",
        tasks=[{"type": "command", "name": "test", "command": "echo test"}],
    )

    result = deploy_hook_app(
        app_name="kubeconfig-hook",
        app=app,
        base_dir=Path("/test"),
        app_config_dir=Path("/test/config"),
        kubeconfig="/path/to/kubeconfig",
        context="test-context",
        namespace="default",
        dry_run=False,
    )

    assert result is True
    init_kwargs = mock_hook_executor_class.call_args[1]
    assert init_kwargs["kubeconfig"] == "/path/to/kubeconfig"
    assert init_kwargs["context"] == "test-context"


@patch("sbkube.commands.deploy.HookExecutor")
def test_deploy_hook_app_dry_run(mock_hook_executor_class):
    """Dry-run 모드 테스트."""
    mock_executor = MagicMock()
    mock_executor.execute_hook_tasks.return_value = True
    mock_hook_executor_class.return_value = mock_executor

    app = HookApp(
        type="hook",
        tasks=[{"type": "command", "name": "test", "command": "echo test"}],
    )

    result = deploy_hook_app(
        app_name="dry-run-hook",
        app=app,
        base_dir=Path("/test"),
        app_config_dir=Path("/test/config"),
        namespace="default",
        dry_run=True,
    )

    assert result is True
    init_kwargs = mock_hook_executor_class.call_args[1]
    assert init_kwargs["dry_run"] is True


# ============================================================================
# 엣지 케이스 테스트
# ============================================================================


@patch("sbkube.commands.deploy.HookExecutor")
@patch("sbkube.commands.deploy.console")
def test_deploy_hook_app_empty_tasks(mock_console, mock_hook_executor_class):
    """빈 태스크 리스트 테스트 (경고 후 성공)."""
    mock_executor = MagicMock()
    mock_hook_executor_class.return_value = mock_executor

    app = HookApp(
        type="hook",
        tasks=[],  # 빈 태스크
    )

    result = deploy_hook_app(
        app_name="empty-tasks-hook",
        app=app,
        base_dir=Path("/test"),
        app_config_dir=Path("/test/config"),
        namespace="default",
        dry_run=False,
    )

    # 경고 메시지 출력 확인
    assert result is True
    mock_console.print.assert_any_call(
        "[yellow]⚠️  No tasks defined in Hook app, skipping[/yellow]"
    )
    # execute_hook_tasks는 호출되지 않음
    mock_executor.execute_hook_tasks.assert_not_called()


@patch("sbkube.commands.deploy.HookExecutor")
def test_deploy_hook_app_execution_failure(mock_hook_executor_class):
    """태스크 실행 실패 테스트."""
    mock_executor = MagicMock()
    mock_executor.execute_hook_tasks.return_value = False  # 실패
    mock_hook_executor_class.return_value = mock_executor

    app = HookApp(
        type="hook",
        tasks=[{"type": "command", "name": "fail", "command": "false"}],
    )

    result = deploy_hook_app(
        app_name="failing-hook",
        app=app,
        base_dir=Path("/test"),
        app_config_dir=Path("/test/config"),
        namespace="default",
        dry_run=False,
    )

    assert result is False
    mock_executor.execute_hook_tasks.assert_called_once()


@patch("sbkube.commands.deploy.HookExecutor")
def test_deploy_hook_app_context_passed(mock_hook_executor_class):
    """Hook context가 올바르게 전달되는지 테스트."""
    mock_executor = MagicMock()
    mock_executor.execute_hook_tasks.return_value = True
    mock_hook_executor_class.return_value = mock_executor

    app = HookApp(
        type="hook",
        tasks=[{"type": "command", "name": "test", "command": "echo test"}],
    )

    result = deploy_hook_app(
        app_name="context-hook",
        app=app,
        base_dir=Path("/test"),
        app_config_dir=Path("/test/config"),
        namespace="test-namespace",
        dry_run=True,
    )

    assert result is True
    call_kwargs = mock_executor.execute_hook_tasks.call_args[1]
    context = call_kwargs["context"]

    assert context["namespace"] == "test-namespace"
    assert context["app_name"] == "context-hook"
    assert context["dry_run"] is True


# ============================================================================
# Phase 3 기능 통합 테스트 (Validation, Dependency, Rollback)
# ============================================================================


@patch("sbkube.commands.deploy.HookExecutor")
def test_deploy_hook_app_with_phase3_features(mock_hook_executor_class):
    """Phase 3 기능(validation, dependency, rollback)을 가진 HookApp 테스트."""
    mock_executor = MagicMock()
    mock_executor.execute_hook_tasks.return_value = True
    mock_hook_executor_class.return_value = mock_executor

    app = HookApp(
        type="hook",
        tasks=[
            {
                "type": "manifests",
                "name": "deploy-config",
                "files": ["config.yaml"],
            }
        ],
        validation={
            "kind": "ConfigMap",
            "wait_for_ready": True,
            "timeout": 60,
        },
        dependency={
            "depends_on": ["database"],
            "wait_for": [{"kind": "Pod", "namespace": "default"}],
        },
        rollback={
            "enabled": True,
            "on_failure": "always",
            "commands": ["kubectl delete configmap test"],
        },
    )

    result = deploy_hook_app(
        app_name="phase3-hook",
        app=app,
        base_dir=Path("/test"),
        app_config_dir=Path("/test/config"),
        namespace="default",
        dry_run=False,
    )

    # Phase 3 기능은 HookApp 모델에 포함되지만
    # 실제 실행은 HookExecutor와 배포 로직에서 처리됨
    assert result is True
    assert app.validation is not None
    assert app.dependency is not None
    assert app.rollback is not None
