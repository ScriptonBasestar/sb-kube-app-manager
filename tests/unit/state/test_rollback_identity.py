"""Immutable cluster identity pinning regressions for rollback resolution."""

import base64
from datetime import datetime
from pathlib import Path

import pytest

from sbkube.exceptions import RollbackError
from sbkube.models.deployment_state import DeploymentDetail, DeploymentStatus
from sbkube.state.rollback_cluster import resolve_rollback_cluster
from sbkube.utils.cluster_identity import cluster_identity


def _kubeconfig(
    path: Path,
    *,
    context: str = "home",
    server: str = "https://home:6443",
    ca: bytes = b"public-ca",
) -> Path:
    path.write_text(
        "contexts:\n"
        f"- name: {context}\n  context: {{cluster: home}}\n"
        "clusters:\n"
        f"- name: home\n  cluster: {{server: {server}, certificate-authority-data: {base64.b64encode(ca).decode()}}}\n"
    )
    return path


def _deployment(snapshot: dict) -> DeploymentDetail:
    return DeploymentDetail(
        deployment_id="deploy-1",
        timestamp=datetime(2026, 10, 26),
        cluster="home",
        namespace="default",
        app_config_dir="/apps",
        status=DeploymentStatus.SUCCESS,
        config_snapshot={},
        sources_snapshot=snapshot,
    )


def _pinned_snapshot(recorded: Path, *, context: str = "home") -> dict:
    return {
        "kubeconfig": str(recorded),
        "kubeconfig_context": context,
        "cluster_identity": cluster_identity(recorded, context),
    }


def test_pinned_override_works_after_recorded_kubeconfig_is_deleted(
    tmp_path: Path,
) -> None:
    recorded = _kubeconfig(tmp_path / "recorded")
    snapshot = _pinned_snapshot(recorded)
    override = _kubeconfig(tmp_path / "override")
    recorded.unlink()

    assert resolve_rollback_cluster(_deployment(snapshot), str(override), "home") == (
        str(override),
        "home",
    )


@pytest.mark.parametrize(
    ("context", "server", "ca"),
    [
        ("other", "https://home:6443", b"public-ca"),
        ("home", "https://other:6443", b"public-ca"),
        ("home", "https://home:6443", b"other-ca"),
    ],
)
def test_pinned_override_refuses_context_server_or_ca_mismatch(
    tmp_path: Path, context: str, server: str, ca: bytes
) -> None:
    recorded = _kubeconfig(tmp_path / "recorded")
    override = _kubeconfig(tmp_path / "override", context=context, server=server, ca=ca)

    with pytest.raises(RollbackError, match="immutable identity"):
        resolve_rollback_cluster(
            _deployment(_pinned_snapshot(recorded)), str(override), context
        )


@pytest.mark.parametrize(
    "identity",
    [
        {},
        {"context": "home", "server": "https://home:6443"},
        {"context": "home", "server": "https://home:6443", "ca_sha256": "x" * 64},
    ],
)
def test_malformed_identity_pin_refuses_without_fallback(
    tmp_path: Path, identity: dict
) -> None:
    recorded = _kubeconfig(tmp_path / "recorded")
    snapshot = {
        "kubeconfig": str(recorded),
        "kubeconfig_context": "home",
        "cluster_identity": identity,
    }

    with pytest.raises(RollbackError, match="pin is malformed"):
        resolve_rollback_cluster(_deployment(snapshot), str(recorded), "home")


def test_legacy_snapshot_keeps_server_only_comparison_without_ca(
    tmp_path: Path,
) -> None:
    recorded = _kubeconfig(tmp_path / "recorded")
    override = _kubeconfig(tmp_path / "override", ca=b"other-ca")
    snapshot = {"kubeconfig": str(recorded), "kubeconfig_context": "home"}

    assert resolve_rollback_cluster(_deployment(snapshot), str(override), "home") == (
        str(override),
        "home",
    )


def test_legacy_snapshot_refuses_missing_recorded_file_even_with_override(
    tmp_path: Path,
) -> None:
    recorded = _kubeconfig(tmp_path / "recorded")
    override = _kubeconfig(tmp_path / "override")
    snapshot = {"kubeconfig": str(recorded), "kubeconfig_context": "home"}
    recorded.unlink()

    with pytest.raises(RollbackError, match="Kubeconfig file not found"):
        resolve_rollback_cluster(_deployment(snapshot), str(override), "home")


def test_identity_parser_failure_is_sanitized(tmp_path: Path) -> None:
    path = tmp_path / "broken"
    path.write_text("contexts: [secret: super-secret")
    snapshot = {
        "kubeconfig": str(path),
        "kubeconfig_context": "home",
        "cluster_identity": {
            "context": "home",
            "server": "https://home:6443",
            "ca_sha256": "a" * 64,
        },
    }

    with pytest.raises(RollbackError, match="Cannot inspect") as raised:
        resolve_rollback_cluster(_deployment(snapshot), str(path), "home")
    assert "super-secret" not in str(raised.value)
