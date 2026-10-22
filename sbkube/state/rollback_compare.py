"""Compare a rollback target with the currently recorded deployment.

`sbkube rollback` must not silently restore different code. For every app the
rollback would touch, the recorded current state is compared with the
recorded state Helm would restore on four fields: chart, chart version,
values digest and source commit. Any difference, and any state that cannot be
compared (no record, no source commit, dirty tree, revision mismatch, current
record not the live release state), makes the rollback require the
difference digest. Typing it proves the summary was read; it is not an
approval, which is the deploy gate's job.
"""

import hashlib
import json
from dataclasses import dataclass, field
from typing import Any

from sbkube.exceptions import RollbackError
from sbkube.state.deploy_recorder import DIRTY_SUFFIX

COMPARED_FIELDS = ("chart", "chart_version", "values_digest", "source_commit")
DIGEST_LENGTH = 12


class RollbackConfirmationRequired(RollbackError):
    """Raised when a rollback changes code and the digest was not confirmed."""


@dataclass(frozen=True)
class AppSnapshot:
    """Recorded state of one Helm app in one deployment."""

    deployment_id: str
    revision: int | None
    chart: str | None
    chart_version: str | None
    values_digest: str | None
    source_commit: str | None

    @classmethod
    def from_record(
        cls,
        deployment_id: str,
        rollback_info: dict[str, Any] | None,
        source_commit: str | None,
    ) -> "AppSnapshot":
        info = rollback_info or {}
        return cls(
            deployment_id=deployment_id,
            revision=info.get("revision"),
            chart=info.get("chart"),
            chart_version=info.get("chart_version"),
            values_digest=info.get("values_digest"),
            source_commit=source_commit,
        )


@dataclass
class AppComparison:
    """Comparison result for one app."""

    app_name: str
    current: AppSnapshot | None
    target: AppSnapshot | None
    differences: list[tuple[str, Any, Any]] = field(default_factory=list)
    uncomparable_reason: str | None = None

    @property
    def changed(self) -> bool:
        return bool(self.differences) or self.uncomparable_reason is not None


@dataclass
class RollbackComparison:
    """Comparison result for the whole rollback request."""

    current_deployment_id: str
    apps: list[AppComparison]

    @property
    def requires_confirmation(self) -> bool:
        return any(app.changed for app in self.apps)

    @property
    def digest(self) -> str | None:
        """Short sha256 over every difference, None when nothing differs."""
        if not self.requires_confirmation:
            return None
        entries: list[list[Any]] = []
        for app in sorted(self.apps, key=lambda a: a.app_name):
            if app.uncomparable_reason is not None:
                entries.append([app.app_name, "uncomparable", app.uncomparable_reason])
            for name, current, target in app.differences:
                entries.append([app.app_name, name, current, target])
        payload = {"current": self.current_deployment_id, "differences": entries}
        canonical = json.dumps(payload, sort_keys=True, default=str)
        return hashlib.sha256(canonical.encode()).hexdigest()[:DIGEST_LENGTH]

    def summary_lines(self) -> list[str]:
        """Human-readable lines describing what differs."""
        lines: list[str] = []
        for app in self.apps:
            if not app.changed:
                lines.append(f"  = {app.app_name}: no code change")
                continue
            target = app.target.deployment_id if app.target else "unknown"
            lines.append(
                f"  ! {app.app_name}: {self.current_deployment_id} -> {target}"
            )
            if app.uncomparable_reason is not None:
                lines.append(f"      cannot compare: {app.uncomparable_reason}")
            for name, current, target_value in app.differences:
                lines.append(f"      {name}: {current} -> {target_value}")
        return lines


def compare_snapshots(
    app_name: str,
    current: AppSnapshot | None,
    target: AppSnapshot | None,
    restore_revision: int | None,
) -> AppComparison:
    """Compare two recorded app states.

    restore_revision is the Helm revision the rollback will actually restore;
    a target record of another revision does not describe that state.
    """
    comparison = AppComparison(app_name=app_name, current=current, target=target)
    if current is None:
        comparison.uncomparable_reason = "no recorded state for the current deployment"
        return comparison
    if target is None:
        comparison.uncomparable_reason = "no recorded state for the rollback target"
        return comparison
    if restore_revision is not None and target.revision != restore_revision:
        comparison.uncomparable_reason = (
            f"recorded target revision {target.revision} is not the Helm revision "
            f"{restore_revision} the rollback restores"
        )
        return comparison

    for name in COMPARED_FIELDS:
        current_value = getattr(current, name)
        target_value = getattr(target, name)
        if current_value != target_value:
            comparison.differences.append((name, current_value, target_value))

    for label, snapshot in (("current", current), ("target", target)):
        commit = snapshot.source_commit
        if commit is None:
            comparison.uncomparable_reason = (
                f"{label} deployment has no recorded source commit"
            )
            break
        if commit.endswith(DIRTY_SUFFIX):
            comparison.uncomparable_reason = (
                f"{label} deployment was made from uncommitted changes ({commit})"
            )
            break
    if comparison.uncomparable_reason is None:
        for name in ("chart_version", "values_digest"):
            if getattr(current, name) is None or getattr(target, name) is None:
                comparison.uncomparable_reason = f"{name} was not recorded"
                break
    return comparison
