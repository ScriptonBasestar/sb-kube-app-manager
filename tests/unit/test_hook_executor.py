"""
Hook executor 단위 테스트.

HookExecutor 클래스의 기능을 검증:
- 명령어 훅 실행
- 앱 훅 실행
- 환경 변수 주입
- Dry-run 모드
- 실패 처리
"""

import os
from pathlib import Path
from unittest.mock import MagicMock, patch

import pytest

from sbkube.utils.hook_executor import HookExecutor


@pytest.fixture
def tmp_workspace(tmp_path):
    """임시 작업 공간 생성."""
    base_dir = tmp_path / "workspace"
    config_dir = base_dir / "config"
    base_dir.mkdir()
    config_dir.mkdir()
    return base_dir, config_dir


def test_hook_executor_init(tmp_workspace):
    """HookExecutor 초기화 테스트."""
    base_dir, config_dir = tmp_workspace

    executor = HookExecutor(
        base_dir=base_dir,
        work_dir=config_dir,
        dry_run=False,
    )

    assert executor.base_dir == base_dir
    assert executor.work_dir == config_dir
    assert executor.dry_run is False


def test_hook_executor_dry_run_mode(tmp_workspace):
    """Dry-run 모드 테스트."""
    base_dir, config_dir = tmp_workspace

    executor = HookExecutor(
        base_dir=base_dir,
        work_dir=config_dir,
        dry_run=True,
    )

    # Dry-run 모드에서는 실제 실행하지 않음
    hooks = {"pre": ["echo 'test'"], "post": [], "on_failure": []}
    result = executor.execute_command_hooks(hooks, "pre", "test")

    assert result is True  # Dry-run은 항상 성공


def test_execute_command_hooks_success(tmp_workspace):
    """명령어 훅 실행 성공 테스트."""
    base_dir, config_dir = tmp_workspace

    executor = HookExecutor(
        base_dir=base_dir,
        work_dir=config_dir,
        dry_run=False,
    )

    hooks = {
        "pre": ["echo 'pre hook'"],
        "post": ["echo 'post hook'"],
        "on_failure": ["echo 'failure hook'"],
    }

    # Pre hook 실행
    result = executor.execute_command_hooks(hooks, "pre", "test")
    assert result is True

    # Post hook 실행
    result = executor.execute_command_hooks(hooks, "post", "test")
    assert result is True


def test_execute_command_hooks_failure(tmp_workspace):
    """명령어 훅 실행 실패 테스트."""
    base_dir, config_dir = tmp_workspace

    executor = HookExecutor(
        base_dir=base_dir,
        work_dir=config_dir,
        dry_run=False,
    )

    hooks = {
        "pre": ["exit 1"],  # 실패하는 명령어
        "post": [],
        "on_failure": [],
    }

    # Pre hook 실행 실패
    result = executor.execute_command_hooks(hooks, "pre", "test")
    assert result is False


def test_execute_app_hook_with_context(tmp_workspace):
    """앱 훅 실행 (컨텍스트 포함) 테스트."""
    base_dir, config_dir = tmp_workspace

    executor = HookExecutor(
        base_dir=base_dir,
        work_dir=config_dir,
        dry_run=False,
    )

    app_hooks = {
        "pre_prepare": ["echo $SBKUBE_APP_NAME"],
        "post_prepare": [],
        "pre_build": [],
        "post_build": [],
        "pre_deploy": [],
        "post_deploy": [],
        "on_deploy_failure": [],
    }

    context = {
        "namespace": "test-ns",
        "release_name": "test-release",
    }

    # Pre-prepare hook 실행
    result = executor.execute_app_hook(
        "test-app",
        app_hooks,
        "pre_prepare",
        context=context,
    )

    assert result is True


