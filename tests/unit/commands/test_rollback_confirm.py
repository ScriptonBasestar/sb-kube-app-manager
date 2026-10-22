"""Tests for rollback code-change confirmation and deploy rollback-point recording.

Rollback compares chart version, values digest and source commit of the
current deployment with the state it restores; any difference needs the
difference digest. helm/kubectl are never executed: helm rollback is mocked
at subprocess.run in sbkube.state.rollback and helm upgrade at run_command.
"""

import sqlite3
import subprocess
from datetime import datetime, timedelta
from pathlib import Path
from unittest.mock import MagicMock, patch

import pytest
import yaml
from click.testing import CliRunner

from sbkube.cli import main
from sbkube.commands.deploy import deploy_helm_app
from sbkube.commands.rollback import cmd as rollback_cmd
from sbkube.models.config_model import HelmApp
from sbkube.models.deployment_state import (
    AppDeploymentCreate,
    Deployment,
    DeploymentCreate,
    DeploymentStatus,
    RollbackRequest,
)
from sbkube.state.database import DeploymentDatabase
from sbkube.state.deploy_recorder import DeploymentRecorder, resolve_source_commit
from sbkube.state.rollback import RollbackManager
from sbkube.state.rollback_compare import RollbackConfirmationRequired

COMMIT_A = "a" * 40
COMMIT_B = "b" * 40
CURRENT = "dep-current"
PREVIOUS = "dep-previous"


def _seed(
    db: DeploymentDatabase,
    deployment_id: str,
    *,
    when: datetime,
    revision: int,
    chart_version: str | None = "1.0.0",
    values_digest: str | None = "v" * 64,
    source_commit: str | None = COMMIT_A,
) -> None:
    db.create_deployment(
        DeploymentCreate(
            deployment_id=deployment_id,
            cluster="test-cluster",
            namespace="default",
            app_config_dir="/apps/web",
            config_file_path="/apps/web/config.yaml",
            command="deploy",
            config_snapshot={},
            source_commit=source_commit,
        )
    )
    db.update_deployment_status(deployment_id, DeploymentStatus.SUCCESS)
    with db.get_session() as session:
        row = session.query(Deployment).filter_by(deployment_id=deployment_id).one()
        row.timestamp = when
        row_id = row.id
    app = db.add_app_deployment(
        row_id,
        AppDeploymentCreate(app_name="web", app_type="helm", app_config={}),
    )
    db.update_app_deployment_status(
        app.id,
        DeploymentStatus.SUCCESS,
        rollback_info={
            "type": "helm",
            "release_name": "web",
            "namespace": "default",
            "revision": revision,
            "chart": "repo/web",
            "chart_version": chart_version,
            "values_digest": values_digest,
        },
    )


@pytest.fixture
def db(tmp_path: Path) -> DeploymentDatabase:
    return DeploymentDatabase(tmp_path / "state.db")


def _seed_pair(db: DeploymentDatabase, **previous_overrides) -> None:
    now = datetime(2026, 10, 22, 12, 0, 0)
    _seed(db, PREVIOUS, when=now - timedelta(hours=1), revision=1, **previous_overrides)
    _seed(db, CURRENT, when=now, revision=2)


def _invoke(db: DeploymentDatabase, args: list[str], *, tty: bool = False, input=None):
    """Run `sbkube rollback` against db with helm rollback mocked."""
    helm = MagicMock(return_value=subprocess.CompletedProcess([], 0, "", ""))
    with (
        patch(
            "sbkube.commands.rollback.RollbackManager",
            lambda: RollbackManager(db_path=db.db_path),
        ),
        patch("sbkube.commands.rollback._stdin_is_tty", return_value=tty),
        patch("sbkube.state.rollback.subprocess.run", helm),
    ):
        result = CliRunner().invoke(rollback_cmd, args, input=input)
    return result, helm


def _digest(db: DeploymentDatabase, **request) -> str | None:
    comparison = RollbackManager(db_path=db.db_path).compare_rollback(
        RollbackRequest(deployment_id=CURRENT, **request)
    )
    return comparison.digest


# ---------------------------------------------------------------- comparison


def test_rollback_without_code_change_proceeds(db) -> None:
    _seed_pair(db)

    result, helm = _invoke(db, [CURRENT, "--scope", "all"])

    assert result.exit_code == 0, result.output
    assert "No code change" in result.output
    helm.assert_called_once()
    assert helm.call_args[0][0][:4] == ["helm", "rollback", "web", "1"]


