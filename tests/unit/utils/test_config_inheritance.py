"""Tests for the `_parent` inheritance resolver (sbkube.utils.config_inheritance).

The regressions these guard are *silent* ones: a broken parent reference that
degraded to "no inheritance" would still produce a document that validates --
`values` defaults to an empty list, so the chart would simply render with its
own defaults and nothing would go red. Every failure path below therefore
asserts that an exception is raised, not that a fallback happened.
"""

from pathlib import Path

import pytest
import yaml

from sbkube.models.unified_config_model import UnifiedConfig
from sbkube.utils.config_inheritance import (
    ParentResolutionError,
    resolve_inheritance,
)
from sbkube.utils.file_loader import load_config_file

PARENT_CONFIG = {
    "apiVersion": "sbkube/v1",
    "settings": {
        "namespace": "kube-system",
        "helm_repos": {"traefik": "https://helm.traefik.io/traefik"},
    },
    "apps": {
        "traefik": {
            "type": "helm",
            "enabled": True,
            "chart": "traefik/traefik",
            "version": "40.3.0",
            "namespace": "kube-system",
            "values": ["base-values.yaml"],
        },
    },
}


def _write(path: Path, document: dict) -> Path:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(yaml.safe_dump(document), encoding="utf-8")
    return path


@pytest.fixture
def workspace(tmp_path: Path) -> Path:
    """A minimal workspace: marker + `@lib` anchor + one parent component."""
    (tmp_path / ".sbkube-workspace").write_text(
        yaml.safe_dump({"anchors": {"lib": "library"}}), encoding="utf-8"
    )
    parent_dir = tmp_path / "library" / "charts" / "traefik"
    _write(parent_dir / "config.yaml", PARENT_CONFIG)
    (parent_dir / "base-values.yaml").write_text("replicas: 2\n", encoding="utf-8")
    return tmp_path


@pytest.fixture
def child(workspace: Path) -> Path:
    """A child config inheriting the parent through the `@lib` anchor."""
    return _write(
        workspace / "env" / "app_011_traefik" / "sbkube.yaml",
        {
            "apiVersion": "sbkube/v1",
            "_parent": "@lib/charts/traefik",
            "apps": {"traefik": {"values": ["values/traefik.yaml"]}},
        },
    )


