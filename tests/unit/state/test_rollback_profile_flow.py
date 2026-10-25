"""Rollback selects the recorded app owner's credential and preserves its pin."""

import base64
import json
import time
from datetime import datetime
from pathlib import Path
from unittest.mock import patch

import pytest
import yaml

from sbkube.exceptions import RollbackError
from sbkube.models.deployment_state import (
    DeploymentDetail,
    DeploymentStatus,
    RollbackRequest,
)
from sbkube.state.rollback import RollbackManager
from sbkube.utils.cluster_identity import cluster_identity


def _owner(root: Path) -> Path:
    for name, sa in (("readonly", "agent-readonly"), ("deployer", "sbkube-deployer")):
        payload = (
            base64.urlsafe_b64encode(
                json.dumps(
                    {
                        "sub": f"system:serviceaccount:agent-access:{sa}",
                        "exp": time.time() + 3600,
                    }
                ).encode()
            )
            .rstrip(b"=")
            .decode()
        )
        (root / name).write_text(
            yaml.safe_dump(
                {
                    "contexts": [
                        {"name": "home", "context": {"cluster": "c", "user": "sa"}}
                    ],
                    "clusters": [
                        {
                            "name": "c",
                            "cluster": {
                                "server": "https://home",
                                "certificate-authority-data": "Q0E=",
                            },
                        }
                    ],
                    "users": [
                        {"name": "sa", "user": {"token": f"e30.{payload}.signature"}}
                    ],
                }
            )
        )
    (root / "sbkube.yaml").write_text(
        yaml.safe_dump(
            {
                "apiVersion": "sbkube/v1",
                "settings": {
                    "kubeconfig": str(root / "deleted-admin"),
                    "kubeconfig_context": "home",
                    "access": {
                        "readonly": {"kubeconfig": str(root / "readonly")},
                        "deployer": {"kubeconfig": str(root / "deployer")},
                    },
                },
            }
        )
    )
    return root / "deployer"


def _record(root: Path, pin: dict | None) -> DeploymentDetail:
    snapshot = {"kubeconfig": str(root / "deleted-admin"), "kubeconfig_context": "home"}
    if pin is not None:
        snapshot["cluster_identity"] = pin
    return DeploymentDetail(
        deployment_id="current",
        timestamp=datetime(2026, 10, 26),
        cluster="home",
        namespace="default",
        app_config_dir=str(root),
        config_file_path=str(root / "sbkube.yaml"),
        status=DeploymentStatus.SUCCESS,
        config_snapshot={},
        sources_snapshot=snapshot,
    )


def test_manager_uses_recorded_owner_when_credential_path_was_removed(
    tmp_path: Path,
) -> None:
    chosen = _owner(tmp_path)
    pin = cluster_identity(chosen, "home")
    record = _record(tmp_path, pin)
    with patch("sbkube.state.rollback.DeploymentDatabase") as database:
        database.return_value.get_deployment.return_value = record
        manager = RollbackManager()
        manager._load_deployments(RollbackRequest(deployment_id="current"))
    assert manager._cluster == (str(chosen), "home")
    assert manager._cluster_pin == pin


def test_legacy_missing_recorded_public_cluster_info_is_not_bypassed(
    tmp_path: Path,
) -> None:
    _owner(tmp_path)
    with patch("sbkube.state.rollback.DeploymentDatabase") as database:
        database.return_value.get_deployment.return_value = _record(tmp_path, None)
        with pytest.raises(RollbackError, match="not found"):
            RollbackManager()._load_deployments(
                RollbackRequest(deployment_id="current")
            )


def test_new_rollback_record_keeps_actual_pin_when_restored_source_is_older(
    tmp_path: Path,
) -> None:
    chosen = _owner(tmp_path)
    pin = cluster_identity(chosen, "home")
    current, old_source = _record(tmp_path, pin), _record(tmp_path, None)
    current.apps = [
        {
            "name": "app",
            "type": "helm",
            "rollback_info": {
                "type": "helm",
                "revision": 3,
                "release_name": "app",
                "namespace": "default",
            },
        }
    ]
    with patch("sbkube.state.rollback.DeploymentDatabase") as database:
        manager = RollbackManager()
        manager._cluster = (str(chosen), "home")
        manager._cluster_pin = pin
        with (
            patch.object(manager, "_restore_source_record", return_value=old_source),
            patch.object(manager, "_live_helm_revision", return_value=2),
        ):
            manager._record_rollback(
                current, old_source, {"rollbacks": [{"app": "app", "success": True}]}
            )
        written = database.return_value.create_deployment.call_args.args[0]
    assert written.sources_snapshot["cluster_identity"] == pin
    assert written.sources_snapshot["kubeconfig"] == str(chosen)
