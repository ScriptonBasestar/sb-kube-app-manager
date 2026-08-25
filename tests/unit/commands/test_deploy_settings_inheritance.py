"""Unit coverage for deploy's marker-bounded settings resolver."""

from pathlib import Path
from unittest.mock import patch

import yaml
from click.testing import CliRunner

from sbkube.commands.deploy import cmd


def _write(path: Path, settings: dict) -> None:
    path.write_text(yaml.safe_dump({"apiVersion": "sbkube/v1", "settings": settings, "apps": {}}))


@patch("sbkube.commands.deploy.resolve_cluster_config")
@patch("sbkube.commands.deploy.check_kubectl_installed_or_exit")
@patch("sbkube.commands.deploy.check_cluster_connectivity_or_exit")
def test_deploy_file_uses_marker_bounded_parent_settings(
    _connectivity, _check, resolve_cluster, tmp_path: Path
) -> None:
    (tmp_path / ".sbkube-workspace").write_text("anchors: {}\n")
    _write(tmp_path / "sbkube.yaml", {"kubeconfig": "/root", "kubeconfig_context": "root"})
    phase = tmp_path / "phase"
    phase.mkdir()
    _write(phase / "sbkube.yaml", {"kubeconfig_context": "phase"})
    app = phase / "app"
    app.mkdir()
    _write(app / "sbkube.yaml", {})
    resolve_cluster.return_value = ("/root", "phase")

    result = CliRunner().invoke(cmd, ["-f", str(app / "sbkube.yaml")], obj={"format": "human"})

    assert result.exit_code == 0
    sources = resolve_cluster.call_args.kwargs["sources"]
    assert (sources.kubeconfig, sources.kubeconfig_context) == ("/root", "phase")
