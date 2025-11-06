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
        raise CliToolNotFoundError(
            msg, "https://helm.sh/docs/intro/install/"
        ) from exc
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
