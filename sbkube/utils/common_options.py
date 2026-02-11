"""Shared CLI option helpers for target-based command routing."""

from dataclasses import dataclass
from pathlib import Path

import click

from sbkube.utils.target_resolver import resolve_target


@dataclass(frozen=True)
class ResolvedCommandPaths:
    """Normalized path inputs after applying TARGET/-f precedence."""

    base_dir: Path
    app_config_dir_name: str | None
    config_file_name: str
    sources_file_name: str


def target_options(func):
    """Attach shared positional TARGET and -f/--file option."""
    func = click.argument(
        "target",
        required=False,
        default=None,
        type=click.Path(exists=True, file_okay=False, dir_okay=True),
    )(func)
    func = click.option(
        "-f",
        "--file",
        "config_file",
        default=None,
        type=click.Path(exists=True, file_okay=True, dir_okay=False),
        help="Unified config file (sbkube.yaml)",
    )(func)
    return func


def resolve_command_paths(
    *,
    target: str | None,
    config_file: str | None,
    base_dir: str,
    app_config_dir_name: str | None,
    config_file_name: str,
    sources_file_name: str,
) -> ResolvedCommandPaths:
    """Resolve command path arguments with positional TARGET semantics."""
    if target and app_config_dir_name:
        click.echo(
            "WARNING: '--app-dir' is ignored when positional TARGET is provided.",
            err=True,
        )
    if target and base_dir != ".":
        click.echo(
            "WARNING: '--base-dir' is ignored when positional TARGET is provided.",
            err=True,
        )

    # Legacy mode (no TARGET/-f): keep existing path behavior.
    if not target and not config_file:
        return ResolvedCommandPaths(
            base_dir=Path(base_dir).resolve(),
            app_config_dir_name=app_config_dir_name,
            config_file_name=config_file_name,
            sources_file_name=sources_file_name,
        )

    resolved = resolve_target(
        target=target,
        config_file=config_file,
        base_dir=Path.cwd(),
    )
    scope = resolved.scope_path or "."

    return ResolvedCommandPaths(
        base_dir=resolved.workspace_root,
        app_config_dir_name=scope,
        config_file_name=resolved.config_file.name,
        # Unified config acts as both app config and settings source.
        sources_file_name=resolved.config_file.name,
    )
