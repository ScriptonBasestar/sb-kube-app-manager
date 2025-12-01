import json
import subprocess
from collections.abc import Iterable

from sbkube.exceptions import (
    CliToolExecutionError,
    CliToolNotFoundError,
    KubernetesConnectionError,
)

_CONNECTION_ERROR_KEYWORDS: tuple[str, ...] = (
    "kubernetes cluster unreachable",
    "connection refused",
    "no such host",
    "i/o timeout",
    "context deadline exceeded",
    "tls: handshake timeout",
    "unable to connect",
)


def _matches_any_keyword(message: str, keywords: Iterable[str]) -> bool:
    lowered = message.lower()
    return any(keyword in lowered for keyword in keywords)


def get_installed_charts(
    namespace: str, context: str | None = None, kubeconfig: str | None = None
) -> dict:
    cmd = ["helm", "list", "-o", "json", "-n", namespace]
    if kubeconfig:
        cmd.extend(["--kubeconfig", kubeconfig])
    if context:
        cmd.extend(["--kube-context", context])
    try:
        result = subprocess.run(cmd, check=True, capture_output=True, text=True)
    except FileNotFoundError as exc:
        msg = "helm"
        raise CliToolNotFoundError(msg, "https://helm.sh/docs/intro/install/") from exc
    except subprocess.CalledProcessError as exc:
        error_output = (exc.stderr or exc.stdout or "").strip()
        if error_output and _matches_any_keyword(
            error_output, _CONNECTION_ERROR_KEYWORDS
        ):
            raise KubernetesConnectionError(reason=error_output) from exc
        msg = "helm"
        raise CliToolExecutionError(
            msg, cmd, exc.returncode, exc.stdout, exc.stderr
        ) from exc
    except OSError as exc:
        msg = "helm"
        raise CliToolExecutionError(msg, cmd, -1, None, str(exc)) from exc

    return {item["name"]: item for item in json.loads(result.stdout)}


def get_all_helm_releases(
    context: str | None = None, kubeconfig: str | None = None
) -> list[dict]:
    """Get all Helm releases across all namespaces.

    Args:
        context: Kubernetes context to use
        kubeconfig: Path to kubeconfig file

    Returns:
        List of Helm release dictionaries with keys:
        - name: Release name
        - namespace: Namespace
        - chart: Chart name with version (e.g., "nginx-1.0.0")
        - app_version: Application version
        - status: Release status
        - revision: Release revision number

    Raises:
        CliToolNotFoundError: If helm is not installed
        CliToolExecutionError: If helm command fails
        KubernetesConnectionError: If cluster is unreachable
    """
    cmd = ["helm", "list", "--all-namespaces", "-o", "json"]
    if kubeconfig:
        cmd.extend(["--kubeconfig", kubeconfig])
    if context:
        cmd.extend(["--kube-context", context])

    try:
        result = subprocess.run(
            cmd, check=True, capture_output=True, text=True, timeout=30
        )
    except FileNotFoundError as exc:
        msg = "helm"
        raise CliToolNotFoundError(msg, "https://helm.sh/docs/intro/install/") from exc
    except subprocess.CalledProcessError as exc:
        error_output = (exc.stderr or exc.stdout or "").strip()
        if error_output and _matches_any_keyword(
            error_output, _CONNECTION_ERROR_KEYWORDS
        ):
            raise KubernetesConnectionError(reason=error_output) from exc
        msg = "helm"
        raise CliToolExecutionError(
            msg, cmd, exc.returncode, exc.stdout, exc.stderr
        ) from exc
    except OSError as exc:
        msg = "helm"
        raise CliToolExecutionError(msg, cmd, -1, None, str(exc)) from exc

    return json.loads(result.stdout)


def search_helm_chart(
    repo_name: str,
    chart_name: str,
    version: str | None = None,
    all_versions: bool = False,
) -> list[dict]:
    """Search for a Helm chart in repositories.

    Args:
        repo_name: Repository name (e.g., "grafana")
        chart_name: Chart name (e.g., "grafana")
        version: Specific version to search for (optional)
        all_versions: If True, return all available versions

    Returns:
        List of chart dictionaries with keys:
        - name: Full chart name (e.g., "grafana/grafana")
        - version: Chart version
        - app_version: Application version
        - description: Chart description

    Raises:
        CliToolNotFoundError: If helm is not installed
        CliToolExecutionError: If helm command fails
    """
    cmd = ["helm", "search", "repo", f"{repo_name}/{chart_name}", "-o", "json"]

    if all_versions:
        cmd.append("--versions")
    elif version:
        cmd.extend(["--version", version])

    try:
        result = subprocess.run(
            cmd, check=True, capture_output=True, text=True, timeout=15
        )
    except FileNotFoundError as exc:
        msg = "helm"
        raise CliToolNotFoundError(msg, "https://helm.sh/docs/intro/install/") from exc
    except subprocess.CalledProcessError as exc:
        msg = "helm"
        raise CliToolExecutionError(
            msg, cmd, exc.returncode, exc.stdout, exc.stderr
        ) from exc
    except OSError as exc:
        msg = "helm"
        raise CliToolExecutionError(msg, cmd, -1, None, str(exc)) from exc

    charts = json.loads(result.stdout)
    return charts if charts else []


def get_latest_chart_version(repo_name: str, chart_name: str) -> str | None:
    """Get the latest version of a Helm chart.

    Args:
        repo_name: Repository name (e.g., "grafana")
        chart_name: Chart name (e.g., "grafana")

    Returns:
        Latest version string, or None if chart not found
    """
    charts = search_helm_chart(repo_name, chart_name)
    if not charts:
        return None

    # First result is the latest version when not using --versions
    return charts[0].get("version")


def get_all_chart_versions(repo_name: str, chart_name: str) -> list[str]:
    """Get all available versions of a Helm chart.

    Args:
        repo_name: Repository name (e.g., "grafana")
        chart_name: Chart name (e.g., "grafana")

    Returns:
        List of version strings, sorted from newest to oldest
    """
    charts = search_helm_chart(repo_name, chart_name, all_versions=True)
    return [chart["version"] for chart in charts]