def test_execute_app_hook_environment_variables(tmp_workspace):
    """앱 훅 환경 변수 주입 테스트."""
    base_dir, config_dir = tmp_workspace

    executor = HookExecutor(
        base_dir=base_dir,
        work_dir=config_dir,
        dry_run=False,
    )

    # 환경 변수를 출력하는 스크립트 생성
    script_path = config_dir / "check_env.sh"
    script_path.write_text(
        "#!/bin/bash\n"
        "echo APP_NAME=$SBKUBE_APP_NAME\n"
        "echo NAMESPACE=$SBKUBE_NAMESPACE\n"
        "echo RELEASE_NAME=$SBKUBE_RELEASE_NAME\n"
    )
    script_path.chmod(0o755)

    app_hooks = {
        "pre_deploy": [str(script_path)],
        "post_deploy": [],
        "on_deploy_failure": [],
    }

    context = {
        "namespace": "production",
        "release_name": "my-app-release",
    }

    # Pre-deploy hook 실행
    result = executor.execute_app_hook(
        "my-app",
        app_hooks,
        "pre_deploy",
        context=context,
    )

    assert result is True


def test_execute_command_hooks_empty_list(tmp_workspace):
    """빈 훅 리스트 테스트."""
    base_dir, config_dir = tmp_workspace

    executor = HookExecutor(
        base_dir=base_dir,
        work_dir=config_dir,
        dry_run=False,
    )

    hooks = {
        "pre": [],
        "post": [],
        "on_failure": [],
    }

    # 빈 훅 리스트는 항상 성공
    result = executor.execute_command_hooks(hooks, "pre", "test")
    assert result is True


def test_execute_app_hook_none(tmp_workspace):
    """None 훅 테스트."""
    base_dir, config_dir = tmp_workspace

    executor = HookExecutor(
        base_dir=base_dir,
        work_dir=config_dir,
        dry_run=False,
    )

    # None 훅은 항상 성공
    result = executor.execute_app_hook(
        "test-app",
        None,
        "pre_deploy",
        context=None,
    )

    assert result is True


def test_execute_command_hooks_invalid_phase(tmp_workspace):
    """잘못된 훅 단계 테스트."""
    base_dir, config_dir = tmp_workspace

    executor = HookExecutor(
        base_dir=base_dir,
        work_dir=config_dir,
        dry_run=False,
    )

    hooks = {
        "pre": ["echo 'test'"],
        "post": [],
        "on_failure": [],
    }

    # 존재하지 않는 단계는 빈 리스트로 처리
    result = executor.execute_command_hooks(hooks, "invalid_phase", "test")
    assert result is True


def test_execute_app_hook_multiple_hooks(tmp_workspace):
    """여러 훅 순차 실행 테스트."""
    base_dir, config_dir = tmp_workspace

    executor = HookExecutor(
        base_dir=base_dir,
        work_dir=config_dir,
        dry_run=False,
    )

    app_hooks = {
        "pre_deploy": [
            "echo 'hook 1'",
            "echo 'hook 2'",
            "echo 'hook 3'",
        ],
        "post_deploy": [],
        "on_deploy_failure": [],
    }

    # 여러 훅 순차 실행
    result = executor.execute_app_hook(
        "test-app",
        app_hooks,
        "pre_deploy",
    )

    assert result is True


def test_execute_app_hook_first_failure_stops(tmp_workspace):
    """첫 번째 훅 실패 시 중단 테스트."""
    base_dir, config_dir = tmp_workspace

    executor = HookExecutor(
        base_dir=base_dir,
        work_dir=config_dir,
        dry_run=False,
    )

    app_hooks = {
        "pre_deploy": [
            "echo 'hook 1'",
            "exit 1",  # 실패
            "echo 'hook 3'",  # 실행되지 않아야 함
        ],
        "post_deploy": [],
        "on_deploy_failure": [],
    }

    # 첫 번째 실패 시 중단
    result = executor.execute_app_hook(
        "test-app",
        app_hooks,
        "pre_deploy",
    )

    assert result is False


def test_hook_executor_timeout(tmp_workspace):
    """훅 타임아웃 테스트."""
    base_dir, config_dir = tmp_workspace

    executor = HookExecutor(
        base_dir=base_dir,
        work_dir=config_dir,
        dry_run=False,
    )

    hooks = {
        "pre": ["sleep 1"],  # 1초 대기
        "post": [],
        "on_failure": [],
    }

    # 짧은 타임아웃 시간 내에 완료되어야 함
    result = executor.execute_command_hooks(hooks, "pre", "test")
    assert result is True
