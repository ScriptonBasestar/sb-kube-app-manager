"""Prepare app-owned Git sources without adopting or deleting unknown caches."""

import json
import os
import re
import selectors
import shutil
import signal
import subprocess
import tempfile
import time
import uuid
from pathlib import Path
from typing import Any
from urllib.parse import urlsplit

GIT_PREFIXES = ("https://", "http://", "ssh://", "git://", "git@")
MARKER = "sbkube-source.json"


class GitSourceError(ValueError):
    """Safe diagnostic: never include a URL, command arguments or Git stderr."""

    def __init__(self, message: str, *, retain_staging: bool = False) -> None:
        super().__init__(message)
        self.retain_staging = retain_staging


def _app_path(app_name: str, repos_dir: Path) -> Path:
    if not re.fullmatch(r"[A-Za-z0-9_][A-Za-z0-9_.-]*", app_name):
        raise GitSourceError("Invalid Git app cache key")
    if repos_dir.is_symlink():
        raise GitSourceError("Git repository cache root must not be a symlink")
    for parent in (repos_dir, *repos_dir.parents):
        if parent.is_symlink():
            raise GitSourceError("Git repository cache has a symlink ancestor")
    dest = repos_dir / app_name
    if dest.is_symlink():
        raise GitSourceError("Git app cache must not be a symlink")
    return dest


def resolve_git_source(app_name: str, app: Any, git_repos: dict) -> dict[str, str]:
    """Resolve ref > explicitly supplied branch > alias branch > main."""
    _app_path(app_name, Path("."))
    alias_branch = None
    if isinstance(app.repo, str) and app.repo.startswith(GIT_PREFIXES):
        url = app.repo
    else:
        if app.repo not in git_repos:
            raise GitSourceError("Git repository alias not found in sources")
        source = git_repos[app.repo]
        if isinstance(source, str):
            url = source
        elif isinstance(source, dict):
            url, alias_branch = source.get("url"), source.get("branch")
        else:
            url, alias_branch = source.url, source.branch
    if (
        not isinstance(url, str)
        or not url.startswith(GIT_PREFIXES)
        or any(c.isspace() or ord(c) < 32 for c in url)
    ):
        raise GitSourceError("Invalid Git source URL")
    if url.startswith("git@"):
        host, separator, path = url[4:].partition(":")
        valid = bool(host and not host.startswith("-") and separator and path)
    else:
        try:
            host = urlsplit(url).hostname
            valid = bool(host and not host.startswith("-"))
        except ValueError:
            valid = False
    if not valid:
        raise GitSourceError("Invalid Git source host")
    app_branch = app.branch if "branch" in app.model_fields_set else None
    revision = (
        app.ref
        if app.ref is not None
        else app_branch
        if app_branch is not None
        else alias_branch
    )
    revision = "main" if revision is None else revision
    if (
        not isinstance(revision, str)
        or not revision
        or revision.startswith("-")
        or any(c.isspace() or ord(c) < 32 for c in revision)
    ):
        raise GitSourceError("Invalid Git source revision")
    return {
        "url": url,
        "revision": revision,
        "kind": "ref" if app.ref is not None else "branch",
    }


def _identity(pid: int) -> str | None:
    try:
        result = subprocess.run(
            [
                "ps",
                "-p",
                str(pid),
                "-o",
                "ppid=",
                "-o",
                "pgid=",
                "-o",
                "lstart=",
                "-o",
                "command=",
            ],
            capture_output=True,
            text=True,
            timeout=3,
            check=False,
        )
    except (OSError, subprocess.TimeoutExpired):
        raise GitSourceError(
            "Cannot observe captured Git child identity", retain_staging=True
        ) from None
    if len(result.stdout) > 16384:
        raise GitSourceError(
            "Captured Git identity output exceeds its bound", retain_staging=True
        )
    if result.returncode == 1 and not result.stdout.strip():
        return None
    fields = result.stdout.strip().split(maxsplit=2)
    if (
        result.returncode != 0
        or len(fields) != 3
        or fields[:2] != [str(os.getpid()), str(pid)]
    ):
        raise GitSourceError(
            "Cannot verify captured Git child identity", retain_staging=True
        )
    return result.stdout.strip()


def _group_present(pgid: int) -> bool:
    try:
        result = subprocess.run(
            ["ps", "-axo", "pid=,pgid="],
            capture_output=True,
            text=True,
            timeout=3,
            check=False,
        )
    except (OSError, subprocess.TimeoutExpired):
        raise GitSourceError(
            "Cannot observe captured Git process group", retain_staging=True
        ) from None
    if result.returncode != 0 or len(result.stdout) > 1024 * 1024:
        raise GitSourceError(
            "Cannot verify captured Git process group", retain_staging=True
        )
    rows = [line.split() for line in result.stdout.splitlines()]
    if (
        not rows
        or any(
            len(row) != 2 or not all(re.fullmatch(r"[0-9]+", value) for value in row)
            for row in rows
        )
        or [str(os.getpid()), str(os.getpgrp())] not in rows
    ):
        raise GitSourceError(
            "Incomplete numeric process-group observation", retain_staging=True
        )
    return any(row[1] == str(pgid) for row in rows)


