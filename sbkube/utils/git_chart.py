"""Resolve Helm consumers of prepared Git sources without duplicating a checkout."""

import hashlib
import json
import os
import re
from pathlib import Path
from typing import Any

from sbkube.models.config_model import GitApp, HelmApp
from sbkube.utils.chart_path_resolver import ChartPathResult

MARKER = ".sbkube-git-chart.json"
MAX_ENTRIES = 10_000
MAX_BYTES = 64 * 1024 * 1024
REFERENCE = re.compile(r"\$\{repos\.([A-Za-z0-9_-]+)\}(?:/(.*))?")


def is_git_chart(chart: str) -> bool:
    return isinstance(chart, str) and chart.startswith("${repos.")


def git_chart_repositories(
    config_file: Path,
    document: dict,
    inherited_settings: dict | None = None,
    sources_file: Path | None = None,
) -> dict:
    """Use the same declared settings inheritance as prepare/deploy."""
    from sbkube.models.sources_model import SourceScheme
    from sbkube.utils.file_loader import load_config_file
    from sbkube.utils.settings_inheritance import (
        collect_parent_inherited_settings,
        merge_inherited_settings,
        merge_local_source_settings,
    )

    unified = document.get("apiVersion", "").startswith("sbkube/")
    if unified:
        settings = merge_local_source_settings(
            merge_inherited_settings(
                collect_parent_inherited_settings(config_file.parent),
                inherited_settings or {},
            ),
            document.get("settings", {}),
            config_file,
        )
    elif sources_file is not None and sources_file.is_file():
        settings = load_config_file(sources_file)
    else:
        settings = {}
    source_fields = SourceScheme.model_fields
    if unified:
        settings = {key: value for key, value in settings.items() if key in source_fields}
    return SourceScheme(**settings).git_repos


def _digest(value: Any) -> str:
    return hashlib.sha256(json.dumps(value, sort_keys=True).encode()).hexdigest()


def chart_tree_digest(root: Path, *, exclude_git_metadata: bool = False) -> str:
    """Hash bounded, self-contained chart inputs; never follow directory links."""
    if root.is_symlink() or not root.is_dir():
        raise ValueError("Git chart must be a regular directory")
    resolved_root = root.resolve()
    digest = hashlib.sha256()
    entries = total = 0
    for directory, directories, files in os.walk(root, followlinks=False):
        directories.sort()
        files.sort()
        if ".git" in directories:
            if not exclude_git_metadata:
                raise ValueError("Git chart build contains Git administrative data")
            directories.remove(".git")
        for name in directories:
            child = Path(directory) / name
            if child.is_symlink():
                raise ValueError("Git chart directory symlinks are not supported")
            digest.update(b"D\0" + child.relative_to(root).as_posix().encode() + b"\0")
        for name in files:
            if name == ".git":
                if not exclude_git_metadata:
                    raise ValueError("Git chart build contains Git administrative data")
                continue
            if name == MARKER and Path(directory) == root:
                continue
            child = Path(directory) / name
            target = child.resolve(strict=True)
            if (
                not target.is_relative_to(resolved_root)
                or ".git" in target.relative_to(resolved_root).parts
            ):
                raise ValueError("Git chart symlink escapes its chart directory")
            if not target.is_file():
                raise ValueError("Git chart contains a non-regular file")
            entries += 1
            total += target.stat().st_size
            if entries > MAX_ENTRIES or total > MAX_BYTES:
                raise ValueError("Git chart exceeds the 10000-file/64MiB input limit")
            relative = child.relative_to(root).as_posix()
            kind = b"L" if child.is_symlink() else b"F"
            digest.update(kind + b"\0" + relative.encode() + b"\0")
            if child.is_symlink():
                digest.update(os.readlink(child).encode() + b"\0")
            with child.open("rb") as incoming:
                remaining = target.stat().st_size
                while chunk := incoming.read(min(65536, remaining + 1)):
                    remaining -= len(chunk)
                    if remaining < 0:
                        raise ValueError("Git chart changed while reading")
                    digest.update(chunk)
            if remaining:
                raise ValueError("Git chart changed while reading")
            digest.update(b"\0")
        entries += len(directories)
        if entries > MAX_ENTRIES:
            raise ValueError("Git chart exceeds the 10000-entry input limit")
    return digest.hexdigest()


