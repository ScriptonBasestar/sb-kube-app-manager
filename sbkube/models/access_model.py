"""Access settings model (``settings.access``) for ``sbkube access``.

Agents run sbkube with the same OS uid as the human, so the only boundary they
cannot bypass is Kubernetes RBAC: agents get a readonly ServiceAccount
kubeconfig, and deploys use a short-lived token a human issues.

Only the global (root) ``settings`` carries ``access``. It is not part of the
settings that flow to phases or apps (see ``utils/settings_inheritance.py``), so
a phase/app-level ``access`` block validates but is never read.
"""

import re
from typing import Annotated

from pydantic import ConfigDict, Field, field_validator

from .base_model import ConfigBaseModel

_GO_DURATION = re.compile(r"(?:\d+(?:\.\d+)?[hms])+")
_GO_DURATION_PART = re.compile(r"(\d+(?:\.\d+)?)([hms])")
_GO_DURATION_SECONDS = {"h": 3600, "m": 60, "s": 1}


def parse_go_duration_seconds(value: str) -> float:
    """Parse a Go-style duration (``30m``, ``1h``, ``1h30m``) into seconds.

    Raises:
        ValueError: If the text is not a duration or is not greater than zero.

    """
    if not _GO_DURATION.fullmatch(value):
        msg = f"invalid duration {value!r}: use Go-style units such as 30m, 1h, 1h30m"
        raise ValueError(msg)
    total = sum(
        float(amount) * _GO_DURATION_SECONDS[unit]
        for amount, unit in _GO_DURATION_PART.findall(value)
    )
    if total <= 0:
        msg = f"invalid duration {value!r}: must be greater than zero"
        raise ValueError(msg)
    return total


class AccessPolicyRule(ConfigBaseModel):
    """Extra read rule for the readonly ServiceAccount (RBAC PolicyRule shape)."""

    model_config = ConfigDict(populate_by_name=True)

    api_groups: Annotated[
        list[str],
        Field(
            alias="apiGroups",
            description='API groups of the rule ("" is the core group)',
        ),
    ] = []

    resources: Annotated[
        list[str],
        Field(
            description="Resources the rule applies to",
        ),
    ] = []

    verbs: Annotated[
        list[str],
        Field(
            min_length=1,
            description="Allowed verbs (at least one)",
        ),
    ]

    resource_names: Annotated[
        list[str],
        Field(
            alias="resourceNames",
            description="Restrict the rule to these resource names",
        ),
    ] = []

    non_resource_urls: Annotated[
        list[str],
        Field(
            alias="nonResourceURLs",
            description="Non-resource URL paths the rule applies to",
        ),
    ] = []


class AccessReadonlySettings(ConfigBaseModel):
    """Readonly (agent) credential: ServiceAccount and generated kubeconfig."""

    service_account: Annotated[
        str,
        Field(
            description="ServiceAccount used by agents",
        ),
    ] = "agent-readonly"

    kubeconfig: Annotated[
        str | None,
        Field(
            description="Path of the agent kubeconfig",
        ),
    ] = None

    extra_rules: Annotated[
        list[AccessPolicyRule],
        Field(
            description="Cluster-specific extra read rules",
        ),
    ] = []


class AccessDeployerSettings(ConfigBaseModel):
    """Deployer credential: ServiceAccount and short-lived token."""

    service_account: Annotated[
        str,
        Field(
            description="ServiceAccount that deploys",
        ),
    ] = "sbkube-deployer"

    kubeconfig: Annotated[
        str | None,
        Field(
            description="Path of the deployer kubeconfig",
        ),
    ] = None

    token_ttl: Annotated[
        str,
        Field(
            description="Lifetime of an issued token (Go-style duration, e.g. 30m, 1h, 1h30m)",
        ),
    ] = "1h"

    @field_validator("token_ttl")
    @classmethod
    def validate_token_ttl(cls, v: str) -> str:
        """Reject anything but a positive Go-style duration."""
        parse_go_duration_seconds(v)
        return v


class AccessSettings(ConfigBaseModel):
    """Agent access boundary (``settings.access``).

    Examples:
        settings:
          kubeconfig: ~/.kube/admin          # admin credential
          kubeconfig_context: prod
          access:
            namespace: agent-access
            readonly:
              kubeconfig: ~/.kube/prod-agent
            deployer:
              token_ttl: 1h

    """

    auto_profile: Annotated[
        bool,
        Field(
            description="Pick readonly/deployer kubeconfig per command (reserved; not used yet)",
        ),
    ] = True

    namespace: Annotated[
        str,
        Field(
            description="Namespace holding the access ServiceAccounts",
        ),
    ] = "agent-access"

    token_dir: Annotated[
        str,
        Field(
            description="Directory for token files (mode 600)",
        ),
    ] = "~/.kube/agent-access"

    readonly: Annotated[
        AccessReadonlySettings,
        Field(
            default_factory=AccessReadonlySettings,
            description="Readonly agent credential",
        ),
    ]

    deployer: Annotated[
        AccessDeployerSettings,
        Field(
            default_factory=AccessDeployerSettings,
            description="Deployer credential",
        ),
    ]
