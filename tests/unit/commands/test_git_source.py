"""Local-only Git source identity and failure preservation regressions."""

import os
import subprocess
from pathlib import Path
from unittest.mock import Mock

import pytest

from sbkube.models.config_model import GitApp
from sbkube.utils import git_source
from sbkube.utils.git_source import (
    GitSourceError,
    prepare_git_source,
    read_prepared_git_source,
    resolve_git_source,
)

URL = "https://fixture.invalid/source.git"


def git(path, *args):
    return subprocess.run(
        ["git", "-C", str(path), *args],
        capture_output=True,
        text=True,
        timeout=10,
        check=True,
    ).stdout.strip()


@pytest.fixture
def origin(tmp_path, monkeypatch):
    monkeypatch.setenv("GIT_CONFIG_GLOBAL", os.devnull)
    monkeypatch.setenv("GIT_CONFIG_NOSYSTEM", "1")
    monkeypatch.setenv("GIT_ALLOW_PROTOCOL", "file")
    for name, value in (
        ("GIT_AUTHOR_NAME", "Fixture"),
        ("GIT_COMMITTER_NAME", "Fixture"),
        ("GIT_AUTHOR_EMAIL", "fixture@example.invalid"),
        ("GIT_COMMITTER_EMAIL", "fixture@example.invalid"),
    ):
        monkeypatch.setenv(name, value)
    source = tmp_path / "origin"
    source.mkdir()
    git(source, "init", "--initial-branch=main")
    (source / "Chart.yaml").write_text("version: 1\n")
    git(source, "add", ".")
    git(source, "commit", "--no-gpg-sign", "-m", "first")
    first = git(source, "rev-parse", "HEAD")
    git(source, "tag", "v1")
    git(source, "checkout", "-b", "release")
    (source / "Chart.yaml").write_text("version: 2\n")
    git(source, "commit", "--no-gpg-sign", "-am", "second")
    second = git(source, "rev-parse", "HEAD")
    git(source, "checkout", "main")
    urls = [
        URL,
        "ssh://fixture.invalid/source.git",
        "git://fixture.invalid/source.git",
        "git@fixture.invalid:source.git",
    ]
    monkeypatch.setenv("GIT_CONFIG_COUNT", str(len(urls)))
    for index, url in enumerate(urls):
        monkeypatch.setenv(
            f"GIT_CONFIG_KEY_{index}", f"url.{source.as_uri()}.insteadOf"
        )
        monkeypatch.setenv(f"GIT_CONFIG_VALUE_{index}", url)
    return source, first, second


@pytest.mark.parametrize(
    ("fields", "alias_branch", "revision", "kind"),
    [
        ({"ref": "v1", "branch": "other"}, "release", "v1", "ref"),
        ({"branch": "other"}, "release", "other", "branch"),
        ({}, "release", "release", "branch"),
        ({}, None, "main", "branch"),
    ],
)
def test_revision_precedence(fields, alias_branch, revision, kind):
    app = GitApp(type="git", repo="source", **fields)
    spec = resolve_git_source(
        "chart", app, {"source": {"url": URL, "branch": alias_branch}}
    )
    assert spec == {"url": URL, "revision": revision, "kind": kind}


@pytest.mark.parametrize(
    "url",
    [
        URL,
        "ssh://fixture.invalid/source.git",
        "git://fixture.invalid/source.git",
        "git@fixture.invalid:source.git",
    ],
)
def test_direct_protocols_and_pinned_sha_clone(origin, tmp_path, url):
    _source, first, _second = origin
    app = GitApp(type="git", repo=url, ref=first, branch="does-not-exist")
    repos = tmp_path / "git-cache"
    identity = prepare_git_source("chart", app, {}, repos)
    assert identity["head"] == first
    assert git(repos / "chart", "rev-parse", "HEAD") == first
    detached = subprocess.run(
        ["git", "-C", str(repos / "chart"), "symbolic-ref", "-q", "HEAD"],
        capture_output=True,
        timeout=10,
        check=False,
    )
    assert detached.returncode == 1
    marker = repos / "chart/.git/sbkube-source.json"
    assert marker.stat().st_mode & 0o777 == 0o600
    assert read_prepared_git_source("chart", app, {}, repos) == identity


