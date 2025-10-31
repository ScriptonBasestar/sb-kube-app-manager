"""
Phase 3 HookExecutor 기능 테스트.

Validation, Dependency, Rollback 기능 검증.
"""

import pytest
from pathlib import Path
from unittest.mock import Mock, patch, MagicMock
from sbkube.utils.hook_executor import HookExecutor


# ============================================================================
# Validation 테스트
# ============================================================================


@patch("sbkube.utils.hook_executor.run_command")
@patch("sbkube.utils.hook_executor.apply_cluster_config_to_command")
def test_validate_task_result_simple(mock_apply_config, mock_run_command):
    """간단한 validation (kind만 지정) 테스트."""
    mock_apply_config.side_effect = lambda cmd, *args: cmd
    mock_run_command.return_value = (0, "clusterissuer.cert-manager.io/letsencrypt-prd created", "")

    executor = HookExecutor(base_dir=Path("/test"), dry_run=False)

    task = {
        "name": "test-task",
        "validation": {
            "kind": "ClusterIssuer",
        },
    }

    result = executor._validate_task_result("test-app", task)
    assert result is True
    assert mock_run_command.called


@patch("sbkube.utils.hook_executor.run_command")
@patch("sbkube.utils.hook_executor.apply_cluster_config_to_command")
def test_validate_task_result_wait_for_ready(mock_apply_config, mock_run_command):
    """wait_for_ready=True 검증 테스트."""
    mock_apply_config.side_effect = lambda cmd, *args: cmd
    mock_run_command.return_value = (0, "condition met", "")

    executor = HookExecutor(base_dir=Path("/test"), dry_run=False)

    task = {
        "name": "test-task",
        "validation": {
            "kind": "ClusterIssuer",
            "name": "letsencrypt-prd",
            "wait_for_ready": True,
            "timeout": 120,
        },
    }

    result = executor._validate_task_result("test-app", task)
    assert result is True

    # kubectl wait 명령어 호출 확인
    call_args = mock_run_command.call_args[0][0]
    assert "kubectl" in call_args
    assert "wait" in call_args
    assert "clusterissuer" in call_args
    assert "letsencrypt-prd" in call_args
    assert "--for=condition=Ready" in call_args
    assert "--timeout=120s" in call_args


@patch("sbkube.utils.hook_executor.run_command")
@patch("sbkube.utils.hook_executor.apply_cluster_config_to_command")
def test_validate_task_result_with_conditions(mock_apply_config, mock_run_command):
    """조건부 validation 테스트."""
    mock_apply_config.side_effect = lambda cmd, *args: cmd
    mock_run_command.return_value = (0, "condition met", "")

    executor = HookExecutor(base_dir=Path("/test"), dry_run=False)

    task = {
        "name": "test-task",
        "validation": {
            "kind": "Pod",
            "wait_for_ready": True,
            "conditions": [
                {"type": "Ready", "status": "True"},
                {"type": "ContainersReady", "status": "True"},
            ],
        },
    }

    result = executor._validate_task_result("test-app", task)
    assert result is True


@patch("sbkube.utils.hook_executor.run_command")
@patch("sbkube.utils.hook_executor.apply_cluster_config_to_command")
def test_validate_task_result_failure(mock_apply_config, mock_run_command):
    """Validation 실패 테스트."""
    mock_apply_config.side_effect = lambda cmd, *args: cmd
    mock_run_command.return_value = (1, "", "Error: timed out waiting for the condition")

    executor = HookExecutor(base_dir=Path("/test"), dry_run=False)

    task = {
        "name": "test-task",
        "validation": {
            "kind": "ClusterIssuer",
            "wait_for_ready": True,
            "timeout": 60,
        },
    }

    result = executor._validate_task_result("test-app", task)
    assert result is False


def test_validate_task_result_no_validation():
    """validation 필드가 없는 경우 테스트."""
    executor = HookExecutor(base_dir=Path("/test"), dry_run=False)

    task = {"name": "test-task"}  # validation 없음

    result = executor._validate_task_result("test-app", task)
    assert result is True  # validation 없으면 성공


# ============================================================================
# Dependency 테스트
# ============================================================================


def test_check_task_dependencies_depends_on_success():
    """depends_on 성공 테스트."""
    executor = HookExecutor(base_dir=Path("/test"), dry_run=False)

    task = {
        "name": "task-b",
        "dependency": {
            "depends_on": ["task-a"],
        },
    }

    completed_tasks = {"task-a"}  # task-a가 완료됨

    result = executor._check_task_dependencies("test-app", task, completed_tasks)
    assert result is True


