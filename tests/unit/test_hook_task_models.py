"""
Hook Task 모델 단위 테스트 (Phase 2).

HookTask 모델들의 Pydantic validation 검증:
- ManifestsHookTask
- InlineHookTask
- CommandHookTask
- Discriminated Union 동작
"""

import pytest

from sbkube.exceptions import ConfigValidationError
from sbkube.models.config_model import (
    AppHooks,
    CommandHookTask,
    InlineHookTask,
    ManifestsHookTask,
)

# ============================================================================
# ManifestsHookTask 테스트
# ============================================================================


def test_manifests_hook_task_valid():
    """ManifestsHookTask 유효한 데이터 테스트."""
    data = {
        "type": "manifests",
        "name": "deploy-issuers",
        "files": [
            "manifests/issuer1.yaml",
            "manifests/issuer2.yaml",
        ],
    }

    task = ManifestsHookTask(**data)

    assert task.type == "manifests"
    assert task.name == "deploy-issuers"
    assert len(task.files) == 2
    assert task.validation is None


def test_manifests_hook_task_with_validation():
    """ManifestsHookTask validation 포함 테스트."""
    data = {
        "type": "manifests",
        "name": "deploy-issuers",
        "files": ["manifests/issuer.yaml"],
        "validation": {
            "kind": "ClusterIssuer",
            "wait_for_ready": True,
        },
    }

    task = ManifestsHookTask(**data)

    assert task.validation is not None
    assert task.validation["kind"] == "ClusterIssuer"
    assert task.validation["wait_for_ready"] is True


def test_manifests_hook_task_missing_required():
    """ManifestsHookTask 필수 필드 누락 테스트."""
    data = {
        "type": "manifests",
        "name": "deploy-issuers",
        # files 누락
    }

    with pytest.raises(ConfigValidationError) as exc_info:
        ManifestsHookTask(**data)

    assert "files" in str(exc_info.value)


# ============================================================================
# InlineHookTask 테스트
# ============================================================================


def test_inline_hook_task_valid():
    """InlineHookTask 유효한 데이터 테스트."""
    data = {
        "type": "inline",
        "name": "create-certificate",
        "content": {
            "apiVersion": "cert-manager.io/v1",
            "kind": "Certificate",
            "metadata": {
                "name": "wildcard-cert",
            },
            "spec": {
                "secretName": "wildcard-cert-tls",
                "issuerRef": {
                    "name": "letsencrypt-prd",
                    "kind": "ClusterIssuer",
                },
            },
        },
    }

    task = InlineHookTask(**data)

    assert task.type == "inline"
    assert task.name == "create-certificate"
    assert task.content["apiVersion"] == "cert-manager.io/v1"
    assert task.content["kind"] == "Certificate"


def test_inline_hook_task_missing_content():
    """InlineHookTask content 누락 테스트."""
    data = {
        "type": "inline",
        "name": "create-cert",
        # content 누락
    }

    with pytest.raises(ConfigValidationError) as exc_info:
        InlineHookTask(**data)

    assert "content" in str(exc_info.value)


# ============================================================================
# CommandHookTask 테스트
# ============================================================================


def test_command_hook_task_valid():
    """CommandHookTask 유효한 데이터 테스트."""
    data = {
        "type": "command",
        "name": "verify-dns",
        "command": "dig +short example.com @8.8.8.8",
    }

    task = CommandHookTask(**data)

    assert task.type == "command"
    assert task.name == "verify-dns"
    assert task.command == "dig +short example.com @8.8.8.8"
    assert task.retry is None
    assert task.on_failure == "fail"  # default


def test_command_hook_task_with_retry():
    """CommandHookTask retry 포함 테스트."""
    data = {
        "type": "command",
        "name": "verify-dns",
        "command": "dig +short example.com",
        "retry": {
            "max_attempts": 3,
            "delay": 5,
        },
        "on_failure": "warn",
    }

    task = CommandHookTask(**data)

    assert task.retry is not None
    assert task.retry["max_attempts"] == 3
    assert task.retry["delay"] == 5
    assert task.on_failure == "warn"


def test_command_hook_task_invalid_on_failure():
    """CommandHookTask 잘못된 on_failure 값 테스트."""
    data = {
        "type": "command",
        "name": "test",
        "command": "echo test",
        "on_failure": "invalid",  # 잘못된 값
    }

    with pytest.raises(ConfigValidationError) as exc_info:
        CommandHookTask(**data)

    assert "on_failure" in str(exc_info.value).lower()


# ============================================================================
# Discriminated Union 테스트
# ============================================================================