def test_alias_apps_are_separate_and_legacy_alias_untouched(origin, tmp_path):
    _source, first, second = origin
    repos = tmp_path / "git-cache"
    legacy = repos / "source"
    legacy.mkdir(parents=True)
    (legacy / "user-file").write_text("retain")
    sources = {"source": {"url": URL, "branch": "release"}}
    prepare_git_source(
        "old", GitApp(type="git", repo="source", ref=first), sources, repos
    )
    app = GitApp(type="git", repo="source")
    prepare_git_source("new", app, sources, repos)
    assert git(repos / "old", "rev-parse", "HEAD") == first
    assert git(repos / "new", "rev-parse", "HEAD") == second
    assert (legacy / "user-file").read_text() == "retain"


def test_changed_declaration_refuses_cache_without_force(origin, tmp_path):
    _source, first, second = origin
    repos = tmp_path / "git-cache"
    original = GitApp(type="git", repo=URL, ref=first)
    prepare_git_source("chart", original, {}, repos)
    changed = GitApp(type="git", repo=URL, ref=second)
    with pytest.raises(GitSourceError, match="differs"):
        read_prepared_git_source("chart", changed, {}, repos)
    with pytest.raises(GitSourceError, match="differs"):
        prepare_git_source("chart", changed, {}, repos)
    assert read_prepared_git_source("chart", original, {}, repos)["head"] == first


@pytest.mark.parametrize("change", ["tracked", "untracked", "origin", "head", "marker"])
def test_modified_cache_is_preserved_even_with_force(origin, tmp_path, change):
    _source, first, second = origin
    repos = tmp_path / "git-cache"
    app = GitApp(type="git", repo=URL, ref=first)
    prepare_git_source("chart", app, {}, repos)
    dest = repos / "chart"
    if change == "tracked":
        (dest / "Chart.yaml").write_text("user edit")
    elif change == "untracked":
        (dest / "user-file").write_text("user data")
    elif change == "origin":
        git(dest, "config", "remote.origin.url", "https://other.invalid/repo")
    elif change == "head":
        git(dest, "checkout", "--detach", second)
    else:
        (dest / ".git/sbkube-source.json").unlink()
    before = {
        str(p.relative_to(dest)): p.read_bytes() for p in dest.rglob("*") if p.is_file()
    }
    with pytest.raises(GitSourceError):
        prepare_git_source("chart", app, {}, repos, force=True)
    assert before == {
        str(p.relative_to(dest)): p.read_bytes() for p in dest.rglob("*") if p.is_file()
    }


@pytest.mark.timeout(10)
def test_fifo_marker_is_rejected_without_opening_it(origin, tmp_path):
    _source, first, _second = origin
    repos = tmp_path / "git-cache"
    app = GitApp(type="git", repo=URL, ref=first)
    prepare_git_source("chart", app, {}, repos)
    marker = repos / "chart/.git/sbkube-source.json"
    marker.unlink()
    os.mkfifo(marker, mode=0o600)
    with pytest.raises(GitSourceError, match="owned clone"):
        read_prepared_git_source("chart", app, {}, repos)
    assert marker.exists() and not marker.is_file()


def test_failed_ref_resolution_preserves_previous_and_removes_only_staging(
    origin, tmp_path
):
    _source, first, _second = origin
    repos = tmp_path / "git-cache"
    original = GitApp(type="git", repo=URL, ref=first)
    prepare_git_source("chart", original, {}, repos)
    with pytest.raises(GitSourceError, match="cannot be resolved"):
        prepare_git_source(
            "chart",
            GitApp(type="git", repo=URL, ref="missing-ref"),
            {},
            repos,
            force=True,
        )
    assert read_prepared_git_source("chart", original, {}, repos)["head"] == first
    assert sorted(p.name for p in repos.iterdir()) == ["chart"]


