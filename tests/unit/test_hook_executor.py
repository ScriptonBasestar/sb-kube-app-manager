"""Hook executor 단위 테스트.

HookExecutor 클래스의 기능을 검증:
- 명령어 훅 실행
- 앱 훅 실행
- 환경 변수 주입
- Dry-run 모드
- 실패 처리
"""

from unittest.mock import patch

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


# ============================================================================
# Phase 1: Manifests 지원 테스트
# ============================================================================


def test_execute_app_hook_with_manifests_shell_only(tmp_workspace):
    """Shell 명령어만 있는 경우 테스트 (기존 동작 유지)."""
    base_dir, config_dir = tmp_workspace

    executor = HookExecutor(
        base_dir=base_dir,
        work_dir=config_dir,
        dry_run=False,
    )

    app_hooks = {
        "post_deploy": ["echo 'deployed'"],
        "post_deploy_manifests": [],  # 빈 manifests
    }

    result = executor.execute_app_hook_with_manifests(
        "test-app",
        app_hooks,
        "post_deploy",
    )

    assert result is True


def test_execute_app_hook_with_manifests_dry_run(tmp_workspace):
    """Manifests hooks dry-run 모드 테스트."""
    base_dir, config_dir = tmp_workspace

    # 테스트용 manifest 파일 생성
    manifest_file = config_dir / "test-manifest.yaml"
    manifest_file.write_text(
        """apiVersion: v1
kind: ConfigMap
metadata:
  name: test-config
data:
  key: value
"""
    )

    executor = HookExecutor(
        base_dir=base_dir,
        work_dir=config_dir,
        dry_run=True,  # Dry-run 모드
        kubeconfig=None,
        context=None,
        namespace="test-ns",
    )

    app_hooks = {
        "post_deploy": [],
        "post_deploy_manifests": ["test-manifest.yaml"],
    }

    # Dry-run 모드에서는 실제 kubectl 실행 없이 성공
    with patch("sbkube.utils.hook_executor.run_command") as mock_run:
        mock_run.return_value = (0, "configmap/test-config configured (dry run)", "")

        result = executor.execute_app_hook_with_manifests(
            "test-app",
            app_hooks,
            "post_deploy",
            context={"namespace": "test-ns"},
        )

        assert result is True
        # kubectl apply --dry-run=client 명령어가 호출되었는지 확인
        assert mock_run.called


def test_execute_app_hook_with_manifests_file_not_found(tmp_workspace):
    """Manifest 파일이 없는 경우 테스트."""
    base_dir, config_dir = tmp_workspace

    executor = HookExecutor(
        base_dir=base_dir,
        work_dir=config_dir,
        dry_run=False,
        kubeconfig=None,
        context=None,
        namespace="test-ns",
    )

    app_hooks = {
        "post_deploy": [],
        "post_deploy_manifests": ["non-existent.yaml"],  # 존재하지 않는 파일
    }

    result = executor.execute_app_hook_with_manifests(
        "test-app",
        app_hooks,
        "post_deploy",
        context={"namespace": "test-ns"},
    )

    assert result is False  # 실패해야 함


def test_execute_app_hook_with_manifests_success(tmp_workspace):
    """Manifests hooks 성공 테스트."""
    base_dir, config_dir = tmp_workspace

    # 테스트용 manifest 파일 생성
    manifest_file = config_dir / "test-manifest.yaml"
    manifest_file.write_text(
        """apiVersion: v1
kind: ConfigMap
metadata:
  name: test-config
data:
  key: value
"""
    )

    executor = HookExecutor(
        base_dir=base_dir,
        work_dir=config_dir,
        dry_run=False,
        kubeconfig=None,
        context=None,
        namespace="test-ns",
    )

    app_hooks = {
        "post_deploy": [],
        "post_deploy_manifests": ["test-manifest.yaml"],
    }

    # kubectl apply 명령어 실행을 mock
    with patch("sbkube.utils.hook_executor.run_command") as mock_run:
        mock_run.return_value = (0, "configmap/test-config created", "")

        result = executor.execute_app_hook_with_manifests(
            "test-app",
            app_hooks,
            "post_deploy",
            context={"namespace": "test-ns"},
        )

        assert result is True
        assert mock_run.called


