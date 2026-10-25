"""Node-only k3s administration: no administrator kubeconfig leaves the node.

SSH uses the operator's existing routing and known_hosts, without requesting a
TTY or forwarding stdin. Every request verifies both node identity and the public
server CA against the local readonly kubeconfig before it can mint a credential.
"""

import base64
import binascii
import shlex
import subprocess
from dataclasses import dataclass
from pathlib import Path
from typing import Any
from urllib.parse import urlsplit

from sbkube.models.access_model import AccessAdminSettings
from sbkube.utils.access_issue import TokenIssueError, token_from_output

SSH_TIMEOUT_SECONDS = 45
_K3S = ["sudo", "-n", "k3s", "kubectl", "--kubeconfig", "/etc/rancher/k3s/k3s.yaml"]


def cluster_ca(cluster: dict[str, Any], source: Path) -> bytes:
    """Read only the public CA, following client-go's relative-path semantics."""
    server = cluster.get("server")
    try:
        endpoint = urlsplit(server) if isinstance(server, str) else None
    except ValueError as e:
        raise TokenIssueError("readonly kubeconfig must use an HTTPS server URL") from e
    if endpoint is None or endpoint.scheme != "https" or not endpoint.hostname:
        raise TokenIssueError("readonly kubeconfig must use an HTTPS server URL")
    if cluster.get("insecure-skip-tls-verify"):
        raise TokenIssueError("node access requires server CA verification")
    encoded = cluster.get("certificate-authority-data")
    if isinstance(encoded, str) and encoded:
        try:
            ca = base64.b64decode(encoded, validate=True)
        except (ValueError, binascii.Error) as e:
            raise TokenIssueError("readonly kubeconfig contains invalid CA data") from e
    else:
        ref = cluster.get("certificate-authority")
        if not isinstance(ref, str) or not ref:
            raise TokenIssueError("readonly kubeconfig must provide a server CA")
        path = Path(ref)
        if not path.is_absolute():
            path = source.parent / path
        try:
            ca = path.read_bytes()
        except OSError as e:
            raise TokenIssueError("cannot read readonly kubeconfig's server CA") from e
    if not ca.strip():
        raise TokenIssueError("readonly kubeconfig contains an empty server CA")
    return ca.strip()


@dataclass(frozen=True)
class NodeAdmin:
    """Explicit human-selected SSH destination; no shell command configuration."""

    settings: AccessAdminSettings

    def _run(self, args: list[str], input_text: str | None = None) -> str:
        if not self.settings.ssh_host or not self.settings.expected_hostname:
            raise TokenIssueError("node admin requires ssh_host and expected_hostname")
        command = [
            "ssh",
            "-T",
            "-o",
            "BatchMode=yes",
            "-o",
            "StrictHostKeyChecking=yes",
            "-o",
            "ConnectTimeout=10",
            "--",
            self.settings.ssh_host,
            shlex.join(args),
        ]
        try:
            proc = subprocess.run(  # noqa: S603
                command,
                **(
                    {"stdin": subprocess.DEVNULL}
                    if input_text is None
                    else {"input": input_text}
                ),
                capture_output=True,
                text=True,
                check=False,
                timeout=SSH_TIMEOUT_SECONDS,
            )
        except FileNotFoundError as e:
            raise TokenIssueError("ssh not found in PATH") from e
        except subprocess.TimeoutExpired as e:
            raise TokenIssueError("node admin SSH request timed out") from e
        if proc.returncode:
            # Remote tools may echo credentials on either stream. Never include them.
            raise TokenIssueError(
                f"node admin SSH request failed (exit {proc.returncode}); "
                "check SSH routing, known_hosts and sudo -n k3s access"
            )
        return proc.stdout

    def run_kubectl(self, args: list[str], input_text: str | None = None) -> str:
        """Run fixed command arguments, with optional public manifests over stdin."""
        return self._run([*_K3S, *args], input_text)

    def verify(self, expected_ca: bytes) -> None:
        """Verify the node and its cluster before any TokenRequest."""
        hostname = self._run(["hostname"]).strip()
        if hostname != self.settings.expected_hostname:
            raise TokenIssueError("node hostname does not match expected_hostname")
        encoded = self._run(
            [
                *_K3S,
                "config",
                "view",
                "--raw",
                "--minify",
                "-o",
                "jsonpath={.clusters[0].cluster.certificate-authority-data}",
            ]
        ).strip()
        try:
            ca = base64.b64decode(encoded, validate=True).strip()
        except (ValueError, binascii.Error) as e:
            raise TokenIssueError("node returned invalid server CA data") from e
        if not ca or ca != expected_ca:
            raise TokenIssueError("node server CA does not match readonly kubeconfig")

    def mint_token(self, namespace: str, service_account: str, duration: str) -> str:
        return token_from_output(
            self._run(
                [
                    *_K3S,
                    "-n",
                    namespace,
                    "create",
                    "token",
                    service_account,
                    "--duration",
                    duration,
                ]
            )
        )
