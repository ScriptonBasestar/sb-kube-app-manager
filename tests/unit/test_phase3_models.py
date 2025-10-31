"""
Phase 3 Models 검증 테스트.

ValidationRule, DependencyConfig, RollbackPolicy 모델 및
HookTask에 통합된 Phase 3 필드 테스트.
"""

import pytest

from sbkube.exceptions import ConfigValidationError
from sbkube.models.config_model import (
    AppHooks,
    CommandHookTask,
    DependencyConfig,
    InlineHookTask,
    ManifestsHookTask,
    RollbackPolicy,
    ValidationRule,
)

# ============================================================================
# ValidationRule 테스트
# ============================================================================


def test_validation_rule_basic():
    """ValidationRule 기본 생성 테스트."""
    validation = ValidationRule(
        kind="ClusterIssuer",
        name="letsencrypt-prd",
        wait_for_ready=True,
        timeout=120,
    )
    assert validation.kind == "ClusterIssuer"
    assert validation.name == "letsencrypt-prd"
    assert validation.wait_for_ready is True
    assert validation.timeout == 120


def test_validation_rule_with_conditions():
    """ValidationRule conditions 테스트."""
    validation = ValidationRule(
        kind="Pod",
        wait_for_ready=True,
        conditions=[
            {"type": "Ready", "status": "True"},
            {"type": "ContainersReady", "status": "True"},
        ],
    )
    assert validation.kind == "Pod"
    assert len(validation.conditions) == 2
    assert validation.conditions[0]["type"] == "Ready"


def test_validation_rule_defaults():
    """ValidationRule 기본값 테스트."""
    validation = ValidationRule()
    assert validation.kind is None
    assert validation.name is None
    assert validation.namespace is None
    assert validation.wait_for_ready is False
    assert validation.timeout == 60
    assert validation.conditions is None


# ============================================================================
# DependencyConfig 테스트
# ============================================================================


def test_dependency_config_depends_on():
    """DependencyConfig depends_on 테스트."""
    dependency = DependencyConfig(depends_on=["deploy-secrets", "verify-database"])
    assert len(dependency.depends_on) == 2
    assert "deploy-secrets" in dependency.depends_on


def test_dependency_config_wait_for():
    """DependencyConfig wait_for 테스트."""
    dependency = DependencyConfig(
        wait_for=[
            {
                "kind": "Pod",
                "label_selector": "app=database",
                "condition": "Ready",
                "timeout": 180,
            }
        ]
    )
    assert len(dependency.wait_for) == 1
    assert dependency.wait_for[0]["kind"] == "Pod"
    assert dependency.wait_for[0]["timeout"] == 180


def test_dependency_config_combined():
    """DependencyConfig depends_on + wait_for 테스트."""
    dependency = DependencyConfig(
        depends_on=["task-a", "task-b"],
        wait_for=[{"kind": "Deployment", "name": "nginx", "condition": "Available"}],
    )
    assert len(dependency.depends_on) == 2
    assert len(dependency.wait_for) == 1


def test_dependency_config_defaults():
    """DependencyConfig 기본값 테스트."""
    dependency = DependencyConfig()
    assert dependency.depends_on == []
    assert dependency.wait_for is None


# ============================================================================
# RollbackPolicy 테스트
# ============================================================================


def test_rollback_policy_enabled():
    """RollbackPolicy enabled=True 테스트."""
    rollback = RollbackPolicy(
        enabled=True,
        on_failure="always",
        manifests=["manifests/cleanup.yaml"],
        commands=["kubectl delete certificate wildcard-cert"],
    )
    assert rollback.enabled is True
    assert rollback.on_failure == "always"
    assert len(rollback.manifests) == 1
    assert len(rollback.commands) == 1


def test_rollback_policy_manual():
    """RollbackPolicy on_failure=manual 테스트."""
    rollback = RollbackPolicy(
        enabled=True,
        on_failure="manual",
        commands=["./scripts/restore.sh"],
    )
    assert rollback.on_failure == "manual"


def test_rollback_policy_invalid_on_failure():
    """RollbackPolicy 잘못된 on_failure 값 테스트."""
    with pytest.raises(ConfigValidationError) as exc_info:
        RollbackPolicy(
            enabled=True,
            on_failure="invalid_value",  # always, manual, never만 허용
        )
    assert "on_failure" in str(exc_info.value).lower()


