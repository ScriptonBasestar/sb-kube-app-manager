"""Cluster pinning for rollback.

Rollback must reach the cluster the deployment was made on. Deploy resolves the
kubeconfig and context from sources.yaml (or --kubeconfig/--context) and records
them in the deployment's sources snapshot; rollback reuses that record instead
of the shell's current kube context or KUBECONFIG.
"""

from pathlib import Path

from sbkube.exceptions import RollbackError
from sbkube.models.deployment_state import DeploymentDetail


def resolve_rollback_cluster(
    deployment: DeploymentDetail,
    cli_kubeconfig: str | None,
    cli_context: str | None,
) -> tuple[str, str]:
    """Return the (kubeconfig, context) to roll back the deployment on.

    --kubeconfig/--context replace the recorded values only when the context
    matches the recorded one; they are required when nothing was recorded.

    Raises:
        RollbackError: If no cluster can be resolved, the override names another
            context, or the kubeconfig file does not exist

    """
    snapshot = deployment.sources_snapshot or {}
    recorded_kubeconfig = snapshot.get("kubeconfig")
    recorded_context = snapshot.get("kubeconfig_context")

    if cli_kubeconfig or cli_context:
        if not (cli_kubeconfig and cli_context):
            msg = "Both --kubeconfig and --context must be specified together"
            raise RollbackError(msg)
        if recorded_context and cli_context != recorded_context:
            msg = (
                f"--context {cli_context} differs from context {recorded_context} "
                f"recorded for deployment {deployment.deployment_id} "
                f"(cluster {deployment.cluster})"
            )
            raise RollbackError(msg)
        kubeconfig, context = cli_kubeconfig, cli_context
    elif recorded_kubeconfig and recorded_context:
        kubeconfig, context = recorded_kubeconfig, recorded_context
    else:
        msg = (
            f"Deployment {deployment.deployment_id} (cluster {deployment.cluster}) "
            "records no kubeconfig and context; pass them explicitly: "
            "sbkube --kubeconfig <path> --context <name> rollback ..."
        )
        raise RollbackError(msg)

    kubeconfig = str(Path(kubeconfig).expanduser())
    if not Path(kubeconfig).exists():
        msg = f"Kubeconfig file not found: {kubeconfig}"
        raise RollbackError(msg)
    return kubeconfig, context