def test_rollback_with_code_change_requires_digest_confirmation(db) -> None:
    _seed_pair(db, chart_version="0.9.0")
    digest = _digest(db)
    assert digest is not None and len(digest) == 12

    refused, helm = _invoke(db, [CURRENT, "--scope", "all"])
    assert refused.exit_code != 0
    assert "chart_version: 1.0.0 -> 0.9.0" in refused.output
    assert digest in refused.output
    helm.assert_not_called()

    typed, helm = _invoke(
        db, [CURRENT, "--scope", "all"], tty=True, input=f"{digest}\n"
    )
    assert typed.exit_code == 0, typed.output
    helm.assert_called_once()

    passed, helm = _invoke(db, [CURRENT, "--scope", "all", "--confirm-digest", digest])
    assert passed.exit_code == 0, passed.output
    helm.assert_called_once()


def test_rollback_without_recorded_source_requires_confirmation(db) -> None:
    _seed_pair(db, source_commit=None)

    result, helm = _invoke(db, [CURRENT, "--scope", "all"])

    assert result.exit_code != 0
    assert (
        "cannot compare: target deployment has no recorded source commit"
        in result.output
    )
    helm.assert_not_called()


def test_rollback_with_dirty_source_requires_confirmation(db) -> None:
    _seed_pair(db, source_commit=f"{COMMIT_A}-dirty")

    result, helm = _invoke(db, [CURRENT, "--scope", "all"])

    assert result.exit_code != 0
    assert "uncommitted changes" in result.output
    helm.assert_not_called()


def test_rollback_with_source_commit_change_requires_confirmation(db) -> None:
    _seed_pair(db, source_commit=COMMIT_B)

    result, helm = _invoke(db, [CURRENT, "--scope", "all"])

    assert result.exit_code != 0
    assert f"source_commit: {COMMIT_A} -> {COMMIT_B}" in result.output
    helm.assert_not_called()


def test_rollback_without_previous_record_requires_confirmation(db) -> None:
    _seed(db, CURRENT, when=datetime(2026, 10, 22), revision=2)

    result, helm = _invoke(db, [CURRENT, "--scope", "all"])

    assert result.exit_code != 0
    assert "no recorded state for the rollback target" in result.output
    helm.assert_not_called()


def test_rollback_target_revision_mismatch_requires_confirmation(db) -> None:
    now = datetime(2026, 10, 22, 12, 0, 0)
    _seed(db, PREVIOUS, when=now - timedelta(hours=1), revision=3)
    _seed(db, CURRENT, when=now, revision=5)

    result, helm = _invoke(db, [CURRENT, "--scope", "all"])

    assert result.exit_code != 0
    assert "not the Helm revision 4" in result.output
    helm.assert_not_called()


# -------------------------------------------------------------- confirmation


def test_rollback_wrong_digest_refused(db) -> None:
    _seed_pair(db, values_digest="w" * 64)

    typed, helm = _invoke(
        db, [CURRENT, "--scope", "all"], tty=True, input="000000000000\n"
    )
    assert typed.exit_code != 0
    assert "does not match" in typed.output
    helm.assert_not_called()

    empty, helm = _invoke(db, [CURRENT, "--scope", "all"], tty=True, input="\n")
    assert empty.exit_code != 0
    assert "no input" in empty.output
    helm.assert_not_called()

    passed, helm = _invoke(
        db, [CURRENT, "--scope", "all", "--confirm-digest", "000000000000"]
    )
    assert passed.exit_code != 0
    helm.assert_not_called()


def test_rollback_force_does_not_bypass_confirmation(db) -> None:
    _seed_pair(db, chart_version="0.9.0")

    result, helm = _invoke(db, [CURRENT, "--scope", "all", "--force"])

    assert result.exit_code != 0
    helm.assert_not_called()


def test_rollback_code_change_non_tty_refused(db) -> None:
    _seed_pair(db, chart_version="0.9.0")

    result, helm = _invoke(
        db, [CURRENT, "--scope", "all"], tty=False, input="anything\n"
    )

    assert result.exit_code != 0
    assert "not an interactive terminal" in result.output
    helm.assert_not_called()


def test_rollback_dry_run_shows_comparison_without_confirmation(db) -> None:
    _seed_pair(db, chart_version="0.9.0")

    result, helm = _invoke(db, [CURRENT, "--scope", "all", "--dry-run"])

    assert result.exit_code == 0, result.output
    assert "chart_version: 1.0.0 -> 0.9.0" in result.output
    assert "Difference digest" in result.output
    helm.assert_not_called()


