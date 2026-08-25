"""Workspace-bounded inheritance for cluster and repository settings.

Settings are inherited only inside a workspace declared by
``.sbkube-workspace``.  This keeps a direct ``-f app/sbkube.yaml`` invocation
equivalent to traversing the workspace root, phase, and app explicitly, while
never absorbing an unrelated configuration above the workspace boundary.
"""

from __future__ import annotations

from pathlib import Path
from typing import Any

from sbkube.utils.config_inheritance import find_workspace_root
from sbkube.utils.file_loader import load_config_file

_MAPPING_KEYS = ("helm_repos", "oci_registries", "git_repos")
_SCALAR_KEYS = ("kubeconfig", "kubeconfig_context")
_CONFIG_NAMES = ("sbkube.yaml", "sbkube.yml")


def extract_inherited_settings(config_data: dict[str, Any]) -> dict[str, Any]:
    """Return the settings that may flow from a workspace parent to a child."""
    settings = config_data.get("settings", {})
    if not isinstance(settings, dict):
        return {}

    result: dict[str, Any] = {}
    for key in _MAPPING_KEYS:
        value = settings.get(key)
        if value:
            result[key] = dict(value)
    for key in _SCALAR_KEYS:
        value = settings.get(key)
        if value:
            result[key] = value
    return result


def merge_inherited_settings(
    base: dict[str, Any], override: dict[str, Any]
) -> dict[str, Any]:
    """Merge settings with child values taking precedence over parent values."""
    merged = dict(base)
    for key in _MAPPING_KEYS:
        if key in override:
            combined = dict(merged.get(key, {}))
            combined.update(override[key])
            merged[key] = combined
    for key in _SCALAR_KEYS:
        if key in override:
            merged[key] = override[key]
    return merged


def build_inherited_settings_chain(
    root_config_data: dict[str, Any],
    intermediate_config_paths: list[Path] | Path | None = None,
) -> dict[str, Any]:
    """Merge a root document and existing descendants in shallow-to-deep order.

    An existing invalid config is deliberately not skipped: silently changing a
    cluster target is more dangerous than failing the command before it starts.
    """
    merged = extract_inherited_settings(root_config_data)
    if intermediate_config_paths is None:
        return merged
    paths = [intermediate_config_paths] if isinstance(intermediate_config_paths, Path) else intermediate_config_paths
    for config_path in paths:
        if not config_path.exists():
            continue
        merged = merge_inherited_settings(
            merged, extract_inherited_settings(load_config_file(config_path))
        )
    return merged


def collect_parent_inherited_settings(config_dir: Path) -> dict[str, Any]:
    """Collect root-to-parent settings, bounded by the workspace marker.

    Without a marker there is no declared workspace and therefore no implicit
    parent inheritance.  The local document in ``config_dir`` is excluded.
    """
    workspace_root = find_workspace_root(config_dir)
    if workspace_root is None:
        return {}
    if config_dir.resolve() == workspace_root:
        return {}

    parent_documents: list[dict[str, Any]] = []
    current = config_dir.resolve().parent
    while True:
        for name in _CONFIG_NAMES:
            candidate = current / name
            if candidate.exists():
                # Do not catch errors here: an invalid parent must fail closed.
                parent_documents.append(load_config_file(candidate))
                break
        if current == workspace_root:
            break
        current = current.parent

    merged: dict[str, Any] = {}
    for document in reversed(parent_documents):
        merged = merge_inherited_settings(merged, extract_inherited_settings(document))
    return merged
