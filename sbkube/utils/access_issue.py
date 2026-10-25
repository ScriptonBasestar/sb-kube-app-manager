"""Building blocks of ``sbkube access issue``: token minting and private files.

The token exists only in memory and in the token file. It is never part of an
argv, an environment variable, an exception message or any output; failures
report kubectl's first stderr line (kubectl never echoes the token there).
"""

import os
import secrets
import stat
import subprocess
from pathlib import Path
from typing import Any

import yaml

from sbkube.utils.access_kubeconfig import (
    KubeconfigError,
    context_cluster,
    entries,
    read_kubeconfig,
)

KUBECTL_TIMEOUT_SECONDS = 30
DEPLOYER_USER = "deploy"
TOKEN_FILE_NAME = "deploy.token"

# User keys that point at credential files.
_CREDENTIAL_FILE_KEYS = ("tokenFile", "client-certificate", "client-key")

# Cluster fields copied verbatim from the admin cluster entry.
_COPIED_CLUSTER_KEYS = (
    "server",
    "certificate-authority-data",
    "tls-server-name",
    "proxy-url",
    "insecure-skip-tls-verify",
)


class TokenIssueError(Exception):
    """Minting the token or writing the credential files failed."""


def mint_token(
    admin: Path,
    context: str,
    namespace: str,
    service_account: str,
    duration: str,
) -> str:
    """Request a ServiceAccount token with the admin credential.

    Raises:
        TokenIssueError: On any failure. The message never contains the token.

    """
    command = [
        "kubectl",
        "--kubeconfig",
        str(admin),
        "--context",
        context,
        "-n",
        namespace,
        "create",
        "token",
        service_account,
        "--duration",
        duration,
    ]
    try:
        proc = subprocess.run(  # noqa: S603
            command,
            capture_output=True,
            text=True,
            timeout=KUBECTL_TIMEOUT_SECONDS,
            check=False,
        )
    except FileNotFoundError as e:
        raise TokenIssueError("kubectl not found in PATH") from e
    except subprocess.TimeoutExpired as e:
        raise TokenIssueError(f"kubectl timed out ({KUBECTL_TIMEOUT_SECONDS}s)") from e
    if proc.returncode != 0:
        detail = (proc.stderr.strip().splitlines() or [""])[0][:200]
        raise TokenIssueError(detail or f"kubectl exited {proc.returncode}")
    return token_from_output(proc.stdout)


def token_from_output(output: str) -> str:
    """Validate token output without ever including it in an error message."""
    token = output.strip()
    if not token:
        raise TokenIssueError("kubectl returned an empty token")
    if any(ch.isspace() for ch in token):
        raise TokenIssueError("kubectl returned unexpected multi-part output")
    return token


def check_token_dir(path: Path) -> None:
    """Pre-flight for :func:`ensure_private_dir`; changes nothing.

    Raises:
        TokenIssueError: If ``path`` exists but is not a private directory we
            own, or cannot be created.

    """
    if not path.exists():
        parent = next(p for p in path.parents if p.exists())
        if not parent.is_dir() or not os.access(parent, os.W_OK | os.X_OK):
            raise TokenIssueError(f"cannot create {path}: {parent} is not writable")
        return
    info = path.stat()
    if not stat.S_ISDIR(info.st_mode):
        raise TokenIssueError(f"{path} is not a directory")
    if info.st_uid != os.getuid():
        raise TokenIssueError(f"{path} is not owned by the current user")
    if stat.S_IMODE(info.st_mode) & 0o077:
        raise TokenIssueError(
            f"{path} is accessible to other users (mode "
            f"{stat.S_IMODE(info.st_mode):o}); run `chmod 700 {path}` or set "
            "access.token_dir to a dedicated directory"
        )
    if not os.access(path, os.W_OK | os.X_OK):
        raise TokenIssueError(f"{path} is not writable")


def ensure_private_dir(path: Path) -> None:
    """Create ``path`` with mode 0700; an existing directory is never chmod-ed.

    Raises:
        TokenIssueError: If an existing ``path`` fails :func:`check_token_dir`.

    """
    try:
        if path.exists():
            check_token_dir(path)
            return
        path.parent.mkdir(parents=True, exist_ok=True)
        path.mkdir(mode=0o700)
        path.chmod(0o700)
    except OSError as e:
        raise TokenIssueError(f"cannot prepare {path}: {e.strerror or e}") from e


def check_writable_parent(path: Path) -> None:
    """Pre-flight: the directory that will hold ``path`` exists and is writable."""
    parent = path.parent
    if not parent.is_dir() or not os.access(parent, os.W_OK | os.X_OK):
        raise TokenIssueError(f"{parent} does not exist or is not writable")


def write_private_file(path: Path, content: str) -> None:
    """Write ``content`` to ``path`` atomically with mode 0600.

    A temp file in the same directory is created exclusively (O_EXCL, 0600),
    flushed to disk and renamed over ``path``; on failure the old file stays.
    """
    temp = path.with_name(f".{path.name}.{secrets.token_hex(6)}.tmp")
    try:
        fd = os.open(temp, os.O_WRONLY | os.O_CREAT | os.O_EXCL, 0o600)
        try:
            with os.fdopen(fd, "w", encoding="utf-8") as handle:
                handle.write(content)
                handle.flush()
                os.fsync(handle.fileno())
        except BaseException:
            temp.unlink(missing_ok=True)
            raise
        os.replace(temp, path)
    except OSError as e:
        temp.unlink(missing_ok=True)
        raise TokenIssueError(f"cannot write {path}: {e.strerror or e}") from e


