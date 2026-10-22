"""Record successful deploys as rollback points.

The deploy path calls DeploymentRecorder after each successful Helm
install/upgrade. Each record keeps what `sbkube rollback` compares before it
acts: chart, chart version, values digest, Helm revision and the source
commit of the repository that holds the app config.

The state DB is auxiliary: a recording failure prints a visible warning and
never fails a deploy that already reached the cluster.
"""

import hashlib
import json
import os
import re
import subprocess
import uuid
from collections.abc import Callable
from datetime import UTC, datetime
from pathlib import Path
from typing import Any

import yaml

from sbkube.models.deployment_state import (
    AppDeploymentCreate,
    DeploymentCreate,
    DeploymentStatus,
)
from sbkube.state.database import DeploymentDatabase

DIRTY_SUFFIX = "-dirty"

_REVISION_PATTERN = re.compile(r"^REVISION:\s*(\d+)\s*$", re.MULTILINE)


def resolve_source_commit(path: Path) -> str | None:
    """Return HEAD of the git repository containing path.

    Tracked uncommitted changes append ``-dirty``. Untracked files are
    ignored because sbkube writes its own work directories next to configs;
    values content is compared separately through the values digest.

    Returns None when path is not inside a git work tree or git is missing.
    """
    try:
        head = subprocess.run(
            ["git", "-C", str(path), "rev-parse", "HEAD"],
            capture_output=True,
            text=True,
            check=False,
        )
        if head.returncode != 0:
            return None
        status = subprocess.run(
            ["git", "-C", str(path), "status", "--porcelain", "--untracked-files=no"],
            capture_output=True,
            text=True,
            check=False,
        )
    except OSError:
        return None
    sha = head.stdout.strip()
    if not sha:
        return None
    if status.returncode != 0 or status.stdout.strip():
        return f"{sha}{DIRTY_SUFFIX}"
    return sha


def compute_values_digest(
    app_config_dir: Path,
    values_files: list[str],
    set_values: dict[str, Any] | None,
    cluster_global_values: dict[str, Any] | None,
) -> str:
    """Digest every values input Helm received, in order.

    A values file that does not exist (deploy skips it with a warning) is
    recorded as missing so that creating it later changes the digest.
    """
    files: list[list[str]] = []
    for values_file in values_files:
        values_path = app_config_dir / values_file
        if values_path.is_file():
            content_hash = hashlib.sha256(values_path.read_bytes()).hexdigest()
        else:
            content_hash = "missing"
        files.append([values_file, content_hash])
    payload = {
        "files": files,
        "set_values": set_values or {},
        "cluster_global_values": cluster_global_values or {},
    }
    canonical = json.dumps(payload, sort_keys=True, default=str)
    return hashlib.sha256(canonical.encode()).hexdigest()


def read_chart_version(chart_path: Path, fallback: str | None) -> str | None:
    """Return the version in chart_path/Chart.yaml, else fallback."""
    chart_file = chart_path / "Chart.yaml"
    if chart_file.is_file():
        try:
            data = yaml.safe_load(chart_file.read_text()) or {}
        except (OSError, yaml.YAMLError):
            return fallback
        version = data.get("version")
        if version is not None:
            return str(version)
    return fallback


def parse_helm_revision(stdout: str) -> int | None:
    """Parse ``REVISION: N`` from helm install/upgrade output."""
    match = _REVISION_PATTERN.search(stdout or "")
    return int(match.group(1)) if match else None


class DeploymentRecorder:
    """Record one deploy run of an app group in the state DB.

    The deployment row is created on the first recorded app so that a run
    which deploys nothing leaves no empty rollback point.
    """

    def __init__(
        self,
        *,
        cluster: str,
        namespace: str,
        app_config_dir: Path,
        config_file_path: Path,
        config_data: dict[str, Any],
        sources_data: dict[str, Any] | None,
        warn: Callable[[str], None],
        command: str = "deploy",
        command_args: dict[str, Any] | None = None,
        db_factory: Callable[[], DeploymentDatabase] | None = None,
    ) -> None:
        self.cluster = cluster
        self.namespace = namespace
        self.app_config_dir = app_config_dir
        self.config_file_path = config_file_path
        self.config_data = config_data
        self.sources_data = sources_data
        self.command = command
        self.command_args = command_args
        self._warn = warn
        self._db_factory = db_factory
        self._db: DeploymentDatabase | None = None
        self.deployment_id: str | None = None
        self._deployment_row_id: int | None = None
        self.source_commit = resolve_source_commit(app_config_dir)

    def _ensure_deployment(self) -> tuple[DeploymentDatabase, int]:
        if self._db is None:
            self._db = (self._db_factory or DeploymentDatabase)()
        if self._deployment_row_id is not None:
            return self._db, self._deployment_row_id
        from sbkube import __version__

        timestamp = datetime.now(UTC).strftime("%Y%m%d%H%M%S")
        self.deployment_id = f"dep-{timestamp}-{str(uuid.uuid4())[:8]}"
        deployment = self._db.create_deployment(
            DeploymentCreate(
                deployment_id=self.deployment_id,
                cluster=self.cluster,
                namespace=self.namespace,
                app_config_dir=str(self.app_config_dir),
                config_file_path=str(self.config_file_path),
                command=self.command,
                command_args=self.command_args,
                config_snapshot=self.config_data,
                sources_snapshot=self.sources_data,
                source_commit=self.source_commit,
                sbkube_version=__version__,
                operator=os.environ.get("USER"),
            )
        )
        self._deployment_row_id = deployment.id
        return self._db, deployment.id

    def record_helm_app(
        self,
        *,
        app_name: str,
        app: Any,
        release_name: str,
        namespace: str,
        chart_path: Path,
        app_config_dir: Path,
        cluster_global_values: dict[str, Any] | None,
        helm_stdout: str,
    ) -> bool:
        """Record a successful Helm deploy of a HelmApp.

        Returns False after a visible warning when nothing was recorded.
        """
        try:
            revision = parse_helm_revision(helm_stdout)
            if revision is None:
                self._warn(
                    f"Rollback point not recorded for '{app_name}': helm output had "
                    "no REVISION line"
                )
                return False
            rollback_info = {
                "type": "helm",
                "release_name": release_name,
                "namespace": namespace,
                "revision": revision,
                "chart": app.chart,
                "chart_version": read_chart_version(chart_path, app.version),
                "values_digest": compute_values_digest(
                    app_config_dir, app.values, app.set_values, cluster_global_values
                ),
            }
            db, deployment_row_id = self._ensure_deployment()
            app_deployment = db.add_app_deployment(
                deployment_row_id,
                AppDeploymentCreate(
                    app_name=app_name,
                    app_type="helm",
                    namespace=namespace,
                    app_config=app.model_dump(mode="json"),
                ),
            )
            db.update_app_deployment_status(
                app_deployment.id,
                DeploymentStatus.SUCCESS,
                rollback_info=rollback_info,
            )
        except Exception as e:
            self._warn(
                f"Rollback point not recorded for '{app_name}' "
                f"(state DB write failed: {e}); the deploy itself succeeded"
            )
            return False
        return True

    def finish(self, *, failed: bool) -> None:
        """Set the final status of the recorded deployment, if any."""
        if self._db is None or self.deployment_id is None:
            return
        status = (
            DeploymentStatus.PARTIALLY_FAILED if failed else DeploymentStatus.SUCCESS
        )
        try:
            self._db.update_deployment_status(self.deployment_id, status)
        except Exception as e:
            self._warn(
                f"Deployment record {self.deployment_id} status not updated "
                f"(state DB write failed: {e})"
            )
