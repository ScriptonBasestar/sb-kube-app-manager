"""Pure Kubernetes RBAC manifests for ``sbkube access init``.

The default resource set is deliberately the same as the original polypia
agent-access manifests.  It lives here so every cluster receives one reviewed
source of truth instead of copying YAML files between environment repositories.
"""

from copy import deepcopy
from typing import Any, Literal

from sbkube.models.access_model import AccessPolicyRule, AccessSettings

READONLY_VERBS = frozenset({"get", "list", "watch"})

_CLUSTER_RULES: tuple[dict[str, list[str]], ...] = (
    {
        "apiGroups": [""],
        "resources": ["nodes", "namespaces", "persistentvolumes"],
        "verbs": ["get", "list", "watch"],
    },
    {
        "apiGroups": ["storage.k8s.io"],
        "resources": ["storageclasses", "csidrivers", "csinodes", "volumeattachments"],
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
        "resources": ["clusterroles", "clusterrolebindings", "roles", "rolebindings"],
        "verbs": ["get", "list", "watch"],
    },
    {
        "apiGroups": ["metrics.k8s.io"],
        "resources": ["nodes", "pods"],
        "verbs": ["get", "list"],
    },
)


class AccessTemplateError(ValueError):
    """An access configuration would widen the readonly credential."""


def readonly_secret_name(access: AccessSettings) -> str:
    """The long-lived legacy-token Secret owned by the readonly ServiceAccount."""
    return f"{access.readonly.service_account}-token"


def service_account_manifest(
    access: AccessSettings, profile: Literal["readonly", "deployer"]
) -> dict[str, Any]:
    """Build the ServiceAccount manifest for one access profile."""
    if profile == "readonly":
        name = access.readonly.service_account
    elif profile == "deployer":
        name = access.deployer.service_account
    else:  # Defensive for callers that bypass static type checking.
        raise AccessTemplateError(f"unknown access profile: {profile}")
    return {
        "apiVersion": "v1",
        "kind": "ServiceAccount",
        "metadata": {"name": name, "namespace": access.namespace},
        "automountServiceAccountToken": False,
    }


def _subject(name: str, namespace: str) -> dict[str, str]:
    return {"kind": "ServiceAccount", "name": name, "namespace": namespace}


def _binding(name: str, role_name: str, subject: dict[str, str]) -> dict[str, Any]:
    return {
        "apiVersion": "rbac.authorization.k8s.io/v1",
        "kind": "ClusterRoleBinding",
        "metadata": {"name": name},
        "roleRef": {
            "apiGroup": "rbac.authorization.k8s.io",
            "kind": "ClusterRole",
            "name": role_name,
        },
        "subjects": [subject],
    }


def _extra_rule(rule: AccessPolicyRule) -> dict[str, Any]:
    """Alias-shaped, non-empty Kubernetes PolicyRule after fail-closed checks."""
    if not set(rule.verbs) <= READONLY_VERBS:
        raise AccessTemplateError(
            "access.readonly.extra_rules permits only get, list and watch"
        )
    for resource in rule.resources:
        if "*" in resource or resource.split("/", 1)[0] == "secrets":
            raise AccessTemplateError(
                "access.readonly.extra_rules must not grant secrets or wildcard resources"
            )
    rendered = rule.model_dump(by_alias=True, exclude_none=True)
    return {key: value for key, value in rendered.items() if value}


def access_manifests(access: AccessSettings) -> list[dict[str, Any]]:
    """Return a deterministic, apply-safe manifest sequence for access initialization."""
    readonly = access.readonly.service_account
    deployer = access.deployer.service_account
    if readonly == deployer:
        raise AccessTemplateError(
            "readonly and deployer ServiceAccounts must be distinct"
        )
    if deployer in {f"{readonly}-view", f"{readonly}-cluster"}:
        raise AccessTemplateError(
            "deployer ServiceAccount must not collide with readonly ClusterRoleBinding names"
        )
    readonly_subject = _subject(readonly, access.namespace)
    rules = list(deepcopy(_CLUSTER_RULES))
    rules.extend(_extra_rule(rule) for rule in access.readonly.extra_rules)
    role_name = f"{readonly}-cluster"
    return [
        {
            "apiVersion": "v1",
            "kind": "Namespace",
            "metadata": {
                "name": access.namespace,
                "labels": {"app.kubernetes.io/part-of": "agent-access"},
            },
        },
        service_account_manifest(access, "readonly"),
        {
            "apiVersion": "v1",
            "kind": "Secret",
            "metadata": {
                "name": readonly_secret_name(access),
                "namespace": access.namespace,
                "annotations": {"kubernetes.io/service-account.name": readonly},
            },
            "type": "kubernetes.io/service-account-token",
        },
        _binding(f"{readonly}-view", "view", readonly_subject),
        {
            "apiVersion": "rbac.authorization.k8s.io/v1",
            "kind": "ClusterRole",
            "metadata": {"name": role_name},
            "rules": list(rules),
        },
        _binding(role_name, role_name, readonly_subject),
        service_account_manifest(access, "deployer"),
        _binding(deployer, "cluster-admin", _subject(deployer, access.namespace)),
    ]
