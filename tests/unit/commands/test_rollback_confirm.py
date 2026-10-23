"""Tests for rollback code-change confirmation, rollback-point recording and listing.

Rollback compares chart, chart version, values digest and source commit of
the current deployment with the state it restores; any difference needs the
difference digest. helm/kubectl are never executed: helm rollback is mocked
at subprocess.run and helm status at run_command in sbkube.state.rollback,
helm upgrade at run_command in sbkube.commands.deploy.
"""

import json
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
from sbkube.state.rollback import HELM_STATUS_TIMEOUT_SECONDS, RollbackManager
from sbkube.state.rollback_compare import RollbackConfirmationRequired
from sbkube.utils.common import run_command

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
    chart: str = "repo/web",
    chart_version: str | None = "1.0.0",
    values_digest: str | None = "v" * 64,
    source_commit: str | None = COMMIT_A,
    release_name: str = "web",
    namespace: str = "default",
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
            "release_name": release_name,
            "namespace": namespace,
            "revision": revision,
            "chart": chart,
            "chart_version": chart_version,
            "values_digest": values_digest,
        },
    )


@pytest.fixture
def db(tmp_path: Path) -> DeploymentDatabase:
    return DeploymentDatabase(tmp_path / "state.db")


def _helm_status(revision: int) -> tuple[int, str, str]:
    return 0, json.dumps({"name": "web", "version": revision}), ""


@pytest.fixture(autouse=True)
def live_status():
    """`helm status` result; the live release is at revision 2 unless changed."""
    with patch(
        "sbkube.state.rollback.run_command", return_value=_helm_status(2)
    ) as status:
        yield status


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


def test_rollback_with_confirm_digest_option(db) -> None:
    _seed_pair(db, chart_version="0.9.0")
    digest = _digest(db)

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


def test_rollback_target_at_other_revision_is_rejected(db, live_status) -> None:
    now = datetime(2026, 10, 22, 12, 0, 0)
    _seed(db, PREVIOUS, when=now - timedelta(hours=1), revision=3)
    _seed(db, CURRENT, when=now, revision=5)
    live_status.return_value = _helm_status(5)

    result, helm = _invoke(db, [CURRENT, "--scope", "all", "--target", PREVIOUS])

    assert result.exit_code != 0
    assert "rollback restores revision 4" in result.output
    helm.assert_not_called()


def test_rollback_without_target_ignores_records_at_other_revisions(
    db, live_status
) -> None:
    now = datetime(2026, 10, 22, 12, 0, 0)
    _seed(db, PREVIOUS, when=now - timedelta(hours=1), revision=3)
    _seed(db, CURRENT, when=now, revision=5)
    live_status.return_value = _helm_status(5)

    result, helm = _invoke(db, [CURRENT, "--scope", "all"])

    assert result.exit_code != 0
    assert "no recorded state for the rollback target" in result.output
    helm.assert_not_called()


def test_rollback_chart_change_requires_confirmation(db) -> None:
    _seed_pair(db, chart="other/web")

    result, helm = _invoke(db, [CURRENT, "--scope", "all"])

    assert result.exit_code != 0
    assert "chart: repo/web -> other/web" in result.output
    helm.assert_not_called()


# ------------------------------------------------- live state (review P1-1)


def test_rollback_of_stale_deployment_with_recorded_source_requires_confirmation(
    db,
) -> None:
    """d2 is not live when d3 is newer, even though d1 matches d2 exactly."""
    now = datetime(2026, 10, 22, 12, 0, 0)
    _seed(db, "d1", when=now - timedelta(hours=2), revision=1)
    _seed(db, "d2", when=now - timedelta(hours=1), revision=2)
    _seed(db, "d3", when=now, revision=3)

    result, helm = _invoke(db, ["d2", "--scope", "all"])

    assert result.exit_code != 0
    assert "d2 is not the newest record of release web in default (newest: d3)" in (
        result.output
    )
    helm.assert_not_called()


def test_rollback_live_revision_mismatch_requires_confirmation(db, live_status) -> None:
    _seed_pair(db)
    live_status.return_value = _helm_status(4)

    result, helm = _invoke(db, [CURRENT, "--scope", "all"])

    assert result.exit_code != 0
    assert "live Helm revision 4 of web differs from recorded revision 2" in (
        result.output
    )
    helm.assert_not_called()
    assert live_status.call_args[0][0] == [
        "helm",
        "status",
        "web",
        "-n",
        "default",
        "-o",
        "json",
    ]


@pytest.mark.parametrize(
    "status",
    [(1, "", "Error: release: not found"), (0, "not json", ""), (0, "{}", "")],
    ids=["helm-fails", "unparsable", "no-version"],
)
def test_rollback_unreadable_live_revision_requires_confirmation(
    db, live_status, status
) -> None:
    _seed_pair(db)
    live_status.return_value = status

    result, helm = _invoke(db, [CURRENT, "--scope", "all"])

    assert result.exit_code != 0
    assert "live Helm revision of web in default could not be read" in result.output
    helm.assert_not_called()


