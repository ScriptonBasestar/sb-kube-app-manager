"""Security-related helpers."""

from __future__ import annotations

import os
from typing import Mapping


def is_exec_allowed(env: Mapping[str, str] | None = None) -> bool:
    """Return True if exec/hook command execution is allowed.

    Controlled by the SBKUBE_ALLOW_EXEC environment variable.
    Defaults to True when unset. Explicit false values disable execution.
    """
    source = env or os.environ
    value = source.get("SBKUBE_ALLOW_EXEC")
    if value is None:
        return True

    normalized = value.strip().lower()
    if normalized in {"0", "false", "no", "off"}:
        return False
    if normalized in {"1", "true", "yes", "on"}:
        return True

    # Unknown values default to allow to avoid surprising breaks.
    return True
