"""Bounded metadata for an already-resolved execution, never an authorization.

The command owns resolution. This module records the objects and files it will
consume and rejects changes; it deliberately does not implement another settings
resolver or claim to attest rendered artifacts or arbitrary hook effects.
"""

from __future__ import annotations

import hashlib
import json
import os
import stat
from collections.abc import Iterable
from dataclasses import dataclass, field
from pathlib import Path
from typing import Any

import toml
import yaml

from sbkube.exceptions import SbkubeError

MAX_INPUT_BYTES = 8 * 1024 * 1024
MAX_CONTEXT_BYTES = 32 * 1024
MAX_APPS = 256
MAX_FILES = 512


class ExecutionContextError(SbkubeError):
    """A bounded input could not be bound or changed after resolution."""


def _canonical(value: Any) -> str:
    return json.dumps(value, sort_keys=True, separators=(",", ":"), allow_nan=False)


def _model_digest(value: Any) -> str:
    if value is not None and hasattr(value, "model_dump"):
        value = value.model_dump(mode="json")
    return hashlib.sha256(_canonical(value).encode()).hexdigest()


def _file_state(path: Path) -> tuple[str, str | None, bool]:
    try:
        resolved = path.expanduser().resolve()
        if not resolved.exists():
            return str(resolved), None, False
        descriptor = os.open(resolved, os.O_RDONLY | os.O_NONBLOCK)
        with os.fdopen(descriptor, "rb") as stream:
            before = os.fstat(stream.fileno())
            if not stat.S_ISREG(before.st_mode) or before.st_size > MAX_INPUT_BYTES:
                raise ExecutionContextError("Execution context input is not a bounded regular file")
            raw = stream.read(MAX_INPUT_BYTES + 1)
            after = os.fstat(stream.fileno())
        if (before.st_size, before.st_mtime_ns, before.st_ctime_ns) != (
            after.st_size, after.st_mtime_ns, after.st_ctime_ns
        ):
            raise ExecutionContextError("Execution context input changed while reading")
        if len(raw) > MAX_INPUT_BYTES:
            raise ExecutionContextError("Execution context input exceeds the size limit")
        try:
            document = (
                toml.loads(raw.decode("utf-8"))
                if resolved.suffix == ".toml" else yaml.safe_load(raw)
            )
            has_parent = isinstance(document, dict) and "_parent" in document
        except (yaml.YAMLError, toml.TomlDecodeError, UnicodeError, ValueError):
            # Non-config inputs may use another syntax. Absence of a parsed
            # parent trace is uncertainty, never proof that inputs are complete.
            has_parent = True
        return str(resolved), hashlib.sha256(raw).hexdigest(), has_parent
    except (OSError, RuntimeError) as error:
        raise ExecutionContextError("Cannot read execution context input") from error


def _text(value: str | None) -> str | None:
    if value is not None and (
        not isinstance(value, str) or len(value) > 4096
        or any(ord(char) < 32 for char in value)
    ):
        raise ExecutionContextError("Invalid execution context identifier")
    return value


def effective_app_context(app: Any, group_context: str | None) -> str | None:
    """Use the Helm/YAML override rule shared with their actual executors."""
    if app.type in {"helm", "yaml"}:
        return getattr(app, "context", None) or group_context
    return group_context


@dataclass(frozen=True)
class ResolvedExecutionContext:
    """Snapshot of the exact resolved objects; private objects never leave Python."""

    operation: str
    config_file: Path
    selected_apps: tuple[str, ...]
    kubeconfig: str | None
    context: str | None
    payload_json: str
    _config: Any = field(repr=False, compare=False)
    _sources: Any = field(repr=False, compare=False)
    _config_digest: str = field(repr=False)
    _sources_digest: str = field(repr=False)
    _files: tuple[tuple[Path, tuple[str, str | None, bool]], ...] = field(repr=False)
    _apps: tuple[tuple[str, str], ...] = field(repr=False)

    def verify(self) -> None:
        """Refuse input/model changes, including changes made by a prior hook."""
        try:
            if (
                _model_digest(self._config) != self._config_digest
                or _model_digest(self._sources) != self._sources_digest
                or any(_file_state(path) != expected for path, expected in self._files)
            ):
                raise ExecutionContextError("Resolved execution inputs changed after planning")
        except (TypeError, ValueError) as error:
            raise ExecutionContextError("Resolved execution inputs cannot be verified") from error

    def verify_child(self, child: ResolvedExecutionContext) -> None:
        """A nested deploy may execute a selected subset of its apply plan."""
        self.verify()
        child.verify()
        expected_apps = dict(self._apps)
        if (
            self.config_file != child.config_file
            or self.kubeconfig != child.kubeconfig
            or self.context != child.context
            or self._sources_digest != child._sources_digest
            or any(expected_apps.get(name) != digest for name, digest in child._apps)
        ):
            raise ExecutionContextError("Nested deploy differs from the resolved apply plan")


