"""Settings Merger Utility for SBKube v0.10.0+.

This module provides utilities for merging configuration settings
with proper inheritance rules.

Merge Rules:
- Lists: Merge and deduplicate (preserving order)
- Dicts: Deep merge (child values override parent)
- Scalars: Child overrides parent
- None values: Do not override (parent value preserved)

Usage:
    from sbkube.utils.settings_merger import merge_settings

    parent = UnifiedSettings(kubeconfig="~/.kube/config", timeout=600)
    child = UnifiedSettings(timeout=300)  # Override timeout only
    merged = merge_settings(parent, child)
    # Result: kubeconfig="~/.kube/config", timeout=300
"""

from typing import Any, TypeVar

from pydantic import BaseModel

from sbkube.utils.logger import logger

T = TypeVar("T", bound=BaseModel)


def merge_settings(parent: T, child: T | None) -> T:
    """Merge two settings objects with inheritance rules.

    The child settings override parent settings according to merge rules:
    - Lists: Merge and deduplicate
    - Dicts: Deep merge
    - Scalars: Child overrides parent (unless child is None/default)

    Args:
        parent: Parent settings (base/global)
        child: Child settings (override/local)

    Returns:
        New settings object with merged values

    """
    if child is None:
        return parent.model_copy()

    parent_dict = parent.model_dump()
    child_dict = child.model_dump()

    # Get default values for the model to detect explicit overrides
    defaults = parent.__class__().model_dump()

    merged = _merge_dicts(parent_dict, child_dict, defaults)

    return parent.__class__(**merged)


def _merge_dicts(
    parent: dict[str, Any],
    child: dict[str, Any],
    defaults: dict[str, Any],
) -> dict[str, Any]:
    """Deep merge two dictionaries with inheritance rules.

    Args:
        parent: Parent dictionary
        child: Child dictionary (values to override)
        defaults: Default values (to detect explicit overrides)

    Returns:
        Merged dictionary

    """
    result = parent.copy()

    for key, child_value in child.items():
        parent_value = parent.get(key)
        default_value = defaults.get(key)

        # Skip if child value is the default (not explicitly set)
        if child_value == default_value and parent_value != default_value:
            continue

        # Handle None - don't override with None unless parent is also None
        if child_value is None and parent_value is not None:
            continue

        # Merge based on type
        if isinstance(child_value, dict) and isinstance(parent_value, dict):
            # Deep merge dictionaries
            result[key] = _merge_dicts(
                parent_value,
                child_value,
                default_value if isinstance(default_value, dict) else {},
            )
        elif isinstance(child_value, list) and isinstance(parent_value, list):
            # Merge lists with deduplication
            result[key] = _merge_lists(parent_value, child_value)
        else:
            # Scalar override
            result[key] = child_value

    return result


def _merge_lists(parent: list[Any], child: list[Any]) -> list[Any]:
    """Merge two lists with deduplication.

    The result contains all items from parent, followed by items from child
    that are not already in parent. Order is preserved.

    Args:
        parent: Parent list
        child: Child list (items to add)

    Returns:
        Merged list with unique items

    """
    result = list(parent)  # Copy parent list
    seen = set()

    # Track items in parent (for hashable types)
    for item in parent:
        try:
            seen.add(_make_hashable(item))
        except TypeError:
            # Item not hashable, will use equality check
            pass

    # Add child items that are not in parent
    for item in child:
        try:
            item_hash = _make_hashable(item)
            if item_hash not in seen:
                result.append(item)
                seen.add(item_hash)
        except TypeError:
            # Item not hashable, use equality check
            if item not in result:
                result.append(item)

    return result


def _make_hashable(item: Any) -> Any:
    """Convert item to hashable form for set operations.

    Args:
        item: Item to convert

    Returns:
        Hashable representation

    Raises:
        TypeError: If item cannot be made hashable

    """
    if isinstance(item, dict):
        return tuple(sorted((k, _make_hashable(v)) for k, v in item.items()))
    if isinstance(item, list):
        return tuple(_make_hashable(i) for i in item)
    return item


def merge_settings_chain(*settings: T | None) -> T:
    """Merge a chain of settings objects.

    Settings are merged left-to-right, with later settings
    overriding earlier ones.

    Args:
        *settings: Variable number of settings objects

    Returns:
        Merged settings object

    Raises:
        ValueError: If no valid settings provided

    """
    result = None

    for setting in settings:
        if setting is None:
            continue

        if result is None:
            result = setting.model_copy()
        else:
            result = merge_settings(result, setting)

    if result is None:
        msg = "At least one non-None settings object is required"
        raise ValueError(msg)

    return result


def apply_settings_to_dict(
    settings: BaseModel,
    target: dict[str, Any],
    key_mapping: dict[str, str] | None = None,
) -> dict[str, Any]:
    """Apply settings values to a target dictionary.

    Useful for applying UnifiedSettings to command arguments or
    environment configurations.

    Args:
        settings: Settings object to apply
        target: Target dictionary to update
        key_mapping: Optional mapping of settings keys to target keys
            e.g., {"kubeconfig": "kubeconfig_path"}

    Returns:
        Updated target dictionary

    """
    result = target.copy()
    settings_dict = settings.model_dump(exclude_none=True)
    key_mapping = key_mapping or {}

    for key, value in settings_dict.items():
        target_key = key_mapping.get(key, key)

        # Only update if target doesn't have a value
        if target_key not in result or result[target_key] is None:
            result[target_key] = value

    return result


def extract_settings_subset(
    settings: BaseModel,
    keys: list[str],
) -> dict[str, Any]:
    """Extract a subset of settings as a dictionary.

    Args:
        settings: Settings object
        keys: List of keys to extract

    Returns:
        Dictionary with extracted values

    """
    settings_dict = settings.model_dump()
    return {k: settings_dict[k] for k in keys if k in settings_dict}


def log_settings_diff(
    parent: BaseModel,
    child: BaseModel,
    context: str = "",
) -> None:
    """Log the differences between parent and child settings.

    Useful for debugging inheritance issues.

    Args:
        parent: Parent settings
        child: Child settings
        context: Context string for log messages

    """
    parent_dict = parent.model_dump()
    child_dict = child.model_dump()

    prefix = f"[{context}] " if context else ""

    for key in set(parent_dict.keys()) | set(child_dict.keys()):
        parent_val = parent_dict.get(key)
        child_val = child_dict.get(key)

        if parent_val != child_val:
            logger.debug(
                f"{prefix}Setting '{key}': "
                f"parent={_truncate(parent_val)} -> child={_truncate(child_val)}"
            )


def _truncate(value: Any, max_len: int = 50) -> str:
    """Truncate value for display."""
    s = str(value)
    if len(s) > max_len:
        return s[: max_len - 3] + "..."
    return s
