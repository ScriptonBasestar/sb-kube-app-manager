"""Tests for rollback cluster pinning (issue #6) and app selection (issue #5).

Rollback runs helm/kubectl against the kubeconfig and context recorded with
the deployment, or the global --kubeconfig/--context when they match it; an
empty app selection never widens to every app. helm is never executed: helm
rollback is mocked at subprocess.run and helm status at run_command in
sbkube.state.rollback.
"""

import json
import subprocess
from datetime import datetime, timedelta
from pathlib import Path
from unittest.mock import MagicMock, patch

import pytest
from click.testing import CliRunner

from sbkube.cli import main
from sbkube.exceptions import RollbackError
from sbkube.models.deployment_state import (
    AppDeploymentCreate,
    Deployment,
    DeploymentCreate,
    DeploymentStatus,
    RollbackRequest,
)
from sbkube.state.database import DeploymentDatabase
from sbkube.state.rollback import RollbackManager

CURRENT = "dep-current"
PREVIOUS = "dep-previous"
CONTEXT = "home-cluster"
SERVER = "https://home:6443"


def _write_kubeconfig(path: Path, context: str = CONTEXT, server: str = SERVER) -> Path:
    path.write_text(
        f"contexts:\n- name: {context}\n  context: {{cluster: c}}\n"
        f"clusters:\n- name: c\n  cluster: {{server: '{server}'}}\n"
    )
    return path


def _seed(
    db: DeploymentDatabase,
    deployment_id: str,
    *,
    when: datetime,
    revision: int,
    sources_snapshot: dict | None,
) -> None:
    db.create_deployment(
        DeploymentCreate(
            deployment_id=deployment_id,
            cluster="home",
            namespace="default",
            app_config_dir="/apps/web",
            config_file_path="/apps/web/config.yaml",
            command="deploy",
            config_snapshot={},
            sources_snapshot=sources_snapshot,
            source_commit="a" * 40,
        )
    )
    db.update_deployment_status(deployment_id, DeploymentStatus.SUCCESS)
    with db.get_session() as session:
        row = session.query(Deployment).filter_by(deployment_id=deployment_id).one()
        row.timestamp = when
        row_id = row.id
    for name in ("web", "api"):
        app = db.add_app_deployment(
            row_id,
            AppDeploymentCreate(app_name=name, app_type="helm", app_config={}),
        )
        db.update_app_deployment_status(
            app.id,
            DeploymentStatus.SUCCESS,
            rollback_info={
                "type": "helm",
                "release_name": name,
                "namespace": "default",
                "revision": revision,
                "chart": "repo/web",
                "chart_version": "1.0.0",
                "values_digest": "v" * 64,
            },
        )


@pytest.fixture
def kubeconfig(tmp_path: Path) -> Path:
    return _write_kubeconfig(tmp_path / "kubeconfig")


@pytest.fixture
def db(tmp_path: Path) -> DeploymentDatabase:
    return DeploymentDatabase(tmp_path / "state.db")


def _seed_pair(db: DeploymentDatabase, sources_snapshot: dict | None) -> None:
    now = datetime(2026, 10, 24, 12, 0, 0)
    _seed(
        db,
        PREVIOUS,
        when=now - timedelta(hours=1),
        revision=1,
        sources_snapshot=sources_snapshot,
    )
    _seed(db, CURRENT, when=now, revision=2, sources_snapshot=sources_snapshot)


def _recorded(kubeconfig: Path) -> dict:
    return {"kubeconfig": str(kubeconfig), "kubeconfig_context": CONTEXT}


@pytest.fixture(autouse=True)
def live_status():
    """`helm status`: every release is live at revision 2."""
    with patch(
        "sbkube.state.rollback.run_command",
        return_value=(0, json.dumps({"version": 2}), ""),
    ) as status:
        yield status


def _invoke(db: DeploymentDatabase, args: list[str], *, group_args=()):
    """Run `sbkube [group_args] rollback args` against db with helm mocked."""
    helm = MagicMock(return_value=subprocess.CompletedProcess([], 0, "", ""))
    with (
        patch(
            "sbkube.commands.rollback.RollbackManager",
            lambda **kw: RollbackManager(db_path=db.db_path, **kw),
        ),
        patch("sbkube.commands.rollback._stdin_is_tty", return_value=False),
        patch("sbkube.state.rollback.subprocess.run", helm),
    ):
        result = CliRunner().invoke(main, [*group_args, "rollback", *args])
    return result, helm


def _cluster_args(kubeconfig: Path) -> list[str]:
    return ["--kubeconfig", str(kubeconfig), "--kube-context", CONTEXT]


def _text(result) -> str:
    """Command output with the console's line wrapping undone."""
    return " ".join(result.output.split())


# ------------------------------------------------------------ cluster pinning


def test_rollback_uses_recorded_kubeconfig_and_context(
    db, kubeconfig, live_status
) -> None:
    _seed_pair(db, _recorded(kubeconfig))

    result, helm = _invoke(db, [CURRENT, "--app", "web"])

    assert result.exit_code == 0, result.output
    assert live_status.call_args[0][0][-4:] == _cluster_args(kubeconfig)
    assert helm.call_args[0][0] == [
        "helm",
        "rollback",
        "web",
        "1",
        "-n",
        "default",
        *_cluster_args(kubeconfig),
    ]