def test_rollback_helm_status_timeout_requires_confirmation(db, live_status) -> None:
    """A hung `helm status` is cut at 60s and counts as unreadable."""
    _seed_pair(db)
    live_status.side_effect = run_command
    timeout = subprocess.TimeoutExpired(["helm", "status"], 60)

    with patch("sbkube.utils.common.subprocess.run", side_effect=timeout) as run:
        comparison = RollbackManager(db_path=db.db_path).compare_rollback(
            RollbackRequest(deployment_id=CURRENT)
        )

    assert run.call_args.kwargs["timeout"] == HELM_STATUS_TIMEOUT_SECONDS == 60
    assert comparison.requires_confirmation
    assert comparison.apps[0].uncomparable_reason == (
        "live Helm revision of web in default could not be read"
    )


# -------------------------------------------- release identity (review P1-2)


def test_rollback_with_recorded_source_ignores_same_app_name_in_other_release(
    db,
) -> None:
    """A newer record of app 'web' for another release must not be the target."""
    now = datetime(2026, 10, 22, 12, 0, 0)
    _seed(db, "d-same-release", when=now - timedelta(hours=3), revision=1)
    _seed(
        db,
        "d-other-release",
        when=now - timedelta(hours=2),
        revision=1,
        release_name="web-canary",
        chart_version="0.1.0",
    )
    _seed(
        db,
        "d-other-namespace",
        when=now - timedelta(hours=1),
        revision=1,
        namespace="staging",
        chart_version="0.2.0",
    )
    _seed(db, CURRENT, when=now, revision=2)

    result, helm = _invoke(db, [CURRENT, "--scope", "all"])

    assert result.exit_code == 0, result.output
    assert "No code change" in result.output
    helm.assert_called_once()


def test_rollback_with_only_other_release_recorded_requires_confirmation(db) -> None:
    now = datetime(2026, 10, 22, 12, 0, 0)
    _seed(db, PREVIOUS, when=now - timedelta(hours=1), revision=1, release_name="web-b")
    _seed(db, CURRENT, when=now, revision=2)

    result, helm = _invoke(db, [CURRENT, "--scope", "all"])

    assert result.exit_code != 0
    assert "no recorded state for the rollback target" in result.output
    helm.assert_not_called()


def test_rollback_target_of_other_release_requires_confirmation(db) -> None:
    now = datetime(2026, 10, 22, 12, 0, 0)
    _seed(db, PREVIOUS, when=now - timedelta(hours=1), revision=1, namespace="staging")
    _seed(db, CURRENT, when=now, revision=2)

    result, helm = _invoke(db, [CURRENT, "--scope", "all", "--target", PREVIOUS])

    assert result.exit_code != 0
    assert f"--target {PREVIOUS} has no record of release web in namespace default" in (
        result.output
    )
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


def test_source_commit_marks_untracked_files_dirty(git_repo) -> None:
    (git_repo / ".gitignore").write_text(".sbkube/\n")
    _git(git_repo, "add", ".gitignore")
    _git(
        git_repo,
        "-c",
        "user.name=t",
        "-c",
        "user.email=t@example.com",
        "-c",
        "commit.gpgsign=false",
        "commit",
        "-q",
        "-m",
        "ignore",
    )
    head = _git(git_repo, "rev-parse", "HEAD")
    (git_repo / "web" / ".sbkube").mkdir()
    (git_repo / "web" / ".sbkube" / "work.yaml").write_text("x: 1\n")
    assert resolve_source_commit(git_repo / "web") == head

    (git_repo / "web" / "extra-values.yaml").write_text("x: 1\n")
    assert resolve_source_commit(git_repo / "web") == f"{head}-dirty"


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


def test_migration_ignores_concurrently_added_column(tmp_path) -> None:
    """A duplicate-column error from a concurrent ALTER is not fatal."""
    DeploymentDatabase(tmp_path / "state.db")

    class RacingDatabase(DeploymentDatabase):
        # SQLite column names are case-insensitive: PRAGMA misses it, ALTER fails
        _ADDED_COLUMNS = (("deployments", "SOURCE_COMMIT", "VARCHAR(80)"),)

    RacingDatabase(tmp_path / "state.db")


# ------------------------------------------------------- recorder lifecycle


