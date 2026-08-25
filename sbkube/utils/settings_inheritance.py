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


def _settings_mapping(
    config_data: dict[str, Any], config_path: Path | str | None = None
) -> dict[str, Any]:
    """Validate and return a unified document's settings mapping."""
    label = str(config_path) if config_path else "configuration"
    settings = config_data.get("settings", {})
    if not isinstance(settings, dict):
        raise ValueError(f"{label}: 'settings' must be a mapping")
    for key in _MAPPING_KEYS:
        if key in settings and not isinstance(settings[key], dict):
            raise ValueError(f"{label}: 'settings.{key}' must be a mapping")
    return settings


def extract_inherited_settings(
    config_data: dict[str, Any], config_path: Path | str | None = None
) -> dict[str, Any]:
    """Return the settings that may flow from a workspace parent to a child."""
    settings = _settings_mapping(config_data, config_path)

    result: dict[str, Any] = {}
    for key in _MAPPING_KEYS:
        value = settings.get(key)
        if value:
            result[key] = dict(value)
    for key in _SCALAR_KEYS:
        if key in settings:
            # Preserve an explicitly empty scalar so SourceScheme rejects it
            # instead of silently falling back to an ancestor's cluster.
            result[key] = settings[key]
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


def merge_local_source_settings(
    inherited: dict[str, Any], local_settings: dict[str, Any], config_path: Path | str
) -> dict[str, Any]:
    """Merge inherited settings with a local unified document's full settings.

    Repository mappings are union-merged; all other local SourceScheme fields
    replace inherited values.  Validation occurs before any merge.
    """
    _settings_mapping({"settings": local_settings}, config_path)
    local_inherited = extract_inherited_settings(
        {"settings": local_settings}, config_path
    )
    merged = merge_inherited_settings(inherited, local_inherited)
    for key, value in local_settings.items():
        if key not in _MAPPING_KEYS:
            merged[key] = value
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
            merged, extract_inherited_settings(load_config_file(config_path), config_path)
        )
    return merged


def collect_parent_inherited_settings(config_dir: Path) -> dict[str, Any]:
    """Collect root-to-parent settings, bounded by the workspace marker.

    Without a marker there is no declared workspace and therefore no implicit
    parent inheritance.  The local document in ``config_dir`` is excluded.
    """
    parent_documents = collect_parent_documents(config_dir)
    merged: dict[str, Any] = {}
    for document, document_path in parent_documents:
        merged = merge_inherited_settings(
            merged, extract_inherited_settings(document, document_path)
        )
    return merged


def collect_parent_documents(config_dir: Path) -> list[tuple[dict[str, Any], Path]]:
    """Return valid parent documents from workspace root to immediate parent."""
    workspace_root = find_workspace_root(config_dir)
    if workspace_root is None:
        return []
    if config_dir.resolve() == workspace_root:
        return []

    parent_documents: list[tuple[dict[str, Any], Path]] = []
    current = config_dir.resolve().parent
    while True:
        for name in _CONFIG_NAMES:
            candidate = current / name
            if candidate.exists():
                resolved = candidate.resolve()
                try:
                    resolved.relative_to(workspace_root.resolve())
                except ValueError as exc:
                    raise ValueError(
                        f"{candidate}: symlink escapes workspace boundary {workspace_root}"
                    ) from exc
                # Do not catch errors here: an invalid parent must fail closed.
                document = load_config_file(candidate)
                api_version = document.get("apiVersion") if isinstance(document, dict) else None
                if not isinstance(api_version, str) or not api_version.startswith("sbkube/"):
                    raise ValueError(f"{candidate}: parent must be an sbkube API document")
                parent_documents.append((document, candidate))
                break
        if current == workspace_root:
            break
        current = current.parent

    return list(reversed(parent_documents))