def capture_execution_context(
    operation: str,
    config_file: Path,
    config: Any,
    selected_apps: Iterable[str],
    kubeconfig: str | None,
    context: str | None,
    *,
    sources: Any = None,
    input_paths: Iterable[Path] = (),
    prune_apps: Iterable[str] = (),
) -> ResolvedExecutionContext:
    """Capture resolved inputs without exporting config values or credentials.

    Missing prepared files are explicit incomplete metadata, never a successful
    artifact verification. Existing gates still own all allow/deny decisions.
    """
    try:
        if operation not in {"apply", "deploy", "prune"}:
            raise ExecutionContextError("Unsupported resolved execution operation")
        names = tuple(selected_apps)
        pruned = tuple(prune_apps)
        if len(names) > MAX_APPS or len(pruned) > MAX_APPS or len(set(names)) != len(names):
            raise ExecutionContextError("Invalid resolved execution app selection")
        requested_path = Path(config_file).expanduser().absolute()
        # Relative app inputs and gate discovery use the execution directory,
        # not a symlinked config file's physical source directory. _files binds
        # the resolved file identity separately and notices link retargeting.
        config_path = requested_path.parent.resolve() / requested_path.name
        kube_path = str(Path(kubeconfig).expanduser().resolve()) if kubeconfig else None
        _text(kube_path)
        _text(context)
        paths = [Path(config_file), *list(input_paths)]
        if kubeconfig:
            paths.append(Path(kubeconfig))
        apps = []
        app_digests = []
        incomplete_reasons: set[str] = set()
        for name in names:
            _text(name)
            app = config.apps[name]
            app_digests.append((name, _model_digest(app)))
            apps.append({
                "name": name, "type": app.type, "enabled": app.enabled,
                "namespace": getattr(app, "namespace", None) or config.namespace or "default",
                "context": _text(effective_app_context(app, context)),
                "action_namespaces": [
                    action.namespace or getattr(app, "namespace", None) or config.namespace or "default"
                    for action in getattr(app, "actions", ()) or ()
                ],
                "opaque_effects": bool(getattr(app, "hooks", None))
                or app.type in {"exec", "action", "hook"},
            })
            for value in getattr(app, "values", ()) or ():
                if isinstance(value, str) and "${" not in value:
                    paths.append(config_path.parent / value)
                else:
                    incomplete_reasons.add("unresolved-values-input")
        if len(paths) > MAX_FILES:
            raise ExecutionContextError("Too many execution context inputs")
        # Retain lexical paths as well as their resolved identity so a changed
        # symlink is noticed at the next mutation boundary.
        files = tuple((path, _file_state(path)) for path in dict.fromkeys(paths))
        for _path, (_, digest, has_parent_marker) in files:
            if digest is None:
                incomplete_reasons.add("missing-input")
            elif has_parent_marker:
                # The loader has no parent-source trace API. Do not claim all
                # external inherited inputs have been bound by this v1 carrier.
                incomplete_reasons.add("parent-source-trace-unavailable")
        payload = {
            "schema": "sbkube-deploy-context/v1", "operation": operation,
            "target": str(config_path.parent), "config_file": str(config_path),
            "config_model_sha256": _model_digest(config),
            "sources_model_sha256": _model_digest(sources),
            "kubeconfig": kube_path, "context": context, "apps": apps,
            "prune_apps": list(pruned),
            "global_hooks": bool(getattr(config, "hooks", None)),
            "inputs": [{"path": path, "sha256": digest} for _, (path, digest, _) in files],
            "inputs_complete": not incomplete_reasons,
            "incomplete_reasons": sorted(incomplete_reasons),
            "artifacts": "not-attested", "authority": "none",
        }
        raw = _canonical(payload)
        if len(raw.encode()) > MAX_CONTEXT_BYTES:
            raise ExecutionContextError("Execution context exceeds the transport limit")
        return ResolvedExecutionContext(
            operation, config_path, names, kube_path, context, raw,
            config, sources, _model_digest(config), _model_digest(sources), files,
            tuple(app_digests),
        )
    except ExecutionContextError:
        raise
    except (TypeError, ValueError, KeyError, AttributeError, OSError) as error:
        raise ExecutionContextError("Cannot capture resolved execution inputs") from error