def test_failed_clone_preserves_owned_cache_and_suppresses_url(origin, tmp_path):
    _source, first, _second = origin
    repos = tmp_path / "git-cache"
    original = GitApp(type="git", repo=URL, ref=first)
    prepare_git_source("chart", original, {}, repos)
    with pytest.raises(GitSourceError) as failure:
        prepare_git_source(
            "chart",
            GitApp(type="git", repo=URL + "/missing", ref=first),
            {},
            repos,
            force=True,
        )
    assert URL not in str(failure.value)
    assert read_prepared_git_source("chart", original, {}, repos)["head"] == first
    assert sorted(p.name for p in repos.iterdir()) == ["chart"]


def test_verified_force_replacement_retains_previous_cache(origin, tmp_path):
    _source, first, second = origin
    repos = tmp_path / "git-cache"
    prepare_git_source("chart", GitApp(type="git", repo=URL, ref=first), {}, repos)
    updated = GitApp(type="git", repo=URL, ref=second)
    prepare_git_source("chart", updated, {}, repos, force=True)
    assert read_prepared_git_source("chart", updated, {}, repos)["head"] == second
    backups = list(repos.glob(".chart.previous-*"))
    assert len(backups) == 1
    assert git(backups[0], "rev-parse", "HEAD") == first


def test_chart_rejects_ignored_files_and_force_preserves_them(origin, tmp_path):
    _source, first, second = origin
    repos = tmp_path / "git-cache"
    app = GitApp(type="git", repo=URL, ref=first)
    prepare_git_source("chart", app, {}, repos)
    cache = repos / "chart"
    (cache / ".git/info/exclude").write_text("hidden.env\n")
    (cache / "hidden.env").write_text("private fixture data")
    assert read_prepared_git_source("chart", app, {}, repos)["head"] == first
    with pytest.raises(GitSourceError, match="ignored files") as failure:
        read_prepared_git_source("chart", app, {}, repos, reject_ignored=True)
    assert "hidden.env" not in str(failure.value)
    assert "private fixture data" not in str(failure.value)
    prepare_git_source(
        "chart", GitApp(type="git", repo=URL, ref=second), {}, repos, force=True
    )
    assert (
        next(repos.glob(".chart.previous-*")).joinpath("hidden.env").read_text()
        == "private fixture data"
    )


def test_git_output_bound_is_enforced_without_exposing_output():
    with pytest.raises(GitSourceError, match="1 MiB"):
        git_source._git("-c", "alias.large=!printf '%1100000s' fixture", "large")


def test_git_timeout_stops_only_the_captured_group():
    with pytest.raises(GitSourceError, match="timeout"):
        git_source._git("-c", "alias.brief=!sleep 1", "brief", timeout=0.05)


def test_exited_child_during_identity_observation_is_never_signalled(monkeypatch):
    process = Mock(pid=99999999)
    process.poll.side_effect = [None, 0, 0]
    monkeypatch.setattr(git_source, "_identity", lambda _pid: None)
    monkeypatch.setattr(git_source, "_group_present", lambda _pgid: False)
    signal_group = Mock()
    monkeypatch.setattr(git_source.os, "killpg", signal_group)
    git_source._stop(process, "captured identity")
    signal_group.assert_not_called()


@pytest.mark.parametrize(
    "observation", ["not numeric\n", "1 1\n", "0" * (1024 * 1024 + 1)]
)
def test_uncertain_group_observation_never_claims_absence(monkeypatch, observation):
    monkeypatch.setattr(
        git_source.subprocess,
        "run",
        lambda *a, **kw: subprocess.CompletedProcess(a, 0, observation),
    )
    with pytest.raises(GitSourceError) as failure:
        git_source._group_present(99999999)
    assert failure.value.retain_staging is True


