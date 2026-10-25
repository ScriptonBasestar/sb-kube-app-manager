"""Real CLI wiring with mocked cluster operations and real local credentials."""

import base64
import json
import time
from pathlib import Path
from unittest.mock import patch

import pytest
import yaml
from click.testing import CliRunner

from sbkube.cli import main
from sbkube.models.sources_model import SourceScheme
from sbkube.utils.access_profile import current_profile
from sbkube.utils.cluster_config import resolve_cluster_config
from sbkube.utils.cluster_identity import cluster_identity


def _token(subject: str) -> str:
    payload = (
        base64.urlsafe_b64encode(
            json.dumps(
                {
                    "sub": f"system:serviceaccount:agent-access:{subject}",
                    "exp": time.time() + 3600,
                }
            ).encode()
        )
        .rstrip(b"=")
        .decode()
    )
    return "e30." + payload + ".signature"


@pytest.fixture
def env(tmp_path: Path) -> dict:
    for name, sa in (("readonly", "agent-readonly"), ("deployer", "sbkube-deployer")):
        (tmp_path / name).write_text(
            yaml.safe_dump(
                {
                    "apiVersion": "v1",
                    "kind": "Config",
                    "contexts": [
                        {"name": "home", "context": {"cluster": "home", "user": "sa"}}
                    ],
                    "clusters": [
                        {
                            "name": "home",
                            "cluster": {
                                "server": "https://home:6443",
                                "certificate-authority-data": "Q0E=",
                            },
                        }
                    ],
                    "users": [{"name": "sa", "user": {"token": _token(sa)}}],
                }
            )
        )
    config = tmp_path / "sbkube.yaml"
    data = {
        "apiVersion": "sbkube/v1",
        "metadata": {"name": "test"},
        "settings": {
            "cluster": "home",
            "kubeconfig": str(tmp_path / "removed-admin"),
            "kubeconfig_context": "home",
            "access": {
                "readonly": {"kubeconfig": str(tmp_path / "readonly")},
                "deployer": {"kubeconfig": str(tmp_path / "deployer")},
            },
        },
        "apps": {"nginx": {"type": "helm", "chart": "repo/nginx", "context": "home"}},
    }
    config.write_text(yaml.safe_dump(data))
    build = tmp_path / ".sbkube" / "build" / "nginx"
    build.mkdir(parents=True)
    (build / "Chart.yaml").write_text("apiVersion: v2\nname: nginx\nversion: 1.0.0\n")
    return {
        "root": tmp_path,
        "config": config,
        "data": data,
        "deployer": tmp_path / "deployer",
        "readonly": tmp_path / "readonly",
    }


@pytest.fixture(autouse=True)
def client_tools():
    with (
        patch("sbkube.cli.check_kubectl_installed_or_exit"),
        patch("sbkube.cli.check_helm_installed_or_exit"),
    ):
        yield


def test_upgrade_argv_uses_deployer(env: dict) -> None:
    with (
        patch("sbkube.commands.upgrade.check_helm_installed_or_exit"),
        patch(
            "sbkube.commands.upgrade.run_command", return_value=(0, "upgraded", "")
        ) as run,
    ):
        result = CliRunner().invoke(main, ["upgrade", "-f", str(env["config"])])
    assert result.exit_code == 0, result.output
    command = run.call_args.args[0]
    assert command[command.index("--kubeconfig") + 1] == str(env["deployer"])
    assert command[command.index("--kube-context") + 1] == "home"
    assert current_profile() is None


def test_delete_app_context_cannot_drop_profile_kubeconfig(env: dict) -> None:
    with (
        patch("sbkube.commands.delete.check_helm_installed_or_exit"),
        patch(
            "sbkube.commands.delete.get_installed_charts", return_value={"nginx": {}}
        ) as charts,
        patch(
            "sbkube.commands.delete.run_command", return_value=(0, "deleted", "")
        ) as run,
    ):
        result = CliRunner().invoke(main, ["delete", "-f", str(env["config"])])
    assert result.exit_code == 0, result.output
    assert charts.call_args.kwargs["kubeconfig"] == str(env["deployer"])
    command = run.call_args.args[0]
    assert command[command.index("--kubeconfig") + 1] == str(env["deployer"])


def test_delete_foreign_app_context_refused_before_cluster_command(env: dict) -> None:
    env["data"]["apps"]["nginx"]["context"] = "other"
    env["config"].write_text(yaml.safe_dump(env["data"]))
    with (
        patch("sbkube.commands.delete.check_helm_installed_or_exit"),
        patch("sbkube.commands.delete.get_installed_charts") as charts,
        patch("sbkube.commands.delete.run_command") as run,
    ):
        result = CliRunner().invoke(main, ["delete", "-f", str(env["config"])])
    assert result.exit_code != 0
    charts.assert_not_called()
    run.assert_not_called()


def test_status_unified_config_uses_readonly_and_separate_cache(env: dict) -> None:
    with (
        patch("sbkube.commands.status._display_status"),
        patch("sbkube.commands.status._collect_and_cache"),
        patch("sbkube.commands.status.ClusterCache") as cache,
        patch("sbkube.commands.status.ClusterStatusCollector") as collector,
    ):
        cache.return_value.is_valid.return_value = False
        result = CliRunner().invoke(main, ["status", "--base-dir", str(env["root"])])
    assert result.exit_code == 0, result.output
    assert collector.call_args.kwargs == {
        "kubeconfig": str(env["readonly"]),
        "context": "home",
    }
    assert "/cluster_status/access/" in str(cache.call_args.kwargs["cache_dir"])


def test_deploy_records_selected_immutable_identity(env: dict) -> None:
    env["data"]["apps"] = {"no-op": {"type": "noop"}}
    env["config"].write_text(yaml.safe_dump(env["data"]))
    with (
        patch("sbkube.commands.deploy.DeploymentRecorder") as recorder,
        patch("sbkube.commands.deploy.check_kubectl_installed_or_exit"),
        patch("sbkube.commands.deploy.check_helm_installed_or_exit"),
        patch("sbkube.commands.deploy.check_cluster_connectivity_or_exit"),
    ):
        result = CliRunner().invoke(main, ["deploy", "-f", str(env["config"])])
    assert result.exit_code == 0, result.output
    snapshot = recorder.call_args.kwargs["sources_data"]
    assert snapshot["kubeconfig"] == str(env["deployer"])
    assert snapshot["cluster_identity"] == cluster_identity(env["deployer"], "home")
    assert "users" not in snapshot["cluster_identity"]


def test_apply_scope_reaches_execution_and_checks_source_context(env: dict) -> None:
    def execute(**kwargs):
        assert current_profile() is not None
        assert resolve_cluster_config(
            None,
            None,
            SourceScheme(
                kubeconfig=str(env["root"] / "removed-admin"), kubeconfig_context="home"
            ),
        ) == (str(env["deployer"]), "home")
        from sbkube.utils.access_profile import AccessProfileError

        with pytest.raises(AccessProfileError, match="context"):
            resolve_cluster_config(
                str(env["deployer"]), "home", SourceScheme(kubeconfig_context="other")
            )
        return True

    with patch(
        "sbkube.commands.apply._execute_apps_deployment", side_effect=execute
    ) as execution:
        result = CliRunner().invoke(main, ["apply", "-f", str(env["config"])])
    assert result.exit_code == 0, result.output
    execution.assert_called_once()
    assert current_profile() is None
