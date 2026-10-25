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

from pydantic import ConfigDict, Field, field_validator, model_validator

from .base_model import ConfigBaseModel

# Units come in h, m, s order, each at most once (``1h1h`` is rejected).
_GO_DURATION = re.compile(
    r"(?=.)(?:\d+(?:\.\d+)?h)?(?:\d+(?:\.\d+)?m)?(?:\d+(?:\.\d+)?s)?"
)
_GO_DURATION_PART = re.compile(r"(\d+(?:\.\d+)?)([hms])")
_GO_DURATION_SECONDS = {"h": 3600, "m": 60, "s": 1}
# TokenRequest rejects expirationSeconds below 10 minutes.
MIN_TOKEN_TTL_SECONDS = 600


def parse_go_duration_seconds(value: str) -> float:
    """Parse a Go-style duration (``30m``, ``1h``, ``1h30m``) into seconds.

    Each unit may appear once, in h, m, s order.

    Raises:
        ValueError: If the text is not a duration or is not greater than zero.

    """
    if not _GO_DURATION.fullmatch(value):
        msg = (
            f"invalid duration {value!r}: use Go-style units in h, m, s order "
            "such as 30m, 1h, 1h30m"
        )
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

    @field_validator("verbs", "resources", "resource_names", "non_resource_urls")
    @classmethod
    def reject_empty_entries(cls, v: list[str]) -> list[str]:
        """An empty string never matches anything; refuse it instead of ignoring."""
        if any(not item.strip() for item in v):
            msg = "entries must be non-empty strings"
            raise ValueError(msg)
        return v

    @model_validator(mode="after")
    def require_one_target(self) -> "AccessPolicyRule":
        """RBAC rules target resources or nonResourceURLs, never both or neither."""
        if bool(self.resources) == bool(self.non_resource_urls):
            msg = "exactly one of resources / nonResourceURLs is required"
            raise ValueError(msg)
        return self


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
        """Reject anything but a Go-style duration of at least 10 minutes."""
        if parse_go_duration_seconds(v) < MIN_TOKEN_TTL_SECONDS:
            msg = (
                f"token_ttl {v!r} is below the 10m minimum "
                "(TokenRequest expirationSeconds >= 600)"
            )
            raise ValueError(msg)
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