def test_check_task_dependencies_depends_on_failure():
    """depends_on 실패 테스트 (의존 task 미완료)."""
    executor = HookExecutor(base_dir=Path("/test"), dry_run=False)

    task = {
        "name": "task-b",
        "dependency": {
            "depends_on": ["task-a"],
        },
    }

    completed_tasks = set()  # task-a가 완료되지 않음

    result = executor._check_task_dependencies("test-app", task, completed_tasks)
    assert result is False


@patch("sbkube.utils.hook_executor.run_command")
@patch("sbkube.utils.hook_executor.apply_cluster_config_to_command")
def test_check_task_dependencies_wait_for(mock_apply_config, mock_run_command):
    """wait_for 성공 테스트."""
    mock_apply_config.side_effect = lambda cmd, *args: cmd
    mock_run_command.return_value = (0, "condition met", "")

    executor = HookExecutor(base_dir=Path("/test"), dry_run=False)

    task = {
        "name": "task-c",
        "dependency": {
            "wait_for": [
                {
                    "kind": "Pod",
                    "label_selector": "app=database",
                    "condition": "Ready",
                    "timeout": 180,
                }
            ],
        },
    }

    result = executor._check_task_dependencies("test-app", task, set())
    assert result is True

    # kubectl wait 명령어 호출 확인
    call_args = mock_run_command.call_args[0][0]
    assert "kubectl" in call_args
    assert "wait" in call_args
    assert "pod" in call_args
    assert "--selector" in call_args
    assert "app=database" in call_args
    assert "--for=condition=Ready" in call_args


@patch("sbkube.utils.hook_executor.run_command")
@patch("sbkube.utils.hook_executor.apply_cluster_config_to_command")
def test_check_task_dependencies_wait_for_failure(mock_apply_config, mock_run_command):
    """wait_for 실패 테스트 (timeout)."""
    mock_apply_config.side_effect = lambda cmd, *args: cmd
    mock_run_command.return_value = (1, "", "Error: timed out")

    executor = HookExecutor(base_dir=Path("/test"), dry_run=False)

    task = {
        "name": "task-c",
        "dependency": {
            "wait_for": [
                {"kind": "Pod", "condition": "Ready", "timeout": 30}
            ],
        },
    }

    result = executor._check_task_dependencies("test-app", task, set())
    assert result is False


def test_check_task_dependencies_no_dependency():
    """dependency 필드가 없는 경우 테스트."""
    executor = HookExecutor(base_dir=Path("/test"), dry_run=False)

    task = {"name": "task-a"}  # dependency 없음

    result = executor._check_task_dependencies("test-app", task, set())
    assert result is True


# ============================================================================
# Rollback 테스트
# ============================================================================


@patch("sbkube.utils.hook_executor.HookExecutor._deploy_manifests")
def test_execute_rollback_manifests(mock_deploy_manifests):
    """Rollback manifests 실행 테스트."""
    mock_deploy_manifests.return_value = True

    executor = HookExecutor(base_dir=Path("/test"), dry_run=False)

    task = {
        "name": "failed-task",
        "rollback": {
            "enabled": True,
            "on_failure": "always",
            "manifests": ["manifests/cleanup.yaml"],
        },
    }

    result = executor._execute_rollback("test-app", task)
    assert result is True
    assert mock_deploy_manifests.called


@patch("sbkube.utils.hook_executor.HookExecutor._execute_single_command")
def test_execute_rollback_commands(mock_execute_command):
    """Rollback commands 실행 테스트."""
    mock_execute_command.return_value = True

    executor = HookExecutor(base_dir=Path("/test"), dry_run=False)

    task = {
        "name": "failed-task",
        "rollback": {
            "enabled": True,
            "on_failure": "always",
            "commands": ["kubectl delete certificate wildcard-cert"],
        },
    }

    result = executor._execute_rollback("test-app", task)
    assert result is True
    assert mock_execute_command.called


def test_execute_rollback_manual():
    """Rollback on_failure=manual 테스트 (실행 안 함)."""
    executor = HookExecutor(base_dir=Path("/test"), dry_run=False)

    task = {
        "name": "failed-task",
        "rollback": {
            "enabled": True,
            "on_failure": "manual",
            "manifests": ["manifests/cleanup.yaml"],
        },
    }

    result = executor._execute_rollback("test-app", task)
    assert result is True  # manual이므로 자동 실행 안 함


def test_execute_rollback_never():
    """Rollback on_failure=never 테스트."""
    executor = HookExecutor(base_dir=Path("/test"), dry_run=False)

    task = {
        "name": "failed-task",
        "rollback": {
            "enabled": True,
            "on_failure": "never",
            "manifests": ["manifests/cleanup.yaml"],
        },
    }

    result = executor._execute_rollback("test-app", task)
    assert result is True