def _source(
    app: HelmApp,
    repos_dir: Path,
    git_apps: dict | None,
    git_repos: dict | None,
    app_name: str | None = None,
    app_config_dir: Path | None = None,
) -> tuple[Path, dict]:
    # Imported here so ordinary local/remote Helm consumers need no Git operations.
    from sbkube.utils.git_source import read_prepared_git_source

    match = REFERENCE.fullmatch(app.chart)
    if not match:
        raise ValueError("Expected chart: ${repos.git-app}/relative/chart")
    name, suffix = match.group(1), match.group(2) or ""
    if any(part in ("", ".", "..") for part in suffix.split("/")) and suffix:
        raise ValueError("Git chart path must be a clean relative path")
    git_app = (git_apps or {}).get(name)
    if not isinstance(git_app, GitApp) or not git_app.enabled:
        raise ValueError("Git chart must reference an enabled Git app")
    identity = read_prepared_git_source(
        name, git_app, git_repos or {}, repos_dir, reject_ignored=True
    )
    repository = repos_dir / name
    if repository.is_symlink():
        raise ValueError("Prepared Git checkout cannot be a symlink")
    source = repository / suffix
    resolved_source = source.resolve()
    if source.is_symlink() or not resolved_source.is_relative_to(repository.resolve()):
        raise ValueError("Git chart escapes its prepared checkout")
    if ".git" in resolved_source.relative_to(repository.resolve()).parts:
        raise ValueError("Git chart cannot reference Git administrative data")
    if not (source / "Chart.yaml").is_file():
        raise ValueError("Prepared Git chart has no Chart.yaml")
    if (source / MARKER).exists() or (source / MARKER).is_symlink():
        raise ValueError("Git chart contains a reserved build provenance file")
    metadata = {
        "schema": 1,
        "chart": app.chart,
        "source_identity": _digest(identity),
        "source_tree": chart_tree_digest(source, exclude_git_metadata=True),
        "config": _digest(app.model_dump(mode="json")),
    }
    for pattern in (*app.overrides, *app.removes):
        if (
            Path(pattern).is_absolute()
            or ".." in Path(pattern).parts
            or ".git" in Path(pattern).parts
            or MARKER in Path(pattern).parts
        ):
            raise ValueError("Git chart customization must stay within its chart")
    if app.overrides:
        if app_config_dir is None or app_name is None:
            raise ValueError("Git chart overrides require an application directory")
        overrides = app_config_dir / "overrides" / app_name
        if overrides.is_symlink():
            raise ValueError("Git chart overrides cannot be a symlink")
        metadata["overrides"] = (
            chart_tree_digest(overrides) if overrides.exists() else None
        )
    return source, metadata


def _marker(path: Path) -> dict:
    marker = path / MARKER
    if marker.is_symlink() or not marker.is_file() or marker.stat().st_size > 16384:
        raise ValueError(
            "Git chart build has no valid provenance; preserve it and rebuild"
        )
    value = json.loads(marker.read_text())
    if not isinstance(value, dict) or value.get("schema") != 1:
        raise ValueError("Unsupported Git chart build provenance")
    return value


def verify_owned_build(path: Path, app_name: str) -> None:
    """Refuse removal/reuse of an unknown or locally modified build."""
    if path.is_symlink():
        raise ValueError("Git chart build cannot be a symlink")
    marker = _marker(path)
    if marker.get("app") != app_name or marker.get("output_tree") != chart_tree_digest(
        path
    ):
        raise ValueError(
            "Git chart build is modified or belongs to another app; preserve it"
        )


def resolve_git_chart_path(
    app: HelmApp,
    app_name: str,
    repos_dir: Path,
    git_apps: dict | None,
    git_repos: dict | None,
    build_dir: Path | None = None,
    check_build_first: bool = True,
    output: Any = None,
    app_config_dir: Path | None = None,
) -> ChartPathResult:
    try:
        source, metadata = _source(
            app, repos_dir, git_apps, git_repos, app_name, app_config_dir
        )
        if check_build_first and build_dir is not None:
            built = build_dir / app_name
            if built.exists() or built.is_symlink():
                verify_owned_build(built, app_name)
                if _marker(built).get("input") != metadata:
                    raise ValueError("Git chart build is stale; run sbkube build")
                return ChartPathResult(chart_path=built, found=True)
            if app.overrides or app.removes:
                raise ValueError("Git chart customizations require sbkube build first")
        return ChartPathResult(chart_path=source, found=True)
    except (OSError, ValueError) as error:
        message = f"Git chart unavailable: {error}"
        if output is not None:
            output.print_error(message)
        return ChartPathResult(chart_path=None, found=False, error_message=message)


def record_git_chart_build(
    app: HelmApp,
    app_name: str,
    repos_dir: Path,
    git_apps: dict | None,
    git_repos: dict | None,
    built: Path,
    initial_input: dict,
    app_config_dir: Path | None = None,
) -> None:
    _, current = _source(app, repos_dir, git_apps, git_repos, app_name, app_config_dir)
    if current != initial_input:
        raise ValueError("Git chart source changed during build")
    # Helm loads ordinary chart files into .Files; private metadata is never input.
    ignore = built / ".helmignore"
    content = ignore.read_text() if ignore.exists() else ""
    ignore.write_text(content.rstrip("\n") + "\n" + MARKER + "\n")
    value = {
        "schema": 1,
        "app": app_name,
        "input": current,
        "output_tree": chart_tree_digest(built),
    }
    marker = built / MARKER
    with marker.open("x") as target:
        marker.chmod(0o600)
        json.dump(value, target, sort_keys=True)
        target.write("\n")


def git_chart_input(
    app: HelmApp,
    repos_dir: Path,
    git_apps: dict | None,
    git_repos: dict | None,
    app_name: str | None = None,
    app_config_dir: Path | None = None,
) -> dict:
    return _source(app, repos_dir, git_apps, git_repos, app_name, app_config_dir)[1]
