"""Public cluster identity tests without Kubernetes access."""

import base64
from hashlib import sha256
from pathlib import Path

import pytest

from sbkube.utils.access_issue import TokenIssueError
from sbkube.utils.cluster_identity import cluster_identity


def _kubeconfig(
    path: Path,
    *,
    context: str = "home",
    server: str = "https://home:6443",
    ca: bytes = b"public-ca",
) -> Path:
    path.write_text(
        "contexts:\n"
        f"- name: {context}\n  context: {{cluster: home}}\n"
        "clusters:\n"
        f"- name: home\n  cluster: {{server: {server}, certificate-authority-data: {base64.b64encode(ca).decode()}}}\n"
        "users:\n"
        "- name: private-user\n  user: {token: should-not-be-read}\n"
    )
    return path


def test_cluster_identity_contains_only_public_context_server_and_ca_hash(
    tmp_path: Path,
) -> None:
    path = _kubeconfig(tmp_path / "kubeconfig.yaml")

    assert cluster_identity(path, "home") == {
        "context": "home",
        "server": "https://home:6443",
        "ca_sha256": sha256(b"public-ca").hexdigest(),
    }


@pytest.mark.parametrize("server", ["http://home:6443", "https://"])
def test_cluster_identity_refuses_non_https_server(tmp_path: Path, server: str) -> None:
    with pytest.raises(TokenIssueError, match="HTTPS"):
        cluster_identity(
            _kubeconfig(tmp_path / "kubeconfig.yaml", server=server), "home"
        )