def test_execute_rollback_disabled():
    """Rollback enabled=False 테스트."""
    executor = HookExecutor(base_dir=Path("/test"), dry_run=False)

    task = {
        "name": "failed-task",
        "rollback": {
            "enabled": False,
            "manifests": ["manifests/cleanup.yaml"],
        },
    }

    result = executor._execute_rollback("test-app", task)
    assert result is True  # enabled=False이므로 실행 안 함


def test_execute_rollback_no_rollback():
    """rollback 필드가 없는 경우 테스트."""
    executor = HookExecutor(base_dir=Path("/test"), dry_run=False)

    task = {"name": "test-task"}  # rollback 없음

    result = executor._execute_rollback("test-app", task)
    assert result is True


# ============================================================================
# 통합 시나리오 테스트
# ============================================================================


@patch("sbkube.utils.hook_executor.HookExecutor._execute_single_task")
@patch("sbkube.utils.hook_executor.HookExecutor._validate_task_result")
@patch("sbkube.utils.hook_executor.HookExecutor._check_task_dependencies")
@patch("sbkube.utils.hook_executor.HookExecutor._execute_rollback")
def test_execute_hook_tasks_with_phase3(
    mock_rollback, mock_check_deps, mock_validate, mock_execute_task
):
    """Phase 3 기능 통합 테스트 (전체 워크플로우)."""
    # 모든 단계 성공
    mock_check_deps.return_value = True
    mock_execute_task.return_value = True
    mock_validate.return_value = True

    executor = HookExecutor(base_dir=Path("/test"), dry_run=False)

    tasks = [
        {
            "type": "manifests",
            "name": "task-a",
            "files": ["manifests/a.yaml"],
        },
        {
            "type": "command",
            "name": "task-b",
            "command": "echo hello",
            "dependency": {"depends_on": ["task-a"]},
        },
    ]

    result = executor.execute_hook_tasks("test-app", tasks, "post_deploy")
    assert result is True

    # task-a와 task-b 모두 실행됨
    assert mock_execute_task.call_count == 2
    assert mock_validate.call_count == 2
    assert mock_check_deps.call_count == 2
    assert not mock_rollback.called  # 실패 없으므로 rollback 안 함


@patch("sbkube.utils.hook_executor.HookExecutor._execute_single_task")
@patch("sbkube.utils.hook_executor.HookExecutor._validate_task_result")
@patch("sbkube.utils.hook_executor.HookExecutor._check_task_dependencies")
@patch("sbkube.utils.hook_executor.HookExecutor._execute_rollback")
def test_execute_hook_tasks_dependency_failure(
    mock_rollback, mock_check_deps, mock_validate, mock_execute_task
):
    """Dependency 실패 시 rollback 실행 테스트."""
    # Dependency 체크 실패
    mock_check_deps.side_effect = [True, False]  # task-b의 dependency 실패
    mock_execute_task.return_value = True
    mock_validate.return_value = True
    mock_rollback.return_value = True

    executor = HookExecutor(base_dir=Path("/test"), dry_run=False)

    tasks = [
        {"type": "manifests", "name": "task-a", "files": ["a.yaml"]},
        {
            "type": "command",
            "name": "task-b",
            "command": "echo hello",
            "dependency": {"depends_on": ["task-c"]},  # 존재하지 않는 task에 의존
            "rollback": {"enabled": True, "commands": ["echo rollback"]},
        },
    ]

    result = executor.execute_hook_tasks("test-app", tasks, "post_deploy")
    assert result is False  # dependency 실패로 전체 실패
    assert mock_rollback.called  # rollback 실행됨


@patch("sbkube.utils.hook_executor.HookExecutor._execute_single_task")
@patch("sbkube.utils.hook_executor.HookExecutor._validate_task_result")
@patch("sbkube.utils.hook_executor.HookExecutor._check_task_dependencies")
@patch("sbkube.utils.hook_executor.HookExecutor._execute_rollback")
def test_execute_hook_tasks_validation_failure(
    mock_rollback, mock_check_deps, mock_validate, mock_execute_task
):
    """Validation 실패 시 rollback 실행 테스트."""
    mock_check_deps.return_value = True
    mock_execute_task.return_value = True
    mock_validate.return_value = False  # validation 실패
    mock_rollback.return_value = True

    executor = HookExecutor(base_dir=Path("/test"), dry_run=False)

    tasks = [
        {
            "type": "manifests",
            "name": "task-a",
            "files": ["a.yaml"],
            "validation": {"kind": "ClusterIssuer", "wait_for_ready": True},
            "rollback": {"enabled": True, "manifests": ["cleanup.yaml"]},
        }
    ]

    result = executor.execute_hook_tasks("test-app", tasks, "post_deploy")
    assert result is False  # validation 실패로 전체 실패
    assert mock_rollback.called  # rollback 실행됨
