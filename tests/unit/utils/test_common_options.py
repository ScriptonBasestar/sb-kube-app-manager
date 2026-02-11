"""Tests for common target/file option path resolution."""

from pathlib import Path

from sbkube.utils.common_options import resolve_command_paths


def test_resolve_command_paths_legacy_mode(tmp_path: Path) -> None:
    resolved = resolve_command_paths(
        target=None,
        config_file=None,
        base_dir=str(tmp_path),
        app_config_dir_name="config",
        config_file_name="config.yaml",
        sources_file_name="sources.yaml",
    )

    assert resolved.base_dir == tmp_path
    assert resolved.app_config_dir_name == "config"
    assert resolved.config_file_name == "config.yaml"
    assert resolved.sources_file_name == "sources.yaml"


def test_resolve_command_paths_target_mode(tmp_path: Path) -> None:
    app_dir = tmp_path / "app"
    app_dir.mkdir(parents=True)
    config = app_dir / "sbkube.yaml"
    config.write_text("apiVersion: sbkube/v1\nmetadata:\n  name: app\n")

    resolved = resolve_command_paths(
        target=str(app_dir),
        config_file=None,
        base_dir=".",
        app_config_dir_name=None,
        config_file_name="config.yaml",
        sources_file_name="sources.yaml",
    )

    assert resolved.base_dir == app_dir
    assert resolved.app_config_dir_name == "."
    assert resolved.config_file_name == "sbkube.yaml"
    assert resolved.sources_file_name == "sbkube.yaml"


def test_resolve_command_paths_file_and_scope(tmp_path: Path) -> None:
    workspace = tmp_path / "workspace"
    target = workspace / "p1" / "app1"
    target.mkdir(parents=True)
    config = workspace / "sbkube.yaml"
    config.write_text("apiVersion: sbkube/v1\nmetadata:\n  name: workspace\n")

    resolved = resolve_command_paths(
        target="p1/app1",
        config_file=str(config),
        base_dir=".",
        app_config_dir_name=None,
        config_file_name="config.yaml",
        sources_file_name="sources.yaml",
    )

    assert resolved.base_dir == workspace
    assert resolved.app_config_dir_name == "p1/app1"
    assert resolved.config_file_name == "sbkube.yaml"
    assert resolved.sources_file_name == "sbkube.yaml"