def test_rollback_expands_recorded_home_path(
    db, tmp_path, monkeypatch, live_status
) -> None:
    monkeypatch.setenv("HOME", str(tmp_path))
    (tmp_path / ".kube").mkdir()
    _write_kubeconfig(tmp_path / ".kube" / "home")
    _seed_pair(db, {"kubeconfig": "~/.kube/home", "kubeconfig_context": CONTEXT})

    result, _ = _invoke(db, [CURRENT, "--app", "web", "--dry-run"])

    assert result.exit_code == 0, result.output
    assert live_status.call_args[0][0][-4:-2] == [
        "--kubeconfig",
        str(tmp_path / ".kube" / "home"),
    ]


def test_rollback_with_matching_cli_context_uses_cli_kubeconfig(
    db, kubeconfig, tmp_path
) -> None:
    _seed_pair(db, _recorded(kubeconfig))
    other = _write_kubeconfig(tmp_path / "other-kubeconfig")

    result, helm = _invoke(
        db,
        [CURRENT, "--app", "web"],
        group_args=["--kubeconfig", str(other), "--context", CONTEXT],
    )

    assert result.exit_code == 0, result.output
    assert helm.call_args[0][0][-4:] == _cluster_args(other)


def test_rollback_refuses_cli_context_other_than_recorded(db, kubeconfig) -> None:
    _seed_pair(db, _recorded(kubeconfig))

    result, helm = _invoke(
        db,
        [CURRENT, "--app", "web"],
        group_args=["--kubeconfig", str(kubeconfig), "--context", "dev-cluster"],
    )

    assert result.exit_code != 0
    assert "is not the cluster recorded" in _text(result)
    helm.assert_not_called()


def test_rollback_refuses_same_context_name_on_another_server(
    db, kubeconfig, tmp_path
) -> None:
    """k3s names every context `default`; a different server tells them apart."""
    _seed_pair(db, _recorded(kubeconfig))
    other = _write_kubeconfig(tmp_path / "other", server="https://dev:6443")

    result, helm = _invoke(
        db,
        [CURRENT, "--app", "web"],
        group_args=["--kubeconfig", str(other), "--context", CONTEXT],
    )

    assert result.exit_code != 0
    assert "is not the cluster recorded" in _text(result)
    helm.assert_not_called()


def test_rollback_refuses_context_missing_from_kubeconfig(db, tmp_path) -> None:
    stale = _write_kubeconfig(tmp_path / "stale", context="dev-cluster")
    _seed_pair(db, _recorded(stale))

    result, helm = _invoke(db, [CURRENT, "--app", "web"])

    assert result.exit_code != 0
    assert f"Context {CONTEXT} not found in kubeconfig" in _text(result)
    helm.assert_not_called()


def test_rollback_without_recorded_cluster_requires_cli_options(db, kubeconfig) -> None:
    _seed_pair(db, None)

    result, helm = _invoke(db, [CURRENT, "--app", "web"])

    assert result.exit_code != 0
    assert "records no kubeconfig and context" in _text(result)
    helm.assert_not_called()

    result, helm = _invoke(
        db,
        [CURRENT, "--app", "web"],
        group_args=["--kubeconfig", str(kubeconfig), "--context", CONTEXT],
    )
    assert result.exit_code == 0, result.output
    assert helm.call_args[0][0][-4:] == _cluster_args(kubeconfig)


def test_rollback_refuses_missing_kubeconfig_file(db, tmp_path) -> None:
    _seed_pair(db, _recorded(tmp_path / "gone"))

    result, helm = _invoke(db, [CURRENT, "--app", "web"])

    assert result.exit_code != 0
    assert "Kubeconfig file not found" in _text(result)
    helm.assert_not_called()


def test_rollback_record_keeps_the_cluster_it_ran_on(db, kubeconfig, tmp_path) -> None:
    _seed_pair(db, None)

    result, _ = _invoke(
        db,
        [CURRENT, "--app", "web"],
        group_args=["--kubeconfig", str(kubeconfig), "--context", CONTEXT],
    )

    assert result.exit_code == 0, result.output
    rollbacks = [
        d
        for d in db.list_deployments(limit=10)
        if d.deployment_id not in (CURRENT, PREVIOUS)
    ]
    assert len(rollbacks) == 1
    record = db.get_deployment(rollbacks[0].deployment_id)
    assert record.sources_snapshot == _recorded(kubeconfig)


def test_list_does_not_need_a_cluster(db) -> None:
    _seed_pair(db, None)

    result, _ = _invoke(db, ["--list", "--cluster", "home", "--namespace", "default"])

    assert result.exit_code == 0, result.output


# -------------------------------------------------------------- app selection


def test_phase_without_apps_aborts_instead_of_rolling_back_all(db, kubeconfig) -> None:
    _seed_pair(db, _recorded(kubeconfig))

    result, helm = _invoke(db, [CURRENT, "--scope", "phase", "--phase", "p9-typo"])

    assert result.exit_code != 0
    assert "No apps found for phase 'p9-typo'" in _text(result)
    helm.assert_not_called()


def test_manager_refuses_empty_app_selection(db, kubeconfig) -> None:
    _seed_pair(db, _recorded(kubeconfig))
    manager = RollbackManager(db_path=db.db_path)

    with pytest.raises(RollbackError, match="No apps selected"):
        manager.rollback_deployment(
            RollbackRequest(deployment_id=CURRENT, app_names=[], dry_run=True)
        )


def test_app_selection_touches_only_named_apps(db, kubeconfig) -> None:
    _seed_pair(db, _recorded(kubeconfig))

    result, helm = _invoke(db, [CURRENT, "--app", "api"])

    assert result.exit_code == 0, result.output
    assert [call[0][0][2] for call in helm.call_args_list] == ["api"]
