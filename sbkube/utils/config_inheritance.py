"""Resolution of the ``_parent`` inheritance key in sbkube config files.

A config document may declare a parent to inherit from::

    apiVersion: sbkube/v1
    _parent: "@lib/sbkube-charts/ph1_infra/traefik"
    apps:
      traefik:
        values: [values/traefik.yaml]

The parent document is loaded first and the current document is deep-merged on
top of it. ``_parent`` is consumed here and never reaches the pydantic models,
which set ``extra="forbid"``.

Design notes
------------
* **Fail closed.** Every failure raises :class:`ParentResolutionError`. An
  unresolvable parent that degraded to "no inheritance" would yield a document
  that still validates -- it would simply be missing ``type``, ``chart``,
  ``version`` and the base values -- so a warning-and-continue policy turns a
  broken reference into a silently different deployment.
* **Anchors** (``@lib/...``) resolve through the ``.sbkube-workspace`` marker
  found by walking upward from the child config's own directory.
* **``values`` lists are prepended, not replaced.** A parent's ``values`` entry
  is the base layer the child overlays, so parent entries must come first (helm
  applies later files last). They are also rewritten to absolute paths, because
  they are relative to the *parent's* directory while every consumer resolves
  ``values`` against the *child's* app directory.
"""

from __future__ import annotations

from pathlib import Path
from typing import Any

import yaml

from sbkube.exceptions import ConfigurationError
from sbkube.utils.dict_merge import deep_merge
from sbkube.utils.logger import get_logger

logger = get_logger()

WORKSPACE_MARKER = ".sbkube-workspace"
PARENT_KEY = "_parent"
CONFIG_API_PREFIX = "sbkube/"

# Filenames probed when ``_parent`` points at a directory (declaration order = priority).
_PARENT_FILENAMES = ("config.yaml", "config.yml", "sbkube.yaml", "sbkube.yml")

# App keys whose values are paths relative to the declaring file's own directory.
# Only ``values`` is rewritten to an absolute path on inheritance; the rest would
# be silently reinterpreted against the child's directory, so a parent declaring
# one is rejected rather than resolved to the wrong file.
_UNSUPPORTED_PARENT_PATH_KEYS = (
    "overrides",
    "removes",
    "manifests",
    "files",
    "path",
    "paths",
)


class ParentResolutionError(ConfigurationError, ValueError):
    """Raised when a ``_parent`` reference cannot be resolved.

    Also a :class:`ValueError` so that pydantic wraps it into a
    ``ValidationError`` when raised inside a ``mode="before"`` validator.
    """


def has_parent(raw: Any) -> bool:
    """Whether ``raw`` is a mapping carrying a ``_parent`` key."""
    return isinstance(raw, dict) and PARENT_KEY in raw


def is_sbkube_document(raw: Any) -> bool:
    """Whether ``raw`` is an sbkube config document (``apiVersion: sbkube/...``).

    Used to keep inheritance from firing on unrelated YAML that happens to pass
    through the same loader (helm values files, plain manifests).
    """
    api_version = raw.get("apiVersion") if isinstance(raw, dict) else None
    return isinstance(api_version, str) and api_version.startswith(CONFIG_API_PREFIX)


def find_workspace_root(start: Path) -> Path | None:
    """Walk upward from ``start`` looking for the ``.sbkube-workspace`` marker."""
    base = start if start.is_dir() else start.parent
    base = base.resolve()
    for directory in (base, *base.parents):
        if (directory / WORKSPACE_MARKER).is_file():
            return directory
    return None


def _load_anchors(root: Path) -> dict[str, str]:
    marker = root / WORKSPACE_MARKER
    try:
        document = yaml.safe_load(marker.read_text(encoding="utf-8")) or {}
    except OSError as e:
        raise ParentResolutionError(f"cannot read {marker}: {e}") from e
    except yaml.YAMLError as e:
        raise ParentResolutionError(f"{marker} is not valid YAML: {e}") from e

    anchors = document.get("anchors") if isinstance(document, dict) else None
    if anchors is None:
        return {}
    if not isinstance(anchors, dict):
        raise ParentResolutionError(
            f"{marker}: 'anchors' must be a mapping, got {type(anchors).__name__}"
        )
    return {str(key): str(value) for key, value in anchors.items()}


