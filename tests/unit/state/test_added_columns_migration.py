"""Migration tests for DeploymentDatabase._ADDED_COLUMNS.

create_all() never alters an existing table, so databases created before a
column existed gain it through _ADDED_COLUMNS. Each test builds the old
schema by hand, reopens the database and checks the column arrives, survives
a second open and leaves old rows NULL. The regression target is the
production failure "table app_deployments has no column named app_group"
(state DB created before v0.5.0), so the app_deployments test also replays
the INSERT that crashed on the unmigrated database.
"""

import sqlite3

from sbkube.models.deployment_state import AppDeploymentCreate
from sbkube.state.database import DeploymentDatabase


def _create_pre_app_group_database(db_path) -> None:
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
        "CREATE TABLE app_deployments (id INTEGER PRIMARY KEY, deployment_id INTEGER "
        "NOT NULL, app_name VARCHAR(255) NOT NULL, app_type VARCHAR(50) NOT NULL, "
        "namespace VARCHAR(255), status VARCHAR(20), error_message TEXT, "
        "app_config JSON NOT NULL, deployment_metadata JSON, rollback_info JSON)"
    )
    conn.execute(
        "INSERT INTO deployments (deployment_id, timestamp, cluster, namespace, "
        "app_config_dir, config_file_path, command, status, config_snapshot) VALUES "
        "('dep-old', '2025-01-01 00:00:00', 'c', 'n', '/a', '/a/c.yaml', 'deploy', "
        "'success', '{}')"
    )
    conn.execute(
        "INSERT INTO app_deployments (deployment_id, app_name, app_type, namespace, "
        "status, app_config) VALUES (1, 'web', 'helm', 'n', 'success', '{}')"
    )
    conn.commit()
    conn.close()


def test_existing_database_gains_app_group_column(tmp_path) -> None:
    db_path = tmp_path / "old-app-group.db"
    _create_pre_app_group_database(db_path)

    db = DeploymentDatabase(db_path)
    DeploymentDatabase(db_path)  # second open must not re-add the column

    columns = {
        row[1]
        for row in sqlite3.connect(db_path).execute(
            "PRAGMA table_info(app_deployments)"
        )
    }
    assert "app_group" in columns
    old_group = (
        sqlite3.connect(db_path)
        .execute("SELECT app_group FROM app_deployments WHERE app_name = 'web'")
        .fetchone()[0]
    )
    assert old_group is None
    # The INSERT that failed on the unmigrated DB ("table app_deployments has
    # no column named app_group") must now go through.
    app = db.add_app_deployment(
        1,
        AppDeploymentCreate(
            app_name="web2", app_type="helm", namespace="n", app_config={}
        ),
    )
    assert app.id is not None
