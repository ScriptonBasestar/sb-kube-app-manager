"""Pure template tests for the access RBAC initializer."""

import pytest

from sbkube.models.access_model import AccessSettings
from sbkube.utils.access_templates import (
    AccessTemplateError,
    access_manifests,
    readonly_secret_name,
    service_account_manifest,
)


def manifests(values: dict | None = None) -> list[dict]:
    return access_manifests(AccessSettings(**(values or {})))


def test_default_manifests_match_polypia_resource_contract() -> None:
    resources = manifests()
    assert [
        (item["apiVersion"], item["kind"], item["metadata"]["name"])
        for item in resources
    ] == [
        ("v1", "Namespace", "agent-access"),
        ("v1", "ServiceAccount", "agent-readonly"),
        ("v1", "Secret", "agent-readonly-token"),
        ("rbac.authorization.k8s.io/v1", "ClusterRoleBinding", "agent-readonly-view"),
        ("rbac.authorization.k8s.io/v1", "ClusterRole", "agent-readonly-cluster"),
        (
            "rbac.authorization.k8s.io/v1",
            "ClusterRoleBinding",
            "agent-readonly-cluster",
        ),
        ("v1", "ServiceAccount", "sbkube-deployer"),
        ("rbac.authorization.k8s.io/v1", "ClusterRoleBinding", "sbkube-deployer"),
    ]
    assert resources[0] == {
        "apiVersion": "v1",
        "kind": "Namespace",
        "metadata": {
            "name": "agent-access",
            "labels": {"app.kubernetes.io/part-of": "agent-access"},
        },
    }
    assert resources[1]["automountServiceAccountToken"] is False
    assert resources[2] == {
        "apiVersion": "v1",
        "kind": "Secret",
        "metadata": {
            "name": "agent-readonly-token",
            "namespace": "agent-access",
            "annotations": {"kubernetes.io/service-account.name": "agent-readonly"},
        },
        "type": "kubernetes.io/service-account-token",
    }
    assert resources[3]["roleRef"]["name"] == "view"
    assert resources[4]["rules"] == [
        {
            "apiGroups": [""],
            "resources": ["nodes", "namespaces", "persistentvolumes"],
            "verbs": ["get", "list", "watch"],
        },
        {
            "apiGroups": ["storage.k8s.io"],
            "resources": [
                "storageclasses",
                "csidrivers",
                "csinodes",
                "volumeattachments",
            ],
            "verbs": ["get", "list", "watch"],
        },
        {
            "apiGroups": ["apiextensions.k8s.io"],
            "resources": ["customresourcedefinitions"],
            "verbs": ["get", "list", "watch"],
        },
        {
            "apiGroups": ["apiregistration.k8s.io"],
            "resources": ["apiservices"],
            "verbs": ["get", "list", "watch"],
        },
        {
            "apiGroups": ["scheduling.k8s.io"],
            "resources": ["priorityclasses"],
            "verbs": ["get", "list", "watch"],
        },
        {
            "apiGroups": ["networking.k8s.io"],
            "resources": ["ingressclasses"],
            "verbs": ["get", "list", "watch"],
        },
        {
            "apiGroups": ["admissionregistration.k8s.io"],
            "resources": [
                "mutatingwebhookconfigurations",
                "validatingwebhookconfigurations",
            ],
            "verbs": ["get", "list", "watch"],
        },
        {
            "apiGroups": ["rbac.authorization.k8s.io"],
            "resources": [
                "clusterroles",
                "clusterrolebindings",
                "roles",
                "rolebindings",
            ],
            "verbs": ["get", "list", "watch"],
        },
        {
            "apiGroups": ["metrics.k8s.io"],
            "resources": ["nodes", "pods"],
            "verbs": ["get", "list"],
        },
    ]
    assert resources[-1]["roleRef"]["name"] == "cluster-admin"


def test_nondefault_names_flow_through_every_resource() -> None:
    access = AccessSettings(
        namespace="access-team",
        readonly={"service_account": "reader"},
        deployer={"service_account": "writer"},
    )
    resources = access_manifests(access)
    assert readonly_secret_name(access) == "reader-token"
    assert resources[0]["metadata"]["name"] == "access-team"
    assert resources[2]["metadata"]["name"] == "reader-token"
    assert resources[3]["metadata"]["name"] == "reader-view"
    assert resources[4]["metadata"]["name"] == "reader-cluster"
    assert resources[5]["subjects"][0] == {
        "kind": "ServiceAccount",
        "name": "reader",
        "namespace": "access-team",
    }
    assert resources[-1]["metadata"]["name"] == "writer"
    assert resources[-1]["subjects"][0]["name"] == "writer"


def test_service_account_manifest_validates_profile() -> None:
    access = AccessSettings()
    assert (
        service_account_manifest(access, "readonly")["metadata"]["name"]
        == "agent-readonly"
    )
    assert (
        service_account_manifest(access, "deployer")["metadata"]["name"]
        == "sbkube-deployer"
    )
    with pytest.raises(AccessTemplateError, match="unknown"):
        service_account_manifest(access, "admin")  # type: ignore[arg-type]


def test_extra_rule_is_alias_shaped_and_omits_empty_fields() -> None:
    resources = manifests(
        {
            "readonly": {
                "extra_rules": [
                    {
                        "apiGroups": ["cert-manager.io"],
                        "resources": ["certificates"],
                        "verbs": ["get", "list"],
                        "resourceNames": ["web"],
                    }
                ]
            }
        }
    )
    assert resources[4]["rules"][-1] == {
        "apiGroups": ["cert-manager.io"],
        "resources": ["certificates"],
        "verbs": ["get", "list"],
        "resourceNames": ["web"],
    }


def test_returned_default_rules_do_not_change_the_next_render() -> None:
    first = manifests()
    first[4]["rules"][0]["resources"].append("secrets")
    assert manifests()[4]["rules"][0]["resources"] == [
        "nodes",
        "namespaces",
        "persistentvolumes",
    ]


def test_same_service_account_is_refused_for_unvalidated_caller() -> None:
    valid = AccessSettings(
        readonly={"service_account": "reader"}, deployer={"service_account": "writer"}
    )
    access = valid.model_copy(update={"deployer": valid.readonly})
    with pytest.raises(AccessTemplateError, match="distinct"):
        access_manifests(access)


@pytest.mark.parametrize("deployer", ["reader-view", "reader-cluster"])
def test_deployer_binding_name_collision_is_refused_for_unvalidated_caller(
    deployer: str,
) -> None:
    valid = AccessSettings(
        readonly={"service_account": "reader"}, deployer={"service_account": "writer"}
    )
    access = valid.model_copy(
        update={
            "deployer": valid.deployer.model_copy(update={"service_account": deployer})
        }
    )
    with pytest.raises(AccessTemplateError, match="ClusterRoleBinding"):
        access_manifests(access)


@pytest.mark.parametrize(
    "rule",
    [
        {"resources": ["pods"], "verbs": ["create"]},
        {"resources": ["*"], "verbs": ["get"]},
        {"resources": ["*/*"], "verbs": ["get"]},
        {"resources": ["*/status"], "verbs": ["get"]},
        {"resources": ["pods/*"], "verbs": ["get"]},
        {"resources": ["secrets"], "verbs": ["get"]},
        {"resources": ["secrets/status"], "verbs": ["watch"]},
    ],
)
def test_extra_rule_refuses_privileged_or_secret_access(rule: dict) -> None:
    with pytest.raises(AccessTemplateError):
        manifests({"readonly": {"extra_rules": [rule]}})