def _pick_parent_file(target: Path, ref: str) -> Path:
    if target.is_dir():
        for name in _PARENT_FILENAMES:
            candidate = target / name
            if candidate.is_file():
                return candidate.resolve()
        raise ParentResolutionError(
            f"'{PARENT_KEY}: {ref}' resolved to directory {target}, which contains none of "
            f"{', '.join(_PARENT_FILENAMES)}"
        )
    if target.is_file():
        return target.resolve()
    for suffix in (".yaml", ".yml"):
        candidate = Path(f"{target}{suffix}")
        if candidate.is_file():
            return candidate.resolve()
    raise ParentResolutionError(
        f"'{PARENT_KEY}: {ref}' resolved to {target}, which does not exist"
    )


def _resolve_ref(ref: Any, child_dir: Path | None) -> Path:
    if not isinstance(ref, str) or not ref.strip():
        raise ParentResolutionError(
            f"'{PARENT_KEY}' must be a non-empty string, got {ref!r}"
        )
    ref = ref.strip()
    anchor_root: Path | None = None

    if ref.startswith("@"):
        anchor, _, rest = ref[1:].partition("/")
        search_from = child_dir or Path.cwd()
        root = find_workspace_root(search_from)
        if root is None:
            raise ParentResolutionError(
                f"'{PARENT_KEY}: {ref}' uses an anchor, but no {WORKSPACE_MARKER} was found "
                f"in {search_from} or any parent directory"
            )
        anchors = _load_anchors(root)
        if anchor not in anchors:
            declared = ", ".join(f"@{name}" for name in sorted(anchors)) or "(none)"
            raise ParentResolutionError(
                f"'{PARENT_KEY}: {ref}' — unknown anchor '@{anchor}'. "
                f"{root / WORKSPACE_MARKER} declares: {declared}"
            )
        workspace_root = root.resolve()
        anchor_root = (root / anchors[anchor]).resolve()
        try:
            anchor_root.relative_to(workspace_root)
        except ValueError as exc:
            raise ParentResolutionError(
                f"'{PARENT_KEY}: {ref}' — anchor '@{anchor}' escapes workspace boundary "
                f"{workspace_root}: {anchor_root}"
            ) from exc
        target = anchor_root
        if rest:
            target = target / rest
        resolved_target = target.resolve()
        try:
            resolved_target.relative_to(anchor_root)
        except ValueError as exc:
            raise ParentResolutionError(
                f"'{PARENT_KEY}: {ref}' escapes anchor boundary {anchor_root}: "
                f"{resolved_target}"
            ) from exc
        target = resolved_target
    elif Path(ref).is_absolute():
        target = Path(ref)
    else:
        if child_dir is None:
            raise ParentResolutionError(
                f"'{PARENT_KEY}: {ref}' is a relative path, but the document's own directory is "
                f"unknown (it was validated in memory, not loaded from a file). Use an anchor "
                f"such as '@lib/...' or an absolute path."
            )
        target = child_dir / ref

    parent_file = _pick_parent_file(target, ref)
    if anchor_root is not None:
        try:
            parent_file.relative_to(anchor_root)
        except ValueError as exc:
            raise ParentResolutionError(
                f"'{PARENT_KEY}: {ref}' resolves to a parent file outside anchor boundary "
                f"{anchor_root}: {parent_file}"
            ) from exc
    return parent_file


