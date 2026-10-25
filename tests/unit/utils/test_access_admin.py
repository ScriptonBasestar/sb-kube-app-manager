"""Node identity, transport and credential-output regressions (no SSH connection)."""

import base64
import shlex
import subprocess
from pathlib import Path
from unittest.mock import patch

import pytest

from sbkube.models.access_model import AccessAdminSettings
from sbkube.utils.access_admin import NodeAdmin, cluster_ca
from sbkube.utils.access_issue import TokenIssueError

RUN = "sbkube.utils.access_admin.subprocess.run"
CA = b"public-server-ca"


def node() -> NodeAdmin:
    return NodeAdmin(
        AccessAdminSettings(ssh_host="operator@node-lan", expected_hostname="node1")
    )


def result(stdout: str = "", rc: int = 0) -> subprocess.CompletedProcess:
    return subprocess.CompletedProcess([], rc, stdout, "SECRET-STDERR")


def test_node_identity_and_ca_before_token() -> None:
    outputs = [
        result("node1\n"),
        result(base64.b64encode(CA).decode()),
        result("TOKEN\n"),
    ]
    with patch(RUN, side_effect=outputs) as run:
        admin = node()
        admin.verify(CA)
        assert admin.mint_token("agent-access", "deployer", "1h") == "TOKEN"
    commands = [call.args[0] for call in run.call_args_list]
    assert shlex.split(commands[0][-1]) == ["hostname"]
    assert (
        shlex.split(commands[1][-1])[-1]
        == "jsonpath={.clusters[0].cluster.certificate-authority-data}"
    )
    assert shlex.split(commands[2][-1]) == [
        "sudo",
        "-n",
        "k3s",
        "kubectl",
        "--kubeconfig",
        "/etc/rancher/k3s/k3s.yaml",
        "-n",
        "agent-access",
        "create",
        "token",
        "deployer",
        "--duration",
        "1h",
    ]
    for call in run.call_args_list:
        assert call.kwargs["stdin"] == subprocess.DEVNULL
        assert call.kwargs.get("shell") is None
        assert call.kwargs["timeout"] == 45
        assert "StrictHostKeyChecking=yes" in call.args[0]
        assert "BatchMode=yes" in call.args[0]
        assert "TOKEN" not in repr(call.args)


@pytest.mark.parametrize("hostname", ["wrong-node", "node1\nother", ""])
def test_wrong_hostname_stops_before_kubectl(hostname: str) -> None:
    with patch(RUN, return_value=result(hostname)) as run:
        with pytest.raises(TokenIssueError, match="hostname"):
            node().verify(CA)
    assert run.call_count == 1


@pytest.mark.parametrize(
    "encoded", ["", "not-base64!", base64.b64encode(b"wrong-ca").decode()]
)
def test_wrong_ca_stops_before_token(encoded: str) -> None:
    with patch(RUN, side_effect=[result("node1"), result(encoded)]) as run:
        with pytest.raises(TokenIssueError, match="CA"):
            node().verify(CA)
    assert run.call_count == 2


def test_remote_failure_does_not_echo_streams() -> None:
    with patch(RUN, return_value=result("SECRET-STDOUT", rc=1)):
        with pytest.raises(TokenIssueError, match="exit 1") as raised:
            node().verify(CA)
    assert "SECRET" not in str(raised.value)


@pytest.mark.parametrize(
    "error",
    [FileNotFoundError(), subprocess.TimeoutExpired(["SECRET"], 45, output="SECRET")],
)
def test_transport_failure_does_not_echo_exception(error: Exception) -> None:
    with patch(RUN, side_effect=error):
        with pytest.raises(TokenIssueError) as raised:
            node().verify(CA)
    assert "SECRET" not in str(raised.value)


@pytest.mark.parametrize("token", ["", "one two", "one\ntwo"])
def test_bad_token_output_not_echoed(token: str) -> None:
    with patch(RUN, return_value=result(token)):
        with pytest.raises(TokenIssueError):
            node().mint_token("agent-access", "deployer", "1h")


def test_cluster_ca_file_relative_without_tilde_expansion(tmp_path: Path) -> None:
    folder = tmp_path / "~"
    folder.mkdir()
    (folder / "ca.crt").write_bytes(CA)
    assert (
        cluster_ca(
            {"server": "https://cluster:6443", "certificate-authority": "~/ca.crt"},
            tmp_path / "config",
        )
        == CA
    )


@pytest.mark.parametrize("server", ["http://cluster", "", "https://", "https://["])
def test_insecure_server_refused_before_ssh(server: str, tmp_path: Path) -> None:
    with pytest.raises(TokenIssueError, match="HTTPS"):
        cluster_ca(
            {"server": server, "certificate-authority-data": "Q0E="},
            tmp_path / "config",
        )


@pytest.mark.parametrize(
    "cluster",
    [
        {},
        {"insecure-skip-tls-verify": True},
        {"certificate-authority-data": "!"},
        {"certificate-authority-data": "IA=="},
    ],
)
def test_missing_or_untrusted_ca_refused(cluster: dict, tmp_path: Path) -> None:
    cluster = {"server": "https://cluster:6443", **cluster}
    with pytest.raises(TokenIssueError):
        cluster_ca(cluster, tmp_path / "config")
