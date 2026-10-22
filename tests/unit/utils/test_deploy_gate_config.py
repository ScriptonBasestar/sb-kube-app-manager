"""Discovery and precedence of ``sbkube-gate.yaml`` files."""

from pathlib import Path

import pytest

from sbkube.exceptions import ConfigurationError
from sbkube.utils.deploy_gate_config import (
    GATE_FILE_NAME,
    find_gate_files,
    resolve_gate,
)


def _write_gate(directory: Path, body: str) -> Path:
    directory.mkdir(parents=True, exist_ok=True)
    path = directory / GATE_FILE_NAME
    path.write_text(body, encoding="utf-8")
    return path


def _global(directory: Path, mode: str = "enforce") -> Path:
    return _write_gate(directory, f'deploy_gate:\n  command: "true"\n  mode: {mode}\n')


def _workspace(path: Path) -> Path:
    path.mkdir(parents=True, exist_ok=True)
    (path / ".sbkube-workspace").write_text("anchors: {}\n", encoding="utf-8")
    return path


def test_individual_gate_file_without_global_is_an_error(tmp_path: Path) -> None:
    root = _workspace(tmp_path / "ws")
    _write_gate(root / "p1", "deploy_gate:\n  mode: enforce\n")

    with pytest.raises(ConfigurationError, match="needs a global"):
        resolve_gate(*find_gate_files(root / "p1"))


def test_gated_repository_below_does_not_gate_an_ungated_one(tmp_path: Path) -> None:
    outer = tmp_path / "outer"
    (outer / ".git").mkdir(parents=True)
    vendored = outer / "vendor" / "other"
    (vendored / ".git").mkdir(parents=True)
    _global(vendored)

    assert resolve_gate(*find_gate_files(outer)) is None


def test_phase_with_its_own_repository_still_tightens(tmp_path: Path) -> None:
    root = _workspace(tmp_path / "ws")
    _global(root, mode="warn")
    phase = root / "p1"
    (phase / ".git").mkdir(parents=True)
    _write_gate(phase, "deploy_gate:\n  mode: enforce\n")

    gate = resolve_gate(*find_gate_files(root))

    assert gate is not None and gate.mode == "enforce"


def test_nested_workspace_gate_below_target_fails_closed(tmp_path: Path) -> None:
    root = _workspace(tmp_path / "ws")
    _global(root, mode="warn")
    _global(_workspace(root / "nested"))

    with pytest.raises(ConfigurationError, match="may only be set in"):
        resolve_gate(*find_gate_files(root))


def test_symlinked_phase_in_scope_is_searched_once(tmp_path: Path) -> None:
    root = _workspace(tmp_path / "ws")
    _global(root, mode="warn")
    real_phase = root / "shared" / "p1"
    _write_gate(real_phase, "deploy_gate:\n  mode: enforce\n")
    (root / "apps").mkdir()
    (root / "apps" / "p1").symlink_to(real_phase, target_is_directory=True)
    (real_phase / "loop").symlink_to(root, target_is_directory=True)

    gate = resolve_gate(*find_gate_files(root / "apps"))

    assert gate is not None and gate.mode == "enforce"


def test_symlink_out_of_scope_is_not_followed(tmp_path: Path) -> None:
    root = _workspace(tmp_path / "ws")
    _global(root, mode="warn")
    elsewhere = tmp_path / "elsewhere"
    _global(elsewhere)
    (root / "link").symlink_to(elsewhere, target_is_directory=True)

    gate = resolve_gate(*find_gate_files(root))

    assert gate is not None and gate.mode == "warn"


def test_gate_file_outside_the_repository_is_ignored(tmp_path: Path) -> None:
    _write_gate(tmp_path, "not: [valid")
    repo = tmp_path / "repo"
    (repo / ".git").mkdir(parents=True)
    _global(repo)

    global_source, individuals, _ = find_gate_files(repo / "app")

    assert global_source is not None and global_source.path == repo / GATE_FILE_NAME
    assert individuals == ()


def test_only_the_global_command_runs(tmp_path: Path) -> None:
    root = _workspace(tmp_path / "ws")
    _global(root, mode="warn")
    _write_gate(root / "p1", "deploy_gate:\n  mode: enforce\n")

    gate = resolve_gate(*find_gate_files(root))

    assert gate is not None
    assert gate.mode == "enforce"
    assert gate.command == "true"
    assert gate.command_dir == root
