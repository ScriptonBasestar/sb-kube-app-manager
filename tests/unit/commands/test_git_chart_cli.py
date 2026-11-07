"""Exercise unified prepare/build/template with real file-only Git and Helm."""

import json
import os
import subprocess

import pytest
import yaml
from click.testing import CliRunner

from sbkube.cli import main
from sbkube.utils.git_chart import MARKER


@pytest.mark.integration
@pytest.mark.requires_helm
def test_unified_cli_renders_the_pinned_git_commit(tmp_path, monkeypatch):
    remote = tmp_path / "cli-remote"
    remote.mkdir()
    workspace = tmp_path / "cli-workspace"
    workspace.mkdir()
    monkeypatch.chdir(workspace)
    monkeypatch.setenv("GIT_CONFIG_NOSYSTEM", "1")
    monkeypatch.setenv("GIT_CONFIG_GLOBAL", os.devnull)
    monkeypatch.setenv("GIT_ALLOW_PROTOCOL", "file")
    monkeypatch.setenv("GIT_CONFIG_COUNT", "1")
    monkeypatch.setenv("GIT_CONFIG_KEY_0", f"url.{remote.as_uri()}.insteadOf")
    monkeypatch.setenv("GIT_CONFIG_VALUE_0", "https://fixture.invalid/supply.git")

    def git(*args):
        return subprocess.run(
            ["git", "-c", f"core.hooksPath={os.devnull}", *args],
            cwd=remote,
            text=True,
            capture_output=True,
            timeout=10,
            check=True,
        ).stdout.strip()

    git("init", "--initial-branch=main")
    chart = remote / "charts/demo"
    (chart / "templates").mkdir(parents=True)
    (chart / "Chart.yaml").write_text(
        "apiVersion: v2\nname: cli-fixture\nversion: 0.1.0\n"
    )
    (chart / "templates/configmap.yaml").write_text(
        "apiVersion: v1\nkind: ConfigMap\nmetadata:\n  name: supplied-by-cli\n"
        '  namespace: "{{ .Release.Namespace }}"\ndata:\n  mark: "{{ .Values.mark }}"\n'
    )

    def commit(mark):
        (chart / "values.yaml").write_text("mark: " + mark + "\n")
        git("add", ".")
        git(
            "-c",
            "user.name=Fixture",
            "-c",
            "user.email=fixture@example.invalid",
            "commit",
            "--no-gpg-sign",
            "-m",
            "fixture",
        )
        return git("rev-parse", "HEAD")

    first, second = commit("first"), commit("second")
    assert first != second
    kubeconfig = workspace / "kubeconfig"
    kubeconfig.write_text(
        yaml.safe_dump(
            {
                "apiVersion": "v1",
                "kind": "Config",
                "current-context": "fixture",
                "clusters": [
                    {"name": "fixture", "cluster": {"server": "https://127.0.0.1:1"}}
                ],
                "users": [{"name": "fixture", "user": {}}],
                "contexts": [
                    {
                        "name": "fixture",
                        "context": {"cluster": "fixture", "user": "fixture"},
                    }
                ],
            }
        )
    )
    monkeypatch.setenv("KUBECONFIG", str(kubeconfig))
    # Only connection preflight is replaced; actual Git, Helm, source/config
    # parsing, cache identity, materialization and rendering stay in the CLI.
    monkeypatch.setattr(
        "sbkube.cli.check_kubectl_installed_or_exit", lambda **_kwargs: None
    )
    config = workspace / "sbkube.yaml"
    config.write_text(
        yaml.safe_dump(
            {
                "apiVersion": "sbkube/v1",
                "metadata": {"name": "git-cli-fixture"},
                "settings": {
                    "cluster": "fixture",
                    "kubeconfig": str(kubeconfig),
                    "kubeconfig_context": "fixture",
                    "namespace": "fixture",
                    "timeout": "120s",
                    "git_repos": {
                        "supply": {
                            "url": "https://fixture.invalid/supply.git",
                            "branch": "main",
                        }
                    },
                },
                "apps": {
                    "checkout": {"type": "git", "repo": "supply", "ref": first},
                    "service": {
                        "type": "helm",
                        "chart": "${repos.checkout}/charts/demo",
                        "depends_on": ["checkout"],
                    },
                },
            },
            sort_keys=False,
        )
    )
    runner = CliRunner()
    for command in ("prepare", "build", "template"):
        result = runner.invoke(main, [command, "-f", str(config)])
        assert result.exit_code == 0, f"{command}: {result.output}\n{result.exception}"

    cache = workspace / ".sbkube"
    identity = json.loads(
        (cache / "repos/checkout/.git/sbkube-source.json").read_text()
    )
    assert identity["app"] == "checkout" and identity["head"] == first
    assert identity["source"]["revision"] == first
    assert not (cache / "repos/supply").exists()
    assert (cache / "build/service/values.yaml").read_text() == "mark: first\n"
    assert (cache / "build/service" / MARKER).is_file()
    assert not (cache / "build/service/.git").exists()
    rendered = [
        document
        for path in (cache / "rendered").rglob("*.yaml")
        for document in yaml.safe_load_all(path.read_text())
        if document
    ]
    matches = [
        doc
        for doc in rendered
        if doc.get("kind") == "ConfigMap"
        and doc.get("metadata", {}).get("name") == "supplied-by-cli"
    ]
    assert len(matches) == 1
    assert matches[0]["metadata"]["namespace"] == "fixture"
    assert matches[0]["data"] == {"mark": "first"}
    assert not (workspace / "sources.yaml").exists()
