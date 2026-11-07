"""Prepared Git -> Helm boundary tests; Git transport is restricted to local files."""

import json
import subprocess
from unittest.mock import MagicMock

import pytest
import yaml

from sbkube.commands.build import build_helm_app
from sbkube.commands.prepare import prepare_git_app
from sbkube.commands.template import template_helm_app
from sbkube.models.config_model import GitApp, HelmApp
from sbkube.models.sources_model import GitRepoScheme
from sbkube.utils.git_chart import MARKER, resolve_git_chart_path
from sbkube.utils.output_manager import OutputManager


@pytest.fixture
def supply(tmp_path, monkeypatch):
    remote = tmp_path / "remote"
    remote.mkdir()
    monkeypatch.setenv("GIT_CONFIG_NOSYSTEM", "1")
    monkeypatch.setenv("GIT_CONFIG_GLOBAL", "/dev/null")
    monkeypatch.setenv("GIT_ALLOW_PROTOCOL", "file")
    monkeypatch.setenv("GIT_CONFIG_COUNT", "1")
    monkeypatch.setenv("GIT_CONFIG_KEY_0", f"url.{remote.as_uri()}.insteadOf")
    monkeypatch.setenv("GIT_CONFIG_VALUE_0", "https://fixture.invalid/source.git")

    def git(*args):
        return subprocess.check_output(
            ["git", "-c", "core.hooksPath=/dev/null", *args],
            cwd=remote,
            text=True,
            timeout=10,
        ).strip()

    git("init", "--initial-branch=main")
    chart = remote / "charts/app"
    (chart / "templates").mkdir(parents=True)
    (chart / "Chart.yaml").write_text("apiVersion: v2\nname: fixture\nversion: 0.1.0\n")
    (chart / "templates/cm.yaml").write_text(
        'apiVersion: v1\nkind: ConfigMap\nmetadata:\n  name: fixture\ndata:\n  mark: "{{ .Values.mark }}"\n  provenance: {{ .Files.Get ".sbkube-git-chart.json" | quote }}\n'
    )

    def commit():
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

    (chart / "values.yaml").write_text("mark: first\n")
    first = commit()
    (chart / "values.yaml").write_text("mark: second\n")
    second = commit()
    state = {
        "root": tmp_path,
        "remote": remote,
        "chart": chart,
        "commit": commit,
        "first": first,
        "second": second,
        "repos": tmp_path / ".sbkube/repos",
        "charts": tmp_path / ".sbkube/charts",
        "build": tmp_path / ".sbkube/build",
        "rendered": tmp_path / ".sbkube/rendered",
        "apps": {},
        "aliases": {
            "source": GitRepoScheme(
                url="https://fixture.invalid/source.git", branch="main"
            )
        },
        "output": MagicMock(spec=OutputManager),
        "helm": HelmApp(
            type="helm", chart="${repos.checkout}/charts/app", namespace="fixture"
        ),
    }
    state["build"].mkdir(parents=True)
    state["rendered"].mkdir(parents=True)

    def prepare(revision=first, force=False):
        app = GitApp(type="git", repo="source", ref=revision)
        state["apps"]["checkout"] = app
        assert prepare_git_app(
            "checkout",
            app,
            tmp_path,
            state["repos"],
            tmp_path / "unused.yaml",
            state["output"],
            force=force,
            git_repos=state["aliases"],
        )

    state["prepare"] = prepare
    return state


def resolve(s, chart=None):
    return resolve_git_chart_path(
        chart or s["helm"],
        "service",
        s["repos"],
        s["apps"],
        s["aliases"],
        s["build"],
        app_config_dir=s["root"],
    )


def build(s):
    return build_helm_app(
        "service",
        s["helm"],
        s["root"],
        s["charts"],
        s["build"],
        s["root"],
        s["output"],
        git_apps=s["apps"],
        git_repos=s["aliases"],
    )


def test_model_classifies_git_chart_and_schema_preserves_omitted_branch():
    assert not HelmApp(type="helm", chart="${repos.source}/chart").is_remote_chart()
    assert GitApp(type="git", repo="source").branch is None
    assert GitApp.model_json_schema()["properties"]["branch"]["default"] is None