def test_manager_refuses_unconfirmed_code_change_even_with_force(db) -> None:
    _seed_pair(db, chart_version="0.9.0")
    manager = RollbackManager(db_path=db.db_path)
    request = RollbackRequest(deployment_id=CURRENT, force=True)

    with (
        patch("sbkube.state.rollback.subprocess.run") as helm,
        pytest.raises(RollbackConfirmationRequired),
    ):
        manager.rollback_deployment(request, confirmed_digest=None)
    helm.assert_not_called()

    digest = manager.compare_rollback(request).digest
    with patch("sbkube.state.rollback.subprocess.run") as helm:
        result = manager.rollback_deployment(request, confirmed_digest=digest)
    assert result["success"] is True
    helm.assert_called_once()


# ----------------------------------------------------------------- recording


def _git(repo: Path, *args: str) -> str:
    return subprocess.run(
        ["git", "-C", str(repo), *args],
        check=True,
        capture_output=True,
        text=True,
    ).stdout.strip()


@pytest.fixture
def git_repo(tmp_path: Path) -> Path:
    repo = tmp_path / "repo"
    app_dir = repo / "web"
    app_dir.mkdir(parents=True)
    (app_dir / "values.yaml").write_text("replicaCount: 1\n")
    _git(repo, "init", "-q")
    _git(repo, "add", ".")
    _git(
        repo,
        "-c",
        "user.name=t",
        "-c",
        "user.email=t@example.com",
        "-c",
        "commit.gpgsign=false",
        "commit",
        "-q",
        "-m",
        "init",
    )
    return repo


def _recorder(app_dir: Path, db_path: Path, warn=None) -> DeploymentRecorder:
    return DeploymentRecorder(
        cluster="test-cluster",
        namespace="default",
        app_config_dir=app_dir,
        config_file_path=app_dir / "config.yaml",
        config_data={},
        sources_data=None,
        warn=warn or MagicMock(),
        db_factory=lambda: DeploymentDatabase(db_path),
    )


def _deploy_web(app_dir: Path, recorder: DeploymentRecorder, stdout: str) -> bool:
    chart_dir = app_dir / "chart"
    chart_dir.mkdir(exist_ok=True)
    (chart_dir / "Chart.yaml").write_text("name: web\nversion: 2.3.4\n")
    app = HelmApp(chart="./chart", values=["values.yaml"], namespace="default")
    output = MagicMock()
    with patch("sbkube.commands.deploy.run_command", return_value=(0, stdout, "")):
        return deploy_helm_app(
            "web",
            app,
            app_dir,
            app_dir / ".sbkube" / "charts",
            app_dir / ".sbkube" / "build",
            app_dir,
            output,
            recorder=recorder,
        )


def test_deploy_records_source_commit_and_helm_state(git_repo, tmp_path) -> None:
    app_dir = git_repo / "web"
    recorder = _recorder(app_dir, tmp_path / "state.db")

    assert _deploy_web(app_dir, recorder, "NAME: web\nSTATUS: deployed\nREVISION: 3\n")
    recorder.finish(failed=False)

    detail = DeploymentDatabase(tmp_path / "state.db").get_deployment(
        recorder.deployment_id
    )
    assert detail.source_commit == _git(git_repo, "rev-parse", "HEAD")
    assert detail.status == DeploymentStatus.SUCCESS
    info = detail.apps[0]["rollback_info"]
    assert info["revision"] == 3
    assert info["chart_version"] == "2.3.4"
    assert len(info["values_digest"]) == 64


def test_source_commit_marks_dirty_tree_and_non_git(git_repo, tmp_path) -> None:
    head = _git(git_repo, "rev-parse", "HEAD")
    (git_repo / "web" / "values.yaml").write_text("replicaCount: 2\n")

    assert resolve_source_commit(git_repo / "web") == f"{head}-dirty"
    outside = tmp_path / "plain"
    outside.mkdir()
    assert resolve_source_commit(outside) is None


def test_recording_failure_warns_without_failing_deploy(git_repo) -> None:
    warn = MagicMock()

    def broken_db() -> DeploymentDatabase:
        raise sqlite3.OperationalError("database is locked")

    recorder = DeploymentRecorder(
        cluster="test-cluster",
        namespace="default",
        app_config_dir=git_repo / "web",
        config_file_path=git_repo / "web" / "config.yaml",
        config_data={},
        sources_data=None,
        warn=warn,
        db_factory=broken_db,
    )

    assert _deploy_web(git_repo / "web", recorder, "REVISION: 1\n") is True
    warn.assert_called_once()
    assert "database is locked" in warn.call_args[0][0]
    assert "deploy itself succeeded" in warn.call_args[0][0]


def test_recording_without_revision_warns(git_repo, tmp_path) -> None:
    warn = MagicMock()
    recorder = _recorder(git_repo / "web", tmp_path / "state.db", warn=warn)

    assert _deploy_web(git_repo / "web", recorder, "Release installed") is True
    assert "no REVISION line" in warn.call_args[0][0]
    assert recorder.deployment_id is None


