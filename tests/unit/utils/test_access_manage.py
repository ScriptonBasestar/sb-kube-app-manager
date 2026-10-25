"""Malformed API response and bounded-controller-wait regressions."""

import base64
import json
from unittest.mock import Mock, patch

import pytest

from sbkube.models.access_model import AccessSettings
from sbkube.utils.access_issue import TokenIssueError
from sbkube.utils.access_manage import (
    check_readonly_secret,
    readonly_token,
    revoke_deployer,
)


def secret() -> dict:
    return {
        "type": "kubernetes.io/service-account-token",
        "metadata": {
            "name": "agent-readonly-token",
            "namespace": "agent-access",
            "annotations": {"kubernetes.io/service-account.name": "agent-readonly"},
        },
        "data": {"token": base64.b64encode(b"PRIVATE-TOKEN").decode()},
    }


@pytest.mark.parametrize("value", ["not-json PRIVATE", '"PRIVATE"', "[]", "null"])
def test_invalid_secret_response_is_sanitized(value: str) -> None:
    session = Mock()
    session.run.return_value = value
    with pytest.raises(TokenIssueError) as raised:
        readonly_token(session, AccessSettings())
    assert "PRIVATE" not in str(raised.value)


@pytest.mark.parametrize(
    "metadata", [None, [], {"annotations": None}, {"name": "foreign"}]
)
def test_malformed_metadata_refuses_without_leaking(metadata) -> None:
    data = {**secret(), "metadata": metadata}
    session = Mock()
    session.run.return_value = json.dumps(data)
    with pytest.raises(TokenIssueError, match="expected ServiceAccount"):
        check_readonly_secret(session, AccessSettings())


@pytest.mark.parametrize(
    "fields",
    [None, [], {"token": "!!INVALID!!"}, {"token": base64.b64encode(b"a b").decode()}],
)
def test_malformed_token_data_refused(fields) -> None:
    session = Mock()
    session.run.return_value = json.dumps({**secret(), "data": fields})
    with pytest.raises(TokenIssueError):
        readonly_token(session, AccessSettings())


def test_empty_secret_wait_is_bounded() -> None:
    session = Mock()
    session.run.return_value = json.dumps({**secret(), "data": {}})
    with (
        patch("sbkube.utils.access_manage.time.monotonic", side_effect=[0, 16]),
        patch("sbkube.utils.access_manage.time.sleep") as sleep,
    ):
        with pytest.raises(TokenIssueError, match="15 seconds"):
            readonly_token(session, AccessSettings())
    assert session.run.call_count == 1
    sleep.assert_not_called()


def test_controller_population_retried_without_writing_or_printing() -> None:
    session = Mock()
    session.run.side_effect = [
        json.dumps({**secret(), "data": {}}),
        json.dumps(secret()),
    ]
    with patch("sbkube.utils.access_manage.time.sleep") as sleep:
        assert readonly_token(session, AccessSettings()) == "PRIVATE-TOKEN"
    sleep.assert_called_once_with(0.5)
    assert session.run.call_count == 2


@pytest.mark.parametrize(
    "metadata",
    [
        None,
        [],
        {"name": "other", "namespace": "agent-access"},
        {"name": "sbkube-deployer", "namespace": "foreign"},
    ],
)
def test_unexpected_deployer_identity_never_deleted(metadata) -> None:
    session = Mock()
    session.run.return_value = json.dumps(
        {"kind": "ServiceAccount", "metadata": metadata}
    )
    with pytest.raises(TokenIssueError, match="unexpected deployer"):
        revoke_deployer(session, AccessSettings())
    assert session.run.call_count == 1
