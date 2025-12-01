"""Version comparison utilities for Helm charts.

This module provides utilities for comparing semantic versions
and determining update availability for Helm charts.
"""

from __future__ import annotations

from enum import Enum
from typing import NamedTuple

from packaging.version import InvalidVersion, Version, parse


class VersionComparison(Enum):
    """Version comparison result."""

    OUTDATED = -1  # Current < Available (update available)
    SAME = 0  # Current == Available (up to date)
    NEWER = 1  # Current > Available (ahead of registry)


class VersionDiff(NamedTuple):
    """Detailed version difference information."""

    current: str
    available: str
    comparison: VersionComparison
    is_major_update: bool
    is_minor_update: bool
    is_patch_update: bool


def compare_versions(current: str, available: str) -> VersionComparison:
    """Compare two semantic versions.

    Args:
        current: Current version string (e.g., "1.0.0")
        available: Available version string (e.g., "1.2.0")

    Returns:
        VersionComparison enum indicating relationship

    Raises:
        InvalidVersion: If either version string is invalid
    """
    try:
        current_ver = parse(current)
        available_ver = parse(available)

        if current_ver < available_ver:
            return VersionComparison.OUTDATED
        elif current_ver == available_ver:
            return VersionComparison.SAME
        else:
            return VersionComparison.NEWER
    except InvalidVersion as e:
        raise InvalidVersion(f"Invalid version format: {e}") from e


def get_version_diff(current: str, available: str) -> VersionDiff:
    """Get detailed version difference information.

    Args:
        current: Current version string
        available: Available version string

    Returns:
        VersionDiff with detailed comparison information
    """
    comparison = compare_versions(current, available)

    # Parse versions for detailed comparison
    current_ver = parse(current)
    available_ver = parse(available)

    # Determine update type (only if outdated)
    is_major = False
    is_minor = False
    is_patch = False

    if comparison == VersionComparison.OUTDATED:
        # Extract major.minor.patch from Version objects
        current_parts = _get_version_parts(current_ver)
        available_parts = _get_version_parts(available_ver)

        if current_parts and available_parts:
            curr_major, curr_minor, curr_patch = current_parts
            avail_major, avail_minor, avail_patch = available_parts

            is_major = avail_major > curr_major
            is_minor = not is_major and avail_minor > curr_minor
            is_patch = not is_major and not is_minor and avail_patch > curr_patch

    return VersionDiff(
        current=current,
        available=available,
        comparison=comparison,
        is_major_update=is_major,
        is_minor_update=is_minor,
        is_patch_update=is_patch,
    )


def _get_version_parts(version: Version) -> tuple[int, int, int] | None:
    """Extract major.minor.patch from Version object.

    Args:
        version: Parsed Version object

    Returns:
        Tuple of (major, minor, patch) or None if cannot extract
    """
    try:
        # Version.release is a tuple like (1, 2, 3) for "1.2.3"
        release = version.release
        if len(release) >= 3:
            return (release[0], release[1], release[2])
        elif len(release) == 2:
            return (release[0], release[1], 0)
        elif len(release) == 1:
            return (release[0], 0, 0)
        return None
    except (AttributeError, IndexError):
        return None


def is_update_available(current: str, available: str) -> bool:
    """Check if an update is available.

    Args:
        current: Current version string
        available: Available version string

    Returns:
        True if update is available (current < available)
    """
    return compare_versions(current, available) == VersionComparison.OUTDATED


def get_latest_version(versions: list[str]) -> str | None:
    """Get the latest version from a list of version strings.

    Args:
        versions: List of version strings

    Returns:
        Latest version string, or None if list is empty or all invalid
    """
    if not versions:
        return None

    valid_versions = []
    for ver_str in versions:
        try:
            valid_versions.append((parse(ver_str), ver_str))
        except InvalidVersion:
            continue

    if not valid_versions:
        return None

    # Sort by parsed version and return the original string
    valid_versions.sort(key=lambda x: x[0], reverse=True)
    return valid_versions[0][1]
