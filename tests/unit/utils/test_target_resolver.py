"""Unit tests for target resolver utility."""

from pathlib import Path

import pytest

from sbkube.utils.target_resolver import resolve_target


def test_resolve_target_prefers_target_local_config(tmp_path: Path) -> None:
    workspace = tmp_path / "project"
    workspace.mkdir()
    config = workspace / "sbkube.yaml"
    config.write_text("apiVersion: sbkube/v1\nmetadata:\n  name: test\n")

    resolved = resolve_target(str(workspace), base_dir=tmp_path)

    assert resolved.workspace_root == workspace
    assert resolved.config_file == config
    assert resolved.scope_path is None


def test_resolve_target_searches_upward_and_sets_scope(tmp_path: Path) -> None:
    workspace = tmp_path / "project"
    target = workspace / "ph1" / "app1"
    target.mkdir(parents=True)
    config = workspace / "sbkube.yaml"
    config.write_text("apiVersion: sbkube/v1\nmetadata:\n  name: test\n")

    resolved = resolve_target(str(target), base_dir=tmp_path)

    assert resolved.workspace_root == workspace
    assert resolved.config_file == config
    assert resolved.scope_path == "ph1/app1"


def test_resolve_target_with_file_uses_file_parent_for_scope(tmp_path: Path) -> None:
    workspace = tmp_path / "project"
    nested = workspace / "ph1" / "app1"
    nested.mkdir(parents=True)
    config = workspace / "sbkube.yaml"
    config.write_text("apiVersion: sbkube/v1\nmetadata:\n  name: test\n")

    resolved = resolve_target("ph1/app1", str(config), base_dir=tmp_path)

    assert resolved.workspace_root == workspace
    assert resolved.config_file == config
    assert resolved.scope_path == "ph1/app1"


def test_resolve_target_with_file_rejects_target_outside_workspace(
    tmp_path: Path,
) -> None:
    workspace = tmp_path / "project"
    workspace.mkdir()
    outside = tmp_path / "outside"
    outside.mkdir()
    config = workspace / "sbkube.yaml"
    config.write_text("apiVersion: sbkube/v1\nmetadata:\n  name: test\n")

    with pytest.raises(ValueError, match="inside the workspace"):
        resolve_target(str(outside), str(config), base_dir=tmp_path)


def test_resolve_target_without_target_detects_current_directory(tmp_path: Path) -> None:
    config = tmp_path / "sbkube.yaml"
    config.write_text("apiVersion: sbkube/v1\nmetadata:\n  name: test\n")

    resolved = resolve_target(None, None, base_dir=tmp_path)

    assert resolved.workspace_root == tmp_path
    assert resolved.config_file == config
    assert resolved.scope_path is None
