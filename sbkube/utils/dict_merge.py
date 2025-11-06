"""Deep dictionary merge utilities for SBKube.

This module provides utilities for deeply merging nested dictionaries,
primarily used for merging Helm values with proper precedence.
"""

from typing import Any


def deep_merge(base: dict[str, Any], override: dict[str, Any]) -> dict[str, Any]:
    """Deep merge two dictionaries with override taking precedence.

    This function recursively merges nested dictionaries. When both base and
    override contain the same key:
    - If both values are dicts, they are recursively merged
    - Otherwise, the override value takes precedence

    Args:
        base: Base dictionary (lower priority)
        override: Override dictionary (higher priority)

    Returns:
        New dictionary with merged values

    Example:
        >>> base = {"a": 1, "b": {"c": 2, "d": 3}}
        >>> override = {"b": {"d": 4, "e": 5}, "f": 6}
        >>> result = deep_merge(base, override)
        >>> result
        {'a': 1, 'b': {'c': 2, 'd': 4, 'e': 5}, 'f': 6}

    Note:
        This function does not modify the input dictionaries.
        Lists are not merged recursively; override list replaces base list.

    """
    # Create a copy of base to avoid modifying the original
    result = base.copy()

    for key, override_value in override.items():
        if key in result and isinstance(result[key], dict) and isinstance(override_value, dict):
            # Both are dicts: recursively merge
            result[key] = deep_merge(result[key], override_value)
        else:
            # Override takes precedence
            result[key] = override_value

    return result


def merge_multiple(*dicts: dict[str, Any]) -> dict[str, Any]:
    """Merge multiple dictionaries with later ones taking precedence.

    Args:
        *dicts: Variable number of dictionaries to merge

    Returns:
        Merged dictionary

    Example:
        >>> d1 = {"a": 1, "b": 2}
        >>> d2 = {"b": 3, "c": 4}
        >>> d3 = {"c": 5, "d": 6}
        >>> result = merge_multiple(d1, d2, d3)
        >>> result
        {'a': 1, 'b': 3, 'c': 5, 'd': 6}

    """
    result = {}
    for d in dicts:
        if d:  # Skip None or empty dicts
            result = deep_merge(result, d)
    return result