def test_execute_app_hook_with_manifests_both_shell_and_manifests(tmp_workspace):
    """Shell 명령어와 manifests 모두 있는 경우 테스트."""
    base_dir, config_dir = tmp_workspace

    # 테스트용 manifest 파일 생성
    manifest_file = config_dir / "test-manifest.yaml"
    manifest_file.write_text(
        """apiVersion: v1
kind: ConfigMap
metadata:
  name: test-config
data:
  key: value
"""
    )

    executor = HookExecutor(
        base_dir=base_dir,
        work_dir=config_dir,
        dry_run=False,
        kubeconfig=None,
        context=None,
        namespace="test-ns",
    )

    app_hooks = {
        "post_deploy": ["echo 'deploying'"],  # Shell 명령어
        "post_deploy_manifests": ["test-manifest.yaml"],  # Manifests
    }

    # kubectl apply 명령어 실행을 mock
    with patch("sbkube.utils.hook_executor.run_command") as mock_run:
        mock_run.return_value = (0, "configmap/test-config created", "")

        result = executor.execute_app_hook_with_manifests(
            "test-app",
            app_hooks,
            "post_deploy",
            context={"namespace": "test-ns"},
        )

        assert result is True
        # Shell 명령어와 kubectl apply 모두 실행되어야 함
        assert mock_run.called


def test_execute_app_hook_with_manifests_multiple_files(tmp_workspace):
    """여러 manifest 파일 배포 테스트."""
    base_dir, config_dir = tmp_workspace

    # 여러 테스트용 manifest 파일 생성
    manifest1 = config_dir / "manifest1.yaml"
    manifest1.write_text(
        """apiVersion: v1
kind: ConfigMap
metadata:
  name: config1
"""
    )

    manifest2 = config_dir / "manifest2.yaml"
    manifest2.write_text(
        """apiVersion: v1
kind: Secret
metadata:
  name: secret1
"""
    )

    executor = HookExecutor(
        base_dir=base_dir,
        work_dir=config_dir,
        dry_run=False,
        kubeconfig=None,
        context=None,
        namespace="test-ns",
    )

    app_hooks = {
        "post_deploy": [],
        "post_deploy_manifests": ["manifest1.yaml", "manifest2.yaml"],
    }

    # kubectl apply 명령어 실행을 mock
    with patch("sbkube.utils.hook_executor.run_command") as mock_run:
        mock_run.return_value = (0, "created", "")

        result = executor.execute_app_hook_with_manifests(
            "test-app",
            app_hooks,
            "post_deploy",
            context={"namespace": "test-ns"},
        )

        assert result is True
        # 2개 파일에 대해 kubectl apply가 2번 호출되어야 함
        assert mock_run.call_count == 2


# ============================================================================
# Phase 2: Hook Tasks 실행 테스트
# ============================================================================


def test_execute_hook_tasks_manifests_type(tmp_workspace):
    """Manifests 타입 task 실행 테스트."""
    base_dir, config_dir = tmp_workspace

    # 테스트용 manifest 파일 생성
    manifest_file = config_dir / "test-manifest.yaml"
    manifest_file.write_text(
        """apiVersion: v1
kind: ConfigMap
metadata:
  name: test-config
"""
    )

    executor = HookExecutor(
        base_dir=base_dir,
        work_dir=config_dir,
        dry_run=False,
        kubeconfig=None,
        context=None,
        namespace="test-ns",
    )

    tasks = [
        {
            "type": "manifests",
            "name": "deploy-config",
            "files": ["test-manifest.yaml"],
        }
    ]

    # kubectl apply 명령어 실행을 mock
    with patch("sbkube.utils.hook_executor.run_command") as mock_run:
        mock_run.return_value = (0, "configmap/test-config created", "")

        result = executor.execute_hook_tasks(
            app_name="test-app",
            tasks=tasks,
            hook_type="post_deploy",
            context={"namespace": "test-ns"},
        )

        assert result is True
        assert mock_run.called


def test_execute_hook_tasks_inline_type(tmp_workspace):
    """Inline 타입 task 실행 테스트."""
    base_dir, config_dir = tmp_workspace

    executor = HookExecutor(
        base_dir=base_dir,
        work_dir=config_dir,
        dry_run=False,
        kubeconfig=None,
        context=None,
        namespace="test-ns",
    )

    tasks = [
        {
            "type": "inline",
            "name": "create-config",
            "content": {
                "apiVersion": "v1",
                "kind": "ConfigMap",
                "metadata": {"name": "inline-config"},
                "data": {"key": "value"},
            },
        }
    ]

    # kubectl apply 명령어 실행을 mock
    with patch("sbkube.utils.hook_executor.run_command") as mock_run:
        mock_run.return_value = (0, "configmap/inline-config created", "")

        result = executor.execute_hook_tasks(
            app_name="test-app",
            tasks=tasks,
            hook_type="post_deploy",
            context={"namespace": "test-ns"},
        )

        assert result is True
        assert mock_run.called