def test_app_hooks_with_tasks():
    """AppHooks에 tasks 포함 테스트."""
    data = {
        "post_deploy_tasks": [
            {
                "type": "manifests",
                "name": "deploy-issuers",
                "files": ["manifests/issuer.yaml"],
            },
            {
                "type": "inline",
                "name": "create-cert",
                "content": {
                    "apiVersion": "v1",
                    "kind": "Certificate",
                },
            },
            {
                "type": "command",
                "name": "verify",
                "command": "echo done",
            },
        ],
    }

    hooks = AppHooks(**data)

    assert len(hooks.post_deploy_tasks) == 3

    # 첫 번째 task: manifests
    assert hooks.post_deploy_tasks[0].type == "manifests"
    assert hooks.post_deploy_tasks[0].name == "deploy-issuers"

    # 두 번째 task: inline
    assert hooks.post_deploy_tasks[1].type == "inline"
    assert hooks.post_deploy_tasks[1].name == "create-cert"

    # 세 번째 task: command
    assert hooks.post_deploy_tasks[2].type == "command"
    assert hooks.post_deploy_tasks[2].name == "verify"


def test_app_hooks_discriminator():
    """AppHooks Discriminated Union 타입 구분 테스트."""
    data = {
        "post_deploy_tasks": [
            {
                "type": "manifests",
                "name": "test",
                "files": ["test.yaml"],
            },
        ],
    }

    hooks = AppHooks(**data)

    # Pydantic이 자동으로 ManifestsHookTask로 변환
    assert isinstance(hooks.post_deploy_tasks[0], ManifestsHookTask)


def test_app_hooks_invalid_type():
    """AppHooks 잘못된 task type 테스트."""
    data = {
        "post_deploy_tasks": [
            {
                "type": "invalid_type",  # 지원하지 않는 타입
                "name": "test",
            },
        ],
    }

    with pytest.raises(ConfigValidationError) as exc_info:
        AppHooks(**data)

    assert "type" in str(exc_info.value).lower()


def test_app_hooks_backward_compatibility():
    """AppHooks Phase 1/Phase 2 병행 사용 테스트."""
    data = {
        # Phase 1 (Shell 명령어)
        "post_deploy": ["echo 'old way'"],
        # Phase 1 (Manifests)
        "post_deploy_manifests": ["manifests/issuer.yaml"],
        # Phase 2 (Tasks)
        "post_deploy_tasks": [
            {
                "type": "command",
                "name": "new-way",
                "command": "echo 'new way'",
            },
        ],
    }

    hooks = AppHooks(**data)

    assert len(hooks.post_deploy) == 1
    assert len(hooks.post_deploy_manifests) == 1
    assert len(hooks.post_deploy_tasks) == 1


# ============================================================================
# 실전 시나리오 테스트
# ============================================================================


def test_cert_manager_scenario():
    """cert-manager + ClusterIssuers 실전 시나리오."""
    data = {
        "post_deploy_tasks": [
            # Task 1: Manifests로 ClusterIssuers 배포
            {
                "type": "manifests",
                "name": "deploy-cluster-issuers",
                "files": [
                    "manifests/issuers/cluster-issuer-letsencrypt-prd.yaml",
                    "manifests/issuers/cluster-issuer-letsencrypt-stg.yaml",
                ],
                "validation": {
                    "kind": "ClusterIssuer",
                    "wait_for_ready": True,
                },
            },
            # Task 2: Inline으로 Certificate 생성
            {
                "type": "inline",
                "name": "create-wildcard-certificate",
                "content": {
                    "apiVersion": "cert-manager.io/v1",
                    "kind": "Certificate",
                    "metadata": {
                        "name": "wildcard-cert",
                        "namespace": "default",
                    },
                    "spec": {
                        "secretName": "wildcard-cert-tls",
                        "issuerRef": {
                            "name": "letsencrypt-prd",
                            "kind": "ClusterIssuer",
                        },
                        "dnsNames": ["*.example.com"],
                    },
                },
            },
            # Task 3: DNS 검증
            {
                "type": "command",
                "name": "verify-dns-records",
                "command": "dig +short _acme-challenge.example.com @8.8.8.8",
                "retry": {
                    "max_attempts": 3,
                    "delay": 5,
                },
                "on_failure": "warn",
            },
        ],
    }

    hooks = AppHooks(**data)

    assert len(hooks.post_deploy_tasks) == 3

    # Task 1 검증
    task1 = hooks.post_deploy_tasks[0]
    assert isinstance(task1, ManifestsHookTask)
    assert len(task1.files) == 2
    assert task1.validation is not None

    # Task 2 검증
    task2 = hooks.post_deploy_tasks[1]
    assert isinstance(task2, InlineHookTask)
    assert task2.content["kind"] == "Certificate"

    # Task 3 검증
    task3 = hooks.post_deploy_tasks[2]
    assert isinstance(task3, CommandHookTask)
    assert task3.retry is not None
    assert task3.on_failure == "warn"
