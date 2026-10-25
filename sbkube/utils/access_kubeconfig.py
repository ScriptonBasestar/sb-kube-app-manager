"""Read-only kubeconfig inspection for ``sbkube access``.

Only structure is read: names, server URLs and the *kind* of credential a user
carries. Token values, ``tokenFile`` contents, client keys and certificate data
are never returned, printed or logged.
"""

from dataclasses import dataclass, field
from pathlib import Path
from typing import Any

import yaml

CLIENT_CERT = "client-cert (admin-like)"
TOKEN = "token"
EXEC = "exec"
OTHER = "other"

_CERT_KEYS = (
    "client-certificate",
    "client-certificate-data",
    "client-key",
    "client-key-data",
)
_TOKEN_KEYS = ("token", "tokenFile")
_EXEC_KEYS = ("exec", "auth-provider")


class KubeconfigError(Exception):
    """A kubeconfig file cannot be read or is not a kubeconfig mapping."""


@dataclass(frozen=True)
class KubeconfigUser:
    """A kubeconfig user: its name, credential kind and referencing contexts."""

    name: str
    credential: str
    contexts: tuple[str, ...] = field(default_factory=tuple)

    @property
    def admin_like(self) -> bool:
        return self.credential == CLIENT_CERT


def read_kubeconfig(path: Path) -> dict[str, Any]:
    """Parse a kubeconfig; the error never echoes file content."""
    try:
        data = yaml.safe_load(path.read_text(encoding="utf-8"))
    except OSError as e:
        raise KubeconfigError(f"cannot read {path}: {e.strerror or e}") from e
    except yaml.YAMLError as e:
        mark = getattr(e, "problem_mark", None)
        where = f" at line {mark.line + 1}" if mark is not None else ""
        raise KubeconfigError(f"{path} is not valid YAML{where}") from e
    if not isinstance(data, dict):
        raise KubeconfigError(f"{path} is not a kubeconfig mapping")
    return data


def _entries(data: dict[str, Any], key: str) -> list[dict[str, Any]]:
    items = data.get(key)
    if not isinstance(items, list):
        return []
    return [item for item in items if isinstance(item, dict)]


def classify_credential(user: object) -> str:
    """Kind of credential a kubeconfig ``user`` body carries."""
    if not isinstance(user, dict):
        return OTHER
    if any(user.get(key) for key in _CERT_KEYS):
        return CLIENT_CERT
    if any(user.get(key) is not None for key in _EXEC_KEYS):
        return EXEC
    if any(user.get(key) for key in _TOKEN_KEYS):
        return TOKEN
    return OTHER


def list_users(data: dict[str, Any]) -> list[KubeconfigUser]:
    """Users of a kubeconfig with the contexts that reference each."""
    referenced: dict[str, list[str]] = {}
    for entry in _entries(data, "contexts"):
        body = entry.get("context")
        user = body.get("user") if isinstance(body, dict) else None
        if isinstance(user, str) and isinstance(entry.get("name"), str):
            referenced.setdefault(user, []).append(entry["name"])

    users = []
    for entry in _entries(data, "users"):
        name = entry.get("name")
        if not isinstance(name, str):
            continue
        users.append(
            KubeconfigUser(
                name=name,
                credential=classify_credential(entry.get("user")),
                contexts=tuple(referenced.get(name, [])),
            )
        )
    return users


def context_names(data: dict[str, Any]) -> list[str]:
    return [
        entry["name"]
        for entry in _entries(data, "contexts")
        if isinstance(entry.get("name"), str)
    ]


def context_server(data: dict[str, Any], context: str) -> str | None:
    """API server URL of ``context``'s cluster, or ``None`` if not resolvable."""
    cluster_names = {
        body.get("cluster")
        for entry in _entries(data, "contexts")
        if entry.get("name") == context
        for body in [entry.get("context")]
        if isinstance(body, dict)
    }
    servers = {
        body.get("server")
        for entry in _entries(data, "clusters")
        if entry.get("name") in cluster_names
        for body in [entry.get("cluster")]
        if isinstance(body, dict) and isinstance(body.get("server"), str)
    }
    return servers.pop() if len(servers) == 1 else None