def _stop(process: subprocess.Popen, identity: str | None) -> None:
    if process.poll() is not None:
        if _group_present(process.pid):
            raise GitSourceError(
                "Reaped Git leader has an uncertain remaining group",
                retain_staging=True,
            )
        return
    for sig, delay in ((signal.SIGTERM, 3), (signal.SIGKILL, 2)):
        observed = _identity(process.pid)
        if process.poll() is not None:
            break
        if identity is None or observed != identity:
            raise GitSourceError(
                "Git child identity changed; refusing signal", retain_staging=True
            )
        try:
            os.killpg(process.pid, sig)
        except ProcessLookupError:
            break
        try:
            process.wait(timeout=delay)
            break
        except subprocess.TimeoutExpired:
            continue
    if process.poll() is None or _group_present(process.pid):
        raise GitSourceError("Git process cleanup is uncertain", retain_staging=True)


def _git(
    *args: str, cwd: Path | None = None, optional: bool = False, timeout: float = 120
) -> str | None:
    environment = {
        key: value
        for key, value in os.environ.items()
        if key
        not in (
            "GIT_DIR",
            "GIT_WORK_TREE",
            "GIT_COMMON_DIR",
            "GIT_INDEX_FILE",
            "GIT_OBJECT_DIRECTORY",
            "GIT_ALTERNATE_OBJECT_DIRECTORIES",
            "GIT_NAMESPACE",
            "GIT_SHALLOW_FILE",
            "GIT_CONFIG",
        )
    }
    environment["GIT_TERMINAL_PROMPT"] = "0"
    command = ["git", "--no-optional-locks", "-c", f"core.hooksPath={os.devnull}"]
    if cwd is not None:
        command += ["-c", "core.worktree=" + str(cwd.resolve())]
    deadline = time.monotonic() + timeout
    process = subprocess.Popen(
        [*command, *args],
        cwd=cwd,
        env=environment,
        stdout=subprocess.PIPE,
        stderr=subprocess.PIPE,
        start_new_session=True,
    )
    identity = None
    try:
        identity = _identity(process.pid)
        stdout = bytearray()
        total = 0
        with selectors.DefaultSelector() as selector:
            selector.register(process.stdout, selectors.EVENT_READ, True)
            selector.register(process.stderr, selectors.EVENT_READ, False)
            while selector.get_map():
                if time.monotonic() >= deadline:
                    raise GitSourceError("Git command exceeded the 120-second timeout")
                for key, _ in selector.select(
                    min(0.2, max(0, deadline - time.monotonic()))
                ):
                    chunk = os.read(key.fd, 65536)
                    if not chunk:
                        selector.unregister(key.fd)
                    else:
                        total += len(chunk)
                        if total > 1024 * 1024:
                            raise GitSourceError(
                                "Git output exceeds the combined 1 MiB limit"
                            )
                        if key.data:
                            stdout.extend(chunk)
            try:
                process.wait(timeout=max(0.1, deadline - time.monotonic()))
            except subprocess.TimeoutExpired:
                raise GitSourceError(
                    "Git command exceeded the 120-second timeout"
                ) from None
        if process.returncode != 0:
            if optional:
                return None
            raise GitSourceError("Git source command failed; command output withheld")
        return stdout.decode(errors="replace").strip()
    finally:
        _stop(process, identity)
        process.stdout.close()
        process.stderr.close()


def _commit(path: Path, revision: str) -> str:
    candidates = [revision]
    if revision.startswith("refs/heads/"):
        candidates.insert(
            0, "refs/remotes/origin/" + revision.removeprefix("refs/heads/")
        )
    elif not revision.startswith("refs/"):
        candidates.append("refs/remotes/origin/" + revision)
    for candidate in candidates:
        value = _git(
            "rev-parse",
            "--verify",
            "--end-of-options",
            candidate + "^{commit}",
            cwd=path,
            optional=True,
        )
        if value and re.fullmatch(r"[0-9a-f]{40}|[0-9a-f]{64}", value):
            return value
    raise GitSourceError("Requested Git revision cannot be resolved")


