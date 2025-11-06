"""Cluster status collector.

This module provides functionality to collect comprehensive Kubernetes cluster
status information including nodes, namespaces, and Helm releases.
"""

import json
import subprocess
from pathlib import Path
from typing import Any

from rich.console import Console

# Constants
KUBECTL_TIMEOUT_SECONDS = 30
HELM_TIMEOUT_SECONDS = 30

console = Console()


class ClusterStatusCollector:
    """Collects Kubernetes cluster status information.

    Uses kubectl and helm CLI tools to gather cluster-wide information.
    """

    def __init__(self, kubeconfig: str | None = None, context: str | None = None) -> None:
        """Initialize cluster status collector.

        Args:
            kubeconfig: Path to kubeconfig file (optional, uses default if None)
            context: kubeconfig context name (optional, uses current-context if None)

        """
        self.kubeconfig = Path(kubeconfig).expanduser() if kubeconfig else None
        self.context = context
        self._kubectl_base_cmd = self._build_kubectl_cmd()
        self._helm_base_cmd = self._build_helm_cmd()

    def _build_kubectl_cmd(self) -> list[str]:
        """Build base kubectl command with kubeconfig and context."""
        cmd = ["kubectl"]
        if self.kubeconfig:
            cmd.extend(["--kubeconfig", str(self.kubeconfig)])
        if self.context:
            cmd.extend(["--context", self.context])
        return cmd

    def _build_helm_cmd(self) -> list[str]:
        """Build base helm command with kubeconfig and context."""
        cmd = ["helm"]
        if self.kubeconfig:
            cmd.extend(["--kubeconfig", str(self.kubeconfig)])
        if self.context:
            cmd.extend(["--kube-context", self.context])
        return cmd

    def _run_kubectl(
        self, args: list[str], timeout: int = KUBECTL_TIMEOUT_SECONDS
    ) -> subprocess.CompletedProcess:
        """Run kubectl command with error handling.

        Args:
            args: kubectl arguments
            timeout: command timeout in seconds

        Returns:
            CompletedProcess instance

        Raises:
            subprocess.CalledProcessError: if command fails
            subprocess.TimeoutExpired: if command times out

        """
        cmd = self._kubectl_base_cmd + args
        return subprocess.run(
            cmd,
            capture_output=True,
            text=True,
            timeout=timeout,
            check=True,
        )

    def _run_helm(
        self, args: list[str], timeout: int = HELM_TIMEOUT_SECONDS
    ) -> subprocess.CompletedProcess:
        """Run helm command with error handling.

        Args:
            args: helm arguments
            timeout: command timeout in seconds

        Returns:
            CompletedProcess instance

        Raises:
            subprocess.CalledProcessError: if command fails
            subprocess.TimeoutExpired: if command times out

        """
        cmd = self._helm_base_cmd + args
        return subprocess.run(
            cmd,
            capture_output=True,
            text=True,
            timeout=timeout,
            check=True,
        )

    def collect_all(self) -> dict[str, Any]:
        """Collect all cluster status information.

        Returns:
            Dictionary containing cluster_info, nodes, namespaces, and helm_releases

        """
        result: dict[str, Any] = {}

        # Collect cluster info (non-blocking on failure)
        try:
            result["cluster_info"] = self._collect_cluster_info()
        except Exception as e:
            console.print(
                f"[yellow]Warning: Failed to collect cluster info: {e}[/yellow]"
            )
            result["cluster_info"] = {"error": str(e)}

        # Collect nodes (non-blocking on failure)
        try:
            result["nodes"] = self._collect_nodes()
        except Exception as e:
            console.print(f"[yellow]Warning: Failed to collect nodes: {e}[/yellow]")
            result["nodes"] = []

        # Collect namespaces (non-blocking on failure)
        try:
            result["namespaces"] = self._collect_namespaces()
        except Exception as e:
            console.print(
                f"[yellow]Warning: Failed to collect namespaces: {e}[/yellow]"
            )
            result["namespaces"] = []

        # Collect Helm releases (non-blocking on failure)
        try:
            result["helm_releases"] = self._collect_helm_releases()
        except Exception as e:
            console.print(
                f"[yellow]Warning: Failed to collect Helm releases: {e}[/yellow]"
            )
            result["helm_releases"] = []

        return result

    def _collect_cluster_info(self) -> dict[str, Any]:
        """Collect cluster information (API server, version).

        Returns:
            Dictionary with api_server and version keys

        """
        info: dict[str, Any] = {}

        # Get cluster-info
        try:
            result = self._run_kubectl(["cluster-info"])
            # Parse API server URL from output
            lines = result.stdout.strip().split("\n")
            for line in lines:
                if "Kubernetes control plane" in line or "Kubernetes master" in line:
                    # Extract URL (format: "Kubernetes control plane is running at https://...")
                    parts = line.split(" is running at ")
                    if len(parts) == 2:
                        info["api_server"] = parts[1].strip()
                        break
        except Exception as e:
            console.print(
                f"[dim]Debug: cluster-info failed: {e}[/dim]", highlight=False
            )

        # Get version
        try:
            result = self._run_kubectl(["version", "-o", "json"])
            version_data = json.loads(result.stdout)
            if "serverVersion" in version_data:
                server_version = version_data["serverVersion"]
                info["version"] = server_version.get("gitVersion", "unknown")
        except Exception as e:
            console.print(f"[dim]Debug: version failed: {e}[/dim]", highlight=False)

        return info

    def _collect_nodes(self) -> list[dict[str, Any]]:
        """Collect node status information.

        Returns:
            List of node information dictionaries

        """
        result = self._run_kubectl(["get", "nodes", "-o", "json"])
        data = json.loads(result.stdout)

        nodes = []
        for item in data.get("items", []):
            node_name = item["metadata"]["name"]
            status = "Unknown"
            roles = []

            # Parse node status
            for condition in item.get("status", {}).get("conditions", []):
                if condition.get("type") == "Ready":
                    status = (
                        "Ready" if condition.get("status") == "True" else "NotReady"
                    )
                    break

            # Parse node roles from labels
            labels = item["metadata"].get("labels", {})
            for key in labels:
                if key.startswith("node-role.kubernetes.io/"):
                    role = key.replace("node-role.kubernetes.io/", "")
                    roles.append(role)

            # Get node version
            version = (
                item.get("status", {})
                .get("nodeInfo", {})
                .get("kubeletVersion", "unknown")
            )

            nodes.append(
                {
                    "name": node_name,
                    "status": status,
                    "roles": roles if roles else ["<none>"],
                    "version": version,
                }
            )

        return nodes

    def _collect_namespaces(self) -> list[str]:
        """Collect namespace list.

        Returns:
            List of namespace names

        """
        result = self._run_kubectl(["get", "namespaces", "-o", "json"])
        data = json.loads(result.stdout)

        namespaces = []
        for item in data.get("items", []):
            namespace_name = item["metadata"]["name"]
            namespaces.append(namespace_name)

        return sorted(namespaces)

    def _collect_helm_releases(self) -> list[dict[str, Any]]:
        """Collect Helm release information from all namespaces.

        Returns:
            List of Helm release information dictionaries

        """
        result = self._run_helm(["list", "--all-namespaces", "-o", "json"])
        data = json.loads(result.stdout)

        releases = []
        for item in data:
            releases.append(
                {
                    "name": item.get("name", "unknown"),
                    "namespace": item.get("namespace", "unknown"),
                    "status": item.get("status", "unknown"),
                    "chart": item.get("chart", "unknown"),
                    "app_version": item.get("app_version", "unknown"),
                    "revision": item.get("revision", 0),
                }
            )

        return releases