def test_execute_hook_tasks_command_type(tmp_workspace):
    """Command 타입 task 실행 테스트."""
    base_dir, config_dir = tmp_workspace

    executor = HookExecutor(
        base_dir=base_dir,
        work_dir=config_dir,
        dry_run=False,
    )

    tasks = [
        {
            "type": "command",
            "name": "echo-test",
            "command": "echo 'test'",
        }
    ]

    result = executor.execute_hook_tasks(
        app_name="test-app",
        tasks=tasks,
        hook_type="post_deploy",
    )

    assert result is True


def test_execute_hook_tasks_command_with_retry(tmp_workspace):
    """Command 타입 task retry 테스트."""
    base_dir, config_dir = tmp_workspace

    executor = HookExecutor(
        base_dir=base_dir,
        work_dir=config_dir,
        dry_run=False,
        timeout=10,
    )

    tasks = [
        {
            "type": "command",
            "name": "flaky-command",
            "command": "exit 1",  # 항상 실패
            "retry": {"max_attempts": 2, "delay": 0},
            "on_failure": "warn",  # 실패해도 계속
        }
    ]

    result = executor.execute_hook_tasks(
        app_name="test-app",
        tasks=tasks,
        hook_type="post_deploy",
    )

    # on_failure=warn이므로 실패해도 True 반환
    assert result is True


def test_execute_hook_tasks_mixed_types(tmp_workspace):
    """여러 타입 task 혼합 실행 테스트."""
    base_dir, config_dir = tmp_workspace

    # 테스트용 manifest 파일 생성
    manifest_file = config_dir / "test-manifest.yaml"
    manifest_file.write_text(
        """apiVersion: v1
kind: ConfigMap
metadata:
  name: test-config
"""
    )

    executor = HookExecutor(
        base_dir=base_dir,
        work_dir=config_dir,
        dry_run=False,
        kubeconfig=None,
        context=None,
        namespace="test-ns",
    )

    tasks = [
        # Task 1: manifests
        {
            "type": "manifests",
            "name": "deploy-config",
            "files": ["test-manifest.yaml"],
        },
        # Task 2: inline
        {
            "type": "inline",
            "name": "create-inline-config",
            "content": {
                "apiVersion": "v1",
                "kind": "ConfigMap",
                "metadata": {"name": "inline-config"},
            },
        },
        # Task 3: command
        {
            "type": "command",
            "name": "verify",
            "command": "echo 'verified'",
        },
    ]

    # kubectl apply 명령어 실행을 mock
    with patch("sbkube.utils.hook_executor.run_command") as mock_run:
        mock_run.return_value = (0, "created", "")

        result = executor.execute_hook_tasks(
            app_name="test-app",
            tasks=tasks,
            hook_type="post_deploy",
            context={"namespace": "test-ns"},
        )

        assert result is True
        # manifests + inline = 2번 kubectl apply 호출
        assert mock_run.call_count == 2


def test_execute_hook_tasks_failure_stops(tmp_workspace):
    """Task 실패 시 중단 테스트."""
    base_dir, config_dir = tmp_workspace

    executor = HookExecutor(
        base_dir=base_dir,
        work_dir=config_dir,
        dry_run=False,
    )

    tasks = [
        {
            "type": "command",
            "name": "success-task",
            "command": "echo 'success'",
        },
        {
            "type": "command",
            "name": "fail-task",
            "command": "exit 1",  # 실패
            "on_failure": "fail",  # 중단
        },
        {
            "type": "command",
            "name": "should-not-run",
            "command": "echo 'should not run'",
        },
    ]

    result = executor.execute_hook_tasks(
        app_name="test-app",
        tasks=tasks,
        hook_type="post_deploy",
    )

    # 두 번째 task에서 실패하므로 False
    assert result is False


def test_execute_hook_tasks_empty_list(tmp_workspace):
    """빈 task 리스트 테스트."""
    base_dir, config_dir = tmp_workspace

    executor = HookExecutor(
        base_dir=base_dir,
        work_dir=config_dir,
        dry_run=False,
    )

    result = executor.execute_hook_tasks(
        app_name="test-app",
        tasks=[],
        hook_type="post_deploy",
    )

    assert result is True