def test_rollback_policy_defaults():
    """RollbackPolicy 기본값 테스트."""
    rollback = RollbackPolicy()
    assert rollback.enabled is False
    assert rollback.on_failure == "always"
    assert rollback.manifests == []
    assert rollback.commands == []


# ============================================================================
# HookTask 통합 테스트 (Phase 3 필드)
# ============================================================================


def test_manifests_task_with_phase3_fields():
    """ManifestsHookTask에 Phase 3 필드 통합 테스트."""
    data = {
        "type": "manifests",
        "name": "deploy-issuers",
        "files": ["manifests/issuer.yaml"],
        "validation": {
            "kind": "ClusterIssuer",
            "wait_for_ready": True,
            "timeout": 120,
        },
        "dependency": {
            "depends_on": ["deploy-secrets"],
        },
        "rollback": {
            "enabled": True,
            "manifests": ["manifests/cleanup-issuers.yaml"],
        },
    }
    task = ManifestsHookTask(**data)
    assert task.name == "deploy-issuers"
    assert task.validation["kind"] == "ClusterIssuer"
    assert task.dependency["depends_on"] == ["deploy-secrets"]
    assert task.rollback["enabled"] is True


def test_inline_task_with_phase3_fields():
    """InlineHookTask에 Phase 3 필드 통합 테스트."""
    data = {
        "type": "inline",
        "name": "create-cert",
        "content": {
            "apiVersion": "cert-manager.io/v1",
            "kind": "Certificate",
            "metadata": {"name": "wildcard-cert"},
        },
        "validation": {
            "kind": "Certificate",
            "name": "wildcard-cert",
            "wait_for_ready": True,
        },
        "dependency": {
            "depends_on": ["deploy-issuers"],
        },
    }
    task = InlineHookTask(**data)
    assert task.name == "create-cert"
    assert task.validation["kind"] == "Certificate"
    assert task.dependency["depends_on"] == ["deploy-issuers"]


def test_command_task_with_phase3_fields():
    """CommandHookTask에 Phase 3 필드 통합 테스트."""
    data = {
        "type": "command",
        "name": "verify-dns",
        "command": "dig +short example.com",
        "retry": {"max_attempts": 3, "delay": 5},
        "on_failure": "warn",
        "dependency": {
            "depends_on": ["deploy-issuers"],
            "wait_for": [
                {"kind": "Pod", "label_selector": "app=coredns", "condition": "Ready"}
            ],
        },
    }
    task = CommandHookTask(**data)
    assert task.name == "verify-dns"
    assert task.on_failure == "warn"
    assert task.dependency["depends_on"] == ["deploy-issuers"]
    assert len(task.dependency["wait_for"]) == 1


# ============================================================================
# AppHooks 통합 시나리오
# ============================================================================


def test_app_hooks_with_phase3_tasks():
    """AppHooks에 Phase 3 tasks 통합 시나리오."""
    data = {
        "post_deploy_tasks": [
            {
                "type": "manifests",
                "name": "deploy-issuers",
                "files": ["manifests/issuer.yaml"],
                "validation": {"kind": "ClusterIssuer", "wait_for_ready": True},
                "rollback": {"enabled": True, "manifests": ["manifests/cleanup.yaml"]},
            },
            {
                "type": "inline",
                "name": "create-cert",
                "content": {"apiVersion": "v1", "kind": "Certificate"},
                "dependency": {"depends_on": ["deploy-issuers"]},
            },
            {
                "type": "command",
                "name": "verify-cert",
                "command": "kubectl get certificate wildcard-cert",
                "dependency": {"depends_on": ["create-cert"]},
                "on_failure": "warn",
            },
        ]
    }
    hooks = AppHooks(**data)
    assert len(hooks.post_deploy_tasks) == 3

    # 첫 번째 task: manifests with validation + rollback
    task1 = hooks.post_deploy_tasks[0]
    assert isinstance(task1, ManifestsHookTask)
    assert task1.validation is not None
    assert task1.rollback is not None

    # 두 번째 task: inline with dependency
    task2 = hooks.post_deploy_tasks[1]
    assert isinstance(task2, InlineHookTask)
    assert task2.dependency is not None
    assert task2.dependency["depends_on"] == ["deploy-issuers"]

    # 세 번째 task: command with dependency
    task3 = hooks.post_deploy_tasks[2]
    assert isinstance(task3, CommandHookTask)
    assert task3.dependency is not None
    assert task3.on_failure == "warn"