def test_dry_run_deploy_records_nothing(git_repo, tmp_path) -> None:
    recorder = _recorder(git_repo / "web", tmp_path / "state.db")
    chart_dir = git_repo / "web" / "chart"
    chart_dir.mkdir()
    (chart_dir / "Chart.yaml").write_text("name: web\nversion: 2.3.4\n")
    app = HelmApp(chart="./chart", values=["values.yaml"], namespace="default")
    with patch(
        "sbkube.commands.deploy.run_command", return_value=(0, "REVISION: 9", "")
    ):
        assert deploy_helm_app(
            "web",
            app,
            git_repo / "web",
            tmp_path,
            tmp_path,
            git_repo / "web",
            MagicMock(),
            dry_run=True,
            recorder=recorder,
        )
    assert recorder.deployment_id is None


@patch("sbkube.commands.deploy.run_command")
@patch("sbkube.commands.deploy.check_kubectl_installed_or_exit")
@patch("sbkube.commands.deploy.check_helm_installed_or_exit")
@patch("sbkube.commands.deploy.resolve_cluster_config")
@patch("sbkube.commands.deploy.check_cluster_connectivity_or_exit")
def test_deploy_command_records_rollback_point(
    _connectivity,
    mock_resolve_cluster,
    _helm,
    _kubectl,
    mock_run_command,
    git_repo,
    tmp_path,
    monkeypatch,
) -> None:
    db_path = tmp_path / "state.db"
    monkeypatch.setattr(
        "sbkube.state.deploy_recorder.DeploymentDatabase",
        lambda: DeploymentDatabase(db_path),
    )
    mock_resolve_cluster.return_value = (None, "test-context")
    mock_run_command.return_value = (0, "STATUS: deployed\nREVISION: 7\n", "")
    app_dir = git_repo / "web"
    (git_repo / "sources.yaml").write_text("cluster: test-cluster\n")
    (app_dir / "config.yaml").write_text(
        yaml.dump(
            {
                "namespace": "default",
                "apps": {
                    "web": {
                        "type": "helm",
                        "chart": "./chart",
                        "values": ["values.yaml"],
                    }
                },
            }
        )
    )
    (app_dir / "chart").mkdir()
    (app_dir / "chart" / "Chart.yaml").write_text("name: web\nversion: 2.3.4\n")

    result = CliRunner().invoke(main, ["deploy", str(app_dir)])

    assert result.exit_code == 0, result.output
    deployments = DeploymentDatabase(db_path).list_deployments(cluster="test-cluster")
    assert len(deployments) == 1
    detail = DeploymentDatabase(db_path).get_deployment(deployments[0].deployment_id)
    assert detail.status == DeploymentStatus.SUCCESS
    assert detail.source_commit is not None
    assert detail.source_commit.startswith(_git(git_repo, "rev-parse", "HEAD"))
    assert detail.apps[0]["rollback_info"]["revision"] == 7


# ----------------------------------------------------------------- migration


def test_existing_database_gains_source_commit_column(tmp_path) -> None:
    db_path = tmp_path / "old.db"
    conn = sqlite3.connect(db_path)
    conn.execute(
        "CREATE TABLE deployments (id INTEGER PRIMARY KEY, deployment_id VARCHAR(64) "
        "NOT NULL UNIQUE, timestamp DATETIME NOT NULL, cluster VARCHAR(255) NOT NULL, "
        "namespace VARCHAR(255) NOT NULL, app_config_dir VARCHAR(1024) NOT NULL, "
        "config_file_path VARCHAR(1024) NOT NULL, command VARCHAR(50) NOT NULL, "
        "command_args JSON, dry_run BOOLEAN, status VARCHAR(20), error_message TEXT, "
        "config_snapshot JSON NOT NULL, sources_snapshot JSON, sbkube_version VARCHAR(20), "
        "operator VARCHAR(255))"
    )
    conn.execute(
        "INSERT INTO deployments (deployment_id, timestamp, cluster, namespace, "
        "app_config_dir, config_file_path, command, status, config_snapshot) VALUES "
        "('dep-old', '2025-01-01 00:00:00', 'c', 'n', '/a', '/a/c.yaml', 'deploy', "
        "'success', '{}')"
    )
    conn.commit()
    conn.close()

    db = DeploymentDatabase(db_path)
    DeploymentDatabase(db_path)  # second open must not re-add the column

    columns = {
        row[1]
        for row in sqlite3.connect(db_path).execute("PRAGMA table_info(deployments)")
    }
    assert "source_commit" in columns
    assert db.get_deployment("dep-old").source_commit is None