@patch("sbkube.commands.deploy.deploy_helm_app", side_effect=RuntimeError("boom"))
@patch("sbkube.commands.deploy.DeploymentRecorder")
@patch("sbkube.commands.deploy.check_kubectl_installed_or_exit")
@patch("sbkube.commands.deploy.check_helm_installed_or_exit")
@patch("sbkube.commands.deploy.resolve_cluster_config")
@patch("sbkube.commands.deploy.check_cluster_connectivity_or_exit")
def test_deploy_exception_still_finishes_recorder(
    _connectivity,
    mock_resolve_cluster,
    _helm,
    _kubectl,
    mock_recorder_cls,
    _deploy_helm_app,
    tmp_path,
) -> None:
    mock_resolve_cluster.return_value = (None, "test-context")
    app_dir = tmp_path / "web"
    app_dir.mkdir()
    (app_dir / "config.yaml").write_text(
        yaml.dump(
            {
                "namespace": "default",
                "apps": {"web": {"type": "helm", "chart": "./chart"}},
            }
        )
    )

    result = CliRunner().invoke(main, ["deploy", str(app_dir)])

    assert result.exit_code != 0
    mock_recorder_cls.return_value.finish.assert_called_once_with(failed=True)


# ------------------------------------------------------- rollback recording


def test_successful_rollback_records_entry_and_next_compare_uses_it(
    db: DeploymentDatabase, live_status
) -> None:
    _seed_pair(db)
    live_status.return_value = _helm_status(3)  # revision after helm rollback

    result, _ = _invoke(db, [CURRENT, "--confirm-digest", _digest(db) or ""])

    assert result.exit_code == 0, result.output
    manager = RollbackManager(db_path=db.db_path)
    newest = db.get_latest_helm_release_deployment_id("test-cluster", "web", "default")
    assert newest not in (CURRENT, PREVIOUS)
    detail = db.get_deployment(newest)
    assert detail.status == DeploymentStatus.SUCCESS
    assert detail.source_commit == COMMIT_A
    info = detail.apps[0]["rollback_info"]
    assert info["revision"] == 3
    assert info["restored_from"] == PREVIOUS
    assert info["rolled_back_from"] == CURRENT
    assert info["chart_version"] == "1.0.0"

    # Next rollback restores revision 2 (the pre-rollback record), comparable.
    comparison = manager.compare_rollback(RollbackRequest(deployment_id=newest))
    assert comparison.apps[0].target.deployment_id == CURRENT
    assert comparison.apps[0].uncomparable_reason is None


def test_failed_helm_rollback_records_nothing(db: DeploymentDatabase) -> None:
    _seed_pair(db)
    helm = MagicMock(
        side_effect=subprocess.CalledProcessError(1, "helm", stderr="boom")
    )
    with patch("sbkube.state.rollback.subprocess.run", helm):
        with pytest.raises(Exception):
            RollbackManager(db_path=db.db_path).rollback_deployment(
                RollbackRequest(deployment_id=CURRENT),
                confirmed_digest=_digest(db),
            )
    assert (
        db.get_latest_helm_release_deployment_id("test-cluster", "web", "default")
        == CURRENT
    )


def test_recording_failure_does_not_fail_rollback(
    db: DeploymentDatabase, live_status
) -> None:
    _seed_pair(db)
    live_status.return_value = _helm_status(3)
    manager = RollbackManager(db_path=db.db_path)
    with (
        patch("sbkube.state.rollback.subprocess.run") as helm,
        patch.object(manager.db, "create_deployment", side_effect=OSError("disk")),
    ):
        helm.return_value = subprocess.CompletedProcess([], 0, "", "")
        result = manager.rollback_deployment(
            RollbackRequest(deployment_id=CURRENT), confirmed_digest=_digest(db)
        )
    assert result["success"] is True
    assert (
        db.get_latest_helm_release_deployment_id("test-cluster", "web", "default")
        == CURRENT
    )


# ---------------------------------------------------------------- --list


def test_list_rollback_points_reports_app_count(db) -> None:
    _seed_pair(db)
    args = ["--list", "--cluster", "test-cluster", "--namespace", "default"]
    args += ["--base-dir", "/", "--app-dir", "apps/web"]
    result, helm = _invoke(db, args)
    assert result.exit_code == 0, result.output
    assert (
        f"{CURRENT} - 2026-10-22 12:00:00 - 1 apps - Status: success" in result.output
    )
    assert (
        f"{PREVIOUS} - 2026-10-22 11:00:00 - 1 apps - Status: success" in result.output
    )
    helm.assert_not_called()


def test_list_rollback_points_limit_counts_only_the_requested_app_dir(db) -> None:
    _seed_pair(db)
    for i in range(3):
        db.create_deployment(
            DeploymentCreate(
                deployment_id=f"dep-other-{i}",
                cluster="test-cluster",
                namespace="default",
                app_config_dir="/apps/other",
                config_file_path="/apps/other/config.yaml",
                command="deploy",
                config_snapshot={},
            )
        )
        with db.get_session() as session:
            row = session.query(Deployment).filter_by(deployment_id=f"dep-other-{i}")
            row.one().timestamp = datetime(2026, 10, 22, 13, i)
    args = ["--list", "--cluster", "test-cluster", "--namespace", "default"]
    args += ["--base-dir", "/", "--app-dir", "apps/web", "--limit", "2"]
    result, _ = _invoke(db, args)
    assert result.exit_code == 0, result.output
    assert CURRENT in result.output
    assert PREVIOUS in result.output
    assert "dep-other" not in result.output
