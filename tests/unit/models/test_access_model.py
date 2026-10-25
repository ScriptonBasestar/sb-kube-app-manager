"""Tests for the ``settings.access`` schema."""

import pytest

from sbkube.exceptions import ConfigValidationError
from sbkube.models.access_model import parse_go_duration_seconds
from sbkube.models.unified_config_model import UnifiedConfig, UnifiedSettings


def test_access_is_optional() -> None:
    assert UnifiedSettings().access is None


def test_access_defaults() -> None:
    access = UnifiedSettings(access={}).access
    assert access is not None
    assert access.auto_profile is True
    assert access.namespace == "agent-access"
    assert access.token_dir == "~/.kube/agent-access"
    assert access.readonly.service_account == "agent-readonly"
    assert access.readonly.kubeconfig is None
    assert access.readonly.extra_rules == []
    assert access.deployer.service_account == "sbkube-deployer"
    assert access.deployer.kubeconfig is None
    assert access.deployer.token_ttl == "1h"


def test_extra_rules_accept_rbac_field_names() -> None:
    access = UnifiedSettings(
        access={
            "readonly": {
                "extra_rules": [
                    {
                        "apiGroups": ["cert-manager.io"],
                        "resources": ["certificates"],
                        "verbs": ["get", "list"],
                        "resourceNames": ["web"],
                        "nonResourceURLs": ["/healthz"],
                    }
                ]
            }
        }
    ).access
    assert access is not None
    rule = access.readonly.extra_rules[0]
    assert rule.api_groups == ["cert-manager.io"]
    assert rule.resource_names == ["web"]
    assert rule.non_resource_urls == ["/healthz"]


@pytest.mark.parametrize("ttl", ["30m", "1h", "1h30m", "90s", "1.5h"])
def test_token_ttl_accepts_go_durations(ttl: str) -> None:
    settings = UnifiedSettings(access={"deployer": {"token_ttl": ttl}})
    assert settings.access is not None
    assert settings.access.deployer.token_ttl == ttl


@pytest.mark.parametrize(
    "ttl", ["", "0", "0m", "0h0m", "1d", "abc", "-1h", "1h 30m", "30"]
)
def test_token_ttl_rejects_bad_values(ttl: str) -> None:
    with pytest.raises(ConfigValidationError, match="token_ttl"):
        UnifiedSettings(access={"deployer": {"token_ttl": ttl}})


def test_parse_go_duration_seconds() -> None:
    assert parse_go_duration_seconds("1h30m") == 5400
    assert parse_go_duration_seconds("90s") == 90


def test_empty_verbs_rejected() -> None:
    with pytest.raises(ConfigValidationError, match="verbs"):
        UnifiedSettings(
            access={"readonly": {"extra_rules": [{"resources": ["pods"], "verbs": []}]}}
        )


def test_missing_verbs_rejected() -> None:
    with pytest.raises(ConfigValidationError, match="verbs"):
        UnifiedSettings(access={"readonly": {"extra_rules": [{"resources": ["pods"]}]}})


@pytest.mark.parametrize(
    "access",
    [
        {"bogus": 1},
        {"readonly": {"bogus": 1}},
        {"deployer": {"bogus": 1}},
        {"readonly": {"extra_rules": [{"verbs": ["get"], "bogus": 1}]}},
    ],
)
def test_extra_field_rejected(access: dict) -> None:
    with pytest.raises(ConfigValidationError, match="bogus"):
        UnifiedSettings(access=access)


def test_access_in_unified_config_and_not_inherited_by_phases() -> None:
    config = UnifiedConfig(
        **{
            "apiVersion": "sbkube/v1",
            "settings": {"access": {"namespace": "root-ns"}},
            "phases": {
                "p1": {
                    "apps": {"a": {"type": "exec", "commands": ["true"]}},
                }
            },
        }
    )
    assert config.settings.access is not None
    assert config.settings.access.namespace == "root-ns"
    # Phase settings are independent models: access stays unset unless declared.
    assert config.phases["p1"].settings is None
