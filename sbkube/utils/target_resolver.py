"""Helpers for resolving positional TARGET and config file scope."""

from dataclasses import dataclass
from pathlib import Path

from sbkube.utils.file_loader import ConfigType, detect_config_file

_CONFIG_CANDIDATES = ("sbkube.yaml", "sbkube.yml")


@dataclass(frozen=True)
class ResolvedTarget:
    """Resolved target context for command execution."""

    workspace_root: Path
    config_file: Path
    scope_path: str | None


def _find_local_config(dir_path: Path) -> Path | None:
    for name in _CONFIG_CANDIDATES:
        candidate = dir_path / name
        if candidate.exists():
            return candidate
    return None


def _find_config_upward(start_dir: Path) -> Path | None:
    current = start_dir.resolve()
    root = Path(current.anchor)

    while True:
        found = _find_local_config(current)
        if found:
            return found
        if current == root:
            return None
        current = current.parent


def _normalize_scope(path: Path, root: Path) -> str | None:
    if path == root:
        return None
    relative = path.relative_to(root)
    if not relative.parts:
        return None
    return relative.as_posix()


def resolve_target(
    target: str | None,
    config_file: str | None = None,
    *,
    base_dir: Path | None = None,
) -> ResolvedTarget:
    """Resolve target/config input into workspace root, config path, and scope."""
    working_dir = (base_dir or Path.cwd()).resolve()

    if config_file:
        config_path = Path(config_file)
        if not config_path.is_absolute():
            config_path = (working_dir / config_path).resolve()
        workspace_root = config_path.parent
        scope_path: str | None = None
        if target:
            target_path = Path(target)
            if not target_path.is_absolute():
                target_path = (workspace_root / target_path).resolve()
            try:
                scope_path = _normalize_scope(target_path, workspace_root)
            except ValueError as exc:
                msg = (
                    "TARGET must be inside the workspace when -f/--file is provided: "
                    f"target={target_path}, workspace={workspace_root}"
                )
                raise ValueError(msg) from exc
        return ResolvedTarget(
            workspace_root=workspace_root,
            config_file=config_path,
            scope_path=scope_path,
        )

    if target:
        target_path = Path(target)
        if not target_path.is_absolute():
            target_path = (working_dir / target_path).resolve()

        local_config = _find_local_config(target_path)
        if local_config:
            return ResolvedTarget(
                workspace_root=target_path,
                config_file=local_config,
                scope_path=None,
            )

        found_config = _find_config_upward(target_path)
        if not found_config:
            msg = f"Could not find sbkube.yaml while searching upward from: {target_path}"
            raise ValueError(msg)

        workspace_root = found_config.parent
        scope_path = _normalize_scope(target_path, workspace_root)
        return ResolvedTarget(
            workspace_root=workspace_root,
            config_file=found_config,
            scope_path=scope_path,
        )

    detected = detect_config_file(working_dir, None)
    if detected.config_type == ConfigType.UNKNOWN or not detected.primary_file:
        msg = (
            f"No sbkube.yaml found in {working_dir}. "
            "Create one with 'sbkube init' or specify with -f flag."
        )
        raise ValueError(msg)

    return ResolvedTarget(
        workspace_root=detected.primary_file.parent,
        config_file=detected.primary_file,
        scope_path=None,
    )