def _read_owned(app_name: str, path: Path) -> dict:
    marker_path = path / ".git" / MARKER
    if (
        not path.is_dir()
        or not (path / ".git").is_dir()
        or (path / ".git").is_symlink()
        or marker_path.is_symlink()
        or not marker_path.is_file()
    ):
        raise GitSourceError(
            "Git cache is not an owned clone; existing files preserved"
        )
    try:
        if (
            marker_path.stat().st_size > 65536
            or marker_path.stat().st_mode & 0o777 != 0o600
        ):
            raise GitSourceError("Invalid Git source identity marker")
        marker = json.loads(marker_path.read_text())
    except (OSError, ValueError) as error:
        raise GitSourceError(
            "Missing or invalid Git source identity marker; cache preserved"
        ) from error
    if (
        not isinstance(marker, dict)
        or type(marker.get("schema")) is not int
        or marker.get("schema") != 1
        or marker.get("app") != app_name
        or not isinstance(marker.get("source"), dict)
    ):
        raise GitSourceError("Git source ownership marker does not match this app")
    source = marker["source"]
    if (
        set(source) != {"url", "revision", "kind"}
        or not all(isinstance(v, str) for v in source.values())
        or source["kind"] not in ("ref", "branch")
    ):
        raise GitSourceError("Invalid Git source identity specification")
    if _git("status", "--porcelain", "--untracked-files=all", cwd=path):
        raise GitSourceError(
            "Git cache contains modified or untracked files; cache preserved"
        )
    if _git("config", "--get", "remote.origin.url", cwd=path) != source["url"]:
        raise GitSourceError("Git cache origin differs from its ownership marker")
    if _commit(path, "HEAD") != marker.get("head") or _commit(
        path, source["revision"]
    ) != marker.get("head"):
        raise GitSourceError("Git cache HEAD differs from its recorded revision")
    return marker


def read_prepared_git_source(
    app_name: str,
    app: Any,
    git_repos: dict,
    repos_dir: Path,
    *,
    reject_ignored: bool = False,
) -> dict:
    """Return verified private identity; callers must not log its source URL."""
    spec = resolve_git_source(app_name, app, git_repos)
    marker = _read_owned(app_name, _app_path(app_name, repos_dir))
    if marker["source"] != spec:
        raise GitSourceError(
            "Prepared Git source differs from current declaration; prepare it again"
        )
    if reject_ignored and _git(
        "ls-files",
        "--others",
        "--ignored",
        "--exclude-standard",
        cwd=repos_dir / app_name,
    ):
        raise GitSourceError(
            "Git chart source contains ignored files outside the recorded commit"
        )
    return marker


def prepare_git_source(
    app_name: str, app: Any, git_repos: dict, repos_dir: Path, force: bool = False
) -> dict:
    """Validate a new clone completely before publishing it at repos/app_name."""
    spec = resolve_git_source(app_name, app, git_repos)
    dest = _app_path(app_name, repos_dir)
    previous = None
    if dest.exists():
        previous = _read_owned(app_name, dest)
        if not force:
            if previous["source"] != spec:
                raise GitSourceError(
                    "Prepared Git source differs from current declaration; use --force after review"
                )
            return previous
    repos_dir.mkdir(parents=True, exist_ok=True)
    staging = Path(tempfile.mkdtemp(prefix=f".{app_name}.clone-", dir=repos_dir))
    keep_staging = False
    backup = None
    try:
        _git("clone", "--no-checkout", "--", spec["url"], str(staging))
        head = _commit(staging, spec["revision"])
        _git("checkout", "--detach", head, cwd=staging)
        if _commit(staging, "HEAD") != head:
            raise GitSourceError(
                "Cloned Git HEAD does not match the requested revision"
            )
        marker = {"schema": 1, "app": app_name, "source": spec, "head": head}
        marker_path = staging / ".git" / MARKER
        with marker_path.open("x") as target:
            marker_path.chmod(0o600)
            json.dump(marker, target)
            target.write("\n")
        _read_owned(app_name, staging)
        if previous is not None:
            if _read_owned(app_name, dest) != previous:
                raise GitSourceError(
                    "Existing Git cache changed while preparing; cache preserved"
                )
            backup = repos_dir / f".{app_name}.previous-{uuid.uuid4().hex}"
            dest.rename(backup)
        elif dest.exists() or dest.is_symlink():
            raise GitSourceError(
                "Git cache appeared during preparation; existing files preserved"
            )
        try:
            staging.rename(dest)
        except OSError:
            if backup is not None:
                backup.rename(dest)
            raise
        return marker
    except GitSourceError as error:
        keep_staging = error.retain_staging
        raise
    except OSError as error:
        raise GitSourceError(
            "Cannot publish Git source; previous cache preserved"
        ) from error
    finally:
        if staging.exists() and not keep_staging:
            list(staging.iterdir())
            shutil.rmtree(staging)
