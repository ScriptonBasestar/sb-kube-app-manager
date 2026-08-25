"""Unit coverage for direct unified-config prepare inheritance."""

from pathlib import Path
from unittest.mock import patch

import pytest
import yaml
from click.testing import CliRunner

from sbkube.commands.prepare import cmd


def _write_config(path: Path, settings: dict) -> None:
    path.write_text(
        yaml.safe_dump({"apiVersion": "sbkube/v1", "settings": settings, "apps": {}})
    )


@patch("sbkube.commands.prepare.resolve_cluster_config")
@patch("sbkube.commands.prepare.check_helm_installed_or_exit")
def test_prepare_file_inherits_workspace_settings_with_local_override(
    _check_helm, resolve_cluster, tmp_path: Path
) -> None:
    """prepare -f app/sbkube.yaml resolves root -> phase -> app settings."""
    (tmp_path / ".sbkube-workspace").write_text("anchors: {}\n")
    _write_config(
        tmp_path / "sbkube.yaml",
        {"kubeconfig": "/root", "kubeconfig_context": "root"},
    )
    phase = tmp_path / "phase"
    phase.mkdir()
    _write_config(phase / "sbkube.yaml", {"kubeconfig_context": "phase"})
    app = phase / "app"
    app.mkdir()
    _write_config(
        app / "sbkube.yaml",
        {"kubeconfig": "/app", "kubeconfig_context": "app"},
    )
    resolve_cluster.return_value = ("/app", "app")

    result = CliRunner().invoke(
        cmd,
        ["-f", str(app / "sbkube.yaml")],
        obj={"format": "human"},
    )

    assert result.exit_code == 0
    sources = resolve_cluster.call_args.kwargs["sources"]
    assert sources.kubeconfig == "/app"
    assert sources.kubeconfig_context == "app"


@patch("sbkube.commands.prepare.resolve_cluster_config")
@patch("sbkube.commands.prepare.check_helm_installed_or_exit")
def test_prepare_file_inherits_parent_only_cluster_settings(
    _check_helm, resolve_cluster, tmp_path: Path
) -> None:
    """An app with no cluster fields receives root kubeconfig and phase context."""
    (tmp_path / ".sbkube-workspace").write_text("anchors: {}\n")
    _write_config(tmp_path / "sbkube.yaml", {"kubeconfig": "/root"})
    phase = tmp_path / "phase"
    phase.mkdir()
    _write_config(phase / "sbkube.yaml", {"kubeconfig_context": "phase"})
    app = phase / "app"
    app.mkdir()
    _write_config(app / "sbkube.yaml", {})
    resolve_cluster.return_value = ("/root", "phase")

    result = CliRunner().invoke(cmd, ["-f", str(app / "sbkube.yaml")], obj={"format": "human"})

    assert result.exit_code == 0
    sources = resolve_cluster.call_args.kwargs["sources"]
    assert (sources.kubeconfig, sources.kubeconfig_context) == ("/root", "phase")


@pytest.mark.parametrize("level, field", [("phase", "kubeconfig_context"), ("app", "kubeconfig")])
@patch("sbkube.commands.prepare.check_helm_installed_or_exit")
def test_prepare_explicit_empty_cluster_field_fails_without_parent_fallback(
    _check_helm, level: str, field: str, tmp_path: Path
) -> None:
    (tmp_path / ".sbkube-workspace").write_text("anchors: {}\n")
    _write_config(tmp_path / "sbkube.yaml", {"kubeconfig": "/root", "kubeconfig_context": "root"})
    phase = tmp_path / "phase"
    phase.mkdir()
    _write_config(phase / "sbkube.yaml", {field: ""} if level == "phase" else {})
    app = phase / "app"
    app.mkdir()
    _write_config(app / "sbkube.yaml", {field: ""} if level == "app" else {})

    result = CliRunner().invoke(cmd, ["-f", str(app / "sbkube.yaml")], obj={"format": "human"})

    assert result.exit_code != 0
    assert field in result.output
