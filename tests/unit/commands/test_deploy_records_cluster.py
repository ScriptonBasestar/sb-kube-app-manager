"""Deploy records the cluster it actually used (issue #6).

Rollback pins helm/kubectl to the kubeconfig and context in the deployment's
sources snapshot, so deploy must store the values resolve_cluster_config chose
(--kubeconfig/--context override sources.yaml), not the sources.yaml fields.
"""

from unittest.mock import MagicMock, patch

import yaml
from click.testing import CliRunner

from sbkube.cli import main


@patch("sbkube.commands.deploy.DeploymentRecorder")
@patch("sbkube.commands.deploy.run_command", return_value=(0, "deployed", ""))
@patch("sbkube.commands.deploy.check_kubectl_installed_or_exit")
@patch("sbkube.commands.deploy.check_helm_installed_or_exit")
@patch("sbkube.commands.deploy.resolve_cluster_config")
@patch("sbkube.commands.deploy.check_cluster_connectivity_or_exit")
def test_deploy_records_resolved_cluster_over_sources_yaml(
    mock_cluster_check,
    mock_resolve_cluster,
    mock_helm_check,
    mock_kubectl_check,
    mock_run_command,
    mock_recorder: MagicMock,
    tmp_path,
) -> None:
    mock_resolve_cluster.return_value = ("/override/kubeconfig", "override-context")
    (tmp_path / "sources.yaml").write_text(
        "kubeconfig: /sources/kubeconfig\n"
        "kubeconfig_context: sources-context\n"
        "cluster: test-cluster\n"
    )
    config_dir = tmp_path / "config"
    config_dir.mkdir(exist_ok=True)
    (config_dir / "config.yaml").write_text(
        yaml.dump(
            {
                "namespace": "default",
                "apps": {
                    "nginx": {
                        "type": "helm",
                        "chart": "bitnami/nginx",
                        "version": "15.0.0",
                    }
                },
            }
        )
    )
    build_dir = tmp_path / ".sbkube" / "build" / "nginx"
    build_dir.mkdir(parents=True)
    (build_dir / "Chart.yaml").write_text("name: nginx\nversion: 15.0.0")
    (build_dir / "values.yaml").write_text("replicaCount: 1")

    result = CliRunner().invoke(main, ["deploy", str(config_dir)])

    assert result.exit_code == 0, result.output
    sources_data = mock_recorder.call_args.kwargs["sources_data"]
    assert sources_data["kubeconfig"] == "/override/kubeconfig"
    assert sources_data["kubeconfig_context"] == "override-context"
    assert sources_data["cluster"] == "test-cluster"
