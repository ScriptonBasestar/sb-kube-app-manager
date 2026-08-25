"""Unit tests for marker-bounded workspace settings inheritance."""

from pathlib import Path

import pytest
import yaml

from sbkube.utils.settings_inheritance import (
    build_inherited_settings_chain,
    collect_parent_inherited_settings,
    extract_inherited_settings,
)


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


def test_explicit_empty_cluster_scalar_is_preserved() -> None:
    assert extract_inherited_settings({"settings": {"kubeconfig": ""}}) == {
        "kubeconfig": ""
    }


@pytest.mark.parametrize(
    "settings",
    [{"helm_repos": "not-a-mapping"}, []],
)
def test_invalid_settings_shapes_include_config_path(settings: object, tmp_path: Path) -> None:
    with pytest.raises(ValueError, match=str(tmp_path)):
        extract_inherited_settings({"settings": settings}, tmp_path)


def test_non_sbkube_parent_and_escaping_symlink_fail_closed(tmp_path: Path) -> None:
    (tmp_path / ".sbkube-workspace").write_text("anchors: {}\n")
    app = tmp_path / "app"
    app.mkdir()
    (tmp_path / "sbkube.yaml").write_text("kubeconfig: /legacy\n")
    with pytest.raises(ValueError, match="parent must be an sbkube API document"):
        collect_parent_inherited_settings(app)

    outside = tmp_path.parent / "outside-sbkube.yaml"
    outside.write_text("apiVersion: sbkube/v1\nsettings: {}\n")
    (tmp_path / "sbkube.yaml").unlink()
    (tmp_path / "sbkube.yaml").symlink_to(outside)
    with pytest.raises(ValueError, match="escapes workspace boundary"):
        collect_parent_inherited_settings(app)


def test_broken_parent_symlink_fails_closed_instead_of_root_fallback(tmp_path: Path) -> None:
    (tmp_path / ".sbkube-workspace").write_text("anchors: {}\n")
    _write_config(tmp_path / "sbkube.yaml", {"kubeconfig": "/root"})
    phase = tmp_path / "phase"
    phase.mkdir()
    (phase / "sbkube.yaml").symlink_to(tmp_path / "missing.yaml")
    app = phase / "app"
    app.mkdir()

    with pytest.raises(ValueError, match="phase/sbkube.yaml.*cannot resolve parent"):
        collect_parent_inherited_settings(app)


@pytest.mark.parametrize("kind", ["escaping", "broken", "non_sbkube"])
def test_intermediate_chain_fails_closed_at_workspace_boundary(
    kind: str, tmp_path: Path
) -> None:
    root = tmp_path / "workspace"
    root.mkdir()
    intermediate = root / "phase" / "sbkube.yaml"
    intermediate.parent.mkdir()
    if kind == "escaping":
        outside = tmp_path / "outside.yaml"
        _write_config(outside, {})
        intermediate.symlink_to(outside)
        match = "escapes workspace boundary"
    elif kind == "broken":
        intermediate.symlink_to(root / "missing.yaml")
        match = "cannot resolve intermediate"
    else:
        intermediate.write_text("settings: {}\n")
        match = "must be an sbkube API document"

    with pytest.raises(ValueError, match=match):
        build_inherited_settings_chain(
            {"settings": {}}, [intermediate], boundary=root
        )
