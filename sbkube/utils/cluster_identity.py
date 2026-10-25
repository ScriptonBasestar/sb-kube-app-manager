"""Immutable, public cluster identity derived from a kubeconfig context."""

from hashlib import sha256
from pathlib import Path

from sbkube.utils.access_admin import cluster_ca
from sbkube.utils.access_kubeconfig import context_cluster, read_kubeconfig


def cluster_identity(kubeconfig: str | Path, context: str) -> dict[str, str]:
    """Return the public identity of one kubeconfig context.

    The identity deliberately excludes users and credentials.  ``cluster_ca``
    verifies that the selected endpoint is HTTPS and is CA-authenticated before
    its public CA is fingerprinted.
    """
    source = Path(kubeconfig).expanduser()
    data = read_kubeconfig(source)
    _, cluster = context_cluster(data, context, source)
    ca = cluster_ca(cluster, source)
    return {
        "context": context,
        "server": cluster["server"],
        "ca_sha256": sha256(ca).hexdigest(),
    }