def _absolutize_parent_values(
    parent_raw: dict[str, Any], parent_file: Path
) -> dict[str, Any]:
    """Rewrite the parent's ``values`` entries to absolute paths, in place."""
    apps = parent_raw.get("apps")
    if not isinstance(apps, dict):
        return parent_raw

    parent_dir = parent_file.parent
    for name, app in apps.items():
        if not isinstance(app, dict):
            continue
        for key in _UNSUPPORTED_PARENT_PATH_KEYS:
            if key in app:
                raise ParentResolutionError(
                    f"{parent_file}: apps.{name}.{key} is a path relative to the parent's own "
                    f"directory, and inheritance only rewrites 'values' to an absolute path. "
                    f"Inheriting it would resolve the path against the child's directory instead. "
                    f"Declare it in the child config, or add rewriting support for '{key}'."
                )
        values = app.get("values")
        if not isinstance(values, list):
            continue
        app["values"] = [
            str((parent_dir / value).resolve())
            if isinstance(value, str) and not Path(value).is_absolute()
            else value
            for value in values
        ]
    return parent_raw


def _prepend_parent_values(
    merged: dict[str, Any],
    parent_raw: dict[str, Any],
    child: dict[str, Any],
) -> None:
    """Restore parent-first ``values`` ordering that the plain deep merge replaced."""
    parent_apps = parent_raw.get("apps")
    child_apps = child.get("apps")
    merged_apps = merged.get("apps")
    if not (
        isinstance(parent_apps, dict)
        and isinstance(child_apps, dict)
        and isinstance(merged_apps, dict)
    ):
        return

    for name, child_app in child_apps.items():
        parent_app = parent_apps.get(name)
        merged_app = merged_apps.get(name)
        if not (
            isinstance(parent_app, dict)
            and isinstance(child_app, dict)
            and isinstance(merged_app, dict)
        ):
            continue
        parent_values = parent_app.get("values")
        child_values = child_app.get("values")
        if isinstance(parent_values, list) and isinstance(child_values, list):
            merged_app["values"] = [*parent_values, *child_values]


def resolve_inheritance(
    raw: Any,
    config_path: str | Path | None = None,
    _chain: tuple[str, ...] = (),
) -> Any:
    """Resolve ``_parent`` in ``raw`` and return the merged document.

    Args:
        raw: Parsed config document. Returned unchanged when it is not a mapping
            or carries no ``_parent`` key.
        config_path: Path the document was loaded from. Required for relative
            ``_parent`` references; anchors fall back to the current working
            directory when it is ``None``.
        _chain: Internal. Resolved parent files already visited, for cycle detection.

    Raises:
        ParentResolutionError: On any unresolvable, unreadable, malformed, or
            cyclic parent reference.
    """
    if not has_parent(raw):
        return raw

    child_path = Path(config_path).resolve() if config_path is not None else None
    child_dir = child_path.parent if child_path is not None else None
    parent_file = _resolve_ref(raw[PARENT_KEY], child_dir)

    chain = _chain or ((str(child_path),) if child_path is not None else ())
    key = str(parent_file)
    if key in chain:
        cycle = " -> ".join([*chain, key])
        raise ParentResolutionError(f"'{PARENT_KEY}' inheritance cycle: {cycle}")

    try:
        parent_raw = yaml.safe_load(parent_file.read_text(encoding="utf-8"))
    except OSError as e:
        raise ParentResolutionError(
            f"cannot read parent config {parent_file}: {e}"
        ) from e
    except yaml.YAMLError as e:
        raise ParentResolutionError(
            f"parent config {parent_file} is not valid YAML: {e}"
        ) from e

    if parent_raw is None:
        parent_raw = {}
    if not isinstance(parent_raw, dict):
        raise ParentResolutionError(
            f"parent config {parent_file} must be a mapping, got {type(parent_raw).__name__}"
        )

    parent_raw = resolve_inheritance(parent_raw, parent_file, (*chain, key))
    parent_raw = _absolutize_parent_values(parent_raw, parent_file)

    child = {k: v for k, v in raw.items() if k != PARENT_KEY}
    merged = deep_merge(parent_raw, child)
    _prepend_parent_values(merged, parent_raw, child)

    logger.debug(f"{PARENT_KEY}: {raw[PARENT_KEY]} -> {parent_file}")
    return merged
