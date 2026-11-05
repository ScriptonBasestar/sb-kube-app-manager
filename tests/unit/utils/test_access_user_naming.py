"""Context-unique user names of the generated agent kubeconfigs.

Merged kubeconfigs share one user namespace, so the generated users must carry
the context name. Files written before the rename (users ``readonly`` and
``deploy``) must still be recognised as generated so ``init``/``issue`` can
rewrite them, while hand-made files stay protected.
"""

from pathlib import Path

import pytest
import yaml

from sbkube.utils.access_issue import (
    LEGACY_DEPLOYER_USER,
    LEGACY_READONLY_USER,
    build_deployer_kubeconfig,
    deployer_user_name,
    overwrite_problem,
    readonly_user_name,
)

CTX = "polypia-cluster"


def _generated(path: Path, user: str, token: Path, extra: dict | None = None) -> None:
    entry = {"tokenFile": str(token), **(extra or {})}
    path.write_text(yaml.safe_dump({"users": [{"name": user, "user": entry}]}))


def test_user_names_carry_cluster_and_role() -> None:
    assert readonly_user_name(CTX) == "polypia-cluster-agent-readonly"
    assert deployer_user_name(CTX) == "polypia-cluster-agent-deploy"


def test_user_names_differ_across_clusters_and_roles() -> None:
    assert readonly_user_name("a") != readonly_user_name("b")
    assert deployer_user_name("a") != deployer_user_name("b")
    assert readonly_user_name("a") != deployer_user_name("a")
    # Never the generic pre-rename names that collided when kubeconfigs merged.
    assert readonly_user_name("a") != LEGACY_READONLY_USER
    assert deployer_user_name("a") != LEGACY_DEPLOYER_USER


@pytest.mark.parametrize(
    ("user_name", "expected"),
    [(None, f"{CTX}-agent-deploy"), ("custom-user", "custom-user")],
)
def test_build_kubeconfig_uses_the_given_or_default_user(
    tmp_path: Path, user_name: str | None, expected: str
) -> None:
    admin = {
        "clusters": [{"name": "c", "cluster": {"server": "https://k:6443"}}],
        "contexts": [{"name": CTX, "context": {"cluster": "c", "user": "admin"}}],
    }
    config = build_deployer_kubeconfig(
        admin, CTX, tmp_path / "admin", tmp_path / "t", user_name
    )
    assert [u["name"] for u in config["users"]] == [expected]
    assert config["contexts"][0]["context"]["user"] == expected


def test_overwrite_accepts_current_and_legacy_generated_names(tmp_path: Path) -> None:
    token = tmp_path / "readonly.token"
    token.write_text("x")
    target = tmp_path / "kubeconfig"
    for user in (readonly_user_name(CTX), LEGACY_READONLY_USER):
        _generated(target, user, token)
        assert (
            overwrite_problem(
                target, token, readonly_user_name(CTX), (LEGACY_READONLY_USER,)
            )
            is None
        )


def test_overwrite_refuses_a_foreign_user_name(tmp_path: Path) -> None:
    token = tmp_path / "readonly.token"
    token.write_text("x")
    target = tmp_path / "kubeconfig"
    _generated(target, "someone-else", token)
    problem = overwrite_problem(
        target, token, readonly_user_name(CTX), (LEGACY_READONLY_USER,)
    )
    assert problem is not None
    assert "refusing to overwrite" in problem


def test_overwrite_refuses_the_legacy_name_unless_allowed(tmp_path: Path) -> None:
    token = tmp_path / "deploy.token"
    token.write_text("x")
    target = tmp_path / "kubeconfig"
    _generated(target, LEGACY_DEPLOYER_USER, token)
    assert overwrite_problem(target, token, deployer_user_name(CTX)) is not None


def test_overwrite_refuses_a_generated_name_with_extra_credentials(
    tmp_path: Path,
) -> None:
    # The name alone never authorises a rewrite: the user must authenticate only
    # through the token file.
    token = tmp_path / "readonly.token"
    token.write_text("x")
    target = tmp_path / "kubeconfig"
    _generated(target, readonly_user_name(CTX), token, {"token": "inline"})
    assert (
        overwrite_problem(
            target, token, readonly_user_name(CTX), (LEGACY_READONLY_USER,)
        )
        is not None
    )