def test_override_content_change_requires_rebuild(supply):
    s = supply
    s["prepare"]()
    s["helm"].overrides = ["values.yaml"]
    overrides = s["root"] / "overrides/service"
    overrides.mkdir(parents=True)
    (overrides / "values.yaml").write_text("mark: override\n")
    assert build(s)
    assert resolve(s).found
    (overrides / "values.yaml").write_text("mark: changed\n")
    assert not resolve(s).found
    assert build(s)
    assert resolve(s).found
    assert (s["build"] / "service/values.yaml").read_text() == "mark: changed\n"


@pytest.mark.integration
def test_real_git_build_and_helm_template_use_pinned_older_commit(supply):
    s = supply
    s["prepare"]()
    assert build(s)
    built = s["build"] / "service"
    assert (built / MARKER).stat().st_mode & 0o777 == 0o600
    assert not (built / ".git").exists()
    assert (built / "values.yaml").read_text() == "mark: first\n"
    assert template_helm_app(
        "service",
        s["helm"],
        s["root"],
        s["charts"],
        s["build"],
        s["root"],
        s["rendered"],
        s["output"],
        git_apps=s["apps"],
        git_repos=s["aliases"],
    ), s["output"].mock_calls
    rendered = "\n".join(p.read_text() for p in s["rendered"].rglob("*.yaml"))
    assert yaml.safe_load(rendered)["data"]["mark"] == "first"
    assert yaml.safe_load(rendered)["data"]["provenance"] == ""


def test_new_declared_ref_cannot_reuse_old_cache_or_build(supply):
    s = supply
    s["prepare"]()
    assert build(s)
    s["apps"]["checkout"] = GitApp(type="git", repo="source", ref=s["second"])
    assert not resolve(s).found
    s["prepare"](s["second"], force=True)
    assert not resolve(s).found  # Old materialization is stale even after prepare.
    assert build(s)
    assert resolve(s).found
    assert (s["build"] / "service/values.yaml").read_text() == "mark: second\n"


def test_modified_or_unknown_build_is_preserved(supply):
    s = supply
    s["prepare"]()
    assert build(s)
    path = s["build"] / "service/values.yaml"
    path.write_text("operator data\n")
    assert not resolve(s).found
    assert not build(s)
    assert path.read_text() == "operator data\n"


@pytest.mark.parametrize("suffix", ["../app", ".git", "charts/missing", "charts//app"])
def test_invalid_or_missing_chart_path_is_rejected(supply, suffix):
    s = supply
    s["prepare"]()
    assert not resolve(
        s, HelmApp(type="helm", chart="${repos.checkout}/" + suffix)
    ).found


@pytest.mark.parametrize("directory", [False, True])
def test_child_symlink_escape_is_rejected_before_copy(supply, directory):
    s = supply
    outside = s["root"] / "outside"
    if directory:
        outside.mkdir()
        (outside / "private").write_text("not chart input")
    else:
        outside.write_text("not chart input")
    (s["chart"] / "escape").symlink_to(outside, target_is_directory=directory)
    s["prepare"](s["commit"]())
    assert not build(s)
    assert not (s["build"] / "service").exists()


def test_ignored_files_cannot_enter_commit_pinned_chart(supply):
    s = supply
    (s["chart"] / ".gitignore").write_text("private.env\n")
    s["prepare"](s["commit"]())
    secret = s["repos"] / "checkout/charts/app/private.env"
    secret.write_text("operator-owned ignored data")
    assert not build(s)
    assert secret.read_text() == "operator-owned ignored data"


def test_bounded_chart_and_unowned_build_fail_closed(supply, monkeypatch):
    s = supply
    s["prepare"]()
    monkeypatch.setattr("sbkube.utils.git_chart.MAX_BYTES", 1)
    assert not resolve(s).found
    monkeypatch.setattr("sbkube.utils.git_chart.MAX_BYTES", 64 * 1024 * 1024)
    target = s["build"] / "service"
    target.mkdir()
    (target / "operator-file").write_text("keep")
    assert not build(s)
    assert (target / "operator-file").read_text() == "keep"


def test_build_provenance_contains_no_source_url(supply):
    s = supply
    s["prepare"]()
    assert build(s)
    raw = (s["build"] / "service" / MARKER).read_text()
    assert "https://" not in raw
    assert json.loads(raw)["app"] == "service"