def test_backward_compatibility_phase2_tasks():
    """Phase 2 tasks (Phase 3 필드 없이) 호환성 테스트."""
    data = {
        "post_deploy_tasks": [
            {
                "type": "manifests",
                "name": "simple-deploy",
                "files": ["manifests/app.yaml"],
                # validation, dependency, rollback 없음
            },
            {
                "type": "command",
                "name": "simple-command",
                "command": "echo hello",
                # Phase 3 필드 없음
            },
        ]
    }
    hooks = AppHooks(**data)
    assert len(hooks.post_deploy_tasks) == 2

    # Phase 3 필드들이 모두 None이어야 함
    task1 = hooks.post_deploy_tasks[0]
    assert task1.validation is None
    assert task1.dependency is None
    assert task1.rollback is None

    task2 = hooks.post_deploy_tasks[1]
    assert task2.validation is None
    assert task2.dependency is None
    assert task2.rollback is None


# ============================================================================
# 실전 시나리오 테스트
# ============================================================================


def test_cert_manager_full_scenario_with_phase3():
    """cert-manager + ClusterIssuers + Certificate with Phase 3 features."""
    data = {
        "post_deploy_tasks": [
            # Step 1: ClusterIssuer 배포 (manifests)
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
                    "timeout": 120,
                    "conditions": [{"type": "Ready", "status": "True"}],
                },
                "rollback": {
                    "enabled": True,
                    "on_failure": "always",
                    "manifests": ["manifests/issuers/cleanup.yaml"],
                },
            },
            # Step 2: Certificate 생성 (inline)
            {
                "type": "inline",
                "name": "create-wildcard-certificate",
                "content": {
                    "apiVersion": "cert-manager.io/v1",
                    "kind": "Certificate",
                    "metadata": {"name": "wildcard-cert", "namespace": "default"},
                    "spec": {
                        "secretName": "wildcard-cert-tls",
                        "issuerRef": {
                            "name": "letsencrypt-prd",
                            "kind": "ClusterIssuer",
                        },
                        "dnsNames": ["*.example.com"],
                    },
                },
                "dependency": {
                    "depends_on": ["deploy-cluster-issuers"],
                },
                "validation": {
                    "kind": "Certificate",
                    "name": "wildcard-cert",
                    "namespace": "default",
                    "wait_for_ready": True,
                    "timeout": 300,
                },
            },
            # Step 3: DNS 검증 (command)
            {
                "type": "command",
                "name": "verify-dns-records",
                "command": "dig +short _acme-challenge.example.com TXT @8.8.8.8",
                "retry": {"max_attempts": 5, "delay": 10},
                "on_failure": "warn",
                "dependency": {
                    "depends_on": ["create-wildcard-certificate"],
                    "wait_for": [
                        {
                            "kind": "CertificateRequest",
                            "namespace": "default",
                            "label_selector": "acme.cert-manager.io/order-name",
                            "condition": "Ready",
                            "timeout": 300,
                        }
                    ],
                },
            },
        ]
    }

    hooks = AppHooks(**data)
    assert len(hooks.post_deploy_tasks) == 3

    # Step 1: ClusterIssuer with validation + rollback
    issuer_task = hooks.post_deploy_tasks[0]
    assert isinstance(issuer_task, ManifestsHookTask)
    assert issuer_task.validation["kind"] == "ClusterIssuer"
    assert issuer_task.rollback["enabled"] is True

    # Step 2: Certificate with dependency + validation
    cert_task = hooks.post_deploy_tasks[1]
    assert isinstance(cert_task, InlineHookTask)
    assert cert_task.dependency["depends_on"] == ["deploy-cluster-issuers"]
    assert cert_task.validation["kind"] == "Certificate"

    # Step 3: DNS verification with dependency + wait_for
    verify_task = hooks.post_deploy_tasks[2]
    assert isinstance(verify_task, CommandHookTask)
    assert verify_task.dependency["depends_on"] == ["create-wildcard-certificate"]
    assert len(verify_task.dependency["wait_for"]) == 1
    assert verify_task.on_failure == "warn"