class TestParentInheritanceMerge:
    """Happy paths: what the child actually ends up with."""

    def test_parent_inheritance_merges_via_lib_anchor(self, child: Path) -> None:
        """The parent's app definition and settings reach the child."""
        merged = load_config_file(str(child))

        assert "_parent" not in merged, (
            "_parent must be consumed, not forwarded to the model"
        )
        assert merged["apps"]["traefik"]["type"] == "helm"
        assert merged["apps"]["traefik"]["chart"] == "traefik/traefik"
        assert merged["settings"]["helm_repos"] == {
            "traefik": "https://helm.traefik.io/traefik"
        }

    def test_parent_inheritance_prepends_parent_values_as_absolute_paths(
        self, workspace: Path, child: Path
    ) -> None:
        """Parent values come first (helm applies later files last) and absolute.

        Relative entries would be resolved against the *child's* app directory by
        every downstream consumer, which is not where the parent's file lives.
        """
        base = workspace / "library" / "charts" / "traefik" / "base-values.yaml"

        values = load_config_file(str(child))["apps"]["traefik"]["values"]

        assert values == [str(base.resolve()), "values/traefik.yaml"]

    def test_parent_inheritance_keeps_parent_values_when_child_declares_none(
        self, workspace: Path
    ) -> None:
        """A child that overrides nothing still inherits the base values."""
        base = workspace / "library" / "charts" / "traefik" / "base-values.yaml"
        child = _write(
            workspace / "env" / "bare" / "sbkube.yaml",
            {
                "apiVersion": "sbkube/v1",
                "_parent": "@lib/charts/traefik",
                "apps": {"traefik": {}},
            },
        )

        merged = load_config_file(str(child))

        assert merged["apps"]["traefik"]["values"] == [str(base.resolve())]

    def test_parent_inheritance_child_wins_on_conflicting_scalar(
        self, workspace: Path
    ) -> None:
        """Child precedence: an explicit version pin overrides the library's."""
        child = _write(
            workspace / "env" / "pinned" / "sbkube.yaml",
            {
                "apiVersion": "sbkube/v1",
                "_parent": "@lib/charts/traefik",
                "apps": {"traefik": {"version": "39.0.8"}},
            },
        )

        merged = load_config_file(str(child))

        assert merged["apps"]["traefik"]["version"] == "39.0.8"

    def test_parent_inheritance_keeps_child_only_apps(self, child: Path) -> None:
        """Apps the parent never declares survive the merge."""
        document = yaml.safe_load(child.read_text())
        document["apps"]["whoami"] = {"type": "yaml", "manifests": ["whoami.yaml"]}
        _write(child, document)

        merged = load_config_file(str(child))

        assert sorted(merged["apps"]) == ["traefik", "whoami"]

    def test_parent_inheritance_resolves_relative_parent_ref(
        self, workspace: Path
    ) -> None:
        """A plain relative `_parent` resolves against the child's own directory."""
        child = _write(
            workspace / "env" / "rel" / "sbkube.yaml",
            {
                "apiVersion": "sbkube/v1",
                "_parent": "../../library/charts/traefik",
                "apps": {"traefik": {}},
            },
        )

        assert load_config_file(str(child))["apps"]["traefik"]["type"] == "helm"


    def test_parent_inheritance_resolves_grandparent_chain(
        self, workspace: Path
    ) -> None:
        """A parent may itself declare `_parent`; the whole chain is merged."""
        _write(
            workspace / "library" / "charts" / "traefik-hardened" / "config.yaml",
            {
                "apiVersion": "sbkube/v1",
                "_parent": "@lib/charts/traefik",
                "apps": {"traefik": {"version": "41.0.0"}},
            },
        )
        child = _write(
            workspace / "env" / "grand" / "sbkube.yaml",
            {
                "apiVersion": "sbkube/v1",
                "_parent": "@lib/charts/traefik-hardened",
                "apps": {"traefik": {}},
            },
        )

        merged = load_config_file(str(child))

        assert merged["apps"]["traefik"]["chart"] == "traefik/traefik"
        assert merged["apps"]["traefik"]["version"] == "41.0.0"

    def test_parent_inheritance_produces_a_valid_unified_config(
        self, child: Path
    ) -> None:
        """The merged document validates -- the child alone would not.

        Without inheritance the child has no `type:`, so the AppConfig
        discriminator cannot pick a variant.
        """
        assert UnifiedConfig.model_validate(load_config_file(str(child))).apps[
            "traefik"
        ]

        with pytest.raises(Exception):
            UnifiedConfig.model_validate(
                {"apiVersion": "sbkube/v1", "apps": {"traefik": {"values": ["v.yaml"]}}}
            )


class TestParentInheritanceBoundaries:
    """Anchors are workspace-scoped capabilities, not arbitrary path aliases."""

    def test_anchor_target_cannot_escape_workspace(self, tmp_path: Path) -> None:
        outside = tmp_path.parent / f"{tmp_path.name}-outside" / "parent"
        _write(outside / "config.yaml", PARENT_CONFIG)
        (tmp_path / ".sbkube-workspace").write_text(
            yaml.safe_dump({"anchors": {"lib": f"../{outside.parent.name}"}}),
            encoding="utf-8",
        )
        child = _write(
            tmp_path / "env" / "app" / "sbkube.yaml",
            {"apiVersion": "sbkube/v1", "_parent": "@lib/parent"},
        )

        with pytest.raises(ParentResolutionError, match="escapes workspace boundary"):
            load_config_file(str(child))

    def test_anchor_reference_cannot_escape_anchor_root(self, workspace: Path) -> None:
        outside = workspace / "outside"
        _write(outside / "config.yaml", PARENT_CONFIG)
        child = _write(
            workspace / "env" / "app" / "sbkube.yaml",
            {"apiVersion": "sbkube/v1", "_parent": "@lib/../outside"},
        )

        with pytest.raises(ParentResolutionError, match="escapes anchor boundary"):
            load_config_file(str(child))

    def test_anchor_parent_file_symlink_cannot_escape_anchor_root(
        self, workspace: Path
    ) -> None:
        outside = workspace / "outside" / "config.yaml"
        _write(outside, PARENT_CONFIG)
        parent_dir = workspace / "library" / "symlinked"
        parent_dir.mkdir()
        (parent_dir / "config.yaml").symlink_to(outside)
        child = _write(
            workspace / "env" / "app" / "sbkube.yaml",
            {"apiVersion": "sbkube/v1", "_parent": "@lib/symlinked"},
        )

        with pytest.raises(
            ParentResolutionError, match="parent file outside anchor boundary"
        ):
            load_config_file(str(child))


