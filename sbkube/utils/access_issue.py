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
    token = proc.stdout.strip()
    if not token:
        raise TokenIssueError("kubectl returned an empty token")
    if any(ch.isspace() for ch in token):
        raise TokenIssueError("kubectl returned unexpected multi-part output")
    return token


def ensure_private_dir(path: Path) -> None:
    """Create ``path`` with mode 0700, or tighten an existing directory to it.

    Raises:
        TokenIssueError: If ``path`` is not a directory this user owns.

    """
    try:
        path.mkdir(mode=0o700, parents=True, exist_ok=True)
        info = path.stat()
        if not stat.S_ISDIR(info.st_mode):
            raise TokenIssueError(f"{path} is not a directory")
        if info.st_uid != os.getuid():
            raise TokenIssueError(f"{path} is not owned by the current user")
        if stat.S_IMODE(info.st_mode) != 0o700:
            path.chmod(0o700)
    except OSError as e:
        raise TokenIssueError(f"cannot prepare {path}: {e.strerror or e}") from e


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


def overwrite_problem(path: Path) -> str | None:
    """Why an existing ``path`` must not be overwritten, or ``None``.

    Only a file that looks generated (every user authenticates solely via
    ``tokenFile``) may be replaced; anything else could be a hand-made or
    admin kubeconfig.
    """
    if not path.exists():
        return None
    try:
        data = read_kubeconfig(path)
    except KubeconfigError as e:
        return f"{e}; refusing to overwrite it"
    users = entries(data, "users")
    raw_users = data.get("users")
    generated = (
        isinstance(raw_users, list)
        and bool(raw_users)
        and len(users) == len(raw_users)
        and all(
            isinstance(u.get("user"), dict) and set(u["user"]) == {"tokenFile"}
            for u in users
        )
    )
    if not generated:
        return (
            f"{path} does not look like a generated deployer kubeconfig (every "
            "user must authenticate only via tokenFile); refusing to overwrite it"
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
        resolved = Path(ca_file).expanduser()
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
