"""Datetime utilities for SBKube.

This module provides consistent datetime handling across the codebase.
"""

from datetime import UTC, datetime


def utc_now() -> datetime:
    """Get current UTC time as timezone-naive datetime.

    Returns timezone-naive datetime for SQLite compatibility.
    SQLite stores datetime values without timezone info, so we need
    to ensure consistency when comparing stored values with new ones.

    Returns:
        Current UTC time as timezone-naive datetime

    """
    return datetime.now(UTC).replace(tzinfo=None)


def utc_now_aware() -> datetime:
    """Get current UTC time as timezone-aware datetime.

    Use this for in-memory operations where timezone-aware
    comparisons are acceptable.

    Returns:
        Current UTC time as timezone-aware datetime

    """
    return datetime.now(UTC)


def format_timestamp(dt: datetime | None, fmt: str = "%Y-%m-%d %H:%M:%S") -> str:
    """Format datetime for display.

    Args:
        dt: Datetime to format (can be None)
        fmt: strftime format string

    Returns:
        Formatted string or "-" if dt is None

    """
    if dt is None:
        return "-"
    return dt.strftime(fmt)