class TestParentInheritanceFailsClosed:
    """Every unresolvable reference raises. None of them degrade to a warning."""

    def test_parent_inheritance_fails_closed_on_unknown_anchor(
        self, workspace: Path
    ) -> None:
        child = _write(
            workspace / "env" / "bad" / "sbkube.yaml",
            {"apiVersion": "sbkube/v1", "_parent": "@nope/charts/traefik", "apps": {}},
        )

        with pytest.raises(ParentResolutionError, match="unknown anchor"):
            load_config_file(str(child))

    def test_parent_inheritance_fails_closed_on_missing_workspace_marker(
        self, tmp_path: Path
    ) -> None:
        child = _write(
            tmp_path / "env" / "sbkube.yaml",
            {"apiVersion": "sbkube/v1", "_parent": "@lib/charts/traefik", "apps": {}},
        )

        with pytest.raises(ParentResolutionError, match=".sbkube-workspace"):
            load_config_file(str(child))

    def test_parent_inheritance_fails_closed_on_missing_target(
        self, workspace: Path
    ) -> None:
        child = _write(
            workspace / "env" / "gone" / "sbkube.yaml",
            {"apiVersion": "sbkube/v1", "_parent": "@lib/charts/ghost", "apps": {}},
        )

        with pytest.raises(ParentResolutionError, match="does not exist"):
            load_config_file(str(child))

    def test_parent_inheritance_fails_closed_on_cycle(self, workspace: Path) -> None:
        _write(
            workspace / "library" / "charts" / "loop-a" / "config.yaml",
            {"apiVersion": "sbkube/v1", "_parent": "@lib/charts/loop-b", "apps": {}},
        )
        _write(
            workspace / "library" / "charts" / "loop-b" / "config.yaml",
            {"apiVersion": "sbkube/v1", "_parent": "@lib/charts/loop-a", "apps": {}},
        )
        child = _write(
            workspace / "env" / "loop" / "sbkube.yaml",
            {"apiVersion": "sbkube/v1", "_parent": "@lib/charts/loop-a", "apps": {}},
        )

        with pytest.raises(ParentResolutionError, match="cycle"):
            load_config_file(str(child))

    def test_parent_inheritance_fails_closed_on_relative_ref_without_a_path(
        self,
    ) -> None:
        """In-memory validation cannot resolve a relative ref -- and says so."""
        with pytest.raises(ParentResolutionError, match="relative"):
            resolve_inheritance({"apiVersion": "sbkube/v1", "_parent": "../lib"})

    def test_parent_inheritance_fails_closed_on_non_string_ref(
        self, workspace: Path
    ) -> None:
        child = _write(
            workspace / "env" / "list" / "sbkube.yaml",
            {"apiVersion": "sbkube/v1", "_parent": ["@lib/charts/traefik"], "apps": {}},
        )

        with pytest.raises(ParentResolutionError, match="non-empty string"):
            load_config_file(str(child))

    def test_parent_inheritance_rejects_parent_declaring_overrides(
        self, workspace: Path
    ) -> None:
        """`overrides` in a parent would silently resolve against the child's dir.

        Only `values` is rewritten to an absolute path, so any other
        directory-relative key must be refused rather than mis-resolved.
        """
        parent = workspace / "library" / "charts" / "traefik" / "config.yaml"
        document = yaml.safe_load(parent.read_text())
        document["apps"]["traefik"]["overrides"] = ["files/traefik.toml"]
        _write(parent, document)
        child = _write(
            workspace / "env" / "ovr" / "sbkube.yaml",
            {"apiVersion": "sbkube/v1", "_parent": "@lib/charts/traefik", "apps": {}},
        )

        with pytest.raises(ParentResolutionError, match="overrides"):
            load_config_file(str(child))


class TestParentInheritanceScope:
    """The loader is shared; inheritance must not fire on other people's YAML."""

    def test_parent_inheritance_skips_non_sbkube_documents(
        self, workspace: Path
    ) -> None:
        """A helm values file keeps its own `_parent` key untouched.

        The trigger is the document's declared kind (`apiVersion: sbkube/...`),
        not the mere presence of a key name that any chart is free to use.
        """
        values_file = _write(
            workspace / "env" / "values" / "app.yaml",
            {"_parent": "@nope/not/an/anchor", "replicas": 3},
        )

        loaded = load_config_file(str(values_file))

        assert loaded == {"_parent": "@nope/not/an/anchor", "replicas": 3}

    def test_parent_inheritance_leaves_documents_without_parent_alone(
        self, workspace: Path
    ) -> None:
        document = {"apiVersion": "sbkube/v1", "apps": {"x": {"type": "noop"}}}
        plain = _write(workspace / "env" / "plain" / "sbkube.yaml", document)

        assert load_config_file(str(plain)) == document
