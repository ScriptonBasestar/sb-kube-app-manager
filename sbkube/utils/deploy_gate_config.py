"""``sbkube-gate.yaml`` files: loading, discovery and precedence.

The runtime side (which commands are gated, running the gate command, the
human skip) lives in :mod:`sbkube.utils.deploy_gate`.
"""

from __future__ import annotations

import os
import re
from collections.abc import Sequence
from dataclasses import dataclass
from datetime import timedelta
from pathlib import Path
from typing import Any, Literal, NamedTuple

import yaml
from pydantic import BaseModel, ConfigDict, ValidationError, field_validator

from sbkube.exceptions import ConfigurationError
from sbkube.utils.config_inheritance import find_workspace_root

GATE_FILE_NAME = "sbkube-gate.yaml"

GateMode = Literal["enforce", "warn", "off"]
Precedence = Literal["asymmetric", "individual", "global"]

_MODE_STRENGTH: dict[str, int] = {"off": 0, "warn": 1, "enforce": 2}


_TTL_PATTERN = re.compile(r"^([1-9][0-9]*)([mhd])$")
_TTL_UNITS = {"m": "minutes", "h": "hours", "d": "days"}


def parse_grant_ttl(ttl: str) -> timedelta | None:
    """``30m``/``1h``/``2d`` as a duration; ``unlimited`` as ``None``."""
    if ttl == "unlimited":
        return None
    match = _TTL_PATTERN.match(ttl)
    if match is None:
        raise ValueError(
            f"invalid agent_grant.ttl {ttl!r}: use <n>m, <n>h, <n>d or unlimited"
        )
    return timedelta(**{_TTL_UNITS[match.group(2)]: int(match.group(1))})


class AgentGrantSettings(BaseModel):
    """``deploy_gate.agent_grant`` block: enables ``sbkube gate grant``."""

    model_config = ConfigDict(extra="forbid")

    ttl: str = "1h"

    @field_validator("ttl")
    @classmethod
    def _valid_ttl(cls, value: str) -> str:
        parse_grant_ttl(value)
        return value


class DeployGateSettings(BaseModel):
    """``deploy_gate`` block of a gate file."""

    model_config = ConfigDict(extra="forbid")

    command: str | None = None
    mode: GateMode | None = None
    precedence: Precedence | None = None
    allow_override: bool | None = None
    agent_grant: AgentGrantSettings | None = None

    @field_validator("mode", mode="before")
    @classmethod
    def _unquoted_off(cls, value: Any) -> Any:
        # YAML 1.1 (PyYAML) reads an unquoted ``off`` as False.
        return "off" if value is False else value


class DeployGateFile(BaseModel):
    """Top-level document of ``sbkube-gate.yaml``."""

    model_config = ConfigDict(extra="forbid")

    deploy_gate: DeployGateSettings


@dataclass(frozen=True)
class GateSource:
    """A loaded gate file."""

    path: Path
    settings: DeployGateSettings


@dataclass(frozen=True)
class ResolvedGate:
    """Effective gate for one command invocation."""

    mode: GateMode
    command: str | None
    command_dir: Path | None
    warnings: tuple[str, ...]
    # From the global file only; ``None`` means agent grants are disabled.
    agent_grant: AgentGrantSettings | None = None


def load_gate_file(path: Path) -> GateSource:
    """Load and validate one gate file, failing closed."""
    try:
        document = yaml.safe_load(path.read_text(encoding="utf-8"))
    except OSError as e:
        raise ConfigurationError(f"{path}: cannot read deploy gate file: {e}") from e
    except yaml.YAMLError as e:
        raise ConfigurationError(
            f"{path}: deploy gate file is not valid YAML: {e}"
        ) from e
    try:
        parsed = DeployGateFile.model_validate(document)
    except ValidationError as e:
        raise ConfigurationError(f"{path}: invalid deploy gate file: {e}") from e
    return GateSource(path=path, settings=parsed.deploy_gate)


class GateFiles(NamedTuple):
    """Gate files that apply to one command target."""

    global_source: GateSource | None
    individuals: tuple[GateSource, ...]
    # True when no individual file sits between the target and the global level.
    governed_by_global: bool


def find_gate_files(start: Path) -> GateFiles:
    """Return the gate files for a command run on ``start``.

    The scope is the ``.sbkube-workspace`` root, or without a marker the
    enclosing VCS root (``.git``); outside both, files are searched up to the
    filesystem root. The global file is the one at the workspace root, or
    without a marker the topmost file in scope above ``start``. Individual files
    are the nearest file between ``start`` and the global level (it governs
    ``start``) followed by every file below ``start`` (a command on a directory
    also deploys what is under it, e.g. ``apply`` on the workspace root).
    Nested workspaces and repositories below ``start`` are searched too, because
    an outer ``apply`` deploys into them; their global-only keys then fail
    closed in :func:`resolve_gate`.
    """
    base = start.resolve()
    workspace_root = find_workspace_root(base)
    scope_root = workspace_root or _vcs_root(base)

    above = [
        directory / GATE_FILE_NAME
        for directory in (base, *base.parents)
        if scope_root is None or directory.is_relative_to(scope_root)
        if (directory / GATE_FILE_NAME).is_file()
    ]
    if workspace_root is not None:
        global_path: Path | None = workspace_root / GATE_FILE_NAME
        if not global_path.is_file():
            global_path = None
    else:
        global_path = above[-1] if above else None
    individual_paths = [path for path in above[:1] if path != global_path]
    governed_by_global = not individual_paths
    if global_path is not None:
        # Only an opted-in scope is walked: without a global file there is no
        # gate, and a gated repository vendored below must not refuse ours.
        # A followed link can reach a file already counted (e.g. the global one).
        seen = {path.resolve() for path in (global_path, *individual_paths)}
        for path in _gate_files_below(base, bound=scope_root or global_path.parent):
            if path.resolve() not in seen:
                seen.add(path.resolve())
                individual_paths.append(path)

    global_source = load_gate_file(global_path) if global_path else None
    individuals = tuple(load_gate_file(path) for path in individual_paths)
    return GateFiles(global_source, individuals, governed_by_global)