@pytest.mark.parametrize("observer", ["_identity", "_group_present"])
@pytest.mark.parametrize("failure_kind", ["os_error", "timeout"])
def test_observer_failure_preserves_staging_and_previous_cache(
    origin, tmp_path, monkeypatch, observer, failure_kind
):
    _source, first, second = origin
    repos = tmp_path / "git-cache"
    original = GitApp(type="git", repo=URL, ref=first)
    prepare_git_source("chart", original, {}, repos)
    real_git = git_source._git

    def unavailable_observation(*_args, **_kwargs):
        if failure_kind == "os_error":
            raise OSError("private observer diagnostic")
        raise subprocess.TimeoutExpired(["ps"], timeout=3)

    def clone_with_uncertain_observation(*args, **kwargs):
        if args[0] != "clone":
            return real_git(*args, **kwargs)
        staging = Path(args[-1])
        (staging / "partial-clone").write_text("preserve until process ownership is known")
        with monkeypatch.context() as fault:
            fault.setattr(git_source.subprocess, "run", unavailable_observation)
            getattr(git_source, observer)(99999999)

    monkeypatch.setattr(git_source, "_git", clone_with_uncertain_observation)
    with pytest.raises(GitSourceError) as failure:
        prepare_git_source(
            "chart", GitApp(type="git", repo=URL, ref=second), {}, repos, force=True
        )
    assert failure.value.retain_staging is True
    assert "private observer diagnostic" not in str(failure.value)
    staging = list(repos.glob(".chart.clone-*"))
    assert len(staging) == 1 and (staging[0] / "partial-clone").is_file()
    assert read_prepared_git_source("chart", original, {}, repos)["head"] == first


def test_publish_failure_rolls_back_previous_cache(origin, tmp_path, monkeypatch):
    _source, first, second = origin
    repos = tmp_path / "git-cache"
    original = GitApp(type="git", repo=URL, ref=first)
    prepare_git_source("chart", original, {}, repos)
    rename = Path.rename

    def refuse_staging_publish(path, target):
        if ".clone-" in path.name:
            raise OSError("injected publish failure")
        return rename(path, target)

    monkeypatch.setattr(Path, "rename", refuse_staging_publish)
    with pytest.raises(GitSourceError, match="publish"):
        prepare_git_source(
            "chart", GitApp(type="git", repo=URL, ref=second), {}, repos, force=True
        )
    assert read_prepared_git_source("chart", original, {}, repos)["head"] == first
    assert sorted(p.name for p in repos.iterdir()) == ["chart"]


@pytest.mark.parametrize(
    "revision", ["", " ", "--upload-pack=evil", "main\x00other", "main\nother"]
)
def test_invalid_ref_fails_before_clone(tmp_path, revision, monkeypatch):
    called = []
    monkeypatch.setattr(git_source, "_git", lambda *a, **kw: called.append(a))
    with pytest.raises(GitSourceError, match="revision"):
        prepare_git_source(
            "chart",
            GitApp.model_construct(type="git", repo=URL, ref=revision),
            {},
            tmp_path / "git-cache",
        )
    assert called == []


@pytest.mark.parametrize(
    "url",
    [
        "--upload-pack=evil",
        "https://-option/repo",
        "ssh://-option/repo",
        "https://fixture.invalid/a\x00b",
    ],
)
def test_invalid_source_fails_before_clone(tmp_path, url):
    with pytest.raises(GitSourceError):
        prepare_git_source(
            "chart",
            GitApp.model_construct(type="git", repo=url),
            {},
            tmp_path / "git-cache",
        )
    assert not (tmp_path / "git-cache").exists()


def test_symlink_cache_refused_without_touching_target(origin, tmp_path):
    target = tmp_path / "user-data"
    target.mkdir()
    (target / "keep").write_text("retain")
    repos = tmp_path / "git-cache"
    repos.mkdir()
    (repos / "chart").symlink_to(target, target_is_directory=True)
    with pytest.raises(GitSourceError, match="symlink"):
        prepare_git_source("chart", GitApp(type="git", repo=URL), {}, repos, force=True)
    assert (target / "keep").read_text() == "retain"