def same_file(first: Path, second: Path) -> bool:
    """Whether two paths name the same file (symlinks and hard links included)."""
    if first.resolve() == second.resolve():
        return True
    try:
        return first.samefile(second)
    except OSError:
        return False


def _resolve_ref(value: str, base: Path) -> Path:
    # client-go resolves kubeconfig references relative to the file; no tilde expansion.
    path = Path(value)
    return path if path.is_absolute() else base.parent / path


def referenced_credential_files(path: Path, data: dict[str, Any]) -> list[Path]:
    """Files a kubeconfig's users read credentials from (relative to ``path``)."""
    found: list[Path] = []
    for entry in entries(data, "users"):
        user = entry.get("user")
        if not isinstance(user, dict):
            continue
        for key in _CREDENTIAL_FILE_KEYS:
            value = user.get(key)
            if isinstance(value, str) and value:
                found.append(_resolve_ref(value, path))
    for entry in entries(data, "clusters"):
        cluster = entry.get("cluster")
        value = (
            cluster.get("certificate-authority") if isinstance(cluster, dict) else None
        )
        if isinstance(value, str) and value:
            found.append(_resolve_ref(value, path))
    return found


def protected_files(admin: Path | None, readonly: Path | None) -> dict[Path, str]:
    """Every file ``issue`` must not write: the kubeconfigs and their credential files.

    Raises:
        KubeconfigError: If the admin kubeconfig, or an existing readonly one,
            cannot be read (refusing is safer than skipping it).

    """
    protected: dict[Path, str] = {}
    sources = []
    if admin is not None:
        if admin.exists():
            sources.append(("admin", admin))
        else:
            protected[admin] = "admin kubeconfig"
    if readonly is not None:
        if readonly.exists():
            sources.append(("readonly", readonly))
        else:
            protected[readonly] = "readonly kubeconfig"
    for role, source in sources:
        protected[source] = f"{role} kubeconfig"
        for ref in referenced_credential_files(source, read_kubeconfig(source)):
            protected[ref] = f"credential file of the {role} kubeconfig"
    return protected


def collision(path: Path, protected: dict[Path, str]) -> str | None:
    """What ``path`` collides with in ``protected``, or ``None``."""
    for other, what in protected.items():
        if same_file(path, other):
            return f"{what} ({other})"
    return None


def overwrite_problem(path: Path, token_path: Path) -> str | None:
    """Why an existing ``path`` must not be overwritten, or ``None``.

    Only the generated shape may be replaced: exactly one user named
    ``deploy`` whose only key is a ``tokenFile`` naming ``token_path``.
    Anything else could be a hand-made or admin kubeconfig.
    """
    if not path.exists():
        return None
    try:
        data = read_kubeconfig(path)
    except KubeconfigError as e:
        return f"{e}; refusing to overwrite it"
    users = entries(data, "users")
    ok = (
        isinstance(data.get("users"), list)
        and len(data["users"]) == 1
        and len(users) == 1
        and users[0].get("name") == DEPLOYER_USER
        and isinstance(users[0].get("user"), dict)
        and set(users[0]["user"]) == {"tokenFile"}
        and isinstance(users[0]["user"]["tokenFile"], str)
        and same_file(_resolve_ref(users[0]["user"]["tokenFile"], path), token_path)
    )
    if not ok:
        return (
            f"{path} does not look like a kubeconfig generated by `access issue` "
            f"(one user '{DEPLOYER_USER}' authenticating only via tokenFile "
            f"{token_path}); refusing to overwrite it"
        )
    return None


def build_deployer_kubeconfig(
    admin_data: dict[str, Any], context: str, admin_path: Path, token_path: Path
) -> dict[str, Any]:
    """Kubeconfig with the admin cluster, one ``deploy`` token-file user, no admin credential.

    Raises:
        KubeconfigError: If the admin context or cluster is unusable.

    """
    cluster_name, admin_cluster = context_cluster(admin_data, context, admin_path)
    cluster = {k: admin_cluster[k] for k in _COPIED_CLUSTER_KEYS if k in admin_cluster}
    ca_file = admin_cluster.get("certificate-authority")
    if isinstance(ca_file, str):
        resolved = Path(ca_file)
        if not resolved.is_absolute():
            resolved = admin_path.parent / resolved
        cluster["certificate-authority"] = str(resolved)
    return {
        "apiVersion": "v1",
        "kind": "Config",
        "clusters": [{"name": cluster_name, "cluster": cluster}],
        "contexts": [
            {
                "name": context,
                "context": {"cluster": cluster_name, "user": DEPLOYER_USER},
            }
        ],
        "current-context": context,
        "users": [{"name": DEPLOYER_USER, "user": {"tokenFile": str(token_path)}}],
    }


def dump_kubeconfig(data: dict[str, Any]) -> str:
    return yaml.safe_dump(data, sort_keys=False)
