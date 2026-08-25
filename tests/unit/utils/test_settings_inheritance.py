"""Unit tests for marker-bounded workspace settings inheritance."""

from pathlib import Path

import pytest
import yaml

from sbkube.utils.settings_inheritance import collect_parent_inherited_settings


def _write_config(path: Path, settings: dict) -> None:
    path.write_text(yaml.safe_dump({"apiVersion": "sbkube/v1", "settings": settings}))


def test_collects_root_phase_and_keeps_local_for_caller(tmp_path: Path) -> None:
    """Parents merge shallow-to-deep; callers can merge the local settings last."""
    (tmp_path / ".sbkube-workspace").write_text("anchors: {}\n")
    _write_config(
        tmp_path / "sbkube.yaml",
        {"kubeconfig": "/root", "kubeconfig_context": "root", "helm_repos": {"base": "https://base"}},
    )
    phase = tmp_path / "phase"
    phase.mkdir()
    _write_config(phase / "sbkube.yaml", {"kubeconfig_context": "phase", "helm_repos": {"phase": "https://phase"}})
    app = phase / "app"
    app.mkdir()
    _write_config(app / "sbkube.yaml", {"kubeconfig_context": "local"})

    inherited = collect_parent_inherited_settings(app)

    assert inherited == {
        "kubeconfig": "/root",
        "kubeconfig_context": "phase",
        "helm_repos": {"base": "https://base", "phase": "https://phase"},
    }


def test_does_not_absorb_config_above_workspace_marker(tmp_path: Path) -> None:
    """A parent outside .sbkube-workspace is not a valid settings source."""
    _write_config(tmp_path / "sbkube.yaml", {"kubeconfig": "/outside", "kubeconfig_context": "outside"})
    workspace = tmp_path / "workspace"
    workspace.mkdir()
    (workspace / ".sbkube-workspace").write_text("anchors: {}\n")
    _write_config(workspace / "sbkube.yaml", {"kubeconfig": "/inside", "kubeconfig_context": "inside"})
    app = workspace / "app"
    app.mkdir()

    assert collect_parent_inherited_settings(app) == {
        "kubeconfig": "/inside", "kubeconfig_context": "inside"
    }


def test_no_marker_means_no_implicit_parent_inheritance(tmp_path: Path) -> None:
    _write_config(tmp_path / "sbkube.yaml", {"kubeconfig": "/outside", "kubeconfig_context": "outside"})
    app = tmp_path / "app"
    app.mkdir()

    assert collect_parent_inherited_settings(app) == {}


def test_invalid_existing_parent_fails_closed(tmp_path: Path) -> None:
    (tmp_path / ".sbkube-workspace").write_text("anchors: {}\n")
    (tmp_path / "sbkube.yaml").write_text("settings: [not-a-mapping\n")
    app = tmp_path / "app"
    app.mkdir()

    with pytest.raises(Exception):
        collect_parent_inherited_settings(app)