def _vcs_root(base: Path) -> Path | None:
    for directory in (base, *base.parents):
        if (directory / ".git").exists():
            return directory
    return None


def _gate_files_below(base: Path, *, bound: Path) -> list[Path]:
    if not base.is_dir():
        return []

    def unreadable(error: OSError) -> None:
        # A directory we cannot read may hide a stricter file: fail closed.
        raise ConfigurationError(
            f"{error.filename}: cannot search for deploy gate files: {error}"
        ) from error

    found = []
    # Phase directories may be symlinks. Follow those that stay inside the
    # scope, visiting each real directory once so a link cycle cannot loop.
    visited: set[str] = set()
    for directory, subdirs, files in os.walk(
        base, onerror=unreadable, followlinks=True
    ):
        here = Path(directory)
        real = os.path.realpath(directory)
        if real in visited:
            subdirs[:] = []
            continue
        visited.add(real)
        subdirs[:] = sorted(
            d
            for d in subdirs
            if not d.startswith(".")
            and (
                not (here / d).is_symlink()
                or Path(os.path.realpath(here / d)).is_relative_to(bound)
            )
        )
        if here != base and GATE_FILE_NAME in files:
            found.append(here / GATE_FILE_NAME)
    return found


def resolve_gate(
    global_source: GateSource | None,
    individuals: Sequence[GateSource] = (),
    governed_by_global: bool | None = None,
) -> ResolvedGate | None:
    """Apply the precedence rules. ``None`` means no gate is configured.

    Only the global file names the gate ``command``, so exactly one command
    runs. Each individual file is resolved against the global file and the
    strictest result wins, because one gate run covers every directory the
    command touches. ``governed_by_global`` says whether the command's own
    directory falls under the global file directly (no individual file above
    it); it defaults to "no individual files".
    """
    if global_source is None:
        if individuals:
            raise ConfigurationError(
                f"{individuals[0].path}: an individual deploy gate file needs a "
                f"global {GATE_FILE_NAME} at the workspace root"
            )
        return None

    for individual in individuals:
        global_only = [
            name
            for name in ("command", "precedence", "allow_override", "agent_grant")
            if getattr(individual.settings, name) is not None
        ]
        if global_only:
            raise ConfigurationError(
                f"{individual.path}: {', '.join(global_only)} may only be set in "
                f"the global gate file {global_source.path}"
            )

    global_mode = global_source.settings.mode
    if global_mode is None:
        raise ConfigurationError(f"{global_source.path}: deploy_gate.mode is required")

    # Effective mode for every directory the command covers.
    modes: list[GateMode] = []
    warnings: list[str] = []
    if governed_by_global is None:
        governed_by_global = not individuals
    if governed_by_global:
        modes.append(global_mode)
    for individual in individuals:
        individual_mode = individual.settings.mode
        if individual_mode is None or individual_mode == global_mode:
            modes.append(global_mode)
            continue
        mode = _pick_mode(global_source.settings, global_mode, individual_mode)
        modes.append(mode)
        warnings.append(
            f"deploy gate settings disagree: global {global_source.path} "
            f"mode={global_mode}, individual {individual.path} "
            f"mode={individual_mode}; precedence="
            f"{global_source.settings.precedence or 'asymmetric'} -> "
            f"mode={mode} there"
        )

    mode = max(modes, key=_MODE_STRENGTH.__getitem__)
    if len(modes) > 1 and warnings:
        warnings.append(f"running the gate once with the strictest mode={mode}")
    command = global_source.settings.command
    if mode != "off" and not command:
        raise ConfigurationError(
            f"{global_source.path}: deploy_gate.command is required when mode is {mode}"
        )
    return ResolvedGate(
        mode=mode,
        command=command,
        command_dir=global_source.path.parent,
        warnings=tuple(warnings),
        agent_grant=global_source.settings.agent_grant,
    )


def _pick_mode(
    global_settings: DeployGateSettings,
    global_mode: GateMode,
    individual_mode: GateMode,
) -> GateMode:
    if _MODE_STRENGTH[individual_mode] > _MODE_STRENGTH[global_mode]:
        return individual_mode  # tightening always wins
    precedence = global_settings.precedence or "asymmetric"
    if precedence == "individual":
        return individual_mode
    if precedence == "global":
        return global_mode
    return individual_mode if global_settings.allow_override else global_mode
