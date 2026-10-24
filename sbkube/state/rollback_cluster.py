"""Cluster pinning for rollback.

Rollback must reach the cluster the deployment was made on. Deploy records the
kubeconfig and context it resolved (sources.yaml or --kubeconfig/--context) in
the deployment's sources snapshot; rollback reuses that record instead of the
shell's current kube context or KUBECONFIG.
"""

from pathlib import Path

import yaml

from sbkube.exceptions import RollbackError
from sbkube.models.deployment_state import DeploymentDetail


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
    recorded_kubeconfig = snapshot.get("kubeconfig")
    recorded_context = snapshot.get("kubeconfig_context")
    recorded = (
        (_existing(recorded_kubeconfig), recorded_context)
        if recorded_kubeconfig and recorded_context
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


def _existing(kubeconfig: str) -> str:
    path = Path(kubeconfig).expanduser()
    if not path.exists():
        msg = f"Kubeconfig file not found: {path}"
        raise RollbackError(msg)
    return str(path)


def _context_server(kubeconfig: str, context: str) -> str:
    """API server URL the context points at, read from the kubeconfig file."""
    try:
        data = yaml.safe_load(Path(kubeconfig).read_text()) or {}
    except (OSError, yaml.YAMLError) as e:
        msg = f"Cannot read kubeconfig {kubeconfig}: {e}"
        raise RollbackError(msg) from e

    clusters = {
        entry.get("context", {}).get("cluster")
        for entry in data.get("contexts") or []
        if entry.get("name") == context
    }
    servers = {
        entry.get("cluster", {}).get("server")
        for entry in data.get("clusters") or []
        if entry.get("name") in clusters
    }
    if not clusters:
        msg = f"Context {context} not found in kubeconfig {kubeconfig}"
        raise RollbackError(msg)
    if len(servers) != 1 or None in servers:
        msg = (
            f"Context {context} in kubeconfig {kubeconfig} has no single cluster server"
        )
        raise RollbackError(msg)
    return servers.pop()
