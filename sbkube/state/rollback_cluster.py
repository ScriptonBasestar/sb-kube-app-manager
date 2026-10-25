"""Cluster pinning for rollback.

Rollback must reach the cluster the deployment was made on. Deploy records the
kubeconfig and context it resolved (sources.yaml or --kubeconfig/--context) in
the deployment's sources snapshot; rollback reuses that record instead of the
shell's current kube context or KUBECONFIG.
"""

from pathlib import Path

from sbkube.exceptions import RollbackError
from sbkube.models.deployment_state import DeploymentDetail
from sbkube.utils.access_kubeconfig import (
    KubeconfigError,
    context_cluster,
    read_kubeconfig,
)
from sbkube.utils.cluster_identity import cluster_identity


def resolve_rollback_cluster(
    deployment: DeploymentDetail,
    cli_kubeconfig: str | None,
    cli_context: str | None,
) -> tuple[str, str]:
    """Return the (kubeconfig, context) to roll back the deployment on.

    --kubeconfig/--context replace the recorded values only when they name the
    same context and the context points at the same API server; they are
    required when nothing was recorded.

    Raises:
        RollbackError: If no cluster can be resolved, the override names another
            cluster, or a kubeconfig or its context cannot be read

    """
    snapshot = deployment.sources_snapshot or {}
    if not isinstance(snapshot, dict):
        raise RollbackError("Deployment sources snapshot is malformed")
    recorded_kubeconfig = snapshot.get("kubeconfig")
    recorded_context = snapshot.get("kubeconfig_context")
    saved_identity = _saved_identity(snapshot)

    if saved_identity is not None:
        chosen = _choose_pinned_cluster(
            deployment,
            cli_kubeconfig,
            cli_context,
            recorded_kubeconfig,
            recorded_context,
        )
        if _identity(*chosen) != saved_identity:
            raise RollbackError(
                f"Selected cluster is not the immutable identity recorded for deployment "
                f"{deployment.deployment_id}"
            )
        return chosen

    recorded = (
        (_existing(recorded_kubeconfig), recorded_context)
        if isinstance(recorded_kubeconfig, str)
        and recorded_kubeconfig
        and isinstance(recorded_context, str)
        and recorded_context
        else None
    )

    if cli_kubeconfig or cli_context:
        if not (cli_kubeconfig and cli_context):
            msg = "Both --kubeconfig and --context must be specified together"
            raise RollbackError(msg)
        chosen = (_existing(cli_kubeconfig), cli_context)
        if recorded and (
            cli_context != recorded_context
            or _context_server(*chosen) != _context_server(*recorded)
        ):
            msg = (
                f"--kubeconfig {cli_kubeconfig} --context {cli_context} is not the "
                f"cluster recorded for deployment {deployment.deployment_id}: "
                f"context {recorded_context} in {recorded_kubeconfig} "
                f"(cluster {deployment.cluster})"
            )
            raise RollbackError(msg)
    elif recorded:
        chosen = recorded
    else:
        msg = (
            f"Deployment {deployment.deployment_id} (cluster {deployment.cluster}) "
            "records no kubeconfig and context; pass them explicitly: "
            "sbkube --kubeconfig <path> --context <name> rollback ..."
        )
        raise RollbackError(msg)

    _context_server(*chosen)
    return chosen


def _choose_pinned_cluster(
    deployment: DeploymentDetail,
    cli_kubeconfig: str | None,
    cli_context: str | None,
    recorded_kubeconfig: object,
    recorded_context: object,
) -> tuple[str, str]:
    """Choose a cluster for a deployment whose immutable identity is pinned."""
    if cli_kubeconfig or cli_context:
        if not (cli_kubeconfig and cli_context):
            raise RollbackError(
                "Both --kubeconfig and --context must be specified together"
            )
        return _existing(cli_kubeconfig), cli_context
    if (
        isinstance(recorded_kubeconfig, str)
        and recorded_kubeconfig
        and isinstance(recorded_context, str)
        and recorded_context
    ):
        return _existing(recorded_kubeconfig), recorded_context
    raise RollbackError(
        f"Deployment {deployment.deployment_id} has a cluster identity pin but no "
        "usable kubeconfig and context; pass them explicitly"
    )


def _saved_identity(snapshot: dict[object, object]) -> dict[str, str] | None:
    """Validate the optional deployment-time immutable identity pin."""
    if "cluster_identity" not in snapshot:
        return None
    identity = snapshot["cluster_identity"]
    required = {"context", "server", "ca_sha256"}
    if not isinstance(identity, dict) or not required <= identity.keys():
        raise RollbackError("Deployment cluster identity pin is malformed")
    values = {key: identity[key] for key in required}
    if not all(isinstance(value, str) and value for value in values.values()):
        raise RollbackError("Deployment cluster identity pin is malformed")
    fingerprint = values["ca_sha256"]
    if len(fingerprint) != 64 or any(
        char not in "0123456789abcdef" for char in fingerprint
    ):
        raise RollbackError("Deployment cluster identity pin is malformed")
    return values


def _existing(kubeconfig: str) -> str:
    path = Path(kubeconfig).expanduser()
    if not path.exists():
        msg = f"Kubeconfig file not found: {path}"
        raise RollbackError(msg)
    return str(path)


def _context_server(kubeconfig: str, context: str) -> str:
    """API server URL the context points at, read from the kubeconfig file."""
    try:
        data = read_kubeconfig(Path(kubeconfig))
        _, cluster = context_cluster(data, context, Path(kubeconfig))
        return cluster["server"]
    except KubeconfigError as error:
        if "not found exactly once" in str(error):
            raise RollbackError(
                f"Context {context} not found in kubeconfig {kubeconfig}"
            ) from error
        raise RollbackError(
            f"Cannot inspect kubeconfig {kubeconfig} for context {context}"
        ) from error


def _identity(kubeconfig: str, context: str) -> dict[str, str]:
    """Inspect an identity without exposing kubeconfig parser details."""
    try:
        return cluster_identity(kubeconfig, context)
    except Exception as error:
        raise RollbackError(
            f"Cannot inspect kubeconfig {kubeconfig} for immutable cluster identity"
        ) from error
